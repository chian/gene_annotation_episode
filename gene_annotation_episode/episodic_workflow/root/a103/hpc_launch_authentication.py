"""Authenticate an A103 launch against its original HPC allocation."""

from pathlib import Path

from .communication import plain
from .hpc_ledger import HPCLedger
from . import hpc_queue


def authenticate_launch(parent, selection, operation_key, directory):
    owner = parent.assignment['owner_episode_id'] if parent.role == 'hpc_execution' else parent.episode_id
    ledger = HPCLedger.open_existing(Path(directory) / 'hpc' / hpc_queue.digest([parent.run_id, owner]))
    matching = [row for row in ledger.records('plan') if row['body']['launch_assignment'] == plain(selection)]
    if len(matching) != 1 or ledger.read('owner')['scope'] != plain(parent.scope):
        raise ValueError('hpc_launch_must_match_original_planned_portfolio')
    plan = matching[0]['body']
    identity = 'launch:' + plan['plan_id']
    reservation = {'operation_key': operation_key, 'plan_id': plan['plan_id']}
    if any(row['id'] == identity for row in ledger.records('launch_commission')):
        ledger.put('launch_commission', reservation, identity=identity)
        return
    if any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('hpc_allocation_already_closed')
    ledger.put('launch_commission', reservation, identity=identity)
