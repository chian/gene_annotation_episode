"""Pure preparation shared by ordinary, assigned and prospective HMMER work."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType

from .communication import plain
from .provider_jobs import build_search_request


VERSION = 'hmmer_request_preparation_v1'
ALLOCATION = {'cpu': None, 'memory_bytes': None, 'scratch_bytes': None, 'wall_seconds': None}
CONSTRAINTS = set(ALLOCATION) | {'allowed_resource_ids', 'allowed_kinds', 'resource_id', 'kind'}


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class PreparedHmmerRequest:
    arguments: Mapping
    normalized_arguments: Mapping
    request: Mapping
    query_fasta: str

    def __post_init__(self):
        for field in ('arguments', 'normalized_arguments', 'request'):
            object.__setattr__(self, field, _freeze(plain(getattr(self, field))))


def prepare_hmmer_request(arguments, *, sequence_symbols, scope):
    """Validate supplied operands, retain exact FASTA bytes, and normalize once.

    The accessor owns reference/scope qualification; aliases are not resolved
    here. The provider's existing builder alone defines the search identity.
    """
    arguments = plain(arguments)
    allowed = {'subject_ref', 'algorithm', 'database', 'parameters', 'page_size'}
    if (not isinstance(arguments, dict) or set(arguments) - allowed
            or not {'subject_ref', 'algorithm', 'database'} <= set(arguments)
            or not isinstance(arguments['subject_ref'], str)
            or not isinstance(arguments['algorithm'], str) or arguments['algorithm'] not in {'phmmer', 'hmmscan'}
            or not isinstance(arguments['database'], str) or not arguments['database']
            or type(arguments.get('page_size', 50)) is not int or arguments.get('page_size', 50) < 1):
        raise ValueError('unsupported_api_job_request')
    parameters = arguments.get('parameters', {})
    permitted = {'E', 'domE', 'incE', 'incdomE', 'T', 'domT', 'incT', 'incdomT',
        'popen', 'pextend', 'threshold', 'mx', 'include_taxonomy', 'exclude_taxonomy'}
    if not isinstance(parameters, dict) or set(parameters) - permitted:
        raise ValueError('unsupported_api_job_request')
    for key, value in parameters.items():
        if key in {'include_taxonomy', 'exclude_taxonomy'}:
            valid = isinstance(value, list) and all(type(item) is int and item > 0 for item in value)
        elif key == 'threshold':
            valid = isinstance(value, str) and value in {'evalue', 'bitscore'}
        elif key == 'mx':
            valid = isinstance(value, str) and bool(value)
        else:
            valid = type(value) in {int, float} and (type(value) is int or math.isfinite(value))
        if not valid:
            raise ValueError('unsupported_api_job_request')
    # Validation, including finiteness, precedes any JSON canonicalization.
    original = json.loads(json.dumps(arguments, allow_nan=False))
    normalized = {key: original[key] for key in ('subject_ref', 'algorithm', 'database')}
    normalized.update(parameters=original.get('parameters', {}), page_size=original.get('page_size', 50))
    symbols = sequence_symbols(normalized['subject_ref'], scope=scope)
    fasta = '>' + normalized['subject_ref'] + '\n' + symbols
    request, _ = build_search_request(query_fasta=fasta, provider='hmmer', **normalized)
    return PreparedHmmerRequest(original, normalized, request, fasta)


def qualify_api_candidate(store, *, scope, selection, constraints, immutable_input_versions):
    """Preserve the assigned API reader's constraint and explicit-pin checks."""
    constraints, selection = plain(constraints), plain(selection)
    if not isinstance(constraints, dict) or set(constraints) - CONSTRAINTS:
        raise ValueError('unsupported_api_constraints')
    for key, actual in (('resource_id', selection['resource_id']), ('kind', 'api'), *ALLOCATION.items()):
        if key in constraints and constraints[key] != actual:
            raise ValueError('resource_selection_conflict')
    for key, actual in (('allowed_resource_ids', selection['resource_id']), ('allowed_kinds', 'api')):
        if key in constraints and (not isinstance(constraints[key], list)
                or any(not isinstance(value, str) or not value for value in constraints[key])
                or actual not in constraints[key]):
            raise ValueError('resource_selection_conflict')
    for item in immutable_input_versions:
        record = store.get(item['reference'])
        if not store.reference_subset([item['reference']], scope):
            raise ValueError('resource_input_outside_assigned_scope')
        if item['version'] is not None and str(record.get('revision')) != item['version']:
            raise ValueError('resource_input_version_conflict')
        if item['content_sha256'] is not None:
            artifact = record['id'] if record['record_type'] == 'artifact' else record.get('sequence_ref')
            if artifact is None or hashlib.sha256(store.get_artifact(artifact)).hexdigest() != item['content_sha256']:
                raise ValueError('resource_input_version_conflict')
