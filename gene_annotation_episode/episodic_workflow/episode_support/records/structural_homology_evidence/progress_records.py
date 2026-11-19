"""Typed native progress without episode return or acknowledgment identities."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import base64
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError, canonical, obj, validate_schema


RESOURCE_STATUS_VERSION = 'resource_execution_status_v1'
_TEXT = {'type': 'string', 'minLength': 1}
RESOURCE_OBSERVATION_SCHEMA = obj({
    'observed_at': _TEXT,
    'state': {'enum': ['submitted', 'running', 'completed', 'failed', 'unknown']},
    'returncode': {'type': ['integer', 'null']},
    'failure_code': {'type': ['string', 'null'], 'minLength': 1},
    'result_available': {'type': 'boolean'},
    'measurements': {'type': 'array', 'items': obj({
        'measure': _TEXT, 'seconds': {'type': 'number', 'minimum': 0}})},
    'outputs': {'type': 'array', 'items': obj({'role': _TEXT,
        'available': {'type': 'boolean'}, 'bytes': {'type': ['integer', 'null'], 'minimum': 0},
        'writer_closed': {'type': 'boolean'}})},
    'logs': {'type': 'array', 'items': obj({'role': _TEXT, 'path': _TEXT,
        'offset': {'type': 'integer', 'minimum': 0},
        'observed_size': {'type': 'integer', 'minimum': 0},
        'bytes_base64': {'type': 'string'}})},
    'provenance_refs': {'type': 'array', 'items': _TEXT, 'uniqueItems': True},
    'native': {'type': 'object'},
})
RESOURCE_STATUS_SCHEMA = obj({'version': {'const': RESOURCE_STATUS_VERSION},
    'handle': _TEXT, 'observed_at': _TEXT,
    'lifecycle_state': {'enum': ['pending', 'executing', 'returned', None]},
    'result_available': {'type': 'boolean'}, 'resource_id': _TEXT,
    'resource_kind': {'enum': ['api', 'local', 'hpc']}, 'execution_id': _TEXT,
    'request_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
    'native': deepcopy(RESOURCE_OBSERVATION_SCHEMA)})
_RESOURCE_LIFECYCLE = {'submitted': 'pending', 'running': 'executing',
    'completed': 'returned', 'failed': 'returned', 'unknown': None}


def validate_resource_observation(value):
    """Qualify one finite, byte-preserving observation of an existing target."""
    try:
        value = json.loads(canonical(plain(value)))
        validate_schema(value, RESOURCE_OBSERVATION_SCHEMA)
        stamp = datetime.fromisoformat(value['observed_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
            raise ValueError('UTC timestamp required')
        for field, key in (('outputs', 'role'), ('logs', 'role'), ('measurements', 'measure')):
            if len({row[key] for row in value[field]}) != len(value[field]):
                raise ValueError('duplicate resource observation identity')
        for row in value['measurements']:
            if not math.isfinite(row['seconds']):
                raise ValueError('finite measured resource interval required')
        for row in value['outputs']:
            if ((not row['available'] and (row['bytes'] is not None or row['writer_closed']))
                    or row['available'] and row['bytes'] is None
                    or row['writer_closed'] and value['state'] not in {'completed', 'failed'}):
                raise ValueError('invalid output relationship')
        outputs = {row['role']: row for row in value['outputs']}
        for row in value['logs']:
            raw = base64.b64decode(row['bytes_base64'], validate=True)
            output_role = ('requested_output:' + row['path']
                if row['role'] == 'native_log' else row['role'])
            if (base64.b64encode(raw).decode('ascii') != row['bytes_base64']
                    or row['offset'] + len(raw) > row['observed_size']
                    or output_role not in outputs or not outputs[output_role]['available']):
                raise ValueError('invalid retained log bytes')
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        raise ContractError('invalid_resource_progress_observation') from error
    return value


def validate_resource_status(value):
    try:
        value = json.loads(canonical(plain(value)))
        validate_schema(value, RESOURCE_STATUS_SCHEMA)
        native = validate_resource_observation(value['native'])
        if (value['lifecycle_state'] != _RESOURCE_LIFECYCLE[native['state']]
                or value['observed_at'] != native['observed_at']
                or value['result_available'] != native['result_available']):
            raise ValueError('resource status relationship mismatch')
    except (ValueError, TypeError, KeyError) as error:
        raise ContractError('invalid_resource_progress_status') from error
    return value


def resource_status(target, observation):
    native = validate_resource_observation(observation)
    return validate_resource_status({'version': RESOURCE_STATUS_VERSION,
        'handle': target['handle'], 'observed_at': native['observed_at'],
        'lifecycle_state': _RESOURCE_LIFECYCLE[native['state']],
        'result_available': native['result_available'],
        **{key: target[key] for key in ('resource_id', 'resource_kind', 'execution_id', 'request_sha256')},
        'native': native})



__all__ = ['RESOURCE_STATUS_VERSION', 'RESOURCE_STATUS_SCHEMA', 'RESOURCE_OBSERVATION_SCHEMA',
    'resource_status', 'validate_resource_status', 'validate_resource_observation']
