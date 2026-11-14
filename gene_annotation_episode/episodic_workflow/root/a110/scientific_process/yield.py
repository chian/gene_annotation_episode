"""Private scientific-process yield behavior for A110."""
from __future__ import annotations
from .scientific_assignment_contracts import (AXIS, ContractError, ROLE, plain, scientific_digest)

class ScientificProcessYield:
    @property
    def private_yield_binding(self):
        return self._yield_bindings is not None

    def continuation_task(self, context):
        projector = self.credit_projector(context)
        if projector is None:
            raise ContractError('scientific_task_credit_not_declared')
        assigned = plain(context.assignment).get('context', {}).get(AXIS.lower() + '_task')
        if assigned is not None:
            if not isinstance(assigned, dict) or not isinstance(assigned.get('name'), str) or not assigned['name']:
                raise ContractError('scientific_continuation_original_task_required')
            return AXIS + ':' + assigned['name']
        return AXIS + ':' + projector.as_record()['kind']

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
        if scientific_digest(plain(projector.as_record())) != scientific_digest(
                declaration['credit_definition']):
            raise ContractError('scientific_yield_credit_definition_mismatch:' + task)
        if getattr(projector, 'yield_method', None) != declaration['kind']:
            raise ContractError('scientific_yield_method_credit_mismatch:' + task)
        if declaration['kind'] == 'accumulation':
            from gene_annotation_episode.episodic_workflow.root.a110.numerical import YieldController, YieldParameters
            return YieldController(epoch, initial_credit, declaration['cutoff'],
                YieldParameters(**declaration['parameters']))
        raise ContractError('scientific_yield_method_unavailable:' + task)
