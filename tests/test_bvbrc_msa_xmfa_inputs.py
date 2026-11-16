"""Actual staged-byte checks for the MSA XMFA source handoff."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_alignment_provider_contracts import ASSOCIATION_KEYS
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_msa_xmfa_inputs import verify_xmfa_source_inputs
from gene_annotation_episode.episodic_workflow.root.library.phylogeny_formats import parse_aligned_fasta


def content(data, name='source.fa'):
    return {'source_ref': 'source:' + name, 'artifact_field': 'artifact_ref',
        'artifact_ref': name, 'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data)}


def artifact(data, name='source.fa'):
    value = content(data, name)
    return {'raw_artifact_ref': name, 'source_ref': value['source_ref'], 'sha256': value['sha256']}


def empty_associations():
    return {k: [] for k in ASSOCIATION_KEYS}


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


