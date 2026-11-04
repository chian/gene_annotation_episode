"""Scientific-support instructions and read-only declarations of an actual policy.

Instruction metadata neither supplies target evidence nor chooses a projector.
Only the concrete annotation-support executable's matching recorded definition
can declare routes; formatting this view never projects state or invokes work.
"""
from __future__ import annotations

import json
import re
from typing import Literal, TypedDict

from jsonschema import Draft202012Validator
from method_loop.durable import canonical, content_digest

from .credit import CreditPolicy
from .domain import (FINDING_QUALIFICATIONS, IDENTIFIER, OBSERVATION_KINDS,
                     PREDICATES, RECORD_SCHEMAS)
from .scientific_credit import AnnotationSupportScore


SUPPORT_ENTRY_VERSION = "scientific_support_entry_v1"
ROUTES_VERSION = "scientific_support_routes_v1"


class InstructionSourceRow(TypedDict):
    case_group: str
    case_id: str
    source_url: str
    source_locator: str
    observation: str
    limit: str


class SupportOperandV1(TypedDict):
    operand_id: str
    observation_kinds: list[str]
    hypothesis_predicates: list[str]
    assessment_relations: list[str]
    applicabilities: list[str]
    extent_bases: list[str]
    finding_qualifications: list[str]
    instruction: str


class SupportMetadataV1(TypedDict):
    proposition: str
    operands: list[SupportOperandV1]
    qualifications: list[str]
    boundary: str


class SupportEntryV1(TypedDict):
    entry_version: Literal["scientific_support_entry_v1"]
    id: str
    slot: Literal["annotation_distinction"]
    name: str
    description: str
    support: SupportMetadataV1
    evidence: list[InstructionSourceRow]


class AnnotationSupportRouteV1(TypedDict):
    observation_kind: str
    status: Literal["mapped", "unmapped", "unavailable"]
    axis: Literal["empirical", "comparative", "mechanistic", "biological_context"] | None


class AnnotationSupportRoutesV1(TypedDict):
    version: Literal["scientific_support_routes_v1"]
    status: Literal["available", "unavailable"]
    reason: Literal["annotation_score_unbound", "unsupported_projector",
                    "binding_definition_missing", "binding_definition_mismatch"] | None
    annotation_binding_sha256: str | None
    projection_version: str | None
    formula_version: str | None
    integration_arithmetic: str | None
    policy: dict | None
    routes: list[AnnotationSupportRouteV1]


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _list(items):
    return {"type": "array", "items": items, "minItems": 1, "uniqueItems": True}


_TEXT = {"type": "string", "pattern": r"\S"}
_ASSESSMENT = RECORD_SCHEMAS["assessment"]["properties"]
_OPERAND_SCHEMA = _object({
    "operand_id": IDENTIFIER,
    "observation_kinds": _list({"enum": OBSERVATION_KINDS}),
    "hypothesis_predicates": _list({"enum": PREDICATES}),
    "assessment_relations": _list(_ASSESSMENT["relation"]),
    "applicabilities": _list(_ASSESSMENT["applicability"]),
    "extent_bases": _list({"enum": _ASSESSMENT["extent_basis"]["enum"]}),
    "finding_qualifications": _list({"enum": FINDING_QUALIFICATIONS}),
    "instruction": _TEXT,
})
_ENTRY_SCHEMA = _object({
    "entry_version": {"const": SUPPORT_ENTRY_VERSION},
    "id": {"type": "string", "pattern": r"^A[0-9]+$"},
    "slot": {"const": "annotation_distinction"},
    "name": _TEXT,
    "description": _TEXT,
    "support": _object({
        "proposition": _TEXT,
        "operands": _list(_OPERAND_SCHEMA),
        "qualifications": _list(_TEXT),
        "boundary": _TEXT,
    }),
    "evidence": _list(_object({key: _TEXT for key in
        "case_group case_id source_url source_locator observation limit".split()})),
})
_ENTRY_VALIDATOR = Draft202012Validator(_ENTRY_SCHEMA)
_KINDS_VALIDATOR = Draft202012Validator({"type": "array", "uniqueItems": True,
    "items": {"enum": OBSERVATION_KINDS}})
_BINDING_FIELDS = {"projector", "versions", "definition", "scope_source", "meaning"}
_CASE_FIELDS = {"policy_source_sha256", "policy_parameters_sha256", "definition"}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def validate_support_entry(value) -> SupportEntryV1:
    """Validate a closed, reference-free instruction body and detach its JSON."""
    code = "scientific_support_entry_invalid"
    try:
        if not _ENTRY_VALIDATOR.is_valid(value):
            raise ValueError(code)
        if re.fullmatch(r"A[0-9]+", value["id"]) is None:
            raise ValueError(code)
        operands = value["support"]["operands"]
        if len({operand["operand_id"] for operand in operands}) != len(operands):
            raise ValueError(code)
        if any(re.fullmatch(IDENTIFIER["pattern"], operand["operand_id"]) is None
               for operand in operands):
            raise ValueError(code)
        return json.loads(canonical(value))
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError(code) from error


def support_observation_kinds(entry) -> list[str]:
    """Return precisely the selected body's declared existing observation kinds."""
    body = validate_support_entry(entry)
    return sorted({kind for operand in body["support"]["operands"]
                   for kind in operand["observation_kinds"]})


def _unavailable(reason, kinds) -> AnnotationSupportRoutesV1:
    return {"version": ROUTES_VERSION, "status": "unavailable", "reason": reason,
        "annotation_binding_sha256": None, "projection_version": None,
        "formula_version": None, "integration_arithmetic": None, "policy": None,
        "routes": [{"observation_kind": kind, "status": "unavailable", "axis": None}
                   for kind in kinds]}


def annotation_policy_routes(projector, annotation_score_binding, *,
                             observation_kinds) -> AnnotationSupportRoutesV1:
    """Describe actual kind dispatch without calling a projector or controller.

    Recognize only the host's current outer envelope and its direct or fixed-case
    definition. No custom callable, arbitrary wrapper or progress score acquires
    annotation-policy semantics through a name, attribute or JSON resemblance.
    """
    try:
        valid_kinds = _KINDS_VALIDATOR.is_valid(observation_kinds)
    except (TypeError, ValueError, RecursionError):
        valid_kinds = False
    if not valid_kinds:
        raise ValueError("scientific_support_observation_kinds_invalid")
    kinds = sorted(observation_kinds)
    if projector is None:
        return _unavailable("annotation_score_unbound", kinds)
    if type(projector) is not AnnotationSupportScore or type(projector.policy) is not CreditPolicy:
        return _unavailable("unsupported_projector", kinds)
    if (not isinstance(annotation_score_binding, dict)
            or annotation_score_binding.get("definition") is None):
        return _unavailable("binding_definition_missing", kinds)
    try:
        # Finite JSON/string-key validation precedes comparison and hashing.
        binding = json.loads(canonical(annotation_score_binding))
        if (set(binding) != _BINDING_FIELDS
                or binding["projector"] != (AnnotationSupportScore.__module__ + "." +
                                            AnnotationSupportScore.__qualname__)
                or binding["versions"] != {"requirement": "same_caller_injected_executable"}
                or binding["scope_source"] != "context.scope"
                or not isinstance(binding["meaning"], str) or not binding["meaning"].strip()):
            return _unavailable("binding_definition_mismatch", kinds)
        definition = binding["definition"]
        if isinstance(definition, dict) and set(definition) == _CASE_FIELDS:
            if any(not isinstance(definition[key], str) or
                   _SHA256.fullmatch(definition[key]) is None for key in
                   ("policy_source_sha256", "policy_parameters_sha256")):
                return _unavailable("binding_definition_mismatch", kinds)
            definition = definition["definition"]
        actual = projector.as_record()
        if canonical(definition) != canonical(actual):
            return _unavailable("binding_definition_mismatch", kinds)
        policy = actual["policy"]
        axes = dict(policy["observation_axes"])
        return {"version": ROUTES_VERSION, "status": "available", "reason": None,
            "annotation_binding_sha256": content_digest(binding),
            "projection_version": actual["projection_version"],
            "formula_version": actual["formula_version"],
            "integration_arithmetic": actual["integration_arithmetic"], "policy": policy,
            "routes": [{"observation_kind": kind,
                "status": "mapped" if kind in axes else "unmapped", "axis": axes.get(kind)}
                for kind in kinds]}
    except (ValueError, TypeError, OverflowError, RecursionError):
        return _unavailable("binding_definition_mismatch", kinds)


__all__ = ["SupportEntryV1", "SupportMetadataV1", "SupportOperandV1",
    "AnnotationSupportRoutesV1", "SUPPORT_ENTRY_VERSION", "ROUTES_VERSION",
    "validate_support_entry", "support_observation_kinds", "annotation_policy_routes"]
