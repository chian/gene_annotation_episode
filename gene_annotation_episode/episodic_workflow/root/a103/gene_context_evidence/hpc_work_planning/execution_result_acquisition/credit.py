"""Private A103 Results credit."""
from __future__ import annotations
from .execution_contracts import math, plain

class ResultsCredit:

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def project_credit(self, context, receiver_selection):
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        if self.native_blast_masking_results.applies(context):
            return self.native_blast_masking_results.credit_view(context, receiver_selection)
        if self.native_blast_utility_results.applies(context):
            return self.native_blast_utility_results.credit_view(context, receiver_selection)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return self.native_blast_standard_database_results.credit_view(context, receiver_selection)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return self.native_blast_database_results.credit_view(context, receiver_selection)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return self.native_hmmer_preparation_results.credit_view(context, receiver_selection)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return self.native_blast_results.credit_view(context, receiver_selection)
        if self.native_hmmer_results.applies(context):
            return self.native_hmmer_results.credit_view(context, receiver_selection)
        if self._target(context)['resource_kind'] == 'api':
            return self.api_execution.credit_view(context, receiver_selection)
        selected, handoffs, results = self._received(context, receiver_selection)
        handoffs = {ref: target for ref, target in handoffs.items() if self.job_progress_provider.targets.usable_handoff(target)}
        initial = set(selected['initial_known_record_refs'])
        baseline = {target['resource_id'] for ref, target in handoffs.items() if ref in initial}
        identities = {target['resource_id'] for target in handoffs.values()}
        handoff_count = 0
        mixed = self.local_file_sources.acquisition_counts(context, selected, results)
        acquired_fraction = self._generic_result_selector_progress(context, results, initial) if mixed is None else 0.0
        acquired_count = int(acquired_fraction > 0)
        credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_fraction
        if mixed is not None:
            acquired_count = sum(mixed)
            credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_count
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': handoff_count, **({'new_file_acquisition_count': mixed[1]} if mixed is not None else {}), **({'new_acquired_selector_fraction': acquired_fraction} if mixed is None else {}), 'new_acquired_record_count': acquired_count, 'operational_credit_binding': {'version': 'execution_received_selector_coverage_credit_v2' if mixed is None else 'execution_received_records_credit_v1', 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'qualification': 'original_selector_byte_position_union_current_filesystem_version_unverified' if mixed is None else 'original_request_resource_scope_selector_and_actual_received_unique_information'}}

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)
