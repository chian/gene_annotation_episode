"""How the A107 monitor's credit is counted (carried from ``credit.py`` and the check in ``yield_estimator.py``).

Credit kind ``monitoring``: the monitor's own ``ProgressInformationCredit`` (newly informative received progress
snapshots times ``information_unit``) over the assignment's known baseline. ``credit`` has no services, so the
progress reader of the old projector is a reader over the snapshots the summary holds: the baseline snapshots the
commissioner passed, those this episode's observe tool returned in its outcomes and those its dependency monitors
returned. A reference without a snapshot there would have been read from the old progress provider: that read
raises where it is needed (BLOCKED-ON-JOB-SERVICE). The old estimator's rule that monitoring information credit
cannot decrease lives here. Credit is never bounded, clamped or rescaled.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.grading.partner_presence_evidence.progress_information_credit import ProgressInformationCredit


class SummaryProgress:
    """The ``read_progress(reference, scope)`` the projector calls, answered from the summary's snapshots."""

    def __init__(self, snapshots):
        self.snapshots = snapshots

    def read_progress(self, reference, scope=None):
        if reference not in self.snapshots:
            raise NotImplementedError(
                'BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services[\'job_access\'].read_progress('
                + repr(reference) + ') for a progress observation received without its snapshot (credit and the '
                'summary have no services)')
        return {**self.snapshots[reference], 'progress_ref': reference}


def checked_increment(previous, current):
    """The old estimator's rule: monitoring information credit cannot decrease."""
    if current < previous:
        raise ValueError('monitor_information_credit_cannot_decrease')
    return current


def credit(summary, records):
    projector = ProgressInformationCredit(SummaryProgress(summary['progress_snapshots']),
                                          information_unit=summary['information_unit'])
    refs = summary['received_progress_refs']

    def over(received):
        return projector(summary['scope'], initial_progress_refs=summary['known_progress_refs'],
                         known_progress_refs=received)['credit']

    current = over(refs)
    previous = over(refs[:-1]) if refs else current
    return checked_increment(previous, current)
