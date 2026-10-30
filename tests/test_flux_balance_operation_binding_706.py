"""Selected FBA operation custody with real Store/state and operational status controls.

The supplied704 model/software fixtures and native status/dispatch controls are
synthetic operational metadata, never scientific measurements or a solver run.
Original688 saved bytes are read only for output/window checks.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_progress import ExecutionProgressProvider, ExecutionTargetReader, describe_execution_target
from gene_annotation_episode.native_flux_balance_contracts import POLICY
from gene_annotation_episode.native_flux_balance_local import local_flux_balance_plan
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from test_flux_balance_execution_inputs_704 import selected

pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')
REAL_PREPARE = native.prepare_job
ROOT = Path(__file__).resolve().parents[1]
SAVED = ROOT / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions/sbml'


@pytest.fixture
def case(selected, monkeypatch, tmp_path):
    f = selected
    # A selected completed-output endpoint remains open while synthetic status
    # is being investigated; usable handoff would correctly close at first start.
    assignment = deepcopy(f.assignment)
    assignment['endpoint'] = 'completed_job_outputs'
    assignment['progress_requirements'] = [{'key': 'outputs', 'credit': 1,
        'predicate': {'kind': 'requested_job_outputs', 'output_paths': [str(f.workspace / 'requested-final-marker')]}}]
    assignment['completion_keys'] = ['outputs']
    launch = deepcopy(plain(f.parent.assignment))
    launch['requests']['selected-local'] = deepcopy(assignment)
    f.parent = f.records.child(f.records.root, 'launch', launch, 1)
    context = f.records.child(f.parent, 'launch_local', assignment, 0)
    control = f.inputs.initialize(context)
    state = PracticalState(f.owner.directory / 'practical-execution' / digest({
        'run_id': context.run_id, 'episode_id': context.episode_id}), context.run_id, context.episode_id, plain(context.assignment))
    job = state.assignment['requested_job']['native_flux_balance']
    config = {'kind': 'local', 'workspace': str(f.workspace), 'policy': deepcopy(POLICY),
        'native_flux_balance': [{'version': 'flux_balance_local_binding_v1',
            'operation': job['operation'], 'mode': job['mode'], 'software': deepcopy(job['software']),
            'model_formats': ['cobra_json', 'sbml']}]}
    reads, dispatches, prepares = [], [], []
    def reader(actual):
        assert actual is state
        reads.append(actual)
        return f.inputs.for_start(actual)
    def prepare(*args, **kwargs):
        prepares.append((args, kwargs))
        return REAL_PREPARE(*args, **kwargs)
    def dispatch(handle):
        assert handle.read()['stage'] == 'prepared'
        dispatches.append(str(handle.path))
        return handle
    view = {'state': 'running', 'terminal': False, 'quiescent': False,
        'metadata': {'native_returncode': None, 'policy': deepcopy(POLICY)}}
    monkeypatch.setattr(native, 'prepare_job', prepare)
    monkeypatch.setattr(native, 'start_prepared', dispatch)
    monkeypatch.setattr(native, 'status', lambda handle: deepcopy(view))
    operations = LocalPracticalOperations(config, flux_balance_input_reader=reader)
    receipt_reader = PracticalReceiptInformation(f.store, context.run_id)
    def action(tool='practical.job.start', arguments=None, *, finish=True, owner=state, bound=context):
        arguments = arguments or {}
        index = len(owner.receipts())
        key = f'{owner.run_id}:{owner.episode_id}:{index}'
        f.records.journal.save('runtime_actions', {'episode_id': owner.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': arguments}),
            'result': None, 'credit': None})
        owner.begin(key, tool, arguments)
        outcome, updated = operations._execute(owner, tool, arguments, key)
        if not finish: return outcome, updated, key
        validations = assess_validations(owner.assignment, outcome, owner.context(), tool_name=tool)
        receipt = owner.finish(key, outcome, validations, context_after=updated)
        ref = receipt_reader.publish(bound, receipt)
        return receipt, ref
    return SimpleNamespace(f=f, context=context, state=state, control=control, config=config,
        operations=operations, reads=reads, dispatches=dispatches, prepares=prepares,
        view=view, action=action, receipts=receipt_reader)


def test_selected_start_uses_701_and_preserves_input_file_and_original_facts(case):
    c = case
    receipt, ref = c.action()
    outcome = receipt['outcome'];job = outcome['facts']['requested_job'];detail = outcome['native_outcome']
    assert c.reads == [c.state] and len(c.prepares) == len(c.dispatches) == 1
    execution = job['execution_id']
    plan = local_flux_balance_plan(c.state.assignment, execution)
    assert Path(c.prepares[0][1]['cwd']) == Path(execution).parent
    assert c.prepares[0][0][0][2:5] == ['-S', '-m', 'gene_annotation_episode.native_flux_balance_driver']
    assert job['argv'] == c.state.assignment['requested_job']['argv']
    assert job['environment'] == c.state.assignment['requested_job']['environment']
    assert job['requested_job_sha256'] == digest(c.state.assignment['requested_job'])
    assert job['output_paths'] == sorted(str(Path(plan['attempt_directory']) / row['relative_path']) for row in plan['outputs'])
    assert detail['native_flux_balance_input_binding_file'] == c.control['file']
    assert detail['attempt_operation_key'] == receipt['operation_key']
    assert detail['attempt_id'] == digest(receipt['operation_key'])
    assert 'native_flux_balance_input_binding_file' not in canonical(c.state.assignment)
    assert c.receipts.read(ref, c.context.scope)['receipt'] == receipt
    assert len(c.state.receipts()) == 1
    # Ordinary reopening and explicitly selected status reuse the original handle;
    # no input callback is needed for either operation.
    c.operations.flux_balance_input_reader = None
    for tool in ('practical.job.start', 'practical.job.status', 'practical.job.collect'):
        repeated, _ = c.action(tool)
        assert repeated['outcome']['facts']['requested_job']['execution_id'] == execution
        assert repeated['outcome']['native_outcome']['native_flux_balance_input_binding_file'] == c.control['file']
    assert len(c.dispatches) == len(c.prepares) == 1 and len(c.reads) == 1


@pytest.mark.parametrize('fault', ['unbound', 'format', 'software', 'kind', 'resource', 'workspace', 'memory', 'scratch', 'wall', 'constraint'])
def test_exact_binding_allocation_and_resource_rejections(case, fault):
    c = case;assignment = deepcopy(c.state.assignment);config = deepcopy(c.config)
    if fault == 'unbound': config.pop('native_flux_balance')
    elif fault == 'format': config['native_flux_balance'][0]['model_formats'] = ['sbml']
    elif fault == 'software': config['native_flux_balance'][0]['software']['python_version'] = 'different'
    elif fault == 'kind': assignment['resource_kind'] = 'hpc'
    elif fault == 'resource': assignment.pop('resource_id')
    elif fault == 'workspace': assignment['workspace'] = str(Path(c.config['workspace']).parent / 'other')
    elif fault == 'memory': config['policy']['memory_bytes'] -= 1
    elif fault == 'scratch': config['policy']['scratch_bytes'] -= 1
    elif fault == 'wall': config['policy']['wall_seconds'] = 1
    else: assignment['constraints']['allocation']['memory_bytes'] -= 1
    with pytest.raises(ValueError): LocalPracticalOperations(config).validate_assignment(assignment)
    assert not c.prepares and not c.dispatches


@pytest.mark.parametrize('reader', [None, lambda state: {}, lambda state: {'receipt': {}, 'file': {}, 'extra': 1}])
def test_missing_or_malformed_reader_never_falls_back(case, reader):
    c = case;c.operations.flux_balance_input_reader = reader
    with pytest.raises(ValueError, match='native_flux_balance_input_'): c.action(finish=False)
    assert not c.prepares and not c.dispatches
    assert not list(c.f.workspace.rglob('invoke.py'))


def test_reader_is_not_serialized_and_only_local_receives_it(case):
    c = case
    with pytest.raises(ValueError, match='input_reader_invalid'): LocalPracticalOperations(c.config, flux_balance_input_reader=4)
    practical = PracticalResourceEpisodes(None, directory=c.f.owner.directory, resources={'local': c.config},
        flux_balance_input_reader=c.operations.flux_balance_input_reader)
    assert practical._operations('local').flux_balance_input_reader is c.operations.flux_balance_input_reader
    assert 'flux_balance_input_reader' not in canonical(practical.as_record())


@pytest.mark.parametrize('fault', ['wrong_id', 'active', 'unknown_rc', 'killed', 'uncertain', 'unquiet'])
def test_selected_retry_rejects_nonoriginal_or_not_failed_without_replacing(case, fault):
    c = case;receipt, _ = c.action();execution = receipt['outcome']['facts']['requested_job']['execution_id']
    c.view.update(state='returned', terminal=True, quiescent=True)
    c.view['metadata']['native_returncode'] = 3
    if fault == 'active': c.view.update(state='running', terminal=False, quiescent=False)
    elif fault == 'unknown_rc': c.view['metadata']['native_returncode'] = None
    elif fault == 'killed': c.view['metadata']['service_exit'] = {'EXIT_CODE': 'killed'}
    elif fault == 'uncertain': c.view['state'] = 'unknown'
    elif fault == 'unquiet': c.view['quiescent'] = False
    outcome, _, _ = c.action(arguments={'retry_failed_execution_id': execution + '-other' if fault == 'wrong_id' else execution}, finish=False)
    assert outcome['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
    assert outcome['native_outcome']['native_flux_balance_input_binding_file'] == c.control['file']
    assert len(c.prepares) == len(c.dispatches) == len(c.reads) == 1


def test_explicit_failed_retry_has_new_selected_attempt_and_same_input_control(case):
    c = case;old, _ = c.action();execution = old['outcome']['facts']['requested_job']['execution_id']
    c.view.update(state='returned', terminal=True, quiescent=True);c.view['metadata']['native_returncode'] = 2
    new, _ = c.action(arguments={'retry_failed_execution_id': execution})
    assert new['operation_key'] != old['operation_key']
    assert new['outcome']['facts']['requested_job']['execution_id'] != execution
    assert new['outcome']['native_outcome']['native_flux_balance_input_binding_file'] == c.control['file']
    assert len(c.prepares) == len(c.dispatches) == len(c.reads) == 2
    assert c.state.receipts()[0] == old


def _reader(c):
    return ExecutionTargetReader(c.f.store, run_id=c.state.run_id, directory=c.f.owner.directory,
        resources={'selected-local': c.config}, api_execution=None)


def test_historical_failed_target_needs_no_native_or_current_source_files(case, monkeypatch):
    c = case;c.view.update(state='returned', terminal=True, quiescent=True);c.view['metadata']['native_returncode'] = 2
    receipt, ref = c.action();reader = _reader(c)
    execution = receipt['outcome']['facts']['requested_job']['execution_id']
    shutil.rmtree(Path(execution).parent)
    monkeypatch.setattr(native, 'status', lambda *_: pytest.fail('historical target polled native status'))
    old = c.f.store.get
    def get(reference):
        assert reference != c.f.source, 'historical target rebound current scientific source'
        return old(reference)
    monkeypatch.setattr(c.f.store, 'get', get)
    target = reader.read_target(ref, c.context.scope)
    assert target['origin_episode_id'] == c.state.episode_id and target['execution_id'] == execution
    assert reader.returnable_handoff(target) and not reader.usable_handoff(target)
    metadata = describe_execution_target(target)
    assert metadata['operation'] == 'perform_flux_balance_analysis'
    assert metadata['input_format'] == 'cobra_json' and metadata['output_format'] == 'flux_balance_native_manifest_v1'
    assert len(c.state.receipts()) == 1


@pytest.mark.parametrize('field', ['run_id', 'origin_episode_id', 'original_operation_key', 'attempt_id', 'resource_id', 'requested_job_sha256', 'native_flux_balance_input_binding_file'])
def test_live_identity_conflicts_rejected_before_native_observe_or_read(case, monkeypatch, field):
    c = case;receipt, ref = c.action();reader = _reader(c);target = reader.read_target(ref, c.context.scope)
    identity = reader._native_identity(target);identity[field] = {} if field.endswith('_file') else 'wrong'
    monkeypatch.setattr(native, 'status', lambda *_: pytest.fail('identity conflict reached polling'))
    for port in ('observe', 'read'):
        with pytest.raises(ValueError):
            if port == 'observe': c.operations.observe_execution(c.state.assignment, target['execution_id'], **identity)
            else: c.operations.read_output(c.state.assignment, target['execution_id'], path=target['execution_id'], offset=0, limit=1, **identity)


def test_saved_native_output_windows_have_original_paths_and_writer_closure(case):
    c = case;receipt, ref = c.action();execution = receipt['outcome']['facts']['requested_job']['execution_id']
    plan = local_flux_balance_plan(c.state.assignment, execution);attempt = Path(plan['attempt_directory'])
    # Real original688 emitted bytes are copied, never replaced with a claimed
    # optimizer result. Their retained format differs from this operational
    # fixture's synthetic model and is deliberately not scientifically graded.
    original = json.loads((SAVED / 'selected-plan.json').read_text())
    source_attempt = Path(original['attempt_directory'])
    for row in plan['outputs']:
        source_row = next(x for x in original['outputs'] if x['role'] == row['role'])
        src = SAVED / Path(source_row['relative_path'])
        if not src.exists(): src = source_attempt / source_row['relative_path']
        destination = attempt / row['relative_path'];destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(src.read_bytes())
    Path(execution).with_name('stdout.log').write_bytes(b'operational log window\n')
    reader = _reader(c);target = reader.read_target(ref, c.context.scope)
    identity = reader._native_identity(target)
    observed = c.operations.observe_execution(c.state.assignment, execution, log_window_bytes=7,
        log_roles=('stdout', 'native_log'), **identity)
    assert len(observed['outputs']) == 10 and observed['result_available']
    assert all(not x['writer_closed'] for x in observed['outputs'])
    assert [row['role'] for row in observed['logs']] == ['stdout', 'native_log']
    assert all(len(__import__('base64').b64decode(x['bytes_base64'])) <= 7 for x in observed['logs'])
    output = attempt / plan['outputs'][0]['relative_path']
    result = c.operations.read_output(c.state.assignment, execution, path=str(output), offset=2, limit=5, **identity)
    assert __import__('base64').b64decode(result['bytes_base64']) == output.read_bytes()[2:7]
    c.view.update(state='returned', terminal=True, quiescent=False);c.view['metadata']['native_returncode'] = 2
    observed = c.operations.observe_execution(c.state.assignment, execution, **identity)
    assert observed['state'] == 'failed' and not any(x['writer_closed'] for x in observed['outputs'])
    c.view['quiescent'] = True
    observed = c.operations.observe_execution(c.state.assignment, execution, **identity)
    assert all(x['writer_closed'] for x in observed['outputs'])
    for path in (execution, str(Path(execution).with_name('invoke.json')), str(attempt / 'unselected')):
        with pytest.raises(ValueError, match='original_output_path_required'):
            c.operations.read_output(c.state.assignment, execution, path=path, offset=0, limit=1, **identity)
    assert len(c.state.receipts()) == 1


@pytest.mark.parametrize('control', [None, {'receipt': {}, 'file': {}}])
def test_public_selected_missing_control_is_structured_failure(case, control):
    c = case;c.operations.flux_balance_input_reader = None if control is None else lambda _: control
    key = f'{c.state.run_id}:{c.state.episode_id}:0'
    c.state.begin(key, 'practical.job.start', {})
    outcome, updated = asyncio.run(c.operations.execute(c.state, 'practical.job.start', {}, key))
    code = 'native_flux_balance_input_reader_required' if control is None else 'native_flux_balance_input_control_invalid'
    assert outcome == {'facts': {}, 'native_outcome': {'failure': {'code': code}}}
    assert updated is None and not c.prepares and not c.dispatches


def test_forwarded_selected_status_collect_preserves_original_owner_and_outputs(case):
    c = case;start, original_ref = c.action()
    practical = PracticalResourceEpisodes(None, directory=c.f.owner.directory, resources={'local': c.config}, store=c.f.store)
    context = c.f.records.child(c.f.parent, 'launch_local', deepcopy(c.state.assignment), 1)
    practical.state(context)
    source_ref = original_ref
    reader = _reader(c)
    original_target = reader.read_target(original_ref, c.context.scope)
    for index, tool in enumerate(('practical.job.status', 'practical.job.collect')):
        arguments = {'receipt_ref': source_ref}
        c.f.records.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': arguments}), 'result': None, 'credit': None})
        result = asyncio.run(practical.execute(context, tool, arguments, f'{context.run_id}:{context.episode_id}:{index}'))
        assert result['status'] == 'completed', result
        source_ref = result['record_refs'][0]
        receipt = result['result']
        assert receipt['episode_id'] == context.episode_id
        assert receipt['outcome']['facts']['requested_job']['output_paths'] == start['outcome']['facts']['requested_job']['output_paths']
        assert receipt['outcome']['native_outcome']['native_flux_balance_input_binding_file'] == c.control['file']
        target = reader.read_target(source_ref, context.scope)
        assert target['origin_episode_id'] == original_target['origin_episode_id']
        assert target['execution_id'] == original_target['execution_id']
        assert reader._native_identity(target)['native_flux_balance_input_binding_file'] == c.control['file']
    assert len(c.state.receipts()) == 1 and len(practical.state(context).receipts()) == 2
    assert len(c.prepares) == len(c.dispatches) == 1


@pytest.mark.parametrize('fault', ['file', 'path', 'operation', 'resource', 'request'])
def test_forwarded_frozen_receipt_conflict_cannot_change_original_target(case, fault):
    c = case;start, ref = c.action()
    assignment = deepcopy(c.state.assignment)
    if fault == 'resource': assignment['resource_id'] = 'different-local'
    context = c.f.records.child(c.f.parent, 'launch_local', assignment, 2)
    state = PracticalState(c.f.owner.directory / 'forged-operational-receiver', context.run_id, context.episode_id, assignment)
    key = f'{context.run_id}:{context.episode_id}:0';arguments = {'receipt_ref': ref}
    c.f.records.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': 'practical.job.status', 'arguments': arguments}), 'result': None, 'credit': None})
    state.begin(key, 'practical.job.status', arguments)
    outcome = deepcopy(start['outcome']);job = outcome['facts']['requested_job'];detail = outcome['native_outcome']
    if fault == 'file': detail['native_flux_balance_input_binding_file']['size_bytes'] += 1
    elif fault == 'path': job['execution_id'] = job['handoff']['execution_id'] = str(c.f.workspace / 'other/native.json')
    elif fault == 'operation': detail['attempt_operation_key'] = f'{context.run_id}:{context.episode_id}:0'
    elif fault == 'request': job['requested_job_sha256'] = 'f' * 64
    validations = assess_validations(assignment, outcome, state.context(), tool_name='practical.job.status')
    receipt = state.finish(key, outcome, validations)
    source = c.receipts.publish(context, receipt)
    with pytest.raises(ValueError): _reader(c).read_target(source, context.scope)
    assert len(c.prepares) == len(c.dispatches) == 1


@pytest.mark.parametrize('fault', [None, 'wrong_path', 'unavailable'])
def test_progress_public_ports_observe_and_read_original_declared_log(case, monkeypatch, fault):
    c = case;receipt, ref = c.action()
    execution = receipt['outcome']['facts']['requested_job']['execution_id']
    plan = local_flux_balance_plan(c.state.assignment, execution)
    original = json.loads((SAVED / 'selected-plan.json').read_text())
    source_row = next(x for x in original['outputs'] if x['role'] == 'native_log')
    raw = (Path(original['attempt_directory']) / source_row['relative_path']).read_bytes()
    row = next(x for x in plan['outputs'] if x['role'] == 'native_log')
    path = Path(plan['attempt_directory']) / row['relative_path'];path.parent.mkdir(parents=True);path.write_bytes(raw)
    reader = _reader(c);reader.log_roles = ('native_log',);reader.log_window_bytes = 9
    target = reader.read_target(ref, c.context.scope)
    observation = reader.observe_target(target, operation_key='selected-progress-observation')
    assert observation['state'] == 'running' and observation['result_available']
    assert len(observation['outputs']) == 10
    assert observation['logs'][0]['role'] == 'native_log'
    assert observation['native']['native_flux_balance_input_binding_file'] == c.control['file']
    bounded = reader.read_file(target, path=str(path), offset=1, limit=7)
    assert __import__('base64').b64decode(bounded['bytes_base64']) == raw[1:8]
    if fault is not None:
        changed = deepcopy(observation)
        if fault == 'wrong_path': changed['logs'][0]['path'] = str(path) + '-unselected'
        else:
            selected_output = next(x for x in changed['outputs'] if x['role'] == 'requested_output:' + str(path))
            selected_output.update(available=False, bytes=None, writer_closed=False)
        monkeypatch.setattr(reader.operations['selected-local'], 'observe_execution', lambda *_a, **_k: changed)
        with pytest.raises(ValueError, match='invalid_resource_progress_observation'):
            reader.observe_target(target, operation_key='selected-invalid-log-relationship')
    assert len(c.state.receipts()) == len(c.prepares) == len(c.dispatches) == 1


@pytest.mark.parametrize('binding', ['exact', 'missing', 'empty', 'invalid'])
def test_progress_native_log_option_requires_actual_configured_fba_binding(case, binding):
    c = case;config = deepcopy(c.config)
    if binding == 'missing': config.pop('native_flux_balance')
    elif binding == 'empty': config['native_flux_balance'] = []
    elif binding == 'invalid': config['native_flux_balance'][0]['mode'] = 'unbound'
    def make():
        return ExecutionProgressProvider(c.f.store, run_id=c.state.run_id, directory=c.f.owner.directory,
            resources={'selected-local': config}, api_execution=None, log_window_bytes=13, log_roles=('native_log',))
    if binding != 'exact':
        with pytest.raises(ValueError): make()
    else:
        provider = make()
        assert provider.log_roles == provider.targets.log_roles == ('native_log',)
        assert provider.as_record()['configuration']['log_roles'] == ['native_log']
        generic = deepcopy(c.state.assignment)
        generic['requested_job'] = {'argv': ['/bin/true'], 'environment': {}}
        generic.pop('native_flux_balance_execution')
        with pytest.raises(ValueError, match='unsupported_native_log_role'):
            provider.targets.operations['selected-local'].observe_execution(generic, '/not-polled', log_roles=('native_log',))
