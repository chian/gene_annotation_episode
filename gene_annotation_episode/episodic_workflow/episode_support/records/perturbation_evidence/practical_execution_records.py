"""A106 exact API completion proof and finite receipt values."""
from collections.abc import Mapping
import hashlib
import json
import re

COMPLETION_VERSION = 'practical_completion_v1'
COMPLETION_FIELDS = {'version', 'run_id', 'episode_id', 'assignment_sha256',
    'endpoint', 'operation_key', 'receipt_sha256', 'validation_keys'}
_TEXT_SCHEMA = {'type': 'string', 'minLength': 1}
_DIGEST_SCHEMA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}

def _schema_object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


COMPLETION_PROOF_SCHEMA = _schema_object({'version': {'const': COMPLETION_VERSION},
    'run_id': _TEXT_SCHEMA, 'episode_id': _TEXT_SCHEMA, 'assignment_sha256': _DIGEST_SCHEMA,
    'endpoint': {'enum': ['usable_handoff', 'completed_job_outputs']},
    'operation_key': _TEXT_SCHEMA, 'receipt_sha256': _DIGEST_SCHEMA,
    'validation_keys': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT_SCHEMA}})


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def _json(value):
    if isinstance(value, Mapping):
        value = {key: _json(item) for key, item in value.items()}
    elif isinstance(value, (tuple, list)):
        value = [_json(item) for item in value]
    return json.loads(canonical(value))

def _object(value, fields=None, *, code='invalid_practical_record'):
    if not isinstance(value, Mapping):
        raise ValueError(code)
    try:
        value = _json(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(code) from error
    if fields is not None and set(value) != set(fields):
        raise ValueError(code)
    return value

def _text(value):
    return isinstance(value, str) and bool(value) and '\0' not in value

def _sha(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('invalid_practical_digest')
    return value

def _strings(value, *, nonempty=False, unique=False):
    if (not isinstance(value, list) or nonempty and not value
            or any(not _text(item) for item in value)
            or unique and len(set(value)) != len(value)):
        raise ValueError('invalid_practical_string_array')
    return value

def validate_completion_proof(value):
    value = _object(value, COMPLETION_FIELDS, code='invalid_practical_completion_proof')
    if value['version'] != COMPLETION_VERSION or value['endpoint'] not in {
            'usable_handoff', 'completed_job_outputs'}:
        raise ValueError('invalid_practical_completion_proof')
    for key in ('run_id', 'episode_id', 'operation_key'):
        if not _text(value[key]):
            raise ValueError('invalid_practical_completion_proof')
    _sha(value['assignment_sha256'])
    _sha(value['receipt_sha256'])
    _strings(value['validation_keys'], nonempty=True, unique=True)
    return value

