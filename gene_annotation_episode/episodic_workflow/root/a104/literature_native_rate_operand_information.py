"""Explain the existing native rate selectors without changing their contract.

This module adds descriptions to a fresh copy of the frozen reader's schema.
It acquires no source, nominates no argument, interprets no experiment and
performs no parsing, numerical calculation, dispatch or observation accounting.
"""
from __future__ import annotations

from copy import deepcopy

from .literature_rate_native_inputs import rate_source_population_schema


_WITNESS = (
    "Exact source span: start/end are half-open UTF-8 byte positions; "
    "quote preserves decoded bytes, markup and whitespace."
)
_NUMBER = (
    "Select a complete printed numeric token within the exact quote; "
    "inner offsets count Unicode characters, not UTF-8 bytes."
)
_DEFINITION_GRAMMAR = (
    "Select the complete supported source definition, including all alternative "
    "endpoint branches. The finite reader supports the opening 'one unit was "
    "defined as' or 'one unit was equivalent to' (case-insensitive), optionally "
    "followed by 'the oxidation of', 'oxidation of', 'the reduction of', "
    "'reduction of', 'the formation of' or 'formation of'. Each branch has a "
    "positive literal amount, pmol/nmol/umol (including micro-symbol spellings), "
    "an optional 'of', the entity, an optional oxidized/reduced/formed, and "
    "'per' min/minute/s/second. Branches are separated by a comma, 'or', or "
    "comma followed by 'or'. Preserve actual source wording; unsupported "
    "wording is a reader limitation and must never be rewritten to fit."
)


def _witness(node, meaning=None):
    node["description"] = _WITNESS if meaning is None else meaning + " " + _WITNESS


def _number(node, meaning=None):
    node["description"] = _NUMBER if meaning is None else meaning + " " + _NUMBER
    fields = node["properties"]
    _witness(fields["witness"])
    fields["number_start"]["description"] = (
        "Zero-based inclusive Unicode character position inside witness.quote."
    )
    fields["number_end"]["description"] = (
        "Exclusive Unicode character position inside witness.quote."
    )


def _interpreted(node):
    _witness(node["properties"]["witnesses"]["items"])


def _unit(node, endpoint_path):
    plain, defined, _null = node["anyOf"]
    _witness(plain, "Select the complete printed rate-unit token.")
    defined["description"] = (
        "Endpoint-specific source definition for the selected U/mg token. "
        "There is no universal U conversion. A plain U/mg witness without a "
        "definition retains raw inputs but leaves the canonical rate unavailable."
    )
    fields = defined["properties"]
    _witness(fields["witness"], "Select the full printed U/mg token.")
    definition = fields["definition"]
    definition["description"] = (
        "Keep the source-bound quantity, entity and time basis associated with "
        "the selected arm endpoint. Equal numbers or entity labels do not "
        "establish that association."
    )
    parts = definition["properties"]
    _witness(parts["bridge"], (
        "The complete supported unit-definition statement, including all "
        "alternative endpoint branches and their quantity/time bases. "
        "Do not clip a continuation or rewrite source wording."
    ))
    _witness(parts["clause"], (
        "One complete amount–amount-unit–entity–per-time branch contained in "
        "the bridge. Its amount token, amount unit, definition entity and time "
        "unit must occur within this clause in that actual source order."
    ))
    _number(parts["amount"], (
        "The positive definition amount. Its witness must be contained in the "
        "bridge and its physical numeric token must be contained in the clause."
    ))
    _witness(parts["amount_unit"], (
        "The clause's complete pmol, nmol or umol amount unit (including "
        "micro-symbol spellings), at its actual position in that clause."
    ))
    _witness(parts["time_unit"], (
        "The clause's complete time token: min, minute, s or second, at its "
        "actual position in that clause."
    ))
    _witness(parts["endpoint"], (
        "Copy the exact same witness selected at " + endpoint_path + ": source, "
        "representation, start, end and quote must all agree. Naming the same "
        "entity in a different source occurrence or narrower span is insufficient."
    ))
    _witness(parts["endpoint_entity"], (
        "The complete literal molecular entity contained in the selected "
        "endpoint witness. Use this endpoint occurrence, not an equal string "
        "elsewhere in the source."
    ))
    _witness(parts["definition_entity"], (
        "The complete literal molecular entity contained in the selected "
        "definition clause. Its normalized name must match endpoint_entity; "
        "the reader does not infer chemical aliases or a coupled product."
    ))


def rate_source_population_schema_with_information():
    """Return the existing closed schema with operand descriptions only."""
    schema = deepcopy(rate_source_population_schema())
    schema["description"] = (
        "Witness offsets use zero-based half-open source UTF-8 bytes; inner "
        "numeric selectors use Unicode characters within quote. Exact bytes "
        "verify custody, not experimental meaning. " + _DEFINITION_GRAMMAR
    )
    fields = schema["properties"]
    _witness(fields["experiment"]["anyOf"][0])
    for role in ("reference", "test"):
        arm = fields["arms"]["properties"][role]["anyOf"][0]["properties"]
        for meaning in ("subject", "construct", "preparation", "experiment", "label",
                        "condition", "endpoint", "normalization", "measurement_identity"):
            _witness(arm[meaning]["anyOf"][0])
        rate = arm["rate"]["anyOf"][0]["properties"]
        _number(rate["number"])
        endpoint_path = "arguments.arms." + role + ".endpoint"
        _unit(rate["unit"], endpoint_path)
        uncertainty = arm["uncertainty"]["properties"]
        _number(uncertainty["magnitude"]["anyOf"][0])
        _number(uncertainty["count"]["anyOf"][0])
        _unit(uncertainty["unit"], endpoint_path)
        _witness(uncertainty["kind_witnesses"]["items"])
        _interpreted(uncertainty["sampling_basis"])
    comparison = fields["comparison"]["properties"]
    for relationship in ("subject_relation", "endpoint_relation", "normalization_relation"):
        _interpreted(comparison[relationship])
    _witness(comparison["intended_change"]["anyOf"][0])
    _interpreted(fields["dependence"])
    _interpreted(fields["observation_model"])
    return schema


__all__ = ["rate_source_population_schema_with_information"]
