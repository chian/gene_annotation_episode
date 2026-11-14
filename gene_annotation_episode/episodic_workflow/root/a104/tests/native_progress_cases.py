"""Real stored practical receipts and progress, with one controlled observation.

This reuses the original test_execution_progress publication sequence. It does
not claim a native producer ran, or commission a scientific result. The native
observation is a named controlled port; assignment/receipt authenticity, scoped
target reading, both progress stores and saved operation signatures stay real.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from .api_cases import canonical, error_record, module, rows

HOMES = (
    'execution_result_acquisition',
    'scientific_process/execution_result_acquisition',
    'hpc_work_planning/execution_result_acquisition',
    'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition',
    'scientific_process/hpc_work_planning/execution_result_acquisition',
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition')
FIELDS = ['execution_status', 'measurements', 'log_windows', 'committed_record_refs',
          'dependencies', 'result_available']
STAMP = '2026-11-12T00:00:00+00:00'


def files(directory):
    root = Path(directory)
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*')) if path.is_file()}


def write(path, value):
    path.write_text(json.dumps(canonical(value), sort_keys=True, indent=2) + '\n')


def forbidden(*args, **kwargs):
    raise AssertionError('saved_progress_replay_attempted_new_native_observation')


class NativeProgressCase:
    def __init__(self, directory, home, *, saved=None):
        assert home in HOMES
        self.directory, self.home = Path(directory).resolve(), home
        self.store = module('state').Store(self.directory / 'store')
        try:
            self._initialize(saved)
        except BaseException:
            self.store.close()
            raise

    def _initialize(self, saved):
        from types import SimpleNamespace
        self.run_id = 'controlled-native-progress-' + hashlib.sha256(self.home.encode()).hexdigest()[:16]
        self.journal = module('episode_journal').Journal(self.store, self.run_id)
        if saved is None:
            self.store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        self.scope = self.store.validate_scope(None)
        # On replay, the original logical workspace/configuration is immutable.
        # Reopened Store custody does not rewrite saved absolute paths.
        workspace = (self.directory / 'workspace') if saved is None else Path(saved['resources']['local']['workspace'])
        self.resources = {'local': {'kind': 'local', 'workspace': str(workspace),
            'policy': {'memory_bytes': 5 * 1024**3, 'scratch_bytes': 4 * 1024**3}}}
        if saved is None:
            workspace.mkdir(parents=True)
        else:
            assert self.resources == saved['resources']
        self.assignment = {'version': 'practical_assignment_v1',
            'assignment_id': 'controlled-saved-native-progress', 'resource_id': 'local',
            'resource_kind': 'local', 'workspace': str(workspace), 'endpoint': 'usable_handoff',
            'requested_job': {'argv': ['/controlled-not-executed/native-progress'], 'environment': {}},
            'progress_requirements': [{'key': 'handoff', 'credit': 1.,
                'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}
        path = (('launch_local', 'original-controlled-practical-receipt'),)
        episode_id = module('method_loop.identities').EpisodeRef(self.run_id, path).episode_id
        request = {'message': {'scope': self.scope, 'episode_assignment': self.assignment}}
        self.context = module('episode_bindings').BindingContext(self.run_id, episode_id,
            'launch_local', path, self.scope, self.assignment, request)
        self.receipts = module('practical_receipt_information').PracticalReceiptInformation(self.store, self.run_id)
        if saved is None:
            self.journal.save('runtime_episodes', {'episode_id': episode_id,
                'path': module('runtime')._json(path), 'request': module('runtime')._json(request),
                'initial_credit': 0, 'state': 'running', 'completion': None, 'archive': None})
            self.reference, self.returned = self._publish()
        else:
            self.reference, self.returned = saved['reference'], saved['receipt_outcome']
            assert self.context.as_record() == saved['context']
            assert json.loads(self.journal.row('runtime_episodes', episode_id)['request']) == request
        # The actual private Launch constructor owns the exported provider.
        # No mocked reader, generic episode or constructor-role fallback is used.
        launch = self.home.removesuffix('execution_result_acquisition') + 'execution_job_submission'
        self.binding = module(launch + '/episode').ExecutionEpisode(
            SimpleNamespace(annotation_task_required=lambda: False), store=self.store,
            directory=self.directory / 'execution', run_id=self.run_id,
            resources=self.resources, initial_information={}, tool_registry=None,
            handoff_unit=1., acquired_record_unit=1., log_window_bytes=8,
            log_roles=('stdout', 'stderr'))
        self.job = self.binding.job_progress_provider
        self.target = self.job.targets.read_target(self.reference, self.scope)
        assert self.target['assignment'] == self.assignment
        assert self.receipts.read(self.reference, self.scope)['receipt'] == self.returned['result']
        self.progress = module('episode_monitoring').ProgressProvider(self.store,
            module('method_loop.durable').DurableExecutionStore(self.directory / 'durable'),
            run_id=self.run_id, job_provider=self.job)
        self.key = self.run_id + ':original-progress:0'
        self.calls = []

    def _publish(self):
        practical = module('practical_execution_records')
        state = module('practical_execution_state').PracticalState(self.directory / 'practical',
            self.run_id, self.context.episode_id, self.assignment)
        key = self.run_id + ':' + self.context.episode_id + ':0'
        arguments = {}
        self.journal.save('runtime_actions', {'episode_id': self.context.episode_id,
            'decision_index': 0, 'action': practical.canonical({'kind': 'tool',
                'tool': 'practical.job.start', 'arguments': arguments}), 'result': None, 'credit': None})
        execution_id = str(Path(self.assignment['workspace']) / 'controlled-native.json')
        job = {'requested_job_sha256': practical.digest(self.assignment['requested_job']),
            **deepcopy(self.assignment['requested_job']), 'resource_kind': 'local',
            'execution_id': execution_id, 'status': 'completed', 'output_paths': [],
            'handoff': {'execution_id': execution_id, 'monitor_operation': 'practical.job.status',
                'results_operation': 'practical.job.collect'}}
        outcome = {'facts': {'requested_job': job}, 'native_outcome': {
            'attempt_id': practical.digest(key), 'attempt_operation_key': key,
            'controlled_test_port': 'original_practical_handoff_shape_no_native_producer'}}
        state.begin(key, 'practical.job.start', arguments)
        receipt = state.finish(key, outcome, practical.assess_validations(self.assignment,
            outcome, state.context(), tool_name='practical.job.start'))
        reference = self.receipts.publish(self.context, receipt)
        returned = {'status': 'completed', 'record_refs': [reference],
            'changed_record_refs': [], 'result': receipt}
        self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? '
            'AND episode_id=? AND decision_index=0',
            (practical.canonical(returned), self.run_id, self.context.episode_id))
        return reference, returned

    def observed(self, assignment, execution_id, **arguments):
        assert assignment == self.assignment and execution_id == self.target['execution_id']
        assert arguments['run_id'] == self.run_id
        assert arguments['origin_episode_id'] == self.context.episode_id
        self.calls.append(canonical({'assignment': assignment, 'execution_id': execution_id,
            'arguments': arguments}))
        return module('progress_records').validate_resource_observation({
            'observed_at': STAMP, 'state': 'completed', 'returncode': 0,
            'failure_code': None, 'result_available': False, 'measurements': [],
            'outputs': [], 'logs': [], 'provenance_refs': [],
            'native': {'controlled_test_port': 'native_status_only_no_producer_execution'}})

    def close(self):
        self.store.close()


def capture(directory):
    destination = Path(directory); assert not destination.exists(); destination.mkdir(parents=True)
    captures = []
    for number, home in enumerate(HOMES):
        root = destination / str(number)
        value = NativeProgressCase(root, home)
        try:
            native = value.job.targets.operations['local']
            with patch.object(native, 'observe_execution', value.observed):
                public = value.progress.observe(value.reference, FIELDS, value.scope, operation_key=value.key)
            assert len(value.calls) == 1
            row = dict(value.store.db.execute('SELECT * FROM runtime_execution_progress_operations '
                'WHERE run_id=? AND operation_key=?', (value.run_id, value.key)).fetchone())
            raw = json.loads(row['result'])
            before = rows(value.store)
            with patch.object(native, 'observe_execution', forbidden):
                assert value.progress.observe(value.reference, FIELDS, value.scope, operation_key=value.key) == public
                assert value.job.observe(value.reference, FIELDS, value.scope, operation_key=value.key) == raw
            assert rows(value.store) == before
            saved = {'home': home, 'context': value.context.as_record(), 'reference': value.reference,
                'receipt_outcome': value.returned, 'resources': value.resources,
                'target': value.target, 'operation_key': value.key, 'resource_operation_row': row,
                'provider_descriptor': value.job.as_record(), 'public_observation': public,
                'raw_observation': raw, 'all_rows': before, 'controlled_observations': value.calls,
                'native_producer_executed': False, 'full_workflow_resumption_claimed': False}
        finally:
            value.close()
        write(root / 'capture.json', saved)
        captures.append({'home': home, 'directory': str(number), 'files': files(root)})
    write(destination / 'index.json', {'version': 'a104_native_progress_captures_v1',
        'captures': captures, 'case_count': 6})
    return {'files': files(destination), 'index_sha256': hashlib.sha256((destination / 'index.json').read_bytes()).hexdigest()}


def authenticate(directory, custody):
    root = Path(directory)
    assert files(root) == custody['files']
    assert hashlib.sha256((root / 'index.json').read_bytes()).hexdigest() == custody['index_sha256']
    index = json.loads((root / 'index.json').read_bytes())
    assert index['version'] == 'a104_native_progress_captures_v1' and index['case_count'] == 6
    assert [row['home'] for row in index['captures']] == list(HOMES)
    assert [row['directory'] for row in index['captures']] == [str(number) for number in range(6)]
    for row in index['captures']:
        assert files(root / row['directory']) == row['files']
        assert json.loads((root / row['directory'] / 'capture.json').read_bytes())['home'] == row['home']
    return index


def reopen(directory, destination, *, custody, expected_changed):
    assert type(expected_changed) is bool
    root, output = Path(directory), Path(destination)
    index = authenticate(root, custody)
    assert not output.exists(); output.mkdir(parents=True)
    results = []
    for row in index['captures']:
        source, copied = root / row['directory'], output / row['directory']
        shutil.copytree(source, copied)
        assert files(copied) == row['files']  # Before Store opens a copied database.
        saved = json.loads((copied / 'capture.json').read_bytes())
        value = NativeProgressCase(copied, row['home'], saved=saved)
        try:
            before = rows(value.store)
            assert before == saved['all_rows']
            assert value.target == saved['target'] and value.key == saved['operation_key']
            current = value.job.as_record()
            assert (current != saved['provider_descriptor']) is expected_changed
            with patch.object(value.job.targets.operations['local'], 'observe_execution', forbidden):
                public = value.progress.observe(value.reference, FIELDS, value.scope, operation_key=value.key)
                assert public == saved['public_observation']
                try:
                    result = value.job.observe(value.reference, FIELDS, value.scope, operation_key=value.key)
                except Exception as error:
                    assert expected_changed and type(error) is module('domain').ContractError
                    assert str(error) == 'execution_progress_operation_identity_conflict'
                    direct = {'raised': error_record(error)}
                else:
                    assert not expected_changed and result == saved['raw_observation']
                    direct = {'returned': result}
            assert rows(value.store) == before and value.calls == []
            results.append({'home': row['home'], 'public_replay': public, 'direct_replay': direct,
                'original_provider': saved['provider_descriptor'], 'current_provider': current,
                'all_rows_unchanged': True, 'receipt_and_target_reauthenticated': True,
                'native_observations': 0, 'full_workflow_resumption_claimed': False})
        finally:
            value.close()
        assert files(source) == row['files']
    assert authenticate(root, custody) == index
    return results
