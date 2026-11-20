"""Where the preparation stands, as a pure function of the view: the commission (the parent input); the facts code
counted about the input set (``describe_fasta``: sequences and letters, and its bytes); each unit's status, failure
code and whether it can be retried; the prepared-data records the episode holds (the ones the parent passed and the
ones it wrote) with their controlled features; and the yield table."""
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    describe_fasta)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.prepared_data import (
    prepared_features, prepared_rows)


def internal_summary(view):
    parent = view.parent_input
    fields = parent['fields']
    data = view.records.get_artifact(fields['input_ref'])
    counts = describe_fasta(data, molecule=fields['molecule'], parse_seqids=fields.get('parse_seqids', False))
    units = []
    for position, unit in enumerate(view.outcomes):
        outcome = unit['outcome']
        if unit['tool'] == 'hold':
            units.append({'position': position, 'action': 'hold', 'status': 'held', 'reason': outcome['reason'],
                          'failure_code': None, 'retryable': False})
        else:
            units.append({'position': position, 'action': 'launch_local', 'status': outcome['status'],
                          'resource_id': unit['arguments']['resource_id'], 'failure_code': outcome['failure_code'],
                          'retryable': outcome['retryable'], 'prepared_ref': outcome['prepared_ref']})
    held = prepared_rows(view.records)
    prior = {view.records.get(ref)['data_key'] for ref in parent['prior_prepared_refs']}
    controller = view.controller_state
    return {'fields': fields, 'prepared_unit': parent['prepared_unit'],
            'prior_prepared_refs': parent['prior_prepared_refs'], 'prior_data_keys': sorted(prior),
            'input': {'bytes': len(data), 'sequences': counts['records'], 'letters': counts['residues']},
            'units': units,
            'prepared': [{'ref': row['id'], 'passed_by_parent': row['id'] in parent['prior_prepared_refs'],
                          'features': prepared_features(row), 'failure_codes': row['failure_codes']}
                         for row in held],
            'prepared_refs': [row['id'] for row in held if row['usable'] and row['data_key'] not in prior],
            'yield_table': (None if controller is None
                            else yield_table(controller, forecast_unit='prepared_data_credit'))}
