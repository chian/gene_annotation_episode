from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _delegate
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _practical_context
from .execution_contracts import ROLE_KINDS
from .execution_contracts import plain

class NativeState:
    _delegate = _delegate
    _practical_context = _practical_context

    def initialize(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch
        if is_compact_launch(plain(context.assignment)):
            self.flux_balance_requests.initialize_launch(context)
            return
        if is_compact_assignment(plain(context.assignment)):
            self.flux_balance_requests.initialize_resource(context)
            self.flux_balance_inputs.initialize(context)
            return self._delegate(context).initialize(self._practical_context(context))
        self._check_parent_inputs(context)
        if 'native_flux_balance' in plain(context.assignment).get('requested_job', {}):
            self.flux_balance_inputs.initialize(context)
        return self._delegate(context).initialize(context)

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        return self._delegate(context).state(self._practical_context(context))
