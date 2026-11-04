"""Saved model presentation with original calculation inputs; isolated fixtures.

All work uses scripted providers and synthetic semantic records. No configured
model, public client, native executable or scientific workspace is invoked.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import runtime
from gene_annotation_episode.domain import ContractError
from method_loop.durable import canonical
from method_loop.identities import UnitRef
from test_runtime import (FixtureController, ScriptedProvider, fixture_credit,
    obj, reason, run, setup)


MODE = 'bounded_wait_history_v1'
VERSION = 'runtime_model_call_request_v2'


class CapturingProvider(ScriptedProvider):
    def __init__(self, script, *, has_session=False):
        super().__init__(script)
        self.session = has_session
        self.instructions = []
        self.schemas = []
        self.texts = []

    def has_session(self, *_):
        return self.session

    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.instructions.append(instructions)
        self.schemas.append(deepcopy(output_schema))
        self.texts.append(json.dumps(context, allow_nan=False))
        return await super().complete(episode_id, role, instructions, context, output_schema)


def host(tmp_path, *, mode=True, preview_size=24, provider=None):
    store, tools = setup(tmp_path)
    settings = {'preview_size': preview_size}
    if mode:
        settings['model_presentation'] = MODE
    provider = provider or CapturingProvider([])
    workflow = runtime.Workflow(store, tools, provider, tmp_path/'run', 'presentation-fixture',
        lambda path, initial: FixtureController(str(path), initial, 50), fixture_credit,
        restoration_settings=settings)
    source = workflow.build('annotation', 'root', 'Keep exact original fixture inputs',
        {'subject_refs': ['subject_A']}).source
    return SimpleNamespace(store=store, tools=tools, workflow=workflow, source=source,
        provider=provider)


def saved_call(h, index=0):
    return h.workflow.journal.row('runtime_model_calls', h.source.episode_id, index)


def forbidden(*_, **__):
    raise AssertionError('Saved request replay must not capture current state')


def seed_history(h, count, *, decisions=None):
    decisions = decisions or list(range(count))
    values = [0, -1.25, 2.5, -0.0]
    for unit, decision in enumerate(decisions):
        value = values[unit % len(values)]
        observation = {'label': f'fixture-{unit}', 'credit': {'credit': value},
            'step': {'marginal_credit': value, 'unknown': None,
                'estimate': {'provenance': {'fixture': 'original', 'value': unit}}},
            'unit_ref': UnitRef(h.source.episode_id, unit).as_record(), 'decision_index': decision}
        h.workflow.journal.save('runtime_observations', {'episode_id': h.source.episode_id,
            'unit_index': unit, 'observation': canonical(observation)})


def counts(h):
    return tuple(h.store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        for table in ('runtime_actions', 'runtime_observations'))


def test_opt_in_captures_model_view_and_original_raw_request_before_dispatch(tmp_path):
    h = host(tmp_path, preview_size=2)
    seed_history(h, 3, decisions=[5, 1, 3])
    h.source.calls = 6
    observed = []

    def inspect(context):
        record = saved_call(h, 6)
        capture = json.loads(record['request'])
        assert record['response'] is None and set(capture) == {
            'version', 'context', 'schema', 'model_presentation'}
        assert capture['version'] == VERSION
        raw = capture['context']['waiting_support']['own_completed_action_history']
        page = context['waiting_support']['own_completed_action_history_page']
        assert len(raw) == 3 and context['waiting_support']['own_completed_action_history'] == raw[-2:]
        assert page['decision_indices'] == [1, 3]
        assert page['range'] == {'start': 1, 'end_exclusive': 3,
            'unit': 'completed_own_action_history_position'}
        assert page['total_rows'] == 3 and page['included_rows'] == 2 and page['omitted_rows'] == 1
        presentation = capture['model_presentation']
        assert presentation['context'] == context
        assert presentation['model_input_text_sha256'] == hashlib.sha256(h.provider.texts[0].encode()).hexdigest()
        assert presentation['model_input_char_count'] == len(h.provider.texts[0])
        assert presentation['model_input_utf8_byte_count'] == len(h.provider.texts[0].encode())
        assert context['scientific_fixture'] == {'unknown': None, 'signed': -2.5, 'unicode': 'μ'}
        observed.append(record['request'])
        # A provider receives an independent model view, not the raw numerical
        # context or the durable capture's mutable in-memory authority.
        context['waiting_support']['own_completed_action_history'][0]['controller_input']['credit'] = 999
        return reason(0)

    h.provider = h.workflow.provider = CapturingProvider([inspect], has_session=True)
    _, _, raw, schema = asyncio.run(h.source.call({'visible_record_refs': [],
        'tools': h.workflow.catalog(h.source.scope, source=h.source),
        'scientific_fixture': {'unknown': None, 'signed': -2.5, 'unicode': 'μ'}}, obj({})))
    assert saved_call(h, 6)['request'] == observed[0]
    assert raw == json.loads(observed[0])['context']
    assert len(raw['waiting_support']['own_completed_action_history']) == 3
    assert schema == obj({}) and counts(h) == (0, 3)


def test_pending_v2_reuses_captured_view_and_schema_without_current_capture(tmp_path, monkeypatch):
    h = host(tmp_path, preview_size=2,
        provider=CapturingProvider([KeyboardInterrupt()], has_session=True))
    seed_history(h, 5)
    h.source.calls = 10
    schema = obj({})
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(h.source.call({'visible_record_refs': [], 'unicode': 'μ',
            'tools': h.workflow.catalog(h.source.scope, source=h.source)}, schema))
    original = json.loads(saved_call(h, 10)['request'])
    assert 'restored_episode_history' not in original['context']
    text = json.dumps(dict(reversed(list(original.items()))), indent=3, ensure_ascii=True) + '\n'
    h.store.db.execute('UPDATE runtime_model_calls SET request=?', (text,))
    first_text = h.provider.texts[0]
    first_instructions = h.provider.instructions[0]
    seed_history(h, 6)  # A prior selected completion became visible after capture.
    replay_seen = []

    def inspect(_):
        assert saved_call(h, 10)['request'] == text
        replay_seen.append(True)
        return reason(0)

    fresh = CapturingProvider([inspect], has_session=False)
    h.workflow.provider = fresh
    with monkeypatch.context() as patch:
        for name in ('waiting_support', 'history_preview', 'api_execution_planning_context',
                     'native_estimation_context'):
            patch.setattr(h.workflow, name, forbidden)
        patch.setattr(runtime, 'prepare_model_context_presentation', forbidden)
        h.source.calls = 10
        response, _, raw, actual_schema = asyncio.run(h.source.call({}, obj({'new': {'type': 'string'}})))
        assert saved_call(h, 10)['request'] == text and replay_seen
        assert raw == original['context'] and actual_schema == schema
        assert fresh.texts == [first_text] and fresh.instructions == [first_instructions]
        assert len(raw['waiting_support']['own_completed_action_history']) == 5
        assert len(fresh.contexts[0]['waiting_support']['own_completed_action_history']) == 2
        patch.setattr(runtime, 'validate_model_context_presentation', forbidden)
        h.source.calls = 10
        assert asyncio.run(h.source.call({}, {}))[0] == response
        assert len(fresh.texts) == 1 and saved_call(h, 10)['request'] == text
    # Only a new unsaved call can receive newer original history/restoration.
    next_provider = CapturingProvider([reason(0)], has_session=False)
    h.workflow.provider = next_provider
    asyncio.run(h.source.call({'visible_record_refs': [],
        'tools': h.workflow.catalog(h.source.scope, source=h.source)}, schema))
    next_capture = json.loads(saved_call(h, 11)['request'])
    assert len(next_capture['context']['waiting_support']['own_completed_action_history']) == 6
    assert next_capture['context']['restored_episode_history']['total_prior_decisions'] == 1
    assert len(next_capture['context']['restored_episode_history']['entries']) <= 2
    assert next_provider.instructions == [first_instructions]
    assert counts(h) == (0, 6)


@pytest.mark.parametrize('mode,damage', [(True, 'legacy'), (False, 'v2'),
    (True, 'version'), (False, 'extra')])
@pytest.mark.parametrize('completed', [False, True])
def test_mixed_envelope_mode_rejects_before_dispatch_or_journal_change(
        tmp_path, monkeypatch, mode, damage, completed):
    h = host(tmp_path, mode=mode, provider=CapturingProvider([reason(0)]))
    asyncio.run(h.source.call({'visible_record_refs': []}, obj({})))
    original = json.loads(saved_call(h)['request'])
    if damage == 'legacy':
        corrupt = {key: original[key] for key in ('context', 'schema')}
    elif damage == 'v2':
        corrupt = {**original, 'version': VERSION, 'model_presentation': {}}
    elif damage == 'version':
        corrupt = {**original, 'version': 'unsupported'}
    else:
        corrupt = {**original, 'unexpected': True}
    h.store.db.execute('UPDATE runtime_model_calls SET request=?,response=?',
        (json.dumps(corrupt, indent=2), json.dumps(reason(0)) if completed else None))
    before = saved_call(h)
    h.workflow.provider = CapturingProvider([])
    monkeypatch.setattr(h.workflow.journal, 'save', forbidden)
    monkeypatch.setattr(h.workflow, 'waiting_support', forbidden)
    h.source.calls = 0
    with pytest.raises(ContractError, match='model_presentation_contract_conflict'):
        asyncio.run(h.source.call({}, {}))
    assert saved_call(h) == before and h.workflow.provider.contexts == []
    assert counts(h) == (0, 0)


@pytest.mark.parametrize('field', ['episode_id', 'presented_context_sha256'])
def test_saved_presentation_tampering_rejects_without_recapture_or_mutation(tmp_path, monkeypatch, field):
    h = host(tmp_path, provider=CapturingProvider([KeyboardInterrupt()]))
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(h.source.call({'visible_record_refs': []}, obj({})))
    corrupt = json.loads(saved_call(h)['request'])
    corrupt['model_presentation'][field] = 'wrong-original-identity'
    h.store.db.execute('UPDATE runtime_model_calls SET request=?', (json.dumps(corrupt),))
    before = saved_call(h)
    h.source.calls = 0
    h.workflow.provider = CapturingProvider([])
    monkeypatch.setattr(h.workflow.journal, 'save', forbidden)
    monkeypatch.setattr(h.workflow, 'waiting_support', forbidden)
    monkeypatch.setattr(runtime, 'prepare_model_context_presentation', forbidden)
    with pytest.raises(ContractError, match='model_presentation_contract_conflict'):
        asyncio.run(h.source.call({}, {}))
    assert saved_call(h) == before and not h.workflow.provider.contexts


def test_full_raw_wait_completed_action_and_history_inputs_are_exact(tmp_path):
    from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand
    from test_runtime_history import history

    store, tools = setup(tmp_path)
    calls = []

    def estimate(history, settings, contexts):
        calls.append((tuple(history), deepcopy(contexts)))
        return YieldEstimate(len(history), NumericBand.exact(1), settings,
            {'fixture': 'explicit_context_callback_no_production_fit'},
            estimator_binding={'fixture': 'original_signed_context_callback'})

    def factory(path, initial):
        return YieldController(str(path), initial, 0, estimate_with_context=estimate)

    values = [1, 0, -.25, .5, 0, -.125] * 5
    condition = {'version': 'event_condition_v1', 'events': [],
        'reconsider_at': '2000-01-01T00:00:00+00:00'}
    scripts = [reason(value) for value in values]
    scripts.insert(4, {'selection': 'invalid_fixture_choice', 'report_update': {}})
    scripts.extend([history([0]), history(view='records', offset=28, limit=2),
        {'selection': {'kind': 'tool', 'tool': 'episode.estimate_wait',
            'arguments': {'condition': condition}}, 'report_update': {}},
        {'selection': {'kind': 'wait', 'condition': condition}, 'report_update': {}},
        KeyboardInterrupt()])
    provider = CapturingProvider(scripts)
    workflow = runtime.Workflow(store, tools, provider, tmp_path/'run', 'numeric-presentation',
        factory, fixture_credit, restoration_settings={'preview_size': 24, 'model_presentation': MODE})
    owner = workflow.build('annotation', 'root', 'Original numerical operand fixture',
        {'subject_refs': ['subject_A']})
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(owner.run_async(workflow.context))
    records = list(store.db.execute('SELECT * FROM runtime_observations ORDER BY unit_index'))
    assert len(records) == len(values) + 4
    observations = [json.loads(row['observation']) for row in records]
    assert [entry['step']['marginal_credit'] for entry in observations] == values + [0] * 4
    assert calls[-1][0] == tuple(values + [0] * 4)
    assert [entry['decision_index'] for entry in observations[:6]] == [0, 1, 2, 3, 5, 6]
    for observation in observations:
        decision = observation['decision_index']
        request = json.loads(workflow.journal.row('runtime_model_calls', owner.source.episode_id, decision)['request'])
        raw = request['context']['waiting_support']['own_completed_action_history']
        displayed = request['model_presentation']['context']['waiting_support']['own_completed_action_history']
        assert canonical(displayed) == canonical(raw[-24:])
        context_row = store.db.execute('SELECT data FROM runtime_estimation_contexts WHERE decision_index=?',
            (decision,)).fetchone()
        actual = json.loads(context_row[0])
        assert canonical(actual['own_completed_action_history']) == canonical(raw)
        assert canonical(calls[observation['unit_ref']['unit_index'] + 1][1][-1]) == canonical(actual)
    assert len(calls[-1][1][-1]['own_completed_action_history']) == 33 > 24
    pending = workflow.journal.row('runtime_model_calls', owner.source.episode_id, len(scripts)-1)
    assert pending['response'] is None
    pending_context = json.loads(pending['request'])
    assert len(pending_context['context']['waiting_support']['own_completed_action_history']) == 34
    page = pending_context['model_presentation']['context']['waiting_support']['own_completed_action_history_page']
    assert page['included_rows'] == 24 and page['omitted_rows'] == 10
    waits = list(store.db.execute('SELECT request FROM episode_waits'))
    wait_request = json.loads(waits[0][0])
    assert len(wait_request['estimate_snapshot']['local_history_refs']) == 33
    # Both included and omitted original controller steps are reachable through
    # the actual prior-own-decision reader, with its real distinct row path.
    for decision in (0, 28):
        read = workflow.history_read(owner.source, {'view': 'records', 'decision_indices': [decision]},
            before=len(scripts))['result']['records'][0]['controller_observation']
        original = next(value for value in observations if value['decision_index'] == decision)
        assert canonical(read) == canonical(original)
    assert tools.executions == 0


def test_session_instructions_and_model_text_match_first_attempt_and_replay(tmp_path, monkeypatch):
    from gene_annotation_episode.providers import _SessionConnection, ModelCallError, default_config_path
    import tomllib

    config = tomllib.loads(default_config_path().read_text())['models']
    connection = _SessionConnection(config, tmp_path/'fixture-wire', tmp_path)
    turns, threads = [], []
    fail_next = [False]

    async def rpc(method, parameters):
        if method == 'thread/start':
            threads.append(deepcopy(parameters))
            role = connection.roles['REASONING']
            return {'thread': {'id': 'fixture-thread'}, 'model': role.model,
                'reasoningEffort': role.reasoning_effort}
        assert method == 'turn/start'
        turns.append(deepcopy(parameters))
        if fail_next[0]:
            fail_next[0] = False
            raise ModelCallError('Explicit fixture transport failure; no live model')
        turn = f'fixture-turn-{len(turns)}'
        connection.pending.extend([
            {'method': 'item/completed', 'params': {'threadId': 'fixture-thread',
                'item': {'type': 'agentMessage', 'text': json.dumps(reason(0))}}},
            {'method': 'turn/completed', 'params': {'threadId': 'fixture-thread',
                'turn': {'id': turn, 'status': 'completed'}}}])
        return {'turn': {'id': turn}}

    monkeypatch.setattr(connection, '_rpc', rpc)
    # Actual _SessionConnection.complete/_session/serializer/audit execute;
    # __aenter__, subprocess startup and external RPC are never called.
    h = host(tmp_path, preview_size=1, provider=connection)
    seed_history(h, 2, decisions=[1, 3])
    h.source.calls = 4
    supplied = {'visible_record_refs': [], 'unicode': 'μ',
        'tools': h.workflow.catalog(h.source.scope, source=h.source)}
    asyncio.run(h.source.call(supplied, obj({})))
    seed_history(h, 3, decisions=[1, 3, 2])
    fail_next[0] = True
    with pytest.raises(ModelCallError, match='Explicit fixture'):
        asyncio.run(h.source.call(supplied, obj({})))
    pending = saved_call(h, 5)
    assert pending['response'] is None
    captured = json.loads(pending['request'])
    h.source.calls = 5
    with monkeypatch.context() as patch:
        patch.setattr(h.workflow, 'waiting_support', forbidden)
        patch.setattr(h.workflow, 'history_preview', forbidden)
        patch.setattr(runtime, 'prepare_model_context_presentation', forbidden)
        asyncio.run(h.source.call({}, obj({})))
    assert saved_call(h, 5)['request'] == pending['request']
    assert len(threads) == 1 and len(turns) == 3 and connection.process is None
    assert turns[1]['input'] == turns[2]['input']
    assert turns[1]['outputSchema'] == turns[2]['outputSchema']
    assert turns[1]['input'][0]['text'] == json.dumps(captured['model_presentation']['context'], allow_nan=False)
    assert hashlib.sha256(turns[1]['input'][0]['text'].encode()).hexdigest() == captured['model_presentation']['model_input_text_sha256']
    assert 'own_completed_action_history_page' in threads[0]['developerInstructions']
    for number in range(1, 4):
        audit = json.loads((tmp_path/'fixture-wire'/f'call-{number:05}'/'request.json').read_text())
        assert audit['input'] == turns[number-1]['input']
        assert audit['instructions'] == threads[0]['developerInstructions']
    assert counts(h) == (0, 3)


def test_default_absent_marker_and_immutable_restoration_on_real_resume(tmp_path):
    store, tools = setup(tmp_path)
    first = CapturingProvider([reason(0), KeyboardInterrupt()], has_session=True)
    settings = {'preview_size': 3, 'model_presentation': MODE}
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, first, tmp_path/'run', restoration_settings=settings)
    before = [tuple(row) for row in store.db.execute('SELECT call_index,request,response FROM runtime_model_calls')]
    persisted = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
    assert persisted['restoration'] == settings
    assert json.loads((tmp_path/'run'/'run.json').read_text())['restoration'] == settings
    fresh = CapturingProvider([reason(0)], has_session=False)
    summary = run(store, tools, fresh, None, resume=True)
    assert summary['completed_actions'] == 2
    after = [tuple(row) for row in store.db.execute('SELECT call_index,request,response FROM runtime_model_calls')]
    assert after[0] == before[0] and after[1][1] == before[1][1]
    assert 'restored_episode_history' not in fresh.contexts[0]
    for replacement in ({'preview_size': 4}, {'model_presentation': None},
                        {'model_presentation': 'unavailable_mode'}):
        with pytest.raises((ValueError, runtime.WorkflowError)):
            run(store, tools, CapturingProvider([]), None, resume=True,
                restoration_settings=replacement)
    assert json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['restoration'] == settings

    other = tmp_path/'default'
    other.mkdir()
    plain_store, plain_tools = setup(other)
    provider = CapturingProvider([reason(0)])
    run(plain_store, plain_tools, provider, other/'run', counts=(1, 1))
    plain = json.loads(plain_store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
    assert plain['restoration'] == {'preview_size': 24}
    request = json.loads(plain_store.db.execute('SELECT request FROM runtime_model_calls').fetchone()[0])
    assert set(request) == {'context', 'schema'} and request['context'] == provider.contexts[0]
    assert 'own_completed_action_history_page' not in provider.instructions[0]
    assert runtime._effective_restoration_configuration(base={'preview_size': 0}) == {'preview_size': 0}
    with pytest.raises(runtime.WorkflowError, match='restoration settings'):
        run(plain_store, plain_tools, CapturingProvider([]), None, resume=True,
            restoration_settings={'model_presentation': MODE})


def test_prepared_case_preserves_exact_opt_in_configuration_without_launch(tmp_path, monkeypatch):
    from gene_annotation_episode.case_execution import prepare_case_run
    from test_case_execution import prepared
    case, configuration, _ = prepared(tmp_path, with_protein=False)
    configuration['restoration'] = {'preview_size': 0, 'model_presentation': MODE}
    monkeypatch.setattr('subprocess.Popen', forbidden)
    manifest = prepare_case_run(case, tmp_path/'case-run', configuration)
    assert manifest['configuration']['restoration'] == configuration['restoration']
    assert prepare_case_run(case, tmp_path/'case-run', configuration) == manifest
    changed = deepcopy(configuration)
    changed['restoration'] = {'preview_size': 0}
    with pytest.raises(ValueError, match='prepared_case_assignment_conflict'):
        prepare_case_run(case, tmp_path/'case-run', changed)
    assert not (tmp_path/'case-run'/'run.json').exists()


def test_pending_legacy_request_text_is_byte_identical_across_fresh_transport(tmp_path, monkeypatch):
    h = host(tmp_path, mode=False,
        provider=CapturingProvider([KeyboardInterrupt()], has_session=True))
    schema = obj({})
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(h.source.call({'visible_record_refs': [], 'unicode': 'μ', 'z': -0.0}, schema))
    first = saved_call(h)
    original = json.loads(first['request'])
    assert 'restored_episode_history' not in original['context']
    # Valid formatting variations are original captured TEXT, not an excuse to
    # normalize a pending request at the dispatch/response upserts.
    text = json.dumps({'schema': original['schema'], 'context': original['context']},
        ensure_ascii=True, indent=3) + '\n'
    h.store.db.execute('UPDATE runtime_model_calls SET request=?', (text,))
    provider = CapturingProvider([reason(0)], has_session=False)
    h.workflow.provider = provider
    monkeypatch.setattr(h.workflow, 'history_preview', forbidden)
    monkeypatch.setattr(h.workflow, 'waiting_support', forbidden)
    monkeypatch.setattr(h.workflow, 'api_execution_planning_context', forbidden)
    h.source.calls = 0
    response, index, context, actual_schema = asyncio.run(h.source.call({}, obj({'new': {'type': 'string'}})))
    assert saved_call(h)['request'] == text
    assert response == reason(0) and index == 0
    assert context == original['context'] == provider.contexts[0]
    assert actual_schema == schema
    assert provider.schemas == [runtime._action_generation_schema(schema)]
    assert h.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
