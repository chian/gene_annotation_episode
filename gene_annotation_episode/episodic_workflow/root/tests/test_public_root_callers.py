"""Public dispatch and actual Root case construction, without workflow work."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

from gene_annotation_episode import cli, case_execution as case
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root import tool_configuration, run_execution
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.tests.public_caller_checks import (
    PARAMETERS, create_workspace, forbidden, prepare_case,
)


@pytest.fixture
def cli_ports(tmp_path, monkeypatch):
    workspace = tmp_path / 'cli-store'
    target, _ = create_workspace(workspace)
    events = []
    tools = SimpleNamespace(catalog=lambda: {'controlled': True}, execute=forbidden)
    def build(store, config, *, run_directory):
        assert type(store) is Store and store.path == workspace.resolve()
        assert store.targets()[0]['id'] == target
        events.append(('build', deepcopy(config), Path(run_directory)))
        return tools
    monkeypatch.setattr(tool_configuration, 'build_tools', build)
    monkeypatch.setattr(run_execution, 'run_workflow', forbidden)
    return SimpleNamespace(workspace=workspace, target=target, tools=tools, events=events)


def test_cli_capabilities_uses_root_supplier_and_owned_directory(cli_ports, capsys):
    p = cli_ports
    assert cli.main(['capabilities', '--workspace', str(p.workspace)]) == 0
    assert json.loads(capsys.readouterr().out) == {'controlled': True}
    _, config, directory = p.events.pop()
    assert config is None and directory.parent == p.workspace / 'runs'
    assert re.fullmatch(r'\d{8}T\d{6}\.\d{6}Z', directory.name)
    assert not p.events


@pytest.mark.parametrize('status,code', [('completed', 0), ('partial', 0), ('failed', 1)])
def test_cli_tool_preserves_arguments_scope_and_status(cli_ports, capsys, status, code):
    p = cli_ports
    def execute(name, arguments, *, scope):
        p.events.append(('execute', name, arguments, scope))
        return {'status': status, 'marker': 'actual-dispatch'}
    p.tools.execute = execute
    scope = {'subject_refs': [p.target]}
    assert cli.main(['tool', '--workspace', str(p.workspace), 'fixture.operation',
        '--args', '{"value":7}', '--scope', json.dumps(scope)]) == code
    assert json.loads(capsys.readouterr().out) == {'status': status, 'marker': 'actual-dispatch'}
    assert p.events[0][0] == 'build'
    assert p.events[1:] == [('execute', 'fixture.operation', {'value': 7}, scope)]


@pytest.mark.parametrize('resume', [False, True], ids=['explicit-fresh', 'implicit-saved'])
def test_cli_run_forwards_real_directory_and_caller_options(cli_ports, tmp_path, monkeypatch, capsys, resume):
    p = cli_ports
    run = tmp_path / 'selected-run'
    config = tmp_path / 'caller.toml'
    config.write_text('[credit]\nkind="controlled-caller-policy"\n')
    if resume:
        run.mkdir()
        (run / 'run.json').write_text(json.dumps({'run_id': 'saved-public-run'}))
        with Store(p.workspace) as store:
            journal = Journal(store, 'saved-public-run')
            with store.transaction():
                journal.save('runtime_runs', {'settings': json.dumps({'directory': str(run)}),
                    'state': 'held', 'started_at': '2026-11-13T00:00:00Z',
                    'updated_at': '2026-11-13T00:00:00Z'})
    async def workflow(store, tools, **options):
        assert type(store) is Store and tools is p.tools
        p.events.append(('workflow', options))
        return {'status': 'controlled-workflow-boundary'}
    monkeypatch.setattr(run_execution, 'run_workflow', workflow)
    argv = ['run', '--workspace', str(p.workspace), '--config', str(config), '--goal', 'caller goal']
    argv += ['--resume'] if resume else ['--run-dir', str(run)]
    assert cli.main(argv) == 0
    assert json.loads(capsys.readouterr().out) == {'status': 'controlled-workflow-boundary'}
    assert p.events[0] == ('build', {'credit': {'kind': 'controlled-caller-policy'}}, run)
    assert p.events[1:] == [('workflow', {'provider_config': {'credit': {'kind': 'controlled-caller-policy'}},
        'run_dir': run, 'resume': resume, 'goal': 'caller goal',
        'credit_policy': {'kind': 'controlled-caller-policy'}})]


@pytest.mark.parametrize('interrupt,code', [(False, 1), (True, 130)], ids=['error', 'interrupt'])
def test_cli_run_preserves_failure_boundary(cli_ports, tmp_path, monkeypatch, capsys, interrupt, code):
    p = cli_ports
    error = KeyboardInterrupt() if interrupt else ValueError('controlled-workflow-failure')
    async def workflow(*args, **kwargs):
        raise error
    monkeypatch.setattr(run_execution, 'run_workflow', workflow)
    assert cli.main(['run', '--workspace', str(p.workspace), '--run-dir', str(tmp_path / 'run')]) == code
    value = json.loads(capsys.readouterr().out)
    if interrupt:
        assert value == {'status': 'externally_interrupted', 'scientific_completion': 'not_established'}
    else:
        assert value == {'status': 'operational_failure', 'error_type': 'ValueError',
            'detail': 'controlled-workflow-failure'}
    assert len(p.events) == 1 and p.events[0][0] == 'build'


def test_cli_keeps_combined_genome_unavailable_before_supplier(cli_ports, tmp_path, capsys):
    config = tmp_path / 'combined.toml'
    config.write_text('[genome_investigation]\nversion="combined_genome_investigation_v2"\n'
        '[genome_investigation.root]\n[genome_investigation.services]\nscientific_yield_bindings={}\n')
    assert cli.main(['capabilities', '--workspace', str(cli_ports.workspace), '--config', str(config)]) == 1
    assert json.loads(capsys.readouterr().out)['detail'] == 'combined_genome_private_tool_bindings_unavailable'
    assert cli_ports.events == []


def assert_actual_bindings(options):
    from gene_annotation_episode.episodic_workflow.root.library.homology_episode_family import HomologyEpisodes
    from gene_annotation_episode.episodic_workflow.root.homology_jobs import HomologyJobs
    from gene_annotation_episode.episodic_workflow.root.execution_recording import HomologyStatistics
    from gene_annotation_episode.episodic_workflow.root.execution_expectations import ExecutionExpectations
    from gene_annotation_episode.episodic_workflow.root.native_timing_information import NativeTimingInformation
    from gene_annotation_episode.episodic_workflow.root.resource_estimation import ResourceToolEstimator
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    from gene_annotation_episode.episodic_workflow.root.homology_job_submission.episode import HomologySubmissionEpisodes
    from gene_annotation_episode.episodic_workflow.root.homology_job_monitoring.episode import HomologyMonitoringEpisodes
    from gene_annotation_episode.episodic_workflow.root.homology_result_acquisition.episode import HomologyAcquisitionEpisodes
    family = options['job_episodes']
    assert type(family) is HomologyEpisodes and type(family.jobs) is HomologyJobs
    assert type(family.parser_policy) is LocalJobPolicy and type(family.statistics) is HomologyStatistics
    assert family.roles == ('job_launch', 'job_monitor', 'job_results')
    expected = (HomologySubmissionEpisodes, HomologyMonitoringEpisodes, HomologyAcquisitionEpisodes)
    for role, cls in zip(family.roles, expected):
        actual = family.implementation_for(role)
        assert type(actual) is cls and actual.jobs is family.jobs
        assert actual._custody is family._custody
        assert family.implementation_for_path((('annotation', 'root'), (role, 'child'))) is actual
        nested = family.implementation_for_path((('annotation', 'root'), ('improvement', 'again'), (role, 'child')))
        assert type(nested) is not cls and nested._custody is family._custody
    assert type(options['execution_expectations']) is ExecutionExpectations
    assert type(options['native_timing_information']) is NativeTimingInformation
    assert type(options['resource_estimator']) is ResourceToolEstimator
    assert options['project_child_credit'] is None
    assert family.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    return family.as_record()


def test_case_preparation_constructs_real_private_family_and_restores_saved_policy(tmp_path):
    p = prepare_case(tmp_path)
    assert case.prepare_case_run(p.case_dir, p.run, p.settings, focus='Controlled public construction.') == p.manifest
    with Store(p.workspace) as store:
        assert store.get(p.manifest['context_source_ref'])['provider'] == 'caller.fixed_gene_evidence_index'
        with case.prepared_case_bindings(store, p.run, policy_file=p.policy, parameters=PARAMETERS, resume=False) as (manifest, options):
            assert manifest == p.manifest
            first = assert_actual_bindings(options)
            initial = (p.run / 'policy-binding.json').read_bytes()
        with case.prepared_case_bindings(store, p.run, resume=True) as (_, options):
            assert assert_actual_bindings(options) == first
        assert (p.run / 'policy-binding.json').read_bytes() == initial
        with pytest.raises(ValueError, match='resume_cannot_replace_policy_parameters'):
            with case.prepared_case_bindings(store, p.run, parameters={'different': True}, resume=True):
                pytest.fail('different saved policy parameters admitted')
    assert not (p.run / 'run.json').exists()


def test_case_run_forwards_constructed_types_and_directory_without_dispatch(tmp_path, monkeypatch):
    p = prepare_case(tmp_path)
    marker = object()
    events = []
    def build(store, settings, *, run_directory):
        assert type(store) is Store and store.path == p.workspace.resolve()
        assert settings == p.manifest['configuration'] and run_directory == p.run
        events.append('build_tools')
        return marker
    async def workflow(store, tools, **options):
        assert tools is marker and type(store) is Store
        assert_actual_bindings(options)
        assert options['run_dir'] == p.run and options['resume'] is False
        assert options['goal'] == p.manifest['goal'] and options['decision_protocol'] is case._DEFAULT_DECISION_PROTOCOL
        assert options['provider'] is forbidden
        assert options['provider_config'] == {'models': p.manifest['configuration']['models'],
            'restoration': p.manifest['configuration']['restoration']}
        events.append('workflow')
        return {'status': 'controlled-case-workflow-boundary'}
    monkeypatch.setattr(case, 'build_tools', build)
    monkeypatch.setattr(case, 'run_workflow', workflow)
    assert asyncio.run(case.run_prepared_case(p.run, policy_file=p.policy, parameters=PARAMETERS,
        provider=forbidden)) == {'status': 'controlled-case-workflow-boundary'}
    assert events == ['build_tools', 'workflow']
    assert not (p.run / 'run.json').exists()
