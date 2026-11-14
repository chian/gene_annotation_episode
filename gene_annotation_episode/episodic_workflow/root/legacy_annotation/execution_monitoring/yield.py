from __future__ import annotations
from collections.abc import Mapping
from dataclasses import replace

def _monitor_information_yield(scores, parameters, contexts):
    """Estimate another newly informative snapshot from this monitor's actions."""
    from gene_annotation_episode.episodic_workflow.root.numerical import estimate_nonnegative_yield
    if any((score < 0 for score in scores)):
        raise ValueError('monitor_information_credit_cannot_decrease')
    result = estimate_nonnegative_yield(scores, parameters, contexts=contexts)
    return replace(result, estimator_binding={'kind': 'monitor_information_accumulation_v1', 'credit': 'newly_informative_received_snapshot_count_times_information_unit', 'forecast': 'next_monitor_action_information_credit', 'decision': 'predicted_upper_gain_at_or_below_monitor_cutoff'})

def _blast_monitor_yield(scores, parameters, contexts, target_handle):
    """One original BLAST status observation completes this monitor visit.

    The external job can remain unfinished. Another episode may later monitor
    its saved handoff. This rule concerns the monitor's local task only.
    """
    from gene_annotation_episode.episodic_workflow.root.numerical import NumericBand, YieldEstimate, STATUS_UNIDENTIFIABLE
    observed = any((isinstance(item, Mapping) and isinstance(item.get('current_completion_evidence'), Mapping) and any((isinstance(row, Mapping) and row.get('target_handle') == target_handle and (row.get('execution_status', {}).get('native', {}).get('native', {}).get('service') == 'ncbi_blast') for row in item['current_completion_evidence'].get('progress_records', ()))) for item in contexts or ()))
    return YieldEstimate(len(scores), NumericBand.exact(0) if observed else NumericBand.coded(STATUS_UNIDENTIFIABLE), parameters, {'original_blast_status_observed': observed}, estimator_binding={'kind': 'blast_monitor_one_observation_completion_v1', 'forecast': 'zero_remaining_local_monitor_work_after_original_status_observation'})

def yield_controller(self, context, initial_credit, epoch):
    """Interpret the monitor's own newly informative snapshot credit."""
    self._role(context.role)
    if not self.private_yield_binding:
        raise ValueError('monitor_private_yield_binding_not_enabled')
    from gene_annotation_episode.episodic_workflow.root.numerical import YieldController, YieldParameters
    estimate = (lambda scores, parameters, contexts: _blast_monitor_yield(scores, parameters, contexts, context.assignment['target_handle'])) if self._is_blast_job(context) else _monitor_information_yield
    return YieldController(epoch, initial_credit, self.yield_settings['cutoff'], YieldParameters(uncertainty_alpha=self.yield_settings['uncertainty_alpha']), estimate_with_context=estimate)

def _is_blast_job(self, context):
    describe = getattr(self.services, 'describe_progress_target', None)
    if not callable(describe):
        return False
    target = describe(context.assignment['target_handle'], context.scope)
    return isinstance(target, Mapping) and target.get('resource_kind') == 'api' and (target.get('service_or_program') == 'ncbi_blast')
