"""Original forecast facts through ordinary scientific-child method_loop paths.

Scripted decisions and fixed-length controllers are engineering fixtures. The
homology variant uses real Store/protein bindings without submitting a job.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.resource_estimation import ESTIMATE_SCHEMA, ResourceToolEstimator, report_source
from gene_annotation_episode.runtime import DecisionSource, Record, run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_homology_episode_runtime import Provider, prepared
from test_runtime import FixtureController, fixture_credit, obj, setup, tool
from test_runtime_expectations import append, make_history


@pytest.fixture(params=['static', 'homology'])
def bound_case(tmp_path, request):
    if request.param == 'static':
        store, tools = setup(tmp_path)
        scope = {'subject_refs': ['subject_A']}
        history = tmp_path/'history.sqlite'
        execution_class = make_history(history)
        expectations = ExecutionExpectations(history,
            by_grain={'annotation': [execution_class], 'improvement': [execution_class]})
        jobs, binding, projector = None, None, fixture_credit
        action = lambda report=None: tool(report=report)
    else:
        store, _, _, scope, jobs, binding = prepared(tmp_path, statistics=True)
        tools = ToolRegistry(store)
        execution_class, = binding.prospective_execution_classes(store, scope)
        history = binding.statistics.history_path
        append(history, execution_class, 'initial-measured-duration', 2)
        expectations = ExecutionExpectations.for_homology(jobs, binding.statistics, roles=binding.roles,
            planning_roles=('annotation', 'improvement'))
        projector = lambda store, scope: 0
        action = lambda report=None: {'selection': {'kind': 'tool', 'tool': 'state.query',
            'arguments': {'kind': 'subject', 'offset': 0, 'limit': 1}}, 'report_update': report or {}}
    case = {'store': store, 'tools': tools, 'scope': scope, 'history': history,
        'execution_class': execution_class, 'expectations': expectations, 'jobs': jobs,
        'binding': binding, 'projector': projector, 'action': action, 'directory': tmp_path/'run'}
    try:
        yield case
    finally:
        if jobs is not None:
            assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
            jobs.close()
        store.close() if hasattr(store, 'close') else store.db.close()


def commission(case, schema, initial):
    return {'selection': {'kind': 'child', 'goal': 'Iteratively inspect the assigned question',
        'scope': case['scope'], 'purpose': 'Use the original recorded execution forecasts',
        'schema_json': json.dumps(schema), 'initial_report_json': json.dumps(initial)}, 'report_update': {}}


def run(case, provider, *, child_actions=2):
    return asyncio.run(run_workflow(case['store'], case['tools'], provider=provider,
        run_dir=case['directory'], controller_factory=lambda path, initial:
            FixtureController(str(path), initial, 2 if len(path) == 1 else child_actions),
        project_credit=case['projector'], job_episodes=case['binding'],
        execution_expectations=case['expectations'], resource_estimator=ResourceToolEstimator()))


def test_requested_forecast_source_uses_original_own_decision_records(bound_case):
    case = bound_case
    child_forecasts = []
    schema = obj({'execution': report_source()['report_schema']})
    def choose(context):
        assert context['resource_tool_estimates'][0]['expected_total_seconds'] == 2
        return commission(case, schema, {})
    def first(context):
        child_forecasts.append(deepcopy(context['resource_tool_estimates']))
        append(case['history'], case['execution_class'], 'later-measured-duration', 10)
        return case['action']()
    def second(context):
        child_forecasts.append(deepcopy(context['resource_tool_estimates']))
        assert child_forecasts[0][0]['expected_total_seconds'] == 2
        assert child_forecasts[1][0]['expected_total_seconds'] == 6
        return case['action']()
    def use_return(context):
        assert context['child_reports'] == [{'execution': child_forecasts[1]}]
        assert context['current_credit'] == 0
        assert 'resource_tool_estimates' not in context['child_reports'][0]
        return case['action']()
    result = run(case, Provider([choose, first, second, use_return]))
    assert result['completed_actions'] == 2 and result['credit'] == 0
    assert case['store'].db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
    saved = [json.loads(row[0]) for row in case['store'].db.execute(
        'SELECT form FROM runtime_report_attempts WHERE form IS NOT NULL')]
    assert saved == [{'execution': child_forecasts[1]}]


@pytest.mark.parametrize('forgery_at', ['initial', 'update'])
def test_prospective_forecast_identity_cannot_carry_changed_values(bound_case, forgery_at):
    case = bound_case
    schema = obj({'forecast': deepcopy(ESTIMATE_SCHEMA)})
    def choose(context):
        return commission(case, schema, {'forecast': context['resource_tool_estimates'][0]})
    def bad_initial(context):
        altered = {**context['resource_tool_estimates'][0], 'expected_total_seconds': 0}
        return commission(case, schema, {'forecast': altered})
    def correct_initial(context):
        assert context['feedback']['category'] == 'action_contract'
        return choose(context)
    def first(context):
        forecast = deepcopy(context['resource_tool_estimates'][0])
        if forgery_at == 'update':
            forecast['expected_total_seconds'] = 0
        return case['action']({'forecast': forecast})
    def second(context):
        if forgery_at == 'update':
            assert context['feedback']['category'] == 'report_format'
            assert context['feedback']['detail']['code'] == 'estimate_fact_mismatch'
            assert context['current_report_update']['forecast']['expected_total_seconds'] == 2
        return case['action']({'forecast': context['resource_tool_estimates'][0]})
    def use_return(context):
        assert context['child_reports'][0]['forecast']['expected_total_seconds'] == 2
        assert context['current_credit'] == 0
        return case['action']()
    script = ([bad_initial, correct_initial] if forgery_at == 'initial' else [choose])
    result = run(case, Provider([*script, first, second, use_return]))
    assert result['completed_actions'] == 2
    assert case['store'].db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4


def test_final_admission_and_redelivery_use_recorded_facts_without_refresh(bound_case, monkeypatch):
    case = bound_case
    schema = obj({'forecast': deepcopy(ESTIMATE_SCHEMA)})
    factual_schema = obj({'execution': report_source()['report_schema']})
    original_finish = DecisionSource.finish
    async def altered_return(source, record):
        result = await original_finish(source, record)
        if source.request.report_contract is None:
            return result
        altered = deepcopy(result.as_record())
        altered['form']['forecast']['expected_total_seconds'] = 0
        return Record(altered)
    monkeypatch.setattr(DecisionSource, 'finish', altered_return)
    def choose(context):
        return commission(case, schema, {'forecast': context['resource_tool_estimates'][0]})
    def child(context):
        return case['action']({'forecast': context['resource_tool_estimates'][0]})
    def repair(context):
        assert context['feedback']['kind'] == 'report_delivery_failure'
        assert context['feedback']['reason'] == 'estimate_fact_mismatch'
        append(case['history'], case['execution_class'], 'after-child-closed', 10)
        return {'selection': {'kind': 'redeliver_report', 'delivery_ref': context['feedback']['delivery_ref'],
            'purpose': 'Obtain the original closed-child forecast facts',
            'schema_json': json.dumps(factual_schema)}, 'report_update': {}}
    def use_return(context):
        assert context['resource_tool_estimates'][0]['expected_total_seconds'] == 6
        assert context['child_reports'][0]['execution'][0]['expected_total_seconds'] == 2
        return case['action']()
    result = run(case, Provider([choose, child, repair, use_return]), child_actions=1)
    assert result['completed_actions'] == 2 and result['pending_report_deliveries'] == 0
    assert case['store'].db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
    attempts = case['store'].db.execute('SELECT failure,form FROM runtime_report_attempts ORDER BY decision_index').fetchall()
    assert json.loads(attempts[0]['failure'])['reason'] == 'estimate_fact_mismatch'
    assert json.loads(attempts[1]['form'])['execution'][0]['expected_total_seconds'] == 2


def test_parent_field_named_estimate_ref_honors_its_declared_scientific_namespace(bound_case):
    case = bound_case
    schema = obj({'estimate_ref': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'subject'}})
    report = {'estimate_ref': case['scope']['subject_refs'][0]}
    def choose(context):
        return commission(case, schema, report)
    def child(context):
        return case['action'](report)
    def use_return(context):
        assert context['child_reports'] == [report]
        return case['action']()
    result = run(case, Provider([choose, child, use_return]), child_actions=1)
    assert result['completed_actions'] == 2
    assert case['store'].db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3


def test_forecast_namespace_protects_an_identity_under_a_parent_chosen_name(bound_case):
    case = bound_case
    forecast_schema = deepcopy(ESTIMATE_SCHEMA)
    forecast_schema['properties']['original_forecast'] = forecast_schema['properties'].pop('estimate_ref')
    forecast_schema['required'].remove('estimate_ref')
    forecast_schema['required'].append('original_forecast')
    schema = obj({'forecast': forecast_schema})
    def renamed(context):
        forecast = deepcopy(context['resource_tool_estimates'][0])
        forecast['original_forecast'] = forecast.pop('estimate_ref')
        return forecast
    def choose(context):
        return commission(case, schema, {'forecast': renamed(context)})
    def changed(context):
        forecast = renamed(context)
        forecast['expected_total_seconds'] = 0
        return case['action']({'forecast': forecast})
    def correct(context):
        assert context['feedback']['category'] == 'report_format'
        assert context['feedback']['detail']['code'] == 'estimate_fact_mismatch'
        return case['action']({'forecast': renamed(context)})
    def use_return(context):
        assert context['child_reports'][0]['forecast']['expected_total_seconds'] == 2
        return case['action']()
    result = run(case, Provider([choose, changed, correct, use_return]))
    assert result['completed_actions'] == 2
    assert case['store'].db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
