"""Private A104 credit."""
from __future__ import annotations
from .contracts import ContractError

class LiteratureCredit:

    def credit_kind(self, role):
        self._role(role)
        return 'scientific'

    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        return self.services.scientific_credit(context, receiver_selection)

    def credit_projector(self, context):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_task_credit import LiteratureTaskCredit, commissioned_task
        self._role(context.role)
        task, _ = commissioned_task(context)
        if self.assay_grading_population and task['evidence_axis'] != 'A105':
            raise ContractError('literature_task_original_axis_mismatch')
        return LiteratureTaskCredit(self, context)
