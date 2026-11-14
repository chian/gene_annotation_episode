"""Actual private job_results tool_actions."""
from __future__ import annotations
from .message_contracts import AcquisitionError, ContractError, HomologyResults, NativePhmmerInput, obj, recorded_coverage, reference, sqlite3, subprocess
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_role_readers import tool_catalog

def tool_contracts():
    empty = obj({})
    definitions = [('homology.extract', {'type': 'object', 'properties': {'limit': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0}, 'snapshot_ref': reference('source'), 'retry_from': reference('source')}, 'required': ['limit'], 'additionalProperties': False}), ('homology.coverage', obj({'snapshot_ref': reference('source')})), ('homology.errors', obj({'snapshot_ref': reference('source'), 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 0}}))]
    descriptions = {'homology.extract': 'Extract a selected page of actual native measurements; explicit snapshot for later pages and retry_from for an explicit failed-attempt retry. Parent integrates scientific meaning.', 'homology.coverage': 'Read recorded acquisition coverage and captured parser/native completeness for one assigned-job snapshot. This does not poll, parse or acquire new rows.', 'homology.errors': 'Read a requested page of typed extraction failures without rerunning extraction.'}
    return [{'name': name, 'input_schema': schema, 'description': descriptions[name]} for name, schema in definitions]
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_operations import operation_for_role

async def execute_assigned_operation(owner, source, name, args, *, operation_key):
    if name not in {item['name'] for item in owner.catalog(source)}:
        raise ValueError('tool_not_owned_by_job_role')
    assignment = owner.assignment(source)
    job_ref = assignment['job_ref']
    try:
        row = owner.jobs._row(job_ref)
        if row['cpu'] != assignment['cpu']:
            raise ValueError('job_assignment_cpu_mismatch')
        if row['search_mode'] != assignment.get('search_mode', 'native_defaults'):
            raise ValueError('job_assignment_search_mode_mismatch')
        if name == 'homology.coverage':
            value = recorded_coverage(source.workflow.store, args['snapshot_ref'], query_ref=assignment['query_ref'], scope=source.scope, execution_context={'job_ref': job_ref, 'registry_ref': owner.jobs.config['registry_ref']})
        else:
            adapter = HomologyResults(source.workflow.store, policy=owner.parser_policy)
            if name == 'homology.extract':
                inputs = NativePhmmerInput.from_job(owner.jobs, assignment['handoff'])
                return await adapter.extract(inputs, scope=source.scope, **args, attempt_key=operation_key)
            value = adapter.errors(scope=source.scope, query_ref=assignment['query_ref'], execution_context={'job_ref': job_ref, 'registry_ref': owner.jobs.config['registry_ref']}, **args)
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': value, 'feedback': None}
    except (ValueError, KeyError, OSError, sqlite3.Error, subprocess.SubprocessError, ContractError, AcquisitionError) as error:
        return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': error.code if isinstance(error, AcquisitionError) else 'job_storage_failed' if isinstance(error, sqlite3.Error) else 'job_control_failed' if isinstance(error, subprocess.SubprocessError) else str(error) if isinstance(error, ValueError) else 'job_operation_failed', 'exception_type': type(error).__name__, 'operation': name, 'job_ref': job_ref, **({'phase': error.phase, **{key: error.operational[key] for key in ('retryable', 'retry_same_prepared_job', 'local_resources') if key in (error.operational or {})}} if isinstance(error, AcquisitionError) else {})}}
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_family_resources import execute_assigned
