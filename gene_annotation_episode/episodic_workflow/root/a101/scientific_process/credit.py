"""Private scientific-process credit behavior for A101."""
from __future__ import annotations
from .scientific_contracts import (ContractError, EVIDENCE_AXIS_VERSION, INSTRUCTION_VERSION, ROLE, selection_fields)

from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.native_correspondence_credit import A101SequenceCredit
def original_task_projector(assignment):
    return A101SequenceCredit()

class ScientificProcessCredit:
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
        if self.library.resolve(axis).get("entry_version") not in (INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION):
            return None
        return original_task_projector(context.assignment)

    def credit_view(self, context, receiver_selection):
        self.validate_context(context)
        return self.services.scientific_credit(context, receiver_selection)
