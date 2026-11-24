"""Credit: the monitor's information credit, carried from the old ``credit.py`` (``MonitorEpisodeCredit``: credit
kind ``monitoring``; ``information_credit`` = ``ProgressInformationCredit(progress_reader, information_unit=...)``
with the unit always explicit). One information unit per newly informative received progress snapshot, over the
assignment's original baseline; repeated observation identities and read timestamps earn nothing. Never bounded,
clamped or rescaled.

``credit`` has no services, so the progress reader of the old projector is a reader over the snapshots the summary
holds: the baseline snapshots the commissioner passed, the snapshots this episode's observe tool returned in its
outcomes and the snapshots its child monitors returned. A progress reference without a snapshot there would have
been read from the old progress provider: that read raises where it is needed. The old estimator's raise on a
decreasing information credit (``monitor_information_credit_cannot_decrease``) is here, against the credit the
controller last saw."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.progress_information_credit import (
    ProgressInformationCredit)


def snapshot_of(snapshots, reference):
    """The delivered snapshot of a progress reference; the old progress provider's ``read_progress``."""
    if reference not in snapshots:
        raise NotImplementedError(
            'BLOCKED-ON-JOB-SERVICE: progress snapshot for ' + repr(reference) + '; wanted call: '
            "ctx.services['job_access'].read_progress(reference) for an observation the commissioner passed in "
            'known_progress_refs without its snapshot (credit and the summary have no services)')
    return snapshots[reference]


class _SummaryProgress:
    """The ``read_progress(reference, scope)`` the projector calls, answered from the summary's snapshots."""

    def __init__(self, snapshots):
        self.snapshots = snapshots

    def read_progress(self, reference, scope):
        return snapshot_of(self.snapshots, reference)


def information_projection(summary):
    """The projector's whole answer over the summary's received progress."""
    projector = ProgressInformationCredit(_SummaryProgress(summary['progress_snapshots']),
                                          information_unit=summary['information_unit'])
    return projector({'target_handle': summary['target_handle']},
                     initial_progress_refs=summary['known_progress_refs'],
                     known_progress_refs=summary['own_progress_refs'])


def credit(summary, records):
    value = information_projection(summary)['credit']
    prior = summary['current_credit']
    if not math.isfinite(value):
        raise ValueError('finite_monitoring_information_credit_required')
    if prior is not None and value < prior:
        raise ValueError('monitor_information_credit_cannot_decrease')
    return value
