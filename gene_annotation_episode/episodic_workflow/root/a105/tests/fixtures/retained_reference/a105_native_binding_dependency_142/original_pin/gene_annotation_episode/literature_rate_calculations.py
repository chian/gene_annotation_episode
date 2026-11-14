"""Deterministic A105 source-preparation rate summaries and conditional evidence.

These calculations concern a specified measured endpoint on the actual source
preparation. Oxygen consumption, for example, does not become isolated product
formation here. No target correspondence, annotation credit or episode decision
is calculated. Acquisition, source interpretation and statistical-model selection
remain outside this module.
"""
from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
from numpy.polynomial import Polynomial

from .literature_experimental_contracts import (
    ExperimentalContractError, RATE_UNITS, validate_rate_extraction,
)


VERSION = "a105_rate_contrast_sheet_v1"
_BASE_UNITS = {"amount_rate": "umol/min", "concentration_rate": "uM/min",
               "turnover_rate": "per_min", "specific_amount_rate": "umol/min/mg"}


def _error(code, field):
    raise ExperimentalContractError(code, field)


def _identity(row):
    source = row["source"]
    if source["representation"] == "native_source_spans":
        return (deepcopy(source["location"]) if source["location"] is not None else
                {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
                 "start": None, "end": None, "arm": row["arm"]})
    return {key: source[key] for key in ("source_ref", "artifact_ref", "row_number")}


def _identity_key(row):
    source = row["source"]
    if source["representation"] == "native_source_spans":
        location = source["location"]
        return (tuple(location[name] for name in ("source_ref", "artifact_ref", "representation", "start", "end")) if location is not None else
                (source["source_ref"], source["artifact_ref"], None, row["arm"]))
    return source["source_ref"], source["artifact_ref"], source["row_number"]


def _cell(value, unit, formula, rows, *, reason=None, origin="derived", conditional=()):
    if value is not None and not math.isfinite(value):
        value, reason = None, "nonfinite_calculation"
    return {"value": value, "unit": unit,
            "status": "unavailable" if value is None else "populated",
            "formula": formula, "input_rows": [_identity(row) for row in rows],
            "origin": origin, "unavailable_reason": reason,
            "conditional_on": list(conditional)}


def _select(rows, arm, condition, which):
    selected = [row for row in rows if row["arm"] == arm]
    if not selected:
        return None, f"missing_{which}_arm", []
    native = all(row["source"]["representation"] == "native_source_spans" for row in selected)
    if any(row["condition"] != condition for row in selected):
        _error("condition_mismatch", which + "_condition")
    if native:
        # A repeated observation under the other arm is a pair limitation,
        # not grounds to delete its individual reported value.
        if len(selected) != 1:
            return None, f"ambiguous_{which}_arm", selected
        row = selected[0]
        unit = row["source"]["unit"]
        reason = ("source_rate_unit_unreported" if row["source"]["number"] is not None and unit is None
                  else unit["unavailable_reason"] if unit and unit["unavailable_reason"]
                  else {"observed": None, "unavailable": "source_measurement_unavailable",
                        "censored": "censored_measurement", "conflicting": "conflicting_measurement"}[row["status"]])
        return row, reason, [row]
    # Source identity is global across the supplied extraction. Relabelling the
    # same underlying row as the other arm cannot manufacture an independent
    # comparison, even when the selected values happen to be equal.
    global_identities, conflicts = {}, set()
    for row in rows:
        key = _identity_key(row)
        if key in global_identities and global_identities[key] != row:
            conflicts.add(key)
        global_identities[key] = row
    if any(_identity_key(row) in conflicts for row in selected):
        return None, "conflicting_source_identity", selected
    identities = {}
    for row in selected:
        key = _identity_key(row)
        if key in identities and identities[key] != row:
            return None, "conflicting_source_identity", selected
        identities[key] = row
    if len(identities) != 1:
        return None, f"ambiguous_{which}_arm", selected
    row = next(iter(identities.values()))
    reason = {"observed": None, "unavailable": "source_measurement_unavailable",
              "censored": "censored_measurement", "conflicting": "conflicting_measurement"}[row["status"]]
    return row, reason, [row]


def _converted(row):
    dimension, multiplier = RATE_UNITS[row["unit"]]
    return row["value"] * multiplier, _BASE_UNITS[dimension], multiplier


def _mean_se(row, reason, unit, multiplier, model, rows):
    formula = "reported_SEM; or SD/sqrt(count) under independent normal observations"
    if reason:
        return _cell(None, unit, formula, rows, reason=reason)
    uncertainty = row["uncertainty"]
    if uncertainty.get("unavailable_reason"):
        return _cell(None, unit, formula, rows, reason=uncertainty["unavailable_reason"])
    kind, magnitude, count = (uncertainty[key] for key in ("kind", "magnitude", "count"))
    if kind == "sem":
        converted = magnitude * multiplier
        underflow = magnitude != 0 and converted == 0
        return _cell(None if underflow else converted, unit,
                     "reported_SEM*unit_multiplier", rows,
                     reason="numerical_model_range" if underflow else None,
                     origin=row["origin"] if multiplier == 1 else "derived")
    if kind != "sd":
        return _cell(None, unit, formula, rows, reason="mean_uncertainty_unreported")
    if model != "independent_normal_groups":
        return _cell(None, unit, formula, rows, reason="observation_model_unspecified")
    if count is None:
        return _cell(None, unit, formula, rows, reason="measurement_count_unreported")
    if count < 2:
        return _cell(None, unit, formula, rows, reason="insufficient_measurement_count")
    if magnitude <= 0:
        return _cell(None, unit, formula, rows, reason="positive_sd_required")
    try:
        value = magnitude * multiplier / math.sqrt(count)
    except (OverflowError, ValueError):
        value = math.inf
    underflow = value == 0
    return _cell(None if underflow else value, unit, "SD*unit_multiplier/sqrt(count)", rows,
                 reason="numerical_model_range" if underflow else None,
                 conditional=("independent_normal_groups",))


def _profile(a, b, row_a, row_b, multiplier_a, multiplier_b):
    """Global common-mean boundary fit for two unknown separate normal variances.

    The normalized cubic enumerates all real stationary points between the two
    observed means; the endpoints are evaluated too. The minimized direct
    log1p loss equals l_free-max(l_equal), without subtracting large log terms.
    No empirical variance or zero spread is repaired by a numerical epsilon.
    """
    groups = []
    for row, multiplier in ((row_a, multiplier_a), (row_b, multiplier_b)):
        error = row["uncertainty"]
        if error["kind"] != "sd":
            return None, "profile_requires_sample_sd"
        if error["count"] is None:
            return None, "measurement_count_unreported"
        if error["count"] < 2:
            return None, "insufficient_measurement_count"
        if error["magnitude"] <= 0:
            return None, "positive_sd_required"
        try:
            groups.append((float(error["count"]), error["magnitude"] * multiplier))
        except OverflowError:
            return None, "numerical_model_range"
    try:
        (na, sa), (nb, sb) = groups
        delta = b - a
        scale = max(abs(delta), sa, sb)
        if not all(math.isfinite(v) for v in (a, b, na, nb, sa, sb, delta, scale)):
            return None, "numerical_model_range"
        center = a + delta / 2
        xa, xb = (a-center)/scale, (b-center)/scale
        va, vb = (1-1/na)*(sa/scale)**2, (1-1/nb)*(sb/scale)**2
        if min(va, vb) <= 0:
            return None, "numerical_model_range"
        variable = Polynomial([0.0, 1.0])
        da, db = variable-xa, variable-xb
        # Common scaling preserves roots while preventing huge sample counts
        # from overflowing the cubic coefficients.
        nscale = max(na, nb)
        cubic = (na/nscale)*da*(vb+db*db) + (nb/nscale)*db*(va+da*da)
        lower, upper = min(xa, xb), max(xa, xb)
        roots = cubic.roots()
        interior = [float(root.real) for root in roots
                    if abs(root.imag) <= 1e-9*max(1, abs(root.real))
                    and lower <= root.real <= upper]
        candidates = sorted(set([lower, upper, *interior]))
        losses = [.5*(na*math.log1p((xa-mu)**2/va)
                       + nb*math.log1p((xb-mu)**2/vb)) for mu in candidates]
        best_index = min(range(len(losses)), key=losses.__getitem__)
        loss = losses[best_index]
        sign = 1 if a > b else -1 if a < b else 0
        result = {
            "signed_profile_log_ratio": sign*loss,
            "source_signed_index": math.tanh(sign*loss/2),
            "boundary_mean": center+scale*candidates[best_index],
            "stationary_boundary_means": [center+scale*mu for mu in interior],
            "candidate_boundary_means": [center+scale*mu for mu in candidates],
            "candidate_log_likelihood_losses": losses,
            "normalization_center": center, "normalization_scale": scale,
            "normalized_MLE_variances": [va, vb],
        }
        if not all(math.isfinite(v) for v in [result["signed_profile_log_ratio"],
                result["boundary_mean"], *result["candidate_boundary_means"], *losses]):
            return None, "numerical_model_range"
        return result, None
    except (ArithmeticError, ValueError, np.linalg.LinAlgError):
        return None, "numerical_model_range"


def populate_rate_contrast(extraction, *, reference_arm, test_arm,
                           reference_condition, test_condition,
                           dependence="unknown", observation_model="none"):
    """Populate source-rate cells; unknown assumptions remain visible unknowns.

    ``independent_normal_groups`` is an explicit conditional observation model,
    not a claim derived from a count, error-bar label or sampling-basis token.
    It does not establish independent biological preparations. Reported SEM can
    be retained without that model, but is not converted back into sample SD.
    """
    extracted = validate_rate_extraction(extraction)
    native = extracted["version"] == "a105_rate_extraction_v2"
    for name, value in (("reference_arm", reference_arm), ("test_arm", test_arm),
                        ("reference_condition", reference_condition),
                        ("test_condition", test_condition)):
        if native and name in ("reference_condition", "test_condition") and value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            _error("nonempty_selection_required", name)
    if reference_arm == test_arm:
        _error("distinct_arms_required", "test_arm")
    if dependence not in ("unknown", "independent"):
        _error("unsupported_dependence", "dependence")
    if observation_model not in ("none", "independent_normal_groups"):
        _error("unsupported_observation_model", "observation_model")
    if native:
        model = extracted["native_context"]["model"]
        if dependence != model["dependence"]["value"] or observation_model != model["observation_model"]["value"]:
            _error("native_model_selection_mismatch", "model")

    arow, areason, arows = _select(extracted["rows"], reference_arm, reference_condition, "reference")
    brow, breason, brows = _select(extracted["rows"], test_arm, test_condition, "test")
    native_pair_reason = None
    if native:
        from .literature_rate_native_inputs import native_pair_reason as reason_for_native_pair
        native_pair_reason = reason_for_native_pair(extracted)
    if arow is not None and brow is not None and not native:
        for field in ("endpoint", "normalization"):
            if arow[field] != brow[field]:
                _error(field + "_mismatch", field)
        if RATE_UNITS[arow["unit"]][0] != RATE_UNITS[brow["unit"]][0]:
            _error("incompatible_rate_dimensions", "unit")

    first_unit = next((row["unit"] for row in (arow, brow) if row is not None and row["unit"]), None)
    unit = _BASE_UNITS[RATE_UNITS[first_unit][0]] if first_unit else None
    aunit = _BASE_UNITS[RATE_UNITS[arow["unit"]][0]] if arow and arow["unit"] else None
    bunit = _BASE_UNITS[RATE_UNITS[brow["unit"]][0]] if brow and brow["unit"] else None
    if native and aunit and bunit and aunit != bunit:
        native_pair_reason, unit = "incompatible_rate_dimensions", None
    avalue, amultiplier = None, 1
    bvalue, bmultiplier = None, 1
    if arow is not None and arow["unit"] is not None:
        amultiplier = RATE_UNITS[arow["unit"]][1]
        if not areason:
            avalue, _, _ = _converted(arow)
            if not math.isfinite(avalue):
                avalue, areason = None, "nonfinite_calculation"
            elif avalue == 0 and arow["value"] != 0:
                avalue, areason = None, "numerical_model_range"
    if brow is not None and brow["unit"] is not None:
        bmultiplier = RATE_UNITS[brow["unit"]][1]
        if not breason:
            bvalue, _, _ = _converted(brow)
            if not math.isfinite(bvalue):
                bvalue, breason = None, "nonfinite_calculation"
            elif bvalue == 0 and brow["value"] != 0:
                bvalue, breason = None, "numerical_model_range"
    pair_rows = [*arows, *brows]
    pair_reason = areason or breason or native_pair_reason
    def native_origin(row, multiplier):
        if row is None:
            return "derived"
        if native:
            source_unit = row["source"]["unit"]
            return row["origin"] if source_unit and source_unit["multiplier"] == 1 else "derived"
        return row["origin"] if multiplier == 1 else "derived"
    cells = {
        "reference_rate": _cell(avalue, aunit if native else unit, "reference_value*unit_multiplier", arows,
            reason=areason, origin=native_origin(arow, amultiplier)),
        "test_rate": _cell(bvalue, bunit if native else unit, "test_value*unit_multiplier", brows,
            reason=breason, origin=native_origin(brow, bmultiplier)),
        "rate_difference": _cell(avalue-bvalue if not pair_reason else None, unit,
            "reference_rate-test_rate", pair_rows, reason=pair_reason),
    }
    ratio_reason = pair_reason or ("zero_reference_rate" if avalue == 0 else None)
    ratio = bvalue/avalue if not ratio_reason else None
    if ratio == 0 and bvalue != 0:
        ratio, ratio_reason = None, "numerical_model_range"
    cells["retained_fraction"] = _cell(ratio, "fraction", "test_rate/reference_rate",
                                      pair_rows, reason=ratio_reason)
    cells["fractional_decrease"] = _cell(1-ratio if ratio is not None else None, "fraction",
        "1-test_rate/reference_rate", pair_rows, reason=ratio_reason)
    cells["reference_mean_se"] = _mean_se(arow, areason, aunit if native else unit, amultiplier,
                                            observation_model, arows)
    cells["test_mean_se"] = _mean_se(brow, breason, bunit if native else unit, bmultiplier,
                                       observation_model, brows)
    se_a, se_b = (cells[key] for key in ("reference_mean_se", "test_mean_se"))
    se_reason = pair_reason
    if se_reason is None and dependence != "independent":
        se_reason = "dependence_unknown"
    if se_reason is None:
        se_reason = se_a["unavailable_reason"] or se_b["unavailable_reason"]
    cells["difference_se"] = _cell(
        math.hypot(se_a["value"], se_b["value"]) if se_reason is None else None,
        unit, "sqrt(reference_mean_se^2+test_mean_se^2)", pair_rows,
        reason=se_reason, conditional=tuple(dict.fromkeys([
            "independent_groups", *se_a["conditional_on"], *se_b["conditional_on"]])))

    profile_reason = pair_reason
    if profile_reason is None and observation_model != "independent_normal_groups":
        profile_reason = "observation_model_unspecified"
    if profile_reason is None and dependence != "independent":
        profile_reason = "dependence_unknown"
    if native and profile_reason is None:
        profile_reason = arow["uncertainty"].get("unavailable_reason") or brow["uncertainty"].get("unavailable_reason")
    profile = None
    if profile_reason is None:
        profile, profile_reason = _profile(avalue, bvalue, arow, brow, amultiplier, bmultiplier)
    conditional = ("independent_normal_groups", "independent_groups")
    for key, formula in (
            ("signed_profile_log_ratio", "sign(reference-test)*(l_free-max_common_mean(l_equal))"),
            ("source_signed_index", "tanh(signed_profile_log_ratio/2)")):
        cells[key] = _cell(profile[key] if profile else None, "dimensionless", formula,
            pair_rows, reason=profile_reason,
            origin="proposed" if key == "source_signed_index" else "derived",
            conditional=conditional)
    if native:
        for side, row in (("reference", arow), ("test", brow)):
            spread_unit = row["source"]["uncertainty"]["unit"] if row else None
            if spread_unit and spread_unit["multiplier"] != 1 and cells[side + "_mean_se"]["value"] is not None:
                cells[side + "_mean_se"]["origin"] = "derived"
        approximations = {side: bool(row and row["approximate"])
                          for side, row in (("reference", arow), ("test", brow))}
        for name, cell in cells.items():
            bounded_row = arow if name == "reference_rate" else brow if name == "test_rate" else None
            number = bounded_row["source"]["number"] if bounded_row else None
            relation = number["relation"] if number else "point"
            censored = relation != "point"
            # An individual source limit is information even when no point or
            # canonical quantity is available. No derived contrast bound is
            # inferred from a censored arm.
            cell["threshold"] = bounded_row["value"] if censored else None
            cell["bound"] = relation if censored else "none"
            # Mean-SE magnitudes/counts are separate source operands from an
            # approximately printed mean. Their parser retains only points.
            cell["approximate"] = (approximations["reference"] if name == "reference_rate" else
                approximations["test"] if name == "test_rate" else
                False if name in ("reference_mean_se", "test_mean_se", "difference_se") else
                any(approximations.values()))
    return {
        "version": VERSION, "axis": "A105", "scope": "source_preparation_endpoint",
        "subject": extracted["subject"], "experiment": extracted["experiment"],
        "comparison": {"reference_arm": reference_arm, "test_arm": test_arm,
            "reference_condition": reference_condition, "test_condition": test_condition,
            "endpoint": (arow or brow)["endpoint"] if arow or brow else None,
            "normalization": (arow or brow)["normalization"] if arow or brow else None},
        "model": {"dependence": dependence, "observation_model": observation_model,
            "sampling_basis_inferred": False, "index_is_annotation_probability": False},
        "source_uncertainty": {
            "reference": deepcopy(arow["uncertainty"]) if arow else None,
            "test": deepcopy(brow["uncertainty"]) if brow else None},
        "extraction": extracted, "cells": cells, "profile_diagnostics": profile,
        "annotation_credit": None, "molecule_specific_product_rate": None,
    }


__all__ = ["VERSION", "populate_rate_contrast"]
