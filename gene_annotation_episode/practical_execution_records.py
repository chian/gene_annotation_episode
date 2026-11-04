"""Closed factual contracts for selected practical execution actions.

These functions inspect supplied records only. They execute no command, inspect
no filesystem and make no episode decision. Facts come from caller-bound real
operations; validation compares those facts with the original assignment.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from .launch_instructions import (SELECTION_SCHEMA as LAUNCH_INSTRUCTION_SELECTION_SCHEMA,
    validate_selection)

ASSIGNMENT_VERSION = 'practical_assignment_v1'
RECEIPT_VERSION = 'practical_action_receipt_v1'
COMPLETION_VERSION = 'practical_completion_v1'
JOB_TOOLS = frozenset({'practical.job.start', 'practical.job.status', 'practical.job.collect'})
LUMPY_OUTPUT_ROLES = ('vcf', 'stderr', 'seal', 'bam_headers')
PREDICATE_FIELDS = {
    'context_cwd': {'kind', 'path'},
    'context_environment': {'kind', 'name', 'value'},
    'path_exists': {'kind', 'path', 'object_type'},
    'file_sha256': {'kind', 'path', 'sha256'},
    'command_exit': {'kind', 'argv', 'returncode'},
    'requested_job_handoff': {'kind'},
    'requested_job_outputs': {'kind', 'output_paths'},
}
COMPLETION_FIELDS = {'version', 'run_id', 'episode_id', 'assignment_sha256',
    'endpoint', 'operation_key', 'receipt_sha256', 'validation_keys'}
RECEIPT_FIELDS = {'version', 'run_id', 'episode_id', 'assignment_sha256',
    'operation_key', 'tool_name', 'arguments', 'context_before', 'context_after',
    'outcome', 'validations', 'started_at', 'finished_at'}


def _schema_object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


_TEXT_SCHEMA = {'type': 'string', 'minLength': 1}
_PATH_SCHEMA = {'type': 'string', 'pattern': '^/'}
_DIGEST_SCHEMA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
_ARGV_SCHEMA = {'type': 'array', 'minItems': 1, 'items': _TEXT_SCHEMA}
_ENV_SCHEMA = {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
    'additionalProperties': {'type': 'string'}}
CONTEXT_SCHEMA = _schema_object({'revision': {'type': 'integer', 'minimum': 0},
    'cwd': _PATH_SCHEMA, 'environment': _ENV_SCHEMA})
GENERIC_REQUESTED_JOB_SCHEMA = _schema_object({'argv': _ARGV_SCHEMA, 'environment': _ENV_SCHEMA})
from .native_hmmer_contracts import NATIVE_HMMER_REQUESTED_JOB_SCHEMA
from .native_hmmer_preparation_job_schema import NATIVE_HMMER_PREPARATION_REQUESTED_JOB_SCHEMA
from .native_infernal_contracts import NATIVE_INFERNAL_REQUESTED_JOB_SCHEMA
from .native_infernal_preparation_job_schema import NATIVE_INFERNAL_PREPARATION_REQUESTED_JOB_SCHEMA
from .native_blast_contracts import NATIVE_BLAST_REQUESTED_JOB_SCHEMA
from .native_blast_masking_contracts import NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA
from .native_blast_utility_contracts import NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA
from .native_blast_database_contracts import NATIVE_BLAST_DATABASE_REQUESTED_JOB_SCHEMA
from .native_blast_standard_database_contracts import NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA
from .native_rna_structure_contracts import NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA
from .native_protein_structure_contracts import NATIVE_PROTEIN_STRUCTURE_REQUESTED_JOB_SCHEMA
from .native_genomic_overlap_contracts import genomic_overlap_execution_schema
from .native_chromatin_interaction_contracts import chromatin_interaction_execution_schema
from .native_atac_differential_contracts import atac_execution_schema
from .native_macs2_peak_execution import macs2_peak_execution_schema
from .native_lumpy_execution import lumpy_execution_schema
from .native_expression_nmf_contracts import NATIVE_EXPRESSION_NMF_REQUESTED_JOB_SCHEMA
from .native_fluorescence_contracts import NATIVE_FLUORESCENCE_REQUESTED_JOB_SCHEMA
from .flux_balance_contracts import flux_balance_schema
REQUESTED_JOB_SCHEMA = {'anyOf': [GENERIC_REQUESTED_JOB_SCHEMA,
    NATIVE_HMMER_REQUESTED_JOB_SCHEMA, NATIVE_HMMER_PREPARATION_REQUESTED_JOB_SCHEMA,
    NATIVE_INFERNAL_REQUESTED_JOB_SCHEMA,
    NATIVE_INFERNAL_PREPARATION_REQUESTED_JOB_SCHEMA, NATIVE_BLAST_REQUESTED_JOB_SCHEMA,
    NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA,
    NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA,
    NATIVE_BLAST_DATABASE_REQUESTED_JOB_SCHEMA, NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA,
    NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA, NATIVE_PROTEIN_STRUCTURE_REQUESTED_JOB_SCHEMA,
    genomic_overlap_execution_schema('RequestedJob'),
    chromatin_interaction_execution_schema('RequestedJob'),
    atac_execution_schema('RequestedJob'), macs2_peak_execution_schema('RequestedJob'),
    lumpy_execution_schema('RequestedJob'),
    NATIVE_EXPRESSION_NMF_REQUESTED_JOB_SCHEMA,
    NATIVE_FLUORESCENCE_REQUESTED_JOB_SCHEMA, flux_balance_schema('FBARequestedJob')]}
_FBA_EXECUTION_SELECTION_SCHEMA = _schema_object({
    'version': {'const': 'flux_balance_execution_selection_v1'},
    'environment_realization': {'const': 'operation_scoped_tmp_and_cache_v1'}})
_PREDICATE_OPERANDS = {
    'context_cwd': {'path': _PATH_SCHEMA},
    'context_environment': {'name': {'type': 'string', 'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
        'value': {'type': 'string'}},
    'path_exists': {'path': _PATH_SCHEMA, 'object_type': {'enum': ['file', 'directory']}},
    'file_sha256': {'path': _PATH_SCHEMA, 'sha256': _DIGEST_SCHEMA},
    'command_exit': {'argv': _ARGV_SCHEMA, 'returncode': {'type': 'integer'}},
    'requested_job_handoff': {},
    'requested_job_outputs': {'output_paths': {'type': 'array', 'minItems': 1,
        'uniqueItems': True, 'items': _PATH_SCHEMA}},
}
PREDICATE_SCHEMA = {'anyOf': [_schema_object({'kind': {'const': kind}, **operands})
    for kind, operands in _PREDICATE_OPERANDS.items()]}
PREDICATE_SCHEMA['anyOf'].append(_schema_object({'kind': {'const': 'requested_job_outputs'},
    'output_roles': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT_SCHEMA}}))
REQUIREMENT_SCHEMA = _schema_object({'key': _TEXT_SCHEMA,
    'credit': {'type': 'number', 'minimum': 0}, 'predicate': PREDICATE_SCHEMA})
ASSIGNMENT_SCHEMA = _schema_object({'version': {'const': ASSIGNMENT_VERSION},
    'assignment_id': _TEXT_SCHEMA, 'resource_kind': {'enum': ['local', 'hpc']},
    'workspace': _PATH_SCHEMA, 'endpoint': {'enum': ['usable_handoff', 'completed_job_outputs']},
    'requested_job': REQUESTED_JOB_SCHEMA,
    'progress_requirements': {'type': 'array', 'items': REQUIREMENT_SCHEMA},
    'completion_keys': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT_SCHEMA},
    'initial_context': CONTEXT_SCHEMA, 'inventory_snapshot': {'type': 'object'},
    'constraints': {'type': 'object'}})
ASSIGNMENT_SCHEMA['properties']['launch_instructions'] = deepcopy(LAUNCH_INSTRUCTION_SELECTION_SCHEMA)
ASSIGNMENT_SCHEMA['properties']['resource_id'] = deepcopy(_TEXT_SCHEMA)
ASSIGNMENT_SCHEMA['properties']['native_flux_balance_execution'] = deepcopy(_FBA_EXECUTION_SELECTION_SCHEMA)
ASSIGNMENT_SCHEMA['allOf'] = [{'if': {'required': ['native_flux_balance_execution']},
    'then': {'properties': {'requested_job': {'required': ['native_flux_balance']}}}}]
VALIDATION_SCHEMA = _schema_object({'key': _TEXT_SCHEMA, 'satisfied': {'type': 'boolean'},
    'predicate': PREDICATE_SCHEMA, 'evidence_refs': {'type': 'array', 'uniqueItems': True,
        'items': _TEXT_SCHEMA}, 'evidence': _schema_object({'source': {'enum': ['context', 'outcome']},
        'value': {}}), 'checked_at': {'type': 'string', 'format': 'date-time'}})
RECEIPT_SCHEMA = _schema_object({'version': {'const': RECEIPT_VERSION},
    'run_id': _TEXT_SCHEMA, 'episode_id': _TEXT_SCHEMA, 'assignment_sha256': _DIGEST_SCHEMA,
    'operation_key': _TEXT_SCHEMA, 'tool_name': _TEXT_SCHEMA, 'arguments': {'type': 'object'},
    'context_before': CONTEXT_SCHEMA, 'context_after': CONTEXT_SCHEMA,
    'outcome': {'type': 'object'}, 'validations': {'type': 'array', 'items': VALIDATION_SCHEMA},
    'started_at': {'type': 'string', 'format': 'date-time'},
    'finished_at': {'type': 'string', 'format': 'date-time'}})
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


def _path(value):
    if (not _text(value) or not value.startswith('/')
            or '..' in PurePosixPath(value).parts or str(PurePosixPath(value)) != value):
        raise ValueError('invalid_practical_absolute_path')
    return value


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


def _environment(value):
    value = _object(value, code='invalid_practical_environment')
    if any(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', key) is None
            or not isinstance(item, str) or '\0' in item for key, item in value.items()):
        raise ValueError('invalid_practical_environment')
    return value


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('invalid_practical_timestamp')
    try:
        result = datetime.fromisoformat(value)
        if result.utcoffset() is None:
            raise ValueError
    except (ValueError, TypeError) as error:
        raise ValueError('invalid_practical_timestamp') from error
    return result


def validate_context(value, *, workspace=None):
    value = _object(value, {'revision', 'cwd', 'environment'}, code='invalid_practical_context')
    if type(value['revision']) is not int or value['revision'] < 0:
        raise ValueError('invalid_practical_context_revision')
    _path(value['cwd'])
    value['environment'] = _environment(value['environment'])
    if workspace is not None:
        _path(workspace)
        if not PurePosixPath(value['cwd']).is_relative_to(workspace):
            raise ValueError('practical_context_outside_workspace')
    return value


def validate_predicate(value):
    value = _object(value, code='invalid_practical_predicate')
    kind = value.get('kind')
    if kind == 'requested_job_outputs' and 'output_roles' in value:
        from .flux_balance_request_binding import OUTPUT_ROLES
        from .macs2_peak_request_binding import OUTPUT_ROLES as MACS2_ROLES
        if set(value) != {'kind', 'output_roles'} or not set(_strings(
                value['output_roles'], nonempty=True, unique=True)) <= set(OUTPUT_ROLES) | set(MACS2_ROLES) | set(LUMPY_OUTPUT_ROLES):
            raise ValueError('invalid_practical_flux_balance_output_roles')
        return value
    if kind not in PREDICATE_FIELDS or set(value) != PREDICATE_FIELDS[kind]:
        raise ValueError('invalid_practical_predicate')
    if 'path' in value:
        _path(value['path'])
    if kind == 'context_environment':
        _environment({value['name']: value['value']})
    if kind == 'path_exists' and value['object_type'] not in {'file', 'directory'}:
        raise ValueError('invalid_practical_predicate')
    if kind == 'file_sha256':
        _sha(value['sha256'])
    if kind == 'command_exit':
        _strings(value['argv'], nonempty=True)
        if type(value['returncode']) is not int:
            raise ValueError('invalid_practical_returncode')
    if kind == 'requested_job_outputs':
        for path in _strings(value['output_paths'], nonempty=True, unique=True):
            _path(path)
    return value


def validate_assignment(value):
    value = _object(value, code='invalid_practical_assignment')
    required = {'version', 'assignment_id', 'resource_kind', 'workspace',
        'endpoint', 'requested_job', 'progress_requirements', 'completion_keys',
        'initial_context', 'inventory_snapshot', 'constraints'}
    if not required <= set(value) or set(value) - required - {
            'launch_instructions', 'resource_id', 'native_flux_balance_execution'}:
        raise ValueError('invalid_practical_assignment')
    if 'resource_id' in value and not _text(value['resource_id']):
        raise ValueError('invalid_practical_resource_id')
    if 'launch_instructions' in value:
        value['launch_instructions'] = validate_selection(value['launch_instructions'])
    if (value['version'] != ASSIGNMENT_VERSION or not _text(value['assignment_id'])
            or value['resource_kind'] not in {'local', 'hpc'}
            or value['endpoint'] not in {'usable_handoff', 'completed_job_outputs'}):
        raise ValueError('invalid_practical_assignment')
    _path(value['workspace'])
    job = _object(value['requested_job'], code='invalid_practical_job')
    if 'native_flux_balance_execution' in value:
        if ('native_flux_balance' not in job or value['native_flux_balance_execution'] != {
                'version': 'flux_balance_execution_selection_v1',
                'environment_realization': 'operation_scoped_tmp_and_cache_v1'}):
            raise ValueError('fba_environment_selection_invalid')
    if 'native_blast_utility' in job:
        from .native_blast_utility_contracts import validate_native_blast_utility_requested_job
        job = validate_native_blast_utility_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_utility_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_utility_resource_identity_required')
    elif 'native_blast_masking' in job:
        from .native_blast_masking_contracts import validate_native_blast_masking_requested_job
        job = validate_native_blast_masking_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_masking_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_masking_resource_identity_required')
    elif 'native_flux_balance' in job:
        from .native_flux_balance_contracts import validate_flux_balance_requested_job
        job = validate_flux_balance_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_flux_balance_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_flux_balance_resource_identity_required')
    elif 'native_fluorescence' in job:
        from .native_fluorescence_contracts import validate_fluorescence_requested_job
        job = validate_fluorescence_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_fluorescence_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_fluorescence_resource_identity_required')
    elif 'native_expression_nmf' in job:
        from .native_expression_nmf_contracts import validate_expression_nmf_requested_job
        job = validate_expression_nmf_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_expression_nmf_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_expression_nmf_resource_identity_required')
    elif 'native_lumpy' in job:
        from .native_lumpy_execution import validate_lumpy_requested_job
        job = validate_lumpy_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_lumpy_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_lumpy_resource_identity_required')
    elif 'native_macs2_peak' in job:
        from .native_macs2_peak_execution import validate_macs2_peak_requested_job
        job = validate_macs2_peak_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_macs2_peak_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_macs2_peak_resource_identity_required')
    elif 'native_atac_differential' in job:
        from .native_atac_differential_contracts import validate_atac_requested_job
        job = validate_atac_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_atac_differential_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_atac_differential_resource_identity_required')
    elif 'native_chromatin_interactions' in job:
        from .native_chromatin_interaction_contracts import validate_chromatin_requested_job
        job = validate_chromatin_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_chromatin_interactions_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_chromatin_interactions_resource_identity_required')
    elif 'native_genomic_overlap' in job:
        from .native_genomic_overlap_contracts import validate_genomic_overlap_requested_job
        job = validate_genomic_overlap_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_genomic_overlap_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_genomic_overlap_resource_identity_required')
    elif 'native_protein_structure' in job:
        from .native_protein_structure_contracts import validate_protein_structure_requested_job
        job = validate_protein_structure_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_protein_structure_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_protein_structure_resource_identity_required')
    elif 'native_rna_structure' in job:
        from .native_rna_structure_contracts import validate_rna_structure_requested_job
        job = validate_rna_structure_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_rna_structure_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_rna_structure_resource_identity_required')
    elif 'native_blast_standard_database' in job:
        from .native_blast_standard_database_contracts import validate_standard_blast_database_requested_job
        job = validate_standard_blast_database_requested_job(job)
        if value['resource_kind'] != 'hpc':
            raise ValueError('native_blast_standard_database_hpc_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_standard_database_resource_identity_required')
    elif 'native_blast_database' in job:
        from .native_blast_database_contracts import validate_native_blast_database_requested_job
        job = validate_native_blast_database_requested_job(job)
        if value['resource_kind'] != 'hpc':
            raise ValueError('native_blast_database_hpc_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_database_resource_identity_required')
    elif 'native_blast' in job:
        from .native_blast_contracts import validate_native_blast_requested_job
        job = validate_native_blast_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_resource_binding_unfinished:' + value['resource_kind'])
        if not value.get('resource_id'):
            raise ValueError('native_blast_resource_identity_required')
    elif 'native_hmmer' in job:
        from .native_hmmer_contracts import validate_native_hmmer_requested_job
        job = validate_native_hmmer_requested_job(job)
    elif 'native_hmmer_preparation' in job:
        from .native_hmmer_preparation_contracts import validate_native_hmmer_preparation_requested_job
        job = validate_native_hmmer_preparation_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_hmmer_preparation_resource_binding_unfinished:' + value['resource_kind'])
        if not value.get('resource_id'):
            raise ValueError('native_hmmer_preparation_resource_identity_required')
    elif 'native_infernal' in job:
        from .native_infernal_contracts import validate_native_infernal_requested_job
        job = validate_native_infernal_requested_job(job)
    elif 'native_infernal_preparation' in job:
        from .native_infernal_preparation_contracts import validate_native_infernal_preparation_requested_job
        job = validate_native_infernal_preparation_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_infernal_preparation_resource_binding_unfinished:' + value['resource_kind'])
    elif set(job) != {'argv', 'environment'}:
        raise ValueError('invalid_practical_job')
    _strings(job['argv'], nonempty=True)
    _environment(job['environment'])
    value['initial_context'] = validate_context(value['initial_context'], workspace=value['workspace'])
    if value['initial_context']['revision'] != 0:
        raise ValueError('practical_initial_context_requires_revision_zero')
    _object(value['inventory_snapshot'], code='invalid_practical_inventory_snapshot')
    _object(value['constraints'], code='invalid_practical_constraints')
    if not isinstance(value['progress_requirements'], list):
        raise ValueError('invalid_practical_requirements')
    keys = set()
    requirements = []
    for raw in value['progress_requirements']:
        requirement = _object(raw, {'key', 'credit', 'predicate'}, code='invalid_practical_requirement')
        credit = requirement['credit']
        try:
            valid_credit = type(credit) in (int, float) and math.isfinite(credit) and credit >= 0
        except OverflowError:
            valid_credit = False
        if (not _text(requirement['key']) or requirement['key'] in keys
                or not valid_credit):
            raise ValueError('invalid_practical_requirement')
        requirement['predicate'] = validate_predicate(requirement['predicate'])
        if 'output_roles' in requirement['predicate']:
            if 'native_lumpy' in job:
                if not set(requirement['predicate']['output_roles']) <= set(LUMPY_OUTPUT_ROLES):
                    raise ValueError('invalid_practical_lumpy_output_roles')
            elif 'native_macs2_peak' in job:
                from .macs2_peak_request_binding import OUTPUT_ROLES
                if not set(requirement['predicate']['output_roles']) <= set(OUTPUT_ROLES):
                    raise ValueError('invalid_practical_macs2_peak_output_roles')
            elif 'native_flux_balance' in job:
                from .flux_balance_request_binding import OUTPUT_ROLES
                if not set(requirement['predicate']['output_roles']) <= set(OUTPUT_ROLES):
                    raise ValueError('invalid_practical_flux_balance_output_roles')
            else:
                raise ValueError('practical_flux_balance_output_roles_require_fba')
        keys.add(requirement['key'])
        requirements.append(requirement)
    value['progress_requirements'] = requirements
    completion = _strings(value['completion_keys'], nonempty=True, unique=True)
    if not set(completion) <= keys:
        raise ValueError('unknown_practical_completion_key')
    endpoint_kind = ('requested_job_handoff' if value['endpoint'] == 'usable_handoff'
        else 'requested_job_outputs')
    if not any(item['key'] in completion and item['predicate']['kind'] == endpoint_kind
            for item in requirements):
        raise ValueError('practical_completion_requires_requested_job_endpoint')
    # Overflow in the total is invalid even when every individual credit is finite.
    try:
        total = math.fsum(item['credit'] for item in requirements)
    except OverflowError as error:
        raise ValueError('nonfinite_practical_credit_total') from error
    if not math.isfinite(total):
        raise ValueError('nonfinite_practical_credit_total')
    return value


def validate_outcome(value):
    """Qualify the closed factual subrecord of an otherwise operation-owned outcome."""
    value = _object(value, code='invalid_practical_outcome')
    facts = _object(value.get('facts', {}), code='invalid_practical_outcome_facts')
    if set(facts) - {'paths', 'command', 'requested_job'}:
        raise ValueError('invalid_practical_outcome_facts')
    paths = facts.get('paths', [])
    if not isinstance(paths, list):
        raise ValueError('invalid_practical_path_facts')
    seen = set()
    for path in paths:
        _object(path, {'path', 'exists', 'object_type', 'sha256'}, code='invalid_practical_path_fact')
        _path(path['path'])
        if (path['path'] in seen or type(path['exists']) is not bool
                or path['object_type'] not in {'file', 'directory', 'other', 'missing'}
                or path['exists'] != (path['object_type'] != 'missing')):
            raise ValueError('invalid_practical_path_fact')
        seen.add(path['path'])
        if path['sha256'] is not None:
            _sha(path['sha256'])
            if not path['exists'] or path['object_type'] != 'file':
                raise ValueError('invalid_practical_path_fact')
    for name in ('command', 'requested_job'):
        if name not in facts:
            continue
        fields = {'argv', 'environment', 'returncode', 'execution_id'}
        if name == 'requested_job':
            fields |= {'requested_job_sha256', 'resource_kind', 'status', 'output_paths', 'handoff'}
        item = _object(facts[name], fields, code='invalid_practical_' + name + '_fact')
        _strings(item['argv'], nonempty=True)
        _environment(item['environment'])
        if not _text(item['execution_id']) or item['returncode'] is not None and type(item['returncode']) is not int:
            raise ValueError('invalid_practical_' + name + '_fact')
        if name == 'requested_job':
            _sha(item['requested_job_sha256'])
            if (item['resource_kind'] not in {'local', 'hpc'}
                    or item['status'] not in {'submitted', 'running', 'completed', 'failed', 'unknown'}):
                raise ValueError('invalid_practical_requested_job_fact')
            if item['status'] == 'completed' and item['returncode'] is None:
                raise ValueError('completed_practical_job_requires_returncode')
            for path in _strings(item['output_paths'], unique=True):
                _path(path)
            if item['handoff'] is not None:
                handoff = _object(item['handoff'], {'execution_id', 'monitor_operation', 'results_operation'},
                    code='invalid_practical_job_handoff')
                if (any(not _text(part) for part in handoff.values())
                        or handoff['execution_id'] != item['execution_id']):
                    raise ValueError('invalid_practical_job_handoff')
    if 'evidence_refs' in value:
        _strings(value['evidence_refs'], unique=True)
    detail = value.get('native_outcome')
    if isinstance(detail, dict) and 'native_blast_utility_validation' in detail:
        _validate_utility_validation(detail)
    value['facts'] = facts
    return value


def _validate_utility_validation(detail):
    """Check saved executor evidence, without rereading files or running work."""
    from .native_blast_utility_contracts import (
        validate_native_blast_utility_bundle, validate_native_blast_utility_plan)
    plan = validate_native_blast_utility_plan(detail.get('native_blast_utility_plan'))
    owner = plan['identity']
    if (detail.get('attempt_id') != owner['attempt_id']
            or detail.get('attempt_operation_key') != owner['operation_key']):
        raise ValueError('native_blast_utility_validation_attempt_conflict')
    record = _object(detail['native_blast_utility_validation'], {
        'version', 'bundle', 'bundle_sha256', 'files_validated', 'failure_code'},
        code='native_blast_utility_validation_invalid')
    if (record['version'] != 'native_blast_utility_validation_v1'
            or type(record['files_validated']) is not bool
            or record['failure_code'] not in {None, 'sealed_bundle_unavailable',
                'original_bundle_invalid', 'original_bundle_files_invalid'}):
        raise ValueError('native_blast_utility_validation_invalid')
    if record['bundle'] is None:
        if (record['bundle_sha256'] is not None or record['files_validated']
                or record['failure_code'] not in {'sealed_bundle_unavailable', 'original_bundle_invalid'}):
            raise ValueError('native_blast_utility_validation_invalid')
    else:
        bundle = validate_native_blast_utility_bundle(record['bundle'], plan)
        if (record['bundle_sha256'] != digest(bundle)
                or record['failure_code'] != (None if record['files_validated']
                    else 'original_bundle_files_invalid')):
            raise ValueError('native_blast_utility_validation_invalid')
    return plan, record


def _utility_completed_outputs(assignment, outcome, job):
    """Return actual sealed file paths only when the original utility succeeded."""
    detail = outcome.get('native_outcome') or {}
    if 'native_blast_utility_validation' not in detail:
        return None
    plan, record = _validate_utility_validation(detail)
    owner, bundle = plan['identity'], record['bundle']
    native = detail.get('observation', detail)
    if (plan['requested_job'] != assignment['requested_job']
            or owner['resource_id'] != assignment.get('resource_id')
            or owner['requested_job_sha256'] != job['requested_job_sha256']
            or owner['execution_id'] != job['execution_id']
            or native.get('metadata', {}).get('policy') != plan['policy']
            or not native.get('terminal') or native.get('metadata', {}).get('native_returncode') != 0
            or not record['files_validated'] or bundle is None
            or not bundle['started'] or bundle['returncode'] != 0
            or not bundle['writer_closed'] or not bundle['inventory_complete'] or bundle['failures']):
        return None
    root = PurePosixPath(plan['attempt_directory'])
    return {str(root / 'bundle.json'), *(str(root / row['relative_path'])
        for row in bundle['artifacts'] if row['sha256'] is not None and row['completeness'] == 'complete')}


def _job_matches(assignment, job, tool_name):
    return bool(job is not None and tool_name in JOB_TOOLS
        and job['requested_job_sha256'] == digest(assignment['requested_job'])
        and job['argv'] == assignment['requested_job']['argv']
        and job['environment'] == assignment['requested_job']['environment']
        and job['resource_kind'] == assignment['resource_kind'])


def flux_balance_role_paths(assignment, job, roles):
    """Realize selected roles only after the actual native execution is known."""
    from .native_flux_balance_contracts import ATTEMPT_DIRECTORY_NAME, flux_balance_output_files
    if 'native_flux_balance' not in assignment['requested_job'] or job is None:
        raise ValueError('practical_flux_balance_output_roles_require_fba')
    execution = PurePosixPath(job['execution_id'])
    if (not execution.is_absolute() or execution.name != 'native.json'
            or '..' in execution.parts or str(execution) != job['execution_id']):
        raise ValueError('practical_flux_balance_original_execution_required')
    root = execution.parent / ATTEMPT_DIRECTORY_NAME
    declared = {row['role']: str(root / row['relative_path']) for row in
        flux_balance_output_files(assignment['requested_job']['native_flux_balance'])}
    if not set(roles) <= set(declared):
        raise ValueError('invalid_practical_flux_balance_output_roles')
    return [declared[role] for role in roles]


def lumpy_role_outputs(request, roles):
    """Resolve only explicit LUMPY roles against its declared ordered outputs."""
    from .native_lumpy_execution import lumpy_output_files
    selected = _strings(roles, nonempty=True, unique=True)
    if not set(selected) <= set(LUMPY_OUTPUT_ROLES):
        raise ValueError('invalid_practical_lumpy_output_roles')
    outputs = lumpy_output_files(request)
    result = []
    for role in selected:
        matches = [row for row in outputs if row['role'] == (
            'bam_header' if role == 'bam_headers' else role)]
        if not matches or role != 'bam_headers' and len(matches) != 1:
            raise ValueError('native_lumpy_declared_output_roles_conflict')
        result.extend(deepcopy(matches))
    return result


def requested_job_role_paths(assignment, job, roles):
    """Resolve semantic output roles against the observed original execution."""
    if 'native_lumpy' in assignment['requested_job']:
        from .native_lumpy_execution import ATTEMPT_DIRECTORY_NAME
        if job is None:
            raise ValueError('practical_lumpy_original_execution_required')
        execution = PurePosixPath(job['execution_id'])
        if (not execution.is_absolute() or execution.name != 'native.json'
                or '..' in execution.parts or str(execution) != job['execution_id']):
            raise ValueError('practical_lumpy_original_execution_required')
        root = execution.parent / ATTEMPT_DIRECTORY_NAME
        return [str(root / row['relative_path']) for row in lumpy_role_outputs(
            assignment['requested_job']['native_lumpy']['request'], roles)]
    if 'native_macs2_peak' not in assignment['requested_job']:
        return flux_balance_role_paths(assignment, job, roles)
    from .native_macs2_peak_execution import ATTEMPT_DIRECTORY_NAME, macs2_peak_output_files
    if job is None:
        raise ValueError('practical_macs2_peak_original_execution_required')
    execution = PurePosixPath(job['execution_id'])
    if (not execution.is_absolute() or execution.name != 'native.json'
            or '..' in execution.parts or str(execution) != job['execution_id']):
        raise ValueError('practical_macs2_peak_original_execution_required')
    root = execution.parent / ATTEMPT_DIRECTORY_NAME
    declared = {row['role']: str(root / row['relative_path']) for row in
        macs2_peak_output_files(assignment['requested_job']['native_macs2_peak']['request'])}
    if not set(roles) <= set(declared):
        raise ValueError('invalid_practical_macs2_peak_output_roles')
    return [declared[role] for role in roles]


def assess_validations(assignment, outcome, context, *, checked_at=None, tool_name=None):
    """Assess original requirements actually observed by this action, without I/O.

    Absence of a fact is not a negative observation. Context is always supplied;
    paths and native outcomes qualify only the requirements they actually test.
    """
    assignment = validate_assignment(assignment)
    outcome = validate_outcome(outcome)
    context = validate_context(context, workspace=assignment['workspace'])
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    timestamp(checked_at)
    facts = outcome['facts']
    paths = {item['path']: item for item in facts.get('paths', [])}
    values = []
    for requirement in assignment['progress_requirements']:
        predicate = requirement['predicate']
        kind = predicate['kind']
        source, observed, satisfied = 'outcome', None, False
        if kind == 'context_cwd':
            source, observed = 'context', {'cwd': context['cwd']}
            satisfied = context['cwd'] == predicate['path']
        elif kind == 'context_environment':
            source = 'context'
            observed = {'name': predicate['name'], 'value': context['environment'].get(predicate['name'])}
            satisfied = observed['value'] == predicate['value']
        elif kind in {'path_exists', 'file_sha256'}:
            observed = paths.get(predicate['path'])
            if observed is None:
                continue
            if observed is not None and observed['exists']:
                satisfied = (observed['object_type'] == predicate['object_type'] if kind == 'path_exists'
                    else observed['object_type'] == 'file' and observed['sha256'] == predicate['sha256'])
        elif kind == 'command_exit':
            observed = facts.get('command')
            if observed is None or observed['argv'] != predicate['argv']:
                continue
            satisfied = bool(observed is not None and observed['argv'] == predicate['argv']
                and observed['returncode'] == predicate['returncode'])
        elif kind == 'requested_job_handoff':
            observed = facts.get('requested_job')
            if observed is None:
                continue
            satisfied = (_job_matches(assignment, observed, tool_name)
                and observed['status'] in {'submitted', 'running', 'completed'}
                and observed['handoff'] is not None)
            if 'native_blast_utility' in assignment['requested_job'] and observed['status'] == 'completed':
                satisfied = satisfied and _utility_completed_outputs(assignment, outcome, observed) is not None
        elif kind == 'requested_job_outputs':
            job = facts.get('requested_job')
            if job is None:
                continue
            requested_paths = (requested_job_role_paths(assignment, job, predicate['output_roles'])
                if 'output_roles' in predicate else predicate['output_paths'])
            selected_paths = [paths.get(path) for path in requested_paths]
            observed = {'requested_job': job, 'paths': selected_paths}
            satisfied = (_job_matches(assignment, job, tool_name)
                and job['status'] == 'completed' and job['returncode'] == 0
                and set(requested_paths) <= set(job['output_paths'])
                and all(path is not None and path['exists'] and path['object_type'] == 'file'
                    for path in selected_paths))
            if 'native_blast_utility' in assignment['requested_job']:
                qualified = _utility_completed_outputs(assignment, outcome, job)
                satisfied = satisfied and qualified is not None and set(predicate['output_paths']) <= qualified
                observed['native_blast_utility_validation'] = deepcopy(
                    (outcome.get('native_outcome') or {}).get('native_blast_utility_validation'))
        values.append({'key': requirement['key'], 'satisfied': bool(satisfied),
            'predicate': deepcopy(predicate), 'evidence_refs': list(outcome.get('evidence_refs', [])),
            'evidence': {'source': source, 'value': deepcopy(observed)}, 'checked_at': checked_at})
    return values


def validate_validations(value, assignment, outcome, context, *, tool_name=None):
    """Check supplied assessments against exact actual facts, preserving their times."""
    if not isinstance(value, list):
        raise ValueError('invalid_practical_validations')
    expected = {item['key']: item for item in assess_validations(assignment, outcome, context,
        checked_at='1970-01-01T00:00:00+00:00', tool_name=tool_name)}
    result, seen = [], set()
    for raw in value:
        item = validate_validation(raw)
        if item['key'] not in expected or item['key'] in seen:
            raise ValueError('invalid_practical_validation')
        timestamp(item['checked_at'])
        compare = {**item, 'checked_at': expected[item['key']]['checked_at']}
        if canonical(compare) != canonical(expected[item['key']]):
            raise ValueError('practical_validation_does_not_match_actual_facts')
        seen.add(item['key'])
        result.append(item)
    if seen != set(expected):
        raise ValueError('practical_validation_assessment_missing')
    return result


def validate_validation(value):
    """Check closed validation shape; source qualification also needs the action."""
    value = _object(value, {'key', 'satisfied', 'predicate', 'evidence_refs', 'evidence', 'checked_at'},
        code='invalid_practical_validation')
    if not _text(value['key']) or type(value['satisfied']) is not bool:
        raise ValueError('invalid_practical_validation')
    validate_predicate(value['predicate'])
    _strings(value['evidence_refs'], unique=True)
    evidence = _object(value['evidence'], {'source', 'value'}, code='invalid_practical_validation_evidence')
    if evidence['source'] not in {'context', 'outcome'}:
        raise ValueError('invalid_practical_validation_evidence')
    timestamp(value['checked_at'])
    return value


def validate_receipt(value):
    value = _object(value, RECEIPT_FIELDS, code='invalid_practical_action_receipt')
    if value['version'] != RECEIPT_VERSION:
        raise ValueError('invalid_practical_action_receipt')
    for key in ('run_id', 'episode_id', 'operation_key', 'tool_name'):
        if not _text(value[key]):
            raise ValueError('invalid_practical_action_receipt')
    _sha(value['assignment_sha256'])
    _object(value['arguments'])
    validate_context(value['context_before'])
    validate_context(value['context_after'])
    validate_outcome(value['outcome'])
    if timestamp(value['finished_at']) < timestamp(value['started_at']):
        raise ValueError('invalid_practical_action_receipt_time_order')
    if not isinstance(value['validations'], list):
        raise ValueError('invalid_practical_validations')
    seen = set()
    for item in value['validations']:
        validate_validation(item)
        if item['key'] in seen:
            raise ValueError('duplicate_practical_validation_key')
        seen.add(item['key'])
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


__all__ = ['ASSIGNMENT_VERSION', 'RECEIPT_VERSION', 'COMPLETION_VERSION', 'JOB_TOOLS',
    'ASSIGNMENT_SCHEMA', 'CONTEXT_SCHEMA', 'REQUESTED_JOB_SCHEMA', 'GENERIC_REQUESTED_JOB_SCHEMA', 'PREDICATE_SCHEMA',
    'REQUIREMENT_SCHEMA', 'VALIDATION_SCHEMA', 'RECEIPT_SCHEMA', 'COMPLETION_PROOF_SCHEMA',
    'canonical', 'digest', 'validate_assignment', 'validate_context', 'validate_predicate',
    'validate_outcome', 'assess_validations', 'validate_validations', 'validate_receipt',
    'validate_validation', 'validate_completion_proof', 'LUMPY_OUTPUT_ROLES', 'lumpy_role_outputs']
