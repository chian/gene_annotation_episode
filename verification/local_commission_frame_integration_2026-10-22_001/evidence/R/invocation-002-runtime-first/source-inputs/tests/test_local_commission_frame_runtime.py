"""Original C1 facts outside model input and at real completion boundaries.

All state and selected calls are isolated fixtures. No model transport, HTTP,
native executable or scientific workspace is used.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from method_loop.durable import canonical, content_digest
from method_loop.identities import UnitRef

from gene_annotation_episode import runtime
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.waiting import (CONTEXT_COMMISSION_VERSION,
    completed_action_context, validate_completed_action_commission_context)
from test_runtime import ScriptedProvider, obj


V3 = 'runtime_model_call_request_v3'
MODE = 'bounded_wait_history_v1'
BINDING = {'factory_module': 'fixture', 'factory_name': 'never_started', 'arguments': {},
    'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64}
STAMP = '2026-10-22T00:00:00+00:00'


class Interrupted(RuntimeError):
    pass


class Provider(ScriptedProvider):
    def __init__(self, script=(), *, session=True):
        super().__init__(script)
        self.session, self.texts, self.instructions, self.schemas = session, [], [], []

    def has_session(self, *_):
        return self.session

    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.texts.append(json.dumps(context, allow_nan=False))
        self.instructions.append(instructions)
        self.schemas.append(deepcopy(output_schema))
        return await super().complete(episode_id, role, instructions, context, output_schema)


def query():
    return {'selection': {'kind': 'tool', 'tool': 'state.query',
        'arguments': {'kind': 'subject', 'limit': 1}}, 'report_update': {}}


def forbidden(*_, **__):
    raise AssertionError('saved replay/capture must not obtain or execute newer work')


@pytest.fixture
def make_host(tmp_path):
    stores = []

    def make(name='host', *, durable=True, presentation=False, script=None,
             completed='completed_action_inputs_binding_v1', wait_inputs='wait_inputs_binding_v2'):
        directory = tmp_path/name
        directory.mkdir()
        store = Store(directory/'workspace')
        stores.append(store)
        target = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs'][0]
        tools, provider = ToolRegistry(store), Provider([query()] if script is None else script)

        def credit(bound_store, scope):
            # Explicit fixture units from actual admitted forms, never a child score.
            return 2 * bound_store.db.execute(
                'SELECT count(*) FROM runtime_report_attempts WHERE form IS NOT NULL').fetchone()[0]

        workflow = runtime.Workflow(store, tools, provider, directory/'run', 'frame-runtime-fixture',
            lambda path, initial: YieldController(str(path), initial, 1e6), credit,
            project_child_credit=lambda *_args, **_kwargs: 0,
            credit_binding={'kind': 'fixture_received_form_units', 'unit': 2},
            restoration_settings={'preview_size': 2, **({'model_presentation': MODE} if presentation else {})},
            execution_binding=deepcopy(BINDING) if durable else None,
            completed_action_inputs_version=completed, wait_inputs_version=wait_inputs)
        root = workflow.build('annotation', 'root', 'Investigate only the synthetic fixture',
            {'subject_refs': [target]})
        return SimpleNamespace(store=store, tools=tools, provider=provider, workflow=workflow,
            root=root, source=root.source, target=target)

    yield make
    for store in stores:
        store.close()


def dispatch(h, context=None, schema=None):
    return asyncio.run(h.source.call({} if context is None else context, obj({}) if schema is None else schema))


def saved(h, index=0):
    return h.workflow.journal.row('runtime_model_calls', h.source.episode_id, index)


def replace_request(h, value, index=0):
    text = json.dumps(value, indent=3, ensure_ascii=True) + '\n'
    h.workflow.journal.save('runtime_model_calls', {'episode_id': h.source.episode_id,
        'call_index': index, 'purpose': 'decision', 'request': text})
    return text


def selected_child(h, index=0):
    schema = obj({'interpretation': {'type': 'string', 'enum': ['unresolved', 'supported']}})
    choice = {'kind': 'child', 'goal': 'Resolve the synthetic narrow question',
        'scope': deepcopy(h.source.scope), 'purpose': 'Return the constrained fixture finding',
        'schema_json': json.dumps(schema), 'initial_report_json': json.dumps({'interpretation': 'unresolved'})}
    h.provider.script = iter([{'selection': choice, 'report_update': {}}])
    _, actual, _, _ = dispatch(h)
    assert actual == index
    contract = runtime.TypedReportContract(choice['purpose'], schema,
        h.workflow.resolver(h.source.scope))
    child = h.workflow.build('improvement', f'child_{index}', choice['goal'], h.source.scope,
        parent=h.root.goal, parent_path=h.source.path, contract=contract,
        initial={'interpretation': 'unresolved'})
    h.workflow.commission_child(h.source, child, choice, index)
    spec = h.workflow.commissions.recover_selected(h.source.episode_id)[-1]
    h.provider.script = iter([query()])
    return spec, child


def publish(h, spec, child):
    backend = h.workflow.execution_backend
    backend.commission(spec)
    with backend._connect() as db:
        token = db.execute('SELECT execution_token FROM commissions WHERE handle=?',
            (spec['handle'],)).fetchone()[0]
    assert backend._claim(spec['handle'], token)  # fixture owner; no process starts
    form = {'interpretation': 'supported'}
    h.workflow.journal.save('runtime_forms', {'episode_id': child.source.episode_id,
        'facts': canonical({}), 'form': canonical(form)})
    payload = {'version': 'returned_episode_v1', 'handle': spec['handle'], 'return_id': '',
        'commission_sha256': content_digest(spec), 'returned_at': datetime.now(timezone.utc).isoformat(),
        'outcome': 'closed', 'completion': {'ended_by': 'yield_stop', 'end_reason': '', 'units_consumed': 0},
        'episode_archive': h.workflow.archive.store({'private_child_history': 'never read'}).descriptor(),
        'result_archive': h.workflow.archive.store({'private_child_credit': 999}).descriptor(),
        'facts_archive': None, 'form': form, 'pending_handles': [], 'failure': None}
    payload['return_id'] = content_digest({k: v for k, v in payload.items() if k != 'return_id'})
    backend.publish_return(spec['handle'], token, payload)
    return payload


def observe(h, slot, *, confirm=False):
    controller = h.workflow.controller(h.source.path)
    reference = UnitRef(h.source.episode_id, slot['sequence'])
    step = controller.observe_unit(slot['label'], runtime.Record(slot['controller_input']),
        unit_ref=reference, is_root=True)
    if confirm:
        h.workflow.completions.confirm_observed(h.source.episode_id, slot['sequence'], {
            'label': slot['label'], 'credit': slot['controller_input'], 'step': step.as_record(),
            'unit_ref': reference.as_record(), 'decision_index': slot['original_decision_index']})
    context = controller.controller.estimator.contexts[-1]
    return controller, step, context


@pytest.mark.parametrize('presentation', [False, True])
def test_new_durable_frame_is_saved_before_dispatch_without_changing_model_view(make_host, presentation):
    raw = {'fixture': {'signed': -2.5, 'unknown': None, 'unicode': 'μ'},
        'pending_work': {'version': 'pending_work_v1', 'captured_at': STAMP, 'items': []}}
    legacy = make_host('legacy', durable=False, presentation=presentation)
    durable = make_host('durable', presentation=presentation)
    dispatch(legacy, deepcopy(raw))

    def inspect(context):
        capture = json.loads(saved(durable)['request'])
        assert capture['version'] == V3
        assert set(capture) == {'version', 'context', 'schema', 'local_commission_frame'} | (
            {'model_presentation'} if presentation else set())
        assert saved(durable)['response'] is None
        frame = capture['local_commission_frame']
        assert frame['population_status'] == 'complete' and frame['population_count'] == 0
        assert frame['pending_captured_at'] == STAMP
        assert frame['return_scan']['reads'] == []
        assert context == legacy.provider.contexts[0]
        assert 'local_commission_frame' not in json.dumps(context)
        return query()

    durable.provider.script = iter([inspect])
    dispatch(durable, deepcopy(raw))
    assert durable.provider.texts == legacy.provider.texts
    assert durable.provider.instructions == legacy.provider.instructions
    assert durable.provider.schemas == legacy.provider.schemas
    reader = durable.workflow.local_commission_frame
    assert reader.store is durable.store and reader.journal is durable.workflow.journal
    assert reader.backend is durable.workflow.execution_backend
    assert durable.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('kind', ['legacy', 'v2', 'v3', 'v3-presented'])
@pytest.mark.parametrize('completed', [False, True])
def test_original_pending_and_completed_requests_replay_verbatim_without_capture(make_host, monkeypatch,
                                                                                kind, completed):
    presentation = kind in {'v2', 'v3-presented'}
    h = make_host(durable=kind.startswith('v3'), presentation=presentation,
        script=[query() if completed else Interrupted('fixture pending')])
    schema = obj({'original': {'type': 'string'}})
    if completed:
        dispatch(h, {'original': None}, schema)
    else:
        with pytest.raises(Interrupted):
            dispatch(h, {'original': None}, schema)
    original = json.loads(saved(h)['request'])
    text = replace_request(h, original)
    if not kind.startswith('v3'):
        h.workflow.configure_execution(deepcopy(BINDING))
    fresh = Provider([] if completed else [query()], session=False)
    h.workflow.provider = fresh
    for name in ('capture_local_commission_frame', 'waiting_support', 'pending_work',
                 'history_preview', 'native_estimation_context', 'api_execution_planning_context'):
        monkeypatch.setattr(h.workflow, name, forbidden)
    monkeypatch.setattr(runtime, 'prepare_model_context_presentation', forbidden)
    h.source.calls = 0
    response, index, context, actual_schema = dispatch(h, {'new': True}, obj({}))
    assert response == query() and index == 0
    assert context == original['context'] and actual_schema == schema
    assert saved(h)['request'] == text
    assert len(fresh.contexts) == (0 if completed else 1)
    if presentation and not completed:
        assert fresh.texts == h.provider.texts and fresh.instructions == h.provider.instructions
    assert h.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('presentation', [False, True])
def test_v3_pending_retry_preserves_actual_provider_serialization(make_host, monkeypatch, presentation):
    h = make_host(presentation=presentation, script=[Interrupted('first attempt')])
    context = {'zeta_fixture': {'z': 1, 'a': None}, 'alpha_fixture': 'μ'}
    schema = obj({'zeta_fixture': {'type': 'string'}, 'alpha_fixture': {'type': 'boolean'}})
    with pytest.raises(Interrupted):
        dispatch(h, context, schema)
    text = saved(h)['request']
    first_context_text = h.provider.texts[0]
    first_schema_text = json.dumps(h.provider.schemas[0], allow_nan=False)
    fresh = Provider([query()], session=False)
    h.workflow.provider = fresh
    monkeypatch.setattr(h.workflow, 'capture_local_commission_frame', forbidden)
    monkeypatch.setattr(h.workflow, 'pending_work', forbidden)
    h.source.calls = 0
    dispatch(h, {'different': True}, obj({}))
    assert saved(h)['request'] == text
    assert fresh.texts == [first_context_text]
    assert json.dumps(fresh.schemas[0], allow_nan=False) == first_schema_text
    assert fresh.instructions == h.provider.instructions


@pytest.mark.parametrize('completed', [False, True])
@pytest.mark.parametrize('corruption', ['extra', 'missing', 'foreign-run', 'foreign-episode', 'no-binding'])
def test_v3_contract_is_checked_before_transport_or_completed_response(make_host, monkeypatch,
                                                                      completed, corruption):
    h = make_host(script=[query() if completed else Interrupted()])
    if completed:
        dispatch(h)
    else:
        with pytest.raises(Interrupted):
            dispatch(h)
    value = json.loads(saved(h)['request'])
    if corruption == 'extra':
        value['new_unrecognized_field'] = True
    elif corruption == 'missing':
        del value['local_commission_frame']
    elif corruption == 'foreign-run':
        value['local_commission_frame']['run_id'] = 'other-run'
    elif corruption == 'foreign-episode':
        value['local_commission_frame']['episode_id'] = 'other-episode'
    else:
        h.workflow.execution_binding = None  # deliberately corrupt fixture ownership
    text = replace_request(h, value)
    monkeypatch.setattr(h.workflow, 'capture_local_commission_frame', forbidden)
    monkeypatch.setattr(h.provider, 'complete', forbidden)
    h.source.calls = 0
    with pytest.raises(ValueError):
        dispatch(h)
    assert saved(h)['request'] == text


def test_actual_c1_c3_c4_completion_retains_original_frame_and_no_early_payoff(make_host, monkeypatch):
    h = make_host()
    spec, child = selected_child(h)
    original = json.loads(saved(h)['request'])['local_commission_frame']
    assert original['population_count'] == 0
    returned = publish(h, spec, child)
    slot = h.workflow.next_return(h.source)
    assert slot['kind'] == 'child_return' and slot['controller_input']['credit'] == 2
    captured = []
    actual = h.workflow.capture_local_commission_frame

    def capture(episode_id, **kwargs):
        before = h.store.db.total_changes
        with monkeypatch.context() as guard:
            for name in ('status', 'start', 'commission', 'acknowledge', 'wait_events', 'record_progress'):
                guard.setattr(h.workflow.execution_backend, name, forbidden)
            guard.setattr(h.workflow.journal, 'save', forbidden)
            guard.setattr(h.workflow, 'project_credit', forbidden)
            result = actual(episode_id, **kwargs)
        assert h.store.db.total_changes == before
        captured.append(deepcopy(result))
        return result

    monkeypatch.setattr(h.workflow, 'capture_local_commission_frame', capture)
    controller, step, context = observe(h, slot, confirm=True)
    assert context['version'] == CONTEXT_COMMISSION_VERSION
    assert context['local_commission_frame_at_selection'] == original
    after = context['local_commission_frame_after_action']
    assert after == captured[0] and after['population_count'] == 1
    row = after['commissions'][0]
    sample = row['admission_evidence']['sample']
    assert row['return_metadata']['return_id'] == returned['return_id']
    assert row['accounting_status'] == 'completed' and sample['observation_state'] == 'unobserved'
    assert sample['raw_controller_delta'] is None and sample['unit_ref'] is None
    assert context['current_completion_evidence']['unit_ref'] == UnitRef(h.source.episode_id, 0).as_record()
    assert step.marginal_credit == 2 and controller.state().history == (2,)
    assert len(captured) == 1
    h.provider.script = iter([query()])
    dispatch(h)
    latest = json.loads(saved(h, 1)['request'])['local_commission_frame']['commissions'][0]
    assert latest['admission_evidence']['sample']['raw_controller_delta'] == 2
    assert json.loads(saved(h)['request'])['local_commission_frame'] == original
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
    assert h.store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1


@pytest.mark.parametrize('pending_mode', ['missing', 'null', 'empty'])
def test_missing_after_pending_still_captures_full_population_without_status_probe(make_host, monkeypatch,
                                                                                 pending_mode):
    h = make_host()
    selected_child(h)
    _, index, _, _ = dispatch(h)
    assert index == 1
    asyncio.run(h.source.execute(query()['selection'], index))
    row = h.workflow.journal.row('runtime_actions', h.source.episode_id, index)
    outcome = json.loads(row['result'])
    if pending_mode == 'missing':
        outcome.pop('pending_work_after_action')
    elif pending_mode == 'null':
        outcome['pending_work_after_action'] = None
    else:
        outcome['pending_work_after_action'] = {'version': 'pending_work_v1', 'captured_at': STAMP, 'items': []}
    h.workflow.journal.save('runtime_actions', {'episode_id': h.source.episode_id,
        'decision_index': index, 'result': canonical(outcome)})
    monkeypatch.setattr(h.workflow, 'pending_work', forbidden)
    monkeypatch.setattr(h.workflow.execution_backend, 'status', forbidden)
    _, step, context = observe(h, h.workflow.completions.slot(h.source.episode_id, 0))
    frame = context['local_commission_frame_after_action']
    assert frame['population_count'] == 1 and frame['commissions'][0]['pending_status_fact'] is None
    assert context['pending_work_after_action'] == outcome.get('pending_work_after_action')
    assert frame['pending_captured_at'] == (STAMP if pending_mode == 'empty' else None)
    assert ('pending_snapshot_unavailable' in frame['unavailable_reasons']) == (pending_mode != 'empty')
    assert step.marginal_credit == 0


@pytest.mark.parametrize('corruption', ['old-context', 'missing-after', 'changed-selection', 'legacy-request'])
def test_v6_replay_validates_original_pair_and_rejects_mixed_records_without_repair(make_host, monkeypatch,
                                                                                 corruption):
    h = make_host()
    dispatch(h)
    asyncio.run(h.source.execute(query()['selection'], 0))
    slot = h.workflow.completions.slot(h.source.episode_id, 0)
    _, step, context = observe(h, slot)
    key = (h.workflow.run_id, h.source.episode_id, 0)
    original = h.store.db.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? '
        'AND episode_id=? AND decision_index=?', key).fetchone()[0]
    monkeypatch.setattr(h.workflow, 'capture_local_commission_frame', forbidden)
    monkeypatch.setattr(h.workflow, 'capture_completion_evidence', forbidden)
    _, replay_step, replay_context = observe(h, slot)
    assert replay_step.as_record() == step.as_record() and replay_context == context
    assert h.store.db.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? '
        'AND episode_id=? AND decision_index=?', key).fetchone()[0] == original
    if corruption == 'old-context':
        context['version'] = 'completed_action_estimation_context_v5'
        context.pop('local_commission_frame_at_selection')
        context.pop('local_commission_frame_after_action')
    elif corruption == 'missing-after':
        context.pop('local_commission_frame_after_action')
    elif corruption == 'changed-selection':
        # Still internally valid metadata, but no longer the original selected frame.
        context['local_commission_frame_at_selection']['parent_state_at_store_read'] = 'yielded'
    else:
        request = json.loads(saved(h)['request'])
        request.pop('version')
        request.pop('local_commission_frame')
        replace_request(h, request)
    h.store.db.execute('UPDATE runtime_estimation_contexts SET data=? WHERE run_id=? '
        'AND episode_id=? AND decision_index=?', (canonical(context), *key))
    with pytest.raises(ValueError):
        observe(h, slot)
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('presentation', [False, True])
@pytest.mark.parametrize('version', [1, 2, 3, 4, 5])
def test_real_legacy_context_versions_replay_under_durable_binding_without_backfill(make_host, monkeypatch,
                                                                                 presentation, version):
    h = make_host(durable=False, presentation=presentation,
        completed='completed_action_inputs_binding_v1' if version == 5 else None,
        wait_inputs='wait_inputs_binding_v1' if version < 3 else 'wait_inputs_binding_v2')
    if version == 3:
        monkeypatch.setattr(h.workflow, 'source_controller_credit', lambda *_: None)
    dispatch(h)
    asyncio.run(h.source.execute(query()['selection'], 0))
    controller = h.workflow.controller(h.source.path)
    if version == 2:
        controller.include_native = True  # synthetic native context, no native execution
    value = runtime.Record({'credit': 0, 'estimation_action_index': 0})
    unit = UnitRef(h.source.episode_id, 0)
    original_step = controller.observe_unit('legacy-tool', value, unit_ref=unit, is_root=True)
    context = controller.controller.estimator.contexts[-1]
    assert context['version'] == f'completed_action_estimation_context_v{version}'
    original_request = saved(h)['request']
    row = h.store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0]
    h.workflow.configure_execution(deepcopy(BINDING))
    monkeypatch.setattr(h.workflow, 'capture_local_commission_frame', forbidden)
    monkeypatch.setattr(h.workflow, 'capture_completion_evidence', forbidden)
    restored = h.workflow.controller(h.source.path)
    replay = restored.observe_unit('legacy-tool', value, unit_ref=unit, is_root=True)
    assert replay.as_record() == original_step.as_record()
    assert restored.controller.estimator.contexts[-1] == context
    assert saved(h)['request'] == original_request
    assert h.store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0] == row


def test_completed_helper_requires_pair_and_actual_identity_and_preserves_old_calls(make_host):
    h = make_host()
    dispatch(h)
    request = json.loads(saved(h)['request'])
    before = request['local_commission_frame']
    pending = request['context']['pending_work']
    credit = before['controller_credit']
    after = h.workflow.capture_local_commission_frame(h.source.episode_id,
        pending=None, controller_credit=credit)
    original = {'version': 'completed_action_estimation_context_v1', 'expectations': None,
        'native_expectations': {'unknown': None}, 'original_custom_context': {'signed': -2}}
    arguments = {'pending_at_selection': pending, 'pending_after_action': None}
    legacy = completed_action_context(original, **arguments)
    actual = completed_action_context(original, **arguments,
        local_commission_frame_at_selection=before, local_commission_frame_after_action=after,
        run_id=h.workflow.run_id, episode_id=h.source.episode_id, controller_credit=credit)
    assert {key: value for key, value in actual.items() if key not in {'version',
        'local_commission_frame_at_selection', 'local_commission_frame_after_action'}} == {
        key: value for key, value in legacy.items() if key != 'version'}
    assert actual['version'] == CONTEXT_COMMISSION_VERSION
    for kwargs in ({'local_commission_frame_at_selection': before},
            {'local_commission_frame_after_action': after},
            {'local_commission_frame_at_selection': before, 'local_commission_frame_after_action': after}):
        with pytest.raises(ValueError):
            completed_action_context(original, **arguments, **kwargs)
    with pytest.raises(ValueError):
        validate_completed_action_commission_context(actual, selected_frame=before,
            run_id='other-run', episode_id=h.source.episode_id,
            controller_credit=credit, **arguments)
    changed_credit = deepcopy(credit)
    changed_credit['credit_binding']['unit'] = 3
    with pytest.raises(ValueError):
        completed_action_context(original, **arguments, local_commission_frame_at_selection=before,
            local_commission_frame_after_action=after, run_id=h.workflow.run_id,
            episode_id=h.source.episode_id, controller_credit=changed_credit)
    copied = deepcopy(actual)
    before['unavailable_reasons'].append('fixture changed after forwarding')
    assert actual == copied


def test_transition_preserves_capture_callbacks_without_observation(make_host):
    h = make_host()
    controller = h.workflow.controller(h.source.path)
    transitioned = controller.transitioned('explicit-fixture-next-epoch')
    assert transitioned.capture_current_commission_frame is controller.capture_current_commission_frame
    assert transitioned.capture_current_completion is controller.capture_current_completion
    assert controller.state().history == transitioned.state().history == ()


@pytest.mark.parametrize('presentation', [False, True])
def test_factual_context_preserves_signed_raw_controller_history_and_comparison(make_host, presentation):
    h = make_host(presentation=presentation, script=[query()] * 4)
    cumulative = [0.0]
    # An explicitly synthetic caller supplies these cumulative units; reading a
    # commission frame never creates or changes them.
    h.workflow.project_credit = lambda *_: cumulative[0]
    controller = h.workflow.controller(h.source.path)
    plain = YieldController(str(h.source.path), 0, 1e6)
    values = [2.0, -1.25, -1.25, 0.5]
    expected = [2.0, -3.25, 0.0, 1.75]
    for index, value in enumerate(values):
        dispatch(h)
        cumulative[0] = value
        asyncio.run(h.source.execute(query()['selection'], index))
        slot = h.workflow.completions.slot(h.source.episode_id, index)
        unit = UnitRef(h.source.episode_id, index)
        step = controller.observe_unit(slot['label'], runtime.Record(slot['controller_input']),
            unit_ref=unit, is_root=True)
        baseline_step = plain.observe(slot['label'], {'credit': value}, is_root=True)
        assert step.as_record() == baseline_step.as_record()
        h.workflow.completions.confirm_observed(h.source.episode_id, index, {
            'label': slot['label'], 'credit': slot['controller_input'], 'step': step.as_record(),
            'unit_ref': unit.as_record(), 'decision_index': index})
        raw = json.loads(saved(h, index)['request'])['context']['waiting_support']['own_completed_action_history']
        assert [r['controller_step']['marginal_credit'] for r in raw] == expected[:index]
        assert len(controller.controller.estimator.contexts) == index + 1
        assert controller.state().history == tuple(expected[:index + 1])
    assert controller.state().as_record() == plain.state().as_record()
    last = json.loads(saved(h, 3)['request'])
    assert len(last['context']['waiting_support']['own_completed_action_history']) == 3
    if presentation:
        assert len(last['model_presentation']['context']['waiting_support']['own_completed_action_history']) == 2
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
