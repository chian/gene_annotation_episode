"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and no field restates it) and the finding: whether the requested acquisition is complete, the counts of what
was acquired and what failed, and for each BLAST database grading the Episode saved the controlled features code
read from the grading sheet (``INVESTIGATION_FINDING_FEATURES_a101.md`` section 5.3) with the sheet's reference, and for
each hit of the local phmmer gradings it saved the features of its HMMER search sheets (section 6.3). No
model-written text and no open record is returned.

Selectable: ``execution_handoff_refs``, ``execution_result_refs``, ``execution_file_source_refs``,
``execution_file_capture_outcomes``, ``execution_result_origin`` (the empty record when no byte window was retained),
``execution_completed``, ``execution_phmmer_graded_refs`` (the graded local phmmer return) and
``execution_blast_graded_refs`` (the graded return of a BLAST database grader request:
each saved ``blast_database_sheet_v1`` grading artifact and the ``ncbi_blast`` source it is retained on)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    FUNCTION_FEATURES, FUNCTION_MEANINGS, MEANINGS, SHEET_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_search_features import (
    FEATURES as HIT_FEATURES, MEANINGS as HIT_MEANINGS)

FAMILIES = ('blast_graded', 'phmmer_graded', 'local_file_source', 'native_blast_masking', 'native_blast_utility', 'api',
            'native_blast_standard_database', 'native_blast_database', 'native_hmmer_preparation', 'native_hmmer',
            'native_blast', 'native_bytes')
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
HIT_FORM = RecordForm({name: feature_field(name, rule, HIT_MEANINGS) for name, rule in HIT_FEATURES.items()})
FINDING_FORM = RecordForm({
    'execution_completed': Field('boolean', 'Whether the requested acquisition is complete: a completed attempt '
                                            'with return code 0 and every requested window covered, or a saved '
                                            'grading of the requested BLAST return'),
    'target_family': ChoiceField('text', 'The family of the original target', FAMILIES),
    'acquisitions': Field('integer', 'The number of acquisitions that completed'),
    'invalid_acquisitions': Field('integer', 'The number of selected operations that returned an invalid outcome'),
    'windows_acquired': Field('integer', 'The number of byte windows this episode retained'),
    'bytes_acquired': Field('integer', 'The number of bytes this episode retained'),
    'failure_count': Field('integer', 'The number of window failures and invalid outcomes'),
    'graded_sheets': Field('list', 'One entry per BLAST database grading this episode saved', items=SHEET_FORM),
    'profile_sheets': Field('list', 'One entry per hit of the phmmer gradings this episode saved', items=HIT_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested acquisition is complete, its counts and the controlled '
                               'features of the saved gradings', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources actually available to this '
                                    'episode, including authenticated original failed native database attempts for '
                                    'partial-output acquisition; failed attempts do not establish a successful '
                                    'endpoint', required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to '
                                   'this episode. Generic native windows retain current-filesystem observations',
                                   required=False),
    'execution_file_source_refs': Field('record_refs', 'Source references for selected local file streams actually '
                                        'retained by this results episode; no producing-execution or atomic-version '
                                        'identity is established', required=False),
    'execution_file_capture_outcomes': Field('list', 'Recorded selected-file availability, original job status and '
                                             'file-custody qualifications; successful byte retention alone does '
                                             'not establish execution success or closed writers', required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results; empty when no '
                                     'byte window was retained', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information. '
                                 'Generic native results mean requested current-filesystem acquisition plus '
                                 'independently observed successful exact execution, without a producing-attempt '
                                 'or atomic-version claim. Yielding alone is false', required=False),
    'execution_blast_graded_refs': Field('record_refs', 'The graded BLAST return: each saved '
                                         'blast_database_sheet_v1 grading artifact and the ncbi_blast source it is '
                                         'retained on', required=False),
    'execution_phmmer_graded_refs': Field('record_refs', 'The graded local phmmer return: the parsed snapshot, '
                                          'its tool-profile row, the references, each graded alignment source with '
                                          'its observation and its retained hmmer_search_sheet_v1 grading',
                                          required=False),
})


def _facts(summary):
    """The progress the summary holds; ``execution_result_origin`` is the empty record when no window was retained."""
    progress = summary['execution_progress']
    return {**progress, 'execution_result_origin': progress['execution_result_origin'] or {}}


def _finding(summary):
    own = [result for result in summary['results'] if not result['initial']]
    windows = [window for result in own for window in result['windows']]
    rows = (summary['gradings'] if summary['family'] in ('blast_graded', 'phmmer_graded')
            else summary['acquisitions'])
    invalid = sum(1 for row in rows if row['status'] != 'completed')
    return {'execution_completed': summary['execution_completed'], 'target_family': summary['family'],
            'acquisitions': sum(1 for row in rows if row['status'] == 'completed'),
            'invalid_acquisitions': invalid,
            'windows_acquired': len(windows), 'bytes_acquired': sum(window['returned_bytes'] for window in windows),
            'failure_count': sum(len(result['failures']) for result in own) + invalid,
            'graded_sheets': summary['graded_sheets'], 'profile_sheets': summary['profile_sheets']}


def final_to_parent(summary, completion, selection):
    facts = _facts(summary)
    return {'credit': completion['credit'], 'finding': _finding(summary), **{name: facts[name] for name in selection}}
