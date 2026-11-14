"""Original custody and projection of actually received native component records."""
from copy import deepcopy
import json

from ..communication import plain
from gene_annotation_episode.domain import ContractError
from .component_native_profiles import VERSION, PROFILES
from gene_annotation_episode.episodic_workflow.root.library.tool_grading_artifacts import source_tool_grading_entries


REQUEST_PROVIDER = 'host.component_axis.native_request'
RESULT_PROVIDER = 'host.component_axis.native_components'
STATUS_PROVIDER = 'host.component_axis.native_execution'
FACT_SOURCE = 'component_axis_native_component_records'
EXECUTION_SOURCE = 'component_axis_native_execution_records'


def scientific_profile(body):
    return body['scientific_profile'] if 'scientific_profile' in body else PROFILES[body['axis']]


def require(condition, code):
    if not condition:
        raise ContractError('component_native_'+code)


def read(store, reference, provider):
    source = store.get(reference)
    if source.get('provider') != provider:
        return None
    table = 'component_native_requests' if provider == REQUEST_PROVIDER else 'component_native_outputs'
    exists = store.db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (table,)).fetchone()
    saved = store.db.execute('SELECT body FROM '+table+' WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(saved is not None and source['origin'] == 'tool' and source['version'] == VERSION,
        'original_native_grant_required')
    body = json.loads(saved[0])
    require(json.loads(store.get_artifact(source['artifact_ref'])) == body, 'original_native_grant_conflict')
    if provider == RESULT_PROVIDER:
        entries = source_tool_grading_entries(store, reference)
        require(len(entries) == 1 and entries[0]['grading'] == {'grader': scientific_profile(body),
            'failure': None, 'sheet': body['native_components']}, 'original_native_grader_conflict')
    return body


def received_components(store, references, scope, *, axis=None, compact=True, known=None):
    known = set(references if known is None else known)
    rows = []
    for reference in sorted(set(references)):
        body = read(store, reference, RESULT_PROVIDER)
        if body is None or axis is not None and body['axis'] != axis:
            continue
        if not store.scope_contains(plain(scope), body['scope']):
            continue
        row = {'source_ref': reference, 'artifact_ref': store.get(reference)['artifact_ref'], **deepcopy(body)}
        changed = []
        for witness in row['input_provenance']:
            if witness['reference'] in known:
                current = store.get(witness['reference'])
                if any(current.get(key) != value for key, value in witness['identity'].items()):
                    changed.append(witness['reference'])
        row['changed_received_input_metadata_refs'] = changed
        row['input_snapshot_status'] = 'received_input_metadata_changed; historical_bytes_retained' if changed else (
            'no_change_in_actually_received_input_metadata; unknown_unreceived_revisions')
        if compact and row['axis'] == 'A107' and 'pairs' in row['native_components']:
            pairs = row['native_components'].pop('pairs')
            row['native_components']['pairs_retained'] = {'count': len(pairs), 'source_ref': reference,
                'artifact_ref': row['artifact_ref'], 'pointer': '/native_components/pairs',
                'preview': pairs[:8], 'complete_native_pairs_preserved': True}
            for side, criteria in row['native_components'].get('detection_criteria', {}).items():
                row['native_components']['detection_criteria'][side] = {'count': len(criteria),
                    'source_ref': reference, 'artifact_ref': row['artifact_ref'],
                    'pointer': '/native_components/detection_criteria/'+side, 'preview': criteria[:4],
                    'complete_native_criteria_preserved': True}
        if compact and row.get('scientific_profile') == 'a107_genomic_detection_v1':
            for name, artifact in row['native_components']['native_artifacts'].items():
                artifact.pop('bytes_base64')
                artifact.update(source_ref=reference, artifact_ref=row['artifact_ref'],
                    pointer='/native_components/native_artifacts/'+name,
                    availability='complete_original_native_bytes_retained_in_this_received_publication')
        rows.append(row)
    return rows


def execution_findings(store, references, scope, *, axis=None):
    rows = []
    for reference in sorted(set(references)):
        body = read(store, reference, STATUS_PROVIDER)
        if body is None and (request := read(store, reference, REQUEST_PROVIDER)) is not None:
            body = {'version': VERSION, 'axis': request['axis'], 'scope': request['scope'], 'run_id': request['run_id'],
                'request_ref': reference, 'hpc_result_ref': None, 'status': 'native_work_requested',
                'logical_work_sha256': request['logical_work_sha256'], 'resource_id': request['resource_id'],
                'arguments_sha256': request.get('arguments_sha256'),
                'selection': deepcopy(request['request']['selection']),
                'scientific_credit': None, 'meaning': 'no_native_result_admitted_by_this_request_record'}
        if body is None or axis is not None and body['axis'] != axis:
            continue
        if not store.scope_contains(plain(scope), body['scope']):
            continue
        rows.append({'source_ref': reference, **deepcopy(body)})
    prepared = {(row['run_id'], row['arguments_sha256']): row['source_ref'] for row in rows
        if row['status'] == 'native_work_requested' and row.get('arguments_sha256') is not None}
    for row in rows:
        if row['status'] == 'input_admission_unavailable':
            row['resolved_by_received_request_ref'] = prepared.get((row.get('run_id'), row.get('arguments_sha256')))
    return rows


def fact_sources():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    schema = {'type': 'array', 'items': ref, 'uniqueItems': True}
    return {FACT_SOURCE: {'type': 'array', 'meaning':
        'Actually received, automatically graded A107/A110 native component publications.',
        'report_schema': {**deepcopy(schema), 'x-source': FACT_SOURCE}},
        EXECUTION_SOURCE: {'type': 'array', 'meaning':
            'Actually received native execution/admission failures and missing original operand findings.',
            'report_schema': {**deepcopy(schema), 'x-source': EXECUTION_SOURCE}}}
