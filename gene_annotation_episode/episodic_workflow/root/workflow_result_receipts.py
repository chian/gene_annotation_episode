"""Root host ports defined by WorkflowResultReceipts."""
from __future__ import annotations

class WorkflowResultReceipts:

    def read_received_hpc_result(self, context, reference):
        from .hpc_result_receipts import read_received_result
        try:
            binding = self.workflow.episode_bindings.for_role('hpc')
        except LookupError as error:
            raise ValueError('configured_hpc_result_authority_required') from error
        return read_received_result(binding, context, reference)

