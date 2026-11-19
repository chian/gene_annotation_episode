"""The plan, the unit outcomes, how many plan steps are done and the outstanding jobs, read from the job ledger
rows the Episode holds."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import outstanding_jobs


def internal_summary(view):
    return {**view.parent_input, 'outcomes': list(view.outcomes),
            'steps': min(len(view.outcomes), len(view.parent_input['plan'])),
            'outstanding_jobs': outstanding_jobs(view.records)}
