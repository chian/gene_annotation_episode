"""Exact callable-name and resource-variant selection schemas."""
from ..scientific_tool_library import tool_names
from gene_annotation_episode.tool_information import selectors as tool_selectors


def output_schema(names, *, transport=False):
    """The map supplies the enum; uniqueness is additionally checked on return."""
    names = tool_names(list(names))
    selected = {"type": "array", "items": {"type": "string"}}
    if names:
        selected["items"]["enum"] = names
    else:
        # JSON Schema forbids an empty enum. An empty map has no valid names.
        selected["maxItems"] = 0
    if not transport:
        selected["uniqueItems"] = True
    return {"type": "object", "properties": {"tools": selected},
        "required": ["tools"], "additionalProperties": False}


def tool_info_output_schema(rows, *, transport=False):
    choices = tool_selectors([{key: row[key] for key in ('name', 'resources')} for row in rows])
    alternatives = [{'type': 'object', 'additionalProperties': False,
        'properties': {'name': {'type': 'string', 'enum': [row['name']]},
            'resources': {'type': 'string', 'enum': [row['resources']]}},
        'required': ['name', 'resources']} for row in choices]
    selected = {'type': 'array', 'items': {'anyOf': alternatives} if alternatives else {
        'type': 'object', 'additionalProperties': False, 'properties': {}, 'required': []}}
    if not choices:
        selected['maxItems'] = 0
    if not transport:
        selected['uniqueItems'] = True
    return {'type': 'object', 'properties': {'child_tool_info': selected},
        'required': ['child_tool_info'], 'additionalProperties': False}


