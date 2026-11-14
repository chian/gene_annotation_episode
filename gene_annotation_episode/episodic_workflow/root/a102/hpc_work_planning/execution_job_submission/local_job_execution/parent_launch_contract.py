"""Validate the commissioning Launch contract independently of this native child's credit role."""
from __future__ import annotations
from .contracts import INPUT_VERSION_SCHEMA, LAUNCH_VERSION, SELECTION_SCHEMA, deepcopy, obj

def parent_launch_schema(binding):
    schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: binding._request_schema(key, selected=False, internal=True) for key in binding.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema
