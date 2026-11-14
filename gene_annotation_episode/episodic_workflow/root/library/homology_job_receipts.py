"""Original native-event, status and durable handoff receipt operations."""
import json
import time
from gene_annotation_episode._local_job_worker import atomic_json
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.native_lifecycle import collect, status
from ..communication import validate_form
from .homology_job_contracts import VERSION, HANDOFF_SCHEMA
from .homology_job_inputs import ref
from .homology_job_status_contracts import OUTPUTS, STATUS_SCHEMA

class HomologyJobReceipts:

    def _validate_native_event_binding(self, job_ref, handle, native_events):
        from gene_annotation_episode.episodic_workflow.root.native_events import NativeEventBinding
        if native_events is not None:
            if type(native_events) is not NativeEventBinding:
                raise TypeError('typed_native_event_binding_required')
            if native_events.job_ref != job_ref or native_events.registry_ref != self.config['registry_ref']:
                raise ValueError('native_event_binding_identity_conflict')
            if handle.path.is_file() and handle.read().get('native_events') != native_events.as_record():
                raise ValueError('prepared_native_event_binding_is_immutable')

    def native_event_binding(self, job_ref):
        """Read the original reservation binding, including prepared work."""
        from gene_annotation_episode.episodic_workflow.root.native_events import NativeEventBinding
        handle = self._handle(job_ref)
        if not handle.path.is_file():
            return None
        value = handle.read().get('native_events')
        if value is None:
            return None
        binding = NativeEventBinding.from_record(value)
        if binding.job_ref != job_ref or binding.registry_ref != self.config['registry_ref']:
            raise ValueError('native_event_binding_identity_conflict')
        return binding

    def native_event_targets(self, job_ref):
        """Read existing registration only; never register, export or poll."""
        from method_loop.durable import native_target_descriptor, read_native_target
        from gene_annotation_episode.episodic_workflow.root.native_events import _handle, _registration
        handle = self._handle(job_ref)
        binding = self.native_event_binding(job_ref)
        if binding is None:
            return []
        _, _, identity = _handle(handle.path)
        registration = _registration(binding, identity)
        if not (binding.execution_directory / 'executions.sqlite').is_file():
            return []
        try:
            actual = read_native_target(binding.execution_directory, registration['handle'])
        except (FileNotFoundError, KeyError):
            return []
        if actual != registration:
            raise ValueError('native_event_binding_identity_conflict')
        return [native_target_descriptor(actual)]

    def recover_native_events(self, *, native_event_provider, job_ref=None):
        """Export only receipts bound to this exact host run and resource."""
        from gene_annotation_episode.episodic_workflow.root.native_events import NativeEventProvider, publish_native_events
        if type(native_event_provider) is not NativeEventProvider:
            raise TypeError('typed_native_event_provider_required')
        rows = [self._row(job_ref)] if job_ref is not None else self.db.execute('SELECT job_ref FROM orders')
        for row in rows:
            try:
                binding = self.native_event_binding(row['job_ref'])
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if binding is None or any((getattr(binding, key) != getattr(native_event_provider, key) for key in ('execution_directory', 'run_id', 'resource_id'))):
                continue
            path = self._directory(row['job_ref']) / 'native.handle.json'
            yield publish_native_events(path)

    def recover_statistics(self, job_ref=None):
        """Retry only receipt export, never execution or an episode decision."""
        from gene_annotation_episode.episodic_workflow.root.execution_recording import publish_native_statistics
        rows = [self._row(job_ref)] if job_ref is not None else self.db.execute('SELECT job_ref FROM orders WHERE submission_requested=1')
        for row in rows:
            path = self._directory(row['job_ref']) / 'native.handle.json'
            if not path.is_file():
                continue
            try:
                value = publish_native_statistics(path)
            except (OSError, ValueError, KeyError, TypeError) as error:
                value = {'state': 'unavailable', 'code': 'statistics_receipt_unreadable', 'exception_type': type(error).__name__}
                try:
                    atomic_json(path.parent / 'statistics_recovery.json', value)
                except OSError:
                    value['diagnostic_persisted'] = False
            else:
                try:
                    (path.parent / 'statistics_recovery.json').unlink(missing_ok=True)
                except OSError:
                    value['diagnostic_cleanup_failed'] = True
            yield {'job_ref': row['job_ref'], **value}

    def status(self, job_ref):
        row = self._row(job_ref)
        directory = self._directory(job_ref)
        handle = self._handle(job_ref)
        view = status(handle) if handle.path.exists() else None
        state = view['state'] if view else 'submission_unconfirmed' if row['submission_requested'] else 'not_submitted'
        terminal = view is not None and view['terminal']
        outcome, failure, resource, code = ('pending', None, None, None)
        if terminal:
            try:
                returned = collect(handle)
                code = returned.returncode
                outcome = 'succeeded' if code == 0 else 'failed'
                failure = 'native_nonzero_exit' if code != 0 else None
            except AcquisitionError as error:
                outcome, failure = ('failed', error.code)
                resource = (error.operational or {}).get('resource')
                code = (error.operational or {}).get('native_returncode')
        elif state in {'execution_unknown', 'submission_unconfirmed'}:
            outcome = 'unknown'
        outputs = []
        for role, name in OUTPUTS.items():
            path = directory / name
            exists = path.is_file()
            outputs.append({'role': role, 'available': exists, 'bytes': path.stat().st_size if exists else None, 'writer_closed': terminal and exists})
        return {'job_ref': job_ref, 'registry_ref': self.config['registry_ref'], 'state': state, 'outcome': outcome, 'elapsed_seconds': view['metadata']['elapsed_seconds'] if view else None, 'duration_measure': 'systemd_service_wall_seconds', 'native_returncode': code, 'failure_code': failure, 'resource': resource, 'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction', 'outputs': outputs}

    def handoff(self, job_ref):
        row = self._row(job_ref)
        if not row['submission_requested'] or not (self._directory(job_ref) / 'native.handle.json').is_file():
            raise ValueError('job_submission_handoff_unresolved')
        if self._handle(job_ref).read()['stage'] == 'prepared':
            raise ValueError('job_submission_handoff_unresolved')
        return {'job_ref': job_ref, 'registry_ref': self.config['registry_ref'], 'backend': VERSION, 'status_interface': 'homology.status.v1', 'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}

    def receive(self, handoff):
        validate_form(handoff, HANDOFF_SCHEMA, self.resolve)
        if not isinstance(handoff, dict) or handoff != self.handoff(handoff.get('job_ref')):
            raise ValueError('homology_handoff_identity_or_interface_mismatch')
        sample = self.status(handoff['job_ref'])
        return validate_form(sample, STATUS_SCHEMA, self.resolve)

    def check_handoff(self, handoff):
        receiver = type(self)(self.directory)
        try:
            sample = receiver.receive(handoff)
        finally:
            receiver.close()
        receipt = ref('handoff_receipt', handoff)
        checked_at = time.time()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO handoffs VALUES(?,?,?)', (receipt, handoff['job_ref'], canonical({'handoff': handoff, 'first_checked_at_unix_seconds': checked_at, 'first_sample': sample})))
        return {'receipt_ref': receipt, 'handoff': handoff, 'sample': sample, 'checked_at_unix_seconds': checked_at}

    def sample(self, handoff, *, operation_key):
        old = self.db.execute('SELECT job_ref,body FROM samples WHERE operation_key=?', (operation_key,)).fetchone()
        if old:
            if old['job_ref'] != handoff['job_ref']:
                raise ValueError('monitoring_sample_identity_conflict')
            if handoff != self.handoff(handoff.get('job_ref')):
                raise ValueError('homology_handoff_identity_or_interface_mismatch')
            return json.loads(old['body'])
        body = self.receive(handoff)
        body = {'sample_ref': ref('job_sample', [handoff, operation_key]), 'sampled_at_unix_seconds': time.time(), **body}
        with self.db:
            self.db.execute('INSERT INTO samples VALUES(?,?,?,?)', (body['sample_ref'], operation_key, handoff['job_ref'], canonical(body)))
        return body

    def result_file(self, handoff, role):
        self.receive(handoff)
        if role not in OUTPUTS:
            raise ValueError('unknown_homology_result_role')
        path = self._directory(handoff['job_ref']) / OUTPUTS[role]
        if not path.is_file():
            raise ValueError('homology_result_not_available')
        return path

    def resolve(self, value, namespace):
        if namespace is None:
            return any((self.resolve(value, kind) for kind in ('execution_registry', 'homology_job', 'handoff_receipt', 'job_sample')))
        if namespace == 'execution_registry':
            return value == self.config['registry_ref']
        tables = {'homology_job': ('orders', 'job_ref'), 'handoff_receipt': ('handoffs', 'receipt_ref'), 'job_sample': ('samples', 'sample_ref')}
        if namespace not in tables:
            return False
        table, column = tables[namespace]
        return self.db.execute(f'SELECT 1 FROM {table} WHERE {column}=?', (value,)).fetchone() is not None
