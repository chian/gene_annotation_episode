"""The A102 monitor's internal summary (carried from ``internal_summary.py``).

The monitor's own block of the decision context: its assignment, the target description, the target's exposed
direct dependencies, the progress it received, what empty measurements mean, and its planning goal.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import plain

from ..goal import planning_context

MEANING = ('Exposed direct relationships and already delivered observations. Empty measurements/log windows do not '
           'assert absence or a stall.')


def decision_context(provider, *, request_goal, assignment, scope, received, yield_settings):
    """The old ``MonitorSummary.decision_context`` over the run's progress provider."""
    return {'monitor_assignment': assignment,
            'monitor_target_description': plain(provider.describe_target(assignment['target_handle'], scope)),
            'monitor_direct_dependencies': plain(provider.direct_dependencies(assignment['target_handle'], scope)),
            'monitor_received_progress_refs': list(received),
            'monitor_information_meaning': MEANING,
            'monitor_goal': planning_context(request_goal, assignment, yield_settings)}


__all__ = ['MEANING', 'decision_context']
