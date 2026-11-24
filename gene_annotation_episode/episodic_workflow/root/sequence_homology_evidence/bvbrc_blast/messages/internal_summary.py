"""Where the search stands, as a pure function of the view: the commission (the parent input); the query read from the
held records (its sequence artifact, molecule and length); one row per completed unit (its action, status, failure code,
whether it can be retried, and what the action added: the estimate, the request, the state a status request showed, the
fix); the state the units give (``bvbrc_blast_search.episode_state``: the held estimate, the request, the failure waiting
for its fix); the latest search held (its handoff and check rows) with its latest check and the estimate recorded with
its launch; the graded result with the controlled features of the feature reader; and the yield table. The seconds
since the launch are not here (the summary reads no clock): ``decide`` computes them from the recorded decision time and
``final_to_parent`` returns the duration observed at the latest check."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    episode_state, graded_rows, resumed_rows, search_facts, search_notice, search_view)


def _unit(position, unit):
    outcome = unit['outcome']
    row = {'position': position, 'action': unit['tool'], 'status': outcome['status'],
           'failure_code': outcome.get('failure_code'), 'retryable': outcome.get('retryable', False)}
    if outcome['status'] == 'completed':
        if unit['tool'] == 'estimate':
            row['estimate'] = outcome['estimate']
        elif unit['tool'] == 'monitor':
            row.update(state=outcome['state'], result_available=outcome['result_available'],
                       waited_seconds=outcome['waited_seconds'],
                       expected_remaining_seconds=outcome['expected_remaining_seconds'])
        elif unit['tool'] == 'fix':
            row['fix'] = outcome['fix']
    if unit['tool'] == 'launch':
        row['request'] = outcome['request']
    return row


def internal_summary(view):
    parent, records = view.parent_input, view.records
    query_ref = parent['query_ref']
    record = records.get(query_ref)
    sequence = records.get_artifact(record['sequence_ref'])
    rows = [_unit(position, unit) for position, unit in enumerate(view.outcomes)]
    search, graded = search_view(records), graded_rows(records)
    resumed = resumed_rows(search) if parent['resumed'] else []
    facts = episode_state([*resumed, *rows])
    revised = [row['expected_remaining_seconds'] for unit, row in zip(view.outcomes, rows)
               if unit['tool'] == 'monitor' and row['status'] == 'completed' and row['state'] not in ('finished', 'failed', 'unknown')]
    return {'fields': parent['fields'], 'units': parent['units'], 'until': parent['until'], 'prior': parent['prior'],
            'resumed': parent['resumed'], 'known_ended': parent['known_ended'], 'target': parent['target'],
            'notice': (search_notice(search_facts(search), revised[-1] if revised else None)
                       if search is not None and facts['state'] in ('launched', 'finished') else None),
            'query': {'subject_ref': query_ref, 'sequence_ref': record['sequence_ref'],
                      'molecule': record.get('molecule'), 'length': len(sequence)},
            'unit_rows': rows, 'state_facts': facts, 'state': facts['state'],
            'last_failure_code': facts['last_failure_code'], 'search': search_facts(search), 'graded': graded,
            'metadata': [{name: unit['outcome'][name] for name in ('metadata_covered_count', 'metadata_hit_count',
                                                                    'metadata_request_count', 'named_hit_count',
                                                                    'not_asked_hit_count', 'naming_batch_count',
                                                                    'naming_stopped')}
                         for unit in view.outcomes if unit['tool'] == 'extract' and unit['outcome']['status'] == 'completed'],
            'handoff_refs': returned_with_names(records, [ref for unit in view.outcomes if unit['tool'] == 'launch'
                                                          for ref in unit['outcome']['handoff_refs']]),
            'check_refs': returned_with_names(records, [unit['outcome']['check_ref'] for unit in view.outcomes
                                                        if unit['tool'] == 'monitor' and unit['outcome']['status'] == 'completed']),
            'closure_refs': returned_with_names(records, [unit['outcome']['closure_ref'] for unit in view.outcomes
                                                          if unit['tool'] == 'extract' and unit['outcome']['closure_ref'] is not None]),
            'graded_refs': returned_with_names(records, [ref for unit in view.outcomes if unit['tool'] == 'extract'
                                                         for ref in unit['outcome'].get('graded_refs', [])]),
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='bvbrc_blast_credit'))}
