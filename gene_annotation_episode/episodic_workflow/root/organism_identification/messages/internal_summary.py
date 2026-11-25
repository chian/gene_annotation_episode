"""The internal summary: what this episode holds, as its ``decide``, ``action``, ``credit`` and ``final_to_parent`` read it.

From the system's view: the parent input (the scope), one row per unit (the tool, its arguments, the status and the facts
of its result), the records held, the sequences of the scope with their molecule and length, the classifications held
(read from their sources: the query, the index), the scoring sheet of the scope (``credit.held_table``: per sequence the
candidate taxa with their scores, the leading candidate, its rival, the taxon they share), the records to return (those
this episode committed, closed under naming) and the controller's yield table."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.taxonomic_classification.kraken2_classification import (
    PROVIDER as KRAKEN2_PROVIDER)

from ..credit import KRAKEN2_TOOL, TaxonDifferentialCredit, held_table

EXECUTED = ('completed', 'partial')
# The tools whose records this episode's credit reads and so returns: its graded classifications.
CREDITED_TOOLS = (KRAKEN2_TOOL,)
# The record types that carry a sequence: what a classification's query is chosen from.
SEQUENCE_RECORD_TYPES = ('input', 'reference', 'product')
# The facts of a classification's result a unit's row shows (the taxa themselves are in the candidate table).
RESULT_FACTS = ('index', 'index_version', 'classified', 'assigned_taxon_id', 'kmers', 'taxon_count')


def _held_classifications(records):
    """The classifications this episode holds, read from their sources: the query, the index and its version."""
    return [{'query_ref': source['operand_refs'][0], 'index': source['accession'], 'index_version': source['version'],
             'source_ref': source['id']}
            for source in records.list('source') if source['provider'] == KRAKEN2_PROVIDER]


def _candidate(row):
    return {'taxon_id': row['taxon_id'], 'name': row['name'], 'rank_code': row['rank_code'],
            'lineage': [{'taxon_id': taxon} for taxon in row['lineage_taxon_ids']], 'score': row['score']}


def _finding(target, table):
    """The finding of one sequence of the scope (``final_to_parent``)."""
    finding = {'target_ref': [target], 'candidates': [_candidate(row) for row in table['rows']],
               'candidate_count': len(table['rows']), 'test_count': len(table['tests'])}
    for name, value in (('leader_taxon_id', table['leader']), ('rival_taxon_id', table['rival']),
                        ('agreed_taxon_id', table['agreed_taxon_id'])):
        if value is not None:
            finding[name] = value
    return finding


def internal_summary(view):
    records = view.records
    parent = view.parent_input
    units, committed, last = [], [], None
    for position, outcome in enumerate(view.outcomes):
        result = outcome['outcome']
        row = {'position': position, 'kind': 'tool', 'tool': outcome['tool'], 'status': result['status'],
               'record_refs': list(result['record_refs']), 'feedback': result.get('feedback')}
        if outcome['tool'] == KRAKEN2_TOOL:
            row['classification'] = dict(outcome['arguments'])
            row['features'] = (None if result['result'] is None
                               else {name: result['result'][name] for name in RESULT_FACTS})
        if outcome['tool'] in CREDITED_TOOLS and result['status'] in EXECUTED:
            committed.extend(ref for ref in result['record_refs'] if ref not in committed)
        units.append(row)
        last = row
    held = [ref for ref in records.refs() if not ref.startswith('row_')]
    held_sequences = {ref: records.get(ref).get('molecule') for ref in held
                      if ref.split('_')[0] in SEQUENCE_RECORD_TYPES and records.get(ref).get('sequence_ref')}
    summary = {**parent, 'units': units, 'held_sequences': held_sequences,
               'held_classifications': _held_classifications(records)}
    table = held_table(summary, records)
    return {**summary,
            'path_depth': len(view.path),
            'last_local_outcome': last,
            'held_record_refs': held,
            'sequence_lengths': {ref: records.get(ref).get('length') for ref in held_sequences},
            'returned_refs': returned_with_names(records, committed),
            'credit_binding': TaxonDifferentialCredit().as_record(),
            'target_findings': [_finding(target, table['targets'][target]) for target in parent['scope']['subject_refs']],
            'tests': [{'target_ref': target, 'test': test, 'credit': held['test_credits'][test]}
                      for target, held in table['targets'].items() for test in held['tests']],
            'differentials': [{'target_ref': target, **row} for target, held in table['targets'].items()
                              for row in held['differentials']],
            'units_consumed': view.units_consumed,
            'action_yields': (None if view.controller_state is None
                              else yield_table(view.controller_state, forecast_unit='taxon_credit'))}
