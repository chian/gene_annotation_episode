"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations
import sqlite3
import subprocess
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import obj
ROLES = ('job_monitor',)

def catalog(self, source):
    role = source.path[-1][0]
    empty = obj({})
    definitions = {'job_monitor': [('homology.sample', empty)]}
    descriptions = {'homology.sample': 'Record one actual typed job-state sample. Sample counts and unchanged polling are not progress.'}
    return [{'name': name, 'input_schema': schema, 'description': descriptions[name]} for name, schema in definitions[role]]

async def execute(self, source, name, args, *, operation_key):
    result = await self._execute(source, name, args, operation_key=operation_key)
    if self.statistics is not None:
        try:
            exported = list(self.jobs.recover_statistics(self.assignment(source)['job_ref']))
        except (sqlite3.Error, OSError) as error:
            exported = [{'job_ref': self.assignment(source)['job_ref'], 'state': 'unavailable', 'code': 'statistics_registry_unavailable', 'exception_type': type(error).__name__}]
        result['execution_statistics_export'] = exported
    return result

async def _execute(self, source, name, args, *, operation_key):
    if name not in {item['name'] for item in self.catalog(source)}:
        raise ValueError('tool_not_owned_by_job_role')
    assignment = self.assignment(source)
    job_ref = assignment['job_ref']
    try:
        row = self.jobs._row(job_ref)
        if row['cpu'] != assignment['cpu']:
            raise ValueError('job_assignment_cpu_mismatch')
        if row['search_mode'] != assignment.get('search_mode', 'native_defaults'):
            raise ValueError('job_assignment_search_mode_mismatch')
        value = self.jobs.sample(assignment['handoff'], operation_key=operation_key)
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'operational_sample_ref': value['sample_ref'], 'result': value, 'feedback': None}
    except (ValueError, KeyError, OSError, sqlite3.Error, subprocess.SubprocessError, ContractError, AcquisitionError) as error:
        return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': error.code if isinstance(error, AcquisitionError) else 'job_storage_failed' if isinstance(error, sqlite3.Error) else 'job_control_failed' if isinstance(error, subprocess.SubprocessError) else str(error) if isinstance(error, ValueError) else 'job_operation_failed', 'exception_type': type(error).__name__, 'operation': name, 'job_ref': job_ref, **({'phase': error.phase, **{key: error.operational[key] for key in ('retryable', 'retry_same_prepared_job', 'local_resources') if key in (error.operational or {})}} if isinstance(error, AcquisitionError) else {})}}
