"""Exact source pairs for A105 recovery components, without scientific scoring.

Callers interpret source roles. The callback owns received-source authorization;
this module checks selected bytes, complete tokens and supported dimensions.
It acquires no source and treats matching quotations as no semantic proof.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from .domain import REF, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _interpretation, _witness_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_partner_source_fields import (
    _ALL_TAGS, _TABLE_BOUNDARY, _soft_break_numeric_token, _unit_contexts, _unit_continuation,
    number_selector_schema, read_source_number,
)

VERSION = "a105_calibration_recovery_inputs_v1"
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
LITERAL_FIELDS = ("experiment", "analyte", "matrix", "endpoint", "blank_treatment",
                  "expected_quantity_basis")
CONTROL_KINDS = ("reporter_standard", "enzyme_activity_spike", "unknown", "conflicting")
APPLICABILITIES = ("same_matrix_same_endpoint_supported", "different_matrix_or_endpoint",
                   "unknown", "conflicting")
SPREAD_KINDS = ("SD", "SEM", "unspecified", "unknown")
NUMBER_ROLES = ("nominal", "measured", "measured_spread", "reported_recovery")
_ORIGINS = {"primary_source": "reported", "retained_extraction": "derived",
            "synthetic_fixture": "synthetic"}
_FACTORS = {"pmol": ("nmol", Fraction(1, 1000)), "nmol": ("nmol", Fraction(1)),
            "umol": ("nmol", Fraction(1000)),
            "pmol/min": ("nmol/min", Fraction(1, 1000)),
            "nmol/min": ("nmol/min", Fraction(1)),
            "umol/min": ("nmol/min", Fraction(1000))}


def _nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


def _interpretation_schema(values):
    return obj({"value": {"enum": list(values)}, "witnesses": {
        "type": "array", "items": _witness_schema()}})


def calibration_recovery_population_schema():
    """Closed operation arguments: select source spans, never enter measurements."""
    return obj({"source_ref": deepcopy(REF), "source_kind": {"enum": list(SOURCE_KINDS)},
        **{name: _nullable(_witness_schema()) for name in LITERAL_FIELDS},
        "control_kind": _interpretation_schema(CONTROL_KINDS),
        "applicability": _interpretation_schema(APPLICABILITIES),
        **{name: _nullable(number_selector_schema()) for name in NUMBER_ROLES},
        "shared_unit": _nullable(_witness_schema()),
        "spread_kind": _interpretation_schema(SPREAD_KINDS),
        "reported_recovery_unit": _nullable(obj({"value": {"enum": ["fraction", "percent"]},
                                                "witness": _witness_schema()}))})


def calibration_recovery_extraction_schema():
    """Closed retained input record; no source reading is needed to validate it."""
    witness = obj({**_witness_schema()["properties"], "artifact_ref": deepcopy(REF)})
    exact = obj({"numerator": {"type": "string", "pattern": "^-?[0-9]+$"},
                 "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}})
    unit = {"witness": deepcopy(witness), "raw_unit": {"type": "string", "minLength": 1},
            "unit": {"enum": ["nmol", "nmol/min"]}, "multiplier": deepcopy(exact)}
    selector = obj({**number_selector_schema()["properties"], "witness": deepcopy(witness)})
    observation = obj({"selector": selector, "raw_number": {"type": "string", "minLength": 1},
        "native_value": {"type": "number"}, "native_exact_value": deepcopy(exact),
        "value": {"type": ["number", "null"]}, "exact_value": _nullable(exact),
        "unit": {"enum": ["nmol", "nmol/min", "fraction", None]},
        "measurement_key": deepcopy(REF), "number_start_bytes": {"type": "integer", "minimum": 0},
        "number_end_bytes": {"type": "integer", "minimum": 1},
        "origin": {"enum": ["reported", "derived", "synthetic"]}})
    def interpreted(values):
        return obj({"kind": {"const": "source_interpretation"}, "value": {"enum": list(values)},
                    "witnesses": {"type": "array", "items": deepcopy(witness)}})
    return obj({"version": {"const": VERSION}, "source_ref": deepcopy(REF), "artifact_ref": deepcopy(REF),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({name: _nullable(obj({"value": {"type": "string", "minLength": 1},
                                             "witness": deepcopy(witness)})) for name in LITERAL_FIELDS}),
        "control_kind": interpreted(CONTROL_KINDS), "applicability": interpreted(APPLICABILITIES),
        "spread_kind": interpreted(SPREAD_KINDS), "shared_unit": _nullable(obj(unit)),
        "reported_recovery_unit": _nullable(obj({**unit, "unit": {"const": "fraction"},
                                                  "value": {"enum": ["fraction", "percent"]}})),
        "observations": obj({name: _nullable(observation) for name in NUMBER_ROLES}),
        "input_origins": {"type": "array", "uniqueItems": True, "items": {"enum": ["reported", "derived", "synthetic"]}},
        "source_refs": {"type": "array", "uniqueItems": True, "items": deepcopy(REF)},
        "interpretation_limits": {"type": "array", "items": {"type": "string"}}})


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _exact(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _finite_fraction(value, field):
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ExperimentalContractError("numerical_model_range", field) from error
    if not math.isfinite(result) or result == 0 and value != 0:
        _fail("numerical_model_range", field)
    return result


def _unit_text(raw):
    fragments = [html.unescape(_ALL_TAGS.sub("", part)).strip()
                 for part in _TABLE_BOUNDARY.split(raw)]
    if sum(bool(part) for part in fragments) > 1:
        _fail("multiple_source_unit_fields", "shared_unit")
    return html.unescape(_ALL_TAGS.sub("", raw)).strip()


def _complete_unit(witness, sources, field):
    enriched = sources.witness(witness, field)
    raw = enriched["quote"]
    prefix, suffix = _unit_contexts(sources, enriched, 0, len(raw))
    before = prefix[-1:]
    if (before and (before.isalpha() or before in "_µμ/⁻¹^%")) or _unit_continuation(suffix):
        _fail("partial_source_unit", field)
    if _unit_text(raw) == "1":
        if _soft_break_numeric_token(sources, enriched, 0, len(raw), "1", pm_spread=False):
            _fail("partial_source_unit", field)
        numeric_prefix = bool(before and (before.isdigit() or before in ".eE+−-"))
        sentence_stop = suffix.startswith(".") and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ")]};:")
        numeric_suffix = bool(suffix[:1] and (suffix[0].isdigit() or suffix[0] in ".eE+−-")) and not sentence_stop
        if numeric_prefix or numeric_suffix:
            _fail("partial_source_unit", field)
    return enriched, _unit_text(raw)


def _parse_unit(raw):
    visible = _unit_text(raw)
    text = re.sub(r"\s+", "", visible).replace("µ", "u").replace("μ", "u")
    text = text.translate(str.maketrans({"−": "-", "⁻": "-", "¹": "1"})).replace("^", "")
    for amount in ("pmol", "nmol", "umol"):
        if text == amount + "min-1":
            text = amount + "/min"
    if text not in _FACTORS:
        _fail("unsupported_calibration_unit", "shared_unit")
    return _FACTORS[text]


def _read_unit(witness, sources):
    if witness is None:
        return None
    enriched, _ = _complete_unit(witness, sources, "shared_unit")
    unit, multiplier = _parse_unit(enriched["quote"])
    return {"witness": enriched, "raw_unit": enriched["quote"], "unit": unit,
            "multiplier": _exact(multiplier)}


def _read_recovery_unit(value, sources):
    if value is None:
        return None
    enriched, text = _complete_unit(value["witness"], sources, "reported_recovery_unit")
    compact = re.sub(r"\s+", " ", text).lower()
    allowed = {"fraction": ("fraction", "dimensionless", "1"),
               "percent": ("%", "percent", "per cent")}
    if compact not in allowed[value["value"]]:
        _fail("reported_recovery_unit_mismatch", "reported_recovery_unit")
    return {"value": value["value"], "witness": enriched, "raw_unit": enriched["quote"],
            "unit": "fraction", "multiplier": _exact(Fraction(1, 100) if value["value"] == "percent" else Fraction(1))}


def _check_explicit_unit(number, unit, sources, field):
    """A shared header cannot erase a different explicit unit beside a number."""
    if unit is None:
        return
    selector = number["selector"]
    _, suffix = _unit_contexts(sources, selector["witness"], selector["number_start"], selector["number_end"])
    visible = html.unescape(_ALL_TAGS.sub("", suffix)).lstrip()
    # A following plus/minus magnitude is not a unit. A selected header supplies
    # common units where no unit is printed in the selected table field.
    if re.match(r"(?:±|\+\s*/\s*-)", visible):
        return
    if not re.match(r"(?:[pnuµμ]?mol|[pnuµμm]?M|%|percent\b|per\s+cent\b)", visible):
        return
    match = re.match(r"([pnuµμ]mol)(?:\s*/\s*min|\s+min\s*\^?\s*[-−⁻]\s*[1¹])?", visible)
    if match is None:
        _fail("explicit_calibration_unit_mismatch", field)
    tail = visible[match.end():]
    if _unit_continuation(tail):
        _fail("partial_source_unit", field)
    text = re.sub(r"\s+", "", match.group()).replace("µ", "u").replace("μ", "u")
    text = text.translate(str.maketrans({"−": "-", "⁻": "-", "¹": "1"})).replace("^", "")
    for amount in ("pmol", "nmol", "umol"):
        if text == amount + "min-1":
            text = amount + "/min"
    actual = _FACTORS.get(text)
    expected = None if unit is None else (unit["unit"], Fraction(int(unit["multiplier"]["numerator"]), int(unit["multiplier"]["denominator"])))
    if actual != expected:
        _fail("explicit_calibration_unit_mismatch", field)


def _read_number(selector, unit, sources, role):
    if selector is None:
        return None
    number = read_source_number(selector, sources=sources,
                                role="spread" if role == "measured_spread" else "rate")
    if number["relation"] != "point":
        _fail("point_calibration_number_required", role)
    if role != "reported_recovery":
        _check_explicit_unit(number, unit, sources, role)
    elif unit is not None:
        selected = number["selector"]
        _, suffix = _unit_contexts(sources, selected["witness"], selected["number_start"], selected["number_end"])
        visible = html.unescape(_ALL_TAGS.sub("", suffix)).lstrip()
        if re.match(r"(?:%|percent\b|per\s+cent\b)", visible, re.I):
            if unit is None or unit["value"] != "percent":
                _fail("explicit_recovery_unit_mismatch", role)
        elif re.match(r"(?:fraction\b|dimensionless\b)", visible, re.I):
            if unit is None or unit["value"] != "fraction":
                _fail("explicit_recovery_unit_mismatch", role)
        elif re.match(r"(?:[pnumµμ]?mol|[pnumµμ]?M)(?=\b|/)", visible):
            _fail("explicit_recovery_unit_mismatch", role)
    token = number["raw_number"].replace("−", "-")
    native = Fraction(token)
    witness = number["selector"]["witness"]
    start = witness["start"] + len(witness["quote"][:selector["number_start"]].encode("utf-8"))
    end = witness["start"] + len(witness["quote"][:selector["number_end"]].encode("utf-8"))
    exact = None if unit is None else native * Fraction(int(unit["multiplier"]["numerator"]), int(unit["multiplier"]["denominator"]))
    return {"selector": number["selector"], "raw_number": number["raw_number"],
            "native_value": number["value"], "native_exact_value": _exact(native),
            "value": None if exact is None else _finite_fraction(exact, role),
            "exact_value": None if exact is None else _exact(exact),
            "unit": None if unit is None else unit["unit"],
            "measurement_key": identity("literature_measurement", {"artifact_ref": witness["artifact_ref"],
                                                                       "number_start": start, "number_end": end}),
            "number_start_bytes": start, "number_end_bytes": end}


def read_calibration_recovery_inputs(arguments, *, read_source):
    """Retain a nominated source pair and its role-specific interpretation.

    ``read_source(reference, representation)`` must authorize the actual received
    source and return exactly artifact_ref/content. Equal source values do not
    infer measurement identity; only the same artifact numeric span reuses a key.
    Literal bytes do not prove calibration applicability or experimental truth.
    """
    args = deepcopy(arguments)
    validate_schema(args, calibration_recovery_population_schema())
    sources = _Sources(read_source)
    original = sources.source(args["source_ref"], "original")
    literals = {}
    for name in LITERAL_FIELDS:
        witness = None if args[name] is None else sources.witness(args[name], name)
        literals[name] = None if witness is None else {"value": witness["quote"], "witness": witness}
    interpretations = {name: _interpretation(args[name], values, sources, name) for name, values in (
        ("control_kind", CONTROL_KINDS), ("applicability", APPLICABILITIES), ("spread_kind", SPREAD_KINDS))}
    shared_unit = _read_unit(args["shared_unit"], sources)
    recovery_unit = _read_recovery_unit(args["reported_recovery_unit"], sources)
    observations = {name: _read_number(args[name], recovery_unit if name == "reported_recovery" else shared_unit,
                                      sources, name) for name in NUMBER_ROLES}
    origin = _ORIGINS[args["source_kind"]]
    for observation in observations.values():
        if observation is not None:
            observation["origin"] = origin
    result = {"version": VERSION, "source_ref": args["source_ref"], "artifact_ref": original["artifact_ref"],
            "source_kind": args["source_kind"], "literals": literals, **interpretations,
            "shared_unit": shared_unit, "reported_recovery_unit": recovery_unit,
            "observations": observations, "input_origins": [origin], "source_refs": list(sources.references),
            "interpretation_limits": ["source_quotes_do_not_prove_scientific_roles",
                "shared_units_do_not_establish_comparison_linkage", "no_target_measurement_supplied",
                "replicate_independence_not_established", "denominator_uncertainty_and_covariance_not_supplied"]}
    validate_schema(result, calibration_recovery_extraction_schema())
    return result


__all__ = ["VERSION", "SOURCE_KINDS", "LITERAL_FIELDS", "CONTROL_KINDS", "APPLICABILITIES", "SPREAD_KINDS",
           "NUMBER_ROLES", "calibration_recovery_population_schema", "calibration_recovery_extraction_schema",
           "read_calibration_recovery_inputs"]
