"""Native upstream examples and explicit malformed Mauve1 counterexamples."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_alignment_values import document_id, validate_native_number
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa, NATIVE_DIAGNOSTIC_CODES
from gene_annotation_episode.xmfa_format_contracts import validate_xmfa_document, CALLER_ERROR_CODES


NATIVE = Path(__file__).resolve().parents[1] / 'verification' / 'tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25' / 'native_examples'
PREFIX = '#FormatVersion Mauve1\n'


def artifact_for(data, name='supplied.xmfa'):
    return {'raw_artifact_ref': name, 'source_ref': 'supplied-fixture',
            'sha256': hashlib.sha256(data).hexdigest()}


def parse(text, *, encoding='ascii', artifact=None, **parameters):
    data = text.encode(encoding) if type(text) is str else text
    params = {'dialect': 'mauve1', 'alphabet': 'dna', 'encoding': encoding, **parameters}
    return parse_mauve_xmfa(data, artifact=artifact or artifact_for(data), **params)


def codes(result):
    return [item['code'] for item in result['diagnostics']]


def assert_bytes(data, document):
    """Check exact offsets against the authentic input, including all tokens."""
    encoding = document['encoding']
    atoms = []
    for meta in document['metadata']:
        atoms.append((meta['raw_line'], meta['source_location']))
        for key in ('member_number', 'integer_value'):
            if meta[key] is not None:
                atoms.append((meta[key]['raw_token'], meta[key]['source_location']))
    for block in document['blocks']:
        if block['terminated']:
            atoms.append((block['terminator_token'], block['terminator_location']))
        for row in block['records']:
            atoms.append((row['header_token'], row['header_location']))
            for key in ('member_number', 'start_1based', 'end_1based'):
                if row[key] is not None:
                    atoms.append((row[key]['raw_token'], row[key]['source_location']))
                    validate_native_number(row[key])
            atoms.extend((part['text'], part['source_location']) for part in row['sequence_parts'])
    atoms.extend((line['raw_line'], line['source_location']) for line in document['unparsed'])
    for text, loc in atoms:
        assert data[loc['byte_start_0based']:loc['byte_end_0based_exclusive']].decode(encoding) == text
        assert loc['line_start_1based'] == loc['line_end_1based_inclusive']
        # LF and CRLF fixtures: native line numbers count LF, not UTF-8 bytes.
        assert loc['line_start_1based'] == data[:loc['byte_start_0based']].count(b'\n') + 1


@pytest.mark.parametrize(('name', 'widths', 'nrows'), [
    ('combined.xmfa', [49, 1, 1, 41, 1, 1], [3, 1, 1, 1, 1, 1]),
    ('separate.xmfa', [52, 22], [3, 1]),
    ('simple.xmfa', [5670, 4420, 4970, 1470, 1470], [2, 2, 1, 1, 1]),
])
def test_complete_authentic_native_files(name, widths, nrows):
    data = (NATIVE / name).read_bytes()
    result = parse(data)
    doc = result['value']
    assert result['status'] == 'ok' and result['diagnostics'] == []
    assert doc['completeness'] == 'complete'
    assert [b['alignment_column_count'] for b in doc['blocks']] == widths
    assert [len(b['records']) for b in doc['blocks']] == nrows
    assert [b['block_index'] for b in doc['blocks']] == list(range(len(widths)))
    assert all(b['terminated'] and b['terminator_token'] == '=' for b in doc['blocks'])
    assert_bytes(data, doc)
    assert validate_xmfa_document(json.loads(json.dumps(doc, allow_nan=False))) == doc


def test_combined_retains_middle_zero_and_exact_native_intervals():
    result = parse((NATIVE / 'combined.xmfa').read_bytes())
    doc = result['value']
    first, zero, third = doc['blocks'][0]['records']
    assert [r['member_number']['value'] for r in (first, zero, third)] == [1, 2, 3]
    assert [(r['gapped_character_count'], r['nongap_character_count']) for r in (first, zero, third)] == [(49, 48), (49, 0), (49, 47)]
    assert first['interval_0based_half_open'] == [1, 49] and first['strand'] == '-'
    assert zero['coordinate_state'] == 'absent_zero'
    assert zero['sequence'] == '-' * 49 and zero['interval_0based_half_open'] is None
    assert third['interval_0based_half_open'] == [1, 48] and third['strand'] == '+'
    assert all(r['span_matches_nongap'] is True for r in (first, zero, third))
    assert first['sequence'][28] == '-'
    assert third['sequence'][9:11] == '--'
    # Confirm normalized intervals against actual retained input substrings.
    raw_fasta = (NATIVE / 'combined.fa').read_text()
    sequences = [''.join(part.splitlines()[1:]) for part in raw_fasta.split('>')[1:]]
    complement = str.maketrans('ACGTacgt', 'TGCAtgca')
    assert first['sequence'].replace('-', '') == sequences[0][1:49].translate(complement)[::-1]
    assert third['sequence'].replace('-', '') == sequences[2][1:48]
    assert [len(s) for s in sequences] == [50, 41, 49]
    assert [m['integer_value']['value'] for m in doc['metadata'] if m['kind'] == 'sequence_entry'] == [1, 2, 3]


def test_separate_order_and_minus_span_are_native_not_source_entry_order():
    doc = parse((NATIVE / 'separate.xmfa').read_bytes())['value']
    assert [m['value_token'] for m in doc['metadata'] if m['kind'] == 'sequence_file'] == ['equCab1.fa', 'canFam2.fa', 'mm9.fa']
    third = doc['blocks'][0]['records'][2]
    assert third['interval_0based_half_open'] == [0, 19]
    assert third['strand'] == '-' and third['nongap_character_count'] == 19
    last = doc['blocks'][1]['records'][0]
    assert last['member_number']['value'] == 3
    assert last['interval_0based_half_open'] == [19, 41]


def test_simple_keeps_unknown_native_path_without_binding_neighboring_file():
    doc = parse((NATIVE / 'simple.xmfa').read_bytes())['value']
    assert [m['value_token'] for m in doc['metadata'] if m['kind'] == 'sequence_file'] == ['unknown.fa', 'unknown.fa']
    minus = doc['blocks'][1]['records'][0]
    assert minus['interval_0based_half_open'] == [5670, 9940]
    assert minus['nongap_character_count'] == 4270
    assert minus['gapped_character_count'] == 4420
    assert minus['comment_token'] == 'unknown.fa # 1'
    assert not any('source_sequence' in row for block in doc['blocks'] for row in block['records'])


def test_authentic_abbreviated_counterexample_is_not_repaired():
    data = (NATIVE / 'simple_short.xmfa').read_bytes()
    result = parse(data)
    doc = result['value']
    assert result['status'] == 'partial' and doc['completeness'] == 'truncated'
    assert len(doc['blocks']) == 2
    assert [b['alignment_column_count'] for b in doc['blocks']] == [240, 46]
    assert doc['blocks'][-1]['terminated'] is False
    assert doc['blocks'][-1]['terminator_token'] is None
    assert doc['blocks'][-1]['terminator_location'] is None
    positive = [r for b in doc['blocks'] for r in b['records'] if r['member_number']['value'] != 1]
    assert [r['nongap_character_count'] for r in positive] == [159, 180, 23, 46]
    assert [r['end_1based']['value'] - r['start_1based']['value'] + 1 for r in positive] == [552, 601, 47, 48]
    assert all(r['coordinate_state'] == 'incompatible' and r['span_matches_nongap'] is False
               and r['interval_0based_half_open'] is None for r in positive)
    assert codes(result).count('xmfa_span_mismatch') == 4
    assert codes(result).count('xmfa_missing_block_terminator') == 1
    assert_bytes(data, doc)


@pytest.mark.parametrize('text', ['', ' \n\t\r\n', '\r\n'])
def test_empty_bytes_do_not_establish_a_negative_alignment(text):
    result = parse(text)
    assert result['status'] == 'invalid' and result['value'] is None
    assert codes(result) == ['xmfa_empty_input']


@pytest.mark.parametrize('text', ['not an XMFA', '# only a comment\n', 'ACGT\n=\n'])
def test_unrecognized_content_has_distinct_failure(text):
    result = parse(text)
    assert result['status'] == 'invalid' and result['value'] is None
    assert 'xmfa_document_unrecognized' in codes(result)
    assert 'xmfa_header_malformed' not in codes(result)


def test_header_only_is_unknown_and_has_no_fabricated_block():
    result = parse(PREFIX)
    assert result['status'] == 'ok'
    assert result['value']['completeness'] == 'unknown'
    assert result['value']['blocks'] == []


@pytest.mark.parametrize('ending', ['=\n', '=\r\n', '='])
def test_only_native_delimiter_makes_complete_syntax(ending):
    result = parse(PREFIX + '>1:1-2 +\nAC\n' + ending)
    assert result['status'] == 'ok'
    assert result['value']['completeness'] == 'complete'


@pytest.mark.parametrize('ending', ['AC', 'AC\n', 'AC\n\n', 'AC\n# last comment'])
def test_missing_final_delimiter_retains_unterminated_row_without_eof_fabrication(ending):
    text = PREFIX + '>1:1-2 +\n' + ending
    result = parse(text)
    block = result['value']['blocks'][0]
    assert result['value']['completeness'] == block['completeness'] == 'truncated'
    assert block['records'][0]['sequence'] == 'AC'
    assert not block['terminated'] and block['terminator_location'] is None
    assert block['source_location']['byte_end_0based_exclusive'] <= len(text.encode())
    assert codes(result) == ['xmfa_missing_block_terminator']


def test_blank_lines_and_comments_preserve_one_block_and_sequence_parts():
    text = PREFIX + '>  1:1-3 + comment with  spaces  \nA\n\n# between parts\nCG\n\n>\t2:2-4\t-\tsecond\nATG\n= score has unknown units\n'
    result = parse(text)
    block = result['value']['blocks'][0]
    assert result['status'] == 'ok' and len(result['value']['blocks']) == 1
    assert block['records'][0]['sequence'] == 'ACG'
    assert [p['text'] for p in block['records'][0]['sequence_parts']] == ['A', '', 'CG', '']
    assert block['records'][0]['comment_token'] == 'comment with  spaces  '
    assert block['records'][1]['strand'] == '-'
    assert block['terminator_token'] == '= score has unknown units'
    assert result['value']['metadata'][1]['value_token'] == ' between parts'
    assert_bytes(text.encode(), result['value'])


def test_utf8_crlf_byte_offsets_and_metadata_names_with_spaces():
    text = '# note é\r\n#FormatVersion Mauve1\r\n#Sequence01File\tpath with β and spaces.fa\r\n#Sequence01Entry\t1\r\n>\t01:2-3 - naïve label\r\nAc\r\n= score é'
    data = text.encode('utf-8')
    result = parse(data, encoding='utf-8')
    doc = result['value']
    assert result['status'] == 'ok'
    assert doc['metadata'][2]['value_token'] == 'path with β and spaces.fa'
    assert doc['metadata'][2]['member_number']['raw_token'] == '01'
    row = doc['blocks'][0]['records'][0]
    assert row['sequence'] == 'Ac' and row['comment_token'] == 'naïve label'
    assert row['header_location']['byte_start_0based'] == data.index(b'>')
    assert row['header_location']['byte_start_0based'] != text.index('>')
    assert row['header_location']['line_start_1based'] == 5
    assert_bytes(data, doc)


def test_cr_only_line_endings_and_unicode_separator_are_not_confused():
    result = parse(PREFIX.replace('\n', '\r') + '>1:1-2 +\rAC\r=')
    assert result['status'] == 'ok'
    assert result['value']['blocks'][0]['terminator_location']['line_start_1based'] == 4
    result = parse(PREFIX + '>1:1-3 +\nA\u2028C\n=', encoding='utf-8')
    row = result['value']['blocks'][0]['records'][0]
    assert len(row['sequence_parts']) == 1 and row['gapped_character_count'] == 3
    assert row['sequence'] == 'A\u2028C' and row['coordinate_state'] == 'incompatible'


@pytest.mark.parametrize('zero_index', [0, 1, 2])
@pytest.mark.parametrize('zero_text', ['', '---'])
def test_zero_records_first_middle_last_empty_or_observed_gaps(zero_index, zero_text):
    records = ['>1:1-3 +\nACG\n', '>2:2-4 -\nTGA\n']
    records.insert(zero_index, '>3:0-0 +\n' + (zero_text + '\n' if zero_text else ''))
    result = parse(PREFIX + ''.join(records) + '=')
    block = result['value']['blocks'][0]
    assert result['status'] == 'ok' and len(block['records']) == 3
    assert block['alignment_column_count'] == 3
    zero = block['records'][zero_index]
    assert zero['coordinate_state'] == 'absent_zero' and zero['sequence'] == zero_text
    assert zero['gapped_character_count'] == len(zero_text) and zero['nongap_character_count'] == 0
    assert zero['interval_0based_half_open'] is None
    assert zero['span_matches_nongap'] is True


@pytest.mark.parametrize('zero_text', ['', '----'])
def test_all_zero_block_has_no_invented_width(zero_text):
    result = parse(PREFIX + '>1:0-0 +\n' + zero_text + '\n=')
    block = result['value']['blocks'][0]
    assert block['alignment_column_count'] is None
    assert block['records'][0]['sequence'] == zero_text
    assert 'xmfa_all_zero_block' in codes(result)


@pytest.mark.parametrize(('header', 'sequence', 'code', 'span'), [
    ('>1:0-2 +', 'AC', 'coordinate_invalid', None),
    ('>1:2-0 -', 'AC', 'coordinate_invalid', None),
    ('>1:0-0 +', 'A--', 'zero_record_has_residues', False),
    ('>1:1-2 +', '', 'span_mismatch', False),
    ('>1:1-2 +', '--', 'span_mismatch', False),
    ('>1:1-3 +', 'AC', 'span_mismatch', False),
    ('>1:4-2 -', 'ACG', 'coordinate_invalid', None),
])
def test_incompatible_coordinates_keep_raw_numbers_and_sequence(header, sequence, code, span):
    result = parse(PREFIX + header + '\n' + sequence + '\n=')
    row = result['value']['blocks'][0]['records'][0]
    assert row['coordinate_state'] == 'incompatible'
    assert row['sequence'] == sequence and row['interval_0based_half_open'] is None
    assert row['span_matches_nongap'] is span
    assert 'xmfa_' + code in codes(result)


@pytest.mark.parametrize('second', ['>2:1-3 +\nACG\n', '>2:0-0 +\n---\n', '>2:1-1 +\n'])
def test_ragged_rows_and_zero_width_conflicts_survive(second):
    result = parse(PREFIX + '>1:1-2 +\nAC\n' + second + '=')
    block = result['value']['blocks'][0]
    assert block['alignment_column_count'] is None
    assert len(block['records']) == 2 and block['records'][0]['sequence'] == 'AC'
    assert 'xmfa_row_width_conflict' in codes(result)


@pytest.mark.parametrize('header', [
    '>', '>nonsense', '>1:1-2', '>1:1-2 ? comment', '>1:1 + name',
    '>1:1-2+ name', '>1:1.0-2 +', '>1e0:1-2 +', '>1:-1-2 +',
    '>1:1-2-3 +', '>0:1-2 +', '>1:-2 +', '>1:1- +', '>1:NA-2 +',
])
def test_malformed_defline_still_creates_own_record_boundary(header):
    text = PREFIX + '>2:1-2 +\nAC\n' + header + '\nGT\n>3:1-2 +\nTG\n='
    result = parse(text)
    rows = result['value']['blocks'][0]['records']
    assert len(rows) == 3
    assert rows[1]['header_token'] == header and rows[1]['sequence'] == 'GT'
    assert rows[1]['coordinate_state'] in ('unknown', 'incompatible')
    assert rows[1]['interval_0based_half_open'] is None
    assert rows[0]['coordinate_state'] == rows[2]['coordinate_state'] == 'present'
    assert result['status'] == 'partial'
    assert_bytes(text.encode(), result['value'])


@pytest.mark.parametrize(('token', 'state', 'kind'), [
    ('1e0', 'incompatible', 'finite'), ('+1', 'incompatible', 'finite'),
    ('-1', 'incompatible', 'finite'), ('1.0', 'incompatible', 'finite'),
    ('NA', 'not_measured', 'native_na'), ('nan', 'failed', 'nonfinite'),
    ('oops', 'failed', 'malformed'), ('1e1000000', 'failed', 'overflow'),
    ('1e-1000000', 'failed', 'underflow'),
])
def test_numeric_tokens_retain_shared_native_states_but_require_decimal_syntax(token, state, kind):
    result = parse(PREFIX + f'>{token}:1-2 +\nAC\n=')
    row = result['value']['blocks'][0]['records'][0]
    number = row['member_number']
    assert number['raw_token'] == token and number['state'] == state and number['token_kind'] == kind
    assert row['coordinate_state'] == 'incompatible'
    validate_native_number(number)


def test_large_native_decimal_is_retained_exactly_without_float_rounding():
    token = '9' * 1000
    result = parse(PREFIX + f'>{token}:1-2 +\nAC\n=')
    number = result['value']['blocks'][0]['records'][0]['member_number']
    assert number['raw_token'] == token
    assert number['state'] == 'available' and number['token_kind'] == 'finite'
    assert number['value'] == 10 ** 1000 - 1
    assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize('sequence', ['AcgTRYSWKMBDHVN', '--a-Cg--', 'ACGT'])
def test_actual_iupac_case_and_gap_positions_are_retained(sequence):
    nongap = len(sequence.replace('-', ''))
    result = parse(PREFIX + f'>1:1-{nongap} -\n{sequence}\n=')
    row = result['value']['blocks'][0]['records'][0]
    assert row['sequence'] == sequence and row['sequence_state'] == 'dna_iupac'
    assert row['coordinate_state'] == 'present' and row['interval_0based_half_open'] == [0, nongap]
    assert row['nongap_character_count'] == nongap


@pytest.mark.parametrize('sequence', ['A.C', 'AU', 'A*C', 'A?C', 'A C', 'A\tC', 'AéC'])
def test_invalid_symbols_never_become_gaps_or_trusted_coordinates(sequence):
    result = parse(PREFIX + f'>1:1-{len(sequence)} +\n{sequence}\n=', encoding='utf-8')
    row = result['value']['blocks'][0]['records'][0]
    assert row['sequence'] == sequence and row['sequence_state'] == 'incompatible'
    assert row['nongap_character_count'] == len(sequence) and row['span_matches_nongap'] is True
    assert row['coordinate_state'] == 'incompatible' and row['interval_0based_half_open'] is None
    assert 'xmfa_sequence_symbol_invalid' in codes(result)


@pytest.mark.parametrize('prefix', ['', '#FormatVersion Future2\n', '#FormatVersion Mauve1\n#FormatVersion Other\n'])
def test_missing_or_unsupported_version_does_not_grant_coordinate_semantics(prefix):
    result = parse(prefix + '>1:1-1 -\nA\n>2:0-0 +\n-\n=')
    assert result['status'] == 'partial'
    rows = result['value']['blocks'][0]['records']
    assert all(row['coordinate_state'] == 'unknown' and row['span_matches_nongap'] is None
               and row['interval_0based_half_open'] is None for row in rows)
    assert all(row['start_1based']['state'] == 'available' for row in rows)


def test_missing_member_metadata_does_not_invent_association_or_block_literal_coordinates():
    result = parse(PREFIX + '>7:1-1 +\nA\n=')
    assert result['status'] == 'ok'
    assert len(result['value']['metadata']) == 1
    assert result['value']['blocks'][0]['records'][0]['coordinate_state'] == 'present'


def test_duplicates_preserve_every_metadata_declaration_and_record():
    text = (PREFIX + '#Sequence1File\tpath with spaces.fa\n#Sequence1File\tpath with spaces.fa\n'
            '#Sequence1File\tconflicting.fa\n#Sequence1Entry\t1\n#Sequence1Entry\t01\n'
            '#Annotation1File\tgenes with spaces.gbk\n#Annotation1Format\tGenBank\n'
            '#Sequence1Format\tFastA\n#BackboneFile\twith spaces.bbcols\n'
            '#unrecognized retained words\n>1:1-2 +\nAC\n>1:1-2 +\nAC\n=')
    result = parse(text)
    doc = result['value']
    assert len(doc['metadata']) == 11 and len(doc['blocks'][0]['records']) == 2
    assert [m['value_token'] for m in doc['metadata'][1:4]] == ['path with spaces.fa', 'path with spaces.fa', 'conflicting.fa']
    assert codes(result).count('xmfa_metadata_duplicate') == 3
    assert codes(result).count('xmfa_metadata_conflict') == 1
    assert 'xmfa_duplicate_member_record' in codes(result)
    assert doc['metadata'][6]['kind'] == 'annotation_file'
    assert doc['metadata'][7]['kind'] == 'annotation_format'
    assert_bytes(text.encode(), doc)


def test_metadata_entry_is_string_plus_its_separate_native_number():
    result = parse(PREFIX + '#Sequence1Entry\t1e2\n#SequencebadEntry\tNA\n>1:1-1 +\nA\n=')
    meta = result['value']['metadata'][1]
    assert meta['value_token'] == '1e2'
    assert meta['integer_value']['value'] == 100.0 and meta['integer_value']['state'] == 'incompatible'
    assert meta['member_number']['value'] == 1
    assert 'xmfa_metadata_integer_invalid' in codes(result)
    assert 'xmfa_member_invalid' in codes(result)
    assert len(meta) == 7


@pytest.mark.parametrize(('separator', 'payload'), [
    ('\t', '  source with spaces.fa'), ('\t', '\t source.fa\t'),
    (' ', ' another source.fa  '),
])
def test_metadata_consumes_one_separator_and_preserves_leading_filename_whitespace(separator, payload):
    text = PREFIX + '#Sequence1File' + separator + payload + '\n>1:1-1 +\nA\n='
    result = parse(text)
    assert result['status'] == 'ok'
    meta = result['value']['metadata'][1]
    assert meta['value_token'] == payload
    assert meta['raw_line'] == '#Sequence1File' + separator + payload
    assert_bytes(text.encode(), result['value'])


def test_metadata_integer_payload_whitespace_is_preserved_and_not_accepted_as_decimal_syntax():
    text = PREFIX + '#Sequence1Entry\t 1\n>1:1-1 +\nA\n='
    result = parse(text)
    meta = result['value']['metadata'][1]
    assert meta['value_token'] == meta['integer_value']['raw_token'] == ' 1'
    assert meta['integer_value']['state'] == 'incompatible'
    assert 'xmfa_metadata_integer_invalid' in codes(result)
    assert_bytes(text.encode(), result['value'])


def test_repeated_identical_version_is_retained_with_agreed_semantics():
    result = parse(PREFIX + PREFIX + '>1:1-1 +\nA\n=')
    assert len(result['value']['metadata']) == 2
    assert result['value']['format_version_token'] == 'Mauve1'
    assert result['value']['blocks'][0]['records'][0]['coordinate_state'] == 'present'
    assert codes(result) == ['xmfa_metadata_duplicate']


def test_repeated_blocks_and_distinct_coordinates_never_collapse():
    block = '>1:1-2 +\nAC\n=\n'
    result = parse(PREFIX + block * 3 + '>1:3-4 +\nAC\n=')
    assert result['status'] == 'ok'
    assert len(result['value']['blocks']) == 4
    assert [b['records'][0]['interval_0based_half_open'] for b in result['value']['blocks']] == [[0, 2], [0, 2], [0, 2], [2, 4]]


def test_sequence_before_header_and_trailing_garbage_remain_located():
    text = 'AC\n' + PREFIX + '>1:1-1 +\nA\n=\ntrailing garbage\n= stray terminator'
    result = parse(text)
    doc = result['value']
    assert len(doc['blocks']) == 1 and len(doc['unparsed']) == 3
    assert doc['completeness'] == 'partial'
    assert [line['raw_line'] for line in doc['unparsed']] == ['AC', 'trailing garbage', '= stray terminator']
    assert codes(result).count('xmfa_sequence_before_header') == 1
    assert codes(result).count('xmfa_unparsed_line') == 2
    assert_bytes(text.encode(), doc)


@pytest.mark.parametrize('data', [b'\xff', b'\xc3\x28', b'#FormatVersion Mauve1\n>1:1-1 +\n\xff\n='])
def test_bad_explicit_encoding_has_invalid_null_result(data):
    result = parse(data, encoding='utf-8')
    assert result['status'] == 'invalid' and result['value'] is None
    assert codes(result) == ['xmfa_encoding_invalid']


def test_digest_mismatch_does_not_decode_or_relabel_bytes():
    data = PREFIX.encode()
    artifact = artifact_for(data)
    artifact['sha256'] = '0' * 64
    snapshot = deepcopy(artifact)
    result = parse(data, artifact=artifact)
    assert result['status'] == 'invalid' and result['value'] is None
    assert codes(result) == ['xmfa_digest_mismatch'] and artifact == snapshot


@pytest.mark.parametrize(('keyword', 'bad', 'code'), [
    ('dialect', 'xmfa', 'dialect_invalid'), ('dialect', None, 'dialect_invalid'),
    ('alphabet', 'protein', 'alphabet_invalid'), ('alphabet', [], 'alphabet_invalid'),
    ('encoding', 'UTF-8', 'encoding_invalid'), ('encoding', 'latin1', 'encoding_invalid'),
])
def test_wrong_explicit_parameters_are_caller_errors(keyword, bad, code):
    kwargs = {'dialect': 'mauve1', 'alphabet': 'dna', 'encoding': 'ascii', keyword: bad}
    with pytest.raises(ValueError, match='^xmfa_' + code + '$'):
        parse_mauve_xmfa(b'', artifact=artifact_for(b''), **kwargs)
    assert code in CALLER_ERROR_CODES


@pytest.mark.parametrize('data', ['', None, bytearray(b'AC'), memoryview(b'AC'), []])
def test_parser_requires_actual_bytes(data):
    with pytest.raises(ValueError, match='^xmfa_bytes_required$'):
        parse_mauve_xmfa(data, artifact=artifact_for(b''), dialect='mauve1', alphabet='dna', encoding='ascii')


@pytest.mark.parametrize('artifact', [None, {}, {'sha256': '0' * 64}, {'raw_artifact_ref': 'a', 'source_ref': 's', 'sha256': 'z' * 64}])
def test_closed_artifact_errors_use_xmfa_prefix(artifact):
    with pytest.raises(ValueError, match='^xmfa_artifact_invalid$'):
        parse_mauve_xmfa(b'', artifact=artifact, dialect='mauve1', alphabet='dna', encoding='ascii')


def test_document_identity_and_inputs_are_detached():
    data = (PREFIX + '>1:1-1 +\nA\n=').encode()
    artifact = artifact_for(data)
    result = parse(data, artifact=artifact)
    doc = result['value']
    assert doc['document_id'] == document_id('mauve_xmfa', artifact=artifact,
        parameters={'dialect': 'mauve1', 'alphabet': 'dna', 'encoding': 'ascii'})
    artifact['source_ref'] = 'changed by caller'
    assert doc['artifact']['source_ref'] == 'supplied-fixture'
    doc['artifact']['source_ref'] = 'changed output'
    assert doc['blocks'][0]['source_location']['artifact']['source_ref'] == 'supplied-fixture'


def test_all_emitted_native_codes_are_finite_host_diagnostics():
    result = parse('#FormatVersion Future\n>bad:NA--2 ?\nA.é\n', encoding='utf-8')
    for item in result['diagnostics']:
        assert set(item) == {'code', 'phase', 'path', 'severity', 'evidence_refs'}
        assert item['phase'] == 'native_decode'
        assert item['code'].removeprefix('xmfa_') in NATIVE_DIAGNOSTIC_CODES
        assert item['evidence_refs'] == [result['value']['artifact']['raw_artifact_ref']]
