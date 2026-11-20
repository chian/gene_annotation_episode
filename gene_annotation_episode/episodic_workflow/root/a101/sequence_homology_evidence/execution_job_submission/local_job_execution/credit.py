"""Credit: what the assignment's handoff requirement defines, earned by the handoff and by nothing else.

The assignment's ``progress_requirements`` give each requirement a credit; a requirement whose predicate is
``requested_job_handoff`` is satisfied when the job has been handed off. The Episode's credit is the credit of
those requirements (``handoff_credit``, which ``read_from_parent`` summed) once it holds a handoff row of the
assigned resource: the ``JOB_LEDGER`` row ``job_access`` wrote when the resource accepted the job. The only job this
Episode can launch is the assigned one, so the row is that job's. Before it is held the credit is zero: a failed
launch and a hold earn nothing. The row is read through ``records``, so the credit is of a record the Episode
holds, not of what a tool said.

The other predicate kinds of a practical assignment (a path, a digest, a command exit, the job's outputs) are
facts of a job that ran. A launch ends at handoff and establishes none of them, so it earns none of their credit:
they are earned by the Episodes that check the job and fetch its results."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows


def credit(summary, records):
    resource_id = summary['assignment']['resource_id']
    handed_off = any(row['event'] == 'handoff' and row['detail']['resource_id'] == resource_id
                     for row in job_rows(records))
    return summary['handoff_credit'] if handed_off else 0.0
