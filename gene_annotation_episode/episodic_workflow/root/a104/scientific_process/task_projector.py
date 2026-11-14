"""Original A104 evolutionary task/projector selection."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.a104_credit import A104EvolutionaryCredit, A104PanelIdentityCredit, A104AlignmentSuitabilityCredit, A104RobustnessCredit
from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import TASKS
from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import RECORD_SOURCE, received_records

def original_task_projector(assignment):
    assigned = plain(assignment)
    task = assigned.get('context', {}).get('a104_task')
    if task is not None and (not isinstance(task, dict) or task.get('name') not in TASKS or ('allowed_tasks' in task and task['allowed_tasks'] != list(TASKS))):
        raise ContractError('a104_original_task_definition_required')
    if task is None:
        return A104EvolutionaryCredit()
    return {'panel_identity': A104PanelIdentityCredit, 'alignment_suitability': A104AlignmentSuitabilityCredit, 'robustness': A104RobustnessCredit}.get(task['name'], A104EvolutionaryCredit)()
