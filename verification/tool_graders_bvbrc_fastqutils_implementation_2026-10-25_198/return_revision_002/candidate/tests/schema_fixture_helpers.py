"""Build actual allOf tool contracts for transport fixtures."""
import json
import re
from urllib.parse import unquote
from method_loop.durable import canonical
from gene_annotation_episode.schema_support import _schema_nodes


def _plain(value):
    return json.loads(canonical(value))


def _pointer(path):
    return "/" + "/".join(str(item).replace("~", "~0").replace("/", "~1")
                            for item in path) if path else ""


def _local_target(reference, schema, anchors, node_paths):
    if not isinstance(reference, str) or not reference.startswith("#"):
        raise ValueError("scientific_tool_schema_reference_unsupported")
    fragment = unquote(reference[1:])
    if not fragment:
        return ()
    if not fragment.startswith("/"):
        if fragment not in anchors:
            raise ValueError("scientific_tool_schema_reference_invalid")
        return anchors[fragment]
    path, target = [], schema
    try:
        for part in fragment[1:].split("/"):
            if re.search(r"~(?![01])", part):
                raise ValueError("invalid pointer escape")
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(target, list):
                if re.fullmatch(r"0|[1-9][0-9]*", part) is None:
                    raise ValueError("invalid array pointer")
                part = int(part)
            target = target[part]
            path.append(part)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ValueError("scientific_tool_schema_reference_invalid") from error
    if tuple(path) not in node_paths:
        # A reference into a const/enum literal requires separate resource
        # handling; rewriting the literal would change the API's meaning.
        raise ValueError("scientific_tool_schema_reference_unsupported")
    return tuple(path)


def _rebase(schema, prefix):
    """Keep each component's local refs local when nesting it in an allOf.

Ordinary root-local pointers and anchors become pointers into their own
component. Resource-scoped and dynamic references cannot be flattened this
way; report that unsupported configuration instead of changing its meaning.
"""
    result = _plain(schema)
    nodes = list(_schema_nodes(result))
    referenced = any(isinstance(node, dict) and "$ref" in node for _, node in nodes)
    for _, node in nodes:
        if not isinstance(node, dict):
            continue
        if any(key in node for key in ("$dynamicRef", "$recursiveRef", "$dynamicAnchor",
                                       "$recursiveAnchor")):
            raise ValueError("scientific_tool_schema_reference_unsupported")
        if referenced and "$id" in node:
            raise ValueError("scientific_tool_schema_resource_unsupported")
    anchors = {}
    for path, node in nodes:
        if isinstance(node, dict) and "$anchor" in node:
            anchor = node["$anchor"]
            if anchor in anchors:
                raise ValueError("scientific_tool_schema_reference_invalid")
            anchors[anchor] = path
    paths = {path for path, _ in nodes}
    for _, node in nodes:
        if not isinstance(node, dict):
            continue
        if "$ref" in node:
            target = _local_target(node["$ref"], result, anchors, paths)
            node["$ref"] = "#" + _pointer((*prefix, *target))
        # All references to these component-local anchors are now pointers.
        node.pop("$anchor", None)
    return result



