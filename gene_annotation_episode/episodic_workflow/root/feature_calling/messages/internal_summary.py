"""The internal summary: what this episode holds, as its ``decide``, ``action``, ``credit`` and ``final_to_parent`` read it.

From the system's view: the parent input (the scope and the information given with it), one row per unit (a commission
of the search child: its arguments, the state the child returned, its credit, whether it came back with the search still
running; or a run of a tool: its arguments and status), the Prodigal runs and the cmscan runs held (``gene_findings``,
``rna_scans``: what their checks refuse to run again), the records held, the sequences held with their letters and length (the query of the run and any sequence
derived from it), the searches sent (read from their job records: the searched sequence, program, database, state, and
whether still running), the feature records given with the commission (``given_features``: what already existed, each
with its kind, positions and strand), the sheet of the scope (``credit.held_table``: per sequence the candidate feature
calls with their scores and their rivals, and the claims that wait for one), the records to return (those this episode
committed, closed under naming) and the controller's yield table."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import named_records, returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_blast_search as bvbrc)

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.prodigal_calls import (
    SHEET as PRODIGAL_CALL_SHEET)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.prodigal_gene_calls import (
    PROVIDER as PRODIGAL_PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.rna_family_scan import (
    rna_scan_inputs)

from ..credit import FeatureDifferentialCredit, held_table

# The record types that carry a sequence: what a test can be run on.
SEQUENCE_RECORD_TYPES = ('input', 'reference', 'product')
FEATURE_FACTS = ('kind', 'strand', 'segments', 'start', 'end', 'versions', 'score', 'claim_count', 'rivals',
                 'feature_refs')


def _feature(row):
    return {name: row[name] for name in FEATURE_FACTS}


def _finding(target, table):
    """The finding of one sequence of the scope (``final_to_parent``): its feature calls and its waiting claims."""
    finding = {'target_ref': [target], 'features': [_feature(row) for row in table['rows']],
               'feature_count': len(table['rows']), 'waiting_claims': table['waiting'],
               'waiting_claim_count': len(table['waiting']), 'test_count': len(table['tests'])}
    if table['rival_rank'] is not None:
        finding['rival_rank'] = table['rival_rank']
    return finding


def _given_features(records, parent):
    """The feature records the commissioner gave that are of a sequence of the scope."""
    rows = []
    for ref in parent['evidence_refs']:
        if ref.split('_')[0] != 'feature':
            continue
        record = records.get(ref)
        if record['subject_ref'] in parent['scope']['subject_refs']:
            rows.append({'feature_ref': ref, 'target_ref': record['subject_ref'], 'kind': record['kind'],
                         'strand': record['strand'], 'segments': record['segments']})
    return rows


def _gene_findings(records):
    """The Prodigal runs this episode holds, read from their kept call sheets: the searched sequence, the genetic code,
    the mode and the number of genes."""
    rows = []
    for source in records.list('source'):
        if source['provider'] != PRODIGAL_PROVIDER:
            continue
        for entry in source_tool_grading_entries(records, source['id']):
            sheet = entry['grading']['sheet']
            if sheet['schema'] == PRODIGAL_CALL_SHEET:
                rows.append({'searched_ref': sheet['searched_ref'], 'code': sheet['code'], 'mode': sheet['mode'],
                             'gene_count': sheet['gene_count']})
    return rows


def _rna_scans(records):
    """The cmscan runs this episode holds, read from their kept scan sheets: the searched sequence and the database."""
    return [{'searched_ref': scan['query_ref'], 'database': scan['database']}
            for scan in rna_scan_inputs(records).values()]


def internal_summary(view):
    records = view.records
    parent = view.parent_input
    units, committed, last = [], [], None
    for position, outcome in enumerate(view.outcomes):
        if outcome['kind'] == 'tool':
            result = outcome['outcome']
            row = {'position': position, 'kind': 'tool', 'tool': outcome['tool'], 'status': result['status'],
                   'arguments': dict(outcome['arguments']), 'record_refs': list(result['record_refs'])}
            if result['status'] == 'completed':
                committed.extend(ref for ref in result['record_refs'] if ref not in committed)
        else:
            report = outcome['report']
            row = {'position': position, 'kind': 'child', 'slot': outcome['slot'], 'status': 'completed',
                   'arguments': outcome['arguments'], 'child_state': report['finding']['state'],
                   'hit_count': report['finding'].get('hit_count'), 'claim_count': report['finding'].get('claim_count'),
                   'credit': report['credit'], 'record_refs': list(report['record_refs']),
                   # the child came back with its search launched and not extracted: the unit's outcome is pending
                   'parked': report['finding'].get('parked') is True}
            committed.extend(ref for ref in report['graded_refs'] if ref not in committed)
        units.append(row)
        last = row
    held = [ref for ref in records.refs() if not ref.startswith('row_')]
    held_sequences = {ref: records.get(ref).get('molecule') for ref in held
                      if ref.split('_')[0] in SEQUENCE_RECORD_TYPES and records.get(ref).get('sequence_ref')}
    summary = {**parent, 'units': units}
    table = held_table(summary, records)
    return {**summary,
            'path_depth': len(view.path),
            'last_local_outcome': last,
            'held_record_refs': held,
            'held_sequences': held_sequences,
            'sequence_lengths': {ref: records.get(ref).get('length') for ref in held_sequences},
            'searches': bvbrc.held_searches(records, {ref: records.get(ref)['sequence_ref'] for ref in held_sequences},
                                            searched_types=SEQUENCE_RECORD_TYPES),
            'named_refs': {ref: named_records(records, ref) for ref in records.refs()},
            'gene_findings': _gene_findings(records), 'rna_scans': _rna_scans(records),
            # per sequence, the readings of the whole sequence held (its genetic code) with each value's support
            'held_readings': {target: held['readings'] for target, held in table['targets'].items()},
            'set_aside_tests': [test for held in table['targets'].values() for test in held['set_aside']],
            'given_features': _given_features(records, parent),
            'returned_refs': returned_with_names(records, committed),
            'credit_binding': FeatureDifferentialCredit().as_record(),
            'target_findings': [_finding(target, table['targets'][target]) for target in parent['scope']['subject_refs']],
            'tests': [{'target_ref': target, 'test': test, 'credit': held['test_credits'][test]}
                      for target, held in table['targets'].items() for test in held['tests']],
            'differentials': [{'target_ref': target, **row} for target, held in table['targets'].items()
                              for row in held['differentials']],
            'units_consumed': view.units_consumed,
            'action_yields': (None if view.controller_state is None
                              else yield_table(view.controller_state, forecast_unit='feature_credit'))}
