"""Closed supplied relationships with explicitly synthetic task custody.

FASTA records are parsed from actual in-memory bytes. None of the fabricated
task/evidence envelopes claims a live service run or authentic same-run custody.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import (
    validate_genome_alignment_inputs, validate_genome_alignment_associations,
    validate_genome_alignment_native_member,
)
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta


def content(raw, name):
    return {'source_ref': 'synthetic:source:' + name, 'artifact_field': 'artifact_ref',
        'artifact_ref': 'synthetic:artifact:' + name,
        'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


def evidence(raw=b'{}', name='metadata', pointer=''):
    return {'content': content(raw, name), 'pointer': pointer}


def native_member(index, namespace='mauve1_member_1based'):
    return {'namespace': namespace, 'index': index}


def original_task(genome_ids):
    return {'resource_id': 'synthetic:api', 'task_id': 'synthetic:GenomeAlignment:1',
        'required_application_id': 'GenomeAlignment', 'native_application_id': 'GenomeAlignment',
        'submitted_parameters': {'genome_ids': genome_ids, 'recipe': 'progressiveMauve'},
        'submitted_start_parameters': {}, 'scheduler_returned_parameters': None,
        'effective_parameters': None, 'submission_receipt_ref': 'synthetic:submission',
        'submission_operation_key': 'synthetic:run:launch:0', 'submission_source_ref': 'synthetic:request'}


def input_fixture(mode='multiple_files_concatenated', *, duplicate_genome=False):
    raws = {'f0': b'>one\nACGT\n>two\nAC\n'}
    if mode == 'multiple_files_concatenated':
        raws['f1'] = b'>three\nAAGT\n'
    genomes = ['g0', 'g0' if duplicate_genome else 'g1'][:len(raws)]
    task = original_task(genomes)
    request_data = json.dumps(task['submitted_parameters']).encode()
    invocation_evidence = [evidence(b'progressiveMauve /staged/f0 /staged/f1', 'invocation')]
    value = {'schema_version': 'bvbrc_genome_alignment_inputs_v1', 'original_task': task,
        'genome_occurrences': [{'occurrence_index': i, 'genome_id': genome,
            'parameter_pointer': '/genome_ids/' + str(i), 'input_binding_id': None,
            'evidence': [evidence(request_data, 'request', '/genome_ids/' + str(i))]}
            for i, genome in enumerate(genomes)],
        'invocation': {'requested_recipe': 'progressiveMauve', 'effective_recipe': 'progressiveMauve',
            'recipe_basis': 'observed_argv', 'observed_argv': ['progressiveMauve'] + list(raws),
            'observed_program_version': None, 'mode': mode, 'mode_basis': 'observed_invocation',
            'ordered_file_ids': list(raws), 'evidence': invocation_evidence},
        'files': [], 'member_bindings': [], 'contig_bindings': [], 'feature_bindings': [],
        'original_maps': [], 'xmfa_source_inputs': None, 'genome_census_state': 'unknown',
        'requirements': [], 'diagnostics': []}
    for i, (file_id, raw) in enumerate(raws.items()):
        c = content(raw, file_id)
        a = {'source_ref': c['source_ref'], 'raw_artifact_ref': c['artifact_ref'], 'sha256': c['sha256']}
        parsed = parse_aligned_fasta(raw, artifact=a, id_rule='first_whitespace_token', encoding='ascii')
        records = [{'record_id': file_id + ':' + str(r['row_index']), 'entry_1based': r['row_index'] + 1,
            'header': r['raw_header'], 'sequence': r['sequence'], 'source_location': r['source_location']}
            for r in parsed['value']['rows']]
        value['files'].append({'file_id': file_id, 'native_path_token': '/staged/' + file_id,
            'path_state': 'bound', 'artifact': a, 'content': c, 'format': 'FastA',
            'genome_occurrence_indices': [i], 'same_run_state': 'bound', 'record_completeness': 'complete',
            'records': records, 'retrieval': {'query': None, 'requested_record_limit': 25000,
                'reported_total_records': None, 'returned_records': len(records), 'state': 'unknown',
                'evidence': []}, 'path_evidence': invocation_evidence, 'same_run_evidence': invocation_evidence,
            'requirement_ids': []})
    sources = [(f, f['records']) for f in value['files']] if mode == 'multiple_files_concatenated' else [
        (value['files'][0], [r]) for r in value['files'][0]['records']]
    for index, (file, records) in enumerate(sources):
        components, offset = [], 0
        for record in records:
            length = len(record['sequence'])
            components.append({'file_id': file['file_id'], 'record_id': record['record_id'],
                'member_interval_0based_half_open': [offset, offset + length],
                'record_interval_0based_half_open': [0, length]})
            offset += length
        value['member_bindings'].append({'member': native_member(index + 1), 'state': 'bound',
            'genome_occurrence_indices': file['genome_occurrence_indices'], 'components': components,
            'source_length': offset, 'evidence': invocation_evidence, 'requirement_ids': []})
    return value, raws


def artifact_member(role, fmt, name):
    c = content(b'native retained fixture bytes', name)
    return {'role': role, 'source_ref': c['source_ref'], 'raw_artifact_ref': c['artifact_ref'],
        'sha256': c['sha256'], 'byte_count': c['byte_count'],
        'workspace_object': {'path': '/synthetic/' + name, 'uuid': 'synthetic:object:' + name,
            'type': 'file', 'metadata_receipt_ref': None},
        'task_association': {'kind': 'task_result_manifest', 'evidence_ref': 'synthetic:manifest',
            'pointer': '', 'task_id': 'synthetic:GenomeAlignment:1', 'output_path': '/synthetic/' + name,
            'output_uuid': 'synthetic:object:' + name, 'byte_version_status': 'current_bytes_observed',
            'version_evidence': []},
        'transfer': {'receipt_ref': 'synthetic:download:' + name, 'body_complete': True,
            'requested_range': None, 'observed_range': None, 'total_size': c['byte_count'],
            'object_complete': 'yes'},
        'declared_format': {'format': fmt, 'version': None, 'mode': None,
            'producer_source_ref': None, 'transformation_evidence': []}}


def association_fixture():
    value = {'schema_version': 'bvbrc_genome_alignment_associations_v1',
        'original_task': original_task(['g0', 'g1']), 'artifacts': [], 'native_member_joins': [],
        'bbcols_interval_joins': [], 'duplicate_representations': [], 'requirements': [], 'diagnostics': []}
    for role, fmt, name in [('genome_alignment_primary', 'mauve1_xmfa', 'xmfa'),
                            ('genome_alignment_bbcols', 'mauve_bbcols', 'bbcols')]:
        a = artifact_member(role, fmt, name)
        value['artifacts'].append({'artifact': a, 'role': role, 'observed_format': fmt,
            'document_id': name, 'state': 'bound', 'evidence': [evidence()], 'requirement_ids': []})
        value['native_member_joins'].append({'artifact': {k: a[k] for k in
            ('raw_artifact_ref', 'source_ref', 'sha256')},
            'member': native_member(1) if name == 'xmfa' else native_member(0, 'mauve_sidecar_member_0based'),
            'input_member': native_member(1), 'state': 'bound', 'evidence': [evidence()], 'requirement_ids': []})
    value['bbcols_interval_joins'].append({'bbcols_document_id': 'bbcols', 'native_interval_index_0based': 7,
        'xmfa_document_id': 'xmfa', 'xmfa_block_index': 0, 'state': 'bound',
        'evidence': [evidence()], 'requirement_ids': []})
    return value


@pytest.mark.parametrize('mode,lengths', [('multiple_files_concatenated', [6, 4]), ('single_file_entries', [4, 2])])
def test_same_native_ordinal_has_mode_specific_input_membership(mode, lengths):
    value, _ = input_fixture(mode)
    before = deepcopy(value)
    checked = validate_genome_alignment_inputs(value)
    assert [m['source_length'] for m in checked['member_bindings']] == lengths
    assert checked['genome_census_state'] == 'unknown'
    checked['files'][0]['records'][0]['sequence'] = 'changed copy'
    assert value == before


def test_duplicate_genome_ids_retain_distinct_original_occurrences():
    value, _ = input_fixture(duplicate_genome=True)
    checked = validate_genome_alignment_inputs(value)
    assert [r['genome_id'] for r in checked['genome_occurrences']] == ['g0', 'g0']
    assert [r['genome_occurrence_indices'] for r in checked['member_bindings']] == [[0], [1]]


@pytest.mark.parametrize('mutation', ['bool_index', 'missing_key', 'unknown_key', 'reordered_occurrences',
    'wrong_pointer', 'wrong_member_offset', 'wrong_source_span', 'wrong_length', 'missing_record',
    'foreign_record', 'wrong_hash', 'wrong_byte_bounds', 'wrong_recipe', 'unknown_file',
    'unverified_run', 'unbound_length', 'incomplete_census', 'invented_requirement'])
def test_input_relationship_corruption_is_rejected(mutation):
    v, _ = input_fixture()
    if mutation == 'bool_index': v['member_bindings'][0]['member']['index'] = True
    elif mutation == 'missing_key': del v['files'][0]['content']
    elif mutation == 'unknown_key': v['files'][0]['trust_me'] = True
    elif mutation == 'reordered_occurrences': v['genome_occurrences'].reverse()
    elif mutation == 'wrong_pointer': v['genome_occurrences'][0]['parameter_pointer'] = '/genome_ids/1'
    elif mutation == 'wrong_member_offset': v['member_bindings'][0]['components'][1]['member_interval_0based_half_open'] = [3, 5]
    elif mutation == 'wrong_source_span': v['member_bindings'][0]['components'][1]['record_interval_0based_half_open'] = [1, 3]
    elif mutation == 'wrong_length': v['member_bindings'][0]['source_length'] = 7
    elif mutation == 'missing_record': v['member_bindings'][0]['components'].pop()
    elif mutation == 'foreign_record': v['member_bindings'][0]['components'][0]['record_id'] = 'f1:0'
    elif mutation == 'wrong_hash': v['files'][0]['content']['sha256'] = '0' * 64
    elif mutation == 'wrong_byte_bounds': v['files'][0]['records'][0]['source_location']['byte_end_0based_exclusive'] = 999
    elif mutation == 'wrong_recipe': v['invocation']['requested_recipe'] = 'mauveAligner'
    elif mutation == 'unknown_file': v['invocation']['ordered_file_ids'][0] = 'absent'
    elif mutation == 'unverified_run': v['files'][0]['same_run_state'] = 'unverified'
    elif mutation == 'unbound_length': v['member_bindings'][0]['state'] = 'unverified'
    elif mutation == 'incomplete_census': v['genome_census_state'] = 'complete'
    else: v['member_bindings'][0]['requirement_ids'] = ['not-declared']
    with pytest.raises(ValueError):
        validate_genome_alignment_inputs(v)


def test_explicit_missing_input_keeps_other_member_and_original_occurrences():
    v, _ = input_fixture()
    v['files'][0].update(artifact=None, content=None, records=[], same_run_state='missing',
                         record_completeness='unknown', requirement_ids=['missing:f0'])
    v['member_bindings'][0].update(state='missing', source_length=None, components=[], requirement_ids=['missing:f0'])
    v['requirements'] = [{'requirement_id': 'missing:f0', 'kind': 'input_bytes',
        'role': 'genome_alignment_staged_input', 'source_refs': [],
        'reason_code': 'bvbrc_genome_alignment_staged_file_missing'}]
    checked = validate_genome_alignment_inputs(v)
    assert [m['source_length'] for m in checked['member_bindings']] == [None, 4]
    assert len(checked['genome_occurrences']) == 2
    assert checked['requirements'] == v['requirements']


def test_neutral_projection_requires_exact_original_records_and_maps():
    v, _ = input_fixture()
    v['xmfa_source_inputs'] = {'schema_version': 'mauve_xmfa_source_inputs_v1',
        'invocation': {k: deepcopy(v['invocation'][k]) for k in ('mode', 'ordered_file_ids', 'evidence')},
        'files': [{k: deepcopy(f[k]) for k in ('file_id', 'native_path_token', 'artifact', 'format',
            'record_completeness', 'records')} | {'path_binding_evidence': deepcopy(f['path_evidence'])}
            for f in v['files']], 'original_maps': []}
    assert validate_genome_alignment_inputs(v) == v
    v['xmfa_source_inputs']['files'][0]['records'][0]['sequence'] = 'TTTT'
    with pytest.raises(ValueError, match='source_sequence_mismatch'):
        validate_genome_alignment_inputs(v)


def add_feature(v):
    e = [evidence()]
    occurrence = {'input_binding_id': 'gene-input', 'member_id': 'gene', 'occurrence_index': 0}
    segment = {'segment_id': 's0', 'file_id': 'f0', 'record_id': 'f0:0',
        'feature_interval_0based_half_open': [0, 3], 'record_interval_0based_half_open': [1, 4],
        'strand': '-', 'transformation_id': 'explicit-reverse', 'evidence': e}
    v['feature_bindings'] = [{'feature': occurrence, 'original_length': 3,
        'genome_occurrence_index': 0, 'segments': [segment], 'state': 'bound',
        'evidence': e, 'requirement_ids': []}]
    v['original_maps'] = [{'file_id': 'f0', 'record_id': 'f0:0',
        'staged_interval_0based_half_open': [1, 4], 'original_member': occurrence,
        'original_length': 3, 'original_interval_0based_half_open': [0, 3],
        'strand': '-', 'transformation_id': 'explicit-reverse', 'evidence': e}]


def test_feature_maps_preserve_reverse_coordinate_transform_and_reject_foreign_population():
    v, _ = input_fixture()
    add_feature(v)
    assert validate_genome_alignment_inputs(v) == v
    v['feature_bindings'][0]['genome_occurrence_index'] = 1
    with pytest.raises(ValueError, match='genome_occurrence_conflict'):
        validate_genome_alignment_inputs(v)


def test_unrepresented_original_map_cannot_bypass_feature_binding():
    v, _ = input_fixture()
    add_feature(v)
    v['feature_bindings'] = []
    with pytest.raises(ValueError, match='feature_map_conflict'):
        validate_genome_alignment_inputs(v)


def test_documented_complete_census_is_distinct_from_complete_returned_file():
    v, _ = input_fixture()
    for f in v['files']:
        f['retrieval'].update(reported_total_records=len(f['records']), state='complete', evidence=[evidence()])
    v['genome_census_state'] = 'complete'
    assert validate_genome_alignment_inputs(v)['genome_census_state'] == 'complete'


def test_native_interval_ordinal_and_exported_block_index_need_not_equal():
    v = association_fixture()
    checked = validate_genome_alignment_associations(v)
    assert checked['bbcols_interval_joins'][0]['native_interval_index_0based'] == 7
    assert checked['bbcols_interval_joins'][0]['xmfa_block_index'] == 0
    checked['bbcols_interval_joins'].clear()
    assert v['bbcols_interval_joins']


@pytest.mark.parametrize('mutation', ['foreign_task', 'wrong_role', 'wrong_format', 'foreign_artifact',
    'duplicate_join', 'missing_join_evidence', 'unknown_document', 'missing_block_index',
    'duplicate_interval', 'unbound_primary', 'unknown_requirement', 'invented_duplicate',
    'declared_format_conflict', 'declared_version_conflict', 'member_namespace_conflict', 'aliased_block'])
def test_invalid_association_is_not_a_usable_member_or_block_join(mutation):
    v = association_fixture()
    if mutation == 'foreign_task': v['artifacts'][0]['artifact']['task_association']['task_id'] = 'foreign'
    elif mutation == 'wrong_role': v['artifacts'][0]['artifact']['role'] = 'genome_alignment_backbone'
    elif mutation == 'wrong_format': v['artifacts'][0]['observed_format'] = 'mauve_bbcols'
    elif mutation == 'foreign_artifact': v['native_member_joins'][0]['artifact']['source_ref'] = 'foreign'
    elif mutation == 'duplicate_join': v['native_member_joins'].append(deepcopy(v['native_member_joins'][0]))
    elif mutation == 'missing_join_evidence': v['bbcols_interval_joins'][0]['evidence'] = []
    elif mutation == 'unknown_document': v['bbcols_interval_joins'][0]['xmfa_document_id'] = 'unknown'
    elif mutation == 'missing_block_index': v['bbcols_interval_joins'][0]['xmfa_block_index'] = None
    elif mutation == 'duplicate_interval': v['bbcols_interval_joins'].append(deepcopy(v['bbcols_interval_joins'][0]))
    elif mutation == 'unbound_primary': v['artifacts'][0]['state'] = 'unverified'
    elif mutation == 'unknown_requirement': v['bbcols_interval_joins'][0]['requirement_ids'] = ['absent']
    elif mutation == 'declared_format_conflict': v['artifacts'][0]['artifact']['declared_format']['format'] = 'mauve_v4'
    elif mutation == 'declared_version_conflict': v['artifacts'][0]['artifact']['declared_format']['version'] = '4'
    elif mutation == 'member_namespace_conflict': v['native_member_joins'][0]['member'] = native_member(0, 'mauve_v4_member_0based')
    elif mutation == 'aliased_block':
        row = deepcopy(v['bbcols_interval_joins'][0])
        row['native_interval_index_0based'] = 8
        v['bbcols_interval_joins'].append(row)
    else: v['duplicate_representations'] = [{'sha256': '0' * 64, 'raw_artifact_refs': ['absent'],
        'source_refs': ['absent'], 'scientific_identity': 'same_bytes_only'}]
    with pytest.raises(ValueError):
        validate_genome_alignment_associations(v)


def test_unknown_block_join_is_preserved_without_false_index_zero():
    v = association_fixture()
    v['bbcols_interval_joins'][0].update(xmfa_document_id=None, xmfa_block_index=None, state='missing', evidence=[])
    assert validate_genome_alignment_associations(v)['bbcols_interval_joins'][0]['xmfa_block_index'] is None


def test_same_bytes_preserves_both_original_representations():
    v = association_fixture()
    artifacts = [r['artifact'] for r in v['artifacts']]
    v['duplicate_representations'] = [{'sha256': artifacts[0]['sha256'],
        'raw_artifact_refs': [a['raw_artifact_ref'] for a in artifacts],
        'source_refs': [a['source_ref'] for a in artifacts], 'scientific_identity': 'same_original_task_bytes'}]
    assert len(validate_genome_alignment_associations(v)['artifacts']) == 2


@pytest.mark.parametrize('index,namespace', [(0, 'mauve1_member_1based'), (True, 'mauve_v4_member_0based'),
    (1.0, 'mauve_sidecar_member_0based'), (1, 'unqualified')])
def test_native_ordinal_namespace_and_json_integer_type_are_explicit(index, namespace):
    with pytest.raises(ValueError):
        validate_genome_alignment_native_member(native_member(index, namespace))


def test_saved_validation_uses_no_io_native_program_or_parser(monkeypatch):
    v, _ = input_fixture()
    associations = association_fixture()
    before = deepcopy(v)

    def forbidden(*args, **kwargs):
        raise AssertionError('saved contract validation attempted I/O or parsing')

    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', forbidden)
    assert validate_genome_alignment_inputs(v) == before
    assert validate_genome_alignment_associations(associations) == associations
