"""Actual private graph and immutable original publisher metadata controls.

These tests establish metadata custody only. Scientific repositories must still
validate their source, operation, complete extraction and numerical sheet.
"""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import pytest

from .test_private_binding_restoration import frozen_scientific_binding
from .test_private_literature_bindings import AXIS, HOMES


def module(name):
    return import_module(AXIS + '.' + name)


@pytest.fixture
def declared(tmp_path):
    scientific, _ = frozen_scientific_binding(tmp_path)
    bindings = [scientific, *[module(home + '.episode').LiteratureEpisode(SimpleNamespace()) for home in HOMES]]
    registry = module('episode_bindings').EpisodeBindingRegistry(bindings)
    paths = {}
    for home in HOMES:
        parts = home.split('.')
        path = [('annotation', 'original-annotation')]
        for index in range(len(parts)):
            binding = registry.for_binding_path('/'.join(parts[:index + 1]))
            path.append((binding.roles[0], 'original-' + str(index)))
        paths[home] = tuple(path)
    return registry, paths


def initialize(store, registry, path):
    store.create_problem(raw_sequence='MAAA', molecule='protein')
    store.db.execute('CREATE TABLE runtime_runs(run_id TEXT,settings TEXT)')
    store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT)')
    run = 'original-publisher-run'
    store.db.execute('INSERT INTO runtime_runs VALUES(?,?)', (run, json.dumps({'episode_bindings': [binding.as_record() for binding in registry._bindings]})))
    scope, assignment = store.validate_scope(), {'synthetic_identity_control': 'original'}
    request = {'message': {'scope': scope, 'episode_assignment': assignment}}
    ref = module('method_loop.identities').EpisodeRef(run, path)
    context = module('episode_bindings').BindingContext(run, ref.episode_id, path[-1][0], path, scope, assignment, request)
    store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)', (run, ref.episode_id, json.dumps(path), json.dumps(request)))
    original_request = {'run_id': run, 'episode_id': ref.episode_id, 'role': context.role, 'scope': scope, 'assignment': assignment}
    return context, original_request


@pytest.mark.parametrize('home', HOMES)
def test_saved_graph_matches_actual_parent_specific_binding(declared, home):
    registry, paths = declared
    graph = module('episode_binding_graph')
    saved = graph.SavedBindingGraph(graph.snapshot_graph(registry), expected_descriptors=[binding.as_record() for binding in registry._bindings])
    path = paths[home]
    assert saved.for_path(path).descriptor == registry.for_path(path).as_record()
    assert saved.for_child(path[:-1], path[-1][0]).descriptor == registry.for_child(path[:-1], path[-1][0]).as_record()
    with pytest.raises(LookupError, match='requires_parent'):
        saved.for_role('literature_page')


def test_saved_scientific_recursion_preserves_original_child_selection(declared):
    registry, _ = declared
    graph = module('episode_binding_graph')
    saved = graph.SavedBindingGraph(graph.snapshot_graph(registry), expected_descriptors=[binding.as_record() for binding in registry._bindings])
    path = (('annotation', 'root'), ('scientific_process', 'first'), ('scientific_process', 'recursive'))
    assert saved.for_path(path).descriptor == registry.for_path(path).as_record()
    assert saved.for_child(path, 'literature').descriptor == registry.for_child(path, 'literature').as_record()


def test_actual_original_publisher_survives_cold_parent_read(tmp_path, declared):
    registry, paths = declared
    home = next(home for home in HOMES if home.startswith('scientific_process.') and home.endswith('source_evidence_examination'))
    support = module('library.literature_publisher_binding')
    directory = tmp_path / 'state'
    with module('state').Store(directory) as store:
        context, request = initialize(store, registry, paths[home])
        before = store.db.total_changes
        publisher = support.capture_publisher_binding(store, context.run_id, context, registry)
        descriptor = registry.for_path(context.path).as_record()
        assert publisher['descriptor'] == descriptor
        assert registry.for_path(context.path[:-1]).as_record() != descriptor
        assert store.db.total_changes == before
        store.db.commit()
    # No live registry or binding constructor is supplied to the reopened reader.
    with module('state').Store(directory) as store:
        before = store.db.total_changes
        assert support.validate_publisher_binding(store, context.run_id, request, publisher, descriptor) == descriptor
        assert store.db.total_changes == before


@pytest.mark.parametrize('mutation', ['sibling', 'path', 'assignment', 'scope', 'children', 'roles', 'missing_episode', 'declared_none'])
def test_changed_original_owner_or_graph_is_typed_invalid(tmp_path, declared, mutation):
    registry, paths = declared
    home = next(home for home in HOMES if home.startswith('scientific_process.') and home.endswith('source_evidence_examination'))
    support = module('library.literature_publisher_binding')
    with module('state').Store(tmp_path / 'state') as store:
        context, request = initialize(store, registry, paths[home])
        publisher = support.capture_publisher_binding(store, context.run_id, context, registry)
        descriptor = deepcopy(publisher['descriptor'])
        if mutation == 'sibling':
            sibling = next(binding for binding in registry._bindings if binding.roles == registry.for_path(context.path).roles and binding.binding_path != descriptor['binding_id'])
            publisher['binding_id'] = sibling.binding_path
            publisher['descriptor'] = sibling.as_record()
            descriptor = sibling.as_record()
        elif mutation == 'path':
            publisher['path'][-1][1] = 'other-invocation'
        elif mutation in ('assignment', 'scope'):
            request[mutation] = {'changed_original_operand': True}
        elif mutation in ('children', 'roles'):
            node = next(row for row in publisher['graph']['bindings'] if row['binding_path'] == 'scientific_process')
            if mutation == 'children':
                node['children']['scientific_process'] = []
            else:
                node['roles'] = ['forged_role']
        elif mutation == 'missing_episode':
            store.db.execute('DELETE FROM runtime_episodes')
        else:
            publisher = descriptor = None
        before = store.db.total_changes
        with pytest.raises(module('domain').ContractError, match='scientific_publisher_'):
            support.validate_publisher_binding(store, context.run_id, request, publisher, descriptor)
        assert store.db.total_changes == before


def test_genuine_standalone_none_carries_no_owner_claim(tmp_path):
    support = module('library.literature_publisher_binding')
    with module('state').Store(tmp_path / 'state') as store:
        assert support.capture_publisher_binding(store, 'standalone', None, None) is None
        assert support.validate_publisher_binding(store, 'standalone', {}, None, None) is None


def test_capture_requires_actual_registry_and_preserves_unexpected_callback_error(tmp_path, declared, monkeypatch):
    registry, paths = declared
    support = module('library.literature_publisher_binding')
    with module('state').Store(tmp_path / 'state') as store:
        context, _ = initialize(store, registry, paths[HOMES[0]])
        with pytest.raises(module('domain').ContractError, match='registry_required'):
            support.capture_publisher_binding(store, context.run_id, context, SimpleNamespace())
        def broken(role):
            raise RuntimeError('actual binding callback failed')
        monkeypatch.setattr(registry._bindings[0], 'child_roles', broken)
        with pytest.raises(RuntimeError, match='actual binding callback failed'):
            support.capture_publisher_binding(store, context.run_id, context, registry)


