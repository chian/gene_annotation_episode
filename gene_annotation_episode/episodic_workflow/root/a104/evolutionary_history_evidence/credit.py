"""Private scientific-process credit behavior for A104."""
from __future__ import annotations
from .scientific_assignment_contracts import (ContractError, INSTRUCTION_VERSION, ROLE, selection_fields)

class EvolutionaryHistoryEvidenceCredit:
    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    def credit_projector(self, context):
        if context.role != ROLE:
            return None
        if self._yield_bindings is not None and not context.assignment.get("proposed_annotation_ref"):
            raise ContractError("scientific_task_proposed_annotation_required")
        selection = self._original_selection(context)
        axis = selection[selection_fields(selection)[0]]
        if self.library.resolve(axis).get("entry_version") not in (INSTRUCTION_VERSION,):
            return None
        from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.task_projector import original_task_projector
        return original_task_projector(context.assignment)

    def credit_view(self, context, receiver_selection):
        self.validate_context(context)
        return self.services.scientific_credit(context, receiver_selection)
