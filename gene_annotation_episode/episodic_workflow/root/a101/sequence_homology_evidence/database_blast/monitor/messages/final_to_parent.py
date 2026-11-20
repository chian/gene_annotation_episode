"""The return: controlled fields only, read by code from the check rows this episode holds. No text is returned.

Always returned: ``credit`` (the system's), ``finding`` (whether the job was observed, the number of checks the service
answered, and from the latest check the job's state from the job service's fixed vocabulary and whether its results are
available) and ``check_refs`` (the check rows this episode wrote, in custody: the parent passes them back as the baseline
of the next visit and to the results child)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import JOB_STATES

FINDING_FORM = RecordForm({
    'observed': Field('boolean', 'Whether a check of the job was answered by the job service in this visit'),
    'checks_made': Field('integer', 'The number of checks this visit made that the job service answered'),
    'state': ChoiceField('text', "The job's state at the latest check this episode holds", JOB_STATES, required=False),
    'result_available': Field('boolean', "Whether the job's results were available at that check", required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the visit found of the job', form=FINDING_FORM),
    'check_refs': Field('record_refs', 'The check rows this visit wrote'),
})


def final_to_parent(summary, completion, selection):
    latest, own = summary['latest'], summary['own_check_refs']
    finding = {'observed': bool(own), 'checks_made': len(own)}
    if latest is not None:
        finding.update({'state': latest['state'], 'result_available': latest['result_available']})
    return {'credit': completion['credit'], 'finding': finding, 'check_refs': list(own)}
