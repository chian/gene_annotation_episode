"""Private A102 Launch credit."""
from __future__ import annotations
from .execution_contracts import math, plain

class LaunchCredit:

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def project_credit(self, context, receiver_selection):
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        if self.native_protein_structure_results.applies(context):
            return self.native_protein_structure_results.credit_view(context, receiver_selection)
        selected, handoffs, results = self._received(context, receiver_selection)
        handoffs = {ref: target for ref, target in handoffs.items() if self.job_progress_provider.targets.usable_handoff(target)}
        initial = set(selected['initial_known_record_refs'])
        baseline = {target['resource_id'] for ref, target in handoffs.items() if ref in initial}
        identities = {target['resource_id'] for target in handoffs.values()}
        handoff_count = len(identities - baseline)
        acquired_fraction = 0.0
        acquired_count = int(acquired_fraction > 0)
        credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_fraction
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': handoff_count, 'new_acquired_record_count': acquired_count, 'operational_credit_binding': {'version': 'execution_received_records_credit_v1', 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'qualification': 'original_request_resource_scope_selector_and_actual_received_unique_information'}}

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)
