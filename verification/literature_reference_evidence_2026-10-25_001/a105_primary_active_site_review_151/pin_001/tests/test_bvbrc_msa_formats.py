"""Retained native and deliberately synthetic MSA table contract checks."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_alignment_values import document_id
from gene_annotation_episode.bvbrc_msa_format_contracts import (
    frequency_header, validate_msa_frequency_table,
)
from gene_annotation_episode.bvbrc_msa_formats import parse_msa_frequency_table


NATIVE = Path(__file__).resolve().parents[1] / 'verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/native_examples'


def artifact(data, label='synthetic-table'):
    return {'raw_artifact_ref': label, 'source_ref': 'test:' + label,
            'sha256': hashlib.sha256(data).hexdigest()}


def read(data, alphabet='dna', layout='current_without_reference', encoding='ascii'):
    return parse_msa_frequency_table(data, artifact=artifact(data), alphabet=alphabet,
                                     layout=layout, encoding=encoding)


def dna(*rows):
    return ('\t'.join(frequency_header('dna', 'current_without_reference')) + '\n' +
            '\n'.join(rows) + '\n').encode('ascii')


def protein(*rows):
    return ('\t'.join(frequency_header('protein', 'current_without_reference')) + '\n' +
            '\n'.join(rows) + '\n').encode('utf-8')


@pytest.mark.parametrize('alphabet,position,expected', [('dna', 1, 92), ('protein', 3, 100)])
def test_retained_native_tokens_exact_ranges_and_detached_values(alphabet, position, expected):
    data = (NATIVE / alphabet / 'foma.table').read_bytes()
    result = read(data, alphabet)
    assert result['status'] == 'ok'
    table = result['value']
    assert table['rows'][position]['score']['value'] == expected
    for row in table['rows']:
        values = [row['alignment_position'], row['score'], row['n_sequences']]
        values += list(row['dna_counts'].values()) if alphabet == 'dna' else [d['count'] for d in row['protein_detail']]
        for value in values:
            loc = value['source_location']
            assert data[loc['byte_start_0based']:loc['byte_end_0based_exclusive']].decode('ascii') == value['raw_token']
            assert loc['line_start_1based'] == row['row_index'] + 2
    original = deepcopy(table)
    validated = validate_msa_frequency_table(table)
    validated['rows'][0]['score']['value'] = 99
    assert table == original


@pytest.mark.parametrize('alphabet', ['dna', 'protein'])
def test_explicit_with_reference_layout_and_gap_coordinates(alphabet):
    # Deliberate synthetic wrapper output; the underlying unmodified table is
    # native retained output. A full service invocation is not represented.
    lines = (NATIVE / alphabet / 'foma.table').read_text().splitlines()
    output = ['\t'.join(frequency_header(alphabet, 'current_with_reference'))]
    for index, line in enumerate(lines[1:]):
        fields = line.split('\t')
        fields[1:1] = ['' if index == 1 else str(index + 1 if index == 0 else index)]
        fields[3:3] = ['-' if index == 1 else 'A']
        output.append('\t'.join(fields))
    data = ('\n'.join(output) + '\n').encode()
    result = read(data, alphabet, 'current_with_reference')
    assert result['status'] == 'ok'
    row = result['value']['rows'][1]
    assert row['reference_position']['state'] == 'missing'
    assert row['reference_position']['raw_token'] == ''
    assert row['reference_character'] == '-'
    assert result['value']['rows'][2]['reference_position']['value'] == 2
    assert read(data, alphabet)['status'] == 'invalid'


@pytest.mark.parametrize('token,state,kind,value', [
    ('', 'missing', 'blank', None), ('NA', 'not_measured', 'native_na', None),
    ('NaN', 'failed', 'nonfinite', None), ('Inf', 'failed', 'nonfinite', None),
    ('broken', 'failed', 'malformed', None), ('1e-9999', 'failed', 'underflow', None),
    ('1.2', 'incompatible', 'finite', 1.2), ('-1', 'incompatible', 'finite', -1),
])
def test_missing_and_invalid_count_tokens_retained(token, state, kind, value):
    result = read(dna('1\t0\tA\t' + token + '\t0\t0\t0\t0\t1'))
    assert result['status'] == 'partial'
    number = result['value']['rows'][0]['dna_counts']['A']
    assert (number['raw_token'], number['state'], number['token_kind'], number['value']) == (token, state, kind, value)
    validate_msa_frequency_table(result['value'])


def test_score_overflow_native_zero_and_large_exact_integer_counts():
    result = read(dna('1\t1e9999\tA\t9007199254740993\t0\t0\t0\t0\t9007199254740993'))
    row = result['value']['rows'][0]
    assert row['score']['token_kind'] == 'overflow' and row['score']['value'] is None
    assert row['dna_counts']['A']['value'] == 9007199254740993
    assert type(row['dna_counts']['A']['value']) is int
    assert row['dna_counts']['T']['value'] == 0 and row['dna_counts']['T']['state'] == 'available'


@pytest.mark.parametrize('detail,residue,symbol,count,state', [
    ('Del=2', 'Del', '-', 2, 'available'), ('Xaa=2', 'Xaa', 'X', 2, 'available'),
    ('Mystery=2', 'Mystery', None, 2, 'available'), ('=2', '', None, 2, 'available'),
    ('Ala', 'Ala', None, None, 'missing'), ('123', '123', None, None, 'missing'),
    ('', '', None, None, 'missing'), ('Gly=bad', 'Gly', 'G', None, 'failed'),
])
def test_protein_detail_semantics_preserve_unknown_and_malformed(detail, residue, symbol, count, state):
    result = read(protein('1\t0\tXaa\t' + detail + '\t2'), 'protein')
    entry = result['value']['rows'][0]['protein_detail'][0]
    assert entry['raw_token'] == detail and entry['raw_residue_token'] == residue
    assert entry['symbol'] == symbol and entry['count']['value'] == count
    assert entry['count']['state'] == state
    if symbol is None or state != 'available':
        assert result['status'] == 'partial'
    if '=' not in detail:
        assert entry['count']['source_location']['byte_start_0based'] == entry['count']['source_location']['byte_end_0based_exclusive']
        assert any(d['code'].endswith('malformed_detail') for d in result['diagnostics'])


def test_all_native_protein_spellings_decode_in_order():
    residues = ['Del', 'Ala', 'Cys', 'Asp', 'Glu', 'Phe', 'Gly', 'His', 'Ile', 'Lys', 'Leu',
                'Met', 'Asn', 'Pro', 'Gln', 'Arg', 'Ser', 'Thr', 'Val', 'Trp', 'Xaa', 'Tyr']
    row = read(protein('1\t446\tXaa\t' + ','.join(s + '=1' for s in residues) + '\t22'), 'protein')['value']['rows'][0]
    assert ''.join(r['symbol'] for r in row['protein_detail']) == '-ACDEFGHIKLMNPQRSTVWXY'


def test_ragged_rows_preserve_original_ordinals_and_readable_rows():
    data = dna('1\t0\tA\t1\t0\t0\t0\t0\t1', '2\t0',
               '3\t0\tC\t0\t0\t0\t1\t0\t1', '4\t0\tA\t1\t0\t0\t0\t0\t1\textra')
    result = read(data)
    assert result['status'] == 'partial'
    assert result['value']['completeness'] == 'truncated'
    assert [row['row_index'] for row in result['value']['rows']] == [0, 2]
    assert result['value']['rows'][1]['source_location']['line_start_1based'] == 4


def test_duplicate_positions_retained_and_qualified():
    result = read(dna('1\t0\tA\t1\t0\t0\t0\t0\t1', '1\t90\tA\t1\t0\t0\t0\t0\t1'))
    assert result['status'] == 'partial'
    assert len(result['value']['rows']) == 2
    assert any(d['code'].endswith('duplicate_native_coordinate') for d in result['diagnostics'])


def test_header_only_is_readable_empty_and_final_newline_not_required():
    header = '\t'.join(frequency_header('dna', 'current_without_reference')).encode()
    assert read(header)['status'] == 'ok'
    assert read(header)['value']['rows'] == []
    data = dna('1\t0\tA\t1\t0\t0\t0\t0\t1').rstrip(b'\n')
    assert read(data)['value']['completeness'] == 'complete'


@pytest.mark.parametrize('data', [b'', b'not a native header\n', b'Position\tScore\n', b'\xff'])
def test_unreadable_data_is_invalid_null(data):
    result = read(data)
    assert result['status'] == 'invalid' and result['value'] is None


def test_bad_digest_and_caller_contract_misuse_are_distinct():
    data = dna('1\t0\tA\t1\t0\t0\t0\t0\t1')
    wrong = artifact(data)
    wrong['sha256'] = '0' * 64
    assert parse_msa_frequency_table(data, artifact=wrong, alphabet='dna', layout='current_without_reference', encoding='ascii')['status'] == 'invalid'
    for arguments in ({'alphabet': 'rna'}, {'layout': 'guess'}, {'encoding': 'latin-1'}):
        options = dict(artifact=artifact(data), alphabet='dna', layout='current_without_reference', encoding='ascii')
        options.update(arguments)
        with pytest.raises(ValueError):
            parse_msa_frequency_table(data, **options)


def test_utf8_ranges_and_crlf_original_byte_offsets():
    data = protein('1\t0\tXaa\tMystéry=2\t2').replace(b'\n', b'\r\n')
    result = read(data, 'protein', encoding='utf-8')
    entry = result['value']['rows'][0]['protein_detail'][0]
    loc = entry['count']['source_location']
    assert data[loc['byte_start_0based']:loc['byte_end_0based_exclusive']] == b'2'
    assert entry['raw_residue_token'] == 'Mystéry'
    assert read(data, 'protein')['status'] == 'invalid'


@pytest.mark.parametrize('mutation', ['extra_key', 'digest', 'number', 'number_state', 'position_type', 'symbol', 'row_index', 'range'])
def test_saved_table_validator_rejects_mutated_relationships(mutation):
    table = read(protein('1\t0\tGly\tGly=2\t2'), 'protein')['value']
    if mutation == 'extra_key': table['extra'] = 1
    elif mutation == 'digest': table['artifact']['sha256'] = '0' * 64
    elif mutation == 'number': table['rows'][0]['score']['value'] = 99
    elif mutation == 'number_state': table['rows'][0]['n_sequences']['state'] = 'incompatible'
    elif mutation == 'position_type': table['rows'][0]['alignment_position']['value'] = 1.0
    elif mutation == 'symbol': table['rows'][0]['protein_detail'][0]['symbol'] = 'A'
    elif mutation == 'row_index': table['rows'][0]['row_index'] = True
    elif mutation == 'range': table['rows'][0]['score']['source_location']['byte_end_0based_exclusive'] += 1
    with pytest.raises(ValueError): validate_msa_frequency_table(table)


def test_table_identity_includes_declared_encoding():
    data = dna('1\t0\tA\t1\t0\t0\t0\t0\t1')
    first, second = read(data), read(data, encoding='utf-8')
    assert first['value']['table_id'] != second['value']['table_id']
    assert first['value']['table_id'] == document_id('msa_frequency_table', artifact=artifact(data),
        parameters={'alphabet': 'dna', 'layout': 'current_without_reference', 'encoding': 'ascii'})


@pytest.mark.parametrize('alphabet,expected_positions', [('dna', [1, 2, 3, 4, 5, None, None]),
                                                       ('protein', [1, 2, 3, None, 4, 5])])
def test_retained_execution_of_actual_native_reference_branch(alphabet, expected_positions):
    directory = NATIVE.parents[1] / 'tool_graders_bvbrc_msa_pure_2026-10-25/native_reference' / alphabet
    data = (directory / 'retained.snp.tsv').read_bytes()
    result = read(data, alphabet, 'current_with_reference')
    assert result['status'] == 'ok'
    assert [r['reference_position']['value'] for r in result['value']['rows']] == expected_positions
    assert [r['reference_character'] for r in result['value']['rows']] == list(
        'AACGT--' if alphabet == 'dna' else 'ACD-EF')


@pytest.mark.parametrize('data,alphabet', [(dna('1\t0\tA\t3\t0\t0\t0\t0\t2'), 'dna'),
    (protein('1\t0\tGly\tGly=3\t2'), 'protein'), (protein('1\t0\tGly\tGly=1\t2'), 'protein')])
def test_contradictory_native_totals_are_retained_with_qualification(data, alphabet):
    result = read(data, alphabet)
    assert result['status'] == 'partial'
    assert result['value']['rows'][0]['n_sequences']['value'] == 2
    assert any(d['code'].endswith('native_count_total_conflict') for d in result['diagnostics'])


def test_saved_row_ordinal_cannot_diverge_from_original_line():
    table = read(dna('1\t0\tA\t1\t0\t0\t0\t0\t1'))['value']
    table['rows'][0]['row_index'] = 10
    with pytest.raises(ValueError, match='row_line_ordinal_conflict'):
        validate_msa_frequency_table(table)


def test_saved_source_text_must_match_declared_encoding():
    table = read(dna('1\t0\tA\t1\t0\t0\t0\t0\t1'))['value']
    table['rows'][0]['consensus_token'] = 'é'
    with pytest.raises(ValueError, match='encoding_conflict'):
        validate_msa_frequency_table(table)
