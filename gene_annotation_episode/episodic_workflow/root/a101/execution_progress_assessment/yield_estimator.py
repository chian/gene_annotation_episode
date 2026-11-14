"""Original information accumulation and BLAST observation continuation calculations."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import replace
from .target_identity import is_blast_job

def _monitor_information_yield(scores, parameters, contexts):
    """Estimate another newly informative snapshot from this monitor's actions."""
    from gene_annotation_episode.episodic_workflow.root.a101.numerical import estimate_nonnegative_yield
    if any((score < 0 for score in scores)):
        raise ValueError('monitor_information_credit_cannot_decrease')
    result = estimate_nonnegative_yield(scores, parameters, contexts=contexts)
    return replace(result, estimator_binding={'kind': 'monitor_information_accumulation_v1', 'credit': 'newly_informative_received_snapshot_count_times_information_unit', 'forecast': 'next_monitor_action_information_credit', 'decision': 'predicted_upper_gain_at_or_below_monitor_cutoff'})

def blast_monitor_yield(scores, parameters, contexts, target_handle):
    """Complete this monitor visit after one original BLAST status observation."""
    from gene_annotation_episode.episodic_workflow.root.a101.numerical import NumericBand, YieldEstimate, STATUS_UNIDENTIFIABLE
    observed = any((isinstance(item, Mapping) and isinstance(item.get('current_completion_evidence'), Mapping) and any((isinstance(row, Mapping) and row.get('target_handle') == target_handle and (row.get('execution_status', {}).get('native', {}).get('native', {}).get('service') == 'ncbi_blast') for row in item['current_completion_evidence'].get('progress_records', ()))) for item in contexts or ()))
    return YieldEstimate(len(scores), NumericBand.exact(0) if observed else NumericBand.coded(STATUS_UNIDENTIFIABLE), parameters, {'original_blast_status_observed': observed}, estimator_binding={'kind': 'blast_monitor_one_observation_completion_v1', 'forecast': 'zero_remaining_local_monitor_work_after_original_status_observation'})
'Private monitor yield behavior for A101.'

class MonitorEpisodeYield:

    def yield_controller(self, context, initial_credit, epoch):
        """Interpret the monitor's own newly informative snapshot credit."""
        self._role(context.role)
        if not self.private_yield_binding:
            raise ValueError('monitor_private_yield_binding_not_enabled')
        from gene_annotation_episode.episodic_workflow.root.a101.numerical import YieldController, YieldParameters
        estimate = (lambda scores, parameters, contexts: blast_monitor_yield(scores, parameters, contexts, context.assignment['target_handle'])) if is_blast_job(self.services, context) else _monitor_information_yield
        return YieldController(epoch, initial_credit, self.yield_settings['cutoff'], YieldParameters(uncertainty_alpha=self.yield_settings['uncertainty_alpha']), estimate_with_context=estimate)
