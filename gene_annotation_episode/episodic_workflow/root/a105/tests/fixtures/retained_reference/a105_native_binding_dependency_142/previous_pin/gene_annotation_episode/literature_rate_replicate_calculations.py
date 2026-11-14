"""Source-rate summaries with explicit nested measurement/unit denominators.

These are numerical measurement components, not an overall assay-reliability
score. Equal weighting of selected sampling-unit means is explicit. Optional
SE is conditional on an IID-unit model; grouping alone establishes no such
model and supplies no assay false-positive/false-negative rate.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math
import statistics

from .literature_experimental_contracts import ExperimentalContractError, RATE_UNITS
from .literature_rate_replicate_inputs import GROUP_FIELDS, validate_rate_replicate_extraction


VERSION = "a105_rate_replicate_summary_v1"
_BASE = {"amount_rate": "umol/min", "concentration_rate": "uM/min",
         "turnover_rate": "per_min", "specific_amount_rate": "umol/min/mg"}


def _quantity(row):
    if row["value"] is None:
        return None
    # Exact decimal identity prevents equivalent unit representations from
    # being counted twice or spuriously conflicting through binary rounding.
    token = row["raw_value"].strip().lstrip("~<=> ")
    return Fraction(token) * Fraction(str(RATE_UNITS[row["unit"]][1]))


def _signature(row):
    return (tuple(row[name] for name in GROUP_FIELDS), row["sampling_unit"],
            row["sampling_basis"], RATE_UNITS[row["unit"]][0],
            row["status"], row["bound"], row["approximate"], _quantity(row))


def _cell(value, unit, formula, rows, *, reason=None, conditional=()):
    if value is not None and not math.isfinite(value):
        value, reason = None, "numerical_model_range"
    return {"value": value, "unit": unit, "formula": formula, "origin": "derived",
            "status": "populated" if value is not None else "unavailable",
            "unavailable_reason": reason, "conditional_on": list(conditional),
            "approximate": any(row["approximate"] for row in rows),
            "input_rows": [deepcopy(row["source"]) for row in rows],
            "input_origins": list(dict.fromkeys(row["origin"] for row in rows))}


def _stat(values, statistic):
    if not values:
        return None, "no_point_observations"
    if statistic == "sd" and len(values) < 2:
        return None, "insufficient_measurement_count"
    try:
        value = float(statistics.mean(values) if statistic == "mean" else statistics.stdev(values))
        if not math.isfinite(value):
            return None, "numerical_model_range"
        if value == 0:
            nonzero = (sum(values, Fraction()) != 0 if statistic == "mean"
                       else any(item != values[0] for item in values))
            if nonzero:
                return None, "numerical_model_range"
        return float(value), None
    except (ArithmeticError, ValueError):
        return None, "numerical_model_range"


def _unit_summary(rows, conflicts, unit):
    observations = {}
    for row in rows:
        observations.setdefault(row["observation_id"], row)
    unique = list(observations.values())
    conflict = any(row["observation_id"] in conflicts for row in unique)
    reasons = []
    values = []
    for row in unique:
        if row["observation_id"] in conflicts:
            reasons.append("conflicting_observation_identity")
        elif row["status"] != "observed":
            reasons.append({"censored": "censored_measurement", "not_detected": "nondetection_without_point",
                            "unavailable": "source_measurement_unavailable"}[row["status"]])
        else:
            values.append(_quantity(row))
    bases = {row["sampling_basis"] for row in unique}
    if len(bases) > 1:
        reasons.append("sampling_basis_mismatch")
    full_reason = reasons[0] if reasons else None
    mean, mean_reason = _stat(values, "mean")
    sd, sd_reason = _stat(values, "sd")
    cells = {
        "observed_point_mean": _cell(mean, unit, "sum(unique_available_points)/point_count", rows, reason=mean_reason),
        "observed_point_sd": _cell(sd, unit, "sqrt(sum((point-point_mean)^2)/(point_count-1))", rows, reason=sd_reason),
        "mean": _cell(mean if not full_reason else None, unit,
                      "sum(all_unique_measurements)/unique_measurement_count", rows, reason=full_reason or mean_reason),
    }
    exact_mean = sum(values, Fraction()) / len(values) if values and not full_reason else None
    return {"sampling_unit": rows[0]["sampling_unit"],
            "sampling_basis": next(iter(bases)) if len(bases) == 1 else None,
            "observation_ids": list(observations), "measurement_count": len(unique),
            "point_observation_ids": [row["observation_id"] for row in unique
                                      if row["status"] == "observed" and row["observation_id"] not in conflicts],
            "point_count": len(values), "representation_count": len(rows),
            "conflicting_identity": conflict, "complete": full_reason is None,
            "limitations": list(dict.fromkeys(reasons)), "cells": cells}, exact_mean


def summarize_rate_replicates(extraction, *, unit_model="none"):
    """Summarize every arm/condition/endpoint/normalization separately.

    ``iid_units`` means distinct sampling units are conditionally independent
    draws, with a common mean and finite common variance within each group.
    Across-group dependence is not specified here. No normality is required for
    this estimated SE. Its basis remains technical/biological/unspecified as
    selected; a count never establishes independent biological experiments.
    Missing and censored values remain in denominators. Full-set cells remain
    unavailable if any selected unit is incomplete; observed-point descriptive
    cells and unaffected units remain available without an imputation model.
    """
    data = validate_rate_replicate_extraction(extraction)
    if unit_model not in ("none", "iid_units"):
        raise ExperimentalContractError("unsupported_unit_model", "unit_model")
    signatures, conflicts, groups = {}, set(), {}
    for row in data["rows"]:
        identity, signature = row["observation_id"], _signature(row)
        if identity in signatures and signatures[identity] != signature:
            conflicts.add(identity)
        signatures[identity] = signature
        groups.setdefault(tuple(row[name] for name in GROUP_FIELDS), []).append(row)
    results = []
    for key, rows in groups.items():
        dimensions = {RATE_UNITS[row["unit"]][0] for row in rows}
        unit = _BASE[next(iter(dimensions))] if len(dimensions) == 1 else None
        units = {}
        for row in rows:
            units.setdefault(row["sampling_unit"], []).append(row)
        summaries, means = [], []
        for unit_rows in units.values():
            # Do not calculate within-unit means across incompatible dimensions.
            dimensions_here = {RATE_UNITS[row["unit"]][0] for row in unit_rows}
            local_unit = _BASE[next(iter(dimensions_here))] if len(dimensions_here) == 1 else None
            local_conflicts = conflicts | ({row["observation_id"] for row in unit_rows}
                                           if len(dimensions_here) != 1 else set())
            summary, mean = _unit_summary(unit_rows, local_conflicts, local_unit)
            if len(dimensions_here) != 1:
                summary["limitations"].insert(0, "incompatible_rate_dimensions")
            summaries.append(summary)
            if mean is not None:
                means.append(mean)
        bases = {row["sampling_basis"] for row in rows}
        reason = ("incompatible_rate_dimensions" if unit is None else
                  "sampling_basis_mismatch" if len(bases) != 1 else
                  "incomplete_sampling_units" if len(means) != len(units) else None)
        if reason is None:
            mean, mr = _stat(means, "mean")
            sd, sr = _stat(means, "sd")
        else:
            mean, sd, mr, sr = None, None, reason, reason
        se_reason = sr or ("unit_model_unspecified" if unit_model == "none" else None)
        se = sd / math.sqrt(len(means)) if se_reason is None else None
        if se == 0 and sd != 0:
            se, se_reason = None, "numerical_model_range"
        cells = {
            "mean": _cell(mean, unit, "sum(sampling_unit_means)/sampling_unit_count", rows, reason=mr),
            "sample_sd": _cell(sd, unit, "sqrt(sum((unit_mean-mean)^2)/(sampling_unit_count-1))", rows, reason=sr),
            "mean_se": _cell(se, unit, "sample_sd/sqrt(sampling_unit_count)", rows, reason=se_reason,
                             conditional=("iid_units",) if unit_model == "iid_units" else ()),
        }
        results.append({**dict(zip(GROUP_FIELDS, key)),
            "sampling_basis": next(iter(bases)) if len(bases) == 1 else None,
            "measurement_count": len({row["observation_id"] for row in rows}),
            "representation_count": len(rows), "sampling_unit_count": len(units),
            "complete_unit_count": sum(item["complete"] for item in summaries),
            "units": summaries, "cells": cells})
    return {"version": VERSION, "axis": "A105", "scope": "source_preparation_endpoint",
            "subject": data["subject"], "experiment": data["experiment"],
            "model": {"unit_model": unit_model, "sampling_basis_inferred": False},
            "extraction": data, "groups": results, "annotation_credit": None,
            "assay_error_rate": None}


def _exact_unit_means(data, selection):
    rows = [row for row in data["rows"]
            if all(row[name] == selection[name] for name in GROUP_FIELDS)]
    units = {}
    for row in rows:
        units.setdefault(row["sampling_unit"], {}).setdefault(row["observation_id"], row)
    return {identity: sum((_quantity(row) for row in observations.values()), Fraction()) / len(observations)
            for identity, observations in units.items()}


def _exact_cell(value, unit, formula, rows, *, reason=None, conditional=()):
    if value is not None:
        try:
            numeric = float(value)
            if not math.isfinite(numeric) or numeric == 0 and value != 0:
                numeric, reason = None, "numerical_model_range"
        except (OverflowError, ValueError):
            numeric, reason = None, "numerical_model_range"
    else:
        numeric = None
    cell = _cell(numeric, unit, formula, rows, reason=reason, conditional=conditional)
    cell["source_exact_value"] = ({"numerator": str(value.numerator), "denominator": str(value.denominator)}
                                  if value is not None else None)
    return cell


def populate_rate_replicate_contrast(extraction, *, reference, test,
                                     unit_model="none", dependence="unknown"):
    """Populate effect cells from real raw rows without fictitious summary rows.

    Each selector contains exactly GROUP_FIELDS. ``paired_units`` uses the same
    actual sampling-unit IDs on both sides and estimates the SE from unit-level
    differences. ``independent`` uses both group mean SEs and is unavailable if
    the groups explicitly share units. Neither is inferred from matching values.
    A paired result is conditional on IID *pairs*, allowing within-pair
    covariance. No test of normality or assay specificity is invented here.
    """
    for name, selector in (("reference", reference), ("test", test)):
        if not isinstance(selector, dict) or set(selector) != set(GROUP_FIELDS):
            raise ExperimentalContractError("closed_group_selection_required", name)
        if any(not isinstance(value, str) or not value.strip() for value in selector.values()):
            raise ExperimentalContractError("nonempty_selection_required", name)
    if reference == test:
        raise ExperimentalContractError("distinct_groups_required", "test")
    if dependence not in ("unknown", "independent", "paired_units"):
        raise ExperimentalContractError("unsupported_dependence", "dependence")
    summary = summarize_rate_replicates(extraction, unit_model=unit_model)
    data = summary["extraction"]
    selected = []
    for selector in (reference, test):
        selected.append(next((group for group in summary["groups"]
                              if all(group[name] == selector[name] for name in GROUP_FIELDS)), None))
    a, b = selected
    rows = [row for row in data["rows"] if any(
        all(row[name] == selector[name] for name in GROUP_FIELDS) for selector in (reference, test))]
    reason = ("missing_reference_group" if a is None else "missing_test_group" if b is None else
              a["cells"]["mean"]["unavailable_reason"] or b["cells"]["mean"]["unavailable_reason"])
    unit = a["cells"]["mean"]["unit"] if a else b["cells"]["mean"]["unit"] if b else None
    if a and b:
        if a["cells"]["mean"]["unit"] != b["cells"]["mean"]["unit"]:
            reason, unit = "incompatible_rate_dimensions", None
        elif reference["endpoint"] != test["endpoint"]:
            reason = "endpoint_mismatch"
        elif reference["normalization"] != test["normalization"]:
            reason = "normalization_mismatch"
    unit_a = {item["sampling_unit"] for item in a["units"]} if a else set()
    unit_b = {item["sampling_unit"] for item in b["units"]} if b else set()
    means_a = _exact_unit_means(data, reference) if reason is None else {}
    means_b = _exact_unit_means(data, test) if reason is None else {}
    av = sum(means_a.values(), Fraction()) / len(means_a) if means_a else None
    bv = sum(means_b.values(), Fraction()) / len(means_b) if means_b else None
    cells = {}
    for role, group in (("reference", a), ("test", b)):
        cells[role + "_rate"] = deepcopy(group["cells"]["mean"]) if group else _cell(
            None, None, "mean_of_sampling_unit_means", [], reason="missing_" + role + "_group")
    cells["rate_difference"] = _exact_cell(av - bv if reason is None else None,
        unit, "reference_rate-test_rate", rows, reason=reason)
    ratio_reason = reason or ("zero_reference_rate" if av == 0 else None)
    ratio = bv / av if ratio_reason is None else None
    cells["retained_fraction"] = _exact_cell(ratio, "fraction", "test_rate/reference_rate", rows, reason=ratio_reason)
    cells["fractional_decrease"] = _exact_cell(1-ratio if ratio is not None else None,
        "fraction", "1-test_rate/reference_rate", rows, reason=ratio_reason)
    se_reason = reason or ("dependence_unknown" if dependence == "unknown" else
                          "unit_model_unspecified" if unit_model == "none" else None)
    paired_sd, se = None, None
    paired_reason = reason or "paired_model_not_selected"
    conditional = []
    if dependence == "independent":
        conditional = ["iid_units", "independent_groups"]
        se_reason = se_reason or ("shared_sampling_units" if unit_a & unit_b else None)
        if se_reason is None:
            se_reason = a["cells"]["mean_se"]["unavailable_reason"] or b["cells"]["mean_se"]["unavailable_reason"]
        if se_reason is None:
            se = math.hypot(a["cells"]["mean_se"]["value"], b["cells"]["mean_se"]["value"])
    elif dependence == "paired_units":
        conditional = ["iid_unit_pairs"]
        paired_reason = reason or ("pairing_incomplete" if unit_a != unit_b else None)
        se_reason = se_reason or paired_reason
        if paired_reason is None:
            differences = [means_a[identity] - means_b[identity] for identity in means_a]
            paired_sd, paired_reason = _stat(differences, "sd")
            se_reason = se_reason or paired_reason
            if se_reason is None:
                se = paired_sd / math.sqrt(len(differences))
                if se == 0 and paired_sd != 0:
                    se, se_reason = None, "numerical_model_range"
    cells["paired_sample_sd"] = _cell(paired_sd, unit,
        "sample_sd(reference_unit_mean-test_unit_mean)", rows, reason=paired_reason)
    cells["difference_se"] = _cell(se, unit,
        "paired_sample_sd/sqrt(pair_count)" if dependence == "paired_units" else
        "sqrt(reference_mean_se^2+test_mean_se^2)", rows, reason=se_reason,
        conditional=conditional)
    return {"version": "a105_rate_replicate_contrast_v1", "axis": "A105",
            "scope": "source_preparation_endpoint", "subject": data["subject"],
            "experiment": data["experiment"], "reference": deepcopy(reference), "test": deepcopy(test),
            "summary": summary, "dependence": dependence,
            "pairing": {"shared_units": sorted(unit_a & unit_b),
                        "reference_only": sorted(unit_a - unit_b), "test_only": sorted(unit_b - unit_a)},
            "cells": cells, "annotation_credit": None, "assay_error_rate": None}


__all__ = ["VERSION", "summarize_rate_replicates", "populate_rate_replicate_contrast"]
