"""Explicit service setup and role port bindings without scientific work."""
import asyncio
import json

import pytest

from method_loop.durable import DurableExecutionError
from gene_annotation_episode.episodic_workflow.root.episode_application_services import EpisodeApplicationServices, service_binding
from gene_annotation_episode.independent_execution import _check_bindings
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow, WorkflowError, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import obj, ScriptedProvider


MODE = 'actual_tool_catalog_v1'
ROLES = ('scientific_process', 'literature', 'launch', 'monitor', 'results')


def forbidden(*args, **kwargs):
    raise AssertionError('No selected work, numerical observation or transport is allowed')


def test_service_input_protocol_keeps_legacy_record_and_requires_explicit_mode():
    expected = {'version': 'episode_application_services_v1',
        'factory': __name__+'.forbidden', 'definition': {'fixture': True}}
    assert service_binding(forbidden, {'fixture': True}) == expected
    assert service_binding(None, None) is None
    assert service_binding(forbidden, {'fixture': True}, inputs=MODE) == {
        **expected, 'version': 'episode_application_services_v2', 'inputs': MODE}
    for value in ('unknown', False, [], {}):
        with pytest.raises(ValueError, match='unsupported_episode_service_inputs'):
            service_binding(forbidden, {'fixture': True}, inputs=value)
    with pytest.raises(ValueError, match='requires_factory'):
        service_binding(None, None, inputs=MODE)


@pytest.mark.parametrize('mode', [None, MODE])
def test_factory_receives_the_same_actual_map_only_in_explicit_mode(tmp_path, mode):
    calls = []
    with Store(tmp_path/'workspace') as store:
        tools = ToolRegistry(store)
        original = tools.catalog()

        def setup(actual_store, **kwargs):
            assert actual_store is store
            calls.append(kwargs)
            assert set(kwargs) == {'run_id', 'directory', 'job_episodes', 'resource_estimator'} | (
                {'tool_catalog'} if mode else set())
            if mode:
                assert kwargs['tool_catalog'] == original
                assert kwargs['tool_catalog'] is not original
                kwargs['tool_catalog']['state.query']['description'] = 'changed borrowed JSON copy'
            return EpisodeApplicationServices([], {})

        Workflow(store, tools, object(), tmp_path/'run', 'port-fixture', forbidden, forbidden,
            episode_service_factory=setup, episode_service_binding={'fixture': True},
            episode_service_inputs=mode)
        assert len(calls) == 1 and tools.catalog() == original
        for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


@pytest.mark.parametrize('invalid', ['nonstring_key', 'record_object', 'nonfinite_value'])
def test_actual_catalog_rejects_unsupported_json_before_setup_publication(tmp_path, monkeypatch, invalid):
    class RecordObject:
        def as_record(self):
            return {'coerced': True}

    catalog = {'fixture.operation': {'input_schema': obj({}), 'description': 'Actual fixture contract'}}
    if invalid == 'nonstring_key':
        catalog = {7: catalog['fixture.operation']}
    else:
        catalog['fixture.operation']['configuration'] = (
            RecordObject() if invalid == 'record_object' else float('nan'))
    entered, published = [], tmp_path/'factory-publication.json'

    def setup(*args, **kwargs):
        entered.append(kwargs)
        published.write_text('This setup body must never run')
        return EpisodeApplicationServices([], {})

    with Store(tmp_path/'workspace') as store:
        tools = ToolRegistry(store)
        monkeypatch.setattr(tools, 'catalog', lambda: catalog)
        with pytest.raises((ValueError, TypeError)):
            Workflow(store, tools, object(), tmp_path/'run', 'invalid-catalog-fixture',
                forbidden, forbidden, episode_service_factory=setup,
                episode_service_binding={'fixture': True}, episode_service_inputs=MODE)
        assert entered == [] and not published.exists()
        for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


class BeforeRoot(Exception):
    pass


def test_run_persists_explicit_roles_and_rejects_changed_ports_before_provider_construction(tmp_path, monkeypatch):
    calls = []

    def setup(store, **kwargs):
        calls.append(kwargs)
        return EpisodeApplicationServices([], {})

    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='MKK', molecule='protein')
        tools = ToolRegistry(store)
        options = dict(episode_service_factory=setup, episode_service_binding={'fixture': True},
            episode_service_inputs=MODE, annotation_child_roles=(), run_dir=tmp_path/'run')
        with monkeypatch.context() as patched:
            patched.setattr(Workflow, 'build', lambda *a, **k: (_ for _ in ()).throw(BeforeRoot()))
            with pytest.raises(BeforeRoot):
                asyncio.run(run_workflow(store, tools, provider=ScriptedProvider([]), **options))
        saved = json.loads((tmp_path/'run'/'run.json').read_text())
        assert saved['annotation_child_roles'] == []
        assert saved['episode_application_services']['inputs'] == MODE
        assert calls[0]['tool_catalog'] == tools.catalog()
        monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.providers.ModelConnection', forbidden)
        for changed, message in [({'annotation_child_roles': None}, 'original_annotation_child_roles'),
                ({'annotation_child_roles': ('literature',)}, 'original_annotation_child_roles'),
                ({'episode_service_inputs': None}, 'original_episode_application_services')]:
            with pytest.raises(WorkflowError, match=message):
                asyncio.run(run_workflow(store, tools, resume=True, **{**options, **changed}))
        assert len(calls) == 1
        assert json.loads((tmp_path/'run'/'run.json').read_text()) == saved


def test_worker_rejects_changed_ports_before_any_executable_binding_lookup():
    setup = lambda **kwargs: None
    definition = {'fixture': True}
    options = {'episode_service_factory': setup, 'episode_service_binding': definition,
        'episode_service_inputs': MODE, 'annotation_child_roles': ROLES}
    settings = {'episode_application_services': service_binding(setup, definition, inputs=MODE),
        'annotation_child_roles': list(ROLES)}
    for changed, affected in [({'episode_service_inputs': None}, 'episode_application_services'),
            ({'annotation_child_roles': ('literature',)}, 'annotation_child_roles'),
            ({'annotation_child_roles': None}, 'annotation_child_roles')]:
        with pytest.raises(DurableExecutionError) as error:
            _check_bindings({**options, **changed}, settings)
        assert error.value.failure['code'] == 'identity_conflict'
        assert error.value.failure['affected_refs'] == [affected]
