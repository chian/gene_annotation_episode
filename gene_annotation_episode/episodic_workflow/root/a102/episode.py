"""The actual existing unregistered A102 annotation host; no registry addition."""
from __future__ import annotations
from .task import AnnotationTask


def safe_cached_registry(workflow):
    from .runtime import Workflow, EpisodeBindingRegistry
    if type(workflow) is not Workflow or type(workflow.episode_bindings) is not EpisodeBindingRegistry:
        return False
    registry = workflow.episode_bindings
    if type(registry._by_role) is not dict or type(registry._by_path) is not dict:
        return False
    if any(type(key) is not str for key in registry._by_role):
        return False
    if any(type(key) is not str for key in registry._by_path):
        return False
    if any(type(value) is not list and type(value) is not tuple for value in registry._by_role.values()):
        return False
    return True


def plain_path(path):
    return ((type(path) is tuple or type(path) is list)
            and all((type(part) is tuple or type(part) is list) and len(part) == 2
                    and all(type(value) is str for value in part) for part in path))


def selects_annotation_parent(workflow, name, parent_path, binding):
    return (type(name) is str and (type(parent_path) is tuple or type(parent_path) is list)
            and binding is None and name == 'annotation' and not parent_path
            and safe_cached_registry(workflow)
            and 'annotation' not in workflow.episode_bindings._by_role)


def is_annotation_parent(workflow, source):
    return (type(source) is AnnotationTask and safe_cached_registry(workflow)
            and plain_path(source.path) and len(source.path) == 1
            and source.path[0][0] == 'annotation'
            and 'annotation' not in workflow.episode_bindings._by_role)


def selects_annotation_envelope(workflow, name, parent_path):
    return (type(name) is str and (type(parent_path) is tuple or type(parent_path) is list)
            and name == 'annotation' and not parent_path and safe_cached_registry(workflow)
            and 'annotation' not in workflow.episode_bindings._by_role)


def selects_annotation_continuation(workflow, path, binding):
    return (binding is None and plain_path(path) and len(path) == 1
            and path[0][0] == 'annotation' and safe_cached_registry(workflow)
            and 'annotation' not in workflow.episode_bindings._by_role)
