from __future__ import annotations
from collections.abc import Mapping
import json
import math
from pathlib import PurePosixPath
import re
from ...launch_instructions import validate_selection
ASSIGNMENT_VERSION = 'practical_assignment_v1'
LUMPY_OUTPUT_ROLES = ('vcf', 'stderr', 'seal', 'bam_headers')
PREDICATE_FIELDS = {'context_cwd': {'kind', 'path'}, 'context_environment': {'kind', 'name', 'value'}, 'path_exists': {'kind', 'path', 'object_type'}, 'file_sha256': {'kind', 'path', 'sha256'}, 'command_exit': {'kind', 'argv', 'returncode'}, 'requested_job_handoff': {'kind'}, 'requested_job_outputs': {'kind', 'output_paths'}}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

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
    return isinstance(value, str) and bool(value) and ('\x00' not in value)

def _path(value):
    if not _text(value) or not value.startswith('/') or '..' in PurePosixPath(value).parts or (str(PurePosixPath(value)) != value):
        raise ValueError('invalid_practical_absolute_path')
    return value

def _sha(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('invalid_practical_digest')
    return value

def _strings(value, *, nonempty=False, unique=False):
    if not isinstance(value, list) or (nonempty and (not value)) or any((not _text(item) for item in value)) or (unique and len(set(value)) != len(value)):
        raise ValueError('invalid_practical_string_array')
    return value

def _environment(value):
    value = _object(value, code='invalid_practical_environment')
    if any((re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', key) is None or not isinstance(item, str) or '\x00' in item for key, item in value.items())):
        raise ValueError('invalid_practical_environment')
    return value

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
        from ...flux_balance_request_binding import OUTPUT_ROLES
        from ...macs2_peak_request_binding import OUTPUT_ROLES as MACS2_ROLES
        if set(value) != {'kind', 'output_roles'} or not set(_strings(value['output_roles'], nonempty=True, unique=True)) <= set(OUTPUT_ROLES) | set(MACS2_ROLES) | set(LUMPY_OUTPUT_ROLES):
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
    required = {'version', 'assignment_id', 'resource_kind', 'workspace', 'endpoint', 'requested_job', 'progress_requirements', 'completion_keys', 'initial_context', 'inventory_snapshot', 'constraints'}
    if not required <= set(value) or set(value) - required - {'launch_instructions', 'resource_id', 'native_flux_balance_execution', 'scientific_manifest'}:
        raise ValueError('invalid_practical_assignment')
    if 'resource_id' in value and (not _text(value['resource_id'])):
        raise ValueError('invalid_practical_resource_id')
    if 'launch_instructions' in value:
        value['launch_instructions'] = validate_selection(value['launch_instructions'])
    if value['version'] != ASSIGNMENT_VERSION or not _text(value['assignment_id']) or value['resource_kind'] not in {'local', 'hpc'} or (value['endpoint'] not in {'usable_handoff', 'completed_job_outputs'}):
        raise ValueError('invalid_practical_assignment')
    _path(value['workspace'])
    job = _object(value['requested_job'], code='invalid_practical_job')
    if 'scientific_manifest' in value:
        manifest = _object(value['scientific_manifest'], {'path', 'sha256', 'size_bytes', 'format'})
        _path(manifest['path'])
        _sha(manifest['sha256'])
        if type(manifest['size_bytes']) is not int or manifest['size_bytes'] < 0 or value['resource_kind'] != 'hpc' or (not PurePosixPath(manifest['path']).is_relative_to(value['workspace'])) or (not any((key in job and manifest['format'] == key + '_run_plan_v1' for key in ('native_blast_database', 'native_blast_standard_database')))):
            raise ValueError('native_database_scientific_manifest_invalid')
    if 'native_flux_balance_execution' in value:
        if 'native_flux_balance' not in job or value['native_flux_balance_execution'] != {'version': 'flux_balance_execution_selection_v1', 'environment_realization': 'operation_scoped_tmp_and_cache_v1'}:
            raise ValueError('fba_environment_selection_invalid')
    if 'native_blast_utility' in job:
        from ...native_blast_utility_contracts import validate_native_blast_utility_requested_job
        job = validate_native_blast_utility_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_utility_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_utility_resource_identity_required')
    elif 'native_blast_masking' in job:
        from ...native_blast_masking_contracts import validate_native_blast_masking_requested_job
        job = validate_native_blast_masking_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_masking_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_masking_resource_identity_required')
    elif 'native_flux_balance' in job:
        from .historical_native_flux_balance_contracts import validate_flux_balance_requested_job
        job = validate_flux_balance_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_flux_balance_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_flux_balance_resource_identity_required')
    elif 'native_fluorescence' in job:
        from ...native_fluorescence_contracts import validate_fluorescence_requested_job
        job = validate_fluorescence_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_fluorescence_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_fluorescence_resource_identity_required')
    elif 'native_expression_nmf' in job:
        from ...native_expression_nmf_contracts import validate_expression_nmf_requested_job
        job = validate_expression_nmf_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_expression_nmf_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_expression_nmf_resource_identity_required')
    elif 'native_lumpy' in job:
        from gene_annotation_episode.episodic_workflow.root.a107.library.lumpy_request_contracts import validate_lumpy_requested_job
        job = validate_lumpy_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_lumpy_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_lumpy_resource_identity_required')
    elif 'native_macs2_peak' in job:
        from gene_annotation_episode.episodic_workflow.root.a107.library.macs2_request_contracts import validate_macs2_peak_requested_job
        job = validate_macs2_peak_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_macs2_peak_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_macs2_peak_resource_identity_required')
    elif 'native_atac_differential' in job:
        from gene_annotation_episode.episodic_workflow.root.a107.library.atac_execution_contracts import validate_atac_requested_job
        job = validate_atac_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_atac_differential_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_atac_differential_resource_identity_required')
    elif 'native_chromatin_interactions' in job:
        from gene_annotation_episode.episodic_workflow.root.a107.library.chromatin_request_contracts import validate_chromatin_requested_job
        job = validate_chromatin_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_chromatin_interactions_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_chromatin_interactions_resource_identity_required')
    elif 'native_genomic_overlap' in job:
        from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_native_genomic_overlap_contracts import validate_genomic_overlap_requested_job
        job = validate_genomic_overlap_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_genomic_overlap_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_genomic_overlap_resource_identity_required')
    elif 'native_protein_structure' in job:
        from ...native_protein_structure_contracts import validate_protein_structure_requested_job
        job = validate_protein_structure_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_protein_structure_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_protein_structure_resource_identity_required')
    elif 'native_rna_structure' in job:
        from ...native_rna_structure_contracts import validate_rna_structure_requested_job
        job = validate_rna_structure_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_rna_structure_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_rna_structure_resource_identity_required')
    elif 'native_blast_standard_database' in job:
        from ...native_blast_standard_database_contracts import validate_standard_blast_database_requested_job
        job = validate_standard_blast_database_requested_job(job)
        if value['resource_kind'] != 'hpc':
            raise ValueError('native_blast_standard_database_hpc_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_standard_database_resource_identity_required')
    elif 'native_blast_database' in job:
        from ...native_blast_database_contracts import validate_native_blast_database_requested_job
        job = validate_native_blast_database_requested_job(job)
        if value['resource_kind'] != 'hpc':
            raise ValueError('native_blast_database_hpc_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_database_resource_identity_required')
    elif 'native_blast' in job:
        from ...native_blast_contracts import validate_native_blast_requested_job
        job = validate_native_blast_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_resource_binding_unfinished:' + value['resource_kind'])
        if not value.get('resource_id'):
            raise ValueError('native_blast_resource_identity_required')
    elif 'native_hmmer' in job:
        from ...native_hmmer_contracts import validate_native_hmmer_requested_job
        job = validate_native_hmmer_requested_job(job)
    elif 'native_hmmer_preparation' in job:
        from ...native_hmmer_preparation_contracts import validate_native_hmmer_preparation_requested_job
        job = validate_native_hmmer_preparation_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_hmmer_preparation_resource_binding_unfinished:' + value['resource_kind'])
        if not value.get('resource_id'):
            raise ValueError('native_hmmer_preparation_resource_identity_required')
    elif 'native_infernal' in job:
        from ...native_infernal_contracts import validate_native_infernal_requested_job
        job = validate_native_infernal_requested_job(job)
    elif 'native_infernal_preparation' in job:
        from ...native_infernal_preparation_contracts import validate_native_infernal_preparation_requested_job
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
            valid_credit = type(credit) in (int, float) and math.isfinite(credit) and (credit >= 0)
        except OverflowError:
            valid_credit = False
        if not _text(requirement['key']) or requirement['key'] in keys or (not valid_credit):
            raise ValueError('invalid_practical_requirement')
        requirement['predicate'] = validate_predicate(requirement['predicate'])
        if 'output_roles' in requirement['predicate']:
            if 'native_lumpy' in job:
                if not set(requirement['predicate']['output_roles']) <= set(LUMPY_OUTPUT_ROLES):
                    raise ValueError('invalid_practical_lumpy_output_roles')
            elif 'native_macs2_peak' in job:
                from ...macs2_peak_request_binding import OUTPUT_ROLES
                if not set(requirement['predicate']['output_roles']) <= set(OUTPUT_ROLES):
                    raise ValueError('invalid_practical_macs2_peak_output_roles')
            elif 'native_flux_balance' in job:
                from ...flux_balance_request_binding import OUTPUT_ROLES
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
    endpoint_kind = 'requested_job_handoff' if value['endpoint'] == 'usable_handoff' else 'requested_job_outputs'
    if not any((item['key'] in completion and item['predicate']['kind'] == endpoint_kind for item in requirements)):
        raise ValueError('practical_completion_requires_requested_job_endpoint')
    try:
        total = math.fsum((item['credit'] for item in requirements))
    except OverflowError as error:
        raise ValueError('nonfinite_practical_credit_total') from error
    if not math.isfinite(total):
        raise ValueError('nonfinite_practical_credit_total')
    return value
