"""Pure associations for acquired GenomeAlignment native artifacts.

The host authenticates retained receipts before this call. This layer checks
supplied receipt bytes, actual manifest object relationships and parsed native
identities. Manifest membership does not establish producer byte identity, and
caller-authored source/interval metadata cannot establish a missing run witness.
"""
from collections import defaultdict
from copy import deepcopy
import hashlib

from .bvbrc_alignment_values import diagnostic, requirement
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_analysis_protocol import parse_workspace_records
from .bvbrc_appservice_readers import decode_job_result
from .bvbrc_genome_alignment_input_contracts import (
    DIAGNOSTIC_CODES, ROLES, validate_genome_alignment_inputs,
    validate_genome_alignment_associations,
)
from .bvbrc_genome_alignment_inputs import (
    validate_genome_alignment_retained_records,
    validate_genome_alignment_supplied_value_shapes,
)
from .bvbrc_genome_alignment_retained_records import (
    RETAINED_RECORD_ERRORS, validate_retained_record_arguments,
    supplied_content, supplied_evidence,
)
from .execution_contracts import canonical
from .mauve_v4_format_contracts import validate_mauve_v4_document
from .mauve_backbone_contracts import (
    validate_mauve_backbone_document, validate_mauve_bbcols_document,
)
from .xmfa_format_contracts import validate_xmfa_document

PREFIX = 'bvbrc_genome_alignment_'
_DOCUMENT_VALIDATORS = {
    'mauve1_xmfa': validate_xmfa_document,
    'mauve_v4': validate_mauve_v4_document,
    'mauve_backbone': validate_mauve_backbone_document,
    'mauve_bbcols': validate_mauve_bbcols_document,
}
_ROLE_FORMATS = {
    'genome_alignment_primary': ('mauve1_xmfa', 'mauve_v4'),
    'genome_alignment_backbone': ('mauve_backbone',),
    'genome_alignment_bbcols': ('mauve_bbcols',),
    'genome_alignment_visualization': ('p3_mauve_visualization_json',),
}
_NAMESPACES = {
    'mauve1_xmfa': 'mauve1_member_1based', 'mauve_v4': 'mauve_v4_member_0based',
    'mauve_backbone': 'mauve_sidecar_member_0based',
    'mauve_bbcols': 'mauve_sidecar_member_0based',
}
_METADATA_KINDS = frozenset(('genome_alignment_invocation', 'genome_alignment_staged_file',
    'genome_alignment_contig_identity', 'genome_alignment_feature_mapping',
    'genome_alignment_interval_mapping', 'genome_alignment_producer'))


def _require(condition):
    if not condition:
        raise ValueError(PREFIX + 'argument_invalid')


def _key(artifact):
    return tuple(artifact[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256'))


def _native_artifact(artifact):
    return {k: artifact[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256')}


def _number(value, minimum=0):
    return (type(value) is dict and value.get('state') == 'available'
            and type(value.get('value')) is int and value['value'] >= minimum)


class _Reports:
    def __init__(self):
        self.requirements, self.diagnostics = [], []

    def add(self, suffix, path, *, role=None, kind='scientific_metadata', refs=(), needed=True):
        code = PREFIX + suffix
        _require(code in DIAGNOSTIC_CODES)
        refs = list(dict.fromkeys(refs))
        item = diagnostic(code, phase='association', path=path, evidence_refs=refs)
        if item not in self.diagnostics:
            self.diagnostics.append(item)
        if not needed:
            return []
        identity = 'ga_association:' + hashlib.sha256(
            canonical([code, path, kind, role, refs]).encode()).hexdigest()
        req = requirement(identity, kind=kind, role=role, source_refs=refs, reason_code=code)
        if req not in self.requirements:
            self.requirements.append(req)
        return [identity]


def _accepted_records(task, records, supplied_bytes, reports):
    groups = defaultdict(list)
    for index, row in enumerate(records):
        groups[row['record']['source_ref']].append((index, row))
    result = []
    for reference, group in groups.items():
        if len({canonical(row) for _, row in group}) != 1:
            for index, _ in group:
                reports.add('metadata_record_unverified', f'/retained_records/{index}',
                            kind='input_metadata', refs=[reference])
            continue
        index, row = group[0]
        try:
            checked = validate_genome_alignment_retained_records(task,
                retained_records=(row,), supplied_bytes=supplied_bytes)[0]
            result.append((index, checked))
        except ValueError as error:
            if str(error) not in RETAINED_RECORD_ERRORS:
                raise
            suffix = str(error)[len(PREFIX):]
            reports.add(suffix, f'/retained_records/{index}',
                kind='original_task' if suffix == 'metadata_task_conflict' else 'input_metadata',
                refs=[reference])
    handoffs = [r for _, r in result if r['record']['contract'] == 'TaskHandoff']
    # Receipt admission fixes every handoff reference to the OriginalTask's
    # submission receipt. Conflicting copies of that reference were excluded
    # above, so there can be at most one admitted original request.
    _require(len(handoffs) <= 1)
    if handoffs:
        request = _request(handoffs[0])
        kept = []
        for index, row in result:
            if canonical(_request(row)) != canonical(request):
                reports.add('metadata_task_conflict', f'/retained_records/{index}/record/value',
                            kind='original_task', refs=[row['record']['source_ref']])
            else:
                kept.append((index, row))
        result = kept
    return [row for _, row in result]


def _request(row):
    value = row['record']['value']
    snapshot = value['snapshot'] if row['record']['contract'] == 'AcquisitionReceipt' else value['receipt']['snapshot']
    return snapshot['selected_operands']['native_operands']['request']


def _selected_json(value, supplied_bytes):
    selected = supplied_evidence(value['evidence'], supplied_bytes)
    if canonical(selected) != canonical(value['value']):
        raise ValueError(PREFIX + 'metadata_record_unverified')


def _metadata(task, supplied_values, supplied_bytes, reports):
    interval_claims = set()
    for index, wrapper in enumerate(supplied_values):
        path = f'/supplied_values/{index}'
        reference = wrapper['evidence']['content']['source_ref']
        try:
            _selected_json(wrapper, supplied_bytes)
        except ValueError as error:
            if str(error) not in RETAINED_RECORD_ERRORS:
                raise
            reports.add(str(error)[len(PREFIX):], path, kind='input_metadata', refs=[reference])
            continue
        value = wrapper['value']
        kind = value.get('kind') if type(value) is dict else None
        if kind not in _METADATA_KINDS:
            reports.add('metadata_type_unsupported', path, kind='input_metadata', refs=[reference])
            continue
        if value['original_task_id'] != task['task_id']:
            reports.add('metadata_task_conflict', path, kind='original_task', refs=[reference])
            continue
        # Exact JSON pointer equality does not prove the asserted native cause.
        reports.add('metadata_record_unverified', path, kind='input_metadata', refs=[reference])
        if kind == 'genome_alignment_interval_mapping':
            interval_claims.add(_key(value['bbcols_artifact']))
    return interval_claims


def _parsed_records(parsed_artifacts):
    _require(type(parsed_artifacts) is tuple)
    result = {}
    for row in parsed_artifacts:
        _require(type(row) is dict and set(row) == {'artifact', 'format', 'parse_status', 'document', 'diagnostics'})
        _require(type(row['format']) is str and row['format'] in _DOCUMENT_VALIDATORS)
        _require(row['parse_status'] in ('ok', 'partial', 'invalid'))
        _require(type(row['artifact']) is dict and set(row['artifact']) == {'raw_artifact_ref', 'source_ref', 'sha256'})
        _require(type(row['diagnostics']) is list)
        for item in row['diagnostics']:
            validate_contract('Diagnostic', item)
        document = row['document']
        _require((document is None) == (row['parse_status'] == 'invalid'))
        if document is not None:
            _DOCUMENT_VALIDATORS[row['format']](document)
            _require(document['artifact'] == row['artifact'])
            _require(row['parse_status'] != 'ok' or document['completeness'] != 'partial')
        # Native artifact validator is covered by every non-null document; an
        # invalid/null parse still needs an actual well-typed artifact identity.
        from .xmfa_format_contracts import _artifact
        _artifact(row['artifact'])
        key = _key(row['artifact'])
        _require(key not in result or result[key] == row)
        result[key] = row
    return result


def _members(parsed):
    document, fmt = parsed['document'], parsed['format']
    if document is None:
        return []
    indices = set()
    if fmt == 'mauve1_xmfa':
        for block in document['blocks']:
            indices.update(r['member_number']['value'] for r in block['records']
                           if _number(r['member_number'], 1))
        for row in document['metadata']:
            number = row.get('member_number')
            if _number(number, 1):
                indices.add(number['value'])
    elif fmt == 'mauve_v4':
        indices.update(r['member_index_token']['value'] for r in document['metadata']
                       if _number(r['member_index_token']))
        for interval in document['intervals']:
            for segment in interval['segments']:
                indices.update(range(len(segment['native_starts'])))
    elif fmt == 'mauve_backbone':
        for row in document['rows']:
            indices.update(p['member_index_0based'] for p in row['pairs']
                           if p['member_index_0based'] is not None)
        indices.update(c['member_index_token']['value'] for c in document['columns']
                       if _number(c['member_index_token']))
    else:
        for row in document['rows']:
            indices.update(n['value'] for n in row['native_member_indices_0based'] if _number(n))
    return [{'namespace': _NAMESPACES[fmt], 'index': i} for i in sorted(indices)]


def _manifest_association(task, acquisition_record, accepted, supplied_bytes):
    output_acquisition = acquisition_record['record']['value']
    artifact = output_acquisition['artifact']
    association = artifact['task_association']
    candidates = [r for r in accepted if r['record']['contract'] == 'AcquisitionReceipt'
        and r['record']['value']['artifact']['source_ref'] == association['evidence_ref']]
    if len(candidates) != 1:
        return None
    record = candidates[0]
    acquisition = record['record']['value']; manifest = acquisition['artifact']
    if (acquisition['status'] not in ('ok', 'partial')
            or manifest['transfer']['object_complete'] != 'yes'
            or not manifest['transfer']['body_complete']):
        return None
    # Establish that these manifest bytes were obtained from the native task's
    # reported job_result object. A matching caller-authored association alone
    # cannot supply this cross-record relationship.
    manifest_link = manifest['task_association']
    if manifest_link['kind'] != 'task_info_object':
        return None
    info_rows = [r for r in accepted if r['record']['contract'] == 'TaskInfoReceipt'
                 and r['record']['source_ref'] == manifest_link['evidence_ref']]
    if len(info_rows) != 1:
        return None
    info = info_rows[0]['record']['value']
    if not info['body_complete'] or info['local_window'] is not None:
        return None
    if (info['file'] != 'job_result_id'
            or info['reported_object_uuid'] != manifest['workspace_object']['uuid']
            or manifest_link['pointer'] != '/reported_object_uuid'
            or manifest_link['output_uuid'] != info['reported_object_uuid']
            or manifest_link['output_path'] != manifest['workspace_object']['path']):
        raise ValueError(PREFIX + 'artifact_task_conflict')
    info_selection = {'kind': 'task_info_object', 'receipt_ref': info_rows[0]['record']['source_ref']}
    selection = acquisition['object_selection']
    if selection != info_selection:
        if selection['kind'] != 'receipt_row':
            raise ValueError(PREFIX + 'artifact_task_conflict')
        metadata_rows = [r for r in accepted if r['record']['contract'] == 'WorkspaceReceipt'
            and r['record']['source_ref'] == selection['receipt_ref']]
        if not metadata_rows:
            return None
        if len(metadata_rows) != 1 or manifest['workspace_object']['metadata_receipt_ref'] != selection['receipt_ref']:
            raise ValueError(PREFIX + 'artifact_task_conflict')
        metadata = metadata_rows[0]['record']['value']
        rows = [row for row in metadata['rows'] if row['pointer'] == selection['row_pointer']]
        if len(rows) != 1 or not rows[0]['valid'] or any(rows[0][key] != manifest['workspace_object'][key]
                for key in ('path', 'uuid', 'type')):
            raise ValueError(PREFIX + 'artifact_task_conflict')
        call = metadata['receipt']['snapshot']['selected_operands']['native_operands']['call']['rpc_request']
        parsed = parse_workspace_records(metadata['native_value'], operation='get',
            requested_paths=call['params'][0]['objects'])
        matches = [row for row in parsed['records'] if '/result/0/' + str(row['row_index']) == selection['row_pointer']]
        if len(matches) != 1 or matches[0]['status'] != 'ok' or not matches[0]['request_indices']:
            raise ValueError(PREFIX + 'artifact_task_conflict')
        if any(metadata['requested_objects'][i] != info_selection for i in matches[0]['request_indices']):
            raise ValueError(PREFIX + 'artifact_task_conflict')
    raw = supplied_content(acquisition['snapshot']['content'], supplied_bytes)
    decoded = decode_job_result(raw, original_task=task,
        object_binding=manifest['workspace_object'], evidence_ref=manifest['source_ref'])
    identity_fields = ('kind', 'evidence_ref', 'pointer', 'task_id', 'output_path', 'output_uuid')
    matching = [r for r in decoded['value']['outputs']
                if all(r['association'][k] == association[k] for k in identity_fields)]
    if len(matching) != 1:
        raise ValueError(PREFIX + 'artifact_task_conflict')
    row = matching[0]
    if (artifact['workspace_object']['path'] != row['path']
            or artifact['workspace_object']['uuid'] != row['uuid']
            or output_acquisition['object_selection'] != {
                'kind': 'manifest_member', 'manifest_receipt_ref': record['record']['source_ref'],
                'output_index': row['output_index']}):
        raise ValueError(PREFIX + 'artifact_task_conflict')
    return {'content': deepcopy(record['receipt_content']), 'pointer': '/value/artifact'}


def bind_genome_alignment_artifacts(original_task: dict, *, artifacts: tuple[dict, ...],
    parsed_artifacts: tuple[dict, ...], supplied_values: tuple[dict, ...],
    inputs: dict | None, supplied_bytes: dict[str, bytes], retained_records: tuple[dict, ...]) -> dict:
    """Bind observed native objects while preserving missing historical joins."""
    validate_retained_record_arguments(original_task, retained_records=retained_records,
                                      supplied_bytes=supplied_bytes)
    validate_genome_alignment_supplied_value_shapes(supplied_values)
    _require(type(artifacts) is tuple)
    for artifact in artifacts:
        validate_contract('ArtifactMember', artifact)
        _require(artifact['role'] in ROLES)
    parsed = _parsed_records(parsed_artifacts)
    keys = [_key(a) for a in artifacts]
    _require(len(keys) == len(set(keys)))
    _require(set(parsed) <= set(keys))
    if inputs is not None:
        validate_genome_alignment_inputs(inputs)
    reports = _Reports()
    task = deepcopy(original_task)
    ids = task['submitted_parameters'].get('genome_ids')
    if (task['required_application_id'] != 'GenomeAlignment'
            or task['native_application_id'] != 'GenomeAlignment'):
        reports.add('application_mismatch', '/original_task', kind='original_task')
        return {'status': 'invalid', 'value': None, **vars(reports)}
    if type(ids) is not list or not ids or any(type(x) is not str or not x for x in ids):
        reports.add('genome_input_missing', '/original_task/submitted_parameters/genome_ids', kind='original_task')
        return {'status': 'invalid', 'value': None, **vars(reports)}
    accepted = _accepted_records(task, retained_records, supplied_bytes, reports)
    interval_claims = _metadata(task, supplied_values, supplied_bytes, reports)
    if inputs is not None and inputs['original_task'] != task:
        reports.add('metadata_task_conflict', '/inputs/original_task', kind='original_task')
        inputs = None
    value = {'schema_version': 'bvbrc_genome_alignment_associations_v1',
        'original_task': task, 'artifacts': [], 'native_member_joins': [],
        'bbcols_interval_joins': [], 'duplicate_representations': [],
        'requirements': reports.requirements, 'diagnostics': reports.diagnostics}
    by_digest = defaultdict(list)
    for index, artifact in enumerate(artifacts):
        path = f'/artifacts/{index}'; role = artifact['role']; refs = [artifact['source_ref']]
        row_ids, evidence = [], []
        entry = parsed.get(_key(artifact)); doc = None if entry is None else entry['document']
        observed = None if doc is None else entry['format']
        state = 'unverified'
        association = artifact['task_association']
        actual = [r for r in accepted if r['record']['contract'] == 'AcquisitionReceipt'
                  and r['record']['value']['artifact'] == artifact]
        if len(actual) == 1:
            evidence.append({'content': deepcopy(actual[0]['receipt_content']), 'pointer': '/value/artifact'})
        else:
            row_ids += reports.add('metadata_record_unverified', path, role=role, kind='output_metadata', refs=refs)
        if association['task_id'] != task['task_id']:
            state = 'conflicting'
            row_ids += reports.add('artifact_task_conflict', path, role=role, kind='task_manifest', refs=refs)
        elif len(actual) == 1 and association['kind'] == 'task_result_manifest':
            try:
                proof = _manifest_association(task, actual[0], accepted, supplied_bytes)
            except ValueError as error:
                if str(error) != PREFIX + 'artifact_task_conflict':
                    raise
                row_ids += reports.add('artifact_task_conflict', path, role=role,
                                       kind='task_manifest', refs=refs)
                state = 'conflicting'
            else:
                if proof is None:
                    row_ids += reports.add('metadata_record_unverified', path + '/task_association',
                                           role=role, kind='task_manifest', refs=refs)
                else:
                    evidence.append(proof); state = 'bound'
        else:
            row_ids += reports.add('metadata_record_unverified', path + '/task_association',
                                  role=role, kind='task_manifest', refs=refs)
        raw = supplied_bytes.get(artifact['raw_artifact_ref'])
        if raw is None:
            row_ids += reports.add('content_missing', path, role=role, kind='output_bytes', refs=refs)
            state = 'missing' if state != 'conflicting' else state
        elif len(raw) != artifact['byte_count'] or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
            row_ids += reports.add('content_digest_conflict', path, role=role, kind='output_bytes', refs=refs)
            state = 'conflicting'
        declared = artifact['declared_format']
        version = {'mauve1_xmfa': 'Mauve1', 'mauve_v4': '4'}.get(observed)
        if (observed is not None and (observed not in _ROLE_FORMATS[role]
                or declared['format'] != observed
                or version is not None and declared['version'] not in (None, version))):
            row_ids += reports.add('artifact_format_conflict', path, role=role, kind='parser_binding', refs=refs)
            state = 'conflicting'
        elif doc is None:
            row_ids += reports.add('artifact_format_conflict', path, role=role, kind='parser_binding', refs=refs)
            state = 'conflicting' if entry is not None else 'unverified' if state == 'bound' else state
        # Current producer/record dialects have no output-digest/build witness.
        # A supplied producer_bytes_bound label is not a native decoder for one.
        row_ids += reports.add('artifact_version_unverified', path, role=role,
                              kind='byte_version_evidence', refs=refs)
        value['artifacts'].append({'artifact': deepcopy(artifact), 'role': role,
            'observed_format': observed, 'document_id': doc['document_id'] if doc is not None else None,
            'state': state, 'evidence': evidence, 'requirement_ids': list(dict.fromkeys(row_ids))})
        by_digest[artifact['sha256']].append(artifact)
        if doc is not None:
            for member in _members(entry):
                mids = reports.add('member_join_missing', path + '/members/' + str(member['index']),
                    role=role, kind='input_metadata', refs=refs)
                value['native_member_joins'].append({'artifact': _native_artifact(artifact),
                    'member': member, 'input_member': None, 'state': 'unverified',
                    'evidence': deepcopy(evidence), 'requirement_ids': mids})
            if observed == 'mauve_bbcols':
                intervals = sorted({r['native_interval_index_0based']['value'] for r in doc['rows']
                                    if _number(r['native_interval_index_0based'])})
                for interval in intervals:
                    iids = reports.add('interval_join_missing', path + '/intervals/' + str(interval),
                        role='genome_alignment_interval_mapping', refs=refs)
                    value['bbcols_interval_joins'].append({'bbcols_document_id': doc['document_id'],
                        'native_interval_index_0based': interval, 'xmfa_document_id': None,
                        'xmfa_block_index': None, 'state': 'unverified' if _key(artifact) in interval_claims else 'missing',
                        'evidence': deepcopy(evidence), 'requirement_ids': iids})
    if not any(a['role'] == 'genome_alignment_primary' for a in artifacts):
        reports.add('primary_output_missing', '/artifacts', role='genome_alignment_primary', kind='output_bytes')
    for sha, copies in by_digest.items():
        if len(copies) < 2:
            continue
        value['duplicate_representations'].append({'sha256': sha,
            'raw_artifact_refs': list(dict.fromkeys(a['raw_artifact_ref'] for a in copies)),
            'source_refs': list(dict.fromkeys(a['source_ref'] for a in copies)),
            'scientific_identity': 'same_bytes_only'})
        reports.add('duplicate_representation', '/duplicate_representations/' + sha,
                    refs=[a['source_ref'] for a in copies], needed=False)
    value = validate_genome_alignment_associations(value)
    return {'status': 'partial' if reports.requirements or reports.diagnostics else 'ok',
            'value': value, 'requirements': deepcopy(reports.requirements),
            'diagnostics': deepcopy(reports.diagnostics)}


__all__ = ['bind_genome_alignment_artifacts']
