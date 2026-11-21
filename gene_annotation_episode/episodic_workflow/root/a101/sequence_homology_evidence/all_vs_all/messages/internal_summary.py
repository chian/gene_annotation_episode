"""Where the all-vs-all stands, as a pure function of the view: the commission (the parent input); the planned set (the members
the held search gives, ``all_vs_all_run.set_members``); one row per completed unit; the data products the episode holds (the set,
the database, the matrix, the clusters); the failed steps (what the checks refuse to run again); the committed clustering (the
source of provider ``all_vs_all`` with its sheet's facts: the cluster count, the target's cluster size and each candidate's share
of its sequences in it); the state; and the yield table. The returned record lists are closed under naming by
``job_records.returned_with_names`` (the records the child returns together with everything they name among the records it
holds), so the parent holds what the returned records name."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    all_vs_all_run as run)

KINDS = (run.SET_KIND, run.DATABASE_KIND, run.MATRIX_KIND, run.CLUSTERS_KIND)


def _clusterings(records):
    found = []
    for source in records.list('source'):
        if source['provider'] != run.PROVIDER:
            continue
        (entry,) = source_tool_grading_entries(records, source['id'])
        sheet = entry['grading']['sheet']
        found.append({'source_ref': source['id'], 'method': sheet['method'], 'inflation': sheet['parameters']['inflation'],
                      'contrast': sheet['parameters']['contrast'],
                      'cluster_count': sheet['set']['cluster_count'], 'target_cluster_size': sheet['target_cluster']['size'],
                      'groups': [{key: row[key] for key in ('candidate', 'size', 'in_target_cluster', 'share')}
                                 for row in sheet['groups']]})
    return found


def _rows(outcomes):
    rows = []
    for position, unit in enumerate(outcomes):
        outcome = unit['outcome']
        row = {'position': position, 'action': unit['tool'], 'status': outcome['status'],
               'failure_code': outcome['failure_code'], 'retryable': outcome['retryable']}
        if unit['tool'] == 'hold':
            row['reason'] = outcome['reason']
        else:
            row['call'] = unit['arguments']['call']
        rows.append(row)
    return rows


def internal_summary(view):
    parent, records = view.parent_input, view.records
    commission = {key: parent[key] for key in ('query_ref', 'search_ref', 'candidates', 'per_candidate')}
    members = run.set_members(records, commission, parent['per_candidate'])
    rows = _rows(view.outcomes)
    held = [row for row in products(records) if row['kind'] in KINDS]
    clusterings = _clusterings(records)
    failed = {'prepare': any(row['action'] == 'prepare_database' and row['status'] == 'failed' for row in rows),
              'blast': any(row['action'] == 'all_vs_all_blast' and row['status'] == 'failed' for row in rows),
              'cluster': [[row['call']['matrix_ref'], row['call']['inflation'], row['call']['contrast']] for row in rows
                          if row['action'] == 'cluster' and row['status'] == 'failed']}
    outcomes = [unit['outcome'] for unit in view.outcomes]
    tries = [{'clusters_ref': outcome['clusters_ref'], **unit['arguments']['call'], 'same_as_held': outcome['same_as_held'],
              **outcome['facts']} for unit, outcome in zip(view.outcomes, outcomes)
             if unit['tool'] == 'cluster' and outcome['status'] == 'completed']
    kinds = {row['kind'] for row in held}
    state = ('clustered' if clusterings else 'tried' if run.CLUSTERS_KIND in kinds else 'matrix_ready' if run.MATRIX_KIND in kinds
             else 'database_ready' if run.DATABASE_KIND in kinds else 'nothing_done')
    codes = [row['failure_code'] for row in rows if row['failure_code'] is not None]
    return {'commission': commission, 'units': parent['units'], 'target': parent['target'],
            'planned': {'sequences': len(members), 'letters': sum(row['length'] for row in members),
                        'per_candidate': parent['per_candidate'],
                        'by_candidate': {name: sum(1 for row in members if row['candidate'] == name)
                                         for name in parent['candidates']}},
            'unit_rows': rows, 'state': state, 'failed': failed, 'last_failure_code': codes[-1] if codes else None,
            'products': [{'row_ref': row['id'], 'kind': row['kind'], 'edam_data': row['edam_data'],
                          'edam_format': row['edam_format'], 'settings': row['settings']} for row in held],
            'tries': tries, 'tried': [[row['call']['matrix_ref'], row['call']['inflation'], row['call']['contrast']] for row in rows
                                      if row['action'] == 'cluster' and row['status'] in ('completed', 'failed')],
            'committed': bool(clusterings), 'set_ids': [row['id'] for row in members], 'clusterings': clusterings,
            'matrix': [{'pair_count': outcome['pair_count']} for outcome in outcomes if 'pair_count' in outcome],
            'handoff_refs': returned_with_names(records, [ref for outcome in outcomes for ref in outcome['handoff_refs']]),
            'closure_refs': returned_with_names(records, [ref for outcome in outcomes for ref in outcome['closure_refs']]),
            'graded_refs': returned_with_names(records, [ref for outcome in outcomes for ref in outcome['graded_refs']]),
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='all_vs_all_credit'))}
