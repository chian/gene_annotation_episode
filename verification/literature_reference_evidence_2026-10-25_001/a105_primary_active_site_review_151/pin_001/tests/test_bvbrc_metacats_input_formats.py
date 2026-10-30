from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_metacats_input_formats import parse_metacats_input_fasta
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta
from gene_annotation_episode.phylogeny_format_contracts import validate_alignment_document


NATIVE = Path(__file__).resolve().parents[1] / 'verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases'


def artifact(data):
    return {'raw_artifact_ref': 'original-fasta', 'source_ref': 'original-source',
            'sha256': hashlib.sha256(data).hexdigest()}


def parse(data, **kwargs):
    return parse_metacats_input_fasta(data, artifact=artifact(data), **kwargs)


def codes(result):
    return {d['code'] for d in result['diagnostics']}


def forbidden(*args, **kwargs):
    raise AssertionError('Pure input reading must not acquire or execute work')


def test_original_hashes_and_dashes_are_distinct_and_shared_parser_unchanged():
    data = b'>first\n#-A-C-#\n>second\n--C#A--\n'
    result = parse(data)
    assert result['status'] == 'ok' and not result['diagnostics']
    assert [r['sequence'] for r in result['value']['rows']] == ['#-A-C-#', '--C#A--']
    assert result['value']['observed_column_count'] == 7
    strict = parse_aligned_fasta(data, artifact=artifact(data), id_rule='first_whitespace_token')
    assert strict['status'] == 'partial'
    assert 'phylogeny_alignment_symbol_invalid' in codes(strict)


def test_utf8_crlf_locations_duplicates_and_case_survive_json():
    data = '>α details\r\na#-C\r\n>α second\r\nA#-c'.encode('utf-8')
    result = parse(data, encoding='utf-8')
    assert result['status'] == 'ok'
    rows = result['value']['rows']
    assert [r['member_label'] for r in rows] == ['α', 'α']
    assert [r['sequence'] for r in rows] == ['a#-C', 'A#-c']
    cut = data.index('>α second'.encode('utf-8'))
    assert [(r['source_location']['byte_start_0based'],r['source_location']['byte_end_0based_exclusive']) for r in rows] == [(0,cut),(cut,len(data))]
    assert [(r['source_location']['line_start_1based'],r['source_location']['line_end_1based_inclusive']) for r in rows] == [(1,2),(3,4)]
    saved = json.loads(json.dumps(result, allow_nan=False))
    assert validate_alignment_document(saved['value']) == result['value']


@pytest.mark.parametrize('data,sequence,expected_code', [
    (b'>a\nA\t# C\n', 'A#C', 'alignment_whitespace_ignored'),
    (b'>a\nA1#\n', 'A1#', 'alignment_symbol_invalid'),
    (b'>a\nA\x0b#\n', 'A\x0b#', 'alignment_symbol_invalid'),
    (b'>a\nA\x00#\n', 'A\x00#', 'alignment_symbol_invalid'),
])
def test_formatting_is_qualified_and_invalid_symbols_not_deleted(data,sequence,expected_code):
    result = parse(data)
    assert result['value']['rows'][0]['sequence'] == sequence
    assert 'bvbrc_metacats_input_' + expected_code in codes(result)
    assert result['status'] == ('ok' if expected_code == 'alignment_whitespace_ignored' else 'partial')


def test_original_hash_line_is_sequence_not_comment():
    result = parse(b'>a\n###\n')
    assert result['status'] == 'ok'
    assert result['value']['rows'][0]['sequence'] == '###'
    assert parse(b'###\n')['status'] == 'invalid'


def test_unequal_rows_are_retained_without_padding():
    result = parse(b'>a\nA#-\n>b\nC#\n')
    assert result['status'] == 'partial'
    assert result['value']['observed_column_count'] is None
    assert [r['sequence'] for r in result['value']['rows']] == ['A#-', 'C#']
    assert 'bvbrc_metacats_input_alignment_lengths_unequal' in codes(result)


@pytest.mark.parametrize('data', [b'', b' \r\n', b'AC#\n'])
def test_no_rows_does_not_prove_complete_empty_population(data):
    result = parse(data)
    assert result['status'] == 'invalid'
    assert result['value']['rows'] == []
    assert result['value']['completeness'] == 'partial'


def test_explicit_zero_column_rows_and_empty_header_distinguishable():
    result = parse(b'>a\n>b\n')
    assert result['status'] == 'ok'
    assert result['value']['observed_column_count'] == 0
    bad = parse(b'>\n#\n')
    assert bad['status'] == 'partial'
    assert bad['value']['rows'][0]['member_label'] == ''
    assert bad['value']['rows'][0]['sequence'] == '#'


@pytest.mark.parametrize('kwargs', [{'id_rule':'full_header'}, {'encoding':'latin1'}, {'encoding':None}])
def test_unsupported_parameters(kwargs):
    result = parse(b'>a\nA#\n', **kwargs)
    assert result['status'] == 'invalid' and result['value'] is None


@pytest.mark.parametrize('data,kwargs', [(b'>a\n\xff\n',{}), ('>α\nA#\n'.encode(),{})])
def test_unreadable_encoding_does_not_repair_bytes(data,kwargs):
    result = parse(data, **kwargs)
    assert result['status'] == 'invalid' and result['value'] is None
    assert 'bvbrc_metacats_input_encoding_invalid' in codes(result)


def test_digest_type_and_artifact_checks():
    data = b'>a\nA#\n'
    for supplied in [None, {}, {'raw_artifact_ref':'a','source_ref':'b','sha256':'bad'}]:
        result = parse_metacats_input_fasta(data, artifact=supplied)
        assert result['status'] == 'invalid' and result['value'] is None
    wrong = {**artifact(data), 'sha256':'0'*64}
    assert 'bvbrc_metacats_input_artifact_sha256_mismatch' in codes(parse_metacats_input_fasta(data,artifact=wrong))
    assert 'bvbrc_metacats_input_bytes_required' in codes(parse_metacats_input_fasta(data.decode(),artifact=artifact(data)))


@pytest.mark.parametrize('case,rows,columns', [
    ('official_na',14,765), ('aa_two_groups',12,4), ('aa_three_groups',18,4),
    ('metadata_only_first_group',12,4), ('twelve_groups',48,4),
    ('native_pair_tail_underflow',4000,4), ('all_missing',2,3),
])
def test_retained_component_inputs(case, rows, columns, monkeypatch):
    data = (NATIVE/case/'original.fasta').read_bytes()
    original = artifact(data)
    expected = deepcopy(original)
    with monkeypatch.context() as locked:
        locked.setattr(builtins, 'open', forbidden)
        locked.setattr(Path, 'open', forbidden)
        locked.setattr(Path, 'read_bytes', forbidden)
        locked.setattr(socket, 'socket', forbidden)
        locked.setattr(subprocess, 'Popen', forbidden)
        result = parse_metacats_input_fasta(data, artifact=original)
    assert original == expected
    assert result['status'] == 'ok'
    assert result['value']['observed_row_count'] == rows
    assert result['value']['observed_column_count'] == columns
    assert validate_alignment_document(json.loads(json.dumps(result['value']))) == result['value']
