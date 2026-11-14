"""Private A101 job_results execution operations."""
from __future__ import annotations
from .execution_contracts import AcquisitionError, ContractError, HomologyResults, NativePhmmerInput, obj, recorded_coverage, reference, sqlite3, subprocess

class OperationalOperations:

    def catalog(self, source):
        self.credit_kind(source.path[-1][0])
        role = 'job_results'
        empty = obj({})
        definitions = {'job_results': [('homology.extract', {'type': 'object', 'properties': {'limit': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0}, 'snapshot_ref': reference('source'), 'retry_from': reference('source')}, 'required': ['limit'], 'additionalProperties': False}), ('homology.coverage', obj({'snapshot_ref': reference('source')})), ('homology.errors', obj({'snapshot_ref': reference('source'), 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 0}}))]}
        descriptions = {'homology.environment': 'Inspect preparation state and caller-owned resources for your assigned job.', 'homology.configure': 'Apply and check the parent-selected CPU allocation and executable for the assigned job.', 'homology.stage': 'Prepare or repair private snapshots; reuse unchanged inputs.', 'homology.submit': 'Submit the assigned detached job once; a replay preserves its identity.', 'homology.resume_start': 'Repair the existing submitted service startup without submitting another job.', 'homology.check_handoff': 'Exercise a fresh receiver for status, elapsed time, progress and output availability.', 'homology.sample': 'Record one actual typed job-state sample. Sample counts and unchanged polling are not progress.', 'homology.extract': 'Extract a selected page of actual native measurements; explicit snapshot for later pages and retry_from for an explicit failed-attempt retry. Parent integrates scientific meaning.', 'homology.coverage': 'Read recorded acquisition coverage and captured parser/native completeness for one assigned-job snapshot. This does not poll, parse or acquire new rows.', 'homology.errors': 'Read a requested page of typed extraction failures without rerunning extraction.'}
        return [{'name': name, 'input_schema': schema, 'description': descriptions[name]} for name, schema in definitions['job_results']]

    async def execute(self, source, name, args, *, operation_key):
        result = await self._execute(source, name, args, operation_key=operation_key)
        if self.native_event_provider is not None and name in {'homology.submit', 'homology.resume_start'}:
            from gene_annotation_episode.episodic_workflow.root.a101.method_loop.durable import DurableExecutionError
            job_ref = self.assignment(source)['job_ref']
            try:
                self.bind_job_native_events(source, job_ref)
                result['native_event_targets'] = self.jobs.native_event_targets(job_ref)
            except (DurableExecutionError, sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
                result['native_event_targets'] = []
                storage = isinstance(error, (sqlite3.Error, OSError)) or (isinstance(error, DurableExecutionError) and error.failure['code'] == 'storage_failure')
                result['native_event_target_failure'] = {'code': 'native_event_storage_unavailable' if storage else 'native_event_identity_conflict', 'affected_refs': [job_ref]}
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
            if name == 'homology.environment':
                value = self.jobs.environment(job_ref)
            elif name == 'homology.configure':
                value = self.jobs.configure(job_ref, assignment['cpu'])
            elif name == 'homology.stage':
                value = self.jobs.stage(job_ref)
            elif name == 'homology.submit':
                value = self.jobs.submit(job_ref, statistics=self.statistics, native_events=self.bind_job_native_events(source, job_ref))
            elif name == 'homology.resume_start':
                value = self.jobs.resume_start(job_ref, native_events=self.bind_job_native_events(source, job_ref))
            elif name == 'homology.check_handoff':
                value = self.jobs.check_handoff(self.jobs.handoff(job_ref))
            elif name == 'homology.sample':
                value = self.jobs.sample(assignment['handoff'], operation_key=operation_key)
                return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'operational_sample_ref': value['sample_ref'], 'result': value, 'feedback': None}
            elif name == 'homology.coverage':
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
