from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.homology_result_acquisition.contracts import AcquisitionError, ContractError, HomologyResults, NativePhmmerInput, obj, recorded_coverage, reference, sqlite3, subprocess

class AcquisitionOperations:

    def catalog(self, source):
        role = source.path[-1][0]
        empty = obj({})
        definitions = {'job_results': [('homology.extract', {'type': 'object', 'properties': {'limit': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0}, 'snapshot_ref': reference('source'), 'retry_from': reference('source')}, 'required': ['limit'], 'additionalProperties': False}), ('homology.coverage', obj({'snapshot_ref': reference('source')})), ('homology.errors', obj({'snapshot_ref': reference('source'), 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 0}}))]}
        descriptions = {'homology.extract': 'Extract a selected page of actual native measurements; explicit snapshot for later pages and retry_from for an explicit failed-attempt retry. Parent integrates scientific meaning.', 'homology.coverage': 'Read recorded acquisition coverage and captured parser/native completeness for one assigned-job snapshot. This does not poll, parse or acquire new rows.', 'homology.errors': 'Read a requested page of typed extraction failures without rerunning extraction.'}
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
            if name == 'homology.coverage':
                value = recorded_coverage(source.workflow.store, args['snapshot_ref'], query_ref=assignment['query_ref'], scope=source.scope, execution_context={'job_ref': job_ref, 'registry_ref': self.jobs.config['registry_ref']})
            else:
                adapter = HomologyResults(source.workflow.store, policy=self.parser_policy)
                if name == 'homology.extract':
                    inputs = NativePhmmerInput.from_job(self.jobs, assignment['handoff'])
                    return await adapter.extract(inputs, scope=source.scope, **args, attempt_key=operation_key)
                value = adapter.errors(scope=source.scope, query_ref=assignment['query_ref'], execution_context={'job_ref': job_ref, 'registry_ref': self.jobs.config['registry_ref']}, **args)
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': value, 'feedback': None}
        except (ValueError, KeyError, OSError, sqlite3.Error, subprocess.SubprocessError, ContractError, AcquisitionError) as error:
            return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': error.code if isinstance(error, AcquisitionError) else 'job_storage_failed' if isinstance(error, sqlite3.Error) else 'job_control_failed' if isinstance(error, subprocess.SubprocessError) else str(error) if isinstance(error, ValueError) else 'job_operation_failed', 'exception_type': type(error).__name__, 'operation': name, 'job_ref': job_ref, **({'phase': error.phase, **{key: error.operational[key] for key in ('retryable', 'retry_same_prepared_job', 'local_resources') if key in (error.operational or {})}} if isinstance(error, AcquisitionError) else {})}}
