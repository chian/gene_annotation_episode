"""Private A104 Launch credit."""
from __future__ import annotations
import math
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class LaunchCredit:

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def project_credit(self, context, receiver_selection):
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        self.native_blast_masking_results.applies(context)
        self.native_blast_utility_results.applies(context)
        self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context)
        self.native_blast_database_results is not None and self.native_blast_database_results.applies(context)
        self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context)
        self.native_blast_results is not None and self.native_blast_results.applies(context)
        self.native_hmmer_results.applies(context)
        selected, handoffs, results = self._received(context, receiver_selection)
        handoffs = {ref: target for ref, target in handoffs.items() if self.job_progress_provider.targets.usable_handoff(target)}
        initial = set(selected['initial_known_record_refs'])
        baseline = {target['resource_id'] for ref, target in handoffs.items() if ref in initial}
        identities = {target['resource_id'] for target in handoffs.values()}
        handoff_count = len(identities - baseline)
        mixed = None
        acquired_fraction = 0.0
        acquired_count = int(acquired_fraction > 0)
        credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_fraction
        if mixed is not None:
            acquired_count = sum(mixed)
            credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_count
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': handoff_count, **({'new_file_acquisition_count': mixed[1]} if mixed is not None else {}), **{}, 'new_acquired_record_count': acquired_count, 'operational_credit_binding': {'version': 'execution_received_records_credit_v1', 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'qualification': 'original_request_resource_scope_selector_and_actual_received_unique_information'}}

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)
