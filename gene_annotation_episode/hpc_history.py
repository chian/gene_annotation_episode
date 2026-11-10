"""Import retained HPC receipts into shared memory without opening a transport."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from .execution_guidance import resource_identity
from .execution_memory import ExecutionMemory, digest, validate_profile


def closed_measurement(commission, plan, measured, handoff, *, resources, ledger_path):
    resource = resource_identity(commission['resource_id'], resources[commission['resource_id']])
    profile = commission.get('execution_profile') or {'resource_id': resource,
        'backend': 'hpc', 'tool': 'allocation', 'implementation': 'unclassified:'+plan['plan_id'],
        'parameters': digest(plan['manifest']), 'hardware': resource}
    validate_profile(profile)
    return {'attempt_id': 'pbs:'+digest([resource, handoff['job_id'], plan['plan_id']]),
        'profile': profile, 'observation': {'observed_at': measured['body']['observed_at'],
            'features': plan['original_prediction']['features'], 'metrics': measured['body']['metrics'],
            'queue': plan['practical_assignment']['constraints']['queue'],
            'success': measured['body']['success'],
            'provenance': [str(Path(ledger_path).resolve()), measured['id'], handoff['job_id']]}}


def import_ledger(path, *, memory, resources):
    """Read only closed allocations; preserve original times and identities."""
    path = Path(path).resolve()
    with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
        records = [{'id': identity, 'kind': kind, 'body': json.loads(body)} for identity, kind, body
            in db.execute('SELECT id,kind,body FROM evidence ORDER BY recorded,id')]
    def rows(kind):
        return [row for row in records if row['kind'] == kind]
    commission = next(row['body'] for row in records if row['id'] == 'commission')
    closed = {row['body']['plan_id'] for row in rows('closed')}
    exported = []
    for record in rows('plan'):
        plan = record['body']
        if plan['plan_id'] not in closed:
            continue
        frozen = [row['body'] for row in rows('export_measurement')
                  if row['body']['body']['plan_id'] == plan['plan_id']]
        measured = frozen[-1] if frozen else [row for row in rows('measured')
            if row['body']['plan_id'] == plan['plan_id']][-1]
        handoff = [row['body'] for row in rows('handoff') if row['body']['plan_id'] == plan['plan_id']][-1]
        value = closed_measurement(commission, plan, measured, handoff,
                                  resources=resources, ledger_path=path)
        memory.record(**value)
        exported.append({'attempt_id': value['attempt_id'], 'profile': value['profile'],
            'observed_at': value['observation']['observed_at'], 'metrics': value['observation']['metrics']})
    for row in rows('queue')[-1:]:
        body = row['body']
        memory.observe(resource_identity(commission['resource_id'], resources[commission['resource_id']]),
            'queue', body, observed_at=body['snapshot']['captured_at'], provenance=[str(path), row['id']])
    return exported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--resources', type=Path, required=True)
    parser.add_argument('--memory', type=Path)
    args = parser.parse_args()
    memory = ExecutionMemory(args.memory) if args.memory else ExecutionMemory.configured()
    result = import_ledger(args.ledger, memory=memory, resources=json.loads(args.resources.read_text()))
    print(json.dumps({'imported': result, 'memory': memory.as_record()}, indent=2))


if __name__ == '__main__':
    main()
