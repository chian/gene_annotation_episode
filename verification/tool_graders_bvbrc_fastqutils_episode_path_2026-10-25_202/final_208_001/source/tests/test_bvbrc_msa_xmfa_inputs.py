"""Actual staged-byte checks for the MSA XMFA source handoff."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_alignment_associations import extract_alignment_associations
from gene_annotation_episode.bvbrc_alignment_provider_contracts import ASSOCIATION_KEYS
from gene_annotation_episode.bvbrc_msa_xmfa_inputs import (
    verify_xmfa_source_inputs, extract_msa_xmfa_bindings,
    validate_msa_xmfa_source_verification, validate_msa_xmfa_binding_record,
)
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'
SAVED = ROOT / 'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples'


def content(data, name='source.fa'):
    return {'source_ref': 'source:' + name, 'artifact_field': 'artifact_ref',
        'artifact_ref': name, 'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data)}


def artifact(data, name='source.fa'):
    value = content(data, name)
    return {'raw_artifact_ref': name, 'source_ref': value['source_ref'], 'sha256': value['sha256']}


def empty_associations():
    return {k: [] for k in ASSOCIATION_KEYS}


def native_operands(case='combined_native'):
    saved = json.loads((SAVED / (case + '-inputs.json')).read_text())
    sources = saved['inputs']
    data = {f['artifact']['raw_artifact_ref']: (NATIVE / f['file_id']).read_bytes() for f in sources['files']}
    contents = tuple(content(data[f['file_id']], f['file_id']) for f in sources['files'])
    readers = tuple({'file_id': f['file_id'], 'reader': 'fasta_records_for_xmfa_v1',
        'id_rule': 'first_whitespace_token', 'encoding': 'ascii'} for f in sources['files'])
    return saved['document'], {'inputs': sources, 'source_readers': readers,
        'artifact_bytes': data, 'content_bindings': contents, 'associations': empty_associations()}


def fasta_operands(data=b'>one\nACG\n>two\nAT\n', *, encoding='ascii'):
    a = artifact(data)
    parsed = parse_aligned_fasta(data, artifact=a, id_rule='first_whitespace_token', encoding=encoding)
    records = [] if parsed['value'] is None else [{
        'record_id': 'entry:' + str(r['row_index']), 'entry_1based': r['row_index'] + 1,
        'header': r['raw_header'], 'sequence': r['sequence'], 'source_location': r['source_location']}
        for r in parsed['value']['rows']]
    inputs = {'schema_version': 'mauve_xmfa_source_inputs_v1',
        'invocation': {'mode': 'single_file_entries', 'ordered_file_ids': ['f'],
            'evidence': [{'content': content(data), 'pointer': ''}]},
        'files': [{'file_id': 'f', 'native_path_token': 'source.fa', 'artifact': a,
            'format': 'FastA', 'record_completeness': 'complete',
            'path_binding_evidence': [{'content': content(data), 'pointer': ''}], 'records': records}],
        'original_maps': []}
    return {'inputs': inputs, 'source_readers': ({'file_id': 'f', 'reader': 'fasta_records_for_xmfa_v1',
        'id_rule': 'first_whitespace_token', 'encoding': encoding},), 'artifact_bytes': {'source.fa': data},
        'content_bindings': (content(data),), 'associations': empty_associations()}


def raw_operands(data=b'acg\r\nTNN\n', *, sequence='acgTNN', line_end=2):
    operands = fasta_operands()
    a = artifact(data)
    file = operands['inputs']['files'][0]
    file.update(artifact=a, format='raw', records=[{'record_id': 'raw', 'entry_1based': 1,
        'header': None, 'sequence': sequence, 'source_location': {'artifact': a,
            'byte_start_0based': 0, 'byte_end_0based_exclusive': len(data),
            'line_start_1based': 1, 'line_end_1based_inclusive': line_end, 'xml_path': None}}])
    operands.update(source_readers=({'file_id': 'f', 'reader': 'raw_dna_for_xmfa_v1', 'encoding': 'ascii'},),
        artifact_bytes={'source.fa': data}, content_bindings=(content(data),))
    return operands


def reasons(result):
    return {r['reason_code'] for r in result['requirements']}


def binding(document, verification):
    return extract_msa_xmfa_bindings(document, verification=verification,
        source_comparison='case_insensitive_iupac_exact', evidence=())


@pytest.mark.parametrize('case,lengths', [('combined_native', [50, 41, 49]), ('separate_native', [50, 49, 41])])
def test_retained_native_files_validate_and_bind_all_record_bytes(case, lengths):
    document, operands = native_operands(case)
    before = deepcopy(operands)
    verified = verify_xmfa_source_inputs(**operands)
    assert verified['status'] == 'ok'
    assert verified['verified_inputs'] == operands['inputs']
    assert all(f['state'] == 'verified' for f in verified['files'])
    result = binding(document, verified)
    assert result['state'] == 'resolved'
    assert [m['source_length'] for m in result['bindings']['members']] == lengths
    assert all(r['state'] in ('match', 'absent_zero') for r in result['bindings']['source_checks'])
    assert validate_msa_xmfa_binding_record(result, document=document, associations=operands['associations']) == result
    assert operands == before
    verified['supplied_inputs']['files'][0]['records'][0]['header'] = 'changed-return'
    assert operands == before


@pytest.mark.parametrize('change', ['sequence', 'header', 'location', 'order', 'omit_last'])
def test_authenticated_json_claim_is_not_proof_of_matching_native_record_bytes(change):
    document, operands = native_operands()
    rows = operands['inputs']['files'][0]['records']
    if change == 'sequence':
        rows[0]['sequence'] = 'A' + rows[0]['sequence'][1:]
    elif change == 'header':
        rows[0]['header'] = 'different header'
    elif change == 'location':
        rows[0]['source_location']['byte_end_0based_exclusive'] -= 1
    elif change == 'order':
        for key in ('header', 'sequence', 'source_location'):
            rows[0][key], rows[1][key] = rows[1][key], rows[0][key]
    else:
        rows.pop()
    result = verify_xmfa_source_inputs(**operands)
    assert result['status'] == 'invalid' and result['verified_inputs']['files'] == []
    assert result['supplied_inputs'] == operands['inputs']
    assert 'xmfa_source_record_bytes_conflict' in reasons(result)
    assert binding(document, result)['bindings'] is None


@pytest.mark.parametrize('change', ['no_bytes', 'no_content', 'foreign_source', 'wrong_digest', 'wrong_count', 'changed_bytes'])
def test_content_binding_and_actual_bytes_both_required(change):
    _, operands = native_operands()
    if change == 'no_bytes':
        operands['artifact_bytes'] = {}
    elif change == 'no_content':
        operands['content_bindings'] = ()
    elif change == 'foreign_source':
        operands['content_bindings'][0]['source_ref'] = 'unrelated'
    elif change == 'wrong_digest':
        operands['content_bindings'][0]['sha256'] = '0' * 64
    elif change == 'wrong_count':
        operands['content_bindings'][0]['byte_count'] += 1
    else:
        operands['artifact_bytes']['combined.fa'] += b'\n'
    result = verify_xmfa_source_inputs(**operands)
    assert result['verified_inputs']['files'] == []
    expected = 'xmfa_source_bytes_required' if change in ('no_bytes', 'no_content', 'foreign_source') else 'xmfa_source_record_bytes_conflict'
    assert expected in reasons(result)


def test_one_bad_source_does_not_discard_other_verified_sources_or_invocation_order():
    document, operands = native_operands('separate_native')
    operands['artifact_bytes'].pop('canFam2.fa')
    result = verify_xmfa_source_inputs(**operands)
    assert result['status'] == 'partial'
    assert [f['file_id'] for f in result['verified_inputs']['files']] == ['equCab1.fa', 'mm9.fa']
    assert result['verified_inputs']['invocation']['ordered_file_ids'] == ['equCab1.fa', 'canFam2.fa', 'mm9.fa']
    answer = binding(document, result)
    assert [m['source_length'] for m in answer['bindings']['members']] == [50, None, 41]
    assert answer['state'] == 'partial'


@pytest.mark.parametrize('data,encoding', [(b'>one\nACG\n>two\nAT\n', 'ascii'),
    (b'>repeat\nacg\n>repeat\nACT\n', 'ascii'), ('>séquence\r\nAC G\r\nTT\n'.encode(), 'utf-8')])
def test_source_records_preserve_unequal_lengths_duplicate_headers_and_explicit_layout(data, encoding):
    operands = fasta_operands(data, encoding=encoding)
    result = verify_xmfa_source_inputs(**operands)
    assert result['status'] == 'ok'
    assert result['verified_inputs']['files'][0]['records'] == operands['inputs']['files'][0]['records']
    if b'AC G' in data:
        assert any(d['code'] == 'phylogeny_alignment_whitespace_ignored' for d in result['diagnostics'])
    if b'>two' in data:
        assert any(d['code'] == 'phylogeny_alignment_lengths_unequal' and d['severity'] == 'qualification' for d in result['diagnostics'])


@pytest.mark.parametrize('data', [b'orphan\n>a\nAC\n', b'>\nAC\n', b'', b'>a\nA!\n', b'>a\nA\xff\n'])
def test_malformed_source_file_cannot_be_verified_by_a_clean_claim(data):
    operands = fasta_operands(b'>a\nAC\n')
    a = artifact(data)
    file = operands['inputs']['files'][0]; file['artifact'] = a
    for row in file['records']:
        row['source_location']['artifact'] = a
    operands.update(artifact_bytes={'source.fa': data}, content_bindings=(content(data),))
    result = verify_xmfa_source_inputs(**operands)
    assert result['files'][0]['state'] == 'incompatible'
    assert result['verified_inputs']['files'] == []


@pytest.mark.parametrize('data,sequence,line_end', [(b'acg\r\nTNN\n', 'acgTNN', 2),
    (b'ACGT', 'ACGT', 1), (b'', '', 1), (b'\n\n', '', 2)])
def test_raw_dna_exact_line_endings_full_file_and_empty_record(data, sequence, line_end):
    operands = raw_operands(data, sequence=sequence, line_end=line_end)
    result = verify_xmfa_source_inputs(**operands)
    assert result['status'] == 'ok'
    assert result['verified_inputs']['files'][0]['records'][0]['sequence'] == sequence


@pytest.mark.parametrize('data', [b'AC GT', b'AC\tGT', b'AC\rGT', b'AC1GT', b'AC-GT', b'AC#GT', b'>a\nACGT', b'ACUGT', b'AC\xffGT'])
def test_raw_dna_never_strips_biological_or_undocumented_characters(data):
    result = verify_xmfa_source_inputs(**raw_operands(data, sequence='ACGT', line_end=1))
    assert result['status'] == 'invalid'
    assert 'xmfa_source_record_bytes_conflict' in reasons(result)


@pytest.mark.parametrize('format', ['GenBank', 'DNAstar'])
def test_unbound_source_formats_keep_claims_and_specific_extractor_requirement(format):
    operands = fasta_operands(); operands['inputs']['files'][0]['format'] = format
    operands['source_readers'] = ()
    result = verify_xmfa_source_inputs(**operands)
    assert result['files'][0]['state'] == 'unsupported'
    assert result['verified_inputs']['files'] == [] and result['supplied_inputs'] == operands['inputs']
    assert any(r['kind'] == 'parser_binding' and r['role'] == 'xmfa_source_record_extractor'
        and r['reason_code'] == 'xmfa_source_extractor_unbound' for r in result['requirements'])


def test_explicit_reader_and_complete_source_record_population_are_independent_requirements():
    operands = fasta_operands(); operands['source_readers'] = ()
    assert 'xmfa_source_reader_required' in reasons(verify_xmfa_source_inputs(**operands))
    operands = fasta_operands(); operands['inputs']['files'][0]['record_completeness'] = 'partial'
    result = verify_xmfa_source_inputs(**operands)
    assert result['files'][0]['state'] == 'verified'
    assert result['status'] == 'partial' and 'xmfa_input_population_partial' in reasons(result)


@pytest.mark.parametrize('change', ['duplicate', 'unknown_file', 'encoding', 'unknown_reader', 'extra'])
def test_reader_contract_does_not_guess_or_accept_arbitrary_dispatch(change):
    operands = fasta_operands()
    if change == 'duplicate':
        operands['source_readers'] += deepcopy(operands['source_readers'])
    elif change == 'unknown_file':
        operands['source_readers'][0]['file_id'] = 'other'
    elif change == 'encoding':
        operands['source_readers'][0]['encoding'] = 'auto'
    elif change == 'unknown_reader':
        operands['source_readers'][0]['reader'] = 'arbitrary_callable'
    else:
        operands['source_readers'][0]['extra'] = True
    with pytest.raises(ValueError, match='bvbrc_msa_xmfa_'):
        verify_xmfa_source_inputs(**operands)


def original_associations():
    data = '>same\n' + 'A' * 100 + '\n>same\n' + 'A' * 100 + '\n'
    inp = {'binding_id': 'original', 'parameter_pointer': '/fasta', 'kind': 'inline_parameter',
        'content': None, 'workspace_path': None, 'inline_value': data, 'link_evidence': None, 'members': []}
    keys = [{'input_binding_id': 'original', 'member_id': 'same', 'occurrence_index': i} for i in range(2)]
    ev = [{'content': content(b'explicit original map', 'mapping'), 'pointer': ''}]
    declarations = {'common': {'version': 'bvbrc_alignment_associations_v1', 'analysis_id': 'a',
        'input_sequences': [{'kind': 'inline_fasta', 'input_binding_id': 'original',
            'id_rule': 'first_whitespace_token', 'encoding': 'ascii', 'molecule': 'dna', 'evidence': []}],
        'row_joins': [], 'automatic_row_joins': [], 'correspondences': [], 'feature_genomes': [],
        'source_records': [], 'member_entities': [], 'transformations': [{
            'transformation_id': 'mapped-original', 'kind': 'identity', 'input_members': keys,
            'input_rows': [], 'output_rows': [], 'evidence': ev}]}, 'functions': None, 'taxonomy': None}
    parsed = extract_alignment_associations(inputs=(inp,), documents=(), declarations=declarations)
    assert parsed['value'] is not None, parsed
    return parsed['value']


def add_maps(operands):
    operands['associations'] = original_associations()
    file = operands['inputs']['files'][0]
    record = file['records'][0]
    operands['inputs']['original_maps'] = [{
        'file_id': file['file_id'], 'record_id': record['record_id'],
        'staged_interval_0based_half_open': [0, 50], 'original_member': m['key'],
        'original_length': 100, 'original_interval_0based_half_open': [10, 60], 'strand': '+',
        'transformation_id': 'mapped-original',
        'evidence': operands['associations']['transformations'][0]['evidence']}
        for m in operands['associations']['original_members']]


def test_full_original_occurrence_identity_preserves_two_distinct_maps():
    document, operands = native_operands(); add_maps(operands)
    result = verify_xmfa_source_inputs(**operands)
    assert result['status'] == 'ok' and len(result['verified_inputs']['original_maps']) == 2
    returned = binding(document, result)
    assert returned['state'] == 'resolved'
    assert [m['original_member']['occurrence_index'] for m in returned['bindings']['original_maps']] == [0, 1]
    assert validate_msa_xmfa_binding_record(returned, document=document, associations=operands['associations']) == returned


@pytest.mark.parametrize('change', ['unknown_member', 'wrong_length', 'unknown_length', 'unknown_transform', 'unrelated_transform', 'missing_map_evidence'])
def test_missing_or_conflicting_original_map_does_not_discard_source_bytes(change):
    document, operands = native_operands(); add_maps(operands)
    mapping = operands['inputs']['original_maps'][0]
    if change == 'unknown_member':
        mapping['original_member'] = {**mapping['original_member'], 'occurrence_index': 2}
    elif change == 'wrong_length':
        mapping['original_length'] = 99
    elif change == 'unknown_length':
        operands['associations']['original_members'][0]['original_length'] = None
    elif change == 'unknown_transform':
        mapping['transformation_id'] = 'unrecorded'
    elif change == 'unrelated_transform':
        operands['associations']['transformations'][0]['input_members'].pop(0)
    else:
        mapping['evidence'] = []
    result = verify_xmfa_source_inputs(**operands)
    assert result['status'] == 'partial' and len(result['verified_inputs']['files']) == 1
    assert len(result['verified_inputs']['original_maps']) == 1
    assert len(result['supplied_inputs']['original_maps']) == 2
    returned = binding(document, result)
    assert returned['state'] == 'partial'
    assert [m['source_length'] for m in returned['bindings']['members']] == [50, 41, 49]


@pytest.mark.parametrize('change', ['invent_verified_file', 'changed_verified_sequence', 'reader', 'status', 'deleted_requirement'])
def test_saved_verification_checks_closed_associations_and_effective_input_subset(change):
    _, operands = native_operands(); operands['artifact_bytes'] = {}
    result = verify_xmfa_source_inputs(**operands)
    if change == 'invent_verified_file':
        result['verified_inputs']['files'] = deepcopy(result['supplied_inputs']['files'])
    elif change == 'changed_verified_sequence':
        _, operands = native_operands(); result = verify_xmfa_source_inputs(**operands)
        result['verified_inputs']['files'][0]['records'][0]['sequence'] = 'A' * 50
    elif change == 'reader':
        result['files'][0]['reader']['encoding'] = 'utf-8'
    elif change == 'status':
        result['status'] = 'ok'
    else:
        result['requirements'] = []
    with pytest.raises(ValueError, match='bvbrc_msa_xmfa_'):
        validate_msa_xmfa_source_verification(result, associations=operands['associations'])


def test_saved_binding_rechecks_document_and_source_records_without_reparse(monkeypatch):
    document, operands = native_operands()
    verified = verify_xmfa_source_inputs(**operands); expected = binding(document, verified)
    before = deepcopy((operands, document, expected))
    def forbidden(*args, **kwargs):
        raise AssertionError('forbidden I/O or parser during saved validation')
    with monkeypatch.context() as locked:
        locked.setattr('builtins.open', forbidden)
        for name in ('open', 'read_bytes', 'read_text', 'write_bytes', 'write_text'):
            locked.setattr(Path, name, forbidden)
        locked.setattr(socket, 'socket', forbidden); locked.setattr(socket, 'create_connection', forbidden)
        locked.setattr(subprocess, 'Popen', forbidden)
        locked.setattr('gene_annotation_episode.bvbrc_msa_xmfa_inputs.parse_aligned_fasta', forbidden)
        locked.setattr('gene_annotation_episode.xmfa_formats.parse_mauve_xmfa', forbidden)
        restored = json.loads(json.dumps(expected))
        assert validate_msa_xmfa_binding_record(restored, document=document, associations=operands['associations']) == expected
        assert binding(document, verified) == expected
        restored['bindings']['members'][0]['source_sequence'] = 'A' * 50
        with pytest.raises(ValueError, match='bvbrc_msa_xmfa_'):
            validate_msa_xmfa_binding_record(restored, document=document, associations=operands['associations'])
    assert (operands, document, expected) == before


def test_byte_verifier_uses_supplied_bytes_with_files_network_and_subprocess_forbidden(monkeypatch):
    _, operands = native_operands(); expected = verify_xmfa_source_inputs(**operands)
    def forbidden(*args, **kwargs):
        raise AssertionError('supplied-byte verifier attempted acquisition')
    with monkeypatch.context() as locked:
        locked.setattr('builtins.open', forbidden); locked.setattr(Path, 'open', forbidden)
        locked.setattr(Path, 'read_bytes', forbidden); locked.setattr(socket, 'socket', forbidden)
        locked.setattr(subprocess, 'Popen', forbidden)
        assert verify_xmfa_source_inputs(**operands) == expected


def test_saved_binding_rejects_changed_declared_invocation_order():
    document, operands = native_operands('separate_native')
    result = binding(document, verify_xmfa_source_inputs(**operands))
    for field in ('supplied_inputs', 'verified_inputs'):
        result['verification'][field]['invocation']['ordered_file_ids'].reverse()
    with pytest.raises(ValueError, match='bvbrc_msa_xmfa_'):
        validate_msa_xmfa_binding_record(result, document=document, associations=operands['associations'])


def test_saved_empty_source_verification_cannot_claim_success():
    _, operands = native_operands()
    operands['inputs']['files'] = []; operands['source_readers'] = ()
    result = verify_xmfa_source_inputs(**operands)
    result.update(requirements=[], diagnostics=[], status='ok')
    with pytest.raises(ValueError, match='bvbrc_msa_xmfa_'):
        validate_msa_xmfa_source_verification(result, associations=operands['associations'])
