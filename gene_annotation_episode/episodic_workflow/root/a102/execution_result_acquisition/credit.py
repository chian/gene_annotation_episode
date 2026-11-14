"""Private A102 Results credit."""
from __future__ import annotations
from .execution_contracts import math, plain

class ResultsCredit:

    def _generic_result_selector_progress(self, context, results, initial):
        """Credit saved byte positions once, regardless of read boundaries."""
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        if not requested:
            return 0.0

        def covered(windows, start, end):
            intervals = sorted(((max(start, window['offset']), min(end, window['offset'] + window['returned_bytes'])) for window in windows if window['offset'] < end and window['offset'] + window['returned_bytes'] > start))
            total, right = (0, start)
            for left, stop in intervals:
                if stop > right:
                    total += stop - max(left, right)
                    right = stop
            return total
        fractions = []
        for path, (start, length) in requested.items():
            windows = [(reference, window) for reference, body in results.items() for window in body['windows'] if window['path'] == path]
            observed_end = max((window['size_bytes'] for _, window in windows), default=start)
            end = start + length if length is not None else max(start, observed_end)
            if end <= start:
                fractions.append(0.0)
                continue
            all_bytes = covered((window for _, window in windows), start, end)
            old_bytes = covered((window for reference, window in windows if reference in initial), start, end)
            fractions.append((all_bytes - old_bytes) / (end - start))
        return math.fsum(fractions) / len(fractions)

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
