"""Populate partner components from exact native source spans.

Source selection supplies scientific meanings; byte custody does not prove them.
No source acquisition, model call, state mutation or sampling inference occurs.

``native_evidence`` preserves the input arm structure with enriched witnesses.
Numeric condition ``selector`` values become complete ParsedNumber records.
Rate ``value``/``unit`` become ParsedNumber/ParsedUnit, and rate additionally has
``canonical_value`` and ``canonical_spread``. Spread ``unit`` is ParsedUnit or
null for an explicitly selected common-unit source association. ParsedNumber is exactly
{selector:{witness:<enriched>,number_start,number_end},raw_number,value,relation};
Plain ParsedUnit is exactly {witness:<enriched>,raw_unit,canonical_unit,multiplier}.
Source-defined units additionally retain the source-backed ``definition``.
Plain-only inputs keep extraction_v2; a defined rate/spread unit uses v3.
Every enriched witness is {source_ref,representation,start,end,quote,artifact_ref}.
These closed structures support saved-only validation without rereading bytes.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .domain import REF, identity, obj
from .literature_assay_inputs import (
    SOURCE_KINDS, _Sources, _fail, _keys, _nullable, _text, _witness_schema,
)
from .literature_partner_calculations import COMPONENTS, populate_partner_components
from .literature_partner_source_fields import (
    number_selector_schema, read_source_number, read_source_rate_unit,
    convert_source_number,
)
from .literature_partner_defined_units import (
    defined_rate_unit_schema, parsed_defined_rate_unit_schema,
    read_defined_rate_unit, convert_defined_source_number,
    validate_defined_spread_unit,
)


VERSION = "literature_partner_inputs_extraction_v2"
DEFINED_VERSION = "literature_partner_inputs_extraction_v3"
DATA_VERSION = "literature_partner_selection_v1"
LITERAL_FIELDS = ("subject", "partner", "experiment", "endpoint", "normalization",
                  "reference_condition", "omitted_condition", "addback_condition", "function")
ROLES = ("reference", "omitted", "addback")
IDENTITY_FIELDS = ("subject", "partner", "endpoint", "normalization")
SPREAD_KINDS = ("SD", "SEM", "CI", "unspecified", "unreported")
_ARGS = ("source_ref", "data_source_ref", "source_kind", "literals",
         "interpretation_witnesses", "input_mode", "arms")
_ARM_FIELDS = (*IDENTITY_FIELDS, "partner_state", "conditions", "measurement_identity",
               "origin", "rate")
_FACTOR = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,127}$", re.ASCII)


def _enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail("unsupported_native_value", field)


def _enriched_witness_schema():
    return obj({**deepcopy(_witness_schema()["properties"]), "artifact_ref": deepcopy(REF)})


def _parsed_number_schema():
    selector = obj({"witness": _enriched_witness_schema(),
        "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}})
    return obj({"selector": selector, "raw_number": {"type": "string", "minLength": 1},
        "value": {"type": "number"}, "relation": {"enum": ["point", "lt", "le"]}})


def _unit_schema():
    return obj({"witness": _enriched_witness_schema(),
        "raw_unit": {"type": "string", "minLength": 1},
        "canonical_unit": {"enum": ["pmol/min/mg", "per_min", "uM/min"]},
        "multiplier": {"type": "number", "exclusiveMinimum": 0}})


def _arm_schema(*, enriched, defined_units=True):
    witness = _enriched_witness_schema() if enriched else _witness_schema()
    number = _parsed_number_schema() if enriched else number_selector_schema()
    factor_level = {"anyOf": [
        obj({"kind": {"const": "literal"}, "witness": deepcopy(witness)}),
        obj({"kind": {"const": "number"}, "selector": deepcopy(number),
             "unit_witness": _nullable(deepcopy(witness))}),
        {"type": "null"}]}
    unit = _unit_schema() if enriched else deepcopy(witness)
    if defined_units:
        unit = {"anyOf": [unit, parsed_defined_rate_unit_schema() if enriched
                          else defined_rate_unit_schema()]}
    spread = obj({"kind": {"enum": list(SPREAD_KINDS)},
        "magnitude": _nullable(deepcopy(number)),
        "unit": _nullable(deepcopy(unit)),
        "witnesses": {"type": "array", "items": deepcopy(witness)}})
    rate_fields = {"value": deepcopy(number),
        "unit": unit, "spread": spread}
    if enriched:
        rate_fields.update(canonical_value={"type": "number", "minimum": 0},
                           canonical_spread={"type": ["number", "null"], "minimum": 0})
    return obj({**{field: _nullable(deepcopy(witness)) for field in IDENTITY_FIELDS},
        "partner_state": {"enum": ["present", "absent", "unreported"]},
        "conditions": obj({"coverage": {"enum": ["complete", "partial", "unreported"]},
            "factors": {"type": "array", "items": obj({
                "factor": {"type": "string", "pattern": _FACTOR.pattern,
                           "minLength": 1, "maxLength": 128}, "level": factor_level})}}),
        "measurement_identity": _nullable(deepcopy(witness)),
        "origin": {"enum": ["reported", "graph_derived", "synthetic"]},
        "rate": _nullable(obj(rate_fields))})


def partner_source_population_schema():
    """Closed source selectors; only source offsets are numeric arguments."""
    witness = _witness_schema()
    return obj({"source_ref": deepcopy(REF), "data_source_ref": deepcopy(REF),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS}),
        "interpretation_witnesses": {"type": "array", "items": deepcopy(witness)},
        "input_mode": {"const": "native_source_spans"},
        "arms": obj({role: _nullable(_arm_schema(enriched=False)) for role in ROLES})})


def native_evidence_schema(*, defined_units=True):
    """Closed host evidence, distinct from the parent's numerical return form."""
    return obj({role: _nullable(_arm_schema(enriched=True, defined_units=defined_units))
                for role in ROLES})


def _witness(value, sources, field):
    return None if value is None else sources.witness(value, field)


def _identity(field, witness):
    return None if witness is None else identity("partner_native_" + field, witness)


def _conditions(value, sources, field):
    _keys(value, ("coverage", "factors"), field)
    _enum(value["coverage"], ("complete", "partial", "unreported"), field + ".coverage")
    if not isinstance(value["factors"], list):
        _fail("factor_list_required", field + ".factors")
    evidence, factors = [], []
    names = set()
    for index, factor in enumerate(value["factors"]):
        path = f"{field}.factors[{index}]"
        _keys(factor, ("factor", "level"), path)
        name = factor["factor"]
        if not isinstance(name, str) or not _FACTOR.fullmatch(name):
            _fail("condition_factor_identifier_required", path + ".factor")
        if name in names:
            _fail("duplicate_condition_factor", path + ".factor")
        names.add(name)
        level = factor["level"]
        if level is None:
            selected, number, unit = None, None, "unreported"
        elif isinstance(level, dict) and level.get("kind") == "literal":
            _keys(level, ("kind", "witness"), path + ".level")
            literal = sources.witness(level["witness"], path + ".level.witness")
            selected = {"kind": "literal", "witness": literal}
            number, unit = literal["quote"], "source_literal"
        elif isinstance(level, dict) and level.get("kind") == "number":
            _keys(level, ("kind", "selector", "unit_witness"), path + ".level")
            parsed = read_source_number(level["selector"], sources=sources, role="condition")
            literal = _witness(level["unit_witness"], sources, path + ".level.unit_witness")
            selected = {"kind": "number", "selector": parsed, "unit_witness": literal}
            number, unit = parsed["value"], literal["quote"] if literal else "dimensionless"
        else:
            _fail("unsupported_condition_level", path + ".level")
        evidence.append({"factor": name, "level": selected})
        factors.append({"factor": name, "level": number, "unit": unit})
    return ({"coverage": value["coverage"], "factors": evidence},
            {"coverage": value["coverage"], "factors": factors})


def _read_unit(value, sources, endpoint):
    if isinstance(value, dict) and value.get("kind") == "source_defined_rate_unit":
        return read_defined_rate_unit(value, sources=sources, endpoint=endpoint)
    return read_source_rate_unit(value, sources=sources)


def _convert(number, unit):
    return (convert_defined_source_number(number, unit) if "definition" in unit
            else convert_source_number(number, unit))


def _rate(value, sources, field, *, endpoint):
    if value is None:
        return None, {"status": "unreported", "value": None,
                      "spread": {"kind": "unreported", "magnitude": None}}, "unreported"
    _keys(value, ("value", "unit", "spread"), field)
    parsed = read_source_number(value["value"], sources=sources, role="rate")
    unit = _read_unit(value["unit"], sources, endpoint)
    canonical = _convert(parsed, unit)
    if canonical < 0:
        _fail("nonnegative_value_required", field + ".value")
    spread = value["spread"]
    _keys(spread, ("kind", "magnitude", "unit", "witnesses"), field + ".spread")
    _enum(spread["kind"], SPREAD_KINDS, field + ".spread.kind")
    if (spread["kind"] == "unreported") != (spread["magnitude"] is None):
        _fail("spread_kind_magnitude_mismatch", field + ".spread")
    if spread["magnitude"] is None and spread["unit"] is not None:
        _fail("unreported_spread_has_unit", field + ".spread.unit")
    if not isinstance(spread["witnesses"], list):
        _fail("array_required", field + ".spread.witnesses")
    witnesses = [sources.witness(item, f"{field}.spread.witnesses[{i}]")
                 for i, item in enumerate(spread["witnesses"])]
    if spread["kind"] in ("SD", "SEM", "CI") and not witnesses:
        _fail("spread_basis_witness_required", field + ".spread.witnesses")
    magnitude = (None if spread["magnitude"] is None else
                 read_source_number(spread["magnitude"], sources=sources, role="spread"))
    spread_unit = (None if spread["unit"] is None else
                   _read_unit(spread["unit"], sources, endpoint))
    if spread_unit is not None and spread_unit["canonical_unit"] != unit["canonical_unit"]:
        _fail("spread_rate_dimension_mismatch", field + ".spread.unit")
    if magnitude is None:
        canonical_spread = None
    else:
        effective_unit = spread_unit or unit
        # This also rejects an unselected printed U/mg for otherwise plain/v2
        # inputs. Old saved records are validated, never parsed again.
        validate_defined_spread_unit(magnitude, effective_unit, sources=sources)
        canonical_spread = _convert(magnitude, effective_unit)
    evidence = {"value": parsed, "unit": unit,
        "spread": {"kind": spread["kind"], "magnitude": magnitude,
                   "unit": spread_unit, "witnesses": witnesses},
        "canonical_value": canonical, "canonical_spread": canonical_spread}
    measurement = {"status": "observed" if parsed["relation"] == "point" else "upper_bound",
        "value": canonical, "spread": {"kind": spread["kind"], "magnitude": canonical_spread}}
    return evidence, measurement, unit["canonical_unit"]


def _arm(value, sources, field):
    if value is None:
        return None, None
    _keys(value, _ARM_FIELDS, field)
    _enum(value["partner_state"], ("present", "absent", "unreported"), field + ".partner_state")
    _enum(value["origin"], ("reported", "graph_derived", "synthetic"), field + ".origin")
    selected = {name: _witness(value[name], sources, field + "." + name)
                for name in IDENTITY_FIELDS}
    physical = _witness(value["measurement_identity"], sources, field + ".measurement_identity")
    condition_evidence, conditions = _conditions(value["conditions"], sources, field + ".conditions")
    rate_evidence, measurement, unit = _rate(value["rate"], sources, field + ".rate",
                                            endpoint=selected["endpoint"])
    measurement.update(measurement_id=_identity("measurement", physical), origin=value["origin"])
    evidence = {**selected, "partner_state": value["partner_state"], "conditions": condition_evidence,
        "measurement_identity": physical, "origin": value["origin"], "rate": rate_evidence}
    core = {**{name + "_ref": _identity(name, selected[name]) for name in IDENTITY_FIELDS},
        "partner_state": value["partner_state"], "conditions": conditions,
        "unit": unit, "measurement": measurement}
    return evidence, core


def read_partner_native_inputs(arguments, *, read_source):
    """Read native selectors once and populate the unchanged numerical core."""
    _keys(arguments, _ARGS, "arguments")
    for field in ("source_ref", "data_source_ref"):
        _text(arguments[field], field)
    _enum(arguments["source_kind"], SOURCE_KINDS, "source_kind")
    if arguments["input_mode"] != "native_source_spans":
        _fail("unsupported_partner_input_mode", "input_mode")
    _keys(arguments["literals"], LITERAL_FIELDS, "literals")
    _keys(arguments["arms"], ROLES, "arms")
    if not isinstance(arguments["interpretation_witnesses"], list):
        _fail("array_required", "interpretation_witnesses")
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    sources.source(arguments["data_source_ref"], "original")
    literals = {}
    for field in LITERAL_FIELDS:
        selected = _witness(arguments["literals"][field], sources, "literals." + field)
        literals[field] = None if selected is None else {"value": selected["quote"], "witness": selected}
    interpretations = [sources.witness(item, f"interpretation_witnesses[{i}]")
        for i, item in enumerate(arguments["interpretation_witnesses"])]
    evidence, arms = {}, {}
    for role in ROLES:
        evidence[role], arms[role] = _arm(arguments["arms"][role], sources, "arms." + role)
    if arguments["source_kind"] == "synthetic_fixture" and any(
            arm is not None and arm["measurement"]["origin"] != "synthetic" for arm in arms.values()):
        _fail("synthetic_origin_required", "arms")
    if not interpretations and any(arm is not None and arm["conditions"]["coverage"] == "complete"
                                   for arm in arms.values()):
        _fail("interpretation_witness_required", "interpretation_witnesses")
    inputs = {"version": "literature_partner_inputs_v1", "arms": arms}
    calculation = populate_partner_components(inputs)
    defined = any(arm is not None and arm["rate"] is not None and
        ("definition" in arm["rate"]["unit"] or arm["rate"]["spread"]["unit"] is not None
         and "definition" in arm["rate"]["spread"]["unit"]) for arm in evidence.values())
    return {"version": DEFINED_VERSION if defined else VERSION,
        "arguments": deepcopy(arguments), "sources": list(sources.references),
        "literals": literals, "interpretations": interpretations,
        "recipe": {"version": DATA_VERSION, "inputs": inputs}, "calculation": calculation,
        "cells": deepcopy(calculation["cells"]), "native_evidence": evidence}


__all__ = ["VERSION", "DEFINED_VERSION", "DATA_VERSION", "LITERAL_FIELDS", "ROLES", "IDENTITY_FIELDS",
    "SPREAD_KINDS", "SOURCE_KINDS", "COMPONENTS", "partner_source_population_schema",
    "native_evidence_schema", "read_partner_native_inputs"]
