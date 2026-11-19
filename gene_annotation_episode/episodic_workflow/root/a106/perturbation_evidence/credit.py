"""The A106 head's credit: finding progress for the commissioned whole-axis finding task."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.findings.perturbation_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress


def original_task_projector(assignment):
    """One ``credit_unit`` per distinct retained finding known to the episode (never bounded)."""
    assignment = plain(assignment)
    if not isinstance(assignment.get('context'), dict) or 'evidence_task' not in assignment['context']:
        raise ContractError('original_axis_finding_task_required')
    task = assignment['context']['evidence_task']
    if (not isinstance(task, dict) or set(task) != {
            'version', 'kind', 'evidence_axis', 'credit_unit'}
            or task['version'] != 'evidence_axis_task_v1'
            or task['kind'] != 'whole_axis_findings' or task['evidence_axis'] != 'A106'):
        raise ContractError('original_axis_finding_task_required')
    return ScientificFindingProgress(FindingProgressPolicy(task['credit_unit']))
