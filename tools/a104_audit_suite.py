"""Read completed A104 returns and original native accounting sequentially.

Annotation parents can remain checkpointed for broader investigations. This
audit completes no episode, invokes no grader and creates no evidence.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3

from gene_annotation_episode.workflow_budget import active_budget
from tools.a104_audit_case import audit


def accounting(path, native):
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
        rows = [{'id': row[0], 'kind': row[1], 'body': json.loads(row[2])} for row in
                db.execute('SELECT id,kind,body FROM evidence ORDER BY recorded,rowid')]
    handoffs = [row['body'] for row in rows if row['kind'] == 'handoff'
                and row['body']['job_id'] == native['pbs_job_id']]
    if len(handoffs) != 1:
        raise ValueError('a104_audit_requires_original_native_job_handoff')
    plan_id = handoffs[0]['plan_id']
    results = [row for row in rows if row['kind'] == 'result'
               and row['body']['source_ref'] == native['hpc_result_ref'] and row['body']['plan_id'] == plan_id]
    measured = [row for row in rows if row['kind'] == 'measured' and row['body']['plan_id'] == plan_id]
    if len(results) != 1 or not measured or not measured[-1]['body']['success']:
        raise ValueError('a104_audit_requires_original_successful_collection_and_accounting')
    return {'pbs_job_id': native['pbs_job_id'], 'plan_id': plan_id, 'measurement_ref': measured[-1]['id'],
            'metrics': measured[-1]['body']['metrics'], 'original_ledger': str(path.resolve())}


def main():
    run = Path(active_budget()['run_directory'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, nargs='+', required=True)
    parser.add_argument('--ledgers', type=Path, nargs='+', required=True)
    args = parser.parse_args()
    if len(args.cases) != len(args.ledgers):
        parser.error('Each case requires its original native ledger.')
    results = []
    for case, ledger in zip(args.cases, args.ledgers):
        result = audit(case.resolve())
        returns = result['scientific_returns']
        if not returns or not all(row['state'] == 'yielded' and row['all_returned_records_received']
                and row['reported_receipt_credit_agreement']
                and math.isclose(row['reported_credit'], row['owner_current_credit'], abs_tol=1e-12)
                for row in returns):
            raise ValueError('a104_audit_return_owner_receiver_disagreement:'+result['case'])
        if len(result['native_executions']) != 1 or not result['native_executions'][0]['completed']:
            raise ValueError('a104_audit_one_original_completed_native_execution_required')
        if not math.isclose(result['a104_credit'], returns[-1]['reported_credit'], abs_tol=1e-12):
            raise ValueError('a104_audit_latest_return_and_parent_axis_credit_disagree:'+result['case'])
        result['original_accounting'] = accounting(ledger, result['native_executions'][0])
        result['a104_return_boundary_complete'] = True
        result['annotation_parent_completion_claimed'] = result['annotation_parent_state'] == 'yielded'
        results.append(result)
        print(json.dumps({'case': result['case'], 'a104_credit': result['a104_credit'],
            'root_credit': result['root_credit'], 'a104_returns': len(returns),
            'all_report_owner_receiver_checks_passed': True,
            'annotation_parent_state': result['annotation_parent_state'],
            'pbs_job_id': result['native_executions'][0]['pbs_job_id']}), flush=True)
    (run/'A104_AUDITS.json').write_text(json.dumps({'cases': results,
        'audit_scope': 'completed_A104_returns_and_actual_receiving_parent_credit',
        'broader_annotation_parents_may_remain_checkpointed': True,
        'new_scientific_work_or_grading_performed': False}, indent=2)+'\n')


if __name__ == '__main__':
    main()
