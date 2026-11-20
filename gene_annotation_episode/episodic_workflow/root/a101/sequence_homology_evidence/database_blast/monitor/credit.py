"""Credit: only what is gained (owner decision D17). The monitor's credit is one information unit for each check that shows
a fact about its job which the checks before it, including those the parent handed over as the baseline, do not show: the
state, whether results are available, the service's status word, whether a finished job found hits. A re-read, a check
that was not sent, a time stamp and the elapsed time of an unfinished job earn nothing. The credit is computed from the
check rows the episode holds, through ``records``, so it is the credit of records in custody, not of what a tool said."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import FIELDS, progress_information


def credit(summary, records):
    return progress_information(records, summary['known_progress_refs'], FIELDS, summary['information_unit'])['credit']
