"""Validate the commissioning Launch contract independently of this native child's credit role."""
from __future__ import annotations
from .contracts import INPUT_VERSION_SCHEMA, LAUNCH_VERSION, SELECTION_SCHEMA, deepcopy, launch_request_schema, obj

def parent_launch_schema(binding):
    schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: launch_request_schema(binding._request_schema(key, selected=False, internal=True, compact=False), key, binding.resources[key].get('service')) for key in binding.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema
