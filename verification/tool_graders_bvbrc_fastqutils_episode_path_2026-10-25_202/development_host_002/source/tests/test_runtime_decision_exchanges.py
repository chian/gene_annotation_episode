"""Scripted decision exchanges through the actual action/accounting boundary.

These tests make no configured-model or biological investigation claim.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import runtime
from gene_annotation_episode.decision_context import apply_state_frame
from gene_annotation_episode.decision_exchanges import DecisionExchanges
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import (FixtureController, ScriptedProvider, fixture_credit,
    reason, run, setup, tool)


PROTOCOL = 'decision_exchange_v1'


def test_category_yield_parameters_default_controller():
    binding = {'factory': 'gene_annotation_episode.numerical.YieldController',
        'definition': {'cost': .01, 'window_size': 8, 'subsample_size': 3,
            'uncertainty_alpha': .05}}
    assert runtime._category_yield_parameters(binding) == {
        'window_size': 8, 'subsample_size': 3, 'uncertainty_alpha': .05}


@pytest.mark.parametrize('version', ['existing_yield_controller_explicit_parameters_v1',
                                   'existing_yield_controller_explicit_role_costs_v2'])
@pytest.mark.parametrize('wrapped', [False, True])
def test_category_yield_parameters_declared_caller_layout(version, wrapped):
    from gene_annotation_episode.numerical import YieldParameters
    parameters = YieldParameters(window_size=11, subsample_size=5, uncertainty_alpha=.07)
    definition = {'version': version, 'cost': .003, 'parameters': parameters.as_record(),
        'continuation': 'available_next_gain_upper_bound_lte_cost',
        'time_resource_estimation': 'separate_information_for_episode_decisions'}
    if version == 'existing_yield_controller_explicit_role_costs_v2':
        definition.update(cost_by_role={'job_monitor': .1},
            cost_selection='exact_episode_role_override_otherwise_caller_cost')
    if wrapped:
        # prepared_case_bindings wraps controller_definition; assemble_workflow
        # then assigns this exact wrapper to controller_binding.definition.
        definition = {'policy_source_sha256': 'a' * 64,
            'policy_parameters_sha256': 'b' * 64, 'definition': definition}
    binding = {'factory': 'fixed_gene_policy_fixture.create_policy.<locals>.controller',
        'versions': {'requirement': 'same_caller_injected_executable'}, 'definition': definition}
    original = deepcopy(binding)
    assert runtime._category_yield_parameters(binding) == {
        'window_size': 11, 'subsample_size': 5, 'uncertainty_alpha': .07}
    assert binding == original


@pytest.mark.parametrize('binding', [None, {}, {'definition': None},
    {'definition': {'version': 'custom_controller_v1', 'parameters': {
        'window_size': 8, 'subsample_size': 3, 'uncertainty_alpha': .05}}},
    {'definition': {'version': 'custom_controller_v1',
        'window_size': 8, 'subsample_size': 3, 'uncertainty_alpha': .05}},
    {'definition': {'definition': {'version': 'custom_controller_v1', 'parameters': {
        'window_size': 8, 'subsample_size': 3, 'uncertainty_alpha': .05}}}},
    {'definition': {'definition': {'definition': {
        'version': 'existing_yield_controller_explicit_role_costs_v2', 'parameters': {
            'window_size': 8, 'subsample_size': 3, 'uncertainty_alpha': .05}}}}},
    {'definition': {'version': 'existing_yield_controller_explicit_parameters_v1',
        'parameters': {'window_size': 8}}}])
def test_category_yield_parameters_unknown_or_incomplete_remains_unbound(binding):
    assert runtime._category_yield_parameters(binding) is None


def select(action):
    return {'response': {'response_type': 'select_action', **action}}


def lookup(**changes):
    query = {'view': 'own_attempts', 'category': None, 'decision_indices': None,
        'offset': 0, 'limit': 10, **changes}
    return {'response': {'response_type': 'request_context', 'lookup': query}}


class ConversationProvider(ScriptedProvider):
    def __init__(self, script, *, compact_after=()):
        super().__init__(script)
        self.keys = {}
        self.schemas = []
        self.compact_after = compact_after
        self.views = {}

    def conversation_key(self, episode_id, role):
        return self.keys.get((episode_id, role))

    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.schemas.append(deepcopy(output_schema))
        identity = (episode_id, role)
        self.keys.setdefault(identity, (episode_id + '-thread', 0))
        if context['kind'] in {'decision_bootstrap', 'decision_update'}:
            self.views[episode_id] = apply_state_frame(self.views.get(episode_id), context)
        result = await super().complete(episode_id, role, instructions, context, output_schema)
        if len(self.contexts) in self.compact_after:
            thread, epoch = self.keys[identity]
            self.keys[identity] = (thread, epoch + 1)
        return result

    async def release(self, episode_id):
        await super().release(episode_id)
        for identity in [key for key in self.keys if key[0] == episode_id]:
            del self.keys[identity]


def count(store, table):
    return store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]


def exchanges(store, index=0):
    row = store.db.execute('SELECT run_id,episode_id FROM runtime_model_calls '
        'WHERE call_index=? ORDER BY episode_id LIMIT 1', (index,)).fetchone()
    return DecisionExchanges(runtime.Journal(store, row['run_id'])).rows(row['episode_id'], index)


def test_multiple_context_exchanges_complete_one_actual_action_slot_and_observation(tmp_path):
    with Store(tmp_path / 'state') as store:
        subject = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs'][0]
        provider = ConversationProvider([lookup(), lookup(category='tool/sequence.inspect'),
            select({'selection': {'kind': 'tool', 'tool': 'sequence.inspect',
                'arguments': {'subject_ref': subject}}, 'report_update': {}})])
        workflow = runtime.Workflow(store, ToolRegistry(store), provider, tmp_path / 'run',
            'synthetic-exchange-run', lambda path, initial: FixtureController(str(path), initial, 1),
            lambda *_: 0, episode_binding_factories=(), execution_binding={'fixture': True},
            decision_protocol=PROTOCOL)
        root = workflow.build('annotation', 'root', 'Fixture investigation',
            store.validate_scope({'subject_refs': [subject]}))
        result = asyncio.run(root.run_async(workflow.context))
        assert result.units_consumed == 1
        assert count(store, 'runtime_model_calls') == 1
        assert count(store, 'runtime_actions') == 1
        assert count(store, 'runtime_completion_slots') == 1
        assert count(store, 'runtime_observations') == 1
        assert count(store, 'runtime_decision_effects') == 1
        rows = exchanges(store)
        assert len(rows) == 3 and all(row['timing'] for row in rows)
        assert [frame['kind'] for frame in provider.contexts] == [
            'decision_bootstrap', 'decision_lookup_result', 'decision_lookup_result']
        raw = json.loads(store.db.execute('SELECT request FROM runtime_model_calls').fetchone()[0])
        assert 'own_completed_action_history' in raw['context']['waiting_support']
        assert 'own_completed_action_history' not in provider.contexts[0]['fields']['waiting_support']
        assert 'action_yields' not in raw['context']
        assert 'episode.history' not in {item['name'] for item in raw['context']['tools']}
        assert rows[0]['request']['context'] == provider.contexts[0]
        outer = json.loads(store.db.execute('SELECT response FROM runtime_model_calls').fetchone()[0])
        assert set(outer) == {'selection', 'report_update'}
        assert rows[-1]['response']['response']['selection'] == outer['selection']
        assert set(provider.schemas[0]['properties']) == {'response'}


def test_invalid_response_and_lookup_stay_in_one_pending_decision(tmp_path):
    store, tools = setup(tmp_path)
    provider = ConversationProvider([None, lookup(limit=0), lookup(decision_indices=[0]),
        select(reason(2))])
    result = run(store, tools, provider, tmp_path / 'run', counts=(1, 1), decision_protocol=PROTOCOL)
    assert result['completed_actions'] == 1 and result['credit'] == 2
    assert count(store, 'runtime_model_calls') == count(store, 'runtime_actions') == 1
    assert count(store, 'runtime_observations') == 1
    rows = exchanges(store)
    assert len(rows) == 4
    assert rows[0]['response'] is None and rows[0]['response_recorded']
    assert all(row['lookup_result']['status'] == 'invalid' for row in rows[:-1])
    assert all(frame['kind'] == 'decision_lookup_result' for frame in provider.contexts[1:])


def test_invalid_report_value_preserves_selected_scientific_contribution(tmp_path):
    store, tools = setup(tmp_path)
    invalid_report = {**reason(2), 'report_update': []}
    provider = ConversationProvider([select(invalid_report), select(reason(0))])
    result = run(store, tools, provider, tmp_path / 'run', counts=(2, 2), decision_protocol=PROTOCOL)
    assert result['credit'] == 2 and result['completed_actions'] == 2
    assert provider.contexts[1]['fields']['feedback']['category'] == 'report_format'
    assert count(store, 'runtime_actions') == count(store, 'runtime_observations') == 2
    assert len(exchanges(store, 0)) == 1


def test_own_input_detail_requests_stay_inside_pending_decision(tmp_path):
    store, tools = setup(tmp_path)
    detail = {'response': {'response_type': 'request_context', 'lookup': {
        'view': 'own_attempt_detail', 'decision_index': 0, 'pointer': '/arguments/page',
        'offset': 0, 'limit': 1}}}
    provider = ConversationProvider([select(tool(page=7)), lookup(decision_indices=[0]), detail,
        select(reason(0))])
    result = run(store, tools, provider, tmp_path / 'run', counts=(2, 2), decision_protocol=PROTOCOL)
    assert result['completed_actions'] == 2 and tools.executions == 1
    assert provider.contexts[2]['result']['records'][0]['inputs']['arguments']['page'] == 7
    assert provider.contexts[3]['result']['view'] == 'own_attempt_detail'
    assert provider.contexts[3]['result']['values'] == 7
    assert count(store, 'runtime_model_calls') == count(store, 'runtime_observations') == 2
    assert len(exchanges(store, 1)) == 3


def test_continuing_decisions_use_deltas_and_compaction_restores(tmp_path):
    store, tools = setup(tmp_path)
    class SignedController(FixtureController):
        def observe(self, label, value, *, is_root):
            step = super().observe(label, value, is_root=is_root)
            original = step.as_record
            step.as_record = lambda: {**original(), 'marginal_credit': step.delta}
            return step
    provider = ConversationProvider([select(reason(3)), select(reason(-1)), lookup(), select(reason(0))],
        compact_after=(2,))
    result = asyncio.run(runtime.run_workflow(store, tools, provider=provider, run_dir=tmp_path / 'run',
        controller_factory=lambda path, initial: SignedController(str(path), initial, 3),
        project_credit=fixture_credit, decision_protocol=PROTOCOL))
    assert result['credit'] == 2
    assert [frame['kind'] for frame in provider.contexts] == [
        'decision_bootstrap', 'decision_update', 'decision_bootstrap', 'decision_lookup_result']
    assert 'goal' not in provider.contexts[1]['fields']
    assert provider.contexts[2]['fields']['current_credit'] == 2
    table = provider.contexts[2]['fields']['action_yields']['rows']
    assert table[0]['category'] == 'reason'
    assert table[0]['completed_actions'] == 2 and table[0]['total_yield'] == 2
    raw = json.loads(store.db.execute('SELECT request FROM runtime_model_calls '
        'WHERE call_index=2').fetchone()[0])['context']
    assert raw['controller']['scores'] == [3, -1]
    assert 'scores' not in provider.contexts[2]['fields']['controller']


def test_compaction_during_initial_bootstrap_requires_next_bootstrap(tmp_path):
    store, tools = setup(tmp_path)
    provider = ConversationProvider([lookup(), select(reason(0))], compact_after=(1,))
    run(store, tools, provider, tmp_path / 'run', counts=(1, 1), decision_protocol=PROTOCOL)
    assert [frame['kind'] for frame in provider.contexts] == ['decision_bootstrap', 'decision_bootstrap']
    assert provider.contexts[1]['restored_public_exchanges'][0]['response'] == lookup()


def test_lookup_visible_publications_extend_interpretation_basis_without_changing_raw_context(tmp_path):
    store, tools = setup(tmp_path)
    for index in range(40):
        store.add({'id': f'observation_padding_{index}', 'record_type': 'observation',
            'subject_refs': ['subject_A', 'subject_B']})
    provider = ConversationProvider([select(tool()), select(reason(0)), lookup(decision_indices=[0]),
        select(reason(0))])
    workflow = runtime.Workflow(store, tools, provider, tmp_path / 'run', 'basis-fixture',
        lambda path, initial: FixtureController(str(path), initial, 3), fixture_credit,
        decision_protocol=PROTOCOL)
    root = workflow.build('annotation', 'root', 'Fixture',
        store.validate_scope({'subject_refs': store.problem()['subject_refs']}))
    asyncio.run(root.run_async(workflow.context))
    raw = json.loads(store.db.execute('SELECT request FROM runtime_model_calls '
        'WHERE call_index=2').fetchone()[0])['context']
    target = 'observation_1_0_14'
    assert target not in raw['visible_record_refs']
    assert target in root.source.report_basis
    # Replaying a saved normalized final response recovers the same received
    # basis without a fresh lookup or a model call.
    root.source.calls = 2
    _, _, restored_context, _ = asyncio.run(root.source.call({}, {}))
    assert target in restored_context['visible_record_refs']
    assert target not in json.loads(store.db.execute('SELECT request FROM runtime_model_calls '
        'WHERE call_index=2').fetchone()[0])['context']['visible_record_refs']


@pytest.mark.parametrize('boundary', ['response', 'lookup', 'final'])
def test_reconstruction_replays_frozen_lookups_and_final_response(tmp_path, monkeypatch, boundary):
    store, tools = setup(tmp_path)
    original_method = (DecisionExchanges.respond if boundary in {'response', 'final'}
        else DecisionExchanges.resolve_lookup)
    raised = False

    def interrupt(self, episode_id, decision_index, exchange_index, value):
        nonlocal raised
        row = original_method(self, episode_id, decision_index, exchange_index, value)
        target = 1 if boundary == 'final' else 0
        if exchange_index == target and not raised:
            raised = True
            raise KeyboardInterrupt('Fixture interruption after durable ' + boundary)
        return row

    name = 'respond' if boundary in {'response', 'final'} else 'resolve_lookup'
    monkeypatch.setattr(DecisionExchanges, name, interrupt)
    first = ConversationProvider([lookup(), select(reason(1))])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, first, tmp_path / 'run', counts=(1, 1), decision_protocol=PROTOCOL)
    assert count(store, 'runtime_actions') == count(store, 'runtime_observations') == 0
    original = exchanges(store)
    monkeypatch.setattr(DecisionExchanges, name, original_method)
    if boundary != 'response':
        def no_reread(*args, **kwargs):
            raise AssertionError('A frozen lookup result must not be read again')
        monkeypatch.setattr(runtime, 'lookup_attempts', no_reread)
    resumed = ConversationProvider([] if boundary == 'final' else [select(reason(1))])
    result = run(store, tools, resumed, None, counts=(1, 1), resume=True)
    assert result['completed_actions'] == 1 and result['credit'] == 1
    assert count(store, 'runtime_model_calls') == count(store, 'runtime_actions') == 1
    assert count(store, 'runtime_observations') == 1
    if boundary == 'final':
        assert resumed.contexts == []
        assert exchanges(store) == original
    else:
        frame = resumed.contexts[0]
        assert frame['kind'] == 'decision_bootstrap'
        assert frame['restored_pending_decision_index'] == 0
        assert frame['restored_public_exchanges'][0]['response'] == lookup()
        if boundary == 'lookup':
            assert exchanges(store)[0]['lookup_result'] == original[0]['lookup_result']


def test_interrupted_dispatch_appends_exact_restoration_retry_without_rewriting(tmp_path):
    store, tools = setup(tmp_path)
    first = ConversationProvider([lookup(), KeyboardInterrupt('Fixture transport loss')])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, first, tmp_path / 'run', counts=(1, 1), decision_protocol=PROTOCOL)
    before = exchanges(store)
    assert not before[-1]['response_recorded']
    assert before[-1]['request']['context']['kind'] == 'decision_lookup_result'
    resumed = ConversationProvider([select(reason(1))])
    result = run(store, tools, resumed, None, counts=(1, 1), resume=True)
    after = exchanges(store)
    assert result['completed_actions'] == 1
    assert after[:2] == before
    assert after[2]['request']['retry_of_exchange_index'] == 1
    assert after[2]['request']['context']['kind'] == 'decision_bootstrap'
    assert after[2]['request']['context'] == resumed.contexts[0]
    assert after[2]['request']['context']['restored_public_exchanges'][0]['lookup_result'] == before[0]['lookup_result']
    assert count(store, 'runtime_model_calls') == count(store, 'runtime_observations') == 1


def test_injected_legacy_default_and_markerless_resume_do_not_migrate(tmp_path):
    store, tools = setup(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider([tool(), KeyboardInterrupt()]), tmp_path / 'run')
    original = store.db.execute('SELECT request FROM runtime_model_calls WHERE response IS NULL').fetchone()[0]
    settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
    assert 'decision_protocol' not in settings
    assert 'episode.history' in {item['name'] for item in json.loads(original)['context']['tools']}
    with pytest.raises(runtime.WorkflowError, match='original_decision_protocol'):
        run(store, tools, ScriptedProvider([]), None, resume=True, decision_protocol=PROTOCOL)
    resumed = ScriptedProvider([reason(0)])
    result = run(store, tools, resumed, None, resume=True)
    assert result['completed_actions'] == 2
    assert resumed.contexts[0] == json.loads(original)['context']
    assert store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_decision_exchanges'").fetchone() is None


def test_common_assembly_loads_saved_protocol_and_rejects_rebinding(tmp_path):
    store, tools = setup(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ConversationProvider([KeyboardInterrupt()]), tmp_path / 'run',
            decision_protocol=PROTOCOL)
    row = store.db.execute('SELECT run_id,settings FROM runtime_runs').fetchone()
    settings = json.loads(row['settings'])
    assert settings['decision_protocol'] == PROTOCOL
    assert json.loads((tmp_path / 'run/run.json').read_text())['decision_protocol'] == PROTOCOL
    options = dict(controller_factory=lambda path, initial: FixtureController(str(path), initial, 1),
        project_credit=fixture_credit, episode_binding_descriptors=settings['episode_bindings'])
    workflow = runtime.assemble_workflow(store, tools, ConversationProvider([]), tmp_path / 'run',
        row['run_id'], settings, **options)
    assert workflow.decision_protocol == PROTOCOL
    with pytest.raises(runtime.WorkflowError, match='original_decision_protocol'):
        runtime.assemble_workflow(store, tools, ConversationProvider([]), tmp_path / 'run',
            row['run_id'], settings, decision_protocol=None, **options)


@pytest.mark.parametrize('explicit_original', [False, True])
def test_owned_connection_defaults_new_and_explicit_null_keeps_original(tmp_path, monkeypatch,
                                                                     explicit_original):
    from gene_annotation_episode import providers, application_execution_binding
    store, tools = setup(tmp_path)
    instances = []
    class OwnedFixture(ScriptedProvider):
        def __init__(self, *args, **kwargs):
            super().__init__([reason(0) if explicit_original else select(reason(0))])
            instances.append(self)
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
    monkeypatch.setattr(providers, 'ModelConnection', OwnedFixture)
    monkeypatch.setattr(application_execution_binding, 'bind_episode_execution',
        lambda *args, settings, **kwargs: SimpleNamespace(settings=settings, runtime_binding=None))
    kwargs = {'decision_protocol': None} if explicit_original else {}
    result = asyncio.run(runtime.run_workflow(store, tools, run_dir=tmp_path / 'run',
        controller_factory=lambda path, initial: FixtureController(str(path), initial, 1),
        project_credit=fixture_credit, **kwargs))
    settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
    assert settings.get('decision_protocol') == (None if explicit_original else PROTOCOL)
    assert result['completed_actions'] == 1
    assert ('kind' not in instances[0].contexts[0]) == explicit_original
