"""Finite, detached records for the scientific three-slot construction.

These records identify information selected by a parent. They do not introduce
Store evidence references or decide a child's scientific action or credit.
"""
from __future__ import annotations

import json
import re

from method_loop.durable import canonical, content_digest
from method_loop.identities import normalize_structural_path

from .domain import identity


OPTION_REF_VERSION = "scientific_process_option_ref_v1"
SELECTION_VERSION = "scientific_process_selection_v3"
LEGACY_SELECTION_VERSION = "scientific_process_selection_v2"
SELECTION_VIEW_VERSION = "scientific_process_selection_view_v1"
FILLED_PROCESS_VERSION = "filled_scientific_process_v1"
REVISION_VERSION = "scientific_process_revision_v1"
CHILD_SELECTION_VERSION = "scientific_process_child_selection_v1"
REVISION_ORIGIN_VERSION = "scientific_process_revision_origin_v1"
SLOTS = ("evidence_axis", "thought_pattern")
LEGACY_EVIDENCE_SLOT = "annotation_distinction"
ALL_SLOTS = (*SLOTS, LEGACY_EVIDENCE_SLOT)
_PREFIXES = {"evidence_axis": "A", LEGACY_EVIDENCE_SLOT: "A", "thought_pattern": "P"}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_INVOCATION_REF = re.compile(r"scientific_invocation_[0-9a-f]{24}\Z")
_PREPARATION_REF = re.compile(r"operation_[0-9a-f]{24}\Z")


def scientific_digest(value) -> str:
    """SHA-256 of the existing durable finite-JSON canonical representation."""
    return content_digest(value)


def canonical_slot(value):
    """Compare slot meanings without rewriting an old pinned option record."""
    return 'evidence_axis' if value == LEGACY_EVIDENCE_SLOT else value


def scientific_invocation_ref(run_id, path) -> str:
    """Identify the original logical invocation, independent of its placement."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("scientific_invocation_identity_invalid")
    try:
        path = normalize_structural_path(path)
    except (TypeError, ValueError) as error:
        raise ValueError("scientific_invocation_identity_invalid") from error
    return identity("scientific_invocation", {
        "run_id": run_id, "path": [list(segment) for segment in path]})


def validate_invocation_ref(value) -> str:
    if not isinstance(value, str) or _INVOCATION_REF.fullmatch(value) is None:
        raise ValueError("scientific_invocation_reference_invalid")
    return value


def _plain(value):
    try:
        return json.loads(canonical(value))
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("scientific_process_json_invalid") from error


def _exact(value, fields, code):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(code)


def _text(value, code):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)


def _sha256(value, code):
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(code)


def _option_id(value, slot, code):
    if (not isinstance(slot, str) or slot not in _PREFIXES or
            not isinstance(value, str) or
            re.fullmatch(_PREFIXES[slot] + r"[0-9]+", value) is None):
        raise ValueError(code)


def validate_option_ref(value) -> dict:
    value = _plain(value)
    code = "scientific_process_option_ref_invalid"
    _exact(value, "version library_id slot option_id entry_sha256", code)
    if value["version"] != OPTION_REF_VERSION:
        raise ValueError(code)
    _sha256(value["library_id"], code)
    _sha256(value["entry_sha256"], code)
    _option_id(value["option_id"], value["slot"], code)
    return value


def validate_selection(value) -> dict:
    value = _plain(value)
    code = "scientific_process_selection_invalid"
    if not isinstance(value, dict):
        raise ValueError(code)
    if value.get('version') == LEGACY_SELECTION_VERSION:
        fields = ('annotation_ref', 'thought_ref', 'tools')
    elif value.get('version') == SELECTION_VERSION:
        fields = ('evidence_axis', 'thought_pattern', 'child_tool_info')
    else:
        raise ValueError(code)
    _exact(value, 'version ' + ' '.join(fields), code)
    refs = []
    for name, slot in zip(fields[:2], SLOTS):
        ref = validate_option_ref(value[name])
        if canonical_slot(ref["slot"]) != slot:
            raise ValueError(code)
        value[name] = ref
        refs.append(ref)
    if len({ref["library_id"] for ref in refs}) != 1:
        raise ValueError(code)
    if value['version'] == LEGACY_SELECTION_VERSION:
        from .scientific_tool_library import tool_names
        value['tools'] = tool_names(value['tools'])
    else:
        from .tool_information import INFO_FIELDS, tool_info_selection
        information = tool_info_selection(value['child_tool_info'])
        if any(set(row) != INFO_FIELDS for row in information):
            raise ValueError('scientific_canonical_tool_info_required')
        value['child_tool_info'] = information
    return value


def selection_fields(value):
    """Read a versioned identity without normalizing its original dictionary."""
    version = value.get('version')
    if version == LEGACY_SELECTION_VERSION:
        return 'annotation_ref', 'thought_ref', 'tools'
    if version == SELECTION_VERSION:
        return 'evidence_axis', 'thought_pattern', 'child_tool_info'
    raise ValueError('scientific_process_selection_invalid')


def selector_selection(value):
    value = validate_selection(value)
    if value['version'] == LEGACY_SELECTION_VERSION:
        return value
    from .tool_information import selectors
    return {**value, 'child_tool_info': selectors(value['child_tool_info'])}


def parent_selection_view(value):
    value = validate_selection(value)
    if value['version'] == LEGACY_SELECTION_VERSION:
        return value
    from .tool_information import parent_view
    return {**value, 'version': SELECTION_VIEW_VERSION,
            'child_tool_info': parent_view(value['child_tool_info'])}


def validate_parent_selection_view(value):
    value = _plain(value)
    code = 'scientific_process_selection_view_invalid'
    _exact(value, 'version evidence_axis thought_pattern child_tool_info', code)
    if value['version'] != SELECTION_VIEW_VERSION:
        raise ValueError(code)
    refs = [validate_option_ref(value[key]) for key in ('evidence_axis', 'thought_pattern')]
    if (tuple(canonical_slot(ref['slot']) for ref in refs) != SLOTS
            or len({ref['library_id'] for ref in refs}) != 1):
        raise ValueError(code)
    from .tool_information import RESOURCE_KINDS
    if not isinstance(value['child_tool_info'], list):
        raise ValueError(code)
    keys = []
    for row in value['child_tool_info']:
        _exact(row, 'name description resources', code)
        _text(row['name'], code); _text(row['description'], code)
        if row['resources'] not in RESOURCE_KINDS:
            raise ValueError(code)
        keys.append((row['name'], row['resources']))
    if len(keys) != len(set(keys)):
        raise ValueError(code)
    return value


def validate_filled_process(value) -> dict:
    value = _plain(value)
    code = "scientific_process_filled_invalid"
    _exact(value, "version selection assignment_sha256 invocation_sha256 mechanics_binding", code)
    if value["version"] != FILLED_PROCESS_VERSION:
        raise ValueError(code)
    value["selection"] = validate_selection(value["selection"])
    _sha256(value["assignment_sha256"], code)
    _sha256(value["invocation_sha256"], code)
    if not isinstance(value["mechanics_binding"], dict) or not value["mechanics_binding"]:
        raise ValueError(code)
    return value


def validate_revision(value) -> dict:
    """Parse saved historical revisions without selecting any active process."""
    value = _plain(value)
    code = "scientific_process_revision_invalid"
    _exact(value, "version initial_selection_sha256 previous_selection_sha256 selection", code)
    if value["version"] != REVISION_VERSION:
        raise ValueError(code)
    for key in ("initial_selection_sha256", "previous_selection_sha256"):
        _sha256(value[key], code)
    value["selection"] = validate_selection(value["selection"])
    return value


def validate_child_selection(value) -> dict:
    """Validate a detached proposal for a separately commissioned child."""
    value = _plain(value)
    code = "scientific_process_child_selection_invalid"
    _exact(value, "version parent_selection_sha256 selection", code)
    if value["version"] != CHILD_SELECTION_VERSION:
        raise ValueError(code)
    _sha256(value["parent_selection_sha256"], code)
    value["selection"] = validate_selection(value["selection"])
    return value


def validate_revision_origin(value) -> dict:
    """Parse an explicit relationship; authentication requires the own record."""
    value = _plain(value)
    code = "scientific_process_revision_origin_invalid"
    _exact(value, "version parent_invocation_ref preparation_operation_ref", code)
    if value["version"] != REVISION_ORIGIN_VERSION:
        raise ValueError(code)
    validate_invocation_ref(value["parent_invocation_ref"])
    if (not isinstance(value["preparation_operation_ref"], str)
            or _PREPARATION_REF.fullmatch(value["preparation_operation_ref"]) is None):
        raise ValueError(code)
    return value


__all__ = ["scientific_digest", "validate_option_ref", "validate_selection",
           "validate_filled_process", "validate_revision", "validate_child_selection",
           "scientific_invocation_ref", "validate_invocation_ref", "validate_revision_origin",
           "selection_fields", "selector_selection", "parent_selection_view", "validate_parent_selection_view",
           "canonical_slot", "SELECTION_VERSION", "LEGACY_SELECTION_VERSION", "SELECTION_VIEW_VERSION"]
