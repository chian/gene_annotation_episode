"""Caller setup through the public runtime and one-child reconstruction.

Transport entry is intercepted; these checks start no model or native job.
The case policy and units are explicit engineering fixtures.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json
from types import SimpleNamespace

import pytest

from method_loop import EpisodeGoal
from method_loop.durable import DurableExecutionError, DurableExecutionStore, content_digest
from gene_annotation_episode.case_execution import prepare_case_run, prepared_case_bindings, run_prepared_case
from gene_annotation_episode.episode_application_services import (
    EpisodeApplicationServices, job_progress_binding, service_binding)
from gene_annotation_episode.episode_monitoring import MonitorEpisodes, read_progress
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.independent_execution import make_runtime_binding, open_commission
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import Workflow, WorkflowError, TypedReportContract, assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_case_execution import PARAMETERS, POLICY, prepared
from test_homology_episode_runtime import Provider
from test_runtime import obj


class BeforeBuild(Exception):
    pass


class BeforeTransport(Exception):
    pass


def forbidden(*args, **kwargs):
    raise AssertionError('setup must not execute work')


class Reader:
    scope = observe = direct_dependencies = forbidden

    def __init__(self, window=7):
        self.window = window

    def as_record(self):
        return {'version': 'fixture_job_reader_v1', 'window': self.window}


class Setup:
    def __init__(self):
        self.calls, self.window = [], 7

    def __call__(self, store, *, run_id, directory, job_episodes, resource_estimator):
        self.calls.append((store, run_id, directory, job_episodes, resource_estimator))
        projector = ProgressInformationCredit(SimpleNamespace(
            read_progress=partial(read_progress, store, run_id)), information_unit=2)
        return EpisodeApplicationServices([MonitorEpisodes(None).as_record()],
            {'monitor': {'definition': projector.as_record(), 'project': projector}}, Reader(self.window))


def save_before_build(store, directory, setup, monkeypatch, *, resume=False, definition=None, **options):
    def stop(workflow, *args, **kwargs):
        assert workflow.progress_receipt_order == 'received_progress_order_v1'
        assert workflow.episode_application_services_binding == service_binding(setup, definition or {'fixture': True})
        assert workflow.progress_provider.job_provider.as_record() == Reader(setup.window).as_record()
        raise BeforeBuild
    with monkeypatch.context() as patched:
        patched.setattr(Workflow, 'build', stop)
        with pytest.raises(BeforeBuild):
            asyncio.run(run_workflow(store, build_tools(store), provider=Provider([]),
                run_dir=directory, resume=resume, episode_service_factory=setup,
                episode_service_binding=definition or {'fixture': True}, **options))
    return json.loads((directory/'run.json').read_text())


def test_setup_uses_original_run_identity_and_persists_actual_outputs_before_root(tmp_path, monkeypatch):
    setup, directory = Setup(), tmp_path/'run'
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        saved = save_before_build(store, directory, setup, monkeypatch)
        assert len(setup.calls) == 1
        assert setup.calls[0] == (store, saved['run_id'], directory, None, None)
        assert saved['episode_application_services'] == service_binding(setup, {'fixture': True})
        assert saved['episode_job_progress_provider'] == Reader().as_record()
        assert saved['episode_role_credit_bindings']['monitor']['definition']['information_unit'] == 2
        assert saved['episode_progress_receipts'] == {'version': 'received_progress_order_v1'}
        assert save_before_build(store, directory, setup, monkeypatch, resume=True) == saved
        assert len(setup.calls) == 2 and setup.calls[1][1] == saved['run_id']
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 0


def test_resume_rejects_changed_factory_definition_or_generated_job_reader(tmp_path, monkeypatch):
    setup, directory = Setup(), tmp_path/'run'
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        saved = save_before_build(store, directory, setup, monkeypatch)
        with pytest.raises(WorkflowError, match='original_episode_application_services'):
            asyncio.run(run_workflow(store, build_tools(store), provider=Provider([]),
                run_dir=directory, resume=True, episode_service_factory=setup,
                episode_service_binding={'fixture': 'changed'}))
        assert len(setup.calls) == 1
        setup.window = 9
        with pytest.raises(WorkflowError, match='original_episode_job_progress_provider'):
            asyncio.run(run_workflow(store, build_tools(store), provider=Provider([]),
                run_dir=directory, resume=True, episode_service_factory=setup,
                episode_service_binding={'fixture': True}))
        assert json.loads((directory/'run.json').read_text()) == saved


def test_interrupted_original_setup_can_finish_unpublished_composition_on_resume(tmp_path, monkeypatch):
    class InterruptedSetup(Setup):
        interrupted = True

        def __call__(self, *args, **kwargs):
            if self.interrupted:
                raise BeforeBuild
            return super().__call__(*args, **kwargs)

    setup, directory = InterruptedSetup(), tmp_path/'run'
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        with pytest.raises(BeforeBuild):
            asyncio.run(run_workflow(store, build_tools(store), provider=Provider([]),
                run_dir=directory, episode_service_factory=setup,
                episode_service_binding={'fixture': True}))
        original = json.loads((directory/'run.json').read_text())
        assert 'episode_bindings' not in original
        assert original['episode_application_services'] == service_binding(setup, {'fixture': True})
        setup.interrupted = False
        saved = save_before_build(store, directory, setup, monkeypatch, resume=True)
        assert saved['run_id'] == original['run_id']
        assert saved['episode_job_progress_provider'] == Reader().as_record()
        assert len(setup.calls) == 1
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 0


@pytest.mark.parametrize('direct', ['episode_binding_factories', 'episode_binding_descriptors',
                                  'role_credit_bindings', 'job_progress_provider'])
def test_factory_and_direct_specialist_inputs_are_exclusive_before_setup(tmp_path, direct):
    setup = Setup()
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        with pytest.raises(ValueError, match='direct_services_are_exclusive'):
            asyncio.run(run_workflow(store, build_tools(store), provider=Provider([]), run_dir=tmp_path/'run',
                episode_service_factory=setup, episode_service_binding={'fixture': True}, **{direct: []}))
        assert setup.calls == []


def test_factory_output_type_and_reader_definition_are_required_without_observing(tmp_path):
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        with pytest.raises(TypeError, match='must_return_EpisodeApplicationServices'):
            asyncio.run(run_workflow(store, build_tools(store), provider=Provider([]),
                run_dir=tmp_path/'run', episode_service_factory=lambda *a, **k: {},
                episode_service_binding={'fixture': True}))
    assert job_progress_binding(Reader()) == Reader().as_record()
    with pytest.raises(ValueError, match='reconstructible_job_progress_provider_required'):
        job_progress_binding(object())


def test_standard_worker_does_not_infer_a_caller_setup(tmp_path, monkeypatch):
    setup, directory = Setup(), tmp_path/'run'
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        save_before_build(store, directory, setup, monkeypatch)
        with pytest.raises(DurableExecutionError) as error:
            make_runtime_binding(store, directory)
        assert error.value.failure['code'] == 'unavailable_binding'
        assert error.value.failure['affected_refs'] == ['episode_application_services']


CASE_SETUP = '''
from dataclasses import replace
from functools import partial
from types import SimpleNamespace
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
from gene_annotation_episode.episode_monitoring import MonitorEpisodes, read_progress
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.homology_progress import HomologyProgressProvider

_original_create_policy = create_policy

def specialist_setup(store, *, run_id, directory, job_episodes, resource_estimator):
    projector = ProgressInformationCredit(SimpleNamespace(
        read_progress=partial(read_progress, store, run_id)), information_unit=3)
    return EpisodeApplicationServices([MonitorEpisodes(None).as_record()],
        {'monitor': {'definition': projector.as_record(), 'project': projector}},
        HomologyProgressProvider(store, job_episodes.jobs, run_id=run_id,
            log_window_bytes=64, log_roles=('native_text',)))

def create_policy(parameters):
    return replace(_original_create_policy(parameters),
        episode_service_factory=specialist_setup,
        episode_service_binding={'version':'fixture_case_specialists_v1'})
'''


def test_fixed_case_restores_identical_services_in_one_child_before_transport(tmp_path, monkeypatch):
    case, configuration, policy = prepared(tmp_path, with_protein=False)
    policy.write_text(POLICY + CASE_SETUP)
    directory = tmp_path/'run'
    manifest = prepare_case_run(case, directory, configuration)
    entered = []

    async def stop_transport(provider):
        entered.append(provider)
        raise BeforeTransport

    monkeypatch.setattr(ModelConnection, '__aenter__', stop_transport)
    with pytest.raises(BeforeTransport):
        asyncio.run(run_prepared_case(directory, policy_file=policy, parameters=PARAMETERS))
    saved = json.loads((directory/'run.json').read_text())
    assert saved['episode_execution']['version'] == 'durable_episode_application_v1'
    assert saved['episode_job_progress_provider']['configuration']['log_window_bytes'] == 64
    assert saved['episode_role_credit_bindings']['monitor']['definition']['information_unit'] == 3
    assert json.loads((directory/'policy-binding.json').read_text())[
        'episode_application_services'] == saved['episode_application_services']
    settings = {key: value for key, value in saved.items() if key != 'run_id'}

    with Store(case/'workspace') as store, prepared_case_bindings(store, directory) as (_, options):
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 0
        workflow = assemble_workflow(store, build_tools(store, manifest['configuration']), Provider([]),
            directory, saved['run_id'], settings,
            **{key: value for key, value in options.items() if key != 'binding_definitions'})
        scope = store.validate_scope({'subject_refs': [manifest['target_ref']]})
        root = workflow.build('annotation', 'root', settings['goal'], scope)
        schema = obj({'finding': {'type': 'string', 'enum': ['unknown']}})
        contract = TypedReportContract('Return the bounded fixture state', schema,
            workflow.resolver(scope, grain='improvement'))
        child = workflow.build('improvement', 'original_child', 'One original fixture child', scope,
            parent=root.goal, parent_path=root.source.path, contract=contract, initial={'finding': 'unknown'})
        binding = make_runtime_binding(store, directory, kind='fixed_case')
        spec = {'version': 'episode_commission_v1', 'handle': 'episode:setup_fixture_child',
            'operation_key': saved['run_id']+':setup_fixture_child', 'run_id': saved['run_id'],
            'parent': {'episode_id': root.source.episode_id, 'goal_id': root.goal.goal_id,
                'path': [list(item) for item in root.source.path]},
            'child': {'episode_id': child.source.episode_id, 'role': 'improvement', 'key': child.key,
                'path': [list(item) for item in child.source.path],
                'request': child.request.as_record(), 'scope': scope},
            'input_versions': [{'reference': manifest['target_ref'], 'version': None,
                'content_sha256': content_digest(store.get(manifest['target_ref']))}],
            'runtime_binding': binding, 'constraints': {'fixture': True},
            'resource_selection': None, 'expectation_snapshot_refs': []}
        assert workflow.episode_application_services_binding == saved['episode_application_services']
        assert workflow.episode_job_progress_provider_binding == saved['episode_job_progress_provider']
        assert options['job_episodes'].jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    DurableExecutionStore(directory/'episode-execution').commission(spec)

    async def reconstruct():
        async with open_commission(spec):
            pytest.fail('transport fixture must interrupt before episode execution')

    with pytest.raises(BeforeTransport):
        asyncio.run(reconstruct())
    assert len(entered) == 2
    with Store(case/'workspace') as store:
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 2
        for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0

