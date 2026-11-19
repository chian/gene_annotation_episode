"""This monitor's internal summary (carried from ``internal_summary.py``, ``received_progress.py`` and
``progress_records.py``).

What counts as received progress: the assignment's known observations, the observations its own recorded
outcomes delivered and those its admitted dependency monitors delivered, in that order, without repeats. A
snapshot may be read only once received. The summary block the model sees at each decision names the assignment,
the target description, its exposed direct dependencies, the received progress and what those mean.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, plain)

from ..goal import planning_context

INFORMATION_MEANING = ('Exposed direct relationships and already delivered observations. Empty measurements/log '
                       'windows do not assert absence or a stall.')


def unique(values):
    """Order-preserving de-duplication."""
    return list(dict.fromkeys(values))


def received_progress(assignment, outcomes):
    """Received progress refs: the assignment's known refs, then every recorded outcome's ``progress_refs``.

    Old ``ReceivedProgress._received`` joined ``known_progress_refs``, ``_own_progress_refs`` (its own outcomes,
    paged) and ``services.received_progress_refs`` (refs admitted from children). A child unit's recorded outcome
    carries the progress refs its admitted return delivered, so both are recorded outcomes here.
    """
    return unique([*assignment['known_progress_refs'],
                   *(reference for outcome in outcomes for reference in outcome.get('progress_refs', ()))])


def received_snapshot(progress, scope, received, reference):
    """A progress observation this monitor received; any other raises (old ``ReceivedProgress._snapshot``)."""
    if reference not in received:
        raise ContractError('monitor_progress_not_received')
    return progress.read_progress(reference, plain(scope))


def decision_context(progress, request, assignment, scope, received, yield_settings):
    """The monitor's own block of the decision context (old ``MonitorSummary.decision_context``)."""
    return {'monitor_assignment': assignment,
            'monitor_target_description': plain(progress.describe_target(assignment['target_handle'], plain(scope))),
            'monitor_direct_dependencies': plain(progress.direct_dependencies(assignment['target_handle'],
                                                                              plain(scope))),
            'monitor_received_progress_refs': list(received),
            'monitor_information_meaning': INFORMATION_MEANING,
            'monitor_goal': planning_context(request, assignment, yield_settings)}
