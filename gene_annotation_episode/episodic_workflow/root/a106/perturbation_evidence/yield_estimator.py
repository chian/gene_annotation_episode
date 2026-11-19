"""The A106 head's continuation: its declared credit-based yield controller."""
from __future__ import annotations
from .scientific_contracts import AXIS, ContractError, plain, scientific_digest

TASK = AXIS + ':whole_axis_findings'


class PerturbationEvidenceYield:

    def head_continuation(self, evidence_task, initial_credit, epoch):
        """The yield controller this head declared for its commissioned whole-axis finding task.

        The saved task declaration fixes the estimator kind, its parameters and
        the continuation cutoff; its credit definition must be exactly the
        projector of the commissioned evidence task. Credit is never bounded.
        """
        from .credit import original_task_projector
        from yield_control import AccumulationYieldController, YieldParameters
        if TASK not in self._yield_bindings:
            raise ContractError('scientific_yield_binding_missing_for_task:' + TASK)
        declaration = self._yield_bindings[TASK]
        projector = original_task_projector({'context': {'evidence_task': plain(evidence_task)}})
        if scientific_digest(plain(projector.as_record())) != scientific_digest(declaration['credit_definition']):
            raise ContractError('scientific_yield_credit_definition_mismatch:' + TASK)
        if projector.yield_method != declaration['kind']:
            raise ContractError('scientific_yield_method_credit_mismatch:' + TASK)
        return AccumulationYieldController(epoch, initial_credit, declaration['cutoff'], YieldParameters(**declaration['parameters']))
