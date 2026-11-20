"""The return: controlled fields only. Always returned: the Episode's credit (the system hands it in ``completion``;
it is the productivity signal and no field restates it) and the finding: whether the requested acquisition is
complete, the state of the job as last observed, the counts of what was acquired and what was refused (how often
the job service refused because the results of the job were not available), the bytes retained, and for each BLAST
database grading the Episode saved
the controlled features code read from the grading sheet (``INVESTIGATION_FINDING_FEATURES_a101.md`` section 5.3) with
the sheet's reference, for each pairwise BLAST grading the Episode saved the controlled features of its pairwise
sheet (counts and fractions of paired residues, the native E-value and its search-space context), and for each hit of the local phmmer gradings it saved the features of its HMMER search
sheets (section 6.3). No model-written text and no open record is returned.

Selectable: ``execution_handoff_refs`` (the handoff row), ``execution_job_record_refs`` (the latest check row and
the closure row of the job: the parent that holds the closure no longer counts the job as outstanding),
``execution_result_refs`` (each result acquisition this Episode retained: its record, its information artifact and
the fetched files its windows lie in), ``execution_file_source_refs``, ``execution_completed``,
``execution_phmmer_graded_refs`` (the graded local phmmer return) and ``execution_blast_graded_refs`` (the graded
return of a BLAST database grader request: each saved ``blast_database_sheet_v1`` grading artifact and the
``ncbi_blast`` source it is retained on)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    FUNCTION_FEATURES, FUNCTION_MEANINGS, MEANINGS, SHEET_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_pairwise_features import (
    MEANINGS as PAIRWISE_MEANINGS, SHEET_FEATURES as PAIRWISE_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_search_features import (
    FEATURES as HIT_FEATURES, MEANINGS as HIT_MEANINGS)

FAMILIES = ('blast_graded', 'blast_pairwise', 'phmmer_graded', 'local_file_source', 'native_blast_masking', 'native_blast_utility', 'api',
            'native_blast_standard_database', 'native_blast_database', 'native_hmmer_preparation', 'native_hmmer',
            'native_bytes')
JOB_STATES = ('not_observed', 'queued', 'running', 'finished', 'failed', 'cancelled', 'unknown')
FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean', 'refs': 'record_refs', 'text': 'text'}


def feature_field(name, rule, meanings):
    optional = rule[-1] == 'optional'
    if rule[0] == 'choice':
        return ChoiceField('text', meanings[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], meanings[name], required=not optional)


FUNCTION_FORM = RecordForm({name: feature_field(name, rule, FUNCTION_MEANINGS)
                            for name, rule in FUNCTION_FEATURES.items()})
SHEET_FORM = RecordForm({**{name: feature_field(name, rule, MEANINGS) for name, rule in SHEET_FEATURES.items()},
                         'functions': Field('list', MEANINGS['functions'], items=FUNCTION_FORM)})
PAIRWISE_FORM = RecordForm({name: feature_field(name, rule, PAIRWISE_MEANINGS)
                            for name, rule in PAIRWISE_FEATURES.items()})
HIT_FORM = RecordForm({name: feature_field(name, rule, HIT_MEANINGS) for name, rule in HIT_FEATURES.items()})
FINDING_FORM = RecordForm({
    'execution_completed': Field('boolean', 'Whether the requested acquisition is complete: the job finished and '
                                            'every requested byte is retained, or a saved grading of the requested '
                                            'return'),
    'target_family': ChoiceField('text', 'The family of the original target', FAMILIES),
    'acquisitions': Field('integer', 'The number of selected operations that completed'),
    'failure_count': Field('integer', 'The number of selected operations that returned a failed or an invalid '
                                      'outcome'),
    'job_state': ChoiceField('text', 'The state of the job in the latest check or closure row this episode holds',
                             JOB_STATES),
    'results_not_available': Field('integer', 'The number of fetches the job service refused because the results '
                                              'of the job were not available (the job had not ended)'),
    'windows_acquired': Field('integer', 'The number of byte windows this episode retained'),
    'bytes_acquired': Field('integer', 'The number of bytes in the windows this episode retained'),
    'graded_sheets': Field('list', 'One entry per BLAST database grading this episode saved', items=SHEET_FORM),
    'profile_sheets': Field('list', 'One entry per hit of the phmmer gradings this episode saved', items=HIT_FORM),
    'pairwise_sheets': Field('list', 'One entry per pairwise BLAST grading this episode saved', items=PAIRWISE_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested acquisition is complete, its counts and the controlled '
                               'features of the saved gradings', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff row of the job, when this episode holds it',
                                    required=False),
    'execution_job_record_refs': Field('record_refs', 'The job ledger rows this episode chose for its parent: the '
                                       'latest check row it holds (the state of the job last observed) and, once '
                                       'the results were fetched, the closure row of the job', required=False),
    'execution_result_refs': Field('record_refs', 'The result acquisitions this episode retained: each result '
                                   'record, its information artifact and the fetched files its windows lie in',
                                   required=False),
    'execution_file_source_refs': Field('record_refs', 'Source references for selected local file streams actually '
                                        'retained by this results episode; no producing-execution or atomic-version '
                                        'identity is established', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information: '
                                 'the job finished and every requested byte is retained, or the requested grading '
                                 'is saved. Yielding alone is false', required=False),
    'execution_blast_graded_refs': Field('record_refs', 'The graded BLAST return: each saved '
                                         'blast_database_sheet_v1 or blast_pairwise_sheet_v1 grading artifact, the '
                                         'source it is retained on and its tool-profile row', required=False),
    'execution_phmmer_graded_refs': Field('record_refs', 'The graded local phmmer return: the parsed snapshot, '
                                          'its tool-profile row, the references, each graded alignment source with '
                                          'its observation and its retained hmmer_search_sheet_v1 grading',
                                          required=False),
})


def _finding(summary):
    windows = [window for result in summary['results'] if not result['initial'] for window in result['windows']]
    rows = (summary['gradings'] if summary['family'] in ('blast_graded', 'blast_pairwise', 'phmmer_graded')
            else summary['acquisitions'])
    return {'execution_completed': summary['execution_completed'], 'target_family': summary['family'],
            'acquisitions': sum(1 for row in rows if row['status'] == 'completed'),
            'failure_count': sum(1 for row in rows if row['status'] != 'completed'),
            'job_state': summary['job']['last_observed_state'] or 'not_observed',
            'results_not_available': sum(1 for row in summary['acquisitions']
                                         if row['status'] == 'failed'
                                         and row['failure_code'] == 'results_not_available'),
            'windows_acquired': len(windows), 'bytes_acquired': sum(window['returned_bytes'] for window in windows),
            'graded_sheets': summary['graded_sheets'], 'profile_sheets': summary['profile_sheets'],
            'pairwise_sheets': summary['pairwise_sheets']}


def final_to_parent(summary, completion, selection):
    facts = summary['execution_progress']
    return {'credit': completion['credit'], 'finding': _finding(summary), **{name: facts[name] for name in selection}}
