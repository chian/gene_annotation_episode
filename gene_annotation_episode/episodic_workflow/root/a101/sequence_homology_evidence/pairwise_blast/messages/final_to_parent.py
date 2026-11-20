"""The return: controlled data only. Always returned: the episode's credit (the system hands it in ``completion``; it
is the signal of whether the comparison was productive) and the finding: whether the job was handed off and the
correspondence graded, the state of the job as last observed, the counts of units that completed and failed, and the
controlled features code read from the saved pairwise sheet (counts and fractions of paired and identical residues,
the native E-value with the context the report gives). The sheet itself stays in this episode.

Selectable, with the names the generic episodes use: ``execution_handoff_refs`` (the handoff row of the job),
``execution_job_record_refs`` (the latest check row and the closure row), ``execution_blast_graded_refs`` (the saved
pairwise sheet, the source it is retained on and its search row) and ``execution_completed``. No text of any kind is
returned."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_pairwise_features import (
    MEANINGS, SHEET_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import JOB_STATES

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean', 'ref': 'record_refs'}


def feature_field(name, rule):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name], required=rule[-1] != 'optional')


SHEET_FORM = RecordForm({name: feature_field(name, rule) for name, rule in SHEET_FEATURES.items()})
FINDING_FORM = RecordForm({
    'handed_off': Field('boolean', 'Whether the search was launched and handed off'),
    'execution_completed': Field('boolean', 'Whether the correspondence of the two sequences is graded and saved'),
    'job_state': ChoiceField('text', 'The state of the job in the latest check or closure row this episode holds',
                             ('not_observed', *JOB_STATES)),
    'acquisitions': Field('integer', 'The number of units that completed'),
    'failure_count': Field('integer', 'The number of units that returned a failed or an invalid outcome'),
    'pairwise_sheets': Field('list', 'One entry per pairwise grading this episode saved', items=SHEET_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the comparison is graded and the controlled features of the saved sheet',
                     form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff row of the job', required=False),
    'execution_job_record_refs': Field('record_refs', 'The latest check row and the closure row of the job',
                                       required=False),
    'execution_blast_graded_refs': Field('record_refs', 'The saved pairwise sheet, the source it is retained on '
                                                        'and its search row', required=False),
    'execution_completed': Field('boolean', 'Whether the correspondence is graded and saved. Yielding alone is '
                                            'false', required=False),
})


def final_to_parent(summary, completion, selection):
    units = summary['units']
    finding = {'handed_off': summary['handoff_ref'] is not None, 'execution_completed': summary['execution_completed'],
               'job_state': summary['job']['last_observed_state'] or 'not_observed',
               'acquisitions': sum(1 for unit in units if unit['status'] == 'completed'),
               'failure_count': sum(1 for unit in units if unit['status'] != 'completed'),
               'pairwise_sheets': summary['pairwise_sheets']}
    return {'credit': completion['credit'], 'finding': finding,
            **{name: summary['execution_progress'][name] for name in selection}}
