"""Operand information for the existing native partner source contract.

Only description keywords are added to a detached schema. No source selection,
scientific interpretation, parsing, arithmetic or episode behavior occurs here.
"""
from __future__ import annotations

from copy import deepcopy

from .literature_native_rate_operand_information import (
    _DEFINITION_GRAMMAR, _number, _witness,
)
from .literature_partner_native_inputs import partner_source_population_schema


def _unit(node, endpoint_path):
    plain, defined = node["anyOf"]
    _witness(plain, (
        "Select the complete supported printed rate-unit token. A bare U/mg "
        "witness is rejected by this partner reader; use the source-defined "
        "unit form only when its actual supported source definition is available."
    ))
    defined["description"] = (
        "Endpoint-specific source definition for the selected U/mg token. "
        "There is no universal U conversion. Unsupported wording is a reader "
        "capability limit, not evidence that an experiment is absent."
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
        "the bridge. Its positive amount token, amount unit, definition entity "
        "and time unit must occur within this clause in that actual source order."
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


def partner_source_population_schema_with_information():
    """Return the unchanged closed partner schema with descriptions only."""
    schema = deepcopy(partner_source_population_schema())
    schema["description"] = (
        "Witness offsets use zero-based half-open source UTF-8 bytes; inner "
        "numeric selectors use Unicode characters within quote. Exact bytes "
        "verify custody, not experimental meaning. " + _DEFINITION_GRAMMAR
    )
    fields = schema["properties"]
    for name, node in fields["literals"]["properties"].items():
        _witness(node["anyOf"][0], "Source literal for " + name + ".")
    _witness(fields["interpretation_witnesses"]["items"], (
        "Source support for the supplied experimental interpretation, including "
        "any claim of complete condition coverage."
    ))
    for role in ("reference", "omitted", "addback"):
        arm = fields["arms"]["properties"][role]["anyOf"][0]["properties"]
        for name in ("subject", "partner", "endpoint", "normalization", "measurement_identity"):
            _witness(arm[name]["anyOf"][0], role + " arm's source-bound " + name + ".")
        level = arm["conditions"]["properties"]["factors"]["items"]["properties"]["level"]
        literal, numeric, _null = level["anyOf"]
        _witness(literal["properties"]["witness"], "The actual literal condition level.")
        _number(numeric["properties"]["selector"], "The actual numeric condition level.")
        _witness(numeric["properties"]["unit_witness"]["anyOf"][0], (
            "The selected numeric condition's printed unit; null retains the "
            "existing dimensionless interpretation."
        ))
        rate = arm["rate"]["anyOf"][0]["properties"]
        _number(rate["value"], "The arm's reported rate or supported upper-limit token.")
        endpoint_path = "arguments.arms." + role + ".endpoint"
        _unit(rate["unit"], endpoint_path)
        spread = rate["spread"]["properties"]
        _number(spread["magnitude"]["anyOf"][0], "The reported absolute spread magnitude.")
        _unit(spread["unit"]["anyOf"][0], endpoint_path)
        spread["unit"]["description"] = (
            "Select the spread's own printed unit when supplied. Null retains "
            "the selected common rate-unit association; any explicit printed "
            "spread unit is still validated, including its conversion scale."
        )
        _witness(spread["witnesses"]["items"], (
            "Source support for the reported spread meaning; SD, SEM and CI "
            "require a basis witness and remain distinct."
        ))
    return schema


__all__ = ["partner_source_population_schema_with_information"]
