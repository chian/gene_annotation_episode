"""Private A104 HPCExecution retained native receipts."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class HPCExecutionRetainedNativeReceipts:

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        context.role
        return self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        return context

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        if context.role not in {'launch_local', 'launch_hpc'}:
            raise ValueError('practical_resource_role_required')
        return self._delegate(context).state(self._practical_context(context))
