"""Existing implicit A110 annotation source; not an episode registry head."""
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _original_runtime
from .task import next
from .provider import call
from .instructions import instructions

def owns_annotation_root(workflow, name, parent_path, binding):
    return type(name) is str and (type(parent_path) is tuple or type(parent_path) is list) and (binding is None) and (name == 'annotation') and (not parent_path) and safe_cached_annotation_registry(workflow) and ('annotation' not in workflow.episode_bindings._by_role)

def is_annotation_parent(workflow, source):
    return type(source) is AnnotationTask and safe_cached_annotation_registry(workflow) and plain_annotation_parent_path(source.path) and ('annotation' not in workflow.episode_bindings._by_role)
from .action import execute
from .to_parent import finish

class AnnotationTask(_original_runtime._annotation_source_base):
    next = next
    call = call
    instruction_composer = staticmethod(instructions)
    execute = execute
    finish = finish

def safe_cached_annotation_registry(workflow):
    from .runtime import Workflow, EpisodeBindingRegistry
    return type(workflow) is Workflow and type(workflow.episode_bindings) is EpisodeBindingRegistry and (type(workflow.episode_bindings._by_role) is dict) and all((type(key) is str for key in workflow.episode_bindings._by_role))

def plain_annotation_parent_path(path):
    return (type(path) is tuple or type(path) is list) and len(path) == 1 and (type(path[0]) is tuple or type(path[0]) is list) and (len(path[0]) == 2) and all((type(value) is str for value in path[0])) and (path[0][0] == 'annotation')

def selects_annotation_continuation(workflow, path, binding):
    return binding is None and plain_annotation_parent_path(path) and safe_cached_annotation_registry(workflow) and ('annotation' not in workflow.episode_bindings._by_role)


def is_annotation_report_source(workflow, source):
    """Cached nominal dispatch only; preserve all later provider predicates."""
    return is_annotation_parent(workflow, source)
