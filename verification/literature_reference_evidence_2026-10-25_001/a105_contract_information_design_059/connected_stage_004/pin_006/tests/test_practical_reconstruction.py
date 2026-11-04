"""Practical caller reconstruction freezes configuration without doing work."""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import independent_execution as reconstruction
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_service_setup import PracticalServiceFactory
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools


class BeforeModel(Exception):
    pass


def test_factory_keeps_caller_configuration_immutable(tmp_path):
    resources = {'local': {'kind': 'local', 'workspace': str(tmp_path), 'policy': {
        'memory_bytes': 123, 'scratch_bytes': 456, 'wall_seconds': None}}}
    factory = PracticalServiceFactory(resources, {})
    original = factory.as_record()
    resources['local']['workspace'] = '/changed'
    assert factory.as_record() == original
    with pytest.raises(TypeError):
        factory.resources['local']['workspace'] = '/changed'
    binding = PracticalResourceEpisodes(None, directory=tmp_path,
        resources=factory.resources, initial_information=factory.initial_information)
    information = binding.initial_decision_context(None)['practical_resource_capabilities']
    assert information == [{'resource_kind': 'local', 'workspace': str(tmp_path),
        'policy': original['resources']['local']['policy'], 'inventory_snapshot': None}]


def test_configured_practical_services_reconstruct_without_discovery_or_commands(tmp_path, monkeypatch):
    directory = tmp_path/'run'
    resources = {'local': {'kind': 'local', 'workspace': str(tmp_path/'project'),
        'policy': {'memory_bytes': 128*1024**2, 'scratch_bytes': 16*1024**2, 'wall_seconds': None}}}
    factory = PracticalServiceFactory(resources, {})

    def forbidden(*args, **kwargs):
        pytest.fail('Reconstruction must not discover resources or execute an operation')

    monkeypatch.setattr(LocalPracticalOperations, 'initial_outcome', forbidden)
    monkeypatch.setattr(LocalPracticalOperations, 'execute', forbidden)

    async def inspect_before_model(connection):
        with Store(workspace) as reopened:
            binding = json.loads((directory/'episode-execution-binding.json').read_text())
            settings = json.loads(reopened.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
            options = reconstruction._standard_bindings(reopened, directory, settings)
            reconstruction._check_bindings(options, settings)
            assert options['episode_service_factory'].as_record() == factory.as_record()
            assert binding == reconstruction.make_runtime_binding(reopened, directory)
            restored = assemble_workflow(reopened, build_tools(reopened), object(), directory,
                json.loads((directory/'run.json').read_text())['run_id'], settings,
                **{key: value for key, value in options.items() if key != 'binding_definitions'})
            assert restored.episode_bindings.as_record() == settings['episode_bindings']
            assert set(restored.episode_bindings.roles) == {'launch_local'}
            assert reopened.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 0
            assert not (directory/'practical-execution').exists()
            assert not (tmp_path/'project').exists()
            altered = deepcopy(settings)
            altered['episode_application_services']['factory'] = 'unknown.Factory'
            with pytest.raises(Exception) as error:
                reconstruction._standard_bindings(reopened, directory, altered)
            assert error.value.failure['code'] == 'unavailable_binding'
        raise BeforeModel

    monkeypatch.setattr(ModelConnection, '__aenter__', inspect_before_model)
    workspace = tmp_path/'state'
    with Store(workspace) as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        with pytest.raises(BeforeModel):
            asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                episode_service_factory=factory, episode_service_binding=factory.as_record()))
