"""Existing implicit A107 annotation parent and six authenticated entry endpoints."""
from __future__ import annotations
from .task import AnnotationTask

def selects_annotation_parent(workflow, name, parent_path, binding):
    return type(name) is str and (type(parent_path) is tuple or type(parent_path) is list) and (binding is None) and (name == 'annotation') and (not parent_path) and safe_cached_annotation_registry(workflow) and ('annotation' not in workflow.episode_bindings._by_role)

def is_annotation_parent(workflow, source):
    return type(source) is AnnotationTask and safe_cached_annotation_registry(workflow) and plain_annotation_parent_path(source.path) and ('annotation' not in workflow.episode_bindings._by_role)

def child_request_assembler(role):
    if type(role) is not str:
        return None
    if role == 'launch':
        from .to_child_execution_job_submission import assemble_request
        return assemble_request
    if role == 'monitor':
        from .to_child_execution_progress_assessment import assemble_request
        return assemble_request
    if role == 'results':
        from .to_child_execution_result_acquisition import assemble_request
        return assemble_request
    if role == 'hpc':
        from .to_child_hpc_work_planning import assemble_request
        return assemble_request
    if role == 'scientific_process':
        from .to_child_scientific_process import assemble_request
        return assemble_request
    if role == 'literature':
        from .to_child_published_evidence_assessment import assemble_request
        return assemble_request
    return None

def child_report_receiver(role):
    if type(role) is not str:
        return None
    if role == 'launch':
        from .from_child_execution_job_submission import receive_report
        return receive_report
    if role == 'monitor':
        from .from_child_execution_progress_assessment import receive_report
        return receive_report
    if role == 'results':
        from .from_child_execution_result_acquisition import receive_report
        return receive_report
    if role == 'hpc':
        from .from_child_hpc_work_planning import receive_report
        return receive_report
    if role == 'scientific_process':
        from .from_child_scientific_process import receive_report
        return receive_report
    if role == 'literature':
        from .from_child_published_evidence_assessment import receive_report
        return receive_report
    return None

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
