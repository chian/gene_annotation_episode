"""Nominal existing improvement paths; original custom/registered fallback remains."""
from __future__ import annotations
from .task import ImprovementTask


def plain_improvement_path(workflow, path):
    from ..episode import safe_cached_registry, plain_path
    if not safe_cached_registry(workflow) or not plain_path(path) or not path:
        return False
    registry = workflow.episode_bindings
    if workflow.structural_homology_evidence_binding is not None or 'improvement' in registry._by_role:
        return False
    if path[0][0] == 'annotation':
        return ('annotation' not in registry._by_role and len(path) > 1
                and all(part[0] == 'improvement' for part in path[1:]))
    return all(part[0] == 'improvement' for part in path)


def selects_improvement_parent(workflow, name, parent_path, binding):
    from ..episode import plain_path
    return (type(name) is str and name == 'improvement' and binding is None
            and plain_path(parent_path)
            and plain_improvement_path(workflow, (*parent_path, (name, 'selected'))))


def is_improvement_parent(workflow, source):
    return type(source) is ImprovementTask and plain_improvement_path(workflow, source.path)


def selects_improvement_envelope(workflow, name, parent_path):
    return selects_improvement_parent(workflow, name, parent_path, None)


def selects_improvement_continuation(workflow, path, binding):
    return binding is None and plain_improvement_path(workflow, path)
