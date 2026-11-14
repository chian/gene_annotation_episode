"""Original private information accumulation continuation calculations."""
from __future__ import annotations
from dataclasses import replace

def _monitor_information_yield(scores, parameters, contexts):
    """Estimate another newly informative snapshot from this monitor's actions."""
    from gene_annotation_episode.episodic_workflow.root.a110.numerical import estimate_nonnegative_yield
    if any((score < 0 for score in scores)):
        raise ValueError('monitor_information_credit_cannot_decrease')
    result = estimate_nonnegative_yield(scores, parameters, contexts=contexts)
    return replace(result, estimator_binding={'kind': 'monitor_information_accumulation_v1', 'credit': 'newly_informative_received_snapshot_count_times_information_unit', 'forecast': 'next_monitor_action_information_credit', 'decision': 'predicted_upper_gain_at_or_below_monitor_cutoff'})
'Private monitor yield behavior for A110.'

class MonitorEpisodeYield:

    def yield_controller(self, context, initial_credit, epoch):
        """Interpret the monitor's own newly informative snapshot credit."""
        self._role(context.role)
        if not self.private_yield_binding:
            raise ValueError('monitor_private_yield_binding_not_enabled')
        from gene_annotation_episode.episodic_workflow.root.a110.numerical import YieldController, YieldParameters
        estimate = _monitor_information_yield
        return YieldController(epoch, initial_credit, self.yield_settings['cutoff'], YieldParameters(uncertainty_alpha=self.yield_settings['uncertainty_alpha']), estimate_with_context=estimate)
