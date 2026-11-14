"""Private scientific-process yield behavior for A105."""
from __future__ import annotations
from .scientific_contracts import AXIS, ROLE, plain, scientific_digest
from gene_annotation_episode.domain import ContractError

class ScientificProcessYield:

    @property
    def private_yield_binding(self):
        return self._yield_bindings is not None

    def continuation_task(self, context):
        projector = self.credit_projector(context)
        if projector is None:
            raise ContractError('scientific_task_credit_not_declared')
        return AXIS + ':whole_axis_findings'

    def yield_controller(self, context, initial_credit, epoch):
        """Bind this commissioned scientific task to its own credit forecast.

        A saved task declaration fixes the estimator, its parameters, the
        continuation cutoff and the exact credit units. An old workflow with
        no private declarations keeps its recorded controller contract.
        """
        if self._yield_bindings is None:
            return None
        if context.role != ROLE:
            raise ContractError('scientific_yield_role_not_bound')
        task = self.continuation_task(context)
        declaration = self._yield_bindings.get(task)
        if declaration is None:
            raise ContractError('scientific_yield_binding_missing_for_task:' + task)
        projector = self.credit_projector(context)
        if scientific_digest(plain(projector.as_record())) != scientific_digest(declaration['credit_definition']):
            raise ContractError('scientific_yield_credit_definition_mismatch:' + task)
        if getattr(projector, 'yield_method', None) != declaration['kind']:
            raise ContractError('scientific_yield_method_credit_mismatch:' + task)
        if declaration['kind'] == 'accumulation':
            from gene_annotation_episode.episodic_workflow.root.a105.numerical import YieldController, YieldParameters
            return YieldController(epoch, initial_credit, declaration['cutoff'], YieldParameters(**declaration['parameters']))
        if declaration['kind'] == 'bounded_quality':
            from gene_annotation_episode.episodic_workflow.root.a105.numerical import BoundedYieldController, YieldParameters
            return BoundedYieldController(epoch, initial_credit, declaration['cutoff'], projector.native_score_maximum, YieldParameters(**declaration['parameters']))
        if declaration['kind'] == 'completion':
            from gene_annotation_episode.episodic_workflow.root.a105.numerical import CompletionYieldController, YieldParameters
            return CompletionYieldController(epoch, initial_credit, declaration['cutoff'], YieldParameters(**declaration['parameters']))
        raise ContractError('scientific_yield_method_unavailable:' + task)
