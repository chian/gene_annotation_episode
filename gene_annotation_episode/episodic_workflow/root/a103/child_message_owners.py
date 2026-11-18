"""Actual root annotation parent and eight supplied nominal child bindings.

Cached identities only; original registry resolution, callbacks, validators and
error ordering remain in the selected request body. Custom callers fall back.
"""
from __future__ import annotations


def exchange_for_child(workflow, source, role):
    if type(role) is not str:
        return None
    from gene_annotation_episode.episodic_workflow.root.a103.task import LegacyAnnotationTask
    from gene_annotation_episode.episodic_workflow.root.a103 import runtime
    if type(source) is not LegacyAnnotationTask or type(workflow) is not runtime.Workflow:
        return None
    if ((type(source.path) is not tuple and type(source.path) is not list)
            or any((type(part) is not tuple and type(part) is not list) or len(part) != 2
                   or any(type(value) is not str for value in part) for part in source.path)):
        return None
    if len(source.path) != 1 or source.path[0][0] != 'annotation':
        return None
    registry = workflow.episode_bindings
    if type(registry) is not runtime.EpisodeBindingRegistry:
        return None
    if (type(registry._by_role) is not dict or type(registry._by_path) is not dict
            or any(type(key) is not str for key in registry._by_role)
            or any(type(key) is not str for key in registry._by_path)
            or any((type(value) is not list and type(value) is not tuple) for value in registry._by_role.values())):
        return None
    if 'annotation' in registry._by_role:
        return None
    if role == 'launch':
        from gene_annotation_episode.episodic_workflow.root.a103.resource_work_submission.episode import ResourceEpisode
        child = registry._by_path.get('resource_work_submission')
        if type(child) is ResourceEpisode:
            from gene_annotation_episode.episodic_workflow.root.a103.to_child_resource_work_submission import prepare_request
            from gene_annotation_episode.episodic_workflow.root.a103.from_child_resource_work_submission import admit_return
        else:
            from gene_annotation_episode.episodic_workflow.root.a103.execution_job_submission.episode import ExecutionEpisode
            child = registry._by_path.get('execution_job_submission')
            if type(child) is not ExecutionEpisode:
                return None
            from gene_annotation_episode.episodic_workflow.root.a103.to_child_execution_job_submission import prepare_request
            from gene_annotation_episode.episodic_workflow.root.a103.from_child_execution_job_submission import admit_return
            if not any(candidate is child for candidate in registry._by_role.get(role, ())):
                return None
            return prepare_request, admit_return, True
    elif role == 'results':
        from gene_annotation_episode.episodic_workflow.root.a103.resource_result_acquisition.episode import ResourceEpisode
        child = registry._by_path.get('resource_result_acquisition')
        if type(child) is ResourceEpisode:
            from gene_annotation_episode.episodic_workflow.root.a103.to_child_resource_result_acquisition import prepare_request
            from gene_annotation_episode.episodic_workflow.root.a103.from_child_resource_result_acquisition import admit_return
        else:
            from gene_annotation_episode.episodic_workflow.root.a103.execution_result_acquisition.episode import ExecutionEpisode
            child = registry._by_path.get('execution_result_acquisition')
            if type(child) is not ExecutionEpisode:
                return None
            from gene_annotation_episode.episodic_workflow.root.a103.to_child_execution_result_acquisition import prepare_request
            from gene_annotation_episode.episodic_workflow.root.a103.from_child_execution_result_acquisition import admit_return
            if not any(candidate is child for candidate in registry._by_role.get(role, ())):
                return None
            return prepare_request, admit_return, True
    elif role == 'literature':
        from gene_annotation_episode.episodic_workflow.root.a103.published_evidence_assessment.episode import LiteratureEpisode
        child = registry._by_path.get('published_evidence_assessment')
        if type(child) is not LiteratureEpisode:
            return None
        from gene_annotation_episode.episodic_workflow.root.a103.to_child_published_evidence_assessment import prepare_request
        from gene_annotation_episode.episodic_workflow.root.a103.from_child_published_evidence_assessment import admit_return
    elif role == 'gene_context_evidence':
        from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.episode import GeneContextEvidenceEpisode
        child = registry._by_path.get('gene_context_evidence')
        if type(child) is not GeneContextEvidenceEpisode:
            return None
        from gene_annotation_episode.episodic_workflow.root.a103.to_child_gene_context_evidence import prepare_request
        from gene_annotation_episode.episodic_workflow.root.a103.from_child_gene_context_evidence import admit_return
    elif role == 'hpc':
        from gene_annotation_episode.episodic_workflow.root.a103.hpc_work_planning.episode import HPCEpisode
        child = registry._by_path.get('hpc_work_planning')
        if type(child) is not HPCEpisode:
            return None
        from gene_annotation_episode.episodic_workflow.root.a103.to_child_hpc_work_planning import prepare_request
        from gene_annotation_episode.episodic_workflow.root.a103.from_child_hpc_work_planning import admit_return
        if not any(candidate is child for candidate in registry._by_role.get(role, ())):
            return None
        return prepare_request, admit_return, True
    elif role == 'monitor':
        from gene_annotation_episode.episodic_workflow.root.a103.execution_progress_assessment.episode import MonitorEpisode
        child = registry._by_path.get('execution_progress_assessment')
        if type(child) is not MonitorEpisode:
            return None
        from gene_annotation_episode.episodic_workflow.root.a103.to_child_execution_progress_assessment import prepare_request
        from gene_annotation_episode.episodic_workflow.root.a103.from_child_execution_progress_assessment import admit_return
        if not any(candidate is child for candidate in registry._by_role.get(role, ())):
            return None
        return prepare_request, admit_return, True
    else:
        return None
    if not any(candidate is child for candidate in registry._by_role.get(role, ())):
        return None
    return prepare_request, admit_return



def exchange_for_improvement(workflow, source, selection, role):
    from gene_annotation_episode.episodic_workflow.root.a103 import runtime
    from gene_annotation_episode.episodic_workflow.root.a103.task import LegacyAnnotationTask
    from gene_annotation_episode.episodic_workflow.root.a103.legacy_improvement.task import LegacyImprovementTask
    if type(workflow) is not runtime.Workflow or workflow.gene_context_evidence_binding is not None:
        return None
    if type(selection) is not dict or any(type(key) is not str for key in selection):
        return None
    kind = selection.get('kind')
    if type(kind) is not str or kind != 'child' or type(role) is not str or role != 'improvement':
        return None
    if type(source) is not LegacyAnnotationTask and type(source) is not LegacyImprovementTask:
        return None
    path = source.path
    if ((type(path) is not tuple and type(path) is not list) or not path
            or any((type(part) is not tuple and type(part) is not list) or len(part) != 2
                   or any(type(value) is not str for value in part) for part in path)):
        return None
    registry = workflow.episode_bindings
    if type(registry) is not runtime.EpisodeBindingRegistry or type(registry._by_role) is not dict:
        return None
    if any(type(key) is not str for key in registry._by_role):
        return None
    if 'annotation' in registry._by_role or 'improvement' in registry._by_role:
        return None
    if type(source) is LegacyAnnotationTask:
        if len(path) != 1 or path[0][0] != 'annotation':
            return None
        from gene_annotation_episode.episodic_workflow.root.a103.to_child_legacy_improvement import prepare_request
        from gene_annotation_episode.episodic_workflow.root.a103.from_child_legacy_improvement import admit_return
    else:
        if path[-1][0] != 'improvement' or any(part[0] not in ('annotation', 'improvement') for part in path):
            return None
        from gene_annotation_episode.episodic_workflow.root.a103.legacy_improvement.to_child_legacy_improvement import prepare_request
        from gene_annotation_episode.episodic_workflow.root.a103.legacy_improvement.from_child_legacy_improvement import admit_return
    return prepare_request, admit_return, True
