"""Private A101 launch_hpc internal summary."""
from __future__ import annotations
from .execution_contracts import KINDS, deepcopy, plain

class OperationalSummary:

    def initial_decision_context(self, context):
        if self.local_file_sources.applies(context):
            target = self._target(context)
            return {'execution_resource_capabilities': [{'resource_id': target['resource_id'], 'resource_kind': 'local'}], 'execution_initial_information': {}}
        value = {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources], 'execution_initial_information': deepcopy(self.initial_information), 'received_bvbrc_values': [] if self.api_execution is None else self.api_execution.received_bvbrc_context(context)}
        if context.role in {'annotation', 'scientific_process'} and self.api_execution is not None and any((service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            pass
        if self._forwards_minhash_reports(context.role):
            value['received_minhash_values'] = self.api_execution.minhash.received_context(context)
        return value

    def _with_selected_execution_task(self, context, value):
        assignment = plain(context.assignment)
        return value

    def decision_context(self, context, current_view):
        self.credit_kind(context.role)
        value = self._delegate(context).decision_context(context, current_view)
        return self._with_selected_execution_task(context, value)
