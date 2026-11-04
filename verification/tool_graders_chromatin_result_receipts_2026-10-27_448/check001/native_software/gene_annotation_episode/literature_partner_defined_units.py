"""Source-defined activity units, with exact endpoint-bound source custody.

There is deliberately no universal U conversion. A selected source definition
supplies the positive amount, molecular entity and per-time meaning. This finite
reader verifies that relationship's bytes and lexical structure; the association
with an experiment remains an explicit scientific interpretation.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re
import unicodedata

from .domain import REF, obj
from .literature_assay_inputs import _keys, _witness_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_partner_source_fields import (
    _ALL_TAGS, _NUMBER, _PRINTED_RATE_UNIT, _RATE_UNIT_START, _contexts,
    _rate_unit, _selected_witness, _unit_continuation,
    number_selector_schema, read_source_number, validate_source_spread_unit,
)


_WITNESS_KEYS = ("source_ref", "representation", "start", "end", "quote", "artifact_ref")
_DEFINITION_KEYS = ("bridge", "clause", "amount", "amount_unit", "time_unit",
                    "endpoint", "endpoint_entity", "definition_entity")
_UNIT_KEYS = ("witness", "raw_unit", "canonical_unit", "multiplier", "definition")
_AMOUNT_SCALES = {"pmol": 1, "nmol": 1000, "umol": 1000000}
_TIME_SCALES = {"min": 1, "minute": 1, "s": 60, "second": 60}
_BRIDGE = re.compile(r"one\s+unit\s+was\s+(?:equivalent\s+to|defined\s+as)\s+", re.I)
_EVENT = re.compile(r"(?:the\s+)?(?:oxidation|reduction|formation)\s+of\s+", re.I)
_CLAUSE = re.compile(
    r"[+\-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+\-]?[0-9]+)?\s*"
    r"(?:pmol|nmol|umol)\s+(?:of\s+)?[^,;.!?]+?\s+per\s+(?:min|minute|s|second)\Z")
_U_RATE = re.compile(r"U\s*/\s*mg")
_U_START = re.compile(r"(?:[munµμ]?U|units?)\b", re.I)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _normal(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def _quantity_token(text):
    return _normal(text).replace("μ", "u").replace("µ", "u")


def _enriched_schema():
    return obj({**deepcopy(_witness_schema()["properties"]), "artifact_ref": deepcopy(REF)})


def _parsed_number_schema():
    return obj({"selector": obj({"witness": _enriched_schema(),
        "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}}),
        "raw_number": {"type": "string", "minLength": 1},
        "value": {"type": "number"}, "relation": {"enum": ["point", "lt", "le"]}})


def defined_rate_unit_schema():
    """Closed source selectors; no supplied scientific coefficient or scale."""
    fields = {name: deepcopy(_witness_schema()) for name in _DEFINITION_KEYS if name != "amount"}
    fields["amount"] = number_selector_schema()
    return obj({"kind": {"const": "source_defined_rate_unit"},
        "witness": _witness_schema(), "definition": obj(fields)})


def parsed_defined_rate_unit_schema():
    fields = {name: _enriched_schema() for name in _DEFINITION_KEYS if name != "amount"}
    fields["amount"] = _parsed_number_schema()
    return obj({"witness": _enriched_schema(), "raw_unit": {"type": "string", "minLength": 1},
        "canonical_unit": {"const": "pmol/min/mg"},
        "multiplier": {"type": "number", "exclusiveMinimum": 0}, "definition": obj(fields)})


def _witness_shape(value, field):
    _keys(value, _WITNESS_KEYS, field)
    for key in ("source_ref", "artifact_ref", "quote"):
        if not isinstance(value[key], str) or not value[key]:
            _fail("defined_unit_witness_required", field)
    if (value["representation"] not in ("original", "text")
            or type(value["start"]) is not int or type(value["end"]) is not int
            or not 0 <= value["start"] < value["end"]
            or value["end"] - value["start"] != len(value["quote"].encode("utf-8"))):
        _fail("defined_unit_witness_span_mismatch", field)


def _contained(inner, outer, field):
    _witness_shape(inner, field)
    _witness_shape(outer, field)
    identity = ("source_ref", "artifact_ref", "representation")
    if any(inner[name] != outer[name] for name in identity):
        _fail("defined_unit_source_mismatch", field)
    if not outer["start"] <= inner["start"] < inner["end"] <= outer["end"]:
        _fail("defined_unit_containment_required", field)
    left, right = inner["start"] - outer["start"], inner["end"] - outer["start"]
    if outer["quote"].encode()[left:right] != inner["quote"].encode():
        _fail("defined_unit_containment_required", field)


def _whole_entity(entity, outer, field):
    _contained(entity, outer, field)
    raw = outer["quote"].encode()
    left, right = entity["start"] - outer["start"], entity["end"] - outer["start"]
    before = raw[:left].decode()[-1:]
    after = raw[right:].decode()[:1]
    if (before and (before.isalnum() or before == "_")) or (after and (after.isalnum() or after == "_")):
        _fail("defined_unit_partial_entity", field)


def _source_witness(value, sources, field):
    """Accept the enriched endpoint only after revalidating its original fields."""
    if isinstance(value, dict) and set(value) == set(_WITNESS_KEYS):
        actual = sources.witness(_selected_witness(value), field)
        if actual != value:
            _fail("defined_unit_endpoint_mismatch", field)
        return actual
    return sources.witness(value, field)


def _finite_float(exact, field):
    try:
        value = float(exact)
    except (OverflowError, ValueError) as error:
        raise ExperimentalContractError("numerical_model_range", field) from error
    if not math.isfinite(value) or value == 0 and exact != 0:
        _fail("numerical_model_range", field)
    return value


def _number_fraction(number, field, *, point=False):
    _keys(number, ("selector", "raw_number", "value", "relation"), field)
    selector = number["selector"]
    _keys(selector, ("witness", "number_start", "number_end"), field + ".selector")
    witness = selector["witness"]
    _witness_shape(witness, field + ".selector.witness")
    start, end = selector["number_start"], selector["number_end"]
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(witness["quote"])
            or witness["quote"][start:end] != number["raw_number"]):
        _fail("defined_unit_number_record_mismatch", field)
    token = number["raw_number"]
    if (not isinstance(token, str) or not _NUMBER.fullmatch(token)
            or number["relation"] not in (("point",) if point else ("point", "lt", "le"))
            or type(number["value"]) not in (int, float)):
        _fail("defined_unit_number_record_mismatch", field)
    # Check float magnitude before allocating a rational for a hostile exponent.
    try:
        value = float(token.replace("−", "-"))
    except (ValueError, OverflowError) as error:
        raise ExperimentalContractError("numerical_model_range", field) from error
    if (not math.isfinite(value) or value == 0 and any(c in "123456789" for c in token.lower().split("e", 1)[0])):
        _fail("numerical_model_range", field)
    if number["value"] != value:
        _fail("defined_unit_number_record_mismatch", field)
    return Fraction(token.replace("−", "-"))


def _definition_scale(definition):
    """Validate saved internal associations; no sources or scientific inference."""
    _keys(definition, _DEFINITION_KEYS, "unit.definition")
    for name in _DEFINITION_KEYS:
        if name != "amount":
            _witness_shape(definition[name], "unit.definition." + name)
    bridge, clause = definition["bridge"], definition["clause"]
    _contained(clause, bridge, "unit.definition.clause")
    amount = definition["amount"]
    coefficient = _number_fraction(amount, "unit.definition.amount", point=True)
    if coefficient <= 0:
        _fail("defined_unit_positive_amount_required", "unit.definition.amount")
    # The selected number's surrounding quote may be the full clause or only
    # its exact token, but its physical numeric span must be in that clause.
    selected = amount["selector"]
    number_witness = selected["witness"]
    _contained(number_witness, bridge, "unit.definition.amount")
    token_start = number_witness["start"] + len(number_witness["quote"][:selected["number_start"]].encode())
    token = {**number_witness, "start": token_start,
        "end": token_start + len(amount["raw_number"].encode()), "quote": amount["raw_number"]}
    _contained(token, clause, "unit.definition.amount")
    for name in ("amount_unit", "time_unit", "definition_entity"):
        _contained(definition[name], clause, "unit.definition." + name)
    _whole_entity(definition["endpoint_entity"], definition["endpoint"], "unit.definition.endpoint_entity")
    _whole_entity(definition["definition_entity"], clause, "unit.definition.definition_entity")
    entity = _normal(definition["definition_entity"]["quote"])
    if entity != _normal(definition["endpoint_entity"]["quote"]):
        _fail("defined_unit_entity_mismatch", "unit.definition")
    quantity = _quantity_token(definition["amount_unit"]["quote"])
    time = _normal(definition["time_unit"]["quote"])
    if quantity not in _AMOUNT_SCALES or time not in _TIME_SCALES:
        _fail("defined_unit_quantity_time_unsupported", "unit.definition")
    # Position-specific exact gaps prevent selecting the same repeated token
    # from another branch of a multi-endpoint definition.
    pieces = (token, definition["amount_unit"], definition["definition_entity"], definition["time_unit"])
    if any(left["end"] > right["start"] for left, right in zip(pieces, pieces[1:])):
        _fail("defined_unit_clause_association_required", "unit.definition")
    raw = clause["quote"].encode()
    def gap(left, right):
        return _normal(raw[left-clause["start"]:right-clause["start"]].decode())
    if (gap(clause["start"], token["start"])
            or gap(token["end"], definition["amount_unit"]["start"])
            or gap(definition["amount_unit"]["end"], definition["definition_entity"]["start"]) not in ("", "of")
            or not re.fullmatch(r"(?:(?:oxidized|reduced|formed) )?per", gap(definition["definition_entity"]["end"], definition["time_unit"]["start"]))
            or gap(definition["time_unit"]["end"], clause["end"])):
        _fail("defined_unit_clause_association_required", "unit.definition")
    text = _quantity_token(bridge["quote"])
    prefix = _BRIDGE.match(text)
    if prefix is None:
        _fail("defined_unit_bridge_unsupported", "unit.definition.bridge")
    body = text[prefix.end():].rstrip(".").strip()
    body = _EVENT.sub("", body, count=1)
    branches = re.split(r"\s*,\s*(?:or\s+)?|\s+or\s+", body)
    if (not branches or any(not _CLAUSE.fullmatch(branch) for branch in branches)
            or _quantity_token(clause["quote"]) not in branches):
        _fail("defined_unit_bridge_association_required", "unit.definition.bridge")
    return coefficient * _AMOUNT_SCALES[quantity] * _TIME_SCALES[time]


def read_defined_rate_unit(selection, *, sources, endpoint):
    """Read one selected endpoint-specific U/mg definition, without an alias."""
    _keys(selection, ("kind", "witness", "definition"), "defined_unit")
    if selection["kind"] != "source_defined_rate_unit":
        _fail("defined_unit_kind_required", "defined_unit.kind")
    _keys(selection["definition"], _DEFINITION_KEYS, "defined_unit.definition")
    unit = sources.witness(selection["witness"], "defined_unit.witness")
    prefix, suffix = _contexts(sources, unit, 0, len(unit["quote"]))
    before = prefix[-1:]
    if ((before and (before.isalpha() or before in "_µμ/⁻¹^")) or _unit_continuation(suffix)
            or re.match(r"\s+per\b", suffix)):
        _fail("defined_unit_partial_rate_unit", "defined_unit.witness")
    if re.sub(r"\s+", "", unit["quote"]) != "U/mg":
        _fail("defined_unit_rate_unit_unsupported", "defined_unit.witness")
    definition = {name: sources.witness(value, "defined_unit.definition." + name)
        for name, value in selection["definition"].items() if name != "amount"}
    definition["amount"] = read_source_number(selection["definition"]["amount"], sources=sources, role="condition")
    if endpoint is None:
        _fail("defined_unit_endpoint_required", "defined_unit.definition.endpoint")
    if _source_witness(endpoint, sources, "defined_unit.endpoint") != definition["endpoint"]:
        _fail("defined_unit_endpoint_mismatch", "defined_unit.definition.endpoint")
    # A selected bridge cannot end before an unselected continuation of this
    # definition, or begin within a larger word/statement's unit expression.
    bridge = definition["bridge"]
    bp, bs = _contexts(sources, bridge, 0, len(bridge["quote"]))
    if bp[-1:] and (bp[-1:].isalnum() or bp[-1:] == "_"):
        _fail("defined_unit_bridge_boundary_required", "defined_unit.definition.bridge")
    if not bridge["quote"].rstrip().endswith(".") and bs.strip() and not re.match(r"\s*[.;]", bs):
        _fail("defined_unit_bridge_boundary_required", "defined_unit.definition.bridge")
    scale = _definition_scale(definition)
    return {"witness": unit, "raw_unit": unit["quote"], "canonical_unit": "pmol/min/mg",
        "multiplier": _finite_float(scale, "defined_unit.multiplier"), "definition": deepcopy(definition)}


def convert_defined_source_number(number, unit):
    """Convert a source literal using its retained, validated definition."""
    _keys(unit, _UNIT_KEYS, "defined_unit")
    _witness_shape(unit["witness"], "defined_unit.witness")
    if (not isinstance(unit["raw_unit"], str) or unit["raw_unit"] != unit["witness"]["quote"]
            or re.sub(r"\s+", "", unit["raw_unit"]) != "U/mg"
            or unit["canonical_unit"] != "pmol/min/mg"
            or type(unit["multiplier"]) not in (int, float)):
        _fail("defined_unit_record_mismatch", "defined_unit")
    scale = _definition_scale(unit["definition"])
    if unit["multiplier"] != _finite_float(scale, "defined_unit.multiplier"):
        _fail("defined_unit_conversion_mismatch", "defined_unit.multiplier")
    native = _number_fraction(number, "source_number")
    return _finite_float(native * scale, "source_number")


def _definition_selection(unit):
    definition = {name: _selected_witness(value) for name, value in unit["definition"].items() if name != "amount"}
    amount = deepcopy(unit["definition"]["amount"]["selector"])
    amount["witness"] = _selected_witness(amount["witness"])
    definition["amount"] = amount
    return {"kind": "source_defined_rate_unit", "witness": _selected_witness(unit["witness"]),
        "definition": definition}


def validate_defined_spread_unit(number, unit, *, sources):
    """Check any printed spread unit, including unselected U/mg on plain units.

    Plain parsed units are accepted for the consumer's independently selected
    spread route. They retain the original scalar guard, plus rejection of a
    source-defined unit that was not actually selected with its definition.
    """
    if not isinstance(unit, dict):
        _fail("defined_unit_record_mismatch", "defined_unit")
    _keys(number, ("selector", "raw_number", "value", "relation"), "source_number")
    if "definition" not in unit:
        validate_source_spread_unit(number, unit, sources=sources)
    else:
        _keys(unit, _UNIT_KEYS, "defined_unit")
        _keys(unit["definition"], _DEFINITION_KEYS, "defined_unit.definition")
        _keys(number["selector"], ("witness", "number_start", "number_end"), "source_number.selector")
        _witness_shape(number["selector"]["witness"], "source_number.selector.witness")
        _definition_scale(unit["definition"])
        selected = deepcopy(number["selector"])
        selected["witness"] = _selected_witness(selected["witness"])
        if read_source_number(selected, sources=sources, role="spread") != number:
            _fail("source_number_record_mismatch", "source_number")
        actual = read_defined_rate_unit(_definition_selection(unit), sources=sources,
            endpoint=unit["definition"]["endpoint"])
        if actual != unit:
            _fail("defined_unit_record_mismatch", "defined_unit")
    selected = number["selector"]
    _, suffix = _contexts(sources, selected["witness"], selected["number_start"], selected["number_end"])
    visible = html.unescape(_ALL_TAGS.sub("", suffix)).lstrip()
    defined = _U_RATE.match(visible)
    if defined:
        if (_unit_continuation(visible[defined.end():])
                or re.match(r"\s+per\b", visible[defined.end():])):
            _fail("defined_unit_partial_rate_unit", "source_number")
        if "definition" not in unit:
            _fail("defined_unit_spread_definition_required", "source_number")
        return None
    if _U_START.match(visible):
        _fail("defined_unit_spread_unit_unsupported", "source_number")
    if "definition" not in unit:
        return None
    plain = _PRINTED_RATE_UNIT.match(visible)
    if plain is None:
        if _RATE_UNIT_START.match(visible):
            _fail("unsupported_explicit_spread_unit", "source_number")
        return None
    if _unit_continuation(visible[plain.end():]):
        _fail("partial_source_rate_unit", "source_number")
    if _rate_unit(plain.group()) != (unit["canonical_unit"], unit["multiplier"]):
        _fail("source_spread_unit_mismatch", "source_number")
    return None


__all__ = ["defined_rate_unit_schema", "parsed_defined_rate_unit_schema", "read_defined_rate_unit",
           "convert_defined_source_number", "validate_defined_spread_unit"]
