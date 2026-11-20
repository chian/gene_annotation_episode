"""Credit: ``handoff_unit``, earned by the handoff and by nothing else. The Episode holds the handoff row of the
assigned resource (the ``JOB_LEDGER`` row ``job_access`` wrote when the resource accepted the job) once the launch
succeeded; before that the credit is zero. A failed launch earns nothing. The row is read through ``records``, so
the credit is of a record the Episode holds, not of what a tool said."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import job_rows


def credit(summary, records):
    handed_off = any(row['event'] == 'handoff' and row['detail']['resource_id'] == summary['resource_id']
                     for row in job_rows(records))
    return summary['handoff_unit'] if handed_off else 0.0
