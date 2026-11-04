"""Read retained experimental partner measurements and exact source witnesses.

Numerical operands and experimental meanings come from retained JSON bytes.
This boundary does not parse arbitrary publisher papers or infer scientific
truth from quote custody. It performs no acquisition, model call or state write.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .domain import REF, obj
from .literature_assay_inputs import (
    SOURCE_KINDS, _Sources, _fail, _keys, _nullable, _numeric, _text,
    _witness_schema,
)
from .literature_experimental_contracts import ExperimentalContractError
from .literature_partner_calculations import COMPONENTS, populate_partner_components


VERSION = "literature_partner_inputs_extraction_v1"
DATA_VERSION = "literature_partner_selection_v1"
LITERAL_FIELDS = ("subject", "partner", "experiment", "endpoint", "normalization",
                  "reference_condition", "omitted_condition", "addback_condition", "function")
_ARGS = ("source_ref", "data_source_ref", "source_kind", "literals", "interpretation_witnesses")


def partner_population_schema(*, include_assessment=False):
    """Closed selected arguments; scientific numbers stay in retained sources."""
    witness = _witness_schema()
    schema = obj({"source_ref": deepcopy(REF), "data_source_ref": deepcopy(REF),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({name: _nullable(deepcopy(witness)) for name in LITERAL_FIELDS}),
        "interpretation_witnesses": {"type": "array", "items": deepcopy(witness)}})
    if include_assessment:
        from .literature_experiment_assessments import assessment_schema
        from .literature_partner_types import EXPERIMENT_TYPES
        schema["properties"]["experiment_assessment"] = assessment_schema(EXPERIMENT_TYPES)
    return schema


def _json_recipe(raw):
    field = "data_source_ref"

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("duplicate_json_key", field)
            result[key] = value
        return result

    def constant(_token):
        _fail("finite_number_required", field)

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=constant, parse_float=lambda token: _numeric(token, field))
    except ExperimentalContractError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_partner_selection_source", field) from error


def read_partner_inputs(arguments, *, read_source):
    """Populate the finite partner sheet from retained bytes and source witnesses.

    ``read_source(reference, representation)`` authorizes scoped received sources
    and returns exactly ``{artifact_ref, content: bytes}``. Its failures propagate.
    The callback's records establish custody, not experimental comparability.
    """
    if isinstance(arguments, dict) and "input_mode" in arguments:
        from .literature_partner_native_inputs import read_partner_native_inputs
        return read_partner_native_inputs(arguments, read_source=read_source)
    extra = ("experiment_assessment",) if "experiment_assessment" in arguments else ()
    _keys(arguments, (*_ARGS, *extra), "arguments")
    if extra:
        from .literature_experiment_assessments import validate_assessment
        from .literature_partner_types import EXPERIMENT_TYPES
        validate_assessment(arguments["experiment_assessment"], EXPERIMENT_TYPES)
    _text(arguments["source_ref"], "source_ref")
    _text(arguments["data_source_ref"], "data_source_ref")
    if not isinstance(arguments["source_kind"], str) or arguments["source_kind"] not in SOURCE_KINDS:
        _fail("unsupported_source_kind", "source_kind")
    _keys(arguments["literals"], LITERAL_FIELDS, "literals")
    if not isinstance(arguments["interpretation_witnesses"], list):
        _fail("array_required", "interpretation_witnesses")

    sources = _Sources(read_source)
    # Original custody need not decode a binary paper or supplied dataset.
    sources.source(arguments["source_ref"], "original")
    recipe = _json_recipe(sources.source(arguments["data_source_ref"], "original")["content"])
    _keys(recipe, ("version", "inputs"), "data_source")
    if recipe["version"] != DATA_VERSION:
        _fail("unsupported_partner_selection_version", "data_source.version")

    # The pure calculator owns the complete scientific input shape and numeric
    # relationships. Delegating once also prevents a second partial validator
    # from erasing its specific repairable failures.
    calculation = populate_partner_components(recipe["inputs"])
    arms = recipe["inputs"]["arms"]
    if arguments["source_kind"] == "synthetic_fixture":
        for role, arm in arms.items():
            if arm is not None and arm["measurement"]["origin"] != "synthetic":
                _fail("synthetic_origin_required", "data_source.inputs.arms." + role + ".measurement.origin")

    literals = {}
    for field in LITERAL_FIELDS:
        selected = arguments["literals"][field]
        witness = sources.witness(selected, "literals." + field) if selected is not None else None
        literals[field] = {"value": witness["quote"], "witness": witness} if witness else None
    interpretations = [sources.witness(value, f"interpretation_witnesses[{i}]")
        for i, value in enumerate(arguments["interpretation_witnesses"])]
    if not interpretations and any(arm is not None and arm["conditions"]["coverage"] == "complete"
                                   for arm in arms.values()):
        _fail("interpretation_witness_required", "interpretation_witnesses")

    return {"version": VERSION, "arguments": deepcopy(arguments),
        "sources": list(sources.references), "literals": literals,
        "interpretations": interpretations, "recipe": recipe,
        "calculation": calculation, "cells": deepcopy(calculation["cells"])}


__all__ = ["VERSION", "DATA_VERSION", "LITERAL_FIELDS", "COMPONENTS", "SOURCE_KINDS",
           "partner_population_schema", "read_partner_inputs"]
