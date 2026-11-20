"""Credit: the commission's handoff unit, earned by the handoff and by nothing else (D17: only what is gained).

The episode establishes one thing: the chunk's job exists on the resource and is handed off. That is a record the
episode holds, the handoff row ``job_access`` wrote when the resource accepted the job. Before it is held the credit
is zero: a refused launch earns nothing. The row is read through ``records``, so the credit is of a record in
custody, not of what a tool said. A launch ends at handoff and establishes nothing about the result: that is earned
by the episode that fetches and grades it."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows


def credit(summary, records):
    resource_id = summary['assignment']['resource_id']
    handed_off = any(row['event'] == 'handoff' and row['detail']['resource_id'] == resource_id
                     for row in job_rows(records))
    return summary['handoff_unit'] if handed_off else 0.0
