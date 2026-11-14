"""Existing conditional unregistered improvement parent; no added role."""
from __future__ import annotations
from .task import ImprovementTask
from ..episode import safe_cached_registry, plain_path

def selects_improvement_parent(workflow, name, parent_path, binding):
    return (type(name) is str and name == 'improvement' and plain_path(parent_path)
            and binding is None and safe_cached_registry(workflow)
            and 'improvement' not in workflow.episode_bindings._by_role
            and workflow.scientific_process_binding is None)

def is_improvement_parent(workflow, source):
    return (type(source) is ImprovementTask and safe_cached_registry(workflow)
            and plain_path(source.path) and bool(source.path)
            and source.path[-1][0] == 'improvement'
            and 'improvement' not in workflow.episode_bindings._by_role
            and workflow.scientific_process_binding is None)

def request_assembler(workflow, name, parent_path):
    if not selects_improvement_parent(workflow, name, parent_path, None):
        return None
    if len(parent_path) == 1 and parent_path[0][0] == 'annotation':
        from ..to_child_annotation_improvement import assemble_request
    elif parent_path and parent_path[-1][0] == 'improvement':
        from .to_child_annotation_improvement import assemble_request
    else:
        from .from_parent import assemble_request
    return assemble_request
