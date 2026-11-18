"""Exact existing annotation host and its eight real child implementations.

Only cached nominal identities are inspected; the original body still performs
all registry resolution, provider calls and validation in its original order.
"""
from __future__ import annotations

def exchange_for_child(workflow, source, role):
    if type(role) is not str:
        return None
    from .episode import is_annotation_parent
    if not is_annotation_parent(workflow, source):
        return None
    registry = workflow.episode_bindings
    candidates = []
    if role == 'launch':
        candidate = registry._by_path.get('execution_job_submission')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if role == 'results':
        candidate = registry._by_path.get('execution_result_acquisition')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if role == 'launch':
        candidate = registry._by_path.get('resource_work_submission')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if role == 'results':
        candidate = registry._by_path.get('resource_result_acquisition')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if role == 'monitor':
        candidate = registry._by_path.get('execution_progress_assessment')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if role == 'hpc':
        candidate = registry._by_path.get('hpc_work_planning')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if role == 'structural_homology_evidence':
        candidate = registry._by_path.get('structural_homology_evidence')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if role == 'literature':
        candidate = registry._by_path.get('published_evidence_assessment')
        if candidate is not None and any(item is candidate for item in registry._by_role.get(role, ())):
            candidates.append(candidate)
    if len(candidates) != 1:
        return None
    child = candidates[0]
    if role == 'launch' and registry._by_path.get('execution_job_submission') is child:
        from .execution_job_submission.episode import ExecutionEpisode
        if type(child) is not ExecutionEpisode:
            return None
        from .to_child_execution_job_submission import prepare_request
        from .from_child_execution_job_submission import admit_return
    elif role == 'results' and registry._by_path.get('execution_result_acquisition') is child:
        from .execution_result_acquisition.episode import ExecutionEpisode
        if type(child) is not ExecutionEpisode:
            return None
        from .to_child_execution_result_acquisition import prepare_request
        from .from_child_execution_result_acquisition import admit_return
    elif role == 'launch' and registry._by_path.get('resource_work_submission') is child:
        from .resource_work_submission.episode import ResourceEpisode
        if type(child) is not ResourceEpisode:
            return None
        from .to_child_resource_work_submission import prepare_request
        from .from_child_resource_work_submission import admit_return
    elif role == 'results' and registry._by_path.get('resource_result_acquisition') is child:
        from .resource_result_acquisition.episode import ResourceEpisode
        if type(child) is not ResourceEpisode:
            return None
        from .to_child_resource_result_acquisition import prepare_request
        from .from_child_resource_result_acquisition import admit_return
    elif role == 'monitor' and registry._by_path.get('execution_progress_assessment') is child:
        from .execution_progress_assessment.episode import MonitorEpisode
        if type(child) is not MonitorEpisode:
            return None
        from .to_child_execution_progress_assessment import prepare_request
        from .from_child_execution_progress_assessment import admit_return
    elif role == 'hpc' and registry._by_path.get('hpc_work_planning') is child:
        from .hpc_work_planning.episode import HPCEpisode
        if type(child) is not HPCEpisode:
            return None
        from .to_child_hpc_work_planning import prepare_request
        from .from_child_hpc_work_planning import admit_return
    elif role == 'structural_homology_evidence' and registry._by_path.get('structural_homology_evidence') is child:
        from .structural_homology_evidence.episode import StructuralHomologyEvidenceEpisode
        if type(child) is not StructuralHomologyEvidenceEpisode:
            return None
        from .to_child_structural_homology_evidence import prepare_request
        from .from_child_structural_homology_evidence import admit_return
    elif role == 'literature' and registry._by_path.get('published_evidence_assessment') is child:
        from .published_evidence_assessment.episode import LiteratureEpisode
        if type(child) is not LiteratureEpisode:
            return None
        from .to_child_published_evidence_assessment import prepare_request
        from .from_child_published_evidence_assessment import admit_return
    else:
        return None
    return prepare_request, admit_return
