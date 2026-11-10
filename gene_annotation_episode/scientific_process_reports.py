"""Closed process-result facts copied from an episode's existing closure.

These helpers have no host, evidence store or numerical policy. They preserve
the original assignment and already projected local quantities; formatting and
forwarding a result supplies neither new credit nor an observation.
"""
from __future__ import annotations

from collections.abc import Mapping
import re

from jsonschema import Draft202012Validator
from method_loop.durable import canonical
from method_loop.episode import EpisodeCompletion

from .communication import CODE
from .domain import identity
from .episode_reports import report_sources as episode_report_sources
from .scientific_process_records import (OPTION_REF_VERSION, SELECTION_VERSION, LEGACY_SELECTION_VERSION,
    SLOTS, canonical_slot, _exact, _plain, scientific_invocation_ref, validate_invocation_ref,
    validate_option_ref, validate_revision_origin, validate_selection, selection_fields)
from .tool_information import RESOURCE_KINDS


VERSION = "scientific_process_result_v1"
LEGACY_RETURN_VERSION = "scientific_process_result_v2"
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


def _selection_schema(library, tool_library):
    by_slot = {slot: [] for slot in SLOTS}
    for header in library.headers():
        ref = validate_option_ref(header["option_ref"])
        by_slot[canonical_slot(ref["slot"])].append(ref)
    if any(not refs or len(refs) != len({ref["option_id"] for ref in refs})
            for refs in by_slot.values()):
        raise ValueError("scientific_process_result_library_invalid")
    fields = {
        "version": {"type": "string", "const": SELECTION_REPORT_VERSION},
        "source_version": {"type": "string", "enum": [LEGACY_SELECTION_VERSION, SELECTION_VERSION]},
    }
    for slot, refs in by_slot.items():
        fields[slot] = _object({
            "version": {"type": "string", "const": OPTION_REF_VERSION},
            "library_id": _reference("scientific_process_library", identifier=True),
            "slot": {"type": "string", "enum": sorted({ref["slot"] for ref in refs})},
            "option_id": {"type": "string", "enum": sorted(ref["option_id"] for ref in refs)},
            "entry_sha256": _reference("scientific_option_digest", identifier=True),
        })
    information = tool_library.parent_tool_info() if tool_library.supports_tool_info else []
    names = sorted({entry["name"] for entry in [*tool_library.catalog(), *information]})
    resources = sorted({entry["resources"] for entry in information})
    fields["child_tool_info"] = {"type": "array", "items": _object({
        "name": {"type": "string", "enum": names},
        "resources": {"type": ["string", "null"], "enum": [*resources, None]},
    }), "uniqueItems": True} if names else {"type": "array", "maxItems": 0,
        "items": {"type": "null"}}
    return _object(fields)


def report_sources(library, tool_library):
    """Supply a closed array schema using this pinned library's option IDs."""
    schema = {"type": "array", "items": _object({
        "version": {"type": "string", "const": RETURN_VERSION},
        "invocation_ref": _reference("scientific_invocation"),
        "parent_invocation_ref": _reference("scientific_invocation", nullable=True),
        "origin_kind": {"type": "string", "enum": ["ordinary_child", "approach_revision"]},
        "preparation_operation_ref": _reference("scientific_preparation", nullable=True),
        "selection": _selection_schema(library, tool_library),
        "initial_credit": {"type": "number"},
        "credit": {"type": "number"},
        "credit_kind": {"type": ["string", "null"], "enum": [*_CREDIT_KINDS, None]},
        "credit_binding_ref": _reference("scientific_credit_binding", nullable=True),
        "completed_actions": {"type": "integer", "minimum": 0},
        "episode_yield": _yield_schema(),
    }), "x-source": SOURCE}
    schema['items']['properties']['proposed_annotation_ref'] = _reference('hypothesis', nullable=True)
    schema['items']['required'].append('proposed_annotation_ref')
    return {SOURCE: {"type": "array", "meaning": (
        "Recorded original process selection, explicit revision origin and existing closing "
        "local credit/yield for each invocation actually returned through requested forms. "
        "Initial and closing credit retain that episode's own units and binding; forwarding "
        "these facts creates no new score, credit or completed action."),
        "report_schema": schema}}


def _semantic_ref(value, pattern, code):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(code)


def _validate_report_selection(value, *, library=None, tool_library=None):
    """Read the compact return, which is never a child construction selection."""
    code = "scientific_process_selection_report_invalid"
    _exact(value, "version source_version evidence_axis thought_pattern child_tool_info", code)
    if (value["version"] != SELECTION_REPORT_VERSION
            or value["source_version"] not in (LEGACY_SELECTION_VERSION, SELECTION_VERSION)):
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
    legacy = value["source_version"] == LEGACY_SELECTION_VERSION
    seen = set()
    for choice in choices:
        _exact(choice, "name resources", code)
        name, resource = choice["name"], choice["resources"]
        if (not isinstance(name, str) or CODE.fullmatch(name) is None
                or (resource is not None if legacy else resource not in RESOURCE_KINDS)):
            raise ValueError(code)
        key = name, resource
        if key in seen:
            raise ValueError(code)
        seen.add(key)
    if tool_library is not None:
        if legacy:
            tool_library.resolve([choice["name"] for choice in choices])
        else:
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
    if value["version"] not in (VERSION, LEGACY_RETURN_VERSION, RETURN_VERSION):
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
            if selection["version"] == LEGACY_SELECTION_VERSION:
                tool_library.resolve(selection[tools_field])
            else:
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


def project_process_result(value, *, library, tool_library):
    """Make a new compact view of supplied, library-qualified closing facts."""
    if library is None or tool_library is None:
        raise ValueError("scientific_process_result_library_invalid")
    value = validate_process_result(value, library=library, tool_library=tool_library)
    if value["version"] == RETURN_VERSION:
        return value
    if value['version'] == LEGACY_RETURN_VERSION:
        return {**value, 'version': RETURN_VERSION,
            'proposed_annotation_ref': value.get('proposed_annotation_ref')}
    selection = value["selection"]
    axis_field, thought_field, tools_field = selection_fields(selection)
    choices = ([{"name": name, "resources": None} for name in selection[tools_field]]
        if selection["version"] == LEGACY_SELECTION_VERSION else
        [{"name": choice["name"], "resources": choice["resources"]}
         for choice in selection[tools_field]])
    reported_selection = _validate_report_selection({
        "version": SELECTION_REPORT_VERSION, "source_version": selection["version"],
        "evidence_axis": selection[axis_field], "thought_pattern": selection[thought_field],
        "child_tool_info": choices})
    return {**value, "version": RETURN_VERSION, "selection": reported_selection,
        'proposed_annotation_ref': value.get('proposed_annotation_ref')}


def credit_binding_ref(metadata):
    """Identify the actual finite metadata without exposing its definition."""
    if metadata is None:
        return None
    value = _plain(metadata)
    if not isinstance(value, dict) or not value:
        raise ValueError("scientific_process_credit_metadata_invalid")
    return identity("scientific_credit_binding", value)


def build_process_result(context, completion_snapshot):
    """Copy one actual closure; never manufacture or refit a closing value."""
    if not isinstance(completion_snapshot, Mapping):
        raise ValueError("scientific_process_completion_snapshot_invalid")
    if completion_snapshot.get("completion") is None:
        return None
    snapshot = _plain(completion_snapshot)
    completion = snapshot["completion"]
    _exact(completion, "ended_by end_reason units_consumed", "scientific_process_completion_invalid")
    EpisodeCompletion(**completion)
    try:
        count = snapshot["own_action_count"]
        if type(count) is not int or count != completion["units_consumed"]:
            raise ValueError("scientific_process_completion_count_mismatch")
        assignment = _plain(context.assignment)
        message = context.request["message"]
        if assignment != _plain(message["episode_assignment"]):
            raise ValueError("scientific_process_result_assignment_mismatch")
        invocation = validate_invocation_ref(message["scientific_invocation_ref"])
        if invocation != scientific_invocation_ref(context.run_id, context.path):
            raise ValueError("scientific_process_result_invocation_mismatch")
        parent = snapshot["parent_invocation_ref"]
        if parent is not None and (len(context.path) < 2 or
                parent != scientific_invocation_ref(context.run_id, context.path[:-1])):
            raise ValueError("scientific_process_result_parent_mismatch")
        origin = assignment.get("revision_origin")
        if "revision_origin" in assignment:
            origin = validate_revision_origin(origin)
            if origin["parent_invocation_ref"] != parent:
                raise ValueError("scientific_process_result_origin_mismatch")
        metadata = snapshot["controller_credit"]
        kind = None
        if metadata is not None:
            _exact(metadata, "credit_kind credit_binding", "scientific_process_credit_metadata_invalid")
            kind = metadata["credit_kind"]
            if (kind not in _CREDIT_KINDS or not isinstance(metadata["credit_binding"], dict)
                    or not metadata["credit_binding"]):
                raise ValueError("scientific_process_credit_metadata_invalid")
        return validate_process_result({"version": VERSION, "invocation_ref": invocation,
            "parent_invocation_ref": parent,
            "origin_kind": "ordinary_child" if origin is None else "approach_revision",
            "preparation_operation_ref": None if origin is None else origin["preparation_operation_ref"],
            "selection": assignment["selection"], "initial_credit": snapshot["initial_credit"],
            "credit": snapshot["credit"], "credit_kind": kind,
            "credit_binding_ref": credit_binding_ref(metadata), "completed_actions": count,
            "episode_yield": snapshot["episode_yield"],
            **({'proposed_annotation_ref': assignment['proposed_annotation_ref']}
               if assignment.get('proposed_annotation_ref') else {})})
    except (KeyError, AttributeError, TypeError) as error:
        raise ValueError("scientific_process_completion_snapshot_invalid") from error


def merge_process_results(own_result, received_results):
    """Stable own-first union; the same invocation cannot acquire a new body."""
    if not isinstance(received_results, (list, tuple)):
        raise ValueError("scientific_process_results_invalid")
    results, known = [], {}
    for candidate in ([own_result] if own_result is not None else []) + list(received_results):
        row = validate_process_result(candidate)
        invocation = row["invocation_ref"]
        body = canonical(row)
        if invocation in known:
            if known[invocation] != body:
                raise ValueError("scientific_process_result_conflict")
            continue
        known[invocation] = body
        results.append(row)
    return results


__all__ = ["report_sources", "validate_process_result", "project_process_result", "build_process_result",
    "merge_process_results", "credit_binding_ref", "VERSION", "RETURN_VERSION", "SELECTION_REPORT_VERSION"]
