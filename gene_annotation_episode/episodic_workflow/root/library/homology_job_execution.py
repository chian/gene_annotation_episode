"""Original locking, staging and immutable homology submission operations."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import shutil
from gene_annotation_episode.local_jobs import LocalJobPolicy, check_scratch_budget
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, start_prepared
from .homology_job_inputs import digest
from .homology_job_status_contracts import OUTPUTS

class HomologyJobExecution:

    @contextmanager
    def _submission_lock(self, job_ref):
        self._row(job_ref)
        with (self.directory / (job_ref + '.launch.lock')).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _has_intent(self, row):
        return bool(row['submission_requested'] or (self.directory / row['job_ref'] / 'native.handle.json').is_file())

    def configure(self, job_ref, cpu):
        with self._submission_lock(job_ref):
            return self._configure(job_ref, cpu)

    def _configure(self, job_ref, cpu):
        row = self._row(job_ref)
        if type(cpu) is not int or cpu < 1:
            raise ValueError('cpu_outside_caller_allocation')
        if cpu != row['cpu']:
            raise ValueError('selected_job_cpu_is_immutable')
        if self._has_intent(row):
            return self.environment(job_ref)
        program = self.config['executable']
        if not os.access(program['path'], os.X_OK) or digest(program['path']) != program['sha256']:
            raise ValueError('configured_executable_unavailable_or_changed')
        return self.environment(job_ref)

    def stage(self, job_ref):
        with self._submission_lock(job_ref):
            return self._stage(job_ref)

    def _stage(self, job_ref):
        row = self._row(job_ref)
        directory = self._directory(job_ref)
        handle = self._handle(job_ref)
        reserved = handle.path.is_file() and handle.read()['stage'] == 'prepared'
        if self._has_intent(row) and (not reserved):
            if row['staged']:
                return self.environment(job_ref)
            raise ValueError('submitted_job_inputs_are_immutable')
        database = self.config['reference_database']
        reference_ready = (directory / 'references.faa').is_file() and digest(directory / 'references.faa') == database['sha256']
        query_ready = (directory / 'query.faa').is_file() and (directory / 'query.faa').read_text() == row['query_fasta']
        if row['staged'] and reference_ready and query_ready:
            return self.environment(job_ref)
        directory.mkdir(exist_ok=True)
        policy = LocalJobPolicy(**self.config['job_limits'])
        source = Path(database['path'])
        additional = (0 if reference_ready else source.stat().st_size) + (0 if query_ready else len(row['query_fasta'].encode()))
        check_scratch_budget(directory, policy, additional_bytes=additional)
        if not reference_ready:
            shutil.copyfile(source, directory / 'references.faa')
            if digest(directory / 'references.faa') != database['sha256']:
                raise ValueError('reference_database_bytes_changed')
        if not query_ready:
            (directory / 'query.faa').write_text(row['query_fasta'])
        check_scratch_budget(directory, policy)
        with self.db:
            self.db.execute('UPDATE orders SET staged=1 WHERE job_ref=?', (job_ref,))
        return self.environment(job_ref)

    def submit(self, job_ref, *, statistics=None, native_events=None):
        with self._submission_lock(job_ref):
            return self._submit(job_ref, statistics=statistics, native_events=native_events)

    def _validate_inputs(self, row):
        directory, program = (self._directory(row['job_ref']), self.config['executable'])
        if digest(program['path']) != program['sha256'] or digest(directory / 'references.faa') != self.config['reference_database']['sha256'] or (directory / 'query.faa').read_text() != row['query_fasta']:
            raise ValueError('prepared_job_dependency_changed')

    def _submit(self, job_ref, *, statistics=None, native_events=None):
        if statistics is not None:
            from gene_annotation_episode.episodic_workflow.root.execution_recording import HomologyStatistics
            if type(statistics) is not HomologyStatistics:
                raise TypeError('typed_homology_statistics_binding_required')
        row = self._row(job_ref)
        handle = self._handle(job_ref)
        self._validate_native_event_binding(job_ref, handle, native_events)
        if row['submission_requested'] and (not handle.path.is_file()):
            return {'job_ref': job_ref, 'new_submission': False, 'status': self.status(job_ref)}
        if handle.path.is_file() and handle.read()['stage'] != 'prepared':
            return {'job_ref': job_ref, 'new_submission': False, 'status': self.status(job_ref)}
        if row['cpu'] is None or not row['staged']:
            raise ValueError('configured_execution_and_staged_inputs_required')
        directory = self._directory(job_ref)
        program = self.config['executable']
        self._validate_inputs(row)
        if not handle.path.is_file():
            command = self._command(row)
            context = None if statistics is None else statistics.for_job(self, row)
            handle = prepare_job(command, cwd=directory, policy=LocalJobPolicy(**self.config['job_limits']), handle_path=directory / 'native.handle.json', stdout_path=directory / OUTPUTS['native_text'], stderr_path=directory / OUTPUTS['native_stderr'], statistics=context, native_events=native_events, cpu_threads=row['cpu'])
        elif statistics is not None:
            recorded = handle.read().get('statistics')
            expected = statistics.for_job(self, row).as_record()
            if recorded != expected:
                raise ValueError('prepared_statistics_binding_is_immutable')
        with self.db:
            self.db.execute('UPDATE orders SET submission_requested=1 WHERE job_ref=?', (job_ref,))
        start_prepared(handle)
        return {'job_ref': job_ref, 'new_submission': True, 'status': self.status(job_ref)}

    def resume_start(self, job_ref, *, native_events=None):
        with self._submission_lock(job_ref):
            handle = self._handle(job_ref)
            self._validate_native_event_binding(job_ref, handle, native_events)
            if handle.path.is_file() and handle.read()['stage'] == 'prepared':
                self._submit(job_ref, native_events=native_events)
            else:
                resume_start(handle)
            return self.status(job_ref)

    def _handle(self, job_ref):
        row = self._row(job_ref)
        directory = self._directory(job_ref)
        handle = NativeJobHandle(directory / 'native.handle.json')
        if handle.path.exists():
            body = handle.read()
            expected = self._command(row)
            if body['cwd'] != str(directory) or body['command'] != expected or body['metadata']['policy'] != self.config['job_limits'] or (body['stdout'] != str(directory / OUTPUTS['native_text'])) or (body['stderr'] != str(directory / OUTPUTS['native_stderr'])):
                raise ValueError('native_handle_does_not_describe_registered_job')
        return handle
