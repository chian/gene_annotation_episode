"""Finite A110 numeric selectors over retained experimental reports.

Scientists select experimental meanings and the relevant spans. Shared native
scalar readers verify the actual bytes and literal numbers; this module performs
only explicit ratio/unit arithmetic. It does not infer chemistry, digitize spectra,
fit calibration, establish independence, or evaluate a physiological pathway.
Prepared historical datasets keep their own unchanged input path.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from .literature_assay_inputs import _fail, _finite, _keys, _text
from .literature_partner_source_fields import (
    _ALL_TAGS, _contexts, _unit_continuation, read_source_number,
)
from .literature_reaction_meanings import DATA_VERSION as NORMALIZED_VERSION

VERSION = "a110_source_reaction_selection_v1"
TRACE_VERSION = "a110_native_report_operands_v1"
RATIO_BASES = ("reported_molar_ratio", "source_supported_molar_ratio",
               "calibrated_molar_ratio", "signal_ratio", "unresolved")
UNCERTAINTY_KINDS = ("sample_sd", "sem", "unspecified", "unreported")
COUNT_BASES = ("independent_experiment", "biological_preparation", "technical_repeat", "unknown")
# Exact decimal scales; amount, concentration and rate dimensions never mix.
_UNITS = {
    "pmol": ("umol", Fraction(1, 1000000)), "nmol": ("umol", Fraction(1, 1000)),
    "umol": ("umol", Fraction(1)), "mmol": ("umol", Fraction(1000)),
    "nM": ("uM", Fraction(1, 1000)), "uM": ("uM", Fraction(1)), "mM": ("uM", Fraction(1000)),
}
for _native, (_canonical, _scale) in tuple(_UNITS.items()):
    for _time, _factor in (("min", 1), ("s", 60)):
        _UNITS[_native + "/" + _time] = (_canonical + "_per_min", _scale * _factor)


def _enum(value, choices, path):
    if not isinstance(value, str) or value not in choices:
        _fail("unsupported_native_reaction_meaning", path)


def _array(value, path):
    if not isinstance(value, list):
        _fail("array_required", path)


def _float(value, path):
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        from .literature_experimental_contracts import ExperimentalContractError
        raise ExperimentalContractError("numerical_model_range", path) from error
    if not math.isfinite(result) or result == 0 and value != 0:
        _fail("numerical_model_range", path)
    return result


def _number(selection, sources, path, *, role="rate", positive=False):
    number = read_source_number(selection, sources=sources, role=role)
    if number["relation"] != "point":
        _fail("native_reaction_point_required", path)
    exact = Fraction(number["raw_number"].replace("−", "-"))
    if positive and exact <= 0:
        _fail("positive_value_required", path)
    return number, exact


def _ratio(selection, sources, path):
    """One literal ratio point or the author's explicitly printed a:b form."""
    if not isinstance(selection, dict):
        _fail("closed_fields_required", path)
    kind = selection.get("kind")
    if kind == "point":
        _keys(selection, ("kind", "number"), path)
        number, exact = _number(selection["number"], sources, path)
        return _float(exact, path), {"form": "reported_point", "number": number,
            "numerator": None, "denominator": None, "value": _float(exact, path)}
    if kind != "reported_pair":
        _fail("native_reaction_ratio_form_unsupported", path)
    _keys(selection, ("kind", "numerator", "denominator"), path)
    first, numerator = _number(selection["numerator"], sources, path + ".numerator")
    second, denominator = _number(selection["denominator"], sources, path + ".denominator", positive=True)
    left, right = first["selector"], second["selector"]
    if left["witness"] != right["witness"]:
        _fail("native_reaction_pair_shared_expression_required", path)
    start, end = left["number_end"], right["number_start"]
    if start >= end or left["witness"]["quote"][start:end].strip() != ":":
        _fail("native_reaction_colon_pair_required", path)
    value = _float(numerator / denominator, path)
    return value, {"form": "normalized_reported_pair", "number": None,
        "numerator": first, "denominator": second, "value": value}


def _witnesses(value, sources, path):
    _array(value, path)
    return [sources.witness(item, f"{path}[{index}]") for index, item in enumerate(value)]


def _summary(selection, sources, path):
    _keys(selection, ("value", "uncertainty", "count"), path)
    value, ratio_trace = (None, None) if selection["value"] is None else _ratio(selection["value"], sources, path + ".value")
    uncertainty = selection["uncertainty"]
    _keys(uncertainty, ("kind", "number", "basis_witnesses"), path + ".uncertainty")
    _enum(uncertainty["kind"], UNCERTAINTY_KINDS, path + ".uncertainty.kind")
    witnesses = _witnesses(uncertainty["basis_witnesses"], sources, path + ".uncertainty.basis_witnesses")
    spread = None
    if uncertainty["number"] is not None:
        spread, exact = _number(uncertainty["number"], sources, path + ".uncertainty.number", role="spread")
        if exact < 0:
            _fail("nonnegative_value_required", path + ".uncertainty.number")
        selector = spread["selector"]
        prefix, _ = _contexts(sources, selector["witness"], selector["number_start"], selector["number_end"])
        printed = re.search(r"\b(SD|SEM|standard\s+deviation|standard\s+error)\s*[:=]?\s*$", prefix, re.I)
        if printed is not None:
            actual_kind = "sem" if printed.group(1).lower() in ("sem", "standard error") else "sample_sd"
            if uncertainty["kind"] not in (actual_kind, "unspecified"):
                _fail("native_reaction_uncertainty_label_conflict", path + ".uncertainty.kind")
    if uncertainty["kind"] == "unreported" and spread is not None:
        _fail("native_reaction_uncertainty_meaning_mismatch", path + ".uncertainty")
    # A model may interpret the experiment's design using its supporting spans;
    # literal words such as 'independent' are not a prerequisite or parser gate.
    count = selection["count"]
    _keys(count, ("number", "basis", "basis_witnesses"), path + ".count")
    _enum(count["basis"], COUNT_BASES, path + ".count.basis")
    count_witnesses = _witnesses(count["basis_witnesses"], sources, path + ".count.basis_witnesses")
    count_number, reported_n = None, None
    if count["number"] is not None:
        count_number, exact = _number(count["number"], sources, path + ".count.number", role="condition", positive=True)
        if exact.denominator != 1:
            _fail("positive_integer_count_required", path + ".count.number")
        reported_n = int(exact)
    independent_n = reported_n if count["basis"] in ("independent_experiment", "biological_preparation") else None
    sample_sd = spread["value"] if spread is not None and uncertainty["kind"] == "sample_sd" else None
    # Count and uncertainty retain independent meanings: technical/unknown n
    # never manufactures the sample size needed by the existing error identity.
    return value, sample_sd, independent_n, {"ratio": ratio_trace,
        "uncertainty": {"kind": uncertainty["kind"], "number": spread, "basis_witnesses": witnesses},
        "count": {"number": count_number, "reported_n": reported_n,
                  "basis": count["basis"], "basis_witnesses": count_witnesses}}


def _source_unit(value, sources, path):
    witness = sources.witness(value, path)
    raw = html.unescape(_ALL_TAGS.sub("", witness["quote"]))
    raw = re.sub(r"\s+", "", raw).replace("µ", "u").replace("μ", "u")
    prefix, suffix = _contexts(sources, witness, 0, len(witness["quote"]))
    if (prefix[-1:] and (prefix[-1:].isalpha() or prefix[-1:] in "_µμ/^⁻")) or _unit_continuation(suffix):
        _fail("native_reaction_partial_quantity_unit", path)
    if raw not in _UNITS:
        _fail("native_reaction_quantity_unit_unsupported", path)
    canonical, multiplier = _UNITS[raw]
    return {"witness": witness, "raw_unit": witness["quote"], "canonical_unit": canonical,
            "multiplier": _float(multiplier, path), "native_unit": raw}, multiplier


def _quantity(selection, sources, path, expected_unit):
    if selection is None:
        return None, None
    _keys(selection, ("number", "unit"), path)
    number, exact = _number(selection["number"], sources, path + ".number")
    unit, scale = _source_unit(selection["unit"], sources, path + ".unit")
    selector = number["selector"]
    _, suffix = _contexts(sources, selector["witness"], selector["number_start"], selector["number_end"])
    visible = html.unescape(_ALL_TAGS.sub("", suffix)).lstrip().replace("µ", "u").replace("μ", "u")
    # An explicitly printed cell unit takes precedence over a separately
    # nominated header/legend unit. No adjacent unit is required: shared table
    # headings remain legitimate scientifically selected associations.
    printed = re.match(r"([pnmu]?mol|[num]?M)(?:\s*/\s*(min|s))?(?![A-Za-z0-9_])", visible)
    if printed is not None:
        printed_unit = printed.group(1) + ("/" + printed.group(2) if printed.group(2) else "")
        if _unit_continuation(visible[printed.end():]):
            _fail("native_reaction_partial_quantity_unit", path + ".number")
        if printed_unit not in _UNITS:
            _fail("native_reaction_quantity_unit_unsupported", path + ".number")
        if printed_unit != unit["native_unit"]:
            _fail("native_reaction_explicit_unit_conflict", path + ".unit")
    if unit["canonical_unit"] != expected_unit:
        _fail("native_reaction_quantity_dimension_mismatch", path)
    if exact < 0:
        _fail("nonnegative_value_required", path)
    value = _float(exact * scale, path)
    return value, {"number": number, "unit": unit, "value": value}


def _parameter(selection, sources, path):
    """Declared model operands are visibly distinct from report observations."""
    if selection is None:
        return None, None
    if not isinstance(selection, dict):
        _fail("closed_fields_required", path)
    if selection.get("kind") == "source_number":
        _keys(selection, ("kind", "number", "evidence"), path)
        number, exact = _number(selection["number"], sources, path + ".number")
        value = _float(exact, path)
        evidence = _witnesses(selection["evidence"], sources, path + ".evidence")
        return value, {"value": value, "basis": "source_reported", "number": number,
                       "evidence": evidence}
    _keys(selection, ("kind", "value", "basis", "evidence"), path)
    if selection["kind"] != "declared":
        _fail("native_reaction_parameter_kind_unsupported", path + ".kind")
    _enum(selection["basis"], ("source_supported_inference", "conditional_assumption", "unresolved"), path + ".basis")
    value = selection["value"]
    if value is not None:
        _finite(value, path + ".value")
    evidence = _witnesses(selection["evidence"], sources, path + ".evidence")
    return value, {"value": value, "basis": selection["basis"], "number": None, "evidence": evidence}


def read_native_reaction_selection(selection, *, sources, origin="reported"):
    """Return normalized v2 operands plus an exact private native-source trace.

    The caller owns scope/received-source authorization through ``sources``.
    Any newly discovered selector is read through that same callback before its
    bytes are accessed. No raw native trace is added to an aggregate return.
    """
    _enum(origin, ("reported", "graph_derived", "synthetic"), "native_reaction.origin")
    _keys(selection, ("version", "ratio", "budget", "meanings"), "native_reaction")
    if selection["version"] != VERSION:
        _fail("unsupported_native_reaction_version", "native_reaction.version")
    output = {"version": NORMALIZED_VERSION, "ratio": None, "budget": None,
              "meanings": deepcopy(selection["meanings"])}
    trace = {"version": TRACE_VERSION, "ratio": None, "budget": None}
    ratio = selection["ratio"]
    if ratio is not None:
        path = "native_reaction.ratio"
        _keys(ratio, ("mode", "ratio_kind", "unit", "measurement_basis", "basis_witnesses",
            "observations", "summary", "claim", "alternatives"), path)
        _enum(ratio["measurement_basis"], RATIO_BASES, path + ".measurement_basis")
        basis = _witnesses(ratio["basis_witnesses"], sources, path + ".basis_witnesses")
        if ratio["unit"] == "mol_per_mol" and ratio["measurement_basis"] in ("signal_ratio", "unresolved"):
            _fail("native_reaction_molar_conversion_unresolved", path + ".measurement_basis")
        if ratio["unit"] == "signal_per_signal" and ratio["measurement_basis"] not in ("signal_ratio", "unresolved"):
            _fail("native_reaction_ratio_basis_unit_mismatch", path + ".measurement_basis")
        _enum(ratio["mode"], ("independent_units", "source_summary"), path + ".mode")
        _array(ratio["observations"], path + ".observations")
        units, unit_traces, seen, physical_spans = [], [], set(), set()
        for index, item in enumerate(ratio["observations"]):
            location = f"{path}.observations[{index}]"
            _keys(item, ("measurement_key", "value", "basis_witnesses"), location)
            _text(item["measurement_key"], location + ".measurement_key")
            if item["measurement_key"] in seen:
                _fail("duplicate_physical_or_model_key", location + ".measurement_key")
            seen.add(item["measurement_key"])
            value, record = _ratio(item["value"], sources, location + ".value")
            # Two labels over the exact same source expression are one
            # representation, regardless of their nominated measurement keys.
            identity_numbers = [record["number"]] if record["number"] is not None else [record["numerator"], record["denominator"]]
            physical = []
            for number in identity_numbers:
                selector = number["selector"]
                witness = selector["witness"]
                left = witness["start"] + len(witness["quote"][:selector["number_start"]].encode())
                right = witness["start"] + len(witness["quote"][:selector["number_end"]].encode())
                physical.append((witness["source_ref"], witness["artifact_ref"], left, right))
            physical = tuple(physical)
            if physical in physical_spans:
                _fail("duplicate_native_reaction_representation", location)
            physical_spans.add(physical)
            design = _witnesses(item["basis_witnesses"], sources, location + ".basis_witnesses")
            units.append({"measurement_key": item["measurement_key"], "value": value})
            unit_traces.append({"measurement_key": item["measurement_key"], "ratio": record, "basis_witnesses": design})
        mean, sd, n, summary = None, None, None, None
        if ratio["summary"] is not None:
            mean, sd, n, summary = _summary(ratio["summary"], sources, path + ".summary")
        if ratio["mode"] == "source_summary" and (units or ratio["summary"] is None):
            _fail("native_reaction_summary_mode_mismatch", path)
        if ratio["mode"] == "independent_units" and (not units or ratio["summary"] is not None):
            _fail("native_reaction_independent_mode_mismatch", path)
        claim, claim_trace = _parameter(ratio["claim"], sources, path + ".claim")
        _array(ratio["alternatives"], path + ".alternatives")
        alternatives, alternative_traces = [], []
        for index, item in enumerate(ratio["alternatives"]):
            location = f"{path}.alternatives[{index}]"
            _keys(item, ("key", "prediction"), location)
            value, record = _parameter(item["prediction"], sources, location + ".prediction")
            alternatives.append({"key": item["key"], "prediction": value})
            alternative_traces.append({"key": item["key"], "prediction": record})
        output["ratio"] = {"mode": ratio["mode"], "ratio_kind": ratio["ratio_kind"],
            "unit": ratio["unit"], "origin": origin, "observations": units,
            "mean": mean, "sample_sd": sd, "independent_n": n,
            "claim": claim, "alternatives": alternatives}
        trace["ratio"] = {"measurement_basis": ratio["measurement_basis"], "basis_witnesses": basis,
            "observations": unit_traces, "summary": summary,
            "claim": claim_trace, "alternatives": alternative_traces}
    budget = selection["budget"]
    if budget is not None:
        path = "native_reaction.budget"
        _keys(budget, ("basis", "unit", "resources_complete", "resources", "demand"), path)
        _array(budget["resources"], path + ".resources")
        resources, resource_traces = [], []
        for index, item in enumerate(budget["resources"]):
            location = f"{path}.resources[{index}]"
            _keys(item, ("resource_key", "value", "lower", "upper", "coefficient"), location)
            values, records = {}, {}
            for field in ("value", "lower", "upper"):
                values[field], records[field] = _quantity(item[field], sources, location + "." + field, budget["unit"])
            coefficient, coefficient_trace = _parameter(item["coefficient"], sources, location + ".coefficient")
            resources.append({"resource_key": item["resource_key"], **values, "coefficient": coefficient})
            resource_traces.append({"resource_key": item["resource_key"], **records, "coefficient": coefficient_trace})
        demand, demand_trace = _parameter(budget["demand"], sources, path + ".demand")
        output["budget"] = {"basis": budget["basis"], "unit": budget["unit"], "origin": origin,
            "resources_complete": budget["resources_complete"], "resources": resources, "demand": demand}
        trace["budget"] = {"resources": resource_traces, "demand": demand_trace}
    # Reuse the current reader's closed numerical validation. The local import
    # avoids changing the historical reader's import boundary.
    from .literature_reaction_inputs import _validate_ratio, _validate_budget
    _validate_ratio(output["ratio"])
    _validate_budget(output["budget"])
    return output, trace


def native_direct_references(trace):
    """Actual witnessed source roster in deterministic traversal order."""
    refs = []
    def visit(value):
        if isinstance(value, dict):
            if {"source_ref", "artifact_ref", "representation", "start", "end", "quote"} == set(value):
                refs.append(value["source_ref"])
            else:
                for item in value.values():
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(trace)
    return list(dict.fromkeys(refs))


__all__ = ["VERSION", "TRACE_VERSION", "RATIO_BASES", "COUNT_BASES", "UNCERTAINTY_KINDS",
           "read_native_reaction_selection", "native_direct_references"]
