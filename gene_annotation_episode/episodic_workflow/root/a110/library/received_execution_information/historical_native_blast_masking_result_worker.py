"""Bounded deterministic stages over retained masking bytes and saved sheets.

The host owns capture and publication. These stages neither submit native work
nor use a Store or model. Replaying a completed stage reads its original receipt.
"""
from __future__ import annotations
import re
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_acquisition import validate_native_blast_masking_capture
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_contracts import finite_json_copy, native_blast_digest, masking_occurrence_id
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_sequence_masking_contracts import validate_sequence_masking_record as core
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_sequence_masking_result_views import failure, unique_failures
PREFIX = 'native_blast_masking_'
MANIFEST_VERSION = PREFIX + 'result_worker_manifest_v1'
OUTPUT_FILES = {'sheet': 'sheet.json', 'calculations': 'calculations.json', 'statistics': 'statistics.json', 'projection': 'projection.json', 'recalculations': 'recalculations.json'}

def _error(code):
    raise ContractError(PREFIX + code)

def _occurrence_id(bundle, direction, role):
    if direction == 'input' and role == 'statistics':
        return bundle['statistics_binding']['statistics_occurrence_id']
    return masking_occurrence_id(bundle['identity'], direction, role)

def qualified_masking_context(bundle, capture):
    """Reconstruct typed custody facts from a previously authenticated Bundle."""
    capture = validate_native_blast_masking_capture(capture)
    if not capture['bundle_validated'] or capture['bundle_artifact_ref'] is None:
        _error('validated_capture_required')
    originals = {}
    for direction, collection in (('input', 'inputs'), ('output', 'artifacts')):
        for row in bundle[collection]:
            originals[direction, row['role'], row['ordinal']] = row
    rc = bundle['returncode']
    succeeded = rc == 0 and (not bundle['failures'])
    state = 'succeeded' if succeeded else 'incomplete' if rc == 0 else 'failed'
    rows = []
    for item in capture['artifacts']:
        slot = tuple((item[k] for k in ('direction', 'role', 'ordinal')))
        row = originals.get(slot)
        if row is None or any((item[k] != row[k] for k in ('role', 'ordinal', 'format', 'relative_path'))):
            _error('captured_occurrence_association_conflict')
        direction, role, ordinal = slot
        if direction == 'input':
            identities = [(row[p + 'sha256'], row[p + 'size_bytes']) for p in ('expected_', 'staged_', 'final_')]
            valid = all((pair == (item['sha256'], item['size_bytes']) for pair in identities))
        else:
            valid = (row['sha256'], row['size_bytes']) == (item['sha256'], item['size_bytes'])
        if not valid or item['artifact_ref'] != 'artifact_' + item['sha256']:
            _error('captured_occurrence_identity_conflict')
        complete = direction == 'input' or succeeded or (role in {'stdout', 'stderr'} and rc is not None)
        rows.append(core('Occurrence', {'occurrence_id': _occurrence_id(bundle, direction, role), 'direction': direction, 'role': role, 'ordinal': ordinal, 'artifact_ref': item['artifact_ref'], 'sha256': item['sha256'], 'size_bytes': item['size_bytes'], 'completeness': 'complete' if complete else 'partial'}))
    if len({r['occurrence_id'] for r in rows}) != len(rows):
        _error('captured_occurrence_identity_duplicate')
    primary = 'statistics' if bundle['operation']['mode'] == 'create_counts' else 'mask'
    output_complete = succeeded and any((r['direction'] == 'output' and r['role'] == primary for r in rows))
    outcome = core('NativeOutcome', {'returncode': rc, 'state': state, 'output_complete': output_complete})
    failures = []
    for original in bundle['failures']:
        role = original['role']
        direction = 'input' if role in {r['role'] for r in bundle['inputs']} else 'output'
        oid = _occurrence_id(bundle, direction, role) if role else None
        stage = 'input' if original['stage'] in {'inputs', 'preflight'} else 'native'
        failures.append(failure(stage, original['code'], oid))
        for row in original['input_failures']:
            key = oid + '#/records/' + str(row['record_ordinal']) if oid and row['record_ordinal'] is not None else None
            failures.append(failure('input', row['code'], oid, key, row['line_number']))
    for original in capture['failures']:
        oid = _occurrence_id(bundle, original['direction'], original['role']) if original['direction'] else None
        failures.append(failure('custody', original['code'], oid))
    if state != 'succeeded':
        failures.append(failure('native', 'native_' + state))
    return (rows, outcome, unique_failures(failures))

def expected_outputs(plan):
    if plan['task'] == 'project_saved':
        return {'projection', *({'recalculations'} if plan['selector']['mode'] == 'saved_recalculation' else set())}
    roles = set()
    slots = {(r['direction'], r['role']) for r in plan['occurrences']}
    if ('output', 'mask') in slots:
        roles.update({'sheet', 'calculations'})
    if any((role == 'statistics' for _, role in slots)):
        roles.add('statistics')
    return roles

def validate_worker_manifest(manifest, plan):
    manifest = finite_json_copy(manifest)
    if type(manifest) is not dict or set(manifest) != {'version', 'task', 'plan_sha256', 'completed', 'outputs', 'failures'} or manifest['version'] != MANIFEST_VERSION or (manifest['task'] != plan['task']) or (manifest['plan_sha256'] != native_blast_digest(plan)) or (type(manifest['completed']) is not bool) or (type(manifest['outputs']) is not dict):
        _error('worker_manifest_invalid')
    unique_failures(manifest['failures'])
    if not set(manifest['outputs']) <= expected_outputs(plan) or (manifest['completed'] and set(manifest['outputs']) != expected_outputs(plan)):
        _error('worker_manifest_output_population_conflict')
    for role, row in manifest['outputs'].items():
        if type(row) is not dict or set(row) != {'filename', 'sha256', 'size_bytes'} or row['filename'] != OUTPUT_FILES[role] or (type(row['sha256']) is not str) or (re.fullmatch('[0-9a-f]{64}', row['sha256']) is None) or (type(row['size_bytes']) is not int) or (row['size_bytes'] < 0):
            _error('worker_manifest_descriptor_invalid')
    return manifest
