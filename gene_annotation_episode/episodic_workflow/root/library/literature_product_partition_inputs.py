"""Exact source selections for two reported composition fractions.

Scientific meanings are witnessed interpretations. The reader verifies custody,
scalar syntax and unit conversion, without assigning catalytic attribution.
"""
from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from gene_annotation_episode.domain import REF, canonical, identity, obj, validate_schema
from ..literature_assay_inputs import _Sources, _nullable, _keys, _fail, _index
from .literature_rate_unit_witness_schema import _witness_schema
from .literature_partner_source_fields import _NUMBER, _relation, _unit_continuation
from .literature_rate_native_inputs import _field_contexts, _APPROX, _UPPER, _LOWER, _saved_number, _saved_witness

VERSION = "a105_product_partition_inputs_v1"
from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_return_schema import ROLES
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_return_schema import MEANINGS, RELATIONSHIPS, RELATIONS, BASES, STAGES, QUALIFICATIONS, EVIDENCE_ROLES


def product_partition_arguments_schema():
    witness = _witness_schema()
    def meaning(values):
        return obj({"value": {"type": "string", "enum": list(values)},
                    "witnesses": {"type": "array", "items": deepcopy(witness)}})
    number = obj({"witness": deepcopy(witness), "number_start": {"type": "integer", "minimum": 0},
                  "number_end": {"type": "integer", "minimum": 1}})
    quantity = obj({"meanings": obj({name: _nullable(deepcopy(witness)) for name in MEANINGS}),
        "measurement": _nullable(obj({"number": number, "unit": _nullable(deepcopy(witness))})),
        "basis": meaning(BASES), "stage": meaning(STAGES), "qualification": meaning(QUALIFICATIONS)})
    return obj({"source_ref": deepcopy(REF), "source_kind": {"enum": list(SOURCE_KINDS)},
        "experiment": _nullable(deepcopy(witness)),
        "quantities": obj({role: _nullable(deepcopy(quantity)) for role in ROLES}),
        "relationships": obj({name: meaning(RELATIONSHIPS) for name in RELATIONS}),
        "evidence": {"type": "array", "items": obj({"role": {"enum": list(EVIDENCE_ROLES)},
                      "witness": deepcopy(witness)})}})


def _interpret(value, sources, field):
    witnesses = [sources.witness(w, field) for w in value["witnesses"]]
    required = 2 if value["value"] == "conflicting" else 0 if value["value"] == "unknown" else 1
    if len({(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in witnesses}) < required:
        _fail("interpretation_witness_required", field)
    return {"value": value["value"], "witnesses": witnesses}


from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_number import _number

def _unit_scale(raw):
    clean = html.unescape(re.sub(r"</?[A-Za-z_][^<>]*>", "", raw)).strip().lower()
    return {"%": Fraction(1, 100), "percent": Fraction(1, 100), "per cent": Fraction(1, 100),
            "fraction": Fraction(1), "dimensionless": Fraction(1)}.get(clean)


def _unit(selection, sources, number):
    if selection is None:
        return None
    witness = sources.witness(selection, "fraction.unit")
    prefix, suffix = _field_contexts(sources, witness, 0, len(witness["quote"]))
    if (prefix[-1:] and (prefix[-1:].isalpha() or prefix[-1:] in "/_^") or
            _unit_continuation(suffix) or re.match(r"\s+per\b", suffix)):
        _fail("partial_source_fraction_unit", "fraction.unit")
    scale = _unit_scale(witness["quote"])
    if number is not None:
        ns = number["selector"]
        _, adjacent = _field_contexts(sources, ns["witness"], ns["number_start"], ns["number_end"])
        printed = re.match(r"\s*(%|percent\b|per\s+cent\b|fraction\b|dimensionless\b)", adjacent, re.I)
        if printed is not None and (_unit_scale(printed.group(1)) != scale or _unit_continuation(adjacent[printed.end():])):
            _fail("source_fraction_unit_mismatch", "fraction.unit")
        if printed is None and re.match(r"\s*(?:[pnumµμk]?M|[pnumµμk]?mol|[pnumµμk]?g|[pnumµμk]?L|ml|mL|s|sec(?:ond)?s?|min(?:ute)?s?|h|hr|hours?|days?|U)(?![A-Za-z_µμ])", adjacent):
            _fail("source_fraction_unit_mismatch", "fraction.number")
    return {"witness": witness, "raw_unit": witness["quote"],
            "multiplier": float(scale) if scale is not None else None}


def _quantity(number, unit, selected, origin):
    scale = _unit_scale(unit["raw_unit"]) if unit else None
    exact = Fraction(number["raw_number"].replace("−", "-")) * scale if number and scale is not None else None
    value = float(exact) if exact is not None else None
    if value is not None and (not math.isfinite(value) or value == 0 and exact != 0):
        _fail("numerical_model_range", "fraction")
    key = None
    if number:
        ns, w = number["selector"], number["selector"]["witness"]
        key = identity("partition_measurement", {"source_ref": w["source_ref"], "artifact_ref": w["artifact_ref"],
            "start": w["start"] + len(w["quote"][:ns["number_start"]].encode()),
            "end": w["start"] + len(w["quote"][:ns["number_end"]].encode())})
    return {"value": value, "exact_fraction": str(exact) if exact is not None else None,
        "status": "unavailable" if value is None else "observed" if number["relation"] == "point" else "censored",
        "bound": number["relation"] if number and number["relation"] != "point" else "none",
        "approximate": bool(number and number["approximate"] or selected["qualification"]["value"] == "source_qualified_approximate"), "origin": origin,
        "qualification": selected["qualification"]["value"],
        "measurement_key": key, "basis": selected["basis"]["value"], "stage": selected["stage"]["value"],
        "unavailable_reason": "source_measurement_unavailable" if number is None else
            "source_fraction_unit_unreported" if unit is None else "unsupported_source_fraction_unit" if scale is None else None}


def read_product_partition_inputs(arguments, *, read_source):
    validate_schema(arguments, product_partition_arguments_schema())
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    witness = lambda w, field: sources.witness(w, field) if w is not None else None
    selection = deepcopy(arguments)
    selection["experiment"] = witness(arguments["experiment"], "experiment")
    selection["relationships"] = {name: _interpret(v, sources, name) for name, v in arguments["relationships"].items()}
    selection["evidence"] = [{"role": row["role"], "witness": sources.witness(row["witness"], "evidence")} for row in arguments["evidence"]]
    quantities = {}
    for role in ROLES:
        selected = arguments["quantities"][role]
        if selected is None:
            quantities[role] = None
            continue
        row = {"meanings": {name: witness(w, name) for name, w in selected["meanings"].items()},
               **{name: _interpret(selected[name], sources, role + "." + name) for name in ("basis", "stage", "qualification")}}
        measurement = selected["measurement"]
        number = _number(measurement["number"], sources) if measurement else None
        unit = _unit(measurement["unit"], sources, number) if measurement else None
        row["measurement"] = {"number": number, "unit": unit} if measurement else None
        selection["quantities"][role] = row
        quantities[role] = _quantity(number, unit, row,
            "synthetic" if arguments["source_kind"] == "synthetic_fixture" else "reported")
    return {"version": VERSION, "selection": selection, "quantities": quantities, "source_refs": list(sources.references)}


def strip_witnesses(value):
    if isinstance(value, dict):
        if set(value) == {"source_ref", "artifact_ref", "representation", "start", "end", "quote"}:
            return {k: v for k, v in value.items() if k != "artifact_ref"}
        return {k: strip_witnesses(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_witnesses(v) for v in value]
    return value


def validate_product_partition_extraction(extraction, arguments=None):
    """Check stored associations and arithmetic without source IO/classification."""
    _keys(extraction, ("version", "selection", "quantities", "source_refs"), "extraction")
    if extraction["version"] != VERSION:
        _fail("partition_extraction_version_mismatch", "extraction")
    selected = deepcopy(extraction["selection"])
    for role in ROLES:
        row = selected["quantities"][role]
        if row and row["measurement"]:
            _keys(row["measurement"], ("number", "unit"), role + ".measurement")
            number, unit = row["measurement"]["number"], row["measurement"]["unit"]
            _saved_number(number, role)
            if unit is not None:
                _keys(unit, ("witness", "raw_unit", "multiplier"), role + ".unit")
            row["measurement"] = {"number": number["selector"], "unit": unit["witness"] if unit else None}
    original = strip_witnesses(selected)
    validate_schema(original, product_partition_arguments_schema())
    if arguments is None:
        arguments = original
    if original != arguments:
        _fail("partition_saved_selection_mismatch", "selection")
    refs = {arguments["source_ref"]}
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {"value", "witnesses"}:
                required = 2 if value["value"] == "conflicting" else 0 if value["value"] == "unknown" else 1
                distinct = {(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in value["witnesses"]}
                if len(distinct) < required:
                    _fail("interpretation_witness_required", "selection")
            if set(value) == {"source_ref", "artifact_ref", "representation", "start", "end", "quote"}:
                _saved_witness(value, "witness"); refs.add(value["source_ref"])
            else:
                for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(extraction["selection"])
    if (len(extraction["source_refs"]) != len(set(extraction["source_refs"])) or set(extraction["source_refs"]) != refs):
        _fail("partition_source_roster_mismatch", "source_refs")
    expected = {}
    for role in ROLES:
        row = extraction["selection"]["quantities"][role]
        measurement = row["measurement"] if row else None
        expected[role] = _quantity(measurement["number"] if measurement else None,
            measurement["unit"] if measurement else None, row,
            "synthetic" if arguments["source_kind"] == "synthetic_fixture" else "reported") if row else None
        if measurement and measurement["unit"]:
            unit = measurement["unit"]
            scale = _unit_scale(unit["raw_unit"])
            if (unit["raw_unit"] != unit["witness"]["quote"] or
                    canonical(unit["multiplier"]) != canonical(float(scale) if scale is not None else None)):
                _fail("partition_saved_unit_mismatch", role)
    if canonical(extraction["quantities"]) != canonical(expected):
        _fail("partition_saved_quantity_mismatch", "quantities")
    return extraction
