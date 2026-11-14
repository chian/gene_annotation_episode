"""Original publisher metadata over actual configured A106 private graph.

The immutable scientific request/source/operation remains the repository's
responsibility. These graph checks neither publish nor grade scientific evidence.
"""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from .private_analysis_exchange_fixtures import analysis_workflow, module

PARENTS = ('published_evidence_assessment', 'scientific_process/published_evidence_assessment')


def runtime_path(registry, home):
    parts = home.split('/')
    result = [('annotation', 'original-annotation')]
    for index in range(len(parts)):
        owner = registry.for_binding_path('/'.join(parts[:index+1]))
        result.append((owner.roles[0], 'original-invocation-'+str(index)))
    return tuple(result)


def initialize(store, registry, path):
    store.create_problem(raw_sequence='MAAA', molecule='protein')
    store.db.execute('CREATE TABLE runtime_runs(run_id TEXT, settings TEXT)')
    store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT, episode_id TEXT, path TEXT, request TEXT)')
    run = 'original-publisher-run'
    store.db.execute('INSERT INTO runtime_runs VALUES(?,?)',
        (run, json.dumps({'episode_bindings': registry.as_record()})))
    scope, assignment = store.validate_scope(), {'synthetic_identity_control': 'original'}
    request = {'message': {'scope': scope, 'episode_assignment': assignment}}
    identity = module('method_loop.identities').EpisodeRef(run, path)
    context = module('episode_bindings').BindingContext(run, identity.episode_id, path[-1][0],
        path, scope, assignment, request)
    store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
        (run, identity.episode_id, json.dumps(path), json.dumps(request)))
    scientific_request = {'run_id': run, 'episode_id': identity.episode_id,
        'role': context.role, 'scope': scope, 'assignment': assignment}
    return context, scientific_request


def test_actual_full_configured_graph_matches_every_selected_private_owner(analysis_workflow):
    _, workflow, _ = analysis_workflow
    registry = workflow.episode_bindings
    support = module('episode_binding_graph')
    graph = support.SavedBindingGraph(support.snapshot_graph(registry), expected_descriptors=registry.as_record())
    assert len(registry._bindings) == 27  # Actual fixture:14 literature+12 operational+scientific head; monitors not selected.
    for owner in registry._bindings:
        path = runtime_path(registry, owner.binding_path)
        assert graph.for_path(path).descriptor == owner.as_record()
        assert graph.for_child(path[:-1], path[-1][0]).descriptor == registry.for_child(path[:-1], path[-1][0]).as_record()
    with pytest.raises(LookupError, match='requires_parent'):
        graph.for_role('launch')


@pytest.mark.parametrize('parent', PARENTS)
@pytest.mark.parametrize('role,suffix', (
    ('launch', '/execution_job_submission'),
    ('launch_api', '/execution_job_submission/api_job_execution'),
    ('results', '/execution_result_acquisition'),
))
def test_configured_literature_analysis_edges_and_live_provider_lineage(analysis_workflow, parent, role, suffix):
    _, workflow, _ = analysis_workflow
    registry = workflow.episode_bindings
    support = module('episode_binding_graph')
    graph = support.SavedBindingGraph(support.snapshot_graph(registry), expected_descriptors=registry.as_record())
    path = runtime_path(registry, parent+suffix)
    actual = registry.for_path(path)
    assert actual.roles == (role,) and actual.binding_path == parent+suffix
    assert graph.for_path(path).descriptor == actual.as_record()
    assert graph.for_child(path[:-1], role).descriptor == actual.as_record()
    # Existing A106 provider traversal is independent of the five moved methods.
    assert registry.for_context_role('results', path=path).binding_path == parent+'/execution_result_acquisition'
    other = next(value for value in PARENTS if value != parent)
    assert graph.for_path(path).descriptor != registry.for_binding_path(other+suffix).as_record()


def test_original_child_publisher_reopens_without_live_registry(tmp_path, analysis_workflow):
    _, workflow, _ = analysis_workflow
    registry = workflow.episode_bindings
    support = module('library.literature_publisher_binding')
    home = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    path = runtime_path(registry, home)
    directory = tmp_path/'state'
    with module('state').Store(directory) as store:
        context, request = initialize(store, registry, path)
        changes = store.db.total_changes
        publisher = support.capture_publisher_binding(store, context.run_id, context, registry)
        descriptor = registry.for_path(path).as_record()
        assert descriptor != registry.for_path(path[:-1]).as_record()
        assert publisher['descriptor'] == descriptor
        assert store.db.total_changes == changes
        store.db.commit()
    with module('state').Store(directory) as store:
        store.db.execute('PRAGMA query_only=ON')
        changes = store.db.total_changes
        assert support.validate_publisher_binding(store, context.run_id, request, publisher, descriptor) == descriptor
        assert store.db.total_changes == changes


@pytest.mark.parametrize('mutation', ['sibling', 'path', 'assignment', 'scope', 'missing_episode', 'declared_none'])
def test_original_publisher_conflict_is_typed_invalid(tmp_path, analysis_workflow, mutation):
    _, workflow, _ = analysis_workflow
    registry = workflow.episode_bindings
    support = module('library.literature_publisher_binding')
    path = runtime_path(registry, PARENTS[1])
    with module('state').Store(tmp_path/'state') as store:
        context, request = initialize(store, registry, path)
        publisher = support.capture_publisher_binding(store, context.run_id, context, registry)
        descriptor = deepcopy(publisher['descriptor'])
        if mutation == 'sibling':
            sibling = registry.for_binding_path(PARENTS[0])
            publisher.update(binding_id=sibling.binding_path, descriptor=sibling.as_record())
            descriptor = sibling.as_record()
        elif mutation == 'path':
            publisher['path'][-1][1] = 'different-original-invocation'
        elif mutation in ('assignment', 'scope'):
            request[mutation] = {'changed_original_operand': True}
        elif mutation == 'missing_episode':
            store.db.execute('DELETE FROM runtime_episodes')
        else:
            publisher = descriptor = None
        with pytest.raises(module('domain').ContractError, match='scientific_publisher_'):
            support.validate_publisher_binding(store, context.run_id, request, publisher, descriptor)


def test_genuine_standalone_none_makes_no_owner_claim(tmp_path):
    support = module('library.literature_publisher_binding')
    with module('state').Store(tmp_path/'state') as store:
        assert support.capture_publisher_binding(store, 'standalone', None, None) is None
        assert support.validate_publisher_binding(store, 'standalone', {}, None, None) is None


def test_real_registry_required_and_unexpected_callback_preserved(tmp_path, analysis_workflow, monkeypatch):
    _, workflow, _ = analysis_workflow
    registry = workflow.episode_bindings
    support = module('library.literature_publisher_binding')
    with module('state').Store(tmp_path/'state') as store:
        context, _ = initialize(store, registry, runtime_path(registry, PARENTS[0]))
        with pytest.raises(module('domain').ContractError, match='registry_required'):
            support.capture_publisher_binding(store, context.run_id, context, SimpleNamespace())
        def broken(role):
            raise RuntimeError('original callback failure')
        monkeypatch.setattr(registry._bindings[0], 'child_roles', broken)
        with pytest.raises(RuntimeError, match='original callback failure'):
            support.capture_publisher_binding(store, context.run_id, context, registry)
