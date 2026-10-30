"""Selected source operands for preparation-specific endpoint completion times.

Models nominate meanings and source spans. This reader validates custody and
literal syntax; it makes no scientific attribution, acquisition or model call.
"""
from copy import deepcopy
from fractions import Fraction
import html
import re

from .domain import REF, obj, identity, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema, _nullable
from .literature_amount_inputs import _interpret, _saved_interpretation, _keys
from .literature_rate_native_inputs import _number, _field_contexts, _saved_number, _saved_witness
from .literature_experimental_contracts import ExperimentalContractError

VERSION = "a105_completion_time_inputs_v1"
ROLES = ("numerator", "denominator")
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
LITERAL_FIELDS = ("subject", "construct", "preparation", "condition", "endpoint", "measurement_identity")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
RELATIONS = ("same", "different", "unknown", "conflicting")
PAIR_RELATIONS = ("supported", "unknown", "conflicting")
CHANGE_STATUSES = ("described", "partial", "unknown", "conflicting")
COMPARISON_FIELDS = ("endpoint_relation", "preparation_relation", "pair_relationship", "other_changes_status")
COMPARISON_VALUES = (RELATIONS, RELATIONS, PAIR_RELATIONS, CHANGE_STATUSES)
DEPENDENCY = "source_scalar_field_parser_completed_allocation_addition_v1"
_UNIT_RE = re.compile(r"\s*(milliseconds?|microseconds?|nanoseconds?|minutes?|mins?|seconds?|secs?|hours?|days?|weeks?|ms|us|µs|μs|ns|[smhd])(?![A-Za-z_])", re.I)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def completion_time_arguments_schema():
    witness = _witness_schema()
    def interpreted(values):
        return obj({"value": {"enum": list(values)}, "witnesses": {"type": "array", "items": deepcopy(witness)}})
    number = obj({"witness": deepcopy(witness), "number_start": {"type": "integer", "minimum": 0},
                  "number_end": {"type": "integer", "minimum": 1}})
    quantity = obj({**{field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS},
        "measurement": _nullable(obj({"number": number, "unit": _nullable(deepcopy(witness))})),
        "qualification": interpreted(QUALIFICATIONS)})
    return obj({"source_ref": deepcopy(REF), "source_kind": {"enum": list(SOURCE_KINDS)},
        "experiment": _nullable(deepcopy(witness)), "intended_change": _nullable(deepcopy(witness)),
        "other_changes": {"type": "array", "items": deepcopy(witness)},
        "comparison": obj({field: interpreted(values) for field, values in zip(COMPARISON_FIELDS, COMPARISON_VALUES)}),
        "quantities": obj({role: _nullable(deepcopy(quantity)) for role in ROLES})})


def time_unit_scale(raw):
    text = html.unescape(re.sub(r"</?[A-Za-z_][^<>]*>", "", raw)).strip().lower()
    if text in ("min", "mins", "minute", "minutes"):
        return Fraction(1)
    if text in ("s", "sec", "secs", "second", "seconds"):
        return Fraction(1, 60)
    if text in ("h", "hour", "hours"):
        return Fraction(60)
    return None


def _unit(selection, sources):
    if selection is None:
        return None
    witness = sources.witness(selection, "time.unit")
    before, after = _field_contexts(sources, witness, 0, len(witness["quote"]))
    if (before[-1:] and (before[-1:].isalpha() or before[-1:] in "_/^⁻")
            or re.match(r"(?:[A-Za-z_⁻¹^/]|\s*(?:/|\^|[-−⁻]\s*[1¹]|per\s+(?:s|min|h)\b))", after)):
        _fail("partial_source_time_unit", "time.unit")
    scale = time_unit_scale(witness["quote"])
    return {"witness": witness, "raw_unit": witness["quote"], "canonical_unit": "min" if scale else None}


def _explicit_unit(number, unit, sources):
    if number is None or unit is None:
        return
    ns = number["selector"]
    _, suffix = _field_contexts(sources, ns["witness"], ns["number_start"], ns["number_end"])
    match = _UNIT_RE.match(suffix)
    if match:
        if re.match(r"\s*(?:/|\^|[-−⁻]\s*[1¹])", suffix[match.end():]):
            _fail("partial_source_time_unit", "time.number")
        if time_unit_scale(match.group(1)) != time_unit_scale(unit["raw_unit"]):
            _fail("source_time_unit_mismatch", "time.number")
    elif re.match(r"\s*(?:%|[munpkµμ]?M\b|[munpkµμ]?g\b|[munpkµμ]?mol\b|[munpkµμ]?L\b)", suffix):
        _fail("source_time_unit_mismatch", "time.number")


def measurement_location(number):
    if number is None:
        return None
    ns, w = number["selector"], number["selector"]["witness"]
    return {"source_ref": w["source_ref"], "artifact_ref": w["artifact_ref"],
        "start": w["start"] + len(w["quote"][:ns["number_start"]].encode()),
        "end": w["start"] + len(w["quote"][:ns["number_end"]].encode())}


def _derived_quantity(row, synthetic):
    number, unit = row["number"], row["unit"]
    scale = time_unit_scale(unit["raw_unit"]) if unit else None
    exact = Fraction(number["raw_number"].replace("−", "-")) * scale if number and scale else None
    reason = ("source_measurement_unavailable" if number is None else "source_time_unit_unreported" if unit is None
        else "unsupported_source_time_unit" if scale is None else "nonpositive_physical_time" if exact < 0 or
        exact == 0 and number["relation"] not in ("gt", "ge") else None)
    return {"exact_minutes": str(exact) if exact is not None else None,
        "unavailable_reason": reason,
        "measurement_key": identity("completion_time_measurement", measurement_location(number)) if number else None,
        "physical_observation_key": identity("completion_time_observation", {
            field: row["meanings"]["measurement_identity"][field] for field in ("source_ref", "artifact_ref", "start", "end")})
            if row["meanings"]["measurement_identity"] else None,
        "bound": number["relation"] if number and number["relation"] != "point" else "none",
        "approximate": bool(number and number["approximate"] or row["qualification"]["value"] == "source_qualified_approximate"),
        "origin": "synthetic" if synthetic else "derived" if scale and scale != 1 else "reported"}


def read_completion_time_inputs(arguments, *, read_source):
    validate_schema(arguments, completion_time_arguments_schema())
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    w = lambda value, field: None if value is None else sources.witness(value, field)
    result = {"version": VERSION, "source_ref": arguments["source_ref"], "source_kind": arguments["source_kind"],
        "experiment": w(arguments["experiment"], "experiment"), "intended_change": w(arguments["intended_change"], "intended_change"),
        "other_changes": [sources.witness(item, "other_changes") for item in arguments["other_changes"]],
        "comparison": {field: _interpret(arguments["comparison"][field], allowed, sources, field)
            for field, allowed in zip(COMPARISON_FIELDS, COMPARISON_VALUES)}, "quantities": {}}
    for role in ROLES:
        selected = arguments["quantities"][role]
        if selected is None:
            result["quantities"][role] = None
            continue
        row = {"meanings": {field: w(selected[field], role + "." + field) for field in LITERAL_FIELDS},
            "qualification": _interpret(selected["qualification"], QUALIFICATIONS, sources, role + ".qualification")}
        measurement = selected["measurement"]
        row["number"] = _number(measurement["number"], sources, "rate") if measurement else None
        row["unit"] = _unit(measurement["unit"], sources) if measurement else None
        _explicit_unit(row["number"], row["unit"], sources)
        row.update(_derived_quantity(row, arguments["source_kind"] == "synthetic_fixture"))
        result["quantities"][role] = row
    result.update(source_refs=list(sources.references), lexical_dependency=DEPENDENCY)
    return result


def completion_time_selection_from_extraction(extraction):
    def witness(value):
        return None if value is None else {key: value[key] for key in ("source_ref", "representation", "start", "end", "quote")}
    def meaning(value):
        return {"value": value["value"], "witnesses": [witness(w) for w in value["witnesses"]]}
    quantities = {}
    for role, row in extraction["quantities"].items():
        if row is None:
            quantities[role] = None
            continue
        number = row["number"]
        quantities[role] = {**{field: witness(row["meanings"][field]) for field in LITERAL_FIELDS},
            "measurement": None if number is None else {"number": {**number["selector"],
                "witness": witness(number["selector"]["witness"])}, "unit": witness(row["unit"]["witness"]) if row["unit"] else None},
            "qualification": meaning(row["qualification"])}
    return {"source_ref": extraction["source_ref"], "source_kind": extraction["source_kind"],
        "experiment": witness(extraction["experiment"]), "intended_change": witness(extraction["intended_change"]),
        "other_changes": [witness(w) for w in extraction["other_changes"]],
        "comparison": {field: meaning(extraction["comparison"][field]) for field in COMPARISON_FIELDS}, "quantities": quantities}


def validate_completion_time_extraction(extraction):
    """Validate committed data without scientific source reads or reinterpretation."""
    _keys(extraction, ("version", "source_ref", "source_kind", "experiment", "intended_change", "other_changes",
        "comparison", "quantities", "source_refs", "lexical_dependency"), "extraction")
    if extraction["version"] != VERSION or extraction["lexical_dependency"] != DEPENDENCY:
        _fail("completion_time_saved_version_mismatch", "version")
    for field in ("experiment", "intended_change"):
        if extraction[field] is not None:
            _saved_witness(extraction[field], field)
    if not isinstance(extraction["other_changes"], list):
        _fail("witness_list_required", "other_changes")
    for witness in extraction["other_changes"]:
        _saved_witness(witness, "other_changes")
    _keys(extraction["comparison"], COMPARISON_FIELDS, "comparison")
    for field, allowed in zip(COMPARISON_FIELDS, COMPARISON_VALUES):
        _saved_interpretation(extraction["comparison"][field], allowed, field)
    _keys(extraction["quantities"], ROLES, "quantities")
    derived = ("exact_minutes", "unavailable_reason", "measurement_key", "physical_observation_key", "bound", "approximate", "origin")
    for role, row in extraction["quantities"].items():
        if row is None:
            continue
        _keys(row, ("meanings", "qualification", "number", "unit", *derived), role)
        _keys(row["meanings"], LITERAL_FIELDS, role + ".meanings")
        for field, witness in row["meanings"].items():
            if witness is not None:
                _saved_witness(witness, role + "." + field)
        _saved_interpretation(row["qualification"], QUALIFICATIONS, role + ".qualification")
        if row["number"] is not None:
            _saved_number(row["number"], role + ".number")
        if row["unit"] is not None:
            unit = row["unit"]
            _keys(unit, ("witness", "raw_unit", "canonical_unit"), role + ".unit")
            _saved_witness(unit["witness"], role + ".unit")
            if unit["raw_unit"] != unit["witness"]["quote"] or unit["canonical_unit"] != ("min" if time_unit_scale(unit["raw_unit"]) else None):
                _fail("completion_time_saved_unit_mismatch", role)
        expected = _derived_quantity(row, extraction["source_kind"] == "synthetic_fixture")
        if any(row[field] != expected[field] for field in derived):
            _fail("completion_time_saved_quantity_mismatch", role)
    selection = completion_time_selection_from_extraction(extraction)
    validate_schema(selection, completion_time_arguments_schema())
    refs = extraction["source_refs"]
    def source_refs(value):
        if isinstance(value, dict):
            for field, child in value.items():
                if field == "source_ref":
                    yield child
                else:
                    yield from source_refs(child)
        elif isinstance(value, list):
            for child in value:
                yield from source_refs(child)
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or set(refs) != set(source_refs(selection)):
        _fail("completion_time_source_roster_invalid", "source_refs")
    return deepcopy(extraction)


def validate_completion_time_selection(arguments, extraction):
    validate_schema(arguments, completion_time_arguments_schema())
    if arguments != completion_time_selection_from_extraction(extraction):
        _fail("completion_time_saved_selection_mismatch", "selection")
