"""Source-bound operands for preparation-specific active-site titration amounts.

Scientific interpretations nominate roles; readers validate custody and literal
syntax. This module makes no model call or scientific attribution.
"""
from copy import deepcopy
from fractions import Fraction
import html
import re

from .domain import REF, obj, identity, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema, _nullable, _keys, _interpretation
from .literature_rate_native_inputs import _number, _field_contexts, _saved_number, _saved_witness
from .literature_experimental_contracts import ExperimentalContractError
from .literature_product_partition_inputs import _number as _fraction_number

VERSION = "a105_active_site_inputs_v1"
ROLES = ("protein_mass_concentration", "assumed_molecular_weight", "active_site_concentration", "reported_active_fraction")
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
LITERAL_FIELDS = ("subject", "organism", "construct", "preparation", "assay", "condition", "endpoint", "measurement_identity")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
SPREAD_KINDS = ("regression_sd", "sd", "sem", "untyped", "unreported", "unknown", "conflicting")
SAMPLING = ("same_preparation_aliquots", "independent_preparations", "unknown", "conflicting")
INTERPRETATIONS = {
    "molecular_basis": ("per_monomer", "per_dimer", "unknown", "conflicting"),
    "amount_linkage": ("same_preparation_and_assay", "different", "unknown", "conflicting"),
    "active_estimate_meaning": ("titrated_active_sites", "other", "unknown", "conflicting"),
    "titrant_concentration_basis": ("nominal_reported", "independently_standardized_active", "unknown", "conflicting"),
    "titrant_to_site_stoichiometry": ("reported_one_to_one", "other", "unknown", "conflicting"),
    "site_stoichiometry": ("one_site_per_monomer", "other", "unknown", "conflicting"),
    "normalization_stage": ("none", "total_monomer", "active_sites", "unknown", "conflicting"),
}
DEPENDENCY = "source_scalar_field_parser_completed_allocation_addition_v1"


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def active_site_arguments_schema():
    witness = _witness_schema()
    def interpreted(values):
        return obj({"value": {"enum": list(values)}, "witnesses": {"type": "array", "items": deepcopy(witness)}})
    number = obj({"witness": deepcopy(witness), "number_start": {"type": "integer", "minimum": 0},
                  "number_end": {"type": "integer", "minimum": 1}})
    unit = {"anyOf": [deepcopy(witness), obj({"conflicting_units": {
        "type": "array", "minItems": 2, "items": deepcopy(witness)}}), {"type": "null"}]}
    measurement = obj({"number": number, "unit": unit})
    spread = obj({"kind": interpreted(SPREAD_KINDS), "measurement": _nullable(deepcopy(measurement)),
        "sampling_basis": interpreted(SAMPLING), "statement": _nullable(deepcopy(witness))})
    quantity = obj({**{field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS},
        "measurement": _nullable(deepcopy(measurement)), "qualification": interpreted(QUALIFICATIONS),
        "reported_uncertainty": spread})
    return obj({"source_ref": deepcopy(REF), "source_kind": {"enum": list(SOURCE_KINDS)},
        "experiment": _nullable(deepcopy(witness)), "intended_change": _nullable(deepcopy(witness)),
        "other_changes": {"type": "array", "items": deepcopy(witness)},
        "interpretations": obj({field: interpreted(values) for field, values in INTERPRETATIONS.items()}),
        "quantities": obj({role: _nullable(deepcopy(quantity)) for role in ROLES})})


def unit_scale(raw, role):
    text = re.sub(r"\s+", "", html.unescape(re.sub(r"</?[A-Za-z_][^<>]*>", "", raw))).replace("µ", "u").replace("μ", "u")
    units = {
        "protein_mass_concentration": {"ng/uL": ("mg/mL", Fraction(1, 1000)), "mg/mL": ("mg/mL", Fraction(1)), "g/L": ("mg/mL", Fraction(1))},
        "assumed_molecular_weight": {"kDa": ("kDa", Fraction(1)), "Da": ("kDa", Fraction(1, 1000)), "g/mol": ("kDa", Fraction(1, 1000))},
        "active_site_concentration": {"nmol/L": ("nM", Fraction(1)), "umol/L": ("nM", Fraction(1000)), "mmol/L": ("nM", Fraction(1000000)), "mol/L": ("nM", Fraction(1000000000)), "nM": ("nM", Fraction(1)), "uM": ("nM", Fraction(1000)), "mM": ("nM", Fraction(1000000)), "M": ("nM", Fraction(1000000000))},
        "reported_active_fraction": {"%": ("dimensionless", Fraction(1, 100)), "percent": ("dimensionless", Fraction(1, 100)), "dimensionless": ("dimensionless", Fraction(1)), "fraction": ("dimensionless", Fraction(1))},
    }
    return units[role].get(text)


_UNIT = re.compile(r"\s*((?:[npkmuµμ]?mol\s*/\s*[npkmuµμ]?L)|(?:[npkmuµμ]?g\s*/\s*[npkmuµμ]?L)|(?:[npkmuµμ]?g\s*/\s*mol)|(?:k?Da)|(?:[npkmuµμ]?M)|%|percent\b|dimensionless\b|fraction\b)")
_CONTINUATION = re.compile(r"(?:[A-Za-z_µμ%⁻¹^/]|\s*(?:/|\^|[-−⁻]\s*[1¹]|per\s+(?:[npkmuµμ]?(?:g|mol|L)|s|min|h)\b))")


def _unit(selection, sources, role):
    if selection is None:
        return None
    if "conflicting_units" in selection:
        witnesses = [_unit(value, sources, role)["witness"] for value in selection["conflicting_units"]]
        if len({(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in witnesses}) < 2:
            _fail("distinct_conflicting_unit_witnesses_required", role)
        return {"witness": None, "raw_unit": None, "canonical_unit": None, "conflicting_units": witnesses}
    witness = sources.witness(selection, role + ".unit")
    before, after = _field_contexts(sources, witness, 0, len(witness["quote"]))
    if (before[-1:] and (before[-1:].isalpha() or before[-1:] in "_µμ/^⁻") or _CONTINUATION.match(after)):
        _fail("partial_source_active_site_unit", role)
    parsed = unit_scale(witness["quote"], role)
    return {"witness": witness, "raw_unit": witness["quote"], "canonical_unit": parsed[0] if parsed else None, "conflicting_units": []}


def _explicit_unit(number, unit, sources, role):
    if number is None or unit is None or unit["conflicting_units"]:
        return
    ns = number["selector"]
    _, suffix = _field_contexts(sources, ns["witness"], ns["number_start"], ns["number_end"])
    # A displayed central estimate and its spread may share the trailing unit.
    suffix = re.sub(r"^\s*±\s*[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?", "", suffix)
    match = _UNIT.match(suffix)
    if match:
        if _CONTINUATION.match(suffix[match.end():]):
            _fail("partial_source_active_site_unit", role)
        actual, selected = unit_scale(match.group(1), role), unit_scale(unit["raw_unit"], role)
        if actual is None:
            compact = lambda raw: re.sub(r"\s+", "", raw).replace("µ", "u").replace("μ", "u")
            if compact(match.group(1)) != compact(unit["raw_unit"]):
                _fail("source_active_site_unit_mismatch", role)
        elif actual != selected:
            _fail("source_active_site_unit_mismatch", role)
    elif re.match(r"\s*(?:/|per\s+|[npkmuµμ]?(?:g|mol|L)\b|s\b|min\b)", suffix):
        _fail("source_active_site_unit_mismatch", role)


def measurement_location(number):
    if number is None:
        return None
    ns, w = number["selector"], number["selector"]["witness"]
    return {"source_ref": w["source_ref"], "artifact_ref": w["artifact_ref"],
        "start": w["start"] + len(w["quote"][:ns["number_start"]].encode()),
        "end": w["start"] + len(w["quote"][:ns["number_end"]].encode())}


def _derived_quantity(row, role, synthetic):
    number, unit = row["number"], row["unit"]
    parsed = unit_scale(unit["raw_unit"], role) if unit and not unit["conflicting_units"] else None
    exact = Fraction(number["raw_number"].replace("−", "-")) * parsed[1] if number and parsed else None
    reason = ("source_measurement_unavailable" if number is None else "source_unit_unreported" if unit is None
        else "source_unit_conflicting" if unit["conflicting_units"] else "unsupported_source_unit" if parsed is None
        else "negative_physical_amount" if exact < 0 else "nonpositive_molecular_weight" if role == "assumed_molecular_weight" and exact == 0 and number["relation"] not in ("gt", "ge") else "empty_nonnegative_amount_domain" if exact == 0 and number["relation"] == "lt" else None)
    return {"exact_value": str(exact) if exact is not None else None, "unavailable_reason": reason,
        "measurement_key": identity("active_site_measurement", measurement_location(number)) if number else None,
        "physical_observation_key": identity("active_site_observation", {field: row["meanings"]["measurement_identity"][field]
            for field in ("source_ref", "artifact_ref", "start", "end")}) if row["meanings"]["measurement_identity"] else None,
        "bound": number["relation"] if number and number["relation"] != "point" else "none",
        "approximate": bool(number and number["approximate"] or row["qualification"]["value"] == "source_qualified_approximate"),
        "origin": "synthetic" if synthetic else "derived" if parsed and parsed[1] != 1 else "reported"}


def _interpret(value, allowed, sources, field):
    if value["value"] == "unreported" and not value["witnesses"]:
        return {"value": "unreported", "witnesses": []}
    result = _interpretation(value, allowed, sources, field)
    return {key: result[key] for key in ("value", "witnesses")}


def read_active_site_inputs(arguments, *, read_source):
    validate_schema(arguments, active_site_arguments_schema())
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    w = lambda value, field: None if value is None else sources.witness(value, field)
    result = {"version": VERSION, "source_ref": arguments["source_ref"], "source_kind": arguments["source_kind"],
        "experiment": w(arguments["experiment"], "experiment"), "intended_change": w(arguments["intended_change"], "intended_change"),
        "other_changes": [sources.witness(item, "other_changes") for item in arguments["other_changes"]],
        "interpretations": {field: _interpret(arguments["interpretations"][field], allowed, sources, field)
            for field, allowed in INTERPRETATIONS.items()}, "quantities": {}}
    for role in ROLES:
        selected = arguments["quantities"][role]
        if selected is None:
            result["quantities"][role] = None
            continue
        row = {"meanings": {field: w(selected[field], role + "." + field) for field in LITERAL_FIELDS},
            "qualification": _interpret(selected["qualification"], QUALIFICATIONS, sources, role + ".qualification")}
        measurement = selected["measurement"]
        row["number"] = (_fraction_number(measurement["number"], sources) if role == "reported_active_fraction" else _number(measurement["number"], sources, "rate")) if measurement else None
        row["unit"] = _unit(measurement["unit"], sources, role) if measurement else None
        _explicit_unit(row["number"], row["unit"], sources, role)
        unc = selected["reported_uncertainty"]
        spread = unc["measurement"]
        row["reported_uncertainty"] = {"kind": _interpret(unc["kind"], SPREAD_KINDS, sources, role + ".spread.kind"),
            "sampling_basis": _interpret(unc["sampling_basis"], SAMPLING, sources, role + ".sampling_basis"),
            "statement": w(unc["statement"], role + ".spread.statement"),
            "number": _number(spread["number"], sources, "spread") if spread else None,
            "unit": _unit(spread["unit"], sources, role) if spread else None}
        _explicit_unit(row["reported_uncertainty"]["number"], row["reported_uncertainty"]["unit"], sources, role)
        if unc["kind"]["value"] == "unreported" and spread is not None:
            _fail("unreported_spread_has_magnitude", role)
        row.update(_derived_quantity(row, role, arguments["source_kind"] == "synthetic_fixture"))
        result["quantities"][role] = row
    result.update(source_refs=list(sources.references), lexical_dependency=DEPENDENCY)
    return result


def active_site_selection_from_extraction(extraction):
    def witness(value):
        return None if value is None else {key: value[key] for key in ("source_ref", "representation", "start", "end", "quote")}
    def meaning(value):
        return {"value": value["value"], "witnesses": [witness(w) for w in value["witnesses"]]}
    def measurement(number, unit):
        return None if number is None else {"number": {**number["selector"], "witness": witness(number["selector"]["witness"])},
            "unit": {"conflicting_units": [witness(w) for w in unit["conflicting_units"]]} if unit and unit["conflicting_units"] else witness(unit["witness"]) if unit else None}
    quantities = {}
    for role, row in extraction["quantities"].items():
        if row is None:
            quantities[role] = None
            continue
        unc = row["reported_uncertainty"]
        quantities[role] = {**{field: witness(row["meanings"][field]) for field in LITERAL_FIELDS},
            "measurement": measurement(row["number"], row["unit"]), "qualification": meaning(row["qualification"]),
            "reported_uncertainty": {"kind": meaning(unc["kind"]), "sampling_basis": meaning(unc["sampling_basis"]),
                "statement": witness(unc["statement"]), "measurement": measurement(unc["number"], unc["unit"])}}
    return {"source_ref": extraction["source_ref"], "source_kind": extraction["source_kind"],
        "experiment": witness(extraction["experiment"]), "intended_change": witness(extraction["intended_change"]),
        "other_changes": [witness(w) for w in extraction["other_changes"]],
        "interpretations": {field: meaning(value) for field, value in extraction["interpretations"].items()}, "quantities": quantities}


def validate_active_site_extraction(extraction):
    """Validate committed data; source bytes and scientific meanings are not reread."""
    _keys(extraction, ("version", "source_ref", "source_kind", "experiment", "intended_change", "other_changes", "interpretations", "quantities", "source_refs", "lexical_dependency"), "extraction")
    if extraction["version"] != VERSION or extraction["lexical_dependency"] != DEPENDENCY:
        _fail("active_site_saved_version_mismatch", "version")
    def meanings(value, allowed, field):
        _keys(value, ("value", "witnesses"), field)
        if value["value"] not in allowed or not isinstance(value["witnesses"], list):
            _fail("active_site_saved_interpretation_mismatch", field)
        for w in value["witnesses"]:
            _saved_witness(w, field)
        unique = {(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in value["witnesses"]}
        required = 2 if value["value"] == "conflicting" else 0 if value["value"] in ("unknown", "unreported") else 1
        if len(unique) < required:
            _fail("interpretation_witness_required", field)
    def unit(value, role):
        if value is None:
            return
        _keys(value, ("witness", "raw_unit", "canonical_unit", "conflicting_units"), role)
        if not isinstance(value["conflicting_units"], list):
            _fail("active_site_saved_unit_mismatch", role)
        if value["conflicting_units"]:
            for w in value["conflicting_units"]:
                _saved_witness(w, role)
            if len({(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in value["conflicting_units"]}) < 2 or any(value[k] is not None for k in ("witness", "raw_unit", "canonical_unit")):
                _fail("active_site_saved_unit_mismatch", role)
        else:
            _saved_witness(value["witness"], role)
            parsed = unit_scale(value["raw_unit"], role)
            if value["raw_unit"] != value["witness"]["quote"] or value["canonical_unit"] != (parsed[0] if parsed else None):
                _fail("active_site_saved_unit_mismatch", role)
    for field in ("experiment", "intended_change"):
        if extraction[field] is not None:
            _saved_witness(extraction[field], field)
    for w in extraction["other_changes"]:
        _saved_witness(w, "other_changes")
    _keys(extraction["interpretations"], INTERPRETATIONS, "interpretations")
    for field, values in INTERPRETATIONS.items():
        meanings(extraction["interpretations"][field], values, field)
    _keys(extraction["quantities"], ROLES, "quantities")
    derived = ("exact_value", "unavailable_reason", "measurement_key", "physical_observation_key", "bound", "approximate", "origin")
    for role, row in extraction["quantities"].items():
        if row is None:
            continue
        _keys(row, ("meanings", "qualification", "number", "unit", "reported_uncertainty", *derived), role)
        _keys(row["meanings"], LITERAL_FIELDS, role)
        for field, w in row["meanings"].items():
            if w is not None:
                _saved_witness(w, role + "." + field)
        meanings(row["qualification"], QUALIFICATIONS, role + ".qualification")
        if row["number"] is not None:
            _saved_number(row["number"], role)
        unit(row["unit"], role)
        unc = row["reported_uncertainty"]
        _keys(unc, ("kind", "sampling_basis", "statement", "number", "unit"), role + ".spread")
        meanings(unc["kind"], SPREAD_KINDS, role + ".spread.kind")
        meanings(unc["sampling_basis"], SAMPLING, role + ".sampling_basis")
        if unc["statement"] is not None:
            _saved_witness(unc["statement"], role + ".spread.statement")
        if unc["number"] is not None:
            _saved_number(unc["number"], role + ".spread")
            if unc["number"]["relation"] != "point" or unc["number"]["approximate"] or unc["number"]["value"] < 0:
                _fail("plain_source_spread_required", role)
        unit(unc["unit"], role)
        expected = _derived_quantity(row, role, extraction["source_kind"] == "synthetic_fixture")
        if any(row[field] != expected[field] for field in derived):
            _fail("active_site_saved_quantity_mismatch", role)
    selection = active_site_selection_from_extraction(extraction)
    validate_schema(selection, active_site_arguments_schema())
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
    refs = extraction["source_refs"]
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or set(refs) != set(source_refs(selection)):
        _fail("active_site_source_roster_invalid", "source_refs")
    return deepcopy(extraction)


def validate_active_site_selection(arguments, extraction):
    validate_schema(arguments, active_site_arguments_schema())
    if arguments != active_site_selection_from_extraction(extraction):
        _fail("active_site_saved_selection_mismatch", "selection")
