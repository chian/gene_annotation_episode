"""Pure scheduling/valuation and original-result custody regressions."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import os

import pytest

from gene_annotation_episode import hpc_prediction as prediction
from gene_annotation_episode.hpc_episodes import HPCEpisodes
from gene_annotation_episode.hpc_ledger import HPCLedger
from gene_annotation_episode.hpc_monitoring import (
    DEFAULT_POLICY, HPCContinuationEstimator, MonitorCheckpoint, MonitorCronController, choose_schedule)
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.hpc_scheduler import resume_spec
from gene_annotation_episode.state import Store
from hpc_helpers import commission, resources
from test_hpc_episode_design import context
from test_practical_yield import completion_context


def forecast(c, state='queued'):
    value = prediction.predict(prediction.prior_model(c['model']), {'size': 1})
    return prediction.update(value, {'state': state, 'observed_at': 100.,
        'queue_elapsed_seconds': 20., 'work_elapsed_seconds': 0.})


def test_published_result_source_is_readable_only_by_original_received_owner(tmp_path):
    with Store(tmp_path/'store') as store:
        manifest = tmp_path/'inputs.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
        store.create_problem(manifest_path=manifest)
        binding = HPCEpisodes(None, store=store, run_id='test-run', directory=tmp_path,
                              resources=resources(), commissions={'commission': commission()})
        parent = context()
        binding.initialize(parent)
        body = {'run_id': 'test-run', 'episode_id': parent.episode_id, 'scope': {'subject_refs': []},
                'unit': {'finished_at': 100.}, 'document': {'quality': .95}}
        source = binding._publish(parent, body)
        receipt = {**body, 'source_ref': source}
        binding.state(parent).put('result', receipt)
        with pytest.raises(ValueError, match='not_received_or_not_owned'):
            binding.read_evidence(parent, binding.state(parent), source)
        received = replace(parent, received_record_refs=(source,))
        result = asyncio.run(binding.execute(received, 'hpc.read', {'reference': source}, 'read-original'))
        assert result['result'] == receipt
        assert asyncio.run(binding.execute(received, 'hpc.read', {'reference': source}, 'read-original')) == result
        other = replace(context(owner='another-owner'), received_record_refs=(source,))
        with pytest.raises(ValueError, match='not_received_or_not_owned'):
            binding.read_evidence(other, binding.state(other), source)


def test_pending_credit_supports_long_wait_without_awarding_sleep_credit():
    c = commission()
    before = deepcopy(c)
    policy = {**DEFAULT_POLICY, 'max_interval_seconds': 1200.}
    chosen = choose_schedule(forecast(c), c['candidates'][0], c, policy, now=100.)
    assert chosen['schedule']
    assert chosen['delay_seconds'] > policy['min_interval_seconds']
    assert chosen['expected_continuation_credit'] > 0
    assert chosen['earned_wait_credit'] == 0
    assert c == before
    expensive = choose_schedule(forecast(c), c['candidates'][0], c,
        {**policy, 'monitor_cost': 100.}, now=100.)
    assert not expensive['schedule'] and expensive['expected_continuation_credit'] == 0
    accepted = choose_schedule(forecast(c), c['candidates'][0], c, policy,
        credited=['original-work'], now=100.)
    assert not accepted['schedule']
    later = choose_schedule(forecast(c), c['candidates'][0], c, policy, now=5001.)
    assert later['schedule']  # Elapsed time alone cannot expire valuable work.


def test_broad_setup_prior_preserves_possible_success_and_pending_monitor_value():
    import math
    c = commission()
    candidate = c['candidates'][0]
    candidate['wall_seconds'] = 600
    value = forecast(c)
    value['times']['setup'] = prediction.distribution(math.log1p(30), 16.2773)
    value['times']['work'] = prediction.distribution(math.log1p(120), 16.2773)
    assert prediction.quantile(value['times']['setup']) > candidate['wall_seconds']
    result = prediction.compare(candidate, value, c['obligations'], c['preferences'])
    chance = result['attainable_units'][0]['completion_probability']
    upper = prediction.probability_within(value['times']['setup'], 600)*value['success_probability']
    assert 0 < chance < upper
    selected = choose_schedule(value, candidate, c, DEFAULT_POLICY, now=100.)
    assert selected['schedule'] and selected['expected_continuation_credit'] > 0
    assert selected['earned_wait_credit'] == 0


def test_running_work_does_not_pay_setup_again():
    c = commission()
    candidate = c['candidates'][0]
    value = forecast(c, 'running')
    value['telemetry']['allocation_remaining_seconds'] = 120
    result = prediction.compare(candidate, value, c['obligations'], c['preferences'])
    expected = prediction.probability_within(value['times']['work'], 120)*value['success_probability']
    assert result['attainable_units'][0]['completion_probability'] == pytest.approx(expected)


def test_monitor_checkpoint_keeps_exact_job_forecast_due_and_action(tmp_path):
    c = commission()
    ledger = HPCLedger(tmp_path, c)
    candidate = c['candidates'][0]
    plan = {'plan_id': 'original-plan'}
    ledger.put('plan', plan)
    ledger.put('forecast', {'plan_id': 'original-plan', 'issued_at': 100.})
    monitor = {'conditional_prediction': forecast(c), 'forecast_ref': 'original-forecast'}
    controller = MonitorCronController(ledger)
    controller.attach(plan, 'original-job', DEFAULT_POLICY)
    selected = controller.reserve(plan, candidate, monitor, 'selected-monitor', now=100.)
    assert selected == controller.reserve(plan, candidate, monitor, 'selected-monitor', now=200.)
    assert selected['forecast_ref'] == 'original-forecast'
    assert selected['wake_action']['tool'] == 'hpc.monitor'
    assert selected['job_id'] == 'original-job'
    assert ledger.credit_view()['credit'] == 0
    with pytest.raises(ValueError, match='immutable'):
        controller.attach(plan, 'different-job', DEFAULT_POLICY)
    # A selected future monitor yields a checkpoint, never an early observation.
    future = {**selected, 'due_at': 1e12}
    with pytest.raises(MonitorCheckpoint) as checkpoint:
        asyncio.run(controller.wait(future))
    assert checkpoint.value.schedule == future


def test_wait_establishes_observed_state_and_collects_known_completion(tmp_path, monkeypatch):
    """Pure dispatch check: no remote transport, model or clock sleep."""
    c = commission()
    c['monitoring'] = dict(DEFAULT_POLICY)
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    ledger = binding.state(parent)
    plan = {'plan_id': 'original-plan', 'candidate_id': c['candidates'][0]['id']}
    reference = ledger.put('plan', plan)
    ledger.put('handoff', {'plan_id': plan['plan_id']})
    ledger.put('forecast', {'plan_id': plan['plan_id'], 'issued_at': 100.})
    MonitorCronController(ledger).attach(plan, 'original-job', c['monitoring'])
    monkeypatch.setattr(binding, '_target', lambda *args: {'execution_id': 'original-job'})
    original_execute = binding.execute
    observed = []
    async def dispatch(ctx, tool, arguments, operation_key):
        if tool == 'hpc.monitor':
            observed.append(operation_key)
            ledger.put('monitor', {'plan_id': plan['plan_id'], 'forecast_ref': 'observed-terminal',
                                  'conditional_prediction': forecast(c, 'complete')})
            return {'result': {'observed': True}}
        return await original_execute(ctx, tool, arguments, operation_key)
    monkeypatch.setattr(binding, 'execute', dispatch)
    result = asyncio.run(binding.execute(parent, 'hpc.monitor.wait', {'plan_ref': reference}, 'wait-original'))
    assert result['result']['reason'] == 'observed_terminal_job_collect_now'
    assert len(observed) == 1
    assert not ledger.records('monitor_schedule')
    assert not ledger.records('monitor_wake')  # No claim that a timer fired.
    assert asyncio.run(binding.execute(parent, 'hpc.monitor.wait', {'plan_ref': reference}, 'wait-original')) == result
    assert len(observed) == 1


def test_missing_monitor_controller_returns_original_job_recovery_feedback(tmp_path, monkeypatch):
    """A legacy commission can recover without crashing or submitting work."""
    c = commission()
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    ledger = binding.state(parent)
    plan = {'plan_id': 'original-plan', 'candidate_id': c['candidates'][0]['id']}
    reference = ledger.put('plan', plan)
    ledger.put('handoff', {'plan_id': plan['plan_id']})
    monkeypatch.setattr(binding, '_target', lambda *args: {'execution_id': 'original-job'})
    result = asyncio.run(binding.execute(parent, 'hpc.monitor.wait', {'plan_ref': reference}, 'legacy-wait'))
    assert result['status'] == 'invalid'
    assert result['feedback']['code'] == 'hpc_monitor_controller_not_attached'
    assert 'hpc.monitor' in result['feedback']['next_step']
    assert 'hpc.results' in result['feedback']['next_step']
    assert not ledger.records('monitor_schedule')
    assert not ledger.records('monitor_wake')
    assert ledger.credit_view()['credit'] == 0
    assert asyncio.run(binding.execute(parent, 'hpc.monitor.wait', {'plan_ref': reference}, 'legacy-wait')) == result


def test_calendar_resume_is_bound_to_selected_monitor_and_original_window(tmp_path):
    directory = tmp_path/'runs'/'campaign'
    schedule = {'version': 'hpc_monitor_schedule_v1', 'schedule_ref': 'original-schedule',
        'reconsider_at': '2026-11-04T07:20:00+00:00', 'job_id': 'original-job',
        'wake_action': {'tool': 'hpc.monitor'}, 'valuation': {'schedule': True}}
    window = os.environ['CODEX_THREAD_ID']
    spec = resume_spec(directory, tmp_path, ['/python', '/original-driver'], schedule, window=window)
    assert spec == resume_spec(directory, tmp_path, ['/python', '/original-driver'], schedule, window=window)
    assert '--setenv=CODEX_THREAD_ID='+window in spec['registration_argv']
    assert '--on-calendar=2026-11-04 07:20:00 UTC' in spec['registration_argv']
    assert spec['command'][1] == str(tmp_path/'tools'/'one_workflow.sh')
    assert spec['schedule']['job_id'] == 'original-job'
    with pytest.raises(ValueError, match='explicit_pending_monitor'):
        resume_spec(directory, tmp_path, ['/python'], {**schedule, 'wake_action': {'tool': 'hpc.plan'}}, window=window)


def test_yield_controller_uses_frozen_future_value_without_changing_actual_credit():
    saved = {}
    controller = YieldController('hpc', 0., .001,
        estimate_with_context=HPCContinuationEstimator(lambda packet: saved[packet['reference']] == packet['evidence']))
    for index, expected in enumerate((3., 2., 0.)):
        ctx = completion_context(unit_index=index, action_index=index)
        ctx.pop('practical_completion')
        evidence = {'run_id': 'run-practical', 'episode_id': 'episode-practical',
                    'operation_key': f'run-practical:episode-practical:{index}',
                    'active_credit_ceiling': 0.,
                    'expected_continuation_credit': expected}
        saved[str(index)] = evidence
        ctx['hpc_continuation'] = {'reference': str(index), 'evidence': evidence}
        step = controller.observe('observed-or-waited', {'credit': 0., 'estimation_context': ctx})
        assert step.stop == (expected == 0)
        assert step.marginal_credit == 0
        assert step.estimate.expected_next_gain.value == expected
    assert controller.estimator.scores == (0., 0., 0.)


def test_old_unbound_controller_observations_replay_without_changed_provenance():
    original = YieldController('original', 0., .001)
    restored = YieldController('original', 0., .001, estimate_with_context=HPCContinuationEstimator(lambda _: False))
    for value in (0., 0., 0., .001):
        assert original.observe('action', value).as_record() == restored.observe('action', value).as_record()


def test_delayed_result_credit_does_not_become_active_grinding_yield():
    from gene_annotation_episode.numerical import YieldParameters
    ctx = completion_context(unit_index=2, action_index=7)
    ctx.pop('practical_completion')
    body = {'run_id': 'run-practical', 'episode_id': 'episode-practical',
            'operation_key': 'run-practical:episode-practical:7',
            'active_history_indices': [0, 1], 'active_credit_ceiling': 0.,
            'expected_continuation_credit': 2.}
    ctx['hpc_continuation'] = {'reference': 'retained-value', 'evidence': body}
    estimated = HPCContinuationEstimator(lambda _: True, cost=.001)((0., 0., 10.), YieldParameters(), (None, None, ctx))
    assert estimated.diagnostics['active_next_gain']['value'] == 0
    assert estimated.diagnostics['pending_expected_credit'] == 2
    assert estimated.diagnostics['activity_mode'] == 'wait'
    assert estimated.expected_next_gain.value == 2
    body.update(pending_action='collect', valuation={'value_kind': 'unresolved_acceptance_upper_bound'})
    unparsed = HPCContinuationEstimator(lambda _: True, cost=.001)((0., 0., 10.), YieldParameters(), (None, None, ctx))
    assert unparsed.diagnostics['activity_mode'] == 'collect'
    assert unparsed.diagnostics['pending_expected_credit'] is None
    assert unparsed.expected_next_gain.lower == 0
    assert unparsed.expected_next_gain.upper == 2
    body.pop('active_credit_ceiling')
    uncertain = HPCContinuationEstimator(lambda _: True, cost=.001)((0., 0., 10.), YieldParameters(), (None, None, ctx))
    assert uncertain.diagnostics['activity_mode'] == 'active_yield_unknown'


def test_completed_original_goal_closes_on_new_action_without_rewriting_history(tmp_path):
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': commission()})
    parent = context()
    binding.initialize(parent)
    ledger = binding.state(parent)
    assert binding.continuation_for_action(parent, 'test-run:parent:1') is None
    result = ledger.put('result', {'quality': .95})
    ledger.accept('original-work', result)
    captured = binding.continuation_for_action(parent, 'test-run:parent:2')
    assert captured['evidence']['expected_continuation_credit'] == 0
    assert binding.continuation_for_action(parent, 'test-run:parent:2') == captured
    assert ledger.credit_view()['credit'] == 10


def test_pending_allocations_deduplicate_the_same_obligation_and_add_different_work(tmp_path):
    c = commission()
    c['obligations']['second-work'] = deepcopy(c['obligations']['original-work'])
    second = deepcopy(c['candidates'][0])
    second['id'] = 'second-portfolio'
    second['units'][0].update(unit_id='unit-2', obligation_id='second-work')
    c['candidates'].append(second)
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    ledger = binding.state(parent)
    for ordinal, candidate in enumerate([c['candidates'][0], c['candidates'][0], second]):
        plan = {'plan_id': 'pending-'+str(ordinal), 'candidate_id': candidate['id'],
                'original_prediction': forecast(c)}
        ledger.put('plan', plan)
        ledger.put('forecast', {'plan_id': plan['plan_id'], 'issued_at': 100.})
        MonitorCronController(ledger).attach(plan, 'job-'+str(ordinal), DEFAULT_POLICY)
    result = binding.continuation_for_action(parent, 'test-run:parent:1')['evidence']
    assert len(result['pending_allocations']) == 3
    values = result['pending_by_obligation']
    assert set(values) == {'original-work', 'second-work'}
    individual = result['pending_allocations'][0]['valuation']['expected_continuation_credit']
    assert individual > 0
    assert values['original-work'] == pytest.approx(individual)
    assert result['expected_continuation_credit'] == pytest.approx(sum(values.values()))
    assert ledger.credit_view()['credit'] == 0


def test_wait_mode_advises_actions_and_preserves_full_catalog(tmp_path):
    from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
    from gene_annotation_episode.runtime import Workflow, controller_from_settings
    from gene_annotation_episode.tools import ToolRegistry
    with Store(tmp_path/'store') as store:
        manifest = tmp_path/'inputs.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
        store.create_problem(manifest_path=manifest)
        c = {**commission(), 'monitoring': dict(DEFAULT_POLICY)}
        factory = ExecutionServiceFactory(resources(), {}, 1., 1., .01,
                                          hpc_commissions={'commission': c})
        workflow = Workflow(store, ToolRegistry(store), None, tmp_path/'episode', 'test-run',
            controller_factory=controller_from_settings({'controller': {'cost': .001}}),
            project_credit=lambda *_: 0.,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1', root_role='hpc')
        episode = workflow.build('hpc', 'root', 'Original work', {'subject_refs': []},
                                 episode_assignment={'commission_id': 'commission'})
        binding = workflow.specialist(episode.source)
        parent = workflow.binding_context(episode.source)
        ledger = binding.state(parent)
        ledger.put('monitor_controller', {'plan_id': 'original-plan'})
        ledger.put('monitor', {'plan_id': 'original-plan'})
        diagnostic = {'activity_mode': 'wait', 'active_next_gain': {'value': 0.},
                      'pending_expected_credit': 3.}
        def save_mode(mode):
            diagnostic['activity_mode'] = mode
            store.db.execute('INSERT OR REPLACE INTO runtime_observations '
                '(run_id,episode_id,unit_index,observation) VALUES (?,?,?,?)',
                ('test-run', parent.episode_id, 0, json.dumps({'step': {'estimate': {'diagnostics': diagnostic}}})))
        save_mode('wait')
        branches = workflow.action_schema(episode.source)['properties']['selection']['anyOf']
        assert 'hpc.plan' in [branch['properties']['tool']['const'] for branch in branches
                             if 'tool' in branch['properties']]
        assert binding.activity_advice(parent)['suggested_tool'] == 'hpc.monitor.wait'
        assert 'hpc.plan' in {row['name'] for row in binding.catalog(parent)}
        save_mode('collect')
        branches = workflow.action_schema(episode.source)['properties']['selection']['anyOf']
        assert 'hpc.plan' in [branch['properties']['tool']['const'] for branch in branches
                             if 'tool' in branch['properties']]
        assert binding.activity_advice(parent)['suggested_tool'] == 'hpc.results'
        save_mode('active_yield_unknown')
        assert binding.activity_advice(parent) is None
