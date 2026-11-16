"""Closed process-result facts copied from an episode's existing closure.

These helpers have no host, evidence store or numerical policy. They preserve
the original assignment and already projected local quantities; formatting and
forwarding a result supplies neither new credit nor an observation.
"""
from __future__ import annotations

from collections.abc import Mapping
import re

from jsonschema import Draft202012Validator
from .library.record_values import finite_canonical as canonical

CODE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:+/\-]{0,127}$")
from .library.record_values import identity
from .received_episode_yield import report_sources as episode_report_sources
from .scientific_process_records import (OPTION_REF_VERSION, SELECTION_VERSION,
    SLOTS, canonical_slot, _exact, _plain, scientific_invocation_ref, validate_invocation_ref,
    validate_option_ref, validate_revision_origin, validate_selection, selection_fields)
from .tool_reference_records import RESOURCE_KINDS


VERSION = "scientific_process_result_v1"
RETURN_VERSION = "scientific_process_result_v3"
SELECTION_REPORT_VERSION = "scientific_process_selection_report_v1"
SOURCE = "scientific_process_results"
_CREDIT_KINDS = ("scientific", "monitoring", "operational")
_REFERENCE = re.compile(r"scientific_credit_binding_[0-9a-f]{24}\Z")
_PREPARATION = re.compile(r"operation_[0-9a-f]{24}\Z")
_FIELDS = ("version invocation_ref parent_invocation_ref origin_kind "
    "preparation_operation_ref selection initial_credit credit credit_kind "
    "credit_binding_ref completed_actions episode_yield")


def _object(fields):
    return {"type": "object", "properties": fields, "required": list(fields),
        "additionalProperties": False}


def _reference(namespace, *, nullable=False, identifier=False):
    return {"type": ["string", "null"] if nullable else "string",
        "format": "identifier" if identifier else "reference",
        "x-reference-namespace": namespace}


def _yield_schema():
    # x-source binds only whole top-level fields. The numerical schema itself
    # stays identical to the existing episode_yield source.
    schema = episode_report_sources()["episode_yield"]["report_schema"]
    schema.pop("x-source")
    return schema


def _semantic_ref(value, pattern, code):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(code)


def _validate_report_selection(value, *, library=None, tool_library=None):
    """Read the compact return, which is never a child construction selection."""
    code = "scientific_process_selection_report_invalid"
    _exact(value, "version source_version evidence_axis thought_pattern child_tool_info", code)
    if (value["version"] != SELECTION_REPORT_VERSION
            or value["source_version"] != SELECTION_VERSION):
        raise ValueError(code)
    refs = [validate_option_ref(value[name]) for name in SLOTS]
    if (tuple(canonical_slot(ref["slot"]) for ref in refs) != SLOTS
            or len({ref["library_id"] for ref in refs}) != 1):
        raise ValueError(code)
    if library is not None:
        for ref in refs:
            library.resolve(ref)
    choices = value["child_tool_info"]
    if not isinstance(choices, list):
        raise ValueError(code)
    seen = set()
    for choice in choices:
        _exact(choice, "name resources", code)
        name, resource = choice["name"], choice["resources"]
        if (not isinstance(name, str) or CODE.fullmatch(name) is None
                or resource not in RESOURCE_KINDS):
            raise ValueError(code)
        key = name, resource
        if key in seen:
            raise ValueError(code)
        seen.add(key)
    if tool_library is not None:
        tool_library.resolve_tool_info(choices)
    return value


def validate_process_result(value, *, library=None, tool_library=None):
    """Detach and validate one result, optionally resolving its pinned bodies."""
    value = _plain(value)
    code = "scientific_process_result_invalid"
    _exact(value, _FIELDS + (' proposed_annotation_ref' if 'proposed_annotation_ref' in value
        or value.get('version') == RETURN_VERSION else ''), code)
    if value.get('proposed_annotation_ref') is not None:
        _semantic_ref(value['proposed_annotation_ref'], re.compile(r'hypothesis_[0-9a-f]{24,64}\Z'),
            'scientific_process_result_proposed_annotation_invalid')
    if value["version"] not in (VERSION, RETURN_VERSION):
        raise ValueError("scientific_process_result_version_invalid")
    validate_invocation_ref(value["invocation_ref"])
    parent = value["parent_invocation_ref"]
    if parent is not None:
        validate_invocation_ref(parent)
        if parent == value["invocation_ref"]:
            raise ValueError("scientific_process_result_parent_invalid")
    origin, preparation = value["origin_kind"], value["preparation_operation_ref"]
    if origin == "ordinary_child":
        if preparation is not None:
            raise ValueError("scientific_process_result_origin_invalid")
    elif origin == "approach_revision":
        if parent is None:
            raise ValueError("scientific_process_result_origin_invalid")
        _semantic_ref(preparation, _PREPARATION, "scientific_process_result_origin_invalid")
    else:
        raise ValueError("scientific_process_result_origin_invalid")
    if value["version"] == VERSION:
        selection = validate_selection(value["selection"])
        axis_field, thought_field, tools_field = selection_fields(selection)
        if library is not None:
            for name in (axis_field, thought_field):
                library.resolve(selection[name])
        if tool_library is not None:
            tool_library.resolve_tool_info(selection[tools_field])
        value["selection"] = selection
    else:
        value["selection"] = _validate_report_selection(value["selection"],
            library=library, tool_library=tool_library)
    for name in ("initial_credit", "credit"):
        if type(value[name]) not in (int, float):
            raise ValueError(code)
    kind, binding = value["credit_kind"], value["credit_binding_ref"]
    if kind is None:
        if binding is not None:
            raise ValueError("scientific_process_result_binding_invalid")
    else:
        if kind not in _CREDIT_KINDS:
            raise ValueError("scientific_process_result_binding_invalid")
        _semantic_ref(binding, _REFERENCE, "scientific_process_result_binding_invalid")
    count = value["completed_actions"]
    if type(count) is not int or count < 0:
        raise ValueError(code)
    episode_yield = value["episode_yield"]
    errors = list(Draft202012Validator(_yield_schema()).iter_errors(episode_yield))
    if errors:
        raise ValueError("scientific_process_result_yield_invalid") from errors[0]
    if episode_yield is not None and (type(episode_yield["completed_actions"]) is not int
            or episode_yield["completed_actions"] != count):
        raise ValueError("scientific_process_result_yield_count_mismatch")
    return value


def credit_binding_ref(metadata):
    """Identify the actual finite metadata without exposing its definition."""
    if metadata is None:
        return None
    value = _plain(metadata)
    if not isinstance(value, dict) or not value:
        raise ValueError("scientific_process_credit_metadata_invalid")
    return identity("scientific_credit_binding", value)

