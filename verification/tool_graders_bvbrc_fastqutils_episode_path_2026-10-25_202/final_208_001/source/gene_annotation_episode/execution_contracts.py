"""Pure shared contracts for explicit execution episodes and physical targets."""
from copy import deepcopy
import hashlib
import json

from jsonschema import Draft202012Validator

from .communication import plain
from .launch_instructions import SELECTION_SCHEMA, validate_selection


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


TEXT = {'type': 'string', 'minLength': 1}
SHA256 = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
API_ASSIGNMENT_SCHEMA = obj({
    'version': {'type': 'string', 'const': 'api_execution_assignment_v1'},
    'resource_id': TEXT, 'service': {'type': 'string', 'const': 'ebi_hmmer'},
    'subject_ref': TEXT, 'algorithm': {'type': 'string', 'enum': ['phmmer', 'hmmscan']},
    'database': TEXT, 'parameters': {'type': 'object'},
    'page_size': {'type': 'integer', 'minimum': 1},
    'endpoint': {'type': 'string', 'const': 'usable_handoff'},
    'constraints': {'type': 'object'},
})
API_ASSIGNMENT_SCHEMA['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
API_SERVICE_ASSIGNMENT_VERSION = 'api_service_assignment_v1'
API_SERVICE_ASSIGNMENT_SCHEMA = obj({
    'version': {'type': 'string', 'const': API_SERVICE_ASSIGNMENT_VERSION},
    'resource_id': TEXT,
    'service': TEXT,
    # The actual service replaces this envelope with its concrete closed
    # request schema before the parent can commission execution.
    'request': {'type': 'object'},
    'endpoint': {'type': 'string', 'const': 'usable_handoff'},
    'constraints': {'type': 'object'},
})
API_SERVICE_ASSIGNMENT_SCHEMA['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
TARGET_SCHEMA = obj({
    'version': {'type': 'string', 'const': 'execution_target_v1'},
    'handle': TEXT, 'run_id': TEXT, 'resource_id': TEXT,
    'resource_kind': {'type': 'string', 'enum': ['api', 'local', 'hpc']},
    'execution_id': TEXT, 'request_sha256': SHA256, 'origin_episode_id': TEXT,
    'assignment': {'type': 'object'}, 'scope': {'type': 'object'},
})


def canonical(value):
    return json.dumps(plain(value), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def checked(value, schema, code):
    try:
        value = json.loads(canonical(value))
        if not Draft202012Validator(schema).is_valid(value):
            raise ValueError(code)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(code) from error
    return value


def validate_api_assignment(value):
    value = plain(value)
    schema = (API_ASSIGNMENT_SCHEMA if isinstance(value, dict)
        and value.get('version') == 'api_execution_assignment_v1'
        else API_SERVICE_ASSIGNMENT_SCHEMA)
    value = checked(value, schema, 'invalid_api_execution_assignment')
    if 'launch_instructions' in value:
        validate_selection(value['launch_instructions'])
    return value


def validate_api_service_assignment(value):
    value = checked(value, API_SERVICE_ASSIGNMENT_SCHEMA, 'invalid_api_service_assignment')
    if 'launch_instructions' in value:
        validate_selection(value['launch_instructions'])
    return value


def validate_target(value):
    return checked(value, TARGET_SCHEMA, 'invalid_execution_target')
