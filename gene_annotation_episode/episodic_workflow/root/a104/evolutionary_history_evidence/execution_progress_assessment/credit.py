"""Credit: the monitor's information credit, computed from the check rows the Episode holds.

Carried from the old ``credit.py`` (``MonitorEpisodeCredit``: credit kind ``monitoring``; one explicit information
unit per newly informative received progress snapshot, over the assignment's original baseline). The progress is
now the check rows of the job ledger in the Episode's custody: those its own check units wrote and those its
dependency monitors returned, in receipt order, over the baseline of check rows the commissioner passed. A check
that shows no fact the earlier ones do not show earns nothing; neither do a re-read, a log window, a wait,
timestamps, the elapsed time of an unfinished job or the size of its logs. Never bounded, clamped or rescaled.

``credit`` is handed no service: it reads the rows through ``records``. The count is
``job_progress.progress_information`` with this episode's baseline, fields and unit. The old estimator's refusal of
a decreasing credit is not carried: held rows are never taken away from a unit that completed."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import progress_information


def credit(summary, records):
    return progress_information(records, summary['known_progress_refs'], summary['requested_fields'],
                                summary['information_unit'])['credit']
