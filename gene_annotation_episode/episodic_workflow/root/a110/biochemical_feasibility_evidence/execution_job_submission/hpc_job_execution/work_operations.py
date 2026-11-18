from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _selected_result_action
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_resource_information import execution_capability_information
from .execution_contracts import NATIVE_RESULT_ORIGIN
from .execution_contracts import RESULT_PROVIDER
from .execution_contracts import ROLE_KINDS
from .execution_contracts import _immutable
from .execution_contracts import _read
from .execution_contracts import canonical
from .execution_contracts import checked
from .execution_contracts import deepcopy
from .execution_contracts import digest
from .execution_contracts import native_result_operation_catalog
from .execution_contracts import plain

class NativeWorkOperations:
    _selected_result_action = _selected_result_action

    def catalog(self, context):
        return self._delegate(context).catalog(self._practical_context(context))

    async def execute(self, context, tool_name, arguments, operation_key):
        self._check_parent_inputs(context)
        practical_context = self._practical_context(context)
        outcome = await self._delegate(context).execute(practical_context, tool_name, arguments, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment
        if is_compact_assignment(plain(context.assignment)):
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import practical_outcome_view, read_request_binding
            control = read_request_binding(self.store, context.run_id, context.episode_id)
            outcome = {**outcome, 'result': practical_outcome_view(outcome['result'], assignment=plain(practical_context.assignment), control_version=control['version'])}
            outcome.pop('operation_ref', None)
        return outcome
