"""Actual native facts and shared runtime, with scripted decisions/controllers.

The scientific and operational projectors are the run policy's real projectors.
Fixture stopping only bounds this engineering check; no model science is claimed.
"""
import asyncio
from pathlib import Path

import pytest

from gene_annotation_episode.case_execution import _load_policy
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.investigation_policy import create_policy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, cancel
from gene_annotation_episode.runtime import run_workflow
from test_homology_episode_runtime import prepared, Provider, action, commission, wait_terminal
from test_runtime import FixtureController


def parameters(registry_ref):
    return {'scientific_progress': {'finding_unit': 1, 'initial_known_record_refs': [],
                'loss_preview_size': 4},
        'operational': {'registry_ref': registry_ref, 'handoff_unit': 1, 'acquired_record_unit': 1},
        'monitoring': {'information_unit': 1},
        'controller': {'cost': .001, 'window_size': 8, 'subsample_size': 4,
            'uncertainty_alpha': .05,
            'cost_by_role': {'improvement': .001, 'job_launch': .001,
                'job_monitor': .001, 'job_results': .001}}}


def test_operational_contributions_are_actual_job_facts_and_reacquisition_is_inherited(tmp_path):
    store, tools, query, scope, jobs, previous = prepared(tmp_path)
    policy = create_policy(parameters(jobs.config['registry_ref']))
    binding = HomologyEpisodes(jobs, parser_policy=previous.parser_policy,
        credit_projector=policy.project_job_credit, credit_binding=policy.job_credit_definition,
        monitoring_projector=policy.project_monitoring_credit,
        monitoring_binding=policy.monitoring_credit_definition)
    handoffs, reports, controllers = [], [], []

    def results(context):
        report = context['child_reports'][-1]
        assert report['local_credit'] == 1
        handoffs.append(report['job_handoff'])
        wait_terminal(jobs, handoffs[0]['job_ref'])
        return commission(binding, 'job_results', scope, handoff=handoffs[0])

    def second_page(context):
        result = context['last_local_outcome']['result']
        assert result['total'] == 2
        assert context['current_credit'] == 1
        return action('homology.extract', {'limit': 1, 'offset': 1, 'snapshot_ref': result['snapshot_ref']})

    def repeat_acquisition(context):
        report = context['child_reports'][-1]
        reports.append(report)
        assert report['local_credit'] == 2 and len(report['comparisons']) == 1
        return commission(binding, 'job_results', scope, handoff=handoffs[0])

    def inherited(context):
        assert context['current_credit'] == 2
        return action('homology.extract', {'limit': 10})

    def repeat_again(context):
        assert context['current_credit'] == 2
        return action('homology.extract', {'limit': 10,
            'snapshot_ref': context['last_local_outcome']['result']['snapshot_ref']})

    def use_result(context):
        report = context['child_reports'][-1]
        reports.append(report)
        assert report['local_credit'] == 2 and report['comparisons'] == []
        return action('fixture.inspect_returned', {'observation_ref': reports[0]['comparisons'][0]})

    def controller(path, initial):
        count = {'annotation': 4, 'job_launch': 5, 'job_results': 2}[path[-1][0]]
        value = FixtureController(str(path), initial, count)
        controllers.append((path[-1][0], value))
        return value

    provider = Provider([commission(binding, 'job_launch', scope, query_ref=query),
        action('homology.environment'), action('homology.configure'), action('homology.stage'),
        action('homology.submit'), action('homology.check_handoff'), results,
        action('homology.extract', {'limit': 1}), second_page, repeat_acquisition,
        inherited, repeat_again, use_result])
    try:
        summary = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path/'run',
            project_credit=policy.project_task_credit,
            project_child_credit=policy.project_scientific_child_credit,
            controller_factory=controller, job_episodes=binding,
            initial_known_record_refs=[]))
        assert summary['credit'] == 0 and summary['completed_actions'] == 3
        assert store.count('assessment') == store.count('annotation') == 0
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        local = [(role, value.scores) for role, value in controllers]
        assert local == [('annotation', [0, 0, 0]),
            ('job_launch', [0, 0, 0, 0, 1]), ('job_results', [1, 1]), ('job_results', [0, 0])]
        # An unrelated physical job or registry cannot inherit these facts.
        assignment = {'job_ref': 'unrelated', 'query_ref': query}
        for role in ('job_launch', 'job_results'):
            assert policy.project_job_credit(store, role=role, assignment=assignment,
                episode_id='unrelated', run_id='unrelated') == 0
        other = create_policy(parameters('unrelated_registry'))
        assignment['job_ref'] = handoffs[0]['job_ref']
        for role in ('job_launch', 'job_results'):
            assert other.project_job_credit(store, role=role, assignment=assignment,
                episode_id='unrelated', run_id='unrelated') == 0
    finally:
        for path in jobs.directory.glob('*/native.handle.json'):
            cancel(NativeJobHandle(path))
        jobs.close()
        store.close()


@pytest.mark.parametrize('child_mode', ['annotation_accounts', 'interpretation_accounts',
    'received_findings'])
def test_role_wide_child_credit_is_rejected(child_mode):
    config = parameters('registry_fixture')
    config['scientific_child'] = child_mode
    with pytest.raises(ValueError, match='role_wide_scientific_child_credit_policy_retired'):
        create_policy(config)


def test_policy_preserves_explicit_finding_and_controller_settings(tmp_path):
    from gene_annotation_episode import investigation_policy
    config = parameters('registry_fixture')
    config['scientific_progress'].update(finding_unit=7, loss_preview_size=5)
    policy, recorded = _load_policy(tmp_path, Path(investigation_policy.__file__), config, resume=False)
    assert policy.task_credit_definition['policy']['finding_unit'] == 7
    assert policy.scientific_child_credit_definition is None
    assert 'scientific_child_credit' not in recorded['definitions']
    controller = policy.controller_factory((('annotation', 'root'),), 9)
    assert controller.initial_credit == 9 and controller.cost == .001
    assert controller.settings.window_size == 8
    assert policy.monitoring_credit_definition['information_unit'] == 1
    restored, restored_record = _load_policy(tmp_path, None, None, resume=True)
    assert restored_record == recorded
    assert restored.task_credit_definition == policy.task_credit_definition
    assert restored.scientific_child_credit_definition == policy.scientific_child_credit_definition


@pytest.mark.parametrize('include_handoff_checks', [False, True])
def test_received_findings_policy_keeps_progress_annotation_and_time_channels_separate(tmp_path, include_handoff_checks):
    from gene_annotation_episode import investigation_policy
    config = parameters('registry_fixture')
    config['scientific_progress'] = {'finding_unit': 7, 'initial_known_record_refs': [], 'loss_preview_size': 5}
    if include_handoff_checks:
        config['monitoring']['include_handoff_checks'] = True
    policy, recorded = _load_policy(tmp_path, Path(investigation_policy.__file__), config, resume=False)
    assert policy.project_scientific_child_credit is None
    assert policy.task_credit_definition['policy']['finding_unit'] == 7
    assert policy.annotation_score_definition is None
    assert policy.monitoring_credit_definition['information_unit'] == 1
    assert policy.project_monitoring_credit.include_handoff_checks is include_handoff_checks
    assert policy.initial_known_record_refs == recorded['initial_known_record_refs'] == []
    restored, saved = _load_policy(tmp_path, None, None, resume=True)
    assert saved == recorded
    assert restored.task_credit_definition == policy.task_credit_definition
    assert restored.annotation_score_definition is None
    assert restored.monitoring_credit_definition == policy.monitoring_credit_definition
    assert restored.project_monitoring_credit.include_handoff_checks is include_handoff_checks


def test_caller_role_costs_survive_policy_reload_without_changing_raw_yield_history(tmp_path):
    from gene_annotation_episode import investigation_policy
    from gene_annotation_episode.episode_reports import closing_yield
    from types import SimpleNamespace

    config = parameters('registry_fixture')
    config['controller']['cost_by_role'].update(job_launch=.01, job_monitor=.02)
    policy, recorded = _load_policy(tmp_path, Path(investigation_policy.__file__), config, resume=False)
    restored, replay = _load_policy(tmp_path, None, None, resume=True)
    assert replay == recorded
    assert recorded['definitions']['controller']['cost_by_role'] == config['controller']['cost_by_role']
    histories = {}
    for role, expected in [('annotation', .001),
                           ('job_launch', .01), ('job_monitor', .02), ('job_results', .001)]:
        # Role follows the episode's actual path, regardless of nesting depth.
        path = ((role, 'root'),) if role == 'annotation' else (
            ('annotation', 'root'), (role, 'nested'))
        controllers = [binding.controller_factory(path, 3) for binding in (policy, restored)]
        for controller in controllers:
            assert controller.cost == expected and controller.initial_credit == 3
            for index, credit in enumerate([4, 4, 4]):
                controller.observe(str(index), credit)
            histories[role] = controller.state().history
            facts = closing_yield(SimpleNamespace(controller_state=controller.state(), units_consumed=3))
            assert facts['continuation_cost'] == expected
            assert facts['completed_actions'] == 3
        assert controllers[0].state() == controllers[1].state()
    assert all(history == (1, 0, 0) for history in histories.values())


def test_role_costs_are_frozen_against_input_and_report_definition_mutation():
    config = parameters('registry_fixture')
    config['controller']['cost_by_role'] = {'job_monitor': .02}
    policy = create_policy(config)
    config['controller']['cost_by_role']['job_monitor'] = 99
    policy.controller_definition['cost_by_role']['job_monitor'] = 77
    assert policy.controller_factory((('job_monitor', 'child'),), 0).cost == .02


@pytest.mark.parametrize('overrides', [None, [], {'unknown_role': .01},
    {'job_monitor': -1}, {'job_monitor': True}, {'job_monitor': float('nan')}])
def test_invalid_role_cost_configuration_is_rejected_before_a_run(overrides):
    config = parameters('registry_fixture')
    config['controller']['cost_by_role'] = overrides
    with pytest.raises((ValueError, TypeError)):
        create_policy(config)


def test_generic_child_cannot_borrow_the_available_finding_calculation():
    from types import SimpleNamespace
    from gene_annotation_episode.runtime import Workflow

    config = parameters('registry_fixture')
    config['controller']['cost_by_role']['improvement'] = .02
    policy = create_policy(config)
    path = (('annotation', 'root'), ('improvement', 'child'))
    with pytest.raises(ValueError, match='scientific_child_cutoff_requires_original_task'):
        policy.controller_factory(path, 0)
    workflow = SimpleNamespace(project_credit=policy.project_task_credit,
        project_child_credit=policy.project_scientific_child_credit,
        episode_bindings=SimpleNamespace(roles=()))
    context = SimpleNamespace(role='improvement', path=path)
    with pytest.raises(ValueError, match='scientific_task_credit_not_declared:improvement'):
        Workflow.scientific_projector_for_context(workflow, context)
