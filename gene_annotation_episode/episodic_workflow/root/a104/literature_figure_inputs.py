"""Populate source-bound native figure cells from retained selection bytes.

Source custody and exact witnesses do not prove supplied scientific meanings.
The native helper measures pixels; biological replication, reported spread and
the comparability of representations remain explicit supplied interpretations.
No acquisition, model call, SQL access or state mutation occurs here.
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
from .literature_figure_measurements import (
    BOUND_KIND, compare_ordinate_cells, read_bar_ordinate,
)


VERSION = "a105_figure_inputs_v1"
DATA_VERSION = "literature_figure_selection_v1"
LITERAL_FIELDS = ("first_subject", "first_partner", "second_subject", "second_partner",
                  "experiment", "endpoint", "first_condition", "second_condition",
                  "normalization", "function")
COMPONENTS = ("first_ordinate", "second_ordinate", "ordinate_difference")
REASONS = ("no_bar_pixels", "ambiguous_bar_runs", "truncated_mean_edge",
           "numerical_model_range", "missing_ordinate", "second_ordinate_unreported",
           "ordinate_unit_mismatch")
ARRANGEMENTS = ("coexisting_sequential_catalysts", "coexisting_complex", "single_molecule", "unresolved")
CONTRAST_KINDS = ("source_representation", "partner_swap", "other", "unreported")
ENDPOINT_SCOPES = ("coupled_final_product", "direct_subject_step", "binding", "indirect_response", "unreported")
NORMALIZATION_BASES = ("reported_relative_turnover", "arbitrary_signal", "concentration", "unreported")
MEASUREMENT_RELATIONS = ("same_physical_measurement", "distinct_physical_measurements", "unresolved")
REPEAT_KINDS = ("biological", "technical", "unknown")
SPREAD_KINDS = ("SD", "SEM", "CI", "unspecified", "unreported")
IMAGE_ORIGINS = ("published", "synthetic")
_ARGS = ("source_ref", "data_source_ref", "source_kind", "literals", "interpretation_witnesses")
_DESIGN_ENUMS = {"arrangement": ARRANGEMENTS, "contrast_kind": CONTRAST_KINDS,
    "endpoint_scope": ENDPOINT_SCOPES, "normalization_basis": NORMALIZATION_BASES,
    "measurement_relation": MEASUREMENT_RELATIONS}


def figure_population_schema():
    """Closed selected arguments; pixels and selections come from retained bytes."""
    witness = _witness_schema()
    return obj({"source_ref": deepcopy(REF), "data_source_ref": deepcopy(REF),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS}),
        "interpretation_witnesses": {"type": "array", "items": deepcopy(witness)}})


def _enum(value, values, field):
    if not isinstance(value, str) or value not in values:
        _fail("unsupported_" + field.rsplit(".", 1)[-1], field)


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
        # Integers are finite even beyond binary-float range. The helper owns
        # numerical_model_range when a valid selection cannot produce floats.
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=constant, parse_float=lambda token: _numeric(token, field))
    except ExperimentalContractError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_figure_selection_source", field) from error


def _repeat(value, field):
    _keys(value, ("reported_n", "repeat_kind", "independent_preparation_count",
                  "spread_kind", "spread_numeric_status"), field)
    for name in ("reported_n", "independent_preparation_count"):
        count = value[name]
        if count is not None and (type(count) is not int or count < 1):
            _fail("positive_integer_count_required", field + "." + name)
    _enum(value["repeat_kind"], REPEAT_KINDS, field + ".repeat_kind")
    _enum(value["spread_kind"], SPREAD_KINDS, field + ".spread_kind")
    expected = "unreported" if value["spread_kind"] == "unreported" else "not_extracted"
    if value["spread_numeric_status"] != expected:
        _fail("spread_numeric_status_mismatch", field + ".spread_numeric_status")


def _image(value, field):
    _keys(value, ("image_source_ref", "image_origin", "axis_scale", "selection"), field)
    _text(value["image_source_ref"], field + ".image_source_ref")
    _enum(value["image_origin"], IMAGE_ORIGINS, field + ".image_origin")
    _enum(value["axis_scale"], ("linear",), field + ".axis_scale")
    # read_bar_ordinate validates the complete closed native selection before
    # decoding/counting. Never reinterpret an unsupported axis or unit.


def _recipe(value):
    _keys(value, ("version", "first", "second", "design"), "data_source")
    if value["version"] != DATA_VERSION:
        _fail("unsupported_figure_selection_version", "data_source.version")
    _image(value["first"], "data_source.first")
    if value["second"] is not None:
        _image(value["second"], "data_source.second")
    design = value["design"]
    _keys(design, (*_DESIGN_ENUMS, "first_repeat", "second_repeat"), "data_source.design")
    for name, values in _DESIGN_ENUMS.items():
        _enum(design[name], values, "data_source.design." + name)
    _repeat(design["first_repeat"], "data_source.design.first_repeat")
    if (value["second"] is None) != (design["second_repeat"] is None):
        _fail("second_repeat_presence_mismatch", "data_source.design.second_repeat")
    if design["second_repeat"] is not None:
        _repeat(design["second_repeat"], "data_source.design.second_repeat")


def _unavailable(origin, reason):
    return {"value": None, "lower": None, "upper": None, "unit": None,
        "origin": origin, "bound_kind": BOUND_KIND, "status": "unavailable",
        "unavailable_reason": reason}


def read_figure_inputs(arguments, *, read_source):
    """Read original paper, recipe, images and exact selected text witnesses.

    ``read_source(ref, representation)`` authorizes received/scoped sources and
    returns ``{artifact_ref, content: bytes}``. Callback failures propagate.
    Graph-derived digitization domains are never reported biological intervals.
    """
    _keys(arguments, _ARGS, "arguments")
    _enum(arguments["source_kind"], SOURCE_KINDS, "source_kind")
    _text(arguments["source_ref"], "source_ref")
    _text(arguments["data_source_ref"], "data_source_ref")
    _keys(arguments["literals"], LITERAL_FIELDS, "literals")
    if not isinstance(arguments["interpretation_witnesses"], list):
        _fail("array_required", "interpretation_witnesses")
    sources = _Sources(read_source)
    # Establish custody without decoding arbitrary original paper bytes.
    sources.source(arguments["source_ref"], "original")
    recipe = _json_recipe(sources.source(arguments["data_source_ref"], "original")["content"])
    _recipe(recipe)
    measurements = {}
    for side in ("first", "second"):
        image = recipe[side]
        measurements[side] = (None if image is None else read_bar_ordinate(
            sources.source(image["image_source_ref"], "original")["content"], image["selection"]))
    literals = {}
    for field in LITERAL_FIELDS:
        value = arguments["literals"][field]
        witness = sources.witness(value, "literals." + field) if value is not None else None
        literals[field] = {"value": witness["quote"], "witness": witness} if witness else None
    interpretations = [sources.witness(value, f"interpretation_witnesses[{i}]")
        for i, value in enumerate(arguments["interpretation_witnesses"])]
    first = measurements["first"]["cell"]
    if measurements["second"] is None:
        second = _unavailable("graph_derived", "second_ordinate_unreported")
        difference = _unavailable("derived", "second_ordinate_unreported")
    else:
        second = measurements["second"]["cell"]
        difference = (_unavailable("derived", "ordinate_unit_mismatch")
            if first["unit"] != second["unit"]
            else compare_ordinate_cells(first, second)["cell"])
    return {"version": VERSION, "arguments": deepcopy(arguments),
        "sources": list(sources.references), "literals": literals,
        "interpretations": interpretations, "recipe": recipe,
        "measurements": measurements, "cells": dict(zip(COMPONENTS,
            deepcopy((first, second, difference))))}


__all__ = ["VERSION", "DATA_VERSION", "LITERAL_FIELDS", "COMPONENTS", "REASONS",
    "SOURCE_KINDS", "ARRANGEMENTS", "CONTRAST_KINDS", "ENDPOINT_SCOPES",
    "NORMALIZATION_BASES", "MEASUREMENT_RELATIONS", "REPEAT_KINDS", "SPREAD_KINDS",
    "IMAGE_ORIGINS", "figure_population_schema", "read_figure_inputs"]
