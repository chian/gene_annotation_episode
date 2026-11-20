"""The return: controlled data only; no path and no text. Always: ``credit`` and the ``finding``: the state of the
search (``not_submitted``, ``outstanding``, ``finished``, ``graded`` or ``failed``), the hit count of the graded sheet,
the controlled identification features the database feature reader gives (``blast_database_features.grading_features``:
the sheet's counts, the smallest native E-value and one row per explicit function; a feature the sheet leaves without a
value is absent), the predicted, the service-estimated and the observed seconds of the search (as of its latest status
request) and the last failure code (a fixed vocabulary; absent when none). Selectable: ``execution_handoff_refs`` (the
handoff record), ``check_refs`` (the status records), ``closure_refs`` (the closure record of the fetch) and
``graded_refs`` (the graded records: the source, the grading artifact and the search row), which the parent holds and
passes back on a later visit."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    FUNCTION_FEATURES, FUNCTION_MEANINGS, MEANINGS, SHEET_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    FAILURE_CODES, STATES)

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean', 'text': 'text'}


def feature_field(name, rule, meanings):
    if rule[0] == 'choice':
        return ChoiceField('text', meanings[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], meanings[name], required=rule[-1] != 'optional')


FUNCTION_FORM = RecordForm({name: feature_field(name, rule, FUNCTION_MEANINGS)
                            for name, rule in FUNCTION_FEATURES.items()})
IDENTIFICATION_FORM = RecordForm({
    **{name: feature_field(name, rule, MEANINGS) for name, rule in SHEET_FEATURES.items() if rule[0] != 'ref'},
    'functions': Field('list', MEANINGS['functions'], items=FUNCTION_FORM)})
FINDING_FORM = RecordForm({
    'state': ChoiceField('text', 'The search: not_submitted, outstanding (accepted, not finished), finished (the '
                                 'service finished it; not yet graded), graded or failed', STATES),
    'hit_count': Field('integer', 'The hits of the graded sheet', required=False),
    'identification': Field('record', 'The controlled identification features of the graded sheet', required=False,
                            form=IDENTIFICATION_FORM),
    'predicted_seconds': Field('number', 'The seconds the search was predicted to take, from the measured durations '
                                         'of earlier searches of its kind (absent when none was measured)',
                               required=False),
    'service_estimate_seconds': Field('number', 'The seconds the service estimated for the search when it accepted it',
                                      required=False),
    'observed_seconds': Field('number', 'The seconds from the submission to the latest status request', required=False),
    'seconds_past_prediction': Field('number', 'The observed seconds minus the predicted seconds (negative: before '
                                               'the prediction)', required=False),
    'last_failure_code': ChoiceField('text', 'The failure code of the last failure', FAILURE_CODES, required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the search and its controlled facts', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff record of the search', required=False),
    'check_refs': Field('record_refs', 'The status records of the search', required=False),
    'closure_refs': Field('record_refs', 'The closure record of the fetched report', required=False),
    'graded_refs': Field('record_refs', 'The graded records: the source, the grading artifact and the search row',
                         required=False),
})


def final_to_parent(summary, completion, selection):
    search = summary['search']
    finding = {'state': summary['state']}
    if summary['graded']:
        graded = summary['graded'][-1]
        finding['hit_count'] = graded['hit_count']
        finding['identification'] = {name: value for name, value in graded['features'].items()
                                     if name not in ('sheet_refs',)}
    if search is not None:
        if search['predicted_seconds'] is not None:
            finding['predicted_seconds'] = search['predicted_seconds']
        if search['service_estimate_seconds'] is not None:
            finding['service_estimate_seconds'] = search['service_estimate_seconds']
        if search['latest_check'] is not None:
            observed = search['latest_check']['observed_seconds']
            finding['observed_seconds'] = observed
            if search['predicted_seconds'] is not None:
                finding['seconds_past_prediction'] = observed - search['predicted_seconds']
    if summary['last_failure_code'] is not None:
        finding['last_failure_code'] = summary['last_failure_code']
    facts = {'execution_handoff_refs': [] if search is None else [search['handoff_ref']],
             'check_refs': [] if search is None else list(search['check_refs']),
             'closure_refs': [] if search is None or search['closure_ref'] is None else [search['closure_ref']],
             'graded_refs': list(summary['graded_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
