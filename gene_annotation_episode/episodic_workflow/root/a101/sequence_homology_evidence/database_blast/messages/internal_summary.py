"""Where the search stands, as a pure function of the view: the commission (the parent input); the query read from the
held records (its sequence artifact, molecule and length); each unit's status, failure code and whether it can be
retried; the one search held (its handoff and check rows, as the parent passed them back or this episode wrote them)
with its latest check, the prediction recorded with its submission and the service's own estimate; the graded result with
the controlled features of the feature reader; the state of the search from the fixed vocabulary; and the yield table.
The seconds since the submission are not here (the summary reads no clock): ``decide`` computes them from the recorded
decision time and ``final_to_parent`` returns the duration observed at the latest check."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    graded_rows, search_facts, search_state, search_view)


def _unit(position, unit):
    outcome = unit['outcome']
    if unit['tool'] == 'hold':
        return {'position': position, 'action': 'hold', 'status': 'held', 'reason': outcome['reason'],
                'failure_code': None, 'retryable': False}
    row = {'position': position, 'action': unit['tool'], 'status': outcome['status'],
           'failure_code': outcome['failure_code'], 'retryable': outcome['retryable']}
    if unit['tool'] == 'check' and outcome['status'] == 'completed':
        row.update(state=outcome['state'], result_available=outcome['result_available'],
                   waited_seconds=outcome['waited_seconds'])
    return row


def internal_summary(view):
    parent, records = view.parent_input, view.records
    query_ref = parent['query_ref']
    record = records.get(query_ref)
    sequence = records.get_artifact(record['sequence_ref'])
    units = [_unit(position, unit) for position, unit in enumerate(view.outcomes)]
    failures = [[unit['failure_code'], unit['retryable']] for unit in units if unit['status'] == 'failed']
    search, graded = search_view(records), graded_rows(records)
    state, last_failure = search_state(search, graded, [tuple(item) for item in failures])
    summary = {'fields': parent['fields'], 'units': parent['units'], 'prior': parent['prior'],
               'query': {'subject_ref': query_ref, 'sequence_ref': record['sequence_ref'],
                         'molecule': record.get('molecule'), 'length': len(sequence)},
               'unit_rows': units, 'failures': failures, 'state': state, 'last_failure_code': last_failure,
               'search': None, 'graded': graded,
               'graded_refs': [*parent['prior']['graded_refs'],
                               *[ref for unit in view.outcomes if unit['tool'] == 'fetch_and_grade'
                                 for ref in unit['outcome'].get('graded_refs', [])]],
               'yield_table': (None if view.controller_state is None
                               else yield_table(view.controller_state, forecast_unit='database_blast_credit'))}
    summary['search'] = search_facts(search)
    return summary
