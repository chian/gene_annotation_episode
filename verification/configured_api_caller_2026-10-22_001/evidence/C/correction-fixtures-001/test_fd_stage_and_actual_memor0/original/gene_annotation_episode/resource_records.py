"""Pure resource assignment and handoff schemas, shared by producers/readers."""
from copy import deepcopy

from .communication import plain


def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
RESOURCE_ROLES = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
LAUNCH_VERSION = 'resource_launch_assignment_v1'
RESULTS_VERSION = 'resource_results_assignment_v1'
FAILURE_CODES = ('resource_unavailable', 'resource_authentication_required',
    'resource_availability_unknown', 'resource_not_bound', 'resource_selection_conflict',
    'resource_assignment_conflict', 'receiving_interface_unavailable',
    'no_selected_receiving_check', 'invalid_resource_handoff',
    'invalid_resource_selector', 'requested_data_selector_conflict')


def _string():
    return {'type': 'string', 'minLength': 1}


def _reference(namespace, *, identifier=False):
    return {'type': 'string', 'format': 'identifier' if identifier else 'reference',
        'x-reference-namespace': namespace}


def _array(item):
    return {'type': 'array', 'items': item}


def _nullable(schema):
    return {**deepcopy(schema), 'type': [schema['type'], 'null']}


ALLOCATION_SCHEMA = obj({
    'cpu': {'type': ['integer', 'null'], 'minimum': 1},
    'memory_bytes': {'type': ['integer', 'null'], 'minimum': 1},
    'scratch_bytes': {'type': ['integer', 'null'], 'minimum': 1},
    'wall_seconds': {'type': ['number', 'null'], 'exclusiveMinimum': 0}})
SELECTION_SCHEMA = obj({'resource_id': _reference('resource_binding'),
    'kind': {'type': 'string', 'enum': ['api', 'local', 'hpc']},
    'allocation': ALLOCATION_SCHEMA, 'capability_binding_ref': _reference('execution_registry')})
INPUT_VERSION_SCHEMA = obj({'reference': _reference(None),
    'version': _nullable(_reference('resource_input_version', identifier=True)),
    'content_sha256': _nullable(_reference('resource_input_digest', identifier=True))})
CAPABILITY_SCHEMA = obj({'resource_id': _string(),
    'kind': {'type': 'string', 'enum': ['api', 'local', 'hpc']},
    'availability': {'type': 'string', 'enum': ['available', 'unavailable',
        'authentication_required', 'unknown']},
    'observed_at': _string(), 'provenance_refs': _array(_string()),
    'knowledge_entry_ids': _array(_string()), 'tool_names': _array(_string())})
FAILURE_SCHEMA = obj({'code': {'type': 'string', 'enum': list(FAILURE_CODES)},
    'affected_refs': _array(_reference(None)), 'diagnostic_ref': _nullable(_reference(None)),
    'partial_record_refs': _array(_reference(None))})
RECEIVER_SCHEMA = obj({'provider_id': _reference('resource_binding'),
    'target_handle': _reference('resource_execution'),
    'contract_ref': _reference('resource_interface')})
HANDOFF_SCHEMA = obj({'version': {'type': 'string', 'const': 'execution_handoff_v1'},
    'execution_handle': _reference('resource_execution'), 'resource_selection': SELECTION_SCHEMA,
    'submitted_input_versions': _array(INPUT_VERSION_SCHEMA),
    'monitoring': RECEIVER_SCHEMA, 'results': RECEIVER_SCHEMA,
    'checked_at': _reference('resource_check_timestamp', identifier=True),
    'check_record_refs': _array(_reference('handoff_receipt')),
    'state': {'type': 'string', 'enum': ['usable', 'unavailable']},
    'failure': _nullable(FAILURE_SCHEMA)})
LAUNCH_SCHEMA = obj({'version': {'type': 'string', 'const': LAUNCH_VERSION},
    'job_request': {'type': 'object'},
    'immutable_input_versions': _array(INPUT_VERSION_SCHEMA),
    'constraints': {'type': 'object'}, 'resource_selection': _nullable(SELECTION_SCHEMA),
    'software_knowledge_refs': _array(_string()), 'resource_knowledge_refs': _array(_string())})
RESULTS_SCHEMA = obj({'version': {'type': 'string', 'const': RESULTS_VERSION},
    'handoff': HANDOFF_SCHEMA, 'requested_data_selector': {'type': 'object'}})


def _validate(value, schema):
    from jsonschema import Draft202012Validator
    errors = list(Draft202012Validator(schema).iter_errors(plain(value)))
    if errors:
        raise ValueError('invalid_resource_assignment:' + errors[0].message)
    return plain(value)

