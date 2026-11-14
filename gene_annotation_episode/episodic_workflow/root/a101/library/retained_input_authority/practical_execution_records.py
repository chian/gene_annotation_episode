"""Closed factual contracts for selected practical execution actions.

These functions inspect supplied records only. They execute no command, inspect
no filesystem and make no episode decision. Facts come from caller-bound real
operations; validation compares those facts with the original assignment.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a101.practical_execution_records import ASSIGNMENT_VERSION, JOB_TOOLS, PREDICATE_FIELDS, RECEIPT_FIELDS, RECEIPT_VERSION, _environment, _job_matches, _json, _object, _path, _sha, _strings, _text, _utility_completed_outputs, _validate_utility_validation, canonical, digest, terminal_job_matches, timestamp, validate_context, validate_outcome
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from gene_annotation_episode.episodic_workflow.root.a101.launch_instructions import validate_selection
LUMPY_OUTPUT_ROLES = ('vcf', 'stderr', 'seal', 'bam_headers')

def validate_predicate(value):
    value = _object(value, code='invalid_practical_predicate')
    kind = value.get('kind')
    if kind == 'requested_job_outputs' and 'output_roles' in value:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.flux_balance_request_binding import OUTPUT_ROLES
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.macs2_peak_request_binding import OUTPUT_ROLES as MACS2_ROLES
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
        from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_utility_contracts import validate_native_blast_utility_requested_job
        job = validate_native_blast_utility_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_utility_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_utility_resource_identity_required')
    elif 'native_blast_masking' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_masking_contracts import validate_native_blast_masking_requested_job
        job = validate_native_blast_masking_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_masking_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_masking_resource_identity_required')
    elif 'native_flux_balance' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_flux_balance_contracts import validate_flux_balance_requested_job
        job = validate_flux_balance_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_flux_balance_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_flux_balance_resource_identity_required')
    elif 'native_fluorescence' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_fluorescence_contracts import validate_fluorescence_requested_job
        job = validate_fluorescence_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_fluorescence_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_fluorescence_resource_identity_required')
    elif 'native_expression_nmf' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_expression_nmf_contracts import validate_expression_nmf_requested_job
        job = validate_expression_nmf_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_expression_nmf_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_expression_nmf_resource_identity_required')
    elif 'native_lumpy' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_lumpy_execution import validate_lumpy_requested_job
        job = validate_lumpy_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_lumpy_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_lumpy_resource_identity_required')
    elif 'native_macs2_peak' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_macs2_peak_execution import validate_macs2_peak_requested_job
        job = validate_macs2_peak_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_macs2_peak_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_macs2_peak_resource_identity_required')
    elif 'native_atac_differential' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_atac_differential_contracts import validate_atac_requested_job
        job = validate_atac_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_atac_differential_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_atac_differential_resource_identity_required')
    elif 'native_chromatin_interactions' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_chromatin_interaction_contracts import validate_chromatin_requested_job
        job = validate_chromatin_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_chromatin_interactions_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_chromatin_interactions_resource_identity_required')
    elif 'native_genomic_overlap' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_genomic_overlap_contracts import validate_genomic_overlap_requested_job
        job = validate_genomic_overlap_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_genomic_overlap_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_genomic_overlap_resource_identity_required')
    elif 'native_protein_structure' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_protein_structure_contracts import validate_protein_structure_requested_job
        job = validate_protein_structure_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_protein_structure_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_protein_structure_resource_identity_required')
    elif 'native_rna_structure' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_rna_structure_contracts import validate_rna_structure_requested_job
        job = validate_rna_structure_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_rna_structure_local_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_rna_structure_resource_identity_required')
    elif 'native_blast_standard_database' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_standard_database_contracts import validate_standard_blast_database_requested_job
        job = validate_standard_blast_database_requested_job(job)
        if value['resource_kind'] != 'hpc':
            raise ValueError('native_blast_standard_database_hpc_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_standard_database_resource_identity_required')
    elif 'native_blast_database' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_contracts import validate_native_blast_database_requested_job
        job = validate_native_blast_database_requested_job(job)
        if value['resource_kind'] != 'hpc':
            raise ValueError('native_blast_database_hpc_resource_required')
        if not value.get('resource_id'):
            raise ValueError('native_blast_database_resource_identity_required')
    elif 'native_blast' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_contracts import validate_native_blast_requested_job
        job = validate_native_blast_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_blast_resource_binding_unfinished:' + value['resource_kind'])
        if not value.get('resource_id'):
            raise ValueError('native_blast_resource_identity_required')
    elif 'native_hmmer' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.native_hmmer_contracts import validate_native_hmmer_requested_job
        job = validate_native_hmmer_requested_job(job)
    elif 'native_hmmer_preparation' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.native_hmmer_preparation_contracts import validate_native_hmmer_preparation_requested_job
        job = validate_native_hmmer_preparation_requested_job(job)
        if value['resource_kind'] != 'local':
            raise ValueError('native_hmmer_preparation_resource_binding_unfinished:' + value['resource_kind'])
        if not value.get('resource_id'):
            raise ValueError('native_hmmer_preparation_resource_identity_required')
    elif 'native_infernal' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_infernal_contracts import validate_native_infernal_requested_job
        job = validate_native_infernal_requested_job(job)
    elif 'native_infernal_preparation' in job:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_infernal_preparation_contracts import validate_native_infernal_preparation_requested_job
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
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.macs2_peak_request_binding import OUTPUT_ROLES
                if not set(requirement['predicate']['output_roles']) <= set(OUTPUT_ROLES):
                    raise ValueError('invalid_practical_macs2_peak_output_roles')
            elif 'native_flux_balance' in job:
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.flux_balance_request_binding import OUTPUT_ROLES
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

def flux_balance_role_paths(assignment, job, roles):
    """Realize selected roles only after the actual native execution is known."""
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_flux_balance_contracts import ATTEMPT_DIRECTORY_NAME, flux_balance_output_files
    if 'native_flux_balance' not in assignment['requested_job'] or job is None:
        raise ValueError('practical_flux_balance_output_roles_require_fba')
    execution = PurePosixPath(job['execution_id'])
    if not execution.is_absolute() or execution.name != 'native.json' or '..' in execution.parts or (str(execution) != job['execution_id']):
        raise ValueError('practical_flux_balance_original_execution_required')
    root = execution.parent / ATTEMPT_DIRECTORY_NAME
    declared = {row['role']: str(root / row['relative_path']) for row in flux_balance_output_files(assignment['requested_job']['native_flux_balance'])}
    if not set(roles) <= set(declared):
        raise ValueError('invalid_practical_flux_balance_output_roles')
    return [declared[role] for role in roles]

def lumpy_role_outputs(request, roles):
    """Resolve only explicit LUMPY roles against its declared ordered outputs."""
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_lumpy_execution import lumpy_output_files
    selected = _strings(roles, nonempty=True, unique=True)
    if not set(selected) <= set(LUMPY_OUTPUT_ROLES):
        raise ValueError('invalid_practical_lumpy_output_roles')
    outputs = lumpy_output_files(request)
    result = []
    for role in selected:
        matches = [row for row in outputs if row['role'] == ('bam_header' if role == 'bam_headers' else role)]
        if not matches or (role != 'bam_headers' and len(matches) != 1):
            raise ValueError('native_lumpy_declared_output_roles_conflict')
        result.extend(deepcopy(matches))
    return result

def requested_job_role_paths(assignment, job, roles):
    """Resolve semantic output roles against the observed original execution."""
    if 'native_lumpy' in assignment['requested_job']:
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_lumpy_execution import ATTEMPT_DIRECTORY_NAME
        if job is None:
            raise ValueError('practical_lumpy_original_execution_required')
        execution = PurePosixPath(job['execution_id'])
        if not execution.is_absolute() or execution.name != 'native.json' or '..' in execution.parts or (str(execution) != job['execution_id']):
            raise ValueError('practical_lumpy_original_execution_required')
        root = execution.parent / ATTEMPT_DIRECTORY_NAME
        return [str(root / row['relative_path']) for row in lumpy_role_outputs(assignment['requested_job']['native_lumpy']['request'], roles)]
    if 'native_macs2_peak' not in assignment['requested_job']:
        return flux_balance_role_paths(assignment, job, roles)
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_macs2_peak_execution import ATTEMPT_DIRECTORY_NAME, macs2_peak_output_files
    if job is None:
        raise ValueError('practical_macs2_peak_original_execution_required')
    execution = PurePosixPath(job['execution_id'])
    if not execution.is_absolute() or execution.name != 'native.json' or '..' in execution.parts or (str(execution) != job['execution_id']):
        raise ValueError('practical_macs2_peak_original_execution_required')
    root = execution.parent / ATTEMPT_DIRECTORY_NAME
    declared = {row['role']: str(root / row['relative_path']) for row in macs2_peak_output_files(assignment['requested_job']['native_macs2_peak']['request'])}
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
        source, observed, satisfied = ('outcome', None, False)
        if kind == 'context_cwd':
            source, observed = ('context', {'cwd': context['cwd']})
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
                satisfied = observed['object_type'] == predicate['object_type'] if kind == 'path_exists' else observed['object_type'] == 'file' and observed['sha256'] == predicate['sha256']
        elif kind == 'command_exit':
            observed = facts.get('command')
            if observed is None or observed['argv'] != predicate['argv']:
                continue
            satisfied = bool(observed is not None and observed['argv'] == predicate['argv'] and (observed['returncode'] == predicate['returncode']))
        elif kind == 'requested_job_handoff':
            observed = facts.get('requested_job')
            if observed is None:
                continue
            satisfied = _job_matches(assignment, observed, tool_name, outcome) and observed['status'] in {'submitted', 'running', 'completed'} and (observed['handoff'] is not None)
            if 'native_blast_utility' in assignment['requested_job'] and observed['status'] == 'completed':
                satisfied = satisfied and _utility_completed_outputs(assignment, outcome, observed) is not None
        elif kind == 'requested_job_outputs':
            job = facts.get('requested_job')
            if job is None:
                continue
            requested_paths = requested_job_role_paths(assignment, job, predicate['output_roles']) if 'output_roles' in predicate else predicate['output_paths']
            selected_paths = [paths.get(path) for path in requested_paths]
            observed = {'requested_job': job, 'paths': selected_paths}
            satisfied = _job_matches(assignment, job, tool_name, outcome) and job['status'] == 'completed' and (job['returncode'] == 0) and (set(requested_paths) <= set(job['output_paths'])) and all((path is not None and path['exists'] and (path['object_type'] == 'file') for path in selected_paths))
            if 'native_blast_utility' in assignment['requested_job']:
                qualified = _utility_completed_outputs(assignment, outcome, job)
                satisfied = satisfied and qualified is not None and (set(predicate['output_paths']) <= qualified)
                observed['native_blast_utility_validation'] = deepcopy((outcome.get('native_outcome') or {}).get('native_blast_utility_validation'))
        values.append({'key': requirement['key'], 'satisfied': bool(satisfied), 'predicate': deepcopy(predicate), 'evidence_refs': list(outcome.get('evidence_refs', [])), 'evidence': {'source': source, 'value': deepcopy(observed)}, 'checked_at': checked_at})
    return values

def validate_validations(value, assignment, outcome, context, *, tool_name=None):
    """Check supplied assessments against exact actual facts, preserving their times."""
    if not isinstance(value, list):
        raise ValueError('invalid_practical_validations')
    expected = {item['key']: item for item in assess_validations(assignment, outcome, context, checked_at='1970-01-01T00:00:00+00:00', tool_name=tool_name)}
    result, seen = ([], set())
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
    value = _object(value, {'key', 'satisfied', 'predicate', 'evidence_refs', 'evidence', 'checked_at'}, code='invalid_practical_validation')
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
