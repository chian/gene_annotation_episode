"""Authenticate an actually received, completed native phmmer search."""
import hashlib
import json

from .domain import ContractError


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def search_receipt(store, snapshot_ref, native_source_ref, component_ref, known):
    _require({snapshot_ref, native_source_ref, component_ref} <= set(known),
        'a103_native_search_inputs_not_received')
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='homology_result_snapshots'").fetchone()
    row = store.db.execute('SELECT body FROM homology_result_snapshots WHERE source_ref=?',
        (snapshot_ref,)).fetchone() if exists else None
    _require(row is not None, 'a103_registered_native_search_required')
    source, native = store.get(snapshot_ref), store.get(native_source_ref)
    body = json.loads(row[0])
    _require(source['origin'] == 'tool' and source.get('provider') == 'native.phmmer.parsed_snapshot'
        and json.loads(store.get_artifact(source['artifact_ref'])) == body,
        'a103_search_snapshot_custody_conflict')
    _require(body['native_source_ref'] == native_source_ref and native['origin'] == 'tool'
        and native.get('provider') == 'native.phmmer.snapshot'
        and native['artifact_ref'] == body['native_text_artifact'],
        'a103_native_output_custody_conflict')
    inventory = body['parse_inventory']
    _require(body['native_termination_seen'] and inventory['parser_finished']
        and inventory['native_error_count'] == 0 and inventory.get('grading_error_count', 0) == 0
        and body['parse_execution']['failure'] is None,
        'a103_complete_error_free_native_search_required')
    component = store.get(component_ref)
    _require(component.get('sequence_ref') is not None, 'a103_detection_query_sequence_required')
    sequence = store.get_artifact(component['sequence_ref']).decode().strip().upper()
    _require(hashlib.sha256(sequence.encode()).hexdigest() == body['query_sequence_sha256'],
        'a103_detection_actual_query_conflict')
    return body, sequence
