"""Baselineable original behavior and explicit post-split connection checks.

Every controlled operation is named here. Native/API admission is never
patched into success. Full returned payloads and exception types are retained.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import inspect
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from .api_cases import Case, HOMES, Responses, assignment, canonical, error_record, module, outcome, prepare_decision, rows, task_case


@pytest.fixture(params=HOMES, ids=HOMES)
def case(request, tmp_path):
    value = Case(tmp_path, request.param)
    try:
        yield value
    finally:
        value.close()


@pytest.fixture(params=HOMES[:2], ids=HOMES[:2])
def nonhpc_case(request, tmp_path):
    value = Case(tmp_path, request.param)
    try:
        yield value
    finally:
        value.close()


def retained(record_property, name, value):
    record_property(name, json.dumps(canonical(value), sort_keys=True, allow_nan=False))


def compare_original_property(request, name, value):
    if os.environ.get('A104_API_PHASE') != 'connected':
        return
    evidence = json.loads(Path(os.environ['A104_API_BASELINE_EVIDENCE']).read_text())
    recorded = [json.loads(payload) for row in evidence['reports']
        if row['nodeid'] == request.node.nodeid and row['phase'] == 'call'
        for key, payload in row['properties'] if key == name]
    assert len(recorded) == 1, ('original_callback_provenance_not_captured', request.node.nodeid, name)
    assert canonical(value) == recorded[0], ('original_callback_or_controller_identity_changed', value, recorded[0])


def test_actual_factory_constructor_and_private_dispatch(case, record_property):
    descriptor = case.binding.as_record()
    assert descriptor['binding_id'] == case.home
    assert descriptor['configuration']['resources'] == case.options['resources']
    for key in ('initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes',
                'task_yield_profiles'):
        assert descriptor['configuration'][key] == case.options[key]
    assert descriptor['configuration']['log_roles'] == ['stdout', 'stderr']
    protected = module(case.home + '/protected_reference_access').ProtectedReferenceAccess
    assert type(case.binding).__bases__[0] is protected
    task = task_case(case).task
    selected = getattr(case.binding, 'decision_source_type', module('runtime').DecisionSource)
    assert type(task) is selected
    if os.environ.get('A104_API_PHASE') == 'connected':
        assert selected.__module__ == type(case.binding).__module__.removesuffix('.episode') + '.task'
        assert not isinstance(task, module('runtime').DecisionSource)
        assert case.binding.decision_prompt_renderer.presentation_protocol == 'episode_context_presentation_v1'
    retained(record_property, 'original_factory', {'home': case.home,
        'factory': None if case.factory is None else case.factory.__module__ + '.' + case.factory.__name__,
        'direct_axis_factory_absent': case.factory is None,
        'binding_descriptor': descriptor, 'family': [v.as_record() for v in case.family],
        'controlled_context': case.context.as_record(), 'task_type': selected.__module__ + '.' + selected.__qualname__})


def test_real_service_iterator_payload_credit_and_original_replay(case, record_property):
    fixture = task_case(case)
    selection = {'kind': 'tool', 'tool': 'api.uniprot.record', 'arguments': {}}
    value = asyncio.run(fixture.task.execute(selection, 0))
    action = dict(case.journal.row('runtime_actions', case.episode_id, 0))
    payload = json.loads(action['result'])
    assert payload['status'] == 'completed' and payload['record_refs']
    assert json.loads(action['action']) == selection and action['credit'] == case.options['handoff_unit']
    assert value.as_record()['credit'] == case.options['handoff_unit']
    key = f'{case.run_id}:{case.episode_id}:0'
    assert fixture.executions == [key] and len(fixture.observations) == len(fixture.projections) == 1
    proof = case.binding.completion_for_action(case.context, key)
    assert proof and case.binding.verify_completion(case.context, proof)
    assert not case.binding.verify_completion(case.context, {**proof, 'receipt_sha256': '0' * 64})
    before = rows(case.store)
    assert asyncio.run(fixture.task.execute(selection, 0)).as_record() == value.as_record()
    assert rows(case.store) == before and len(case.client.calls) == 1
    assert len(fixture.observations) == len(fixture.projections) == 1
    assert fixture.task.last_outcome == payload
    assert case.store.count('annotation') == 0
    retained(record_property, 'service_iterator', {'selection': selection, 'action_row': action,
        'returned_payload': payload, 'controller_input': value.as_record(), 'proof': proof,
        'credit_view': fixture.projections[0], 'transport': case.client.calls,
        'receipt_rows': before['runtime_record_receipts'], 'replay_all_logical_rows_unchanged': True})


@pytest.mark.parametrize('status', ('invalid', 'failed', 'unavailable'))
def test_executed_return_keeps_original_observation(case, status, record_property):
    fixture = task_case(case)
    chosen = {'kind': 'tool', 'tool': 'api.uniprot.record',
        'arguments': {'unrequested': True} if status == 'invalid' else {}}
    expected = None
    if status != 'invalid':
        expected = {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'result': {'original_resource': 'uniprot', 'retained': [None, False, {'nested': 'payload'}]},
            'feedback': {'code': 'controlled_returned_transport_boundary'}}
        async def returned(source, name, arguments, **kwargs):
            fixture.executions.append(kwargs['operation_key'])
            return deepcopy(expected)
        fixture.workflow.execute = returned  # Only the already-selected operation's return.
    value = asyncio.run(fixture.task.execute(chosen, 2))
    saved = dict(case.journal.row('runtime_actions', case.episode_id, 2))
    payload = json.loads(saved['result'])
    assert payload['status'] == status
    if expected is not None:
        assert payload == expected
    assert json.loads(saved['action']) == chosen
    assert module('runtime').observes_action_outcome('tool', status)
    assert fixture.observations == [(2, chosen, payload)] and len(fixture.projections) == 1
    before = rows(case.store)
    assert asyncio.run(fixture.task.execute(chosen, 2)).as_record() == value.as_record()
    assert rows(case.store) == before and len(fixture.executions) == 1
    retained(record_property, 'executed_return', {'status': status, 'controlled_port': status != 'invalid',
        'selected': chosen, 'payload': payload, 'controller_input': value.as_record()})


@pytest.mark.parametrize('kind,status', (('reason', 'completed'), ('reason', 'invalid'),
                                       ('wait', 'completed'), ('wait', 'failed')))
def test_original_saved_wait_reason_replay(case, kind, status, record_property):
    fixture = task_case(case)
    selected = {'kind': kind, **({'condition': {'original': 'waiting'}} if kind == 'wait'
        else {'commit': {'original': 'returned reason payload'}})}
    payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
        'result': {'original_saved_outcome': kind}, 'feedback': {'code': 'original_saved_feedback'}}
    case.journal.save('runtime_actions', {'episode_id': case.episode_id, 'decision_index': 9,
        'action': module('runtime')._json(selected), 'result': module('runtime')._json(payload), 'credit': 7.25})
    before = rows(case.store)
    if kind == 'wait' and status == 'failed':
        with pytest.raises(module('runtime').ActionFailure):
            asyncio.run(fixture.task.execute(selected, 9))
    else:
        assert asyncio.run(fixture.task.execute(selected, 9)).as_record()['credit'] == 7.25
    assert rows(case.store) == before
    assert fixture.executions == fixture.observations == fixture.projections == []
    assert fixture.task.last_outcome == payload
    retained(record_property, 'saved_nonfresh_action', {'selected': selected, 'payload': payload,
        'unchanged_rows': before['runtime_actions'], 'fresh_common_actions': case.binding.permitted_common_actions(case.context)})


def test_unfinished_original_wait_reenters_iterator_without_reprojection(case):
    fixture = task_case(case)
    selected = {'kind': 'wait', 'condition': {'original': 'condition'}}
    case.journal.save('runtime_actions', {'episode_id': case.episode_id, 'decision_index': 6,
        'action': module('runtime')._json(selected), 'result': None, 'credit': None})
    calls = []
    async def wait(source, condition, index):
        calls.append((deepcopy(condition), index))
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
            'result': {'original_condition_ready': True}}
    fixture.workflow.perform_selected_wait = wait
    fixture.workflow.last_observed_credit = lambda source: 4.5
    first = asyncio.run(fixture.task.execute(selected, 6)).as_record()
    assert first['credit'] == 4.5
    assert asyncio.run(fixture.task.execute(selected, 6)).as_record() == first
    assert calls == [(selected['condition'], 6)]
    assert len(fixture.observations) == 1 and fixture.executions == fixture.projections == []


def test_interrupted_actual_decode_reuses_saved_snapshot(case, monkeypatch, record_property):
    service = case.binding.api_execution.services['uniprot']
    original, visits = service.decode, []
    def interrupt(command, snapshot):
        visits.append(snapshot.content)
        if len(visits) == 1:
            raise asyncio.CancelledError()
        return original(command, snapshot)
    monkeypatch.setattr(service, 'decode', interrupt)
    key = case.selected('api.uniprot.record', {}, 0)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(case.binding.execute(case.context, 'api.uniprot.record', {}, key))
    assert len(case.client.calls) == 1
    completed = case.act('api.uniprot.record')
    assert completed['status'] == 'completed' and len(case.client.calls) == 1
    assert len(visits) == 2 and visits[0] == visits[1]
    assert case.binding.verify_completion(case.context, case.binding.completion_for_action(case.context, key))
    retained(record_property, 'decode_recovery', {'outcome': completed, 'same_raw_snapshot': True,
        'snapshot': visits[0].decode(), 'http_calls': case.client.calls})


@pytest.mark.parametrize('mode', ('unknown', 'not_sent'))
@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_original_submission_outcome_controls_resubmission(tmp_path, home, mode, record_property):
    case = Case(tmp_path, home, service='ncbi_blast')
    try:
        case.client.mode = mode
        failed = case.act('api.blast.submit')
        assert failed['status'] == 'failed'
        assert failed['feedback']['submission_outcome'] == mode
        assert case.act('api.blast.submit') == failed and len(case.client.calls) == 1
        case.client.mode = 'ordinary'
        second = case.act('api.blast.submit', index=1)
        if mode == 'unknown':
            assert second['status'] == 'invalid'
            assert second['feedback']['code'] == 'api_original_submission_already_exists'
            assert len(case.client.calls) == 1
        else:
            assert second['status'] == 'completed' and len(case.client.calls) == 2
        retained(record_property, 'submission_custody', {'first': failed, 'next_selected': second,
            'calls': case.client.calls, 'logical_rows': rows(case.store)})
    finally:
        case.close()


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_actual_hmmer_handoff_proof_and_supported_store_reopen(tmp_path, home, record_property):
    case = Case(tmp_path, home, service='ebi_hmmer')
    try:
        prepared = case.act('api.hmmer.prepare', index=0)
        submitted = case.act('api.hmmer.submit', index=1)
        checked = case.act('api.hmmer.check_handoff', index=2)
        assert prepared['status'] == submitted['status'] == checked['status'] == 'completed'
        assert len(case.client.calls) == 2
        proof = case.binding.completion_for_action(case.context, f'{case.run_id}:{case.episode_id}:2')
        assert case.binding.verify_completion(case.context, proof)
        view = case.binding.credit_view(case.context, case.selection())
        assert view['credit'] == 3.
        before = rows(case.store)
        descriptor = case.binding.as_record()
    finally:
        case.close()
    reopened = Case(tmp_path, home, service='ebi_hmmer', existing=True)
    try:
        assert reopened.store.db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        assert reopened.binding.as_record() == descriptor
        assert reopened.act('api.hmmer.check_handoff', index=2) == checked
        assert reopened.client.calls == [] and rows(reopened.store) == before
        assert reopened.binding.verify_completion(reopened.context, proof)
        retained(record_property, 'supported_saved_service_reopen', {'descriptor': descriptor,
            'prepared': prepared, 'submitted': submitted, 'handoff': checked, 'proof': proof,
            'view': view, 'all_logical_rows_unchanged': True,
            'scope': 'Supported Store plus explicit same literal factory; not saved workflow reconstruction'})
    finally:
        reopened.close()


def test_changed_request_or_scope_keeps_original_action_identity(case, record_property):
    first = case.act('api.uniprot.record')
    key = f'{case.run_id}:{case.episode_id}:0'
    changed_request = deepcopy(case.assignment)
    changed_request['request']['accession'] = 'P12346'
    candidates = (replace(case.context, assignment=changed_request),
        replace(case.context, scope={'subject_refs': []}))
    observed = []
    for context in candidates:
        observed.append(outcome(lambda: asyncio.run(case.binding.execute(context, 'api.uniprot.record', {}, key))))
        assert 'raised' in observed[-1] or observed[-1]['returned']['status'] == 'invalid'
    assert case.act('api.uniprot.record') == first and len(case.client.calls) == 1
    retained(record_property, 'changed_context_denials', observed)


def test_exact_original_api_controller_and_missing_profile_denial(case, record_property, request):
    key = 'launch_api:' + case.binding._request_yield_class(case.assignment)
    assert key == 'launch_api:api_uniprot_handoff'
    controller = case.binding.yield_controller(case.context, 0., 'original-epoch')
    numerical = module('numerical')
    expected = numerical.YieldController('original-epoch', 0., .5, numerical.YieldParameters(),
        estimate_with_context=module('practical_yield').PracticalYieldEstimator(
            lambda proof: case.binding.verify_completion(case.context, proof)))
    assert type(controller) is type(expected)
    assert controller.cost == expected.cost and controller.settings == expected.settings
    assert controller.state().as_record() == expected.state().as_record()
    estimator = controller.estimator.estimate_with_context
    assert type(estimator) is module('practical_yield').PracticalYieldEstimator
    completed = case.act('api.uniprot.record')
    proof = case.binding.completion_for_action(case.context, f'{case.run_id}:{case.episode_id}:0')
    assert estimator.verify_completion(proof)
    assert not estimator.verify_completion({**proof, 'receipt_sha256': '0' * 64})
    old = case.binding.task_yield_profiles
    try:
        case.binding.task_yield_profiles = {}
        with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:' + key):
            case.binding.yield_controller(case.context, 0., 'original-epoch')
    finally:
        case.binding.task_yield_profiles = old
    original_provenance = {'key': key, 'type': type(controller).__module__ + '.' + type(controller).__qualname__,
        'state': controller.state().as_record(), 'estimator': estimator.as_record(),
        'practical_estimator': case.binding.practical_estimator(case.context).as_record(),
        'operational_units': [case.binding.handoff_unit, case.binding.acquired_record_unit]}
    retained(record_property, 'actual_estimator_provenance', original_provenance)
    compare_original_property(request, 'actual_estimator_provenance', original_provenance)
    retained(record_property, 'controller', {'key': key, 'type': type(controller).__module__ + '.' + type(controller).__qualname__,
        'state': controller.state().as_record(), 'estimator': estimator.as_record(), 'proof': proof,
        'actual_outcome': completed, 'operational_units': [case.binding.handoff_unit, case.binding.acquired_record_unit]})


@pytest.mark.parametrize('role', ('launch_api', 'launch', 'results'))
def test_original_callback_provenance_for_all_six_execution_placements(case, role, record_property, request):
    runtime = module('runtime')
    if role == 'launch_api':
        owner, context = case.binding, case.context
    else:
        parent = case.home.rsplit('/', 1)[0]
        target_home = parent if role == 'launch' else parent.removesuffix('execution_job_submission') + 'execution_result_acquisition'
        options = {**case.options, 'task_yield_profiles': {**case.options['task_yield_profiles'],
            'launch:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
            'results:api_uniprot': {'cutoff': .5, 'parameters': {}}}}
        owner = module(target_home + '/episode').ExecutionEpisode(case.services, **options)
        if role == 'launch':
            selected = {'version': 'execution_launch_assignment_v1',
                'requests': {'uniprot': deepcopy(case.assignment)}, 'immutable_input_versions': [], 'constraints': {}}
            refs = []
        else:
            producer = case.act('api.uniprot.record')
            assert producer['status'] == 'completed'
            ref, = producer['record_refs']
            selected = {'version': 'execution_results_assignment_v1', 'handoff_ref': ref, 'selector': {}}
            refs = [ref]
        path = ((role, 'original-callback-owner'),)
        identity = module('method_loop.identities').EpisodeRef(case.run_id, path).episode_id
        receipt = case.receipts.bind(identity)
        case.receipts.receive(identity, [*case.scope['subject_refs'], *refs], kind='initial')
        saved_request = {'message': {'scope': deepcopy(case.scope), 'episode_assignment': selected,
            'knowledge_inheritance': receipt}}
        case.journal.save('runtime_episodes', {'episode_id': identity, 'path': runtime._json(path),
            'request': runtime._json(saved_request), 'initial_credit': 0, 'state': 'active',
            'completion': None, 'archive': None})
        context = module('episode_bindings').BindingContext(case.run_id, identity, role,
            path, case.scope, selected, saved_request)
        owner.initialize(context)
    controller = owner.yield_controller(context, 0., 'original-callback-epoch')
    contextual = getattr(controller.estimator, 'estimate_with_context', None)
    value = {'home': owner.binding_path, 'role': role,
        'practical_estimator': owner.practical_estimator(context).as_record(),
        'controller': {'type': type(controller).__module__ + '.' + type(controller).__qualname__,
            'state': controller.state().as_record(), 'cost': controller.cost,
            'settings': controller.settings.as_record(),
            'contextual_estimator': None if contextual is None else contextual.as_record()},
        'handoff_unit': owner.handoff_unit, 'acquired_record_unit': owner.acquired_record_unit}
    retained(record_property, 'all_owner_original_callback_identity', value)
    compare_original_property(request, 'all_owner_original_callback_identity', value)


@pytest.mark.parametrize('protocol', (None, 'decision_exchange_v1'))
@pytest.mark.parametrize('declared', (False, True))
def test_actual_task_decision_complete_payload_and_saved_response(case, protocol, declared, record_property):
    fixture = task_case(case)
    state, schema, response, calls = prepare_decision(case, fixture.task, protocol, declared=declared)
    assert asyncio.run(fixture.task.call(state, schema))[0] == response
    assert len(calls) == 1
    args, keywords = calls[0]
    presented = module('decision_context').apply_state_frame(None, args[3]) if protocol else args[3]
    for key, value in state.items():
        assert presented[key] == value
    saved = dict(case.journal.row('runtime_model_calls', case.episode_id, 0))
    original_context = json.loads(saved['request'])['context']
    original_instructions = module('runtime_prompt').instructions(fixture.task, original_context)
    # Both ordinary and exchange paths keep the original instruction body,
    # including runtime-added launch-library/context tails.
    assert args[2] == original_instructions + ('\n' + module('decision_context').INSTRUCTIONS if protocol else '')
    private = hasattr(case.binding, 'decision_source_type')
    assert keywords == ({'prompt_renderer': case.binding.decision_prompt_renderer} if private and declared else {})
    assert json.loads(saved['response']) == response
    fixture.task.calls = 0
    assert asyncio.run(fixture.task.call(state, schema))[0] == response and len(calls) == 1
    assert case.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
    retained(record_property, 'decision_payload', {'protocol': protocol, 'declared_port': declared,
        'instructions': args[2], 'context': args[3], 'schema': args[4], 'saved_call': saved})


@pytest.mark.parametrize('with_hpc', (False, True))
def test_actual_provider_precedence_and_complete_state_frames(case, with_hpc, record_property):
    providers, context_module = module('providers'), module('decision_context')
    state = {'execution_assignment': deepcopy(case.assignment), 'api_service': 'uniprot',
        'api_request': deepcopy(case.assignment['request']), 'scope': deepcopy(case.scope),
        'goal': {'objective': 'Original request'}}
    if with_hpc:
        state['hpc_execution_job'] = {'original_commission': 'retained'}
    updated = {**state, 'feedback': {'code': 'original feedback'}}
    frames = [state, context_module.state_frame(state), context_module.state_frame(updated, state),
        {'version': context_module.VERSION, 'kind': 'decision_lookup_result', 'result': {'original': 'lookup'}},
        {'ordinary_unknown_context': {'complete': [None, True, 'JSON retained']}}]
    original = object.__new__(providers._SessionConnection)
    original.scientific_prompt_states = {}
    connected = object.__new__(providers._SessionConnection)
    connected.scientific_prompt_states = {}
    renderer = getattr(case.binding, 'decision_prompt_renderer', None)
    results = []
    for frame in frames:
        expected = original._presentation(case.episode_id, 'TASK', 'Original instructions.', deepcopy(frame))
        actual = connected._presentation(case.episode_id, 'TASK', 'Original instructions.', deepcopy(frame),
            **({'prompt_renderer': renderer} if renderer is not None else {}))
        assert actual == expected
        assert connected.scientific_prompt_states == original.scientific_prompt_states
        results.append({'frame': frame, 'presentation': actual, 'state': deepcopy(connected.scientific_prompt_states.get((case.episode_id, 'TASK')))})
    expected_renderer = module('library.hpc_prompt').render_hpc_prompt if with_hpc else module('execution_prompt').render_api_launch_prompt
    assert results[0]['presentation'][0] == expected_renderer(state, 'Original instructions.')
    assert json.loads(results[-1]['presentation'][0]) == frames[-1]
    retained(record_property, 'presentation_complete_frames', results)


def traced_prepare(binding, parent, selected, scope, key):
    trace = []
    root = Path(module('runtime').__file__).parent
    def record(frame, event, arg):
        if event == 'call' and Path(frame.f_code.co_filename).is_relative_to(root):
            trace.append([str(Path(frame.f_code.co_filename).relative_to(root)), frame.f_code.co_qualname])
    previous = sys.getprofile()
    sys.setprofile(record)
    try:
        value = outcome(lambda: binding.prepare_assignment(parent, 'launch_api', selected, scope, key))
    finally:
        sys.setprofile(previous)
    return value, trace


def test_actual_nonhpc_parent_contract_failure_and_identity_transport(nonhpc_case, record_property):
    case = nonhpc_case
    parent_home = case.home.rsplit('/', 1)[0]
    parent = module(parent_home + '/episode').ExecutionEpisode(case.services, **case.options)
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'uniprot': deepcopy(case.assignment)},
        'immutable_input_versions': [], 'constraints': {}}
    context = replace(case.context, role='launch', path=(('launch', 'original-parent'),), assignment=launch)
    selected = deepcopy(case.assignment)
    before = traced_prepare(case.binding, context, selected, case.scope, 'original-selected-request')
    assert before[0].get('raised', {}).get('message') == 'unknown_execution_episode_role'
    send = getattr(parent, 'prepare_child_request', None)
    forwarded = selected if send is None else send(context, 'launch_api', selected)
    assert forwarded is selected
    after = traced_prepare(case.binding, context, forwarded, case.scope, 'original-selected-request')
    assert after == before
    if os.environ.get('A104_API_PHASE') == 'connected':
        assert callable(getattr(parent, 'child_request_assembler', None))
        assert callable(parent.child_request_assembler('launch_api'))
    retained(record_property, 'nonhpc_actual_admission', {'result': before[0], 'full_nested_trace': before[1],
        'original_selected_object_preserved': True, 'no_admitted_api_child': True})


@pytest.mark.parametrize('home', HOMES[2:], ids=HOMES[2:])
def test_actual_hpc_plan_does_not_authorize_an_api_child(tmp_path, home, record_property):
    from gene_annotation_episode.episodic_workflow.root.tests.hpc_launch_task_checks import LaunchTaskChecks
    adapter = SimpleNamespace(axis='a104', binding_path=home.rsplit('/', 1)[0], module=module)
    generator = LaunchTaskChecks.launch_case.__wrapped__(adapter, tmp_path)
    value = next(generator)
    try:
        api = module(home + '/episode').ExecutionEpisode(value.services, **value.execution_options)
        selected = assignment(value.context.scope['subject_refs'][0])
        before = traced_prepare(api, value.context, selected, value.context.scope, 'actual-hpc-api-request')
        assert 'raised' in before[0]
        send = getattr(value.binding, 'prepare_child_request', None)
        forwarded = selected if send is None else send(value.context, 'launch_api', selected)
        assert forwarded is selected
        after = traced_prepare(api, value.context, forwarded, value.context.scope, 'actual-hpc-api-request')
        assert after == before
        assert set(value.plan['launch_assignment']['requests']) == {'aurora'}
        retained(record_property, 'hpc_actual_admission', {'plan': value.plan, 'parent_context': value.context.as_record(),
            'selected_api_request': selected, 'result': before[0], 'full_nested_trace': before[1],
            'unchanged_plan_no_api_authorization': True})
    finally:
        generator.close()


def complete_commission_trace(workflow, parent, selection, index):
    """Trace actual selected, parent hooks, admission and full build together.

    Only the two new mechanical routing frames are excluded from the compared
    event sequence. All original function calls, including parent-side checks,
    are kept; private file/class moves do not rename a call's actual function.
    The complete raw file/qualname trace is retained as separate source evidence.
    """
    runtime = module('runtime')
    parent_binding = workflow.specialist(parent.source)
    child_binding = workflow.episode_bindings.for_child(parent.source.path, 'launch_api')
    root = Path(runtime.__file__).parent
    trace, comparable, admissions, builds = [], [], [], []
    allowed_routes = {str(root / parent_binding.binding_path / 'to_child_api_job_execution.py')}
    def record(frame, event, arg):
        if event != 'call' or not Path(frame.f_code.co_filename).is_relative_to(root):
            return
        own = frame.f_locals.get('self')
        owner = ('parent' if own is parent_binding else 'child' if own is child_binding
            else 'workflow' if own is workflow else 'other')
        name = frame.f_code.co_name
        row = {'file': str(Path(frame.f_code.co_filename).relative_to(root)),
            'qualname': frame.f_code.co_qualname, 'name': name, 'owner': owner,
            'transaction_open': workflow.store.db.in_transaction}
        trace.append(row)
        route = ((name == 'child_request_assembler' and own is parent_binding)
            or (name == 'assemble_request' and frame.f_code.co_filename in allowed_routes))
        if not route:
            comparable.append({'name': name, 'owner': owner, 'transaction_open': row['transaction_open']})
        if name == 'prepare_assignment' and own is child_binding:
            admissions.append({'trace_index': len(trace) - 1,
                'selected_object_is_original': frame.f_locals['selection'] is selection['assignment'],
                'scope': canonical(frame.f_locals['scope']),
                'operation_key': frame.f_locals['operation_key'],
                'actual_child_configuration': canonical(child_binding.as_record()['configuration']),
                'transaction_open': row['transaction_open']})
        if name == 'build' and own is workflow:
            builds.append({'trace_index': len(trace) - 1, 'name': frame.f_locals['name'],
                'key': frame.f_locals['key'], 'transaction_open': row['transaction_open'],
                'assignment': canonical(frame.f_locals['episode_assignment']),
                'saved_action': dict(workflow.journal.row('runtime_actions', parent.source.episode_id, index))})
    previous = sys.getprofile()
    sys.setprofile(record)
    try:
        try:
            selected = workflow.selected(parent.source, selection, index)
            child = selected.child
            result = {'returned': {'unit_type': type(selected).__module__ + '.' + type(selected).__qualname__,
                'request': child.request.as_record(), 'context': workflow.binding_context(child.source).as_record(),
                'saved_child': dict(workflow.journal.row('runtime_episodes', child.source.episode_id))}}
        except Exception as error:
            result = {'raised': error_record(error)}
    finally:
        sys.setprofile(previous)
    for admission in admissions:
        assert admission['selected_object_is_original']
        assert admission['actual_child_configuration'] == canonical(child_binding.as_record()['configuration'])
    assert len(admissions) <= 1, 'parent_or_child_repeated_original_admission'
    if builds:
        assert len(builds) == 1 and len(admissions) == 1
        assert admissions[0]['trace_index'] < builds[0]['trace_index']
        assert builds[0]['transaction_open'] is True
        assert json.loads(builds[0]['saved_action']['action']) == selection
    return {'result': canonical(result), 'complete_raw_trace': trace, 'comparable_original_calls': comparable,
        'admissions': admissions, 'builds': builds}


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_whole_actual_selected_build_commission_preserves_admission(tmp_path, home, request, record_property):
    from .api_saved_carriers import build_case, SCHEMA
    client = Responses()
    with module('state').Store(tmp_path / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        workflow, factory = build_case(store, tmp_path, home, 'launch', client)
        chosen = assignment(scope['subject_refs'][0])
        launch = {'version': 'execution_launch_assignment_v1', 'requests': {'uniprot': deepcopy(chosen)},
            'immutable_input_versions': [], 'constraints': {}}
        # This is a supported standalone saved Launch factory. It is neither
        # an API-bearing HPC plan nor scientific-parent commissioning authority.
        parent = workflow.build('launch', 'controlled-parent', 'Original API handoff', scope,
            episode_assignment=launch)
        selection = {'kind': 'episode_child', 'role': 'launch_api', 'goal': 'Return original API handoff',
            'scope': scope, 'purpose': 'Retain actual completion', 'assignment': chosen,
            'schema_json': json.dumps(SCHEMA), 'initial_report_json': '{}'}
        observed = complete_commission_trace(workflow, parent, selection, 3)
        assert len(observed['admissions']) == 1
        if home in HOMES[:2]:
            assert observed['result'].get('raised', {}).get('message') == 'unknown_execution_episode_role'
            assert observed['builds'] == []
            assert workflow.journal.row('runtime_actions', parent.source.episode_id, 3) is None
        else:
            assert 'returned' in observed['result'] and len(observed['builds']) == 1
            assert observed['result']['returned']['context']['assignment'] == chosen
        assert client.calls == []
        retained(record_property, 'complete_selected_build_commission', observed)
        # Actual file/qualname relocation is retained above. Full original call
        # order, every parent validation, input identity, payload and admission
        # outcome are compared, without hiding invalid/failed admissions.
        preserved = {'result': observed['result'],
            'complete_original_calls': observed['comparable_original_calls'],
            'admissions': [{key: value for key, value in row.items() if key != 'trace_index'} for row in observed['admissions']],
            'builds': [{key: value for key, value in row.items() if key != 'trace_index'} for row in observed['builds']]}
        retained(record_property, 'original_complete_commission_boundary', preserved)
        compare_original_property(request, 'original_complete_commission_boundary', preserved)
