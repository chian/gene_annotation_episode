"""Real paired programs and practical Workflow; decisions are scripted fixtures."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_blast_contracts import requested_job_from_native
from gene_annotation_episode.native_blast_local import prepare_local_blast, local_blast_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldParameters
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import ASSIGNMENT_SCHEMA, assess_validations, digest, validate_assignment
from gene_annotation_episode.practical_execution_state import PracticalState, _immutable
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'verification/tool_graders_blast_pairwise_2026-10-26_294/native_examples'
LABELS = ('blastn_range_reverse_json15', 'blastp_gaps_json15', 'blastx_reverse_json15',
          'tblastn_reverse_json15', 'tblastx_frames_json15')
POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}


def request(label=LABELS[0]):
    return json.loads((EXAMPLES / label / 'plan.json').read_bytes())['requested_job']


def configuration(workspace, selected):
    return {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_blast': [{key: selected['native_blast'][key] for key in ('program', 'mode', 'software')}]}


def assignment(workspace, selected):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'paired-blast296',
        'resource_kind': 'local', 'resource_id': 'here', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': deepcopy(selected),
        'progress_requirements': [{'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace),
            'environment': {'UNRELATED_CONTEXT': 'not-in-native-job'}}, 'inventory_snapshot': {},
        'constraints': {'allocation': deepcopy(POLICY)}}


def reserve(tmp_path, label=LABELS[0]):
    state = SimpleNamespace(run_id='run296', episode_id='child296',
        assignment=assignment(tmp_path, request(label)))
    key = 'selected-blast296'
    root = tmp_path / '.episode-operations' / digest({'run': state.run_id, 'episode': state.episode_id}) / digest(key)
    root.mkdir(parents=True)
    handle = prepare_local_blast(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    return state, key, handle


def launch(tmp_path, label=LABELS[0], selected=None):
    workspace = tmp_path / 'project'
    workspace.mkdir()
    selected = selected or request(label)
    assigned = assignment(workspace, selected)
    operations = LocalPracticalOperations(configuration(workspace, selected))
    state = PracticalState(tmp_path / 'practical-state', 'run296', 'child296', assigned)
    key = 'run296:child296:0'
    state.begin(key, 'practical.job.start', {})
    outcome, _ = asyncio.run(operations.execute(state, 'practical.job.start', {}, key))
    validations = assess_validations(assigned, outcome, state.context(), tool_name='practical.job.start')
    receipt = state.finish(key, outcome, validations)
    handle = native.NativeJobHandle(Path(outcome['facts']['requested_job']['execution_id']))
    result = native.wait_job(handle)
    plan = local_blast_plan(assigned, str(handle.path))
    target = {'version': 'execution_target_v1', 'handle': 'fixture-original-receipt',
        'run_id': state.run_id, 'origin_episode_id': state.episode_id, 'resource_id': 'here',
        'resource_kind': 'local', 'execution_id': str(handle.path), 'assignment': assigned,
        'request_sha256': digest(selected), 'scope': {'subject_refs': []},
        'original_operation_key': key, 'attempt_id': digest(key)}
    (tmp_path / 'native-receipt.json').write_text(json.dumps({'returncode': result.returncode,
        'metadata': result.metadata, 'target': target}, indent=2) + '\n')
    return SimpleNamespace(state=state, operations=operations, receipt=receipt, handle=handle,
        plan=plan, root=Path(plan['attempt_directory']), target=target, result=result)


@pytest.mark.parametrize('label', LABELS)
def test_exact_native_binding_schema_and_real_selected_start(tmp_path, label):
    selected = request(label)
    assigned = assignment(tmp_path, selected)
    assert Draft202012Validator(ASSIGNMENT_SCHEMA).is_valid(assigned)
    assert validate_assignment(assigned) == assigned
    origin = launch(tmp_path, label)
    bundle = json.loads((origin.root / 'bundle.json').read_bytes())
    assert origin.result.returncode == bundle['returncode'] == 0
    assert not bundle['failures']
    assert bundle['identity'] == origin.plan['identity']
    assert origin.receipt['outcome']['native_outcome']['attempt_id'] == origin.plan['identity']['attempt_id']
    assert origin.receipt['outcome']['native_outcome']['attempt_operation_key'] == origin.plan['identity']['operation_key']
    assert bundle['requested_job'] == selected
    assert origin.handle.read()['metadata']['verified_cgroup'] == {
        'memory_max': POLICY['memory_bytes'], 'memory_swap_max': 0,
        'kill_mode': 'control-group', 'oom_policy': 'kill'}
    assert origin.plan['policy'] == POLICY
    assert 'UNRELATED_CONTEXT' not in bundle['environment']
    assert origin.state.completion_proof()['endpoint'] == 'usable_handoff'
    observation = origin.operations.observe_execution(origin.state.assignment, str(origin.handle.path),
        run_id=origin.state.run_id, origin_episode_id=origin.state.episode_id,
        original_operation_key=origin.receipt['operation_key'], attempt_id=digest(origin.receipt['operation_key']))
    assert observation['state'] == 'completed' and observation['result_available']
    assert {row['role'] for row in observation['outputs']} >= {'stdout', 'stderr', 'native_blast_bundle'}
    assert any(row['role'].startswith('requested_output:') for row in observation['outputs'])
    assert all(row['path'].startswith(str(origin.root)) for row in observation['logs'])


@pytest.mark.parametrize('fault', ['program', 'mode', 'software', 'argv', 'resource', 'missing_resource', 'allocation'])
def test_invalid_binding_cannot_fall_back_to_generic_command(tmp_path, fault):
    selected = request()
    config = configuration(tmp_path, selected)
    assigned = assignment(tmp_path, selected)
    if fault == 'program':
        assigned['requested_job'] = request(LABELS[1])
    elif fault == 'mode':
        assigned['requested_job']['native_blast']['mode'] = 'database'
    elif fault == 'software':
        job = assigned['requested_job']['native_blast']
        job['software']['sha256'] = '0' * 64
        assigned['requested_job'] = requested_job_from_native(job)
    elif fault == 'argv':
        assigned['requested_job']['argv'] = ['/bin/true']
    elif fault == 'resource':
        assigned['resource_kind'] = 'hpc'
    elif fault == 'missing_resource':
        assigned.pop('resource_id')
    else:
        assigned['constraints']['allocation']['memory_bytes'] -= 1
    with pytest.raises(ValueError):
        LocalPracticalOperations(config).validate_assignment(assigned)
    assert not list(tmp_path.rglob('native.json'))


def test_reservation_never_dispatches_and_reuses_original_handle(tmp_path, monkeypatch):
    for name in ('start_prepared', 'resume_start', 'start_job', 'status', 'cancel'):
        monkeypatch.setattr(native, name, lambda *a, **k: pytest.fail('preparation dispatched'))
    state, key, handle = reserve(tmp_path)
    assert handle.read()['stage'] == 'prepared'
    assert not (handle.path.parent / 'blast-attempt').exists()
    assert prepare_local_blast(state, key, root=handle.path.parent, policy=LocalJobPolicy(**POLICY)) == handle
    handle.path.unlink()
    with pytest.raises(ValueError, match='missing_reservation_execution_uncertain'):
        prepare_local_blast(state, key, root=handle.path.parent, policy=LocalJobPolicy(**POLICY))


def test_status_collect_and_read_use_original_outputs_without_parsing_or_dispatch(tmp_path, monkeypatch):
    origin = launch(tmp_path)
    report = origin.root / 'report.json'
    report.write_bytes(b'not JSON; status must not parse scientific output')
    for name in ('start_prepared', 'start_job', 'resume_start'):
        monkeypatch.setattr(native, name, lambda *a, **k: pytest.fail('observation submitted work'))
    for name in ('practical.job.status', 'practical.job.collect'):
        outcome, _ = asyncio.run(origin.operations.execute(origin.state, name, {}, 'observation-' + name))
        assert outcome['facts']['requested_job']['execution_id'] == str(origin.handle.path)
        outputs = outcome['native_outcome']['observed_outputs']
        assert next(row for row in outputs if row['role'] == 'primary_report')['available']
        assert next(row for row in outputs if row['role'] == 'native_blast_bundle')['available']
    read = origin.operations.read_output(origin.state.assignment, str(origin.handle.path),
        path=str(report), offset=0, limit=10, run_id=origin.state.run_id,
        origin_episode_id=origin.state.episode_id)
    assert read['returned_bytes'] == 10
    with pytest.raises(ValueError, match='original_owner_conflict'):
        origin.operations.observe_execution(origin.state.assignment, str(origin.handle.path), run_id='other')
    with pytest.raises(ValueError, match='original_output_path_required'):
        origin.operations.read_output(origin.state.assignment, str(origin.handle.path),
            path=str(origin.root / 'inputs/query_sequence.fa'), offset=0, limit=10)
    report.unlink(); report.symlink_to(origin.root / 'inputs/query_sequence.fa')
    with pytest.raises(ValueError, match='path_escape'):
        origin.operations.observe_execution(origin.state.assignment, str(origin.handle.path))


def test_only_selected_confirmed_failure_retry_creates_another_attempt(tmp_path, monkeypatch):
    job = request(LABELS[1])['native_blast']
    job['options'] += ['-matrix', 'NOT_A_NATIVE_MATRIX']
    origin = launch(tmp_path, selected=requested_job_from_native(job))
    assert origin.result.returncode != 0
    original_handle = origin.handle.read()
    # A second ordinary start observes the existing attempt. Acquisition and
    # result failure never create a new physical execution.
    repeated, _ = asyncio.run(origin.operations.execute(origin.state, 'practical.job.start', {}, 'start-again'))
    assert repeated['facts']['requested_job']['execution_id'] == str(origin.handle.path)
    assert len(list(tmp_path.rglob('native.json'))) == 1
    bad, _ = asyncio.run(origin.operations.execute(origin.state, 'practical.job.start',
        {'retry_failed_execution_id': 'other'}, 'bad-retry'))
    assert bad['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
    assert len(list(tmp_path.rglob('native.json'))) == 1
    actual_status = native.status
    def uncertain(handle):
        result = deepcopy(actual_status(handle)); result['metadata']['native_returncode'] = None
        return result
    with monkeypatch.context() as patch:
        patch.setattr(native, 'status', uncertain)
        result, _ = asyncio.run(origin.operations.execute(origin.state, 'practical.job.start',
            {'retry_failed_execution_id': str(origin.handle.path)}, 'uncertain-retry'))
        assert result['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
    retried, _ = asyncio.run(origin.operations.execute(origin.state, 'practical.job.start',
        {'retry_failed_execution_id': str(origin.handle.path)}, 'explicit-retry'))
    new_handle = native.NativeJobHandle(Path(retried['facts']['requested_job']['execution_id']))
    assert native.wait_job(new_handle).returncode != 0
    assert new_handle != origin.handle and len(list(tmp_path.rglob('native.json'))) == 2
    assert origin.handle.read() == original_handle


@pytest.mark.parametrize('fault', ['command', 'policy', 'resource', 'workspace', 'invoke', 'request',
    'rehashed_request', 'owner', 'stdout', 'path', 'attempt', 'run', 'episode', 'operation', 'attempt_id'])
def test_original_owner_and_driver_ports_cannot_be_swapped(tmp_path, fault):
    state, key, handle = reserve(tmp_path)
    body, assigned = handle.read(), deepcopy(state.assignment)
    root = handle.path.parent
    if fault == 'command': body['command'] = ['/bin/true']
    elif fault == 'policy': body['metadata']['policy']['scratch_bytes'] += 1
    elif fault == 'resource': assigned['resource_id'] = 'other'
    elif fault == 'workspace': assigned['workspace'] = str(tmp_path / 'other')
    elif fault == 'invoke':
        path = root / 'invoke.json'
        value = json.loads(path.read_bytes()); value['argv'] = ['/bin/true']
        path.unlink(); _immutable(path, value)
    elif fault in {'request', 'rehashed_request'}:
        path = Path(body['paths']['request'])
        value = json.loads(path.read_bytes()); value['env']['TMPDIR'] = '/tmp'
        path.write_text(json.dumps(value))
        if fault == 'rehashed_request': body['request_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif fault == 'owner':
        (root / 'blast-attempt').mkdir()
        (root / 'blast-attempt/.native-blast-owner.json').write_text('{}')
    elif fault == 'stdout': body['stdout'] = str(root / 'other')
    elif fault == 'path': body['paths']['result'] = str(tmp_path / 'outside')
    else:
        path = root / 'blast-plan.json'
        value = json.loads(path.read_bytes())
        if fault == 'attempt': value['attempt_directory'] = str(root / 'other')
        else: value['identity'][{'run': 'run_id', 'episode': 'episode_id', 'operation': 'operation_key'}.get(fault, fault)] = 'other'
        path.unlink(); _immutable(path, value)
    handle.path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        local_blast_plan(assigned, str(handle.path))


def test_actual_practical_workflow_handoff_capture_and_saved_replay(tmp_path, monkeypatch):
    from gene_annotation_episode.native_blast_acquisition import capture_local_bundle
    from gene_annotation_episode.execution_progress import ExecutionTargetReader
    workspace = tmp_path / 'project'; workspace.mkdir()
    assigned = assignment(workspace, request(LABELS[1]))
    config = configuration(workspace, assigned['requested_job'])
    directory = tmp_path / 'run'
    descriptor = PracticalResourceEpisodes(None, directory=directory, resources={'local': config}).as_record()

    class Choices:
        def __init__(self, name='practical.job.start', arguments=None):
            self.calls, self.name, self.arguments = 0, name, arguments or {}
        async def complete(self, *args):
            self.calls += 1
            assert self.calls == 1
            return {'selection': {'kind': 'tool', 'tool': self.name, 'arguments': self.arguments}, 'report_update': {}}
        async def release(self, *args): pass

    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        scope = {'subject_refs': store.problem()['subject_refs']}
        def host(value, provider, key):
            flow = Workflow(store, ToolRegistry(store), provider, directory, 'workflow296',
                controller_factory=lambda path, initial: YieldController(str(path), initial, 0, YieldParameters(100, 50)),
                project_credit=lambda *_: 0, episode_binding_descriptors=[descriptor],
                role_credit_bindings={'launch_local': {'definition': {'version': 'fixture-units296'}, 'project': lambda *_: 0}},
                root_role='launch_local', execution_binding={'factory_module': 'fixture', 'factory_name': 'unused',
                    'arguments': {}, 'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64})
            episode = flow.build('launch_local', key, 'Execute selected paired BLAST and retain original handoff',
                scope, episode_assignment=value)
            async def perform():
                record = await episode.run_async(flow.context)
                await episode.build_result(record)
                return record
            record = asyncio.run(perform())
            state = flow.specialist(episode.source).state(flow.binding_context(episode.source))
            return flow, episode, record, state

        provider = Choices()
        flow, episode, record, state = host(assigned, provider, 'original')
        assert provider.calls == record.units_consumed == 1
        assert record.controller_state.history == (7,)
        assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
        original_receipts = state.receipts()
        execution = original_receipts[0]['outcome']['facts']['requested_job']['execution_id']
        handle = native.NativeJobHandle(Path(execution))
        assert native.wait_job(handle).returncode == 0
        action = flow.journal.row('runtime_actions', episode.source.episode_id, 0)
        handoff, = json.loads(action['result'])['record_refs']
        assert PracticalReceiptInformation(store, flow.run_id).read(handoff, scope)['receipt'] == original_receipts[0]
        reader = ExecutionTargetReader(store, run_id=flow.run_id, directory=directory,
            resources={'here': config}, api_execution=None)
        target = reader.read_target(handoff, scope)
        observed_identity = reader._native_identity(target)
        assert observed_identity['original_operation_key'] == original_receipts[0]['operation_key']
        assert observed_identity['attempt_id'] == digest(original_receipts[0]['operation_key'])
        captured = capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert captured['complete'] and len(captured['artifacts']) == 5
        plan = local_blast_plan(assigned, execution)
        received = deepcopy(assigned)
        received['assignment_id'] += '-receiver'
        received['endpoint'] = 'completed_job_outputs'
        received['progress_requirements'][0]['predicate'] = {
            'kind': 'requested_job_outputs', 'output_paths': [str(Path(plan['attempt_directory']) / 'bundle.json')]}
        _, _, observed, receiver_state = host(received, Choices('practical.job.collect', {'receipt_ref': handoff}), 'receiver')
        assert observed.units_consumed == 1 and receiver_state.completion_proof()
        assert state.receipts() == original_receipts
        snapshot = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in
            (handle.path, Path(plan['attempt_directory']) / 'bundle.json', Path(handle.read()['paths']['result']))}
        for name in ('start_prepared', 'start_job', 'resume_start', 'status'):
            monkeypatch.setattr(native, name, lambda *a, **k: pytest.fail('replay executed native work'))
        _, _, replay, _ = host(assigned, Choices(), 'original')
        assert replay.as_record() == record.as_record()
        assert capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == captured
        assert {name: (Path(name).read_bytes(), Path(name).stat().st_mtime_ns) for name in snapshot} == snapshot
        assert len(list(workspace.rglob('native.json'))) == 1
        (tmp_path / 'workflow-evidence.json').write_text(json.dumps({'target': target, 'capture': captured,
            'original_receipts': original_receipts, 'native_metadata': handle.read()['metadata'],
            'workflow_units': record.units_consumed, 'receiver_units': observed.units_consumed,
            'closed_history_unchanged': True, 'physical_handles': 1}, indent=2) + '\n')
