"""A105 head continuation: the configured yield controller over the head's cumulative, unbounded credit."""
from __future__ import annotations

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.option_records import scientific_digest
from yield_control import AccumulationYieldController, YieldParameters

TASK = 'A105:whole_axis_findings'
INITIAL_CREDIT_DECISION = 'a105.head.initial_credit'


class ExperimentalActivityEvidenceYield:

    def yield_declaration(self, projector):
        """This head's configured declaration for its whole-axis task, checked against its projector."""
        if self._yield_bindings is None:
            raise ContractError('a105_head_yield_binding_required:' + TASK)
        declaration = self._yield_bindings.get(TASK)
        if declaration is None:
            raise ContractError('scientific_yield_binding_missing_for_task:' + TASK)
        if scientific_digest(plain(projector.as_record())) != scientific_digest(declaration['credit_definition']):
            raise ContractError('scientific_yield_credit_definition_mismatch:' + TASK)
        if projector.yield_method != declaration['kind']:
            raise ContractError('scientific_yield_method_credit_mismatch:' + TASK)
        return declaration

    def head_controller(self, bound, collaborators):
        """Open the head's controller with the credit this Episode already knows.

        The opening credit is projected over the ``store`` collaborator from the
        Episode's own receipts (its subject, plus what an A105 parent head had
        received) and recorded, so a resumed Episode reopens with the same value.
        Continuation is the configured accumulation yield controller; credit is
        cumulative and unbounded.
        """
        store = collaborators['store']
        projector = self.credit_projector(bound.assignment)
        declaration = self.yield_declaration(projector)
        self.open_receipts(store, bound)
        initial = bound.recorder.recorded(INITIAL_CREDIT_DECISION,
                                          lambda: self.known_finding_credit(store, bound)['credit'])
        return AccumulationYieldController(bound.episode_id, initial, declaration['cutoff'],
                                           YieldParameters(**declaration['parameters']))
