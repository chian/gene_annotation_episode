"""How the A102 monitor's credit is counted (carried from ``credit.py`` and the check in ``yield_estimator.py``).

Credit kind ``monitoring``: the monitor's own ``ProgressInformationCredit`` (newly informative received
progress snapshots times ``information_unit``) over the assignment's known baseline. The old
``credit_view`` delegated to the caller-bound ``services.bound_role_credit``; the new runner has no caller-bound
monitoring projector, so a monitor without its own information unit raises there. Credit is never bounded,
clamped or rescaled; a decrease raises, as the old information-accumulation estimator did.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.progress_information_credit import ProgressInformationCredit

CREDIT_KIND = 'monitoring'


def information_credit(progress_reader, *, information_unit):
    """The monitor's received-information calculation (old ``information_credit``)."""
    if information_unit is None:
        raise NotImplementedError('bound_role_credit_has_no_new_runner_equivalent')
    return ProgressInformationCredit(progress_reader, information_unit=information_unit)


def credit_view(projector, scope, assignment, received):
    """The monitor's credit view over its baseline and the progress observations it received."""
    return projector(scope, initial_progress_refs=assignment['known_progress_refs'], known_progress_refs=received)


def checked_increment(previous, current):
    """The old estimator's rule: monitoring information credit cannot decrease."""
    if current < previous:
        raise ValueError('monitor_information_credit_cannot_decrease')
    return current


__all__ = ['CREDIT_KIND', 'checked_increment', 'credit_view', 'information_credit']
