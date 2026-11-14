"""Caller service setup through the public runtime without executing work."""
import asyncio
from functools import partial
import json
from types import SimpleNamespace

import pytest

from method_loop.durable import DurableExecutionError
from gene_annotation_episode.episodic_workflow.root.episode_application_services import (
    EpisodeApplicationServices, job_progress_binding, service_binding)
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.episodic_workflow.root.progress_observations import read_progress
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.episodic_workflow.root.commissioned_reopening import make_runtime_binding
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
from gene_annotation_episode.episodic_workflow.root.run_execution import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_configuration import build_tools
from test_runtime import ScriptedProvider


class BeforeBuild(Exception):
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
            asyncio.run(run_workflow(store, build_tools(store), provider=ScriptedProvider([]),
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
            asyncio.run(run_workflow(store, build_tools(store), provider=ScriptedProvider([]),
                run_dir=directory, resume=True, episode_service_factory=setup,
                episode_service_binding={'fixture': 'changed'}))
        assert len(setup.calls) == 1
        setup.window = 9
        with pytest.raises(WorkflowError, match='original_episode_job_progress_provider'):
            asyncio.run(run_workflow(store, build_tools(store), provider=ScriptedProvider([]),
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
            asyncio.run(run_workflow(store, build_tools(store), provider=ScriptedProvider([]),
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
            asyncio.run(run_workflow(store, build_tools(store), provider=ScriptedProvider([]), run_dir=tmp_path/'run',
                episode_service_factory=setup, episode_service_binding={'fixture': True}, **{direct: []}))
        assert setup.calls == []


def test_factory_output_type_and_reader_definition_are_required_without_observing(tmp_path):
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        with pytest.raises(TypeError, match='must_return_EpisodeApplicationServices'):
            asyncio.run(run_workflow(store, build_tools(store), provider=ScriptedProvider([]),
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
