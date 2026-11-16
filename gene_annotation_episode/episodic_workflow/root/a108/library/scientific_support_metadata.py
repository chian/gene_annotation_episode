"""Instruction validation and explicit scoring-route availability.

Instruction metadata neither supplies evidence nor chooses a projector. No field
mapping is inferred from an arbitrary numeric scorer or tool-output category.
"""
from __future__ import annotations
from typing import Literal, TypedDict
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a108.domain import OBSERVATION_KINDS
ROUTES_VERSION = 'scientific_support_routes_v1'

class AnnotationSupportRouteV1(TypedDict):
    observation_kind: str
    status: Literal['mapped', 'unmapped', 'unavailable']
    axis: str | None

class AnnotationSupportRoutesV1(TypedDict):
    version: Literal['scientific_support_routes_v1']
    status: Literal['available', 'unavailable']
    reason: Literal['annotation_score_unbound', 'unsupported_projector', 'binding_definition_missing', 'binding_definition_mismatch'] | None
    annotation_binding_sha256: str | None
    projection_version: str | None
    formula_version: str | None
    integration_arithmetic: str | None
    policy: dict | None
    routes: list[AnnotationSupportRouteV1]

_KINDS_VALIDATOR = Draft202012Validator({'type': 'array', 'uniqueItems': True, 'items': {'enum': OBSERVATION_KINDS}})

def support_observation_kinds(entry) -> list[str]:
    """Return precisely the selected body's declared existing observation kinds."""
    from gene_annotation_episode.episodic_workflow.root.a108.library.evidence_axis_contracts import VERSION, observation_kinds
    if entry.get('entry_version') != VERSION:
        raise ValueError('scientific_support_entry_invalid')
    return observation_kinds(entry)

def _unavailable(reason, kinds) -> AnnotationSupportRoutesV1:
    return {'version': ROUTES_VERSION, 'status': 'unavailable', 'reason': reason, 'annotation_binding_sha256': None, 'projection_version': None, 'formula_version': None, 'integration_arithmetic': None, 'policy': None, 'routes': [{'observation_kind': kind, 'status': 'unavailable', 'axis': None} for kind in kinds]}

def annotation_policy_routes(projector, annotation_score_binding, *, observation_kinds) -> AnnotationSupportRoutesV1:
    """Never infer numerical evidence axes from a type of tool output.

    The categorical observation-kind dispatch was retired. A caller's arbitrary
    numerical projector is not enough to declare its field bindings; an explicit
    numerical sheet interface is still required. This metadata read does not
    execute a scorer or change continuation.
    """
    try:
        valid_kinds = _KINDS_VALIDATOR.is_valid(observation_kinds)
    except (TypeError, ValueError, RecursionError):
        valid_kinds = False
    if not valid_kinds:
        raise ValueError('scientific_support_observation_kinds_invalid')
    return _unavailable('annotation_score_unbound' if projector is None else 'unsupported_projector', sorted(observation_kinds))
__all__ = ['AnnotationSupportRoutesV1', 'ROUTES_VERSION', 'support_observation_kinds', 'annotation_policy_routes']
