"""Real saved application configuration; no episode or provider is started.

The fixture stops the public run entry point immediately before root building,
after its real settings and specialist descriptors have been persisted. Custom
projectors are deliberately unavailable fixture executables, never scientific
credit units or production continuation policies.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json

import pytest

from method_loop import Episode
from method_loop.durable import DurableExecutionError, DurableExecutionStore, content_digest

from gene_annotation_episode import independent_execution as independent
from gene_annotation_episode.default_scientific_binding import VERSION as DEFAULT_VERSION
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.native_timing_information import NativeTimingInformation
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools


def forbidden(*args, **kwargs):
    raise AssertionError('reconstruction capability must not execute work')


class UnusedProvider:
    complete = forbidden


class SavedBeforeRoot(Exception):
    pass


def persisted_run(tmp_path, monkeypatch, **options):
    workspace, directory = tmp_path/'workspace', tmp_path/'run'
    with Store(workspace) as store:
        target = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs'][0]
        with monkeypatch.context() as setup:
            def stop_before_build(*args, **kwargs):
                raise SavedBeforeRoot()
            setup.setattr(Workflow, 'build', stop_before_build)
            with pytest.raises(SavedBeforeRoot):
                asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                    provider=UnusedProvider(), initial_known_record_refs=[target], **options))
        saved = json.loads((directory/'run.json').read_text())
        registered = store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
                                     (saved['run_id'],)).fetchone()
        assert json.loads(registered[0]) == {key: value for key, value in saved.items() if key != 'run_id'}
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 0
    return workspace, directory, saved


def forbid_execution(monkeypatch):
    from gene_annotation_episode.homology_jobs import HomologyJobs
    for owner, names in (
            (ModelConnection, ('__init__', '__aenter__', 'complete')),
            (Episode, ('run_async',)), (Workflow, ('build',)),
            (YieldController, ('__init__', 'observe', 'state')),
            (ScientificFindingProgress, ('__call__',)), (AnnotationSupportScore, ('__call__',)),
            (DurableExecutionStore, ('commission', 'start', 'record_progress')),
            (HomologyJobs, ('order', 'configure', 'stage', 'submit', 'sample', 'check_handoff')),
            (Store, ('commit_reasoning',))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)


def test_standard_capability_restores_original_values_without_executing_them(tmp_path, monkeypatch):
    configuration = {'controller': {'cost': .017, 'window_size': 12,
        'subsample_size': 8, 'uncertainty_alpha': .13},
        'scientific_progress': {'finding_unit': 7, 'loss_preview_size': 3},
        'credit': {'scale': 137, 'epsilon': .4}}
    workspace, directory, saved = persisted_run(tmp_path, monkeypatch,
        provider_config=configuration, native_timing_information=NativeTimingInformation(3.5),
        resource_estimator=ResourceToolEstimator(),
        episode_binding_factories=(partial(LiteratureEpisodes, outcome_page_size=3),))
    original = deepcopy(saved)
    forbid_execution(monkeypatch)
    binding = independent.make_runtime_binding(workspace, directory)
    assert binding == {'factory_module': independent.FACTORY_MODULE,
        'factory_name': independent.FACTORY_NAME,
        'arguments': {'version': independent.VERSION, 'workspace': str(workspace),
            'run_directory': str(directory), 'kind': 'standard_default',
            'tool_configuration': {}, 'caller_binding_pins': {}},
        'implementation_sha256': independent.implementation_sha256(),
        'settings_sha256': content_digest({key: value for key, value in saved.items() if key != 'run_id'})}
    with Store(workspace) as store:
        _, settings = independent._settings(store, directory)
        options = independent._standard_bindings(store, directory, settings)
        independent._check_bindings(options, settings)
        assert options['project_credit'].as_record()['policy']['finding_unit'] == 7
        assert options['project_child_credit'].as_record()['loss_preview_size'] == 3
        assert options['project_annotation_score'].as_record()['policy']['scale'] == 137
        assert options['project_annotation_score'].as_record()['policy']['epsilon'] == .4
        assert options['native_timing_information'].information_unit == 3.5
        assert options['binding_definitions'] == saved['binding_definitions']
        for table in ('runtime_episodes', 'runtime_model_calls', 'runtime_actions', 'runtime_observations'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    assert json.loads((directory/'run.json').read_text()) == original
    assert not (directory/'providers').exists()


@pytest.mark.parametrize('custom', ['controller', 'scientific_child_credit', 'annotation_score',
                                   'same_name_child_definition'])
def test_default_root_does_not_advertise_unavailable_other_executables(tmp_path, monkeypatch, custom):
    if custom == 'same_name_child_definition':
        projector = ScientificFindingProgress(FindingProgressPolicy(19), 3)
        options = {'project_child_credit': projector,
            'binding_definitions': {'scientific_child_credit': projector.as_record()}}
    else:
        operand = {'controller': 'controller_factory',
            'scientific_child_credit': 'project_child_credit',
            'annotation_score': 'project_annotation_score'}[custom]
        options = {operand: forbidden, 'binding_definitions': {custom: {'version': 'fixture_custom_v1'}}}
    workspace, directory, saved = persisted_run(tmp_path, monkeypatch, **options)
    assert saved['binding_definitions']['credit']['default_entrypoint'] == DEFAULT_VERSION
    forbid_execution(monkeypatch)
    with pytest.raises(DurableExecutionError) as error:
        independent.make_runtime_binding(workspace, directory)
    assert error.value.failure['code'] == 'unavailable_binding'
    assert error.value.failure['affected_refs']
    assert not (directory/'providers').exists()


class CustomLiterature(LiteratureEpisodes):
    def as_record(self):
        return {**super().as_record(), 'binding_id': 'caller_custom_literature'}


@pytest.mark.parametrize('custom', ['specialist', 'monitor', 'extra_role'])
def test_custom_specialist_and_role_executables_are_not_inferred(tmp_path, monkeypatch, custom):
    if custom == 'specialist':
        options = {'episode_binding_factories': (CustomLiterature,)}
    else:
        options = {'episode_binding_descriptors': ([MonitorEpisodes(None, outcome_page_size=5).as_record()]
                    if custom == 'monitor' else []),
            'role_credit_bindings': {'monitor' if custom == 'monitor' else 'caller_extra_role': {
                'definition': {'version': 'fixture_custom_role_v1'}, 'project': forbidden}}}
    workspace, directory, _ = persisted_run(tmp_path, monkeypatch, **options)
    forbid_execution(monkeypatch)
    with pytest.raises(DurableExecutionError) as error:
        independent.make_runtime_binding(workspace, directory)
    assert error.value.failure['code'] == 'unavailable_binding'
    assert not (directory/'providers').exists()


def rewrite_saved_settings(workspace, directory, saved):
    """Explicit corruption/version fixture; both authoritative copies agree."""
    with Store(workspace) as store:
        settings = {key: value for key, value in saved.items() if key != 'run_id'}
        store.db.execute('UPDATE runtime_runs SET settings=? WHERE run_id=?',
                         (json.dumps(settings), saved['run_id']))
        store.db.commit()
    (directory/'run.json').write_text(json.dumps(saved))


@pytest.mark.parametrize('changed', ['controller_version', 'credit_version', 'annotation_version',
                                   'child_version', 'specialist_version', 'specialist_configuration'])
def test_changed_versions_and_specialist_configuration_fail_before_transport(tmp_path, monkeypatch, changed):
    workspace, directory, saved = persisted_run(tmp_path, monkeypatch)
    if changed == 'specialist_version':
        saved['episode_bindings'][0]['version'] = 'unavailable_saved_version'
    elif changed == 'specialist_configuration':
        saved['episode_bindings'][0]['configuration']['outcome_page_size'] = 0
    else:
        key = {'controller_version': 'controller', 'credit_version': 'credit',
            'annotation_version': 'annotation_score', 'child_version': 'scientific_child_credit'}[changed]
        saved['binding_versions'][key] = {'requirement': 'unavailable_saved_executable'}
    rewrite_saved_settings(workspace, directory, saved)
    forbid_execution(monkeypatch)
    with pytest.raises(DurableExecutionError) as error:
        independent.make_runtime_binding(workspace, directory)
    assert error.value.failure['code'] == ('unavailable_binding' if changed == 'specialist_configuration'
                                         else 'identity_conflict')
    assert not (directory/'providers').exists()


def test_legacy_standard_settings_without_specialists_preserve_their_empty_roster(tmp_path, monkeypatch):
    workspace, directory, saved = persisted_run(tmp_path, monkeypatch, episode_binding_factories=())
    del saved['episode_bindings']
    rewrite_saved_settings(workspace, directory, saved)
    forbid_execution(monkeypatch)
    binding = independent.make_runtime_binding(workspace, directory)
    assert binding['settings_sha256'] == content_digest({key: value for key, value in saved.items() if key != 'run_id'})
