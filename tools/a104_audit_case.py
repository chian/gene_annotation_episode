"""Audit actual A104 returns, parent receipts and original native executions.

This reads real run records. It launches no model or biological algorithm and
does not grade, populate evidence or complete an unfinished research episode.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.state import Store
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.a104_credit import A104EvolutionaryCredit
from gene_annotation_episode.a104_hpc import native_body
from gene_annotation_episode.evidence_root import NativeEvidenceRootCredit


def audit(case):
    prepared = json.loads((case/'PREPARED.json').read_text())
    run_id = 'a104-science-'+case.parent.name
    with Store(case/'state') as store:
        receipts = EpisodeReceipts(store, run_id)
        roots = [row for row in store.db.execute('SELECT episode_id,path,state FROM runtime_episodes WHERE run_id=?',
            (run_id,)) if json.loads(row['path']) == [['annotation', 'root']]]
        if len(roots) != 1:
            raise ValueError('a104_original_annotation_parent_required')
        parent = roots[0]
        known = set(receipts.known(parent['episode_id']))
        before = store.db.total_changes
        root_credit = NativeEvidenceRootCredit().read_details(store, prepared['scope'], known_record_refs=known,
            details_limit=128, details_offset=0)
        axis = A104EvolutionaryCredit().read_details(store, prepared['scope'], known_record_refs=known,
            details_limit=128, details_offset=0)
        reports = []
        for row in store.db.execute('SELECT a.*,e.request,e.path,e.state FROM runtime_report_attempts a '
                'JOIN runtime_episodes e ON e.run_id=a.run_id AND e.episode_id=a.child_episode_id '
                'WHERE a.run_id=? AND a.form IS NOT NULL ORDER BY a.rowid', (run_id,)):
            request = json.loads(row['request'])
            assignment = request['message'].get('episode_assignment', {})
            if assignment.get('selection', {}).get('evidence_axis', {}).get('option_id') != 'A104':
                continue
            form = json.loads(row['form'])
            if 'phylogenetic_credit' not in form or 'records' not in form:
                continue
            child_scope = request['message']['scope']
            returned = set(form['records'])
            receiver_known = set(receipts.known(row['parent_episode_id']))
            owner_credit = A104EvolutionaryCredit()(store, child_scope,
                known_record_refs=receipts.known(row['child_episode_id']))['credit']
            transferred = A104EvolutionaryCredit()(store, child_scope, known_record_refs=returned & receiver_known)['credit']
            reported = form['phylogenetic_credit']
            reports.append({'episode_id': row['child_episode_id'], 'state': row['state'],
                'decision_index': row['decision_index'],
                'parent_episode_id': row['parent_episode_id'], 'reported_credit': reported,
                'owner_current_credit': owner_credit, 'receiver_credit_from_returned_records': transferred,
                'all_returned_records_received': returned <= receiver_known,
                'reported_receipt_credit_agreement': math.isclose(reported, transferred, abs_tol=1e-12),
                'interpretation': {key: form[key] for key in ('phylogeny_status', 'function_scope',
                    'history_interpretation', 'limitations') if key in form}})
        native = []
        for reference in sorted(known):
            body = native_body(store, reference)
            if body is None:
                continue
            result = body['result']
            native.append({'native_ref': reference, 'pbs_job_id': body['pbs_job_id'],
                'hpc_result_ref': body['hpc_result_ref'],
                'request_sha256': body['request_sha256'], 'result_sha256': body['result_sha256'],
                'worker_sha256': result['worker_sha256'], 'completed': result['completed'],
                'compute_hostname': result['compute_hostname'], 'elapsed_seconds': result['elapsed_seconds'],
                'native_children_peak_rss_kib': result['native_children_peak_rss_kib'],
                'analyses': [{'name': item['name'], 'purpose': item['purpose'],
                    'bootstrap_replicates': item['bootstrap_population']['usable_replicates'],
                    'tip_count': len(next(row['members'] for row in body['bindings']
                                         if row['name'] == item['name']))} for item in result['analyses']]})
        if store.db.total_changes != before:
            raise ValueError('a104_credit_audit_must_not_populate_or_grade')
        continuation = []
        for row in store.db.execute('SELECT episode_id,path,state FROM runtime_episodes WHERE run_id=?', (run_id,)):
            path = json.loads(row['path'])
            if path != [['annotation', 'root']] and path[-1][0] != 'scientific_process':
                continue
            observations = [json.loads(item[0]) for item in store.db.execute(
                'SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index',
                (run_id, row['episode_id']))]
            continuation.append({'episode_id': row['episode_id'], 'path': path, 'state': row['state'],
                'completed_acquisitions': len(observations),
                'zero_marginal_credit_acquisitions': sum(item['step']['marginal_credit'] == 0 for item in observations),
                'final_numerical_decision': observations[-1]['step']['decision'] if observations else None})
        return {'case': prepared['case_id'], 'run_id': run_id, 'annotation_parent_state': parent['state'],
            'a104_credit': axis['credit'], 'root_credit': root_credit['credit'],
            'root_axis_components': root_credit['axis_components'], 'target_sheets': axis['target_sheets'],
            'scientific_returns': reports, 'native_executions': native,
            'continuation_trace': continuation,
            'audit_is_pure_read': True, 'no_unfinished_episode_completed_by_audit': True}


if __name__ == '__main__':
    run = Path(active_budget()['run_directory'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-directory', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.case_directory.resolve())
    (run/'A104_AUDIT.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
