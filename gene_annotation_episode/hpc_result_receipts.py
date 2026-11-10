"""Scientific access to an actually received result of the existing HPC owner.

This is a publication reader. It starts no job, observes no scheduler and
creates no replacement receipt or execution authority.
"""
from copy import deepcopy
from collections.abc import Mapping
import base64
import hashlib
import json

from method_loop.identities import EpisodeRef

from .communication import plain
from .domain import ContractError
from .episode_return_records import EpisodeReturnRecords


def planned_input_files(plan):
    """Read original supplied inputs from current or historical HPC plans.

    This is planned byte identity, not proof that a path was staged or executed.
    The actual received execution/result receipts remain separately required.
    Neither the immutable plan nor its historical field meanings are changed.
    """
    fields = [name for name in ('supplied_files', 'files_to_stage') if name in plan]
    if not fields:
        raise ContractError('hpc_scientific_original_plan_files_missing')
    rows = plan[fields[0]]
    if len(fields) > 1 and plain(rows) != plain(plan[fields[1]]):
        raise ContractError('hpc_scientific_original_plan_files_conflict')
    if not isinstance(rows, (list, tuple)):
        raise ContractError('hpc_scientific_original_plan_files_invalid')
    seen = {}
    for row in rows:
        if (not isinstance(row, Mapping) or not isinstance(row.get('path'), str)
                or not isinstance(row.get('text'), str) or not isinstance(row.get('sha256'), str)):
            raise ContractError('hpc_scientific_original_plan_files_invalid')
        value = (row['text'], row['sha256'])
        if (hashlib.sha256(row['text'].encode()).hexdigest() != row['sha256']
                or seen.setdefault(row['path'], value) != value):
            raise ContractError('hpc_scientific_original_plan_files_bytes_conflict')
    return rows


def read_received_result(binding, context, reference):
    store = binding.store
    known = set(context.received_record_refs)
    if context.run_id != binding.run_id or reference not in known:
        raise ContractError('hpc_scientific_result_not_received')
    returns = EpisodeReturnRecords(store, context.run_id, failure_prefix='hpc_scientific_')
    returns.authenticate(context)
    source = store.get(reference)
    if (source.get('provider') != 'episode.hpc_result' or source.get('origin') != 'tool'
            or source.get('version') != 'hpc_result_v1'):
        raise ContractError('hpc_scientific_original_result_required')
    candidate = json.loads(store.get_artifact(source['artifact_ref']))
    original = returns.context(candidate['episode_id'])
    prefixes = [original.path[:index+1] for index, item in enumerate(original.path) if item[0] == 'hpc']
    if candidate['run_id'] != context.run_id or not prefixes:
        raise ContractError('hpc_scientific_original_owner_conflict')
    owner = returns.context(EpisodeRef(context.run_id, prefixes[-1]).episode_id)
    ledger = binding.state(owner)
    receipt = binding.read_evidence(context, ledger, reference)
    receipt = {key: value for key, value in receipt.items() if key != 'source_ref'}
    if receipt != candidate:
        raise ContractError('hpc_scientific_original_receipt_conflict')
    rows = store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
        "AND json_extract(action,'$.tool')='hpc.results' AND result IS NOT NULL",
        (context.run_id, original.episode_id))
    if not any(reference in json.loads(row['result']).get('record_refs', ()) for row in rows):
        raise ContractError('hpc_scientific_completed_collection_required')
    plans = [row['body'] for row in ledger.records('plan') if row['body']['plan_id'] == receipt['plan_id']]
    if len(plans) != 1 or plain(owner.scope) != receipt['scope']:
        raise ContractError('hpc_scientific_original_plan_conflict')
    plan = plans[0]
    units = [unit for unit in plan['manifest']['units'] if unit['unit_id'] == receipt['unit']['unit_id']]
    if len(units) != 1 or units[0]['obligation_id'] != receipt['unit']['obligation_id']:
        raise ContractError('hpc_scientific_original_unit_conflict')
    raw = base64.b64decode(receipt['window']['bytes_base64'], validate=True)
    if (hashlib.sha256(raw).hexdigest() != receipt['unit']['result_sha256']
            or json.loads(raw) != receipt['document']):
        raise ContractError('hpc_scientific_original_result_bytes_conflict')
    store.validate_scope(receipt['scope'], parent_scope=plain(context.scope))
    return deepcopy({'receipt': receipt, 'plan': plan, 'unit': units[0],
        'resource_id': ledger.commission['resource_id'],
        'resource': plain(binding.resources[ledger.commission['resource_id']]),
        'source_ref': reference, 'source_artifact_ref': source['artifact_ref']})
