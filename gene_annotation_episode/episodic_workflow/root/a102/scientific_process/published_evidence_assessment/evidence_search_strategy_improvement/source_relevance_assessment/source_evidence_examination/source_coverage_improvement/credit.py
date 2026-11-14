"""Private A102 literature_ordered credit."""
from __future__ import annotations

class SourceCredit:

    def credit_kind(self, role):
        self._role(role)
        return 'scientific'

    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        return self.services.scientific_credit(context, receiver_selection)

    def credit_projector(self, context):
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import LiteratureTaskCredit
        self._role(context.role)
        return LiteratureTaskCredit(self, context)
