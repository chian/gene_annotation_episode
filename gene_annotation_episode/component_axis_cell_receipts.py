"""Known A107/A110 cells through authenticated, frozen parent receipts.

This is a view over original admissions. It never reconstructs a private sheet,
copies a parent's later receipts, grants references or creates an acquisition.
"""
from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, canonical
from .episode_return_records import EpisodeReturnRecords


def inherited_cells(repository, context, local_cells):
    request = plain(getattr(context, 'request', {}))
    inheritance = request.get('message', {}).get('knowledge_inheritance')
    if not inheritance or inheritance.get('parent_episode_id') is None:
        return local_cells
    source = repository.cells_schema()['x-source']
    known = set(context.received_record_refs)
    result = deepcopy(local_cells)
    seen = {(row['sheet_ref'], row['component']): row for row in result}
    receipts = EpisodeReturnRecords(repository.store, context.run_id,
        failure_prefix='component_axis_')
    parents = {}
    for producer, form, schema in receipts.received_attempts(context):
        fields = [name for name, field in schema.get('properties', {}).items()
            if field.get('x-source') == source]
        if not fields:
            continue
        attempt = repository.store.db.execute(
            'SELECT parent_episode_id,decision_index FROM runtime_report_attempts '
            'WHERE run_id=? AND child_episode_id=?',
            (context.run_id, producer.episode_id)).fetchall()
        if len(attempt) != 1:
            raise ContractError('component_axis_inherited_delivery_identity_conflict')
        parent_id, index = attempt[0]
        if parent_id == context.episode_id:
            continue  # Direct receipts retain their existing admission checks.
        operation_key = f'{context.run_id}:{parent_id}:{index}:typed_form'
        if parent_id not in parents:
            parents[parent_id] = receipts.context(parent_id)
        parent = parents[parent_id]
        original = repository._runtime_delivery_cells(parent, operation_key)
        saved = repository.store.db.execute(
            f'SELECT cells FROM {repository.received_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',
            (context.run_id, parent_id, operation_key)).fetchone()
        if saved is None or original is None or canonical(json.loads(saved[0])) != canonical(original):
            raise ContractError('component_axis_inherited_cells_not_admitted')
        binding = repository._delivery_binding(parent, operation_key)
        if binding is not None and binding[0] != repository._delivery_digest(original):
            raise ContractError('component_axis_inherited_delivery_binding_conflict')
        for name in fields:
            values = plain(form[name])
            if canonical(values) != canonical(original):
                raise ContractError('component_axis_inherited_subset_conflict')
            admitted = [row for row in values if row['sheet_ref'] in known]
            repository.validate_returned_values(admitted,
                permitted_record_refs=context.received_record_refs)
            for row in admitted:
                key = row['sheet_ref'], row['component']
                if key in seen:
                    if canonical(seen[key]) != canonical(row):
                        raise ContractError('component_axis_inherited_cell_conflict')
                    continue
                seen[key] = row
                result.append(deepcopy(row))
    return result
