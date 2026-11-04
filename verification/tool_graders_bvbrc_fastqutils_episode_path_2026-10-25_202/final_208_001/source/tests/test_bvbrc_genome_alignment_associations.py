"""Actual native formats with explicitly synthetic task/receipt custody.

These tests do not establish a live BV-BRC task or host possession. They use
complete current receipt shapes, canonical stored envelopes and actual bytes.
"""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_genome_alignment_associations import bind_genome_alignment_artifacts
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_associations
from gene_annotation_episode.bvbrc_genome_alignment_inputs import validate_genome_alignment_retained_records
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.mauve_v4_formats import parse_mauve_v4
from gene_annotation_episode.mauve_backbone_formats import parse_mauve_backbone, parse_mauve_bbcols
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
from test_bvbrc_genome_alignment_retained_records import (
    fixture, acquisition_record, log_record, rewrap, content, inline,
)
from test_mauve_v4_formats import OFFICIAL as V4_NATIVE


PREFIX = 'bvbrc_genome_alignment_'
NATIVE_DIR = Path(__file__).resolve().parents[1] / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'


def update_acquisition(row, data, *, role=None, fmt=None, path=None, uuid=None,
                       object_type=None, association=None, object_selection=None):
    value = row['record']['value']; artifact = value['artifact']
    native = value['snapshot']['selected_operands']['native_operands']
    args, selected = native['arguments'], native['selector']
    if role is not None:
        artifact['role'] = args['role'] = selected['requirements'][0]['role'] = role
    if fmt is not None:
        artifact['declared_format']['format'] = fmt
        args['declared_format']['format'] = fmt
        selected['requirements'][0]['declared_format']['format'] = fmt
    for key, val in (('path', path), ('uuid', uuid), ('type', object_type)):
        if val is not None:
            artifact['workspace_object'][key] = val
    if association is not None:
        artifact['task_association'] = deepcopy(association)
    if object_selection is not None:
        value['object_selection'] = deepcopy(object_selection)
        args['object'] = deepcopy(object_selection)
        selected['requirements'][0]['exact_object'] = deepcopy(object_selection)
    value['selector_sha256'] = digest(selected)
    value['snapshot']['selected_operands']['arguments_sha256'] = digest(args)
    value['origin']['arguments_sha256'] = digest(args)
    return rewrap(row, data)


def native_case(fmt='mauve_v4'):
    task, request, handoff, data = fixture(recipe='mauveAligner' if fmt == 'mauve_v4' else 'progressiveMauve')
    if fmt == 'mauve_v4':
        raw, role = V4_NATIVE.read_bytes(), 'genome_alignment_primary'
    elif fmt == 'mauve1_xmfa':
        raw, role = (NATIVE_DIR / 'separate.xmfa').read_bytes(), 'genome_alignment_primary'
    elif fmt == 'mauve_backbone':
        raw, role = (NATIVE_DIR / 'separate.xmfa.backbone').read_bytes(), 'genome_alignment_backbone'
    else:
        raw, role = (NATIVE_DIR / 'separate.xmfa.bbcols').read_bytes(), 'genome_alignment_bbcols'
    output = acquisition_record(task, request, data, raw=raw, name='native-output')
    artifact = output['record']['value']['artifact']
    output_path, output_uuid = '/synthetic/result/native', '11111111-1111-1111-1111-111111111111'
    manifest_uuid = '22222222-2222-2222-2222-222222222222'
    manifest_raw = canonical({'id': task['task_id'], 'app': {'id': 'GenomeAlignment'},
        'parameters': deepcopy(task['submitted_parameters']), 'success': 1,
        'output_files': [[output_path, output_uuid]]}).encode()
    manifest = acquisition_record(task, request, data, raw=manifest_raw, name='manifest')
    info = log_record(task, request, data, raw=(manifest_uuid + '\n').encode(),
                      file='job_result_id', name='manifest-info')
    manifest = update_acquisition(manifest, data, role='task_manifest', fmt='json',
        path='/synthetic/result/manifest', uuid=manifest_uuid, object_type='job_result',
        association={'kind': 'task_info_object', 'evidence_ref': info['record']['source_ref'],
            'pointer': '/reported_object_uuid', 'task_id': task['task_id'],
            'output_path': '/synthetic/result/manifest', 'output_uuid': manifest_uuid,
            'byte_version_status': 'unknown', 'version_evidence': []},
        object_selection={'kind': 'task_info_object', 'receipt_ref': info['record']['source_ref']})
    output = update_acquisition(output, data, role=role, fmt=fmt, path=output_path, uuid=output_uuid,
        association={'kind': 'task_result_manifest',
            'evidence_ref': manifest['record']['value']['artifact']['source_ref'],
            'pointer': '/output_files/0', 'task_id': task['task_id'], 'output_path': output_path,
            'output_uuid': output_uuid, 'byte_version_status': 'unknown', 'version_evidence': []},
        object_selection={'kind': 'manifest_member', 'manifest_receipt_ref': manifest['record']['source_ref'], 'output_index': 0})
    artifact = deepcopy(output['record']['value']['artifact'])
    identity = {k: artifact[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256')}
    if fmt == 'mauve_v4':
        result = parse_mauve_v4(raw, artifact=identity, encoding='ascii')
    elif fmt == 'mauve1_xmfa':
        result = parse_mauve_xmfa(raw, artifact=identity, dialect='mauve1', alphabet='dna', encoding='ascii')
    elif fmt == 'mauve_backbone':
        result = parse_mauve_backbone(raw, artifact=identity, dialect='libmems_signed_coordinate_pairs_v1', encoding='ascii')
    else:
        result = parse_mauve_bbcols(raw, artifact=identity, dialect='libmems_interval_columns_members_v1', encoding='ascii')
    parsed = {'artifact': identity, 'format': fmt, 'parse_status': result['status'],
              'document': result['value'], 'diagnostics': result['diagnostics']}
    return {'original_task': task, 'artifacts': (artifact,), 'parsed_artifacts': (parsed,),
        'supplied_values': (), 'inputs': None, 'supplied_bytes': data,
        'retained_records': (handoff, info, manifest, output)}


def bind(case):
    return bind_genome_alignment_artifacts(**case)


def codes(result):
    return {r['reason_code'] for r in result['requirements']}


@pytest.mark.parametrize('fmt,members,namespace', [
    ('mauve_v4', 2, 'mauve_v4_member_0based'),
    ('mauve1_xmfa', 3, 'mauve1_member_1based'),
    ('mauve_backbone', 3, 'mauve_sidecar_member_0based'),
    ('mauve_bbcols', 3, 'mauve_sidecar_member_0based'),
])
def test_native_manifest_object_and_all_native_members_without_invented_run_joins(fmt, members, namespace):
    case = native_case(fmt); before = deepcopy(case)
    validate_genome_alignment_retained_records(case['original_task'],
        retained_records=case['retained_records'], supplied_bytes=case['supplied_bytes'])
    result = bind(case); value = result['value']
    assert result['status'] == 'partial'
    assert value['artifacts'][0]['state'] == 'bound'
    assert value['artifacts'][0]['artifact']['task_association']['byte_version_status'] == 'unknown'
    assert len(value['native_member_joins']) == members
    assert all(r['member']['namespace'] == namespace and r['input_member'] is None
               and r['state'] == 'unverified' for r in value['native_member_joins'])
    assert PREFIX + 'artifact_version_unverified' in codes(result)
    assert case == before
    assert validate_genome_alignment_associations(value) == value
    if fmt == 'mauve_bbcols':
        assert [(r['native_interval_index_0based'], r['xmfa_block_index'], r['state'])
                for r in value['bbcols_interval_joins']] == [(0, None, 'missing')]


@pytest.mark.parametrize('problem', ['no_records', 'no_manifest', 'bad_manifest', 'wrong_task',
                                     'wrong_format', 'missing_bytes', 'changed_bytes'])
def test_local_artifact_failures_preserve_observed_native_document(problem):
    case = native_case()
    if problem == 'no_records': case['retained_records'] = ()
    elif problem == 'no_manifest': case['retained_records'] = case['retained_records'][:2] + case['retained_records'][3:]
    elif problem == 'bad_manifest':
        manifest = case['retained_records'][2]
        case['supplied_bytes'][manifest['record']['value']['snapshot']['content']['artifact_ref']] += b'x'
    elif problem == 'wrong_task': case['artifacts'][0]['task_association']['task_id'] = 'another-task'
    elif problem == 'wrong_format': case['artifacts'][0]['declared_format']['format'] = 'mauve1_xmfa'
    elif problem == 'missing_bytes': del case['supplied_bytes'][case['artifacts'][0]['raw_artifact_ref']]
    else: case['supplied_bytes'][case['artifacts'][0]['raw_artifact_ref']] += b'x'
    result = bind(case)
    assert result['status'] == 'partial'
    assert result['value']['artifacts'][0]['state'] != 'bound'
    assert result['value']['artifacts'][0]['document_id'] == case['parsed_artifacts'][0]['document']['document_id']
    assert len(result['value']['native_member_joins']) == 2


def test_bad_neighbor_receipt_does_not_discard_valid_manifest_and_acquisition():
    case = native_case()
    bad = deepcopy(case['retained_records'][1])
    bad['record']['source_ref'] = bad['receipt_content']['source_ref'] = 'synthetic:bad-neighbor'
    case['retained_records'] += (bad,)
    result = bind(case)
    assert result['value']['artifacts'][0]['state'] == 'bound'
    assert PREFIX + 'metadata_record_unverified' in codes(result)


def test_conflicting_duplicate_reference_disables_its_entire_group():
    case = native_case()
    bad = deepcopy(case['retained_records'][-1])
    bad['record']['value']['snapshot']['retrieved_at'] = '2026-10-25T01:00:00Z'
    bad = rewrap(bad, case['supplied_bytes'])
    case['retained_records'] += (bad,)
    result = bind(case)
    assert result['value']['artifacts'][0]['state'] == 'unverified'
    assert sum(r['reason_code'] == PREFIX + 'metadata_record_unverified'
               for r in result['requirements']) >= 3


def test_identical_duplicate_receipt_is_not_duplicate_scientific_evidence():
    case = native_case(); one = bind(case)
    case['retained_records'] += (deepcopy(case['retained_records'][-1]),)
    assert bind(case) == one


def test_identical_output_bytes_keep_both_acquisitions_without_independence_claim():
    case = native_case(); original = case['artifacts'][0]
    request = case['retained_records'][0]['record']['value']['receipt']['snapshot']['selected_operands']['native_operands']['request']
    raw = case['supplied_bytes'][original['raw_artifact_ref']]
    second = acquisition_record(case['original_task'], request, case['supplied_bytes'], raw=raw, name='second-acquisition')
    second = update_acquisition(second, case['supplied_bytes'], role=original['role'], fmt='mauve_v4',
        path=original['workspace_object']['path'], uuid=original['workspace_object']['uuid'],
        association=original['task_association'],
        object_selection=case['retained_records'][-1]['record']['value']['object_selection'])
    artifact = second['record']['value']['artifact']
    identity = {k: artifact[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256')}
    native = parse_mauve_v4(raw, artifact=identity, encoding='ascii')
    case['retained_records'] += (second,)
    case['artifacts'] += (artifact,)
    case['parsed_artifacts'] += ({'artifact': identity, 'format': 'mauve_v4',
        'parse_status': native['status'], 'document': native['value'], 'diagnostics': native['diagnostics']},)
    result = bind(case)['value']
    assert [a['state'] for a in result['artifacts']] == ['bound', 'bound']
    assert len(result['native_member_joins']) == 4
    assert result['duplicate_representations'] == [{
        'sha256': original['sha256'], 'raw_artifact_refs': [original['raw_artifact_ref']],
        'source_refs': [original['source_ref'], artifact['source_ref']], 'scientific_identity': 'same_bytes_only'}]


def test_missing_primary_preserves_an_explicit_empty_association():
    case = native_case(); case['artifacts'] = case['parsed_artifacts'] = ()
    result = bind(case)
    assert result['status'] == 'partial' and result['value']['artifacts'] == []
    assert PREFIX + 'primary_output_missing' in codes(result)


def test_different_original_input_bindings_cannot_borrow_handoff_identity():
    case = native_case(); changed = deepcopy(case['retained_records'][-1])
    selected = changed['record']['value']['snapshot']['selected_operands']
    request = selected['native_operands']['request']
    request['input_bindings'] = [inline('different-original-binding', '/genome_ids/0', '123.1')]
    selected['request_sha256'] = digest(request)
    changed = rewrap(changed, case['supplied_bytes'])
    # It has valid individual fields and bytes, but disagrees with the actual
    # admitted handoff on a part of the request omitted from OriginalTask.
    validate_genome_alignment_retained_records(case['original_task'],
        retained_records=(changed,), supplied_bytes=case['supplied_bytes'])
    case['retained_records'] = case['retained_records'][:-1] + (changed,)
    result = bind(case)
    assert PREFIX + 'metadata_task_conflict' in codes(result)
    assert result['value']['artifacts'][0]['state'] == 'unverified'
    assert len(result['value']['native_member_joins']) == 2


@pytest.mark.parametrize('missing_index', [1, 2])
def test_missing_task_info_or_manifest_is_unverified_not_conflicting(missing_index):
    case = native_case()
    case['retained_records'] = tuple(row for i, row in enumerate(case['retained_records'])
                                     if i != missing_index)
    result = bind(case)
    assert result['value']['artifacts'][0]['state'] == 'unverified'
    assert PREFIX + 'metadata_record_unverified' in codes(result)
    assert PREFIX + 'artifact_task_conflict' not in codes(result)


def test_actual_reported_manifest_uuid_conflict_is_not_missing():
    case = native_case()
    request = case['retained_records'][0]['record']['value']['receipt']['snapshot']['selected_operands']['native_operands']['request']
    info = log_record(case['original_task'], request, case['supplied_bytes'],
        raw=b'33333333-3333-3333-3333-333333333333\n', file='job_result_id', name='manifest-info')
    case['retained_records'] = (case['retained_records'][0], info) + case['retained_records'][2:]
    result = bind(case)
    assert result['value']['artifacts'][0]['state'] == 'conflicting'
    assert PREFIX + 'artifact_task_conflict' in codes(result)


def test_selected_download_object_cannot_claim_another_manifest_row():
    case = native_case(); output = deepcopy(case['retained_records'][-1])
    selection = deepcopy(output['record']['value']['object_selection'])
    selection['output_index'] = 1
    output = update_acquisition(output, case['supplied_bytes'], object_selection=selection)
    case['retained_records'] = case['retained_records'][:-1] + (output,)
    result = bind(case)
    assert result['value']['artifacts'][0]['state'] == 'conflicting'
    assert PREFIX + 'artifact_task_conflict' in codes(result)


def test_both_c_extractors_consume_same_actual_receipts_and_preserve_native_quantities():
    from gene_annotation_episode.bvbrc_genome_alignment_inputs import extract_genome_alignment_inputs
    from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments
    from test_mauve_v4_calculators import selection
    case = native_case()
    extracted = extract_genome_alignment_inputs(case['original_task'],
        supplied_values=case['supplied_values'], supplied_bytes=case['supplied_bytes'],
        retained_records=case['retained_records'])
    case['inputs'] = extracted['value']
    result = bind(case)
    assert result['value']['artifacts'][0]['state'] == 'bound'
    assert [r['genome_id'] for r in extracted['value']['genome_occurrences']] == ['123.1', '456.2']
    assert extracted['value']['genome_census_state'] == 'unknown'
    assert all(r['input_member'] is None for r in result['value']['native_member_joins'])
    document = case['parsed_artifacts'][0]['document']
    native = calculate_mauve_v4_segments(document,
        selection=selection(document, denominator='native_declared_length'), inputs=extracted['value'])
    assert [(r['known_union_bases']['value'], r['denominator_bases']['value'])
            for r in native['coverage']] == [(690, 693), (2000, 2000)]
    source = calculate_mauve_v4_segments(document,
        selection=selection(document, denominator='validated_staged_length'), inputs=extracted['value'])
    assert [r['known_union_bases']['value'] for r in source['coverage']] == [690, 2000]
    assert all(r['coverage_fraction']['value'] is None for r in source['coverage'])


def test_folder_membership_does_not_become_original_producer_association():
    case = native_case(); acq = case['retained_records'][-1]
    association = deepcopy(case['artifacts'][0]['task_association'])
    association['kind'] = 'task_info_folder_member'
    acq = update_acquisition(acq, case['supplied_bytes'], association=association)
    case['retained_records'] = case['retained_records'][:-1] + (acq,)
    case['artifacts'] = (deepcopy(acq['record']['value']['artifact']),)
    result = bind(case)
    assert result['value']['artifacts'][0]['state'] == 'unverified'


def test_unknown_metadata_and_exact_asserted_interval_map_are_not_native_witnesses():
    case = native_case('mauve_bbcols')
    artifact = case['parsed_artifacts'][0]['artifact']
    assertion = {'kind': 'genome_alignment_interval_mapping', 'original_task_id': case['original_task']['task_id'],
        'bbcols_artifact': artifact, 'xmfa_artifact': {**artifact, 'raw_artifact_ref': 'synthetic:other'},
        'mappings': [{'native_interval_index_0based': 0, 'xmfa_block_index': 0}],
        'omitted_native_interval_indices': []}
    raw = canonical(assertion).encode(); binding = content(raw, 'claimed-map')
    case['supplied_bytes'][binding['artifact_ref']] = raw
    case['supplied_values'] = ({'evidence': {'content': binding, 'pointer': ''}, 'value': assertion},)
    result = bind(case)
    row = result['value']['bbcols_interval_joins'][0]
    assert row['state'] == 'unverified' and row['xmfa_block_index'] is None
    assert PREFIX + 'metadata_record_unverified' in codes(result)
    other = {'message': 'this is unrelated retained JSON'}
    raw = canonical(other).encode(); binding = content(raw, 'unrelated')
    case['supplied_bytes'][binding['artifact_ref']] = raw
    case['supplied_values'] = ({'evidence': {'content': binding, 'pointer': ''}, 'value': other},)
    assert PREFIX + 'metadata_type_unsupported' in codes(bind(case))


@pytest.mark.parametrize('field,value', [('artifacts', []), ('parsed_artifacts', []),
    ('supplied_values', []), ('supplied_bytes', {'bad': 'not bytes'}), ('retained_records', [])])
def test_malformed_caller_is_not_silently_converted_to_partial(field, value):
    case = native_case(); case[field] = value
    with pytest.raises(ValueError, match=PREFIX): bind(case)


def test_no_input_output_network_process_or_native_reparse_during_association(monkeypatch):
    from gene_annotation_episode import mauve_v4_formats, mauve_backbone_formats, xmfa_formats
    from gene_annotation_episode import mauve_v4_calculators, mauve_backbone_calculators, xmfa_calculators
    case = native_case()
    def forbidden(*args, **kwargs): raise AssertionError('forbidden I/O/native parse')
    for target, name in ((builtins, 'open'), (Path, 'open'), (socket, 'socket'),
                         (subprocess, 'Popen')):
        monkeypatch.setattr(target, name, forbidden)
    for target, name in ((mauve_v4_formats, 'parse_mauve_v4'),
        (mauve_backbone_formats, 'parse_mauve_backbone'), (mauve_backbone_formats, 'parse_mauve_bbcols'),
        (xmfa_formats, 'parse_mauve_xmfa'), (mauve_v4_calculators, 'calculate_mauve_v4_segments'),
        (mauve_backbone_calculators, 'calculate_mauve_backbone_components'),
        (mauve_backbone_calculators, 'calculate_mauve_bbcols_components'),
        (xmfa_calculators, 'xmfa_alignment_components'), (xmfa_calculators, 'xmfa_interval_coverage')):
        monkeypatch.setattr(target, name, forbidden)
    assert bind(case)['value']['artifacts'][0]['state'] == 'bound'
