"""Private A102 literature_targeted yield."""
from __future__ import annotations
from .source_contracts import ContractError

class SourceYield:

    def continuation_task(self, context):
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import continuation_task
        self._role(context.role)
        return continuation_task(context)

    def yield_controller(self, context, initial_credit, epoch):
        """Bind this commissioned literature episode's estimator and cutoff."""
        self._role(context.role)
        if not self.private_yield_binding:
            return None
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import _private_yield_controller, continuation_task
        key = continuation_task(context)
        declaration = self._yield_bindings.get(key)
        if declaration is None:
            raise ContractError('literature_yield_binding_missing_for_task:' + key)
        return _private_yield_controller(context, initial_credit, epoch, declaration)
