"""Actual registry/planner/runtime with scripted decisions; no execution jobs.

API clients are local fixtures that must receive no call. Native compatibility
selects only execution.estimate, never sequence.align or a native worker.
"""
import asyncio
from copy import copy, deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_timing_records import ApiTimingBinding
from gene_annotation_episode.assembled_service_setup import (
    bind_assembled_services_with_public_search_timing_planning)
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.resource_estimation import ResourceToolEstimator, reported_report_source
from gene_annotation_episode.run_statistics import ExecutionClass, ReportedResultStatistic, RunHistory
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_timing_runtime import TimingClient
from test_hmmer_api_operations import registry
from test_resource_service_setup import resources
from test_runtime import FixtureController, ScriptedProvider, obj
from test_scientific_process_library import independent_source


API_FIELDS = ('api_reported_execution_expectations', 'api_reported_execution_forecasts',
    'api_execution_options', 'api_timing_planning_disposition')
ROLES = ('scientific_process', 'literature', 'launch', 'monitor', 'results')


def own(name, **arguments):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments}, 'report_update': {}}


def planning_host(r, tmp_path, monkeypatch, *, script=(), count=3):
    from gene_annotation_episode.resource_episodes import HomologyResourceAdapter
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', lambda adapter: {
        'resource_id': adapter.resource_id, 'kind': 'local', 'availability': 'unknown',
        'observed_at': '2026-10-22T00:00:00+00:00', 'provenance_refs': [],
        'knowledge_entry_ids': [], 'tool_names': []})
    subject, = r.store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']
    scope = r.store.validate_scope({'subject_refs': [subject]})
    source_directory = tmp_path/'source'
    independent_source(source_directory)
    client = TimingClient()
    tools = ToolRegistry(r.store, clients=client)
    selected_registry = registry(client)
    history_path = tmp_path/'history.sqlite'
    RunHistory(history_path).close()
    binding = ApiTimingBinding(ledger_path=tmp_path/'timing.sqlite', history_path=history_path,
        resource_id=selected_registry['resource_id'], monitoring_information_unit=.5)
    estimator = ResourceToolEstimator.with_reported_results()
    controllers = {}

    def controller(path, initial):
        value = FixtureController(str(path), initial, count)
        controllers[path] = value
        return value

    def services(store, **operands):
        return bind_assembled_services_with_public_search_timing_planning(store,
            public_search_registry=selected_registry, api_timing=binding,
            source_directory=source_directory,
            tool_retrieval={'version': 'scientific_tool_retrieval_v1', 'mode': 'literal_test_v1'},
            scientific_child_roles=ROLES, handoff_unit=3.25, acquired_record_unit=.375,
            monitoring_information_unit=.5, literature_outcome_page_size=7,
            monitor_outcome_page_size=13, log_window_bytes=123,
            log_roles=('native_stderr',), **operands)

    provider = ScriptedProvider(script)
    workflow = Workflow(r.store, tools, provider, tmp_path/'run', r.run_id,
        controller_factory=controller, project_credit=lambda *_: 0,
        job_episodes=r.homology, resource_estimator=estimator,
        episode_service_factory=services, episode_service_binding={
            'version': 'api_execution_planning_runtime_fixture_v1',
            'api_execution_planning': {'version': 'hmmer_api_execution_planning_v1',
                'callable': 'execution.estimate', 'target': 'public.hmmer.search'}},
        episode_service_inputs='actual_tool_registry_v1',
        episode_record_receipts=True, initial_known_record_refs=[subject],
        annotation_child_roles=ROLES)
    owner = workflow.build('annotation', 'parent', 'Exercise explicit forecast information', scope)
    planner = tools.api_execution_planner
    arguments = {'tool': 'public.hmmer.search', 'arguments': {
        'subject_ref': subject, 'algorithm': 'phmmer', 'database': 'fixture'},
        'resource_selection': {
            'resource_id': selected_registry['resource_id'], 'kind': 'api',
            'allocation': {key: None for key in ('cpu', 'memory_bytes', 'scratch_bytes', 'wall_seconds')},
            'capability_binding_ref': selected_registry['registry_ref']},
        'constraints': {}, 'immutable_input_versions': []}
    return SimpleNamespace(r=r, workflow=workflow, owner=owner, tools=tools, planner=planner,
        arguments=arguments, scope=scope, client=client, provider=provider,
        controllers=controllers, history_path=history_path)


def run_owner(h):
    record = asyncio.run(h.owner.run_async(h.workflow.context))
    asyncio.run(h.owner.build_result(record))
    return record


def actions(h, source=None):
    return [json.loads(row[0]) for row in h.r.store.db.execute(
        'SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
        (h.r.run_id, (source or h.owner.source).episode_id))]


def test_selected_forecast_precedes_next_scientific_choice_and_unavailable_replaces_old_context(
        resources, tmp_path, monkeypatch):
    h = planning_host(resources, tmp_path, monkeypatch)
    second = deepcopy(h.arguments)
    second['arguments']['parameters'] = {'include_taxonomy': [1]}
    seen = []

    def after_first(context):
        proposal = context['api_execution_proposal']
        assert proposal['arguments'] == h.arguments['arguments']
        assert context['api_reported_execution_forecasts'][0]['reported_result_support'] == {
            'reported_result_count': 0}
        assert all(context[key] == proposal[key] for key in API_FIELDS)
        assert context['current_credit'] == context['monitoring_information_credit'] == 0
        assert context['controller']['scores'] == [0]
        assert h.client.calls == []
        assert h.r.store.db.execute('SELECT count(*) FROM public_search_orders').fetchone()[0] == 0
        seen.append(deepcopy(context))
        return own('execution.estimate', **second)

    def after_second(context):
        proposal = context['api_execution_proposal']
        assert proposal['arguments'] == second['arguments']
        assert context['api_reported_execution_forecasts'] == context['api_execution_options'] == []
        assert context['api_timing_planning_disposition']['code'] == 'unsupported_statistics_configuration'
        assert all(context[key] == proposal[key] for key in API_FIELDS)
        assert context['controller']['scores'] == [0, 0]
        assert h.workflow.waiting_support(h.owner.source, context)['duration_expectations'] == []
        seen.append(deepcopy(context))
        return own('state.query', refs=[])

    h.workflow.provider = ScriptedProvider([own('execution.estimate', **h.arguments),
        after_first, after_second])
    record = run_owner(h)
    outcomes = actions(h)
    assert record.units_consumed == 3 and len(seen) == 2
    assert h.controllers[h.owner.source.path].scores == [0, 0, 0]
    assert 'api_execution_proposal' not in h.workflow.provider.contexts[0]
    assert all(outcome['status'] == 'completed' and outcome['record_refs'] == [] for outcome in outcomes)
    for outcome in outcomes[:2]:
        assert all(outcome[key] == outcome['result'][key] for key in API_FIELDS)
        assert 'native_execution_expectations' not in outcome and 'resource_tool_estimates' not in outcome
    assert outcomes[1]['api_reported_execution_forecasts'] == []
    assert outcomes[2]['api_reported_execution_forecasts'] == []
    assert h.r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
    assert h.client.calls == []
    assert h.workflow.source_credit_view(h.owner.source)['monitoring_information_credit'] == 0
    assert h.workflow.facts(h.owner.source)['resource_tool_estimates'] == []


def test_original_own_proposal_validation_is_pure_scoped_and_rejects_tampering(
        resources, tmp_path, monkeypatch):
    h = planning_host(resources, tmp_path, monkeypatch, count=1)
    h.workflow.provider = ScriptedProvider([own('execution.estimate', **h.arguments)])
    run_owner(h)
    source = h.owner.source
    original = deepcopy(actions(h)[0])
    assert h.workflow.api_execution_planning_context(source, before_decision_index=0) is None
    unrelated = h.workflow.build('annotation', 'unrelated', 'Own independent scope', h.scope)
    assert h.workflow.api_execution_planning_context(unrelated.source, before_decision_index=2) is None

    def forbidden(*args, **kwargs):
        raise AssertionError('Original proposal validation must use no current sequence/history/scope query')

    monkeypatch.setattr(h.planner.timing.statistics, 'capture', forbidden)
    monkeypatch.setattr(h.r.store, 'get', forbidden)
    monkeypatch.setattr(h.r.store, 'validate_scope', forbidden)
    context = h.workflow.api_execution_planning_context(source, before_decision_index=1)
    assert context['api_execution_proposal'] == original['result']
    assert all(context[key] == original[key] for key in API_FIELDS)
    context['api_execution_proposal']['arguments']['database'] = 'changed-copy'
    assert h.workflow.api_execution_planning_context(source, before_decision_index=1)[
        'api_execution_proposal'] == original['result']
    forged_scope = copy(source)
    forged_scope.scope = {**deepcopy(source.scope), 'subject_refs': []}
    with pytest.raises(ContractError, match='api_execution_proposal_conflict'):
        h.workflow.api_execution_planning_context(forged_scope, before_decision_index=1)
    row = h.workflow.journal.row('runtime_actions', source.episode_id, 0)
    forged = deepcopy(original)
    forged['result']['api_reported_execution_forecasts'][0]['expected_total_seconds'] = 123
    h.workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
        'decision_index': 0, 'action': row['action'], 'result': canonical(forged), 'credit': row['credit']})
    with pytest.raises(ContractError, match='api_execution_proposal_conflict'):
        h.workflow.api_execution_planning_context(source, before_decision_index=1)
    # The ordinary tool's existing idempotent cache replays its original saved
    # envelope before dispatch. Runtime still validates that actual payload.
    tool_row = h.r.store.db.execute('SELECT operation_key,result FROM tool_operations').fetchone()
    saved_tool = json.loads(tool_row['result'])
    for field, changed in (('version', 'foreign_version'), ('tool', 'sequence.align'),
            ('constraints', {'allowed_kinds': ['api']})):
        forged_tool = deepcopy(saved_tool)
        forged_tool['result'][field] = changed
        h.r.store.db.execute('UPDATE tool_operations SET result=? WHERE operation_key=?',
            (canonical(forged_tool), tool_row['operation_key']))
        with pytest.raises(ContractError, match='api_execution_proposal_conflict'):
            asyncio.run(h.workflow.execute(source, 'execution.estimate', h.arguments,
                decision_index=0, operation_key=tool_row['operation_key']))
    h.r.store.db.execute('UPDATE tool_operations SET result=? WHERE operation_key=?',
        (tool_row['result'], tool_row['operation_key']))


def test_saved_decision_context_is_exact_and_new_explicit_proposal_can_learn(
        resources, tmp_path, monkeypatch):
    h = planning_host(resources, tmp_path, monkeypatch, count=3)
    h.workflow.provider = ScriptedProvider([own('execution.estimate', **h.arguments), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(h.owner.run_async(h.workflow.context))
    source = h.owner.source
    index = 1
    original_request = h.workflow.journal.row('runtime_model_calls', source.episode_id, index)['request']
    original_context = json.loads(original_request)['context']
    assert original_context['api_reported_execution_forecasts'][0]['expected_total_seconds'] is None
    first = actions(h)[0]['result']
    scope = ExecutionClass(**first['api_reported_execution_expectations'][0]['execution_classes'][0])
    history = RunHistory(h.history_path, create=False)
    try:
        history.record_reported_result(scope, ReportedResultStatistic(
            observation_sha256='a'*64, source_sha256='b'*64,
            observed_at='2026-10-22T00:00:00+00:00', elapsed_seconds=8, condition_ref=None))
    finally:
        history.close()

    def forbidden(*args, **kwargs):
        raise AssertionError('Saved decision must not reconstruct its proposal')

    original_projector = h.workflow.api_execution_planning_context
    monkeypatch.setattr(h.workflow, 'api_execution_planning_context', forbidden)
    source.calls = index
    h.workflow.provider = ScriptedProvider([own('state.query', refs=[])])
    response, replay_index, replay_context, _ = asyncio.run(source.call(
        {'visible_record_refs': [], 'changed': True}, obj({})))
    assert replay_index == index and replay_context == original_context
    assert h.workflow.journal.row('runtime_model_calls', source.episode_id, index)['request'] == original_request
    assert response == own('state.query', refs=[])
    source.calls = index
    h.workflow.provider = ScriptedProvider([])
    assert asyncio.run(source.call({}, obj({})))[2] == original_context
    monkeypatch.setattr(h.workflow, 'api_execution_planning_context', original_projector)
    asyncio.run(source.execute(response['selection'], index))
    asyncio.run(source.execute(own('execution.estimate', **h.arguments)['selection'], 2))
    h.workflow.provider = ScriptedProvider([own('state.query', refs=[])])
    source.calls = 3
    _, _, newer, _ = asyncio.run(source.call({'visible_record_refs': []}, h.workflow.action_schema(source)))
    assert newer['api_reported_execution_forecasts'][0]['expected_total_seconds'] == 8
    assert newer['api_reported_execution_forecasts'][0]['reported_result_support'] == {'reported_result_count': 1}
    assert first['api_reported_execution_forecasts'][0]['expected_total_seconds'] is None
    assert h.workflow.journal.row('runtime_model_calls', source.episode_id, index)['request'] == original_request
    assert h.client.calls == []


def test_parent_selected_tool_set_and_private_child_proposal_are_separate(
        resources, tmp_path, monkeypatch):
    h = planning_host(resources, tmp_path, monkeypatch, count=1)
    library = h.workflow.scientific_process_binding.library
    form = obj({'forecasts': reported_report_source()['report_schema']})

    def child(index, names):
        selected = {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': 'Investigate the explicitly selected fixture alternative',
            'scope': h.scope, 'purpose': 'Return the requested original forecast rows',
            'schema_json': json.dumps(form), 'initial_report_json': '{}',
            'assignment': {'selection': {'version': 'scientific_process_selection_v2',
                'annotation_ref': library.reference('A01'), 'thought_ref': library.reference('P01'),
                'tools': names}, 'evidence_refs': [], 'constraints': {}, 'context': {}}}
        return h.workflow.selected(h.owner.source, selected, index).child

    excluded = child(0, [])
    result = asyncio.run(h.workflow.execute(excluded.source, 'execution.estimate', h.arguments,
        decision_index=0, operation_key='unselected-estimate'))
    assert result['status'] == 'invalid' and result['feedback']['code'] == 'tool_not_available_to_episode'
    assert h.r.store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 0
    included = child(1, ['execution.estimate'])
    asyncio.run(included.source.execute(own('execution.estimate', **h.arguments)['selection'], 0))
    original = actions(h, included.source)[0]['result']
    assert h.workflow.api_execution_planning_context(included.source, before_decision_index=1)[
        'api_execution_proposal'] == original
    assert h.workflow.api_execution_planning_context(h.owner.source, before_decision_index=2) is None
    reference = original['api_reported_execution_forecasts'][0]['estimate_ref']
    assert h.workflow.api_forecast_reference(h.workflow.binding_context(included.source),
        reference, 'job_execution_estimate')
    assert not h.workflow.api_forecast_reference(h.workflow.binding_context(h.owner.source),
        reference, 'job_execution_estimate')
    assert h.workflow.services.reference_in_context(h.workflow.binding_context(included.source),
        reference, 'job_execution_estimate')
    assert not h.workflow.services.reference_in_context(h.workflow.binding_context(h.owner.source),
        reference, 'job_execution_estimate')
    h.workflow.provider = ScriptedProvider([own('episode.history', view='index')])
    h.owner.source.calls = 2
    _, _, parent_context, _ = asyncio.run(h.owner.source.call(
        {'visible_record_refs': []}, h.workflow.action_schema(h.owner.source)))
    assert 'api_execution_proposal' not in parent_context
    assert parent_context.get('api_reported_execution_forecasts', []) == []
    assert h.client.calls == []


def test_native_only_execution_estimate_keeps_original_result_and_controller_unit(tmp_path):
    history_path = tmp_path/'history.sqlite'
    RunHistory(history_path).close()
    with Store(tmp_path/'workspace') as store:
        subject, = store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']
        scope = store.validate_scope({'subject_refs': [subject]})
        tools = ToolRegistry(store, native_statistics=OrdinaryExecutionStatistics(
            history_path, 'native-estimation-fixture', tmp_path/'receipts'))
        estimator = ResourceToolEstimator()
        arguments = {'tool': 'sequence.align', 'arguments': {'query_ref': subject,
            'reference_ref': subject, 'molecule': 'protein', 'mode': 'global'}}
        provider = ScriptedProvider([own('execution.estimate', **arguments)])
        controllers = []

        def factory(path, initial):
            value = FixtureController(str(path), initial, 1)
            controllers.append(value)
            return value

        workflow = Workflow(store, tools, provider, tmp_path/'run', 'native-only', factory,
            lambda *_: 0, resource_estimator=estimator)
        owner = workflow.build('annotation', 'parent', 'Estimate only; execute no alignment', scope)
        record = asyncio.run(owner.run_async(workflow.context))
        asyncio.run(owner.build_result(record))
        row = workflow.journal.row('runtime_actions', owner.source.episode_id, 0)
        outcome = json.loads(row['result'])
        original = json.loads(store.db.execute('SELECT result FROM tool_operations').fetchone()[0])
        assert tools.api_execution_planner is None and record.units_consumed == 1
        assert outcome['result'] == original['result']
        assert outcome['native_execution_expectations'] == original['result']['execution_expectations']
        assert outcome['resource_tool_estimates'] == estimator.estimate_context(outcome['native_execution_expectations'])
        assert not any(name in outcome for name in API_FIELDS)
        assert controllers[0].scores == [0]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        assert not list(store.path.glob('.native-sequence-*'))


@pytest.mark.parametrize('api_planning', [False, True], ids=['no_api', 'api'])
def test_pending_decision_without_restoration_metadata_keeps_original_request_on_fresh_session(
        resources, tmp_path, monkeypatch, api_planning):
    class SessionProvider(ScriptedProvider):
        def __init__(self, script, *, existing_session):
            super().__init__(script)
            self.existing_session = existing_session

        def has_session(self, episode_id, role):
            return self.existing_session

    if api_planning:
        h = planning_host(resources, tmp_path, monkeypatch)
        workflow, owner = h.workflow, h.owner
        asyncio.run(owner.source.execute(own('execution.estimate', **h.arguments)['selection'], 0))
        owner.source.calls = 1
    else:
        subject, = resources.store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']
        scope = resources.store.validate_scope({'subject_refs': [subject]})
        tools = ToolRegistry(resources.store, clients=TimingClient())
        workflow = Workflow(resources.store, tools, ScriptedProvider([]), tmp_path/'run',
            resources.run_id, lambda path, initial: FixtureController(str(path), initial, 3), lambda *_: 0)
        owner = workflow.build('annotation', 'parent', 'Keep the original pending request', scope)
    source = owner.source
    index = source.calls
    workflow.provider = SessionProvider([KeyboardInterrupt()], existing_session=True)
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(source.call({'visible_record_refs': [], 'scope': source.scope}, workflow.action_schema(source)))
    original = workflow.journal.row('runtime_model_calls', source.episode_id, index)
    assert original['response'] is None
    original_request = original['request']
    supplied = json.loads(original_request)
    assert 'restored_episode_history' not in supplied['context']
    if api_planning:
        assert supplied['context']['api_execution_proposal']['arguments'] == h.arguments['arguments']

    def forbidden(*args, **kwargs):
        raise AssertionError('Saved pending request must not reconstruct history or recapture forecasts')

    monkeypatch.setattr(workflow, 'history_preview', forbidden)
    monkeypatch.setattr(workflow, 'api_execution_planning_context', forbidden)
    monkeypatch.setattr(workflow, 'native_estimation_context', forbidden)
    if api_planning:
        monkeypatch.setattr(h.planner.timing.statistics, 'capture', forbidden)
    fresh = SessionProvider([own('state.query', refs=[])], existing_session=False)
    workflow.provider = fresh
    source.calls = index
    response, replay_index, context, schema = asyncio.run(source.call(
        {'visible_record_refs': [], 'different_context': True}, obj({})))
    assert replay_index == index and context == supplied['context'] and schema == supplied['schema']
    assert fresh.contexts == [supplied['context']]
    assert workflow.journal.row('runtime_model_calls', source.episode_id, index)['request'] == original_request
    assert 'restored_episode_history' not in context
    source.calls = index
    assert asyncio.run(source.call({}, obj({})))[0] == response
    assert workflow.journal.row('runtime_model_calls', source.episode_id, index)['request'] == original_request
