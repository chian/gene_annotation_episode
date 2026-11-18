"""The existing unregistered improvement grain and recursive path domain."""
from __future__ import annotations
from .task import ImprovementTask


def plain_path(path):
    return ((type(path) is tuple or type(path) is list)
            and all((type(part) is tuple or type(part) is list)
                    and len(part) == 2 and all(type(value) is str for value in part)
                    for part in path))


def plain_improvement_path(workflow, path):
    from ..episode import safe_cached_annotation_registry
    if not safe_cached_annotation_registry(workflow) or not plain_path(path) or not path:
        return False
    registry = workflow.episode_bindings
    if workflow.partner_presence_evidence_binding is not None or 'improvement' in registry._by_role:
        return False
    if path[0][0] == 'annotation':
        return ('annotation' not in registry._by_role and len(path) > 1
                and all(part[0] == 'improvement' for part in path[1:]))
    return all(part[0] == 'improvement' for part in path)


def selects_improvement_parent(workflow, name, parent_path, binding):
    return (type(name) is str and name == 'improvement' and binding is None
            and plain_path(parent_path)
            and plain_improvement_path(workflow, (*parent_path, (name, 'selected'))))


def is_improvement_parent(workflow, source):
    return type(source) is ImprovementTask and plain_improvement_path(workflow, source.path)


def selects_improvement_continuation(workflow, path, binding):
    return binding is None and plain_improvement_path(workflow, path)


def improvement_receiving_owner(workflow, source, role):
    from ..episode import is_annotation_parent
    if type(role) is not str or role != 'improvement':
        return None
    if is_annotation_parent(workflow, source):
        return '' if workflow.partner_presence_evidence_binding is None else None
    if is_improvement_parent(workflow, source):
        return '.annotation_improvement'
    return None


def improvement_exchange_owner(workflow, source, selection, role):
    if type(selection) is not dict or any(type(key) is not str for key in selection) or type(selection.get('kind')) is not str or selection.get('kind') != 'child':
        return None
    return improvement_receiving_owner(workflow, source, role)
