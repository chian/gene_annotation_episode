"""Credit: the monitor's information credit, carried from the old ``credit.py`` (``MonitorEpisodeCredit``:
credit kind ``monitoring``; ``information_credit`` = ``ProgressInformationCredit(progress_reader, information_unit=
...)`` with the unit always explicit). One information unit per newly informative received progress snapshot, over
the assignment's original baseline; repeated observation identities and read timestamps earn nothing. Never
bounded, clamped or rescaled.

``credit`` has no services, so the progress reader of the old projector is a reader over the snapshots the summary
holds: the snapshots this episode's observe tool returned in its outcomes and the snapshots its child monitors
returned. The old estimator's raise on a decreasing information credit (``monitor_information_credit_cannot_
decrease``) is here, against the credit the controller last saw."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.progress_information_credit import (
    ProgressInformationCredit)


class _SummaryProgress:
    """The ``read_progress(reference, scope)`` the projector calls, answered from the summary's snapshots."""

    def __init__(self, snapshots):
        self.snapshots = snapshots

    def read_progress(self, reference, scope):
        if reference not in self.snapshots:
            raise NotImplementedError(
                'BLOCKED-ON-JOB-SERVICE: progress snapshot record for ' + repr(reference) + '; wanted call: '
                "ctx.services['job_access'].read('read_progress', reference, scope) for a progress observation the "
                'commissioner passed in known_progress_refs (credit has no services, the commission passes no '
                'snapshot record)')
        return self.snapshots[reference]


def information_projection(summary):
    """The projector's whole answer over the summary's received progress."""
    projector = ProgressInformationCredit(_SummaryProgress(summary['progress_snapshots']),
                                          information_unit=summary['information_unit'])
    return projector({'target_handle': summary['target_handle']},
                     initial_progress_refs=summary['known_progress_refs'],
                     known_progress_refs=summary['received_progress_refs'])


def credit(summary, records):
    value = information_projection(summary)['credit']
    prior = summary['current_credit']
    if not math.isfinite(value):
        raise ValueError('finite_monitoring_information_credit_required')
    if prior is not None and value < prior:
        raise ValueError('monitor_information_credit_cannot_decrease')
    return value
