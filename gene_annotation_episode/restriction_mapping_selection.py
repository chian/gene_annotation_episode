"""Expand an explicit restriction leaf selection using the existing return schema.

This describes a parent-selected view only. The saved result and its existing
reader remain the authorities for values, coordinates and missingness.
"""
from copy import deepcopy

from .communication import ReportBoundaryError
from .restriction_mapping_contracts import restriction_canonical
from .restriction_mapping_returns import (
    requested_restriction_projections, restriction_mapping_fact_sources,
)


_SOURCE = "restriction_mapping_results"
_KEYS = frozenset(("version", "policy", "sequence_ref", "fields"))
_POLICIES = ("all_own_completed_results", "matching_sequence")


def _require(condition, code, field=None):
    if not condition:
        raise ReportBoundaryError(code, code="restriction_selection_" + code, field=field)


def _leaf_paths(node, prefix=()):
    if "properties" in node:
        for name, child in node["properties"].items():
            yield from _leaf_paths(child, (*prefix, name))
    elif "items" in node and "properties" in node["items"]:
        yield from _leaf_paths(node["items"], prefix)
    else:
        yield ".".join(prefix)


def _selected_tree(node, paths, prefix=()):
    if "properties" in node:
        properties = {}
        for name, child in node["properties"].items():
            selected = _selected_tree(child, paths, (*prefix, name))
            if selected is not None:
                properties[name] = selected
        if not properties:
            return None
        result = deepcopy(node)
        result["properties"] = properties
        result["required"] = list(properties)
        return result
    if "items" in node and "properties" in node["items"]:
        selected = _selected_tree(node["items"], paths, prefix)
        if selected is None:
            return None
        result = deepcopy(node)
        result["items"] = selected
        return result
    return deepcopy(node) if ".".join(prefix) in paths else None


def restriction_selected_return_schema(selection: dict) -> dict:
    """Return the exact closed723 schema for explicitly named leaf fields.

    Missing context dependencies fail through the existing723 validator rather
    than being supplied implicitly. This grants no sequence-reference authority.
    """
    try:
        restriction_canonical(selection)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ReportBoundaryError("Finite JSON required",
            code="restriction_selection_finite_json_required") from error
    _require(type(selection) is dict and set(selection) == _KEYS, "keys_required")
    _require(type(selection["version"]) is str
        and selection["version"] == "restriction_return_selection_v1", "version_invalid", "version")
    policy = selection["policy"]
    _require(type(policy) is str and policy in _POLICIES, "policy_invalid", "policy")
    reference = selection["sequence_ref"]
    _require(reference is None if policy == "all_own_completed_results"
        else type(reference) is str and bool(reference), "reference_invalid", "sequence_ref")
    fields = selection["fields"]
    _require(type(fields) is list and bool(fields)
        and all(type(path) is str for path in fields), "fields_invalid", "fields")
    _require(len(set(fields)) == len(fields), "fields_duplicate", "fields")
    base = restriction_mapping_fact_sources()[_SOURCE]["report_schema"]
    available = set(_leaf_paths(base))
    for path in fields:
        _require(path in available, "field_unknown", path)
    result = _selected_tree(base, set(fields))
    properties = result["items"]["properties"]
    if "selection_policy" in properties:
        properties["selection_policy"] = {"type": "string", "const": policy}
    if policy == "matching_sequence" and "sequence_ref" in properties:
        properties["sequence_ref"]["const"] = reference
    requested_restriction_projections({"type": "object", "properties": {"selected": result},
        "required": ["selected"], "additionalProperties": False})
    restriction_canonical(result)
    return result


__all__ = ["restriction_selected_return_schema"]
