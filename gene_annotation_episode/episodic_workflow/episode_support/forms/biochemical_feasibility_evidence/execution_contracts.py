"""A110 contracts for explicit execution episodes and physical targets."""
from copy import deepcopy
import hashlib
import json

from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.communication import plain


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


TEXT = {'type': 'string', 'minLength': 1}
SHA256 = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
TARGET_SCHEMA = obj({
    'version': {'type': 'string', 'const': 'execution_target'},
    'handle': TEXT, 'run_id': TEXT, 'resource_id': TEXT,
    'resource_kind': {'type': 'string', 'enum': ['local', 'hpc']},
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


def validate_target(value):
    return checked(value, TARGET_SCHEMA, 'invalid_execution_target')
