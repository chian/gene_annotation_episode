"""Actual commissioning Launch contract, independent of this child's role admission."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a104.resource_records import INPUT_VERSION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.a104_execution_bindings import launch_request_schema

LAUNCH_VERSION = 'execution_launch_assignment_v1'

def parent_launch_schema(binding):
    schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: launch_request_schema(binding._request_schema(key, selected=False, internal=True, compact=False), key, binding.resources[key].get('service')) for key in binding.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
    schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
    return schema
