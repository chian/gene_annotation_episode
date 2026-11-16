"""A107 finding progress selection."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError

def original_task_projector(assignment):
    from gene_annotation_episode.episodic_workflow.root.a107.component_axis_workflow import INSTRUCTIONS, finding_progress, task_context
    context = plain(assignment).get('context', {})
    task = context.get('a107_task')
    if task is not None and (not isinstance(task, dict) or task != task_context(task.get('name'))):
        raise ContractError('component_axis_original_task_context_mismatch')
    return finding_progress()
