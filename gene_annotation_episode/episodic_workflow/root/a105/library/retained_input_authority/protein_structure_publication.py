"""Ordinary source and sequence publication for retained protein results.

Payload construction is pure; publication validates retained original bytes.
The result host separately authenticates capture and worker custody. A source's
auxiliary list preserves original files and grants no receiving episode access.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a105.domain import RECORD_SCHEMAS, identity, validate_schema
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_protein_structure_acquisition import ProteinStructureCapture
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_protein_structure_contracts import NativeProteinBundle, validate_protein_structure_bundle
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.protein_structure_contracts import validate_file_identity
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.protein_structure_result_worker import ProteinResultWorkerResult, validate_protein_structure_result_worker_result

def protein_structure_source_payload(*, bundle: NativeProteinBundle, capture: ProteinStructureCapture, worker_result: ProteinResultWorkerResult | None, request_ref: str | None=None) -> dict:
    """Build the single approved immutable payload from qualified actual files.

This checks the supplied metadata relationship. It does not acquire bytes or
establish original episode authority. Saved recalculation must use the original
source, rather than pass its later worker output to this function.
    """
    if capture['bundle_validated'] is not True or capture['original_plan'] is None or capture['bundle_file'] is None:
        raise ValueError('capture_incomplete')
    original = validate_protein_structure_bundle(bundle, plan=capture['original_plan'])
    bundle_file = validate_file_identity(capture['bundle_file'])
    if bundle_file['format'] != 'native_protein_structure_bundle_v1' or bundle_file['sha256'] != digest(original) or bundle_file['byte_length'] != len(canonical(original).encode('utf-8')):
        raise ValueError('input_digest_mismatch')
    references = []
    for row in capture['files']:
        if row['observed'] is not None:
            references.append(validate_file_identity(row['observed'])['artifact_ref'])
    if worker_result is not None:
        result = validate_protein_structure_result_worker_result(worker_result)
        operation = original['requested_job']['native_protein_structure']['request']['operation']
        if result['mode'] != 'original_native_result' or result['operation'] != operation:
            raise ValueError('original_commission_mismatch')
        for name in ('native_result_file', 'sheet_file', 'components_file'):
            if result[name] is not None:
                references.append(result[name]['file_identity']['artifact_ref'])
    return {'provider': 'episode.execution_result', 'accession': 'native_protein_structure_' + digest(original['identity']), 'uri': None, 'artifact_ref': bundle_file['artifact_ref'], 'text_ref': None, 'request_ref': request_ref, 'version': 'native_protein_structure_bundle_v1', 'retrieved_at': original['finished_at'], 'auxiliary_artifact_refs': list(dict.fromkeys(references))}

def _ordinary_record(store, reference, kind):
    """Validate the existing domain identity without creating a new namespace."""
    if type(reference) is not str:
        raise ValueError('invalid_schema')
    try:
        record = store.get(reference)
    except ContractError as error:
        raise ValueError('conflicting_identity') from error
    except (ValueError, TypeError) as error:
        raise ValueError('invalid_schema') from error
    if type(record) is not dict or record.get('id') != reference or record.get('record_type') != kind or (record.get('origin') != 'tool'):
        raise ValueError('conflicting_identity')
    payload = {key: value for key, value in record.items() if key not in {'id', 'record_type', 'origin'}}
    try:
        expected = identity(kind, {'origin': record['origin'], 'record': payload})
    except (ValueError, TypeError) as error:
        raise ValueError('invalid_schema') from error
    if reference != expected:
        raise ValueError('conflicting_identity')
    try:
        validate_schema(payload, RECORD_SCHEMAS[kind])
    except ContractError as error:
        raise ValueError('invalid_schema') from error
    return record

def saved_protein_action_values(work):
    """Project only the explicitly selected values; retain unavailable meanings."""
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.protein_structure_contracts import IssueCode, issue
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.protein_structure_result_views import project_protein_structure_results
    from typing import get_args
    rows = []
    for selection in work['arguments']['projections']:
        if work['scientific'] is None:
            outcome = dict(version='protein_structure_action_unavailable_v1', issues=deepcopy(work['issues']) or [issue('selected_field_unavailable', stage='projection', field='projection_fields')])
        else:
            try:
                outcome, = project_protein_structure_results(work['scientific'], selection=[selection])
            except ValueError as error:
                code = str(error) if str(error) in get_args(IssueCode) else 'invalid_schema'
                outcome = dict(version='protein_structure_action_unavailable_v1', issues=[issue(code, stage='projection', field='projection_fields')])
        rows.append(dict(selection=deepcopy(selection), outcome=outcome))
    return dict(version='protein_structure_saved_action_values_v1', operation='compare', projections=rows, issues=deepcopy(work['issues']))

def saved_protein_action_source_payload(store, *, capsule, public_ref, request_ref):
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.protein_structure_action_records import SAVED_ACTION_SOURCE_VERSION
    work = capsule['work']
    descriptor = work['arguments']['saved_sheet']
    parent = _ordinary_record(store, descriptor['custody']['source_ref'], 'source')
    parents = list(dict.fromkeys([parent['id'], work['admission']['result_ref']]))
    auxiliary = [work['qualified_files'][name]['artifact_ref'] for name in ('sheet_file', 'original_components_file', 'components_file') if work['qualified_files'][name] is not None]
    if work['worker'] is not None:
        prepared = work['worker']['prepared']
        auxiliary.extend((prepared[name] for name in ('plan_artifact_ref', 'execution_receipt_artifact_ref', 'worker_result_artifact_ref') if prepared[name] is not None))
        auxiliary.extend((row['artifact_ref'] for row in prepared['diagnostic_files']))
    return dict(provider='episode.execution_result', accession='protein_structure_saved_action_' + digest(work['invocation']), uri=None, artifact_ref=public_ref, text_ref=None, request_ref=request_ref, version=SAVED_ACTION_SOURCE_VERSION, retrieved_at=None, parent_source_refs=parents, auxiliary_artifact_refs=list(dict.fromkeys(auxiliary)))

def saved_protein_action_result(values, *, source_ref):
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.protein_structure_action_records import validate_protein_structure_tool_result
    return validate_protein_structure_tool_result(dict(version='protein_structure_tool_result_v1', source_ref=source_ref, operation='compare', views=[dict(version='protein_structure_action_view_v1', source_ref=source_ref, operation='compare', **deepcopy(row)) for row in values['projections']], sequences=[], saved_sheets=[], issues=deepcopy(values['issues'])))
