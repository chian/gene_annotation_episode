"""Real tiny HMMER jobs through selected local practical operations.

Fixture sequences are synthetic; native programs, systemd boundaries, durable
receipts and shared Workflow completion are real. No API, HPC or model runs.
These checks do not claim numerical result publication to a scientific parent.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, LAUNCH_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_hmmer_contracts import (
    compile_native_hmmer_job, requested_job_from_native,
)
from gene_annotation_episode.native_hmmer_driver import (
    run_native_hmmer, validate_native_hmmer_bundle_files,
)
from gene_annotation_episode.native_hmmer_local import local_hmmer_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldParameters
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import digest
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / 'verification/tool_graders_native_hmmer_producer_2026-10-24/runs'
POLICY = {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3, 'wall_seconds': None}
LABELS = ('hmmscan_search_ordinary', 'hmmsearch_search_ordinary', 'jackhmmer_search_ordinary',
          'nhmmer_sequence_ordinary', 'nhmmer_profile_ordinary', 'nhmmer_alignment_ordinary',
          'nhmmscan_search_ordinary', 'hmmalign_align_ordinary')


def request(label):
    retained = json.loads((PRODUCER / label / 'plan.json').read_text())['requested_job']
    value = requested_job_from_native(retained['native_hmmer'])
    assert value == retained
    return value


def binding_for(value):
    return {key: deepcopy(value['native_hmmer'][key]) for key in ('program', 'mode', 'software')}


def assignment(workspace, value, *, endpoint='usable_handoff', output_paths=None):
    predicate = ({'kind': 'requested_job_handoff'} if endpoint == 'usable_handoff' else
                 {'kind': 'requested_job_outputs', 'output_paths': output_paths})
    return {'version': 'practical_assignment_v1', 'assignment_id': 'native-hmmer-fixture',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': endpoint, 'requested_job': deepcopy(value),
        'progress_requirements': [{'key': 'endpoint', 'credit': 7, 'predicate': predicate}],
        'completion_keys': ['endpoint'], 'initial_context': {'revision': 0,
            'cwd': str(workspace), 'environment': {'UNRELATED_PREPARATION': 'not-in-job'}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


def launch_assignment(value):
    return {'version': LAUNCH_VERSION, 'requests': {'here': deepcopy(value)},
            'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
                'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)}}


@pytest.fixture
def host(tmp_path):
    workspace = tmp_path / 'project'
    workspace.mkdir()
    store = Store(tmp_path / 'store')
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    journal = Journal(store, 'native-hmmer-local-binding')
    configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
                     'native_hmmer': [binding_for(request(label)) for label in LABELS]}
    family = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=journal.run_id,
        resources={'here': configuration}, initial_information={}, tool_registry=ToolRegistry(store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=['stdout', 'stderr'])
    yield SimpleNamespace(store=store, journal=journal, family=family, workspace=workspace,
        configuration=configuration, scope={'subject_refs': [target]}, tmp_path=tmp_path)
    store.close()


def context(h, role, value, episode_id, *, parent=None):
    path = ((role, episode_id),) if parent is None else (*parent.path, (role, episode_id))
    message = {'message': {'scope': h.scope, 'episode_assignment': deepcopy(value)}}
    ctx = BindingContext(h.journal.run_id, episode_id, role, path, h.scope, value, message)
    with h.store.transaction():
        h.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(message), 'initial_credit': 0, 'state': 'running'})
    return ctx


def select(h, ctx, index, name, arguments=None):
    arguments = {} if arguments is None else arguments
    key = f'{ctx.run_id}:{ctx.episode_id}:{index}'
    with h.store.transaction():
        prior = h.journal.row('runtime_actions', ctx.episode_id, index)
        if prior is None:
            h.journal.save('runtime_actions', {'episode_id': ctx.episode_id, 'decision_index': index,
                'action': canonical({'kind': 'tool', 'tool': name, 'arguments': arguments}),
                'result': None, 'credit': None})
    result = asyncio.run(h.family.execute(ctx, name, arguments, key))
    with h.store.transaction():
        h.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (canonical(result), ctx.run_id, ctx.episode_id, index))
    return result


def start(h, label='hmmsearch_search_ordinary', *, complete=True):
    selected = assignment(h.workspace, request(label))
    parent = context(h, 'launch', launch_assignment(selected), 'launch-parent')
    accepted = h.family.prepare_assignment(parent, 'launch_local', selected, h.scope, 'commission-fixture')
    child = context(h, 'launch_local', accepted, 'native-child', parent=parent)
    h.family.initialize(child)
    outcome = select(h, child, 0, 'practical.job.start')
    assert outcome['status'] == 'completed'
    job = outcome['result']['outcome']['facts']['requested_job']
    handle = native.NativeJobHandle(Path(job['execution_id']))
    if complete:
        assert native.wait_job(handle).returncode == 0
    plan = local_hmmer_plan(selected, job['execution_id'])
    root = Path(plan['attempt_directory'])
    return SimpleNamespace(parent=parent, child=child, assignment=selected, outcome=outcome,
        job=job, handle=handle, plan=plan, root=root)


def receiver(h, origin, *, paths=None, name='receiver'):
    paths = paths or [str(origin.root / 'bundle.json')]
    selected = assignment(h.workspace, origin.assignment['requested_job'],
        endpoint='completed_job_outputs', output_paths=paths)
    selected['assignment_id'] += '-' + name
    ctx = context(h, 'launch_local', selected, name)
    h.family.initialize(ctx)
    return ctx


def native_snapshot(origin):
    body = origin.handle.read()
    return {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in
        [origin.handle.path, origin.root / 'bundle.json', Path(body['paths']['result'])]
        if path.is_file()}


@pytest.mark.parametrize('label', LABELS)
def test_all_modes_are_explicit_resource_commissioning_contracts(host, label):
    h = host
    value = request(label)
    selected = assignment(h.workspace, value)
    parent = context(h, 'launch', launch_assignment(selected), 'parent')
    assert h.family.prepare_assignment(parent, 'launch_local', selected, h.scope, 'unexecuted') == selected
    assert Draft202012Validator(h.family.assignment_schema('launch_local')).is_valid(selected)
    declarations = h.family.resource_tool_contracts()
    entry, = [item for item in declarations if item['name'] == 'native.' + value['native_hmmer']['program']]
    assert entry['resources'] == 'local'
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    assert Draft202012Validator(entry['input_schema']).is_valid(value)
    assert not list(h.workspace.rglob('native.json'))


@pytest.mark.parametrize('change', ['program', 'mode', 'executable', 'digest', 'engine_version', 'resource', 'argv', 'allocation'])
def test_selection_rejects_unbound_or_changed_original_work(host, change):
    h = host
    value = request('nhmmer_profile_ordinary')
    original = assignment(h.workspace, value)
    parent = context(h, 'launch', launch_assignment(original), 'parent')
    selected = deepcopy(original)
    if change in {'program', 'mode'}:
        label = 'hmmsearch_search_ordinary' if change == 'program' else 'nhmmer_sequence_ordinary'
        selected['requested_job'] = request(label)
    elif change in {'executable', 'digest', 'engine_version'}:
        job = selected['requested_job']['native_hmmer']
        field = 'sha256' if change == 'digest' else change
        job['software'][field] = {'executable': '/unbound/nhmmer', 'sha256': '0' * 64,
                                  'engine_version': 'unbound-version'}[field]
        selected['requested_job'] = requested_job_from_native(job)
    elif change == 'resource':
        selected['resource_id'] = 'not-bound'
    elif change == 'argv':
        selected['requested_job']['argv'] = ['/bin/true']
    else:
        selected['constraints']['allocation']['memory_bytes'] -= 1
    with pytest.raises(ValueError):
        h.family.prepare_assignment(parent, 'launch_local', selected, h.scope, 'unexecuted')
    # Program/mode substitutions are valid tools but not the parent's selected work.
    # Also exercise a resource that explicitly binds just the original mode.
    configuration = {**h.configuration, 'native_hmmer': [binding_for(value)]}
    if change in {'program', 'mode', 'executable', 'digest', 'engine_version'}:
        with pytest.raises(ValueError, match='program_mode_software_not_bound'):
            LocalPracticalOperations(configuration).validate_assignment(selected)
    assert not list(h.workspace.rglob('native.json'))


def test_hpc_native_binding_is_explicitly_unfinished(host):
    with pytest.raises(ValueError, match='native_hmmer_resource_execution_binding_unfinished:hpc'):
        ExecutionEpisodes(None, store=host.store, directory=host.tmp_path / 'hpc-unexecuted',
            run_id=host.journal.run_id, resources={'remote': {**host.configuration, 'kind': 'pbs_ssh'}},
            initial_information={}, tool_registry=host.family.tool_registry, handoff_unit=3,
            acquired_record_unit=2, log_window_bytes=128, log_roles=[])


@pytest.mark.parametrize('label', ['hmmsearch_search_ordinary', 'nhmmer_profile_ordinary', 'hmmalign_align_mapali'])
def test_real_native_start_seals_original_inputs_and_outputs_and_replays_once(host, label):
    h = host
    origin = start(h, label)
    bundle = json.loads((origin.root / 'bundle.json').read_text())
    request_value = origin.assignment['requested_job']
    assert origin.job['argv'] == request_value['argv']
    assert origin.job['environment'] == request_value['environment']
    assert origin.plan['policy'] == POLICY
    body = origin.handle.read()
    assert body['metadata']['policy'] == POLICY
    assert body['metadata']['verified_cgroup']['memory_max'] == POLICY['memory_bytes']
    assert body['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert body['metadata']['verified_cgroup']['runtime_max'] == 'infinity'
    assert body['command'][1:3] == ['-m', 'gene_annotation_episode.native_hmmer_driver']
    assert bundle['requested_job'] == request_value
    assert bundle['identity'] == origin.plan['identity']
    assert bundle['returncode'] == 0 and bundle['failures'] == []
    assert 'UNRELATED_PREPARATION' not in bundle['environment']
    staged = {row['role']: str(origin.root / row['relative_path']) for row in bundle['inputs']}
    assert bundle['realized_argv'] == compile_native_hmmer_job(request_value['native_hmmer'],
        input_paths=staged, output_directory=str(origin.root))['argv']
    assert bundle['realized_argv'] != request_value['argv']
    for supplied, retained in zip(request_value['native_hmmer']['operands'], bundle['inputs']):
        raw = (origin.root / retained['relative_path']).read_bytes()
        assert retained['role'] == supplied['role']
        assert retained['original_path'] == supplied['path']
        assert len(raw) == supplied['size_bytes'] == retained['size_bytes']
        assert hashlib.sha256(raw).hexdigest() == supplied['sha256'] == retained['actual_sha256']
    assert {row['role'] for row in bundle['artifacts']} == {
        row['role'] for row in request_value['native_hmmer']['outputs']}
    assert validate_native_hmmer_bundle_files(bundle, origin.root) == bundle
    assert h.family.state(origin.child).verify_completion(h.family.state(origin.child).completion_proof())
    snapshot = native_snapshot(origin)
    replay = select(h, origin.child, 0, 'practical.job.start')
    assert replay == origin.outcome
    assert native_snapshot(origin) == snapshot
    assert len(h.family.state(origin.child).receipts()) == 1
    assert len(list(h.workspace.rglob('native.json'))) == 1


def test_original_handoff_status_then_collect_observes_same_execution(host):
    h = host
    origin = start(h)
    original_receipts = deepcopy(h.family.state(origin.child).receipts())
    handoff, = origin.outcome['record_refs']
    missing = h.workspace / 'selected-but-missing-output'
    ctx = receiver(h, origin, paths=[str(origin.root / 'bundle.json'), str(missing)])
    status = select(h, ctx, 0, 'practical.job.status', {'receipt_ref': handoff})
    actual = status['result']['outcome']['facts']['requested_job']
    assert actual['execution_id'] == str(origin.handle.path)
    assert actual['status'] == 'completed' and actual['returncode'] == 0
    assert not h.family.state(ctx).completion_proof()
    assert h.family.state(ctx).credit_view()['credit'] == 0
    completed = receiver(h, origin, name='complete-receiver')
    result = select(h, completed, 0, 'practical.job.collect', {'receipt_ref': handoff})
    assert result['result']['outcome']['facts']['requested_job']['execution_id'] == str(origin.handle.path)
    assert h.family.state(completed).completion_proof()['endpoint'] == 'completed_job_outputs'
    assert h.family.state(completed).credit_view()['credit'] == 7
    assert h.family.state(origin.child).receipts() == original_receipts
    assert len(list(h.workspace.rglob('native.json'))) == 1


@pytest.mark.parametrize('name', ['practical.job.status', 'practical.job.collect'])
def test_changed_original_plan_is_rejected_by_selected_practical_observation(host, name):
    h = host
    origin = start(h)
    handoff, = origin.outcome['record_refs']
    ctx = receiver(h, origin)
    plan_path = origin.handle.path.parent / 'hmmer-plan.json'
    changed = deepcopy(origin.plan)
    changed['requested_job']['native_hmmer']['metadata']['tampered'] = True
    plan_path.write_text(canonical(changed) + '\n')
    with pytest.raises(ValueError, match='native_hmmer_original_attempt_conflict'):
        select(h, ctx, 0, name, {'receipt_ref': handoff})
    assert not h.family.state(ctx).completion_proof()


@pytest.mark.parametrize('field', ['run_id', 'episode_id', 'attempt_id', 'policy'])
def test_original_plan_owner_and_allocation_are_qualified(host, field):
    origin = start(host)
    changed = deepcopy(origin.plan)
    if field == 'policy':
        changed['policy']['scratch_bytes'] -= 1
    else:
        changed['identity'][field] = 'different-owner'
    (origin.handle.path.parent / 'hmmer-plan.json').write_text(canonical(changed) + '\n')
    # Even a matching changed owner cannot replace the original control
    # directory identities or the native handle's caller-owned allocation.
    (origin.root / '.native-hmmer-owner.json').write_text(json.dumps(changed) + '\n')
    with pytest.raises(ValueError, match='native_hmmer_original_attempt_conflict'):
        local_hmmer_plan(origin.assignment, str(origin.handle.path))


def test_native_handle_command_working_directory_and_policy_are_qualified(host):
    origin = start(host)
    original = origin.handle.read()
    for field in ('command', 'cwd', 'policy'):
        changed = deepcopy(original)
        if field == 'command':
            changed['command'][-1] = str(origin.handle.path.parent / 'other-plan.json')
        elif field == 'cwd':
            changed['cwd'] = str(host.workspace)
        else:
            changed['metadata']['policy']['memory_bytes'] -= 1
        origin.handle.path.write_text(json.dumps(changed) + '\n')
        with pytest.raises(ValueError, match='native_hmmer_original_attempt_conflict'):
            local_hmmer_plan(origin.assignment, str(origin.handle.path))
        origin.handle.path.write_text(json.dumps(original) + '\n')
    assert local_hmmer_plan(origin.assignment, str(origin.handle.path)) == origin.plan


def test_changed_sealed_native_output_rejected_by_producer_replay(host):
    origin = start(host)
    manifest = origin.root / 'bundle.json'
    saved_manifest = manifest.read_bytes()
    bundle = json.loads(saved_manifest)
    artifact = next(row for row in bundle['artifacts'] if row['role'] == 'tblout')
    path = origin.root / artifact['relative_path']
    path.write_bytes(path.read_bytes() + b'# changed after original seal\n')
    before = native_snapshot(origin)
    with pytest.raises(ValueError, match='native_hmmer_sealed_artifact_digest_mismatch'):
        run_native_hmmer(origin.plan)
    assert manifest.read_bytes() == saved_manifest
    assert native_snapshot(origin) == before


def test_unsealed_original_attempt_cannot_rerun_selected_native_job(host):
    h = host
    origin = start(h)
    (origin.root / 'bundle.json').rename(origin.root / 'withheld-bundle.json')
    before = native_snapshot(origin)
    with pytest.raises(ValueError, match='native_hmmer_unsealed_attempt_execution_uncertain'):
        run_native_hmmer(origin.plan)
    assert select(h, origin.child, 0, 'practical.job.start') == origin.outcome
    assert not (origin.root / 'bundle.json').exists()
    assert native_snapshot(origin) == before
    assert len(list(h.workspace.rglob('native.json'))) == 1


def test_recovery_of_unfinished_selection_reuses_uncertain_original_handle(host):
    h = host
    selected = assignment(h.workspace, request('hmmsearch_search_ordinary'))
    child = context(h, 'launch_local', selected, 'pending-child')
    h.family.initialize(child)
    state = h.family.state(child)
    key = f'{child.run_id}:{child.episode_id}:0'
    state.begin(key, 'practical.job.start', {})
    # Execute the real selected primitive but simulate loss before state.finish.
    operations = LocalPracticalOperations(h.configuration)
    actual, _ = asyncio.run(operations.execute(state, 'practical.job.start', {}, key))
    handle = native.NativeJobHandle(Path(actual['facts']['requested_job']['execution_id']))
    assert native.wait_job(handle).returncode == 0
    original_handle = handle.read()
    for name in ('result', 'status'):
        path = Path(original_handle['paths'][name])
        path.rename(path.with_name(path.name + '.withheld'))
    assert native.status(handle)['state'] == 'execution_unknown'
    outcome = select(h, child, 0, 'practical.job.start')
    assert outcome['result']['outcome']['facts']['requested_job']['status'] == 'unknown'
    assert outcome['result']['outcome']['facts']['requested_job']['execution_id'] == str(handle.path)
    assert not state.completion_proof()
    assert handle.read() == original_handle
    assert len(list(h.workspace.rglob('native.json'))) == 1
    assert len(state.receipts()) == 1


def test_shared_workflow_launch_child_return_and_receiver_complete_without_extra_turn(host):
    h = host
    selected = assignment(h.workspace, request('hmmsearch_search_ordinary'))
    factory = ExecutionServiceFactory(resources={'here': h.configuration}, initial_information={},
        handoff_unit=3, acquired_record_unit=2, monitoring_information_unit=1,
        log_window_bytes=128, log_roles=('stdout', 'stderr'))
    form = {'type': 'object', 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'handoffs': h.family.fact_sources('launch_local')['execution_handoff_refs']['report_schema']},
        'required': ['completed', 'handoffs'], 'additionalProperties': False}

    class Choices:
        def __init__(self, collect_ref=None):
            self.calls = []
            self.collect_ref = collect_ref

        async def complete(self, episode_id, role, instructions, context, schema):
            self.calls.append((episode_id, deepcopy(context)))
            if 'practical_assignment' in context:
                name = 'practical.job.collect' if self.collect_ref else 'practical.job.start'
                arguments = {'receipt_ref': self.collect_ref} if self.collect_ref else {}
                return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments}, 'report_update': {}}
            assert len(self.calls) == 1
            return {'selection': {'kind': 'episode_child', 'role': 'launch_local',
                'goal': 'Execute the exact selected HMMER job and return its usable handoff',
                'scope': h.scope, 'purpose': 'Receive the original requested native execution',
                'assignment': selected, 'schema_json': json.dumps(form), 'initial_report_json': '{}'},
                'report_update': {}}

        async def release(self, episode_id):
            pass

    def workflow(provider, root_role):
        return Workflow(h.store, ToolRegistry(h.store), provider, h.tmp_path / 'workflow',
            'native-hmmer-full-workflow', controller_factory=lambda path, initial:
                YieldController(str(path), initial, 0, YieldParameters(100, 50)),
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), root_role=root_role,
            episode_record_receipts=True, initial_known_record_refs=[])

    async def run(episode, flow):
        record = await episode.run_async(flow.context)
        await episode.build_result(record)
        return record

    provider = Choices()
    flow = workflow(provider, 'launch')
    episode = flow.build('launch', 'root', 'Obtain the selected native HMMER handoff', h.scope,
        episode_assignment=launch_assignment(selected))
    record = asyncio.run(run(episode, flow))
    assert len(provider.calls) == 2
    assert record.units_consumed == 1 and record.controller_state.history == (3,)
    assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
    child_record = record.unit_records[0].child
    assert child_record.units_consumed == 1 and child_record.controller_state.history == (7,)
    assert child_record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
    child_action = flow.journal.row('runtime_actions', child_record.episode_id, 0)
    result = json.loads(child_action['result'])
    handoff, = result['record_refs']
    job = result['result']['outcome']['facts']['requested_job']
    handle = native.NativeJobHandle(Path(job['execution_id']))
    assert native.wait_job(handle).returncode == 0
    plan = local_hmmer_plan(selected, str(handle.path))
    source = PracticalReceiptInformation(h.store, flow.run_id).read(handoff, h.scope)
    assert source['receipt'] == result['result']
    before = [tuple(row) for row in h.store.db.execute(
        'SELECT episode_id,unit_index,observation FROM runtime_observations WHERE run_id=?', (flow.run_id,))]
    assert len(before) == 2
    received = assignment(h.workspace, selected['requested_job'], endpoint='completed_job_outputs',
        output_paths=[str(Path(plan['attempt_directory']) / 'bundle.json')])
    received['assignment_id'] += '-receive'
    receiver_provider = Choices(handoff)
    receiving_flow = workflow(receiver_provider, 'launch_local')
    receiving_episode = receiving_flow.build('launch_local', 'receiver', 'Validate original HMMER output custody',
        h.scope, episode_assignment=received)
    received_record = asyncio.run(run(receiving_episode, receiving_flow))
    assert len(receiver_provider.calls) == received_record.units_consumed == 1
    assert received_record.controller_state.history == (7,)
    assert received_record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
    assert len(list(h.workspace.rglob('native.json'))) == 1
    after = [tuple(row) for row in h.store.db.execute(
        'SELECT episode_id,unit_index,observation FROM runtime_observations WHERE run_id=?', (flow.run_id,))]
    assert len(after) == 3
    assert all(row in after for row in before)
