"""Check explicitly supplied XMFA source records against selected actual bytes.

Paths are recorded tokens, never files to open. The caller authenticates Content
custody and the common AssociationSet. These functions check the selected byte
content, exact physical source records, and explicit original-member maps.
Saved validators cannot authenticate external custody and never reparse bytes.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import hashlib
import json
import re

from . import xmfa_source_contracts as c
from .bvbrc_alignment_provider_contracts import ASSOCIATION_KEYS, member_key
from .bvbrc_alignment_values import diagnostic, requirement
from .bvbrc_appservice_contracts import validate_contract
from .phylogeny_formats import parse_aligned_fasta
from .xmfa_format_contracts import validate_xmfa_document
from .xmfa_sources import bind_xmfa_sources, validate_xmfa_bindings_for_document

_PREFIX = 'bvbrc_msa_xmfa_'
_VERIFICATION_FIELDS = {'supplied_inputs', 'source_readers', 'verified_inputs',
    'files', 'status', 'requirements', 'diagnostics'}
_FILE_FIELDS = {'file_id', 'artifact', 'format', 'reader', 'state', 'requirements', 'diagnostics'}
_BINDING_FIELDS = {'document_id', 'source_comparison', 'verification', 'bindings',
    'state', 'evidence', 'requirements', 'diagnostics'}


def _require(condition, code):
    if not condition:
        raise ValueError(_PREFIX + code)


def _closed(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as error:
            if str(error).startswith(_PREFIX):
                raise
            raise ValueError(_PREFIX + 'dependency_invalid') from error
        except (KeyError, TypeError, IndexError, OverflowError, RecursionError) as error:
            raise ValueError(_PREFIX + 'shape_invalid') from error
    return checked


def _reader_map(readers, inputs):
    _require(type(readers) in (tuple, list), 'reader_array_invalid')
    known = {f['file_id'] for f in inputs['files']}
    result = {}
    for reader in readers:
        _require(type(reader) is dict, 'reader_invalid')
        kind = reader.get('reader')
        if kind == 'fasta_records_for_xmfa_v1':
            _require(set(reader) == {'file_id', 'reader', 'id_rule', 'encoding'}
                and reader['id_rule'] == 'first_whitespace_token'
                and reader['encoding'] in ('ascii', 'utf-8'), 'reader_invalid')
        elif kind == 'raw_dna_for_xmfa_v1':
            _require(set(reader) == {'file_id', 'reader', 'encoding'}
                and reader['encoding'] == 'ascii', 'reader_invalid')
        else:
            raise ValueError(_PREFIX + 'reader_unbound')
        c.text(reader['file_id'])
        _require(reader['file_id'] in known, 'reader_file_unknown')
        _require(reader['file_id'] not in result, 'reader_file_duplicate')
        result[reader['file_id']] = deepcopy(reader)
    return result


def _association_members(associations):
    _require(type(associations) is dict and set(associations) == set(ASSOCIATION_KEYS)
             and all(type(v) is list for v in associations.values()), 'associations_invalid')
    members, transforms = {}, {}
    for member in associations['original_members']:
        key = member_key(member['key'])
        _require(key not in members, 'original_member_duplicate')
        c.integer(member['original_length'], nullable=True)
        members[key] = member
    for transform in associations['transformations']:
        c.text(transform['transformation_id']); c.evidence(transform['evidence'])
        _require(transform['transformation_id'] not in transforms, 'transformation_duplicate')
        _require(type(transform['input_members']) is list, 'transformation_members_invalid')
        for key in transform['input_members']:
            member_key(key)
        transforms[transform['transformation_id']] = transform
    return members, transforms


def _map_problem(mapping, members, transforms):
    member = members.get(member_key(mapping['original_member']))
    transform = transforms.get(mapping['transformation_id'])
    if (member is None or member['original_length'] is None or transform is None
            or not mapping['evidence'] or not transform['evidence']):
        return 'xmfa_original_map_missing'
    if (member['original_length'] != mapping['original_length']
            or mapping['original_member'] not in transform['input_members']):
        return 'xmfa_original_map_conflict'
    return None


def _issue(result, identity, code, *, kind='input_metadata', role='xmfa_staged_source',
           source_refs=()):
    token = hashlib.sha256(json.dumps([identity, code], separators=(',', ':')).encode()).hexdigest()
    result['requirements'].append(requirement('xmfa_verified_source:' + token,
        kind=kind, role=role, source_refs=source_refs, reason_code=code))
    result['diagnostics'].append(diagnostic(code, path='/source_inputs', evidence_refs=source_refs))


def _merge_reports(target, source):
    for field in ('requirements', 'diagnostics'):
        for row in source[field]:
            if row not in target[field]:
                target[field].append(deepcopy(row))


def _raw_record(data, artifact):
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError:
        return None
    sequence = text.replace('\r\n', '').replace('\n', '')
    if c.DNA.fullmatch(sequence) is None:
        return None
    end = max(0, len(data) - 1)
    line_end = 1 + len(re.findall(rb'\r\n|\n', data[:end]))
    return {'entry_1based': 1, 'header': None, 'sequence': sequence,
        'source_location': {'artifact': deepcopy(artifact), 'byte_start_0based': 0,
            'byte_end_0based_exclusive': len(data), 'line_start_1based': 1,
            'line_end_1based_inclusive': line_end, 'xml_path': None}}


def _records_from_bytes(data, file, reader, result):
    if reader['reader'] == 'raw_dna_for_xmfa_v1':
        row = _raw_record(data, file['artifact'])
        return None if row is None else [row]
    parsed = parse_aligned_fasta(data, artifact=file['artifact'],
        id_rule=reader['id_rule'], encoding=reader['encoding'])
    for item in parsed['diagnostics']:
        item = deepcopy(item)
        if item['code'] == 'phylogeny_alignment_lengths_unequal':
            # This is a complete population of unaligned source records.
            item['severity'] = 'qualification'
        result['diagnostics'].append(item)
    if parsed['value'] is None or any(item['severity'] == 'error' for item in result['diagnostics']):
        return None
    return [{'entry_1based': row['row_index'] + 1, 'header': row['raw_header'],
             'sequence': row['sequence'], 'source_location': row['source_location']}
            for row in parsed['value']['rows']]


def _verify_file(file, reader, artifact_bytes, contents):
    result = {'file_id': file['file_id'], 'artifact': deepcopy(file['artifact']),
        'format': file['format'], 'reader': deepcopy(reader), 'state': 'missing_bytes',
        'requirements': [], 'diagnostics': []}
    identity = file['file_id']; artifact = file['artifact']
    references = (artifact['source_ref'],)
    candidates = [v for v in contents if v['artifact_ref'] == artifact['raw_artifact_ref']
                  and v['source_ref'] == artifact['source_ref']]
    payload = artifact_bytes.get(artifact['raw_artifact_ref'])
    if not candidates or payload is None:
        _issue(result, identity, 'xmfa_source_bytes_required', kind='input_bytes', source_refs=references)
        return result
    if (any(v['sha256'] != artifact['sha256'] or v['byte_count'] != len(payload) for v in candidates)
            or hashlib.sha256(payload).hexdigest() != artifact['sha256']):
        result['state'] = 'incompatible'
        _issue(result, identity, 'xmfa_source_record_bytes_conflict', source_refs=references)
        return result
    if file['format'] in ('GenBank', 'DNAstar'):
        result['state'] = 'unsupported'
        _issue(result, identity, 'xmfa_source_extractor_unbound', kind='parser_binding',
               role='xmfa_source_record_extractor', source_refs=references)
        return result
    if reader is None:
        result['state'] = 'unsupported'
        _issue(result, identity, 'xmfa_source_reader_required', kind='parser_binding',
               role='xmfa_source_record_extractor', source_refs=references)
        return result
    expected = 'fasta_records_for_xmfa_v1' if file['format'] == 'FastA' else 'raw_dna_for_xmfa_v1'
    if reader['reader'] != expected:
        result['state'] = 'incompatible'
        _issue(result, identity, 'xmfa_source_record_bytes_conflict', source_refs=references)
        return result
    actual = _records_from_bytes(payload, file, reader, result)
    declared = [{k: v for k, v in row.items() if k != 'record_id'} for row in file['records']]
    if actual is None or actual != declared:
        result['state'] = 'incompatible'
        _issue(result, identity, 'xmfa_source_record_bytes_conflict', source_refs=references)
        return result
    result['state'] = 'verified'
    if file['record_completeness'] != 'complete':
        _issue(result, identity, 'xmfa_input_population_partial', role='xmfa_input_records', source_refs=references)
    return result


@_closed
def verify_xmfa_source_inputs(inputs: dict, *, source_readers: tuple[dict, ...],
        artifact_bytes: dict[str, bytes], content_bindings: tuple[dict, ...], associations: dict) -> dict:
    inputs = c.validate_xmfa_source_inputs(inputs)
    readers = _reader_map(source_readers, inputs)
    members, transforms = _association_members(associations)
    _require(type(artifact_bytes) is dict
        and all(type(k) is str and k and type(v) is bytes for k, v in artifact_bytes.items()), 'bytes_map_invalid')
    _require(type(content_bindings) in (tuple, list), 'content_bindings_invalid')
    contents = [validate_contract('ContentBinding', v) for v in content_bindings]
    verified = {**deepcopy(inputs), 'files': [], 'original_maps': []}
    result = {'supplied_inputs': inputs, 'source_readers': list(deepcopy(source_readers)),
        'verified_inputs': verified, 'files': [], 'status': 'ok', 'requirements': [], 'diagnostics': []}
    for file in inputs['files']:
        checked = _verify_file(file, readers.get(file['file_id']), artifact_bytes, contents)
        result['files'].append(checked); _merge_reports(result, checked)
        if checked['state'] == 'verified':
            verified['files'].append(deepcopy(file))
    file_ids = {f['file_id'] for f in verified['files']}
    for index, mapping in enumerate(inputs['original_maps']):
        issue = _map_problem(mapping, members, transforms)
        if mapping['file_id'] not in file_ids:
            issue = issue or 'xmfa_original_map_missing'
        if issue:
            _issue(result, ['map', index], issue, role='xmfa_original_map')
        else:
            verified['original_maps'].append(deepcopy(mapping))
    if not inputs['files']:
        _issue(result, 'empty', 'xmfa_source_bytes_required', kind='input_bytes')
    if result['requirements']:
        result['status'] = ('invalid' if not verified['files']
            and any(f['state'] == 'incompatible' for f in result['files']) else 'partial')
    return validate_msa_xmfa_source_verification(result, associations=associations)


@_closed
def validate_msa_xmfa_source_verification(value: dict, *, associations: dict | None = None) -> dict:
    c.shape(value, _VERIFICATION_FIELDS)
    supplied = c.validate_xmfa_source_inputs(value['supplied_inputs'])
    verified = c.validate_xmfa_source_inputs(value['verified_inputs'])
    readers = _reader_map(value['source_readers'], supplied)
    c.array(value['files']); c.reports(value)
    _require(value['status'] in ('ok', 'partial', 'invalid'), 'verification_status_invalid')
    _require(supplied['invocation'] == verified['invocation'], 'verified_invocation_conflict')
    _require(len(value['files']) == len(supplied['files']), 'verified_file_population_conflict')
    expected = []
    for source, row in zip(supplied['files'], value['files']):
        c.shape(row, _FILE_FIELDS); c.reports(row)
        _require(all(row[k] == source[k] for k in ('file_id', 'artifact', 'format')),
                 'verified_file_identity_conflict')
        _require(row['reader'] == readers.get(source['file_id']), 'verified_reader_conflict')
        _require(row['state'] in ('verified', 'missing_bytes', 'incompatible', 'unsupported'), 'verified_file_state_invalid')
        _require(all(r in value['requirements'] for r in row['requirements'])
            and all(d in value['diagnostics'] for d in row['diagnostics']), 'file_reports_missing')
        if row['state'] == 'verified':
            expected_reader = {'FastA': 'fasta_records_for_xmfa_v1', 'raw': 'raw_dna_for_xmfa_v1'}.get(source['format'])
            _require(row['reader'] is not None and row['reader']['reader'] == expected_reader,
                     'verified_unbound_format')
            _require(not any(d['severity'] == 'error' for d in row['diagnostics']), 'verified_error_conflict')
            expected.append(source)
        else:
            _require(bool(row['requirements']), 'unverified_requirement_missing')
    _require(verified['files'] == expected, 'verified_file_subset_conflict')
    _require(all(m in supplied['original_maps'] for m in verified['original_maps']), 'verified_map_subset_conflict')
    members, transforms = _association_members(associations) if associations is not None else (None, None)
    if members is not None:
        valid_ids = {f['file_id'] for f in expected}
        expected_maps = [m for m in supplied['original_maps'] if m['file_id'] in valid_ids
                         and _map_problem(m, members, transforms) is None]
        _require(verified['original_maps'] == expected_maps, 'verified_original_map_conflict')
    if len(verified['original_maps']) != len(supplied['original_maps']):
        _require(any(r['role'] == 'xmfa_original_map' for r in value['requirements']), 'omitted_map_requirement_missing')
    expected_status = ('invalid' if not expected and any(f['state'] == 'incompatible' for f in value['files'])
                       else 'partial') if value['requirements'] else 'ok'
    _require(value['status'] == expected_status, 'verification_status_conflict')
    return deepcopy(value)


def _binding_sources_match(bindings, inputs):
    files = {f['file_id']: f for f in inputs['files']}
    _require(bindings['invocation_mode'] == inputs['invocation']['mode']
             and bindings['original_maps'] == inputs['original_maps'], 'binding_inputs_conflict')
    for member in bindings['members']:
        if member['state'] != 'resolved':
            continue
        file = files.get(member['file_id'])
        _require(file is not None and member['native_file_token'] == file['native_path_token'], 'bound_source_missing')
        records = {r['record_id']: r for r in file['records']}
        for component in member['components']:
            row = records.get(component['record_id'])
            start, end = component['member_interval_0based_half_open']
            _require(row is not None and row['entry_1based'] == component['entry_1based']
                and row['sequence'] == member['source_sequence'][start:end], 'bound_record_conflict')


@_closed
def extract_msa_xmfa_bindings(document: dict, *, verification: dict,
        source_comparison: str, evidence: tuple[dict, ...]) -> dict:
    document = validate_xmfa_document(document)
    verification = validate_msa_xmfa_source_verification(verification)
    _require(source_comparison == 'case_insensitive_iupac_exact', 'source_comparison_invalid')
    c.evidence(list(evidence))
    result = {'document_id': document['document_id'], 'source_comparison': source_comparison,
        'verification': verification, 'bindings': None, 'state': 'missing',
        'evidence': list(deepcopy(evidence)), 'requirements': deepcopy(verification['requirements']),
        'diagnostics': deepcopy(verification['diagnostics'])}
    if verification['verified_inputs']['files']:
        bindings = bind_xmfa_sources(document, inputs=verification['verified_inputs'], source_comparison=source_comparison)
        result['bindings'] = validate_xmfa_bindings_for_document(document, bindings)
        _binding_sources_match(bindings, verification['verified_inputs'])
        _merge_reports(result, bindings)
        result['state'] = ('conflicting' if any(m['state'] == 'conflicting' for m in bindings['members'])
                           else 'partial' if result['requirements'] else 'resolved')
    elif verification['status'] == 'invalid':
        result['state'] = 'conflicting'
    return result


@_closed
def validate_msa_xmfa_binding_record(value: dict, *, document: dict, associations: dict) -> dict:
    c.shape(value, _BINDING_FIELDS); c.reports(value); c.evidence(value['evidence'])
    document = validate_xmfa_document(document)
    _require(value['document_id'] == document['document_id'], 'binding_document_conflict')
    _require(value['source_comparison'] == 'case_insensitive_iupac_exact', 'source_comparison_invalid')
    _require(value['state'] in ('resolved', 'partial', 'missing', 'conflicting'), 'binding_state_invalid')
    verification = value['verification']
    if verification is not None:
        verification = validate_msa_xmfa_source_verification(verification, associations=associations)
        _require(all(r in value['requirements'] for r in verification['requirements']), 'binding_requirements_missing')
    if value['bindings'] is not None:
        _require(verification is not None and bool(verification['verified_inputs']['files']), 'binding_verification_missing')
        bindings = validate_xmfa_bindings_for_document(document, value['bindings'])
        _binding_sources_match(bindings, verification['verified_inputs'])
        _require(all(r in value['requirements'] for r in bindings['requirements']), 'binding_requirements_missing')
        expected_state = ('conflicting' if any(m['state'] == 'conflicting' for m in bindings['members'])
                          else 'partial' if value['requirements'] else 'resolved')
        _require(value['state'] == expected_state, 'binding_state_conflict')
    else:
        _require(value['state'] in ('missing', 'partial', 'conflicting') and bool(value['requirements']), 'binding_missing_unqualified')
    return deepcopy(value)


__all__ = ['verify_xmfa_source_inputs', 'extract_msa_xmfa_bindings',
    'validate_msa_xmfa_source_verification', 'validate_msa_xmfa_binding_record']
