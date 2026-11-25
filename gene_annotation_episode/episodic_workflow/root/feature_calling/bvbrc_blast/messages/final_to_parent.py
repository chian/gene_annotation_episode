"""The return: controlled data only; no path and no text. EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING: ``internal_summary`` builds each with ``job_records.returned_with_names`` (the records the child returns together with everything they name among the records it holds), so the parent holds what the returned records name and nothing private is named (the summary is where the closing runs: ``final_to_parent`` receives no reader). Always: ``credit`` and the ``finding``: the state of the search
(``no_estimate``, ``estimated``, ``launched``, ``finished``, ``extracted`` or ``failed``), the hit count of the graded
sheet, the controlled identification features the database feature reader gives
(``blast_database_features.grading_features``: the sheet's counts, the smallest native E-value and one row per explicit
function; a feature the sheet leaves without a value is absent), the estimated and observed seconds of the search (as of
its latest status request), how far past the estimate that is, and the last failure code (a fixed vocabulary; absent when
none). Selectable: ``execution_handoff_refs`` (the handoff records), ``check_refs`` (the status records),
``closure_refs`` (the closure records of the fetch) and ``graded_refs`` (the graded records: the source, the grading
artifact, the search row, the report data product (``sequence_search_results``), the hit references and the comparison observations)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    FUNCTION_FEATURES, FUNCTION_MEANINGS, MEANINGS, SHEET_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    ESTIMATE_BASES, FAILURE_CODES, STATES)

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
    'state': ChoiceField('text', 'The search: no_estimate, estimated (an estimate held, nothing launched), launched '
                                 '(accepted, not finished), finished (the service finished it; not yet extracted), '
                                 'extracted (graded) or failed', STATES),
    'hit_count': Field('integer', 'The hits of the graded sheet', required=False),
    'claim_count': Field('integer', 'The claims the hits make about the features of the sequence, kept with the graded '
                                    'records', required=False),
    'identification': Field('record', 'The controlled identification features of the graded sheet', required=False,
                            form=IDENTIFICATION_FORM),
    'metadata_hit_count': Field('integer', 'The hits of the report that the data service was asked about', required=False),
    'metadata_covered_count': Field('integer', 'The hits whose feature the data service described (a hit without it is '
                                               'missing, not a hit with no function)', required=False),
    'named_hit_count': Field('integer', 'The hits whose names were asked of the data service, in the order of their value '
                             'in the search, in batches of 100', required=False),
    'not_asked_hit_count': Field('integer', 'The hits never asked about (the naming stopped): not asked, which is not '
                                            'asked-and-missing', required=False),
    'naming_batch_count': Field('integer', 'The batches of 100 hits named', required=False),
    'naming_stopped': ChoiceField('text', 'Why the naming stopped: settled (a batch admitted no new product and moved no '
                                          'candidate\'s score by more than 0.01) or all_named', ('settled', 'all_named'),
                                  required=False),
    'data_request_count': Field('integer', 'The requests made to the data service for the names of the hits',
                                required=False),
    'parked': Field('boolean', 'The search is launched and not extracted: this child parked, and the parent is shown the '
                               'wait notice (seconds since the launch, estimated seconds, expected remaining seconds)',
                    required=False),
    'seconds_since_launch': Field('number', 'The seconds from the launch to the latest thing the child knew (the launch or '
                                            'its latest status request)', required=False),
    'expected_remaining_seconds': Field('number', 'The seconds still expected: the estimate minus the seconds since the '
                                                  'launch (not below zero), or the revised remaining seconds a status '
                                                  'request came with, the later fact', required=False),
    'estimated_seconds': Field('number', 'The seconds the search was expected to take, as estimated before the launch',
                               required=False),
    'estimate_basis': ChoiceField('text', 'What the estimate rested on', ESTIMATE_BASES, required=False),
    'observed_seconds': Field('number', 'The seconds from the launch to the latest status request', required=False),
    'seconds_past_estimate': Field('number', 'The observed seconds minus the estimated seconds (negative: before the '
                                             'estimate)', required=False),
    'last_failure_code': ChoiceField('text', 'The failure code of the last failure', FAILURE_CODES, required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the search and its controlled facts', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff records of the searches launched', required=False),
    'check_refs': Field('record_refs', 'The status records of the search', required=False),
    'closure_refs': Field('record_refs', 'The closure record of the fetched report', required=False),
    'graded_refs': Field('record_refs', 'The graded records: the source, the grading artifact, the search row, the report data product, the hit '
                                        'references and the comparison observations', required=False),
})


def final_to_parent(summary, completion, selection):
    search = summary['search']
    finding = {'state': summary['state']}
    if summary['graded']:
        graded = summary['graded'][-1]
        finding['hit_count'] = graded['hit_count']
        finding['identification'] = {name: value for name, value in graded['features'].items()
                                     if name not in ('sheet_refs',)}
    if summary['metadata']:
        counts = summary['metadata'][-1]
        finding.update(metadata_hit_count=counts['metadata_hit_count'],
                       metadata_covered_count=counts['metadata_covered_count'],
                       data_request_count=counts['metadata_request_count'], named_hit_count=counts['named_hit_count'],
                       not_asked_hit_count=counts['not_asked_hit_count'], naming_batch_count=counts['naming_batch_count'],
                       naming_stopped=counts['naming_stopped'])
    if summary['claim_counts']:
        finding['claim_count'] = summary['claim_counts'][-1]
    if summary['notice'] is not None:
        finding.update(parked=True, seconds_since_launch=summary['notice']['seconds_since_launch'],
                       expected_remaining_seconds=summary['notice']['expected_remaining_seconds'])
    if search is not None:
        if search['predicted_seconds'] is not None:
            finding['estimated_seconds'] = search['predicted_seconds']
            finding['estimate_basis'] = search['prediction_basis']
        if search['latest_check'] is not None:
            observed = search['latest_check']['observed_seconds']
            finding['observed_seconds'] = observed
            if search['predicted_seconds'] is not None:
                finding['seconds_past_estimate'] = observed - search['predicted_seconds']
    if summary['last_failure_code'] is not None:
        finding['last_failure_code'] = summary['last_failure_code']
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'check_refs': list(summary['check_refs']),
             'closure_refs': list(summary['closure_refs']), 'graded_refs': list(summary['graded_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
