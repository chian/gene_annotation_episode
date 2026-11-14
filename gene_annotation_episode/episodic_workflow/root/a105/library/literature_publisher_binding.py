"""Original scientific publisher identity from an authenticated saved receipt.

This helper neither interprets evidence nor grants reference or scoring credit.
The caller retains original source/artifact/operation authentication and all
scientific validators. Historical receipt versions do not call this interface.
"""
from copy import deepcopy
import json
from ..communication import plain
from gene_annotation_episode.domain import ContractError
from ..episode_binding_graph import SavedBindingGraph, snapshot_graph
from ..episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef


def _require(condition, code):
    if not condition:
        raise ContractError('scientific_publisher_' + code)


def _same(left, right):
    return json.dumps(plain(left), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) == json.dumps(plain(right), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _saved_graph(value, descriptors):
    try:
        return SavedBindingGraph(value, expected_descriptors=descriptors)
    except (ValueError, TypeError) as error:
        raise ContractError('scientific_publisher_graph_invalid') from error


def _select(graph, path):
    try:
        return graph.for_path(path)
    except (ValueError, LookupError) as error:
        raise ContractError('scientific_publisher_graph_owner_invalid') from error


def _settings(store, run_id):
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_runs'").fetchone() is None:
        return None
    row = store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?', (run_id,)).fetchone()
    if row is None:
        return None
    result = json.loads(row['settings'])
    _require(type(result) is dict and type(result.get('episode_bindings')) is list, 'saved_bindings_required')
    return result


def _episode(store, run_id, episode_id):
    _require(store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_episodes'").fetchone() is not None, 'saved_episode_required')
    row = store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?', (run_id, episode_id)).fetchone()
    _require(row is not None, 'saved_episode_required')
    path, request = json.loads(row['path']), json.loads(row['request'])
    _require(type(path) is list and bool(path) and all(type(part) is list and len(part) == 2 and all(type(item) is str and item for item in part) for part in path), 'saved_path_invalid')
    _require(EpisodeRef(run_id, tuple(map(tuple, path))).episode_id == episode_id, 'saved_episode_identity_conflict')
    _require(type(request) is dict and type(request.get('message')) is dict, 'saved_request_invalid')
    return path, request


def capture_publisher_binding(store, run_id, context, registry):
    """Use only the actual supplied workflow registry for a new population."""
    settings = _settings(store, run_id)
    if settings is None:
        # True standalone execution has no declared runtime owner to invent.
        return None
    _require(isinstance(registry, EpisodeBindingRegistry), 'registry_required')
    _require(context.run_id == run_id, 'run_conflict')
    path, request = _episode(store, run_id, context.episode_id)
    _require(_same(path, context.path) and _same(request, context.request), 'context_conflict')
    graph = snapshot_graph(registry)
    saved_graph = _saved_graph(graph, settings['episode_bindings'])
    node = _select(saved_graph, path)
    actual = _select(registry, path)
    _require(_same(actual.as_record(), node.descriptor), 'registry_owner_conflict')
    return {'version': 'scientific_publisher_binding_v1', 'episode_id': context.episode_id,
        'path': deepcopy(path), 'graph': graph, 'binding_id': node.descriptor['binding_id'],
        'descriptor': deepcopy(node.descriptor)}


def validate_publisher_binding(store, run_id, request, publisher, bound_descriptor):
    """Reopen original publisher metadata after original receipt authentication.

    The supplied request is the original immutable scientific operation request,
    already matched to its stored operation. It is not the current reader's
    context. A new-version standalone None requires no declared runtime settings
    and carries no ownership claim; historical versions retain their own checks.
    """
    if publisher is None:
        _require(bound_descriptor is None, 'standalone_descriptor_conflict')
        _require(_settings(store, run_id) is None, 'declared_run_publisher_required')
        return None
    _require(type(publisher) is dict and set(publisher) == {'version', 'episode_id', 'path', 'graph', 'binding_id', 'descriptor'} and publisher['version'] == 'scientific_publisher_binding_v1', 'record_invalid')
    _require(request['run_id'] == run_id and publisher['episode_id'] == request['episode_id'], 'original_operation_conflict')
    settings = _settings(store, run_id)
    _require(settings is not None, 'saved_bindings_required')
    path, original_request = _episode(store, run_id, request['episode_id'])
    message = original_request['message']
    _require(_same(path, publisher['path']) and path[-1][0] == request['role'] and _same(message.get('scope'), request['scope']) and _same(message.get('episode_assignment', {}), request['assignment']), 'original_context_conflict')
    graph = _saved_graph(publisher['graph'], settings['episode_bindings'])
    node = _select(graph, path)
    _require(publisher['binding_id'] == node.descriptor['binding_id'] and _same(publisher['descriptor'], node.descriptor) and _same(bound_descriptor, node.descriptor), 'original_descriptor_conflict')
    return deepcopy(node.descriptor)
