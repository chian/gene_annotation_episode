"""Official retained native bytes plus explicitly synthetic corruption cases."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.mauve_v4_formats import parse_mauve_v4
from gene_annotation_episode.mauve_v4_format_contracts import validate_mauve_v4_document

OFFICIAL = Path(__file__).resolve().parents[1] / 'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/retained_sources/mauve/testdata/small.mauve'


def parse(raw, *, encoding='ascii'):
    data = raw.encode(encoding) if isinstance(raw, str) else raw
    return parse_mauve_v4(data, artifact={'raw_artifact_ref': 'synthetic:artifact',
        'source_ref': 'synthetic:source', 'sha256': hashlib.sha256(data).hexdigest()}, encoding=encoding)


def native(body='4 1 1\n', *, lengths=(12, 12), paths=('/staged/f0', '/staged/f1')):
    return ('FormatVersion\t4\nSequenceCount\t2\n'
        f'Sequence0File\t{paths[0]}\nSequence0Length\t{lengths[0]}\n'
        f'Sequence1File\t{paths[1]}\nSequence1Length\t{lengths[1]}\n'
        'IntervalCount\t1\nInterval 0\n' + body)


def codes(result):
    return {r['code'].removeprefix('mauve_v4_') for r in result['diagnostics']}


def test_official_native_v4_has_exact_rows_metadata_and_source_locations():
    data = OFFICIAL.read_bytes(); result = parse_mauve_v4(data, artifact={
        'source_ref': 'official:small.mauve', 'raw_artifact_ref': str(OFFICIAL),
        'sha256': hashlib.sha256(data).hexdigest()}, encoding='ascii')
    assert result['status'] == 'ok' and result['diagnostics'] == []
    d = result['value']; assert [len(i['segments']) for i in d['intervals']] == [4, 1, 1, 1, 1]
    assert d['metadata'][2]['value_token'].startswith('C:\\Documents and Settings\\')
    assert [m['number']['value'] for m in d['metadata'] if m['kind'] == 'sequence_length'] == [693, 2000]
    gap = d['intervals'][0]['segments'][2]
    assert gap['native_width']['value'] == 269
    assert [len(r['sequence'].replace('-', '')) for r in gap['sequence_rows']] == [4, 269]
    def inspect(value):
        if isinstance(value, dict):
            if 'raw_token' in value:
                loc = value['source_location']; assert data[loc['byte_start_0based']:loc['byte_end_0based_exclusive']].decode() == value['raw_token']
            if 'raw_line' in value:
                loc = value['source_location']; assert data[loc['byte_start_0based']:loc['byte_end_0based_exclusive']].decode() == value['raw_line']
            for v in value.values(): inspect(v)
        elif isinstance(value, list):
            for v in value: inspect(v)
    inspect(d)
    detached = validate_mauve_v4_document(d); detached['metadata'][0]['raw_line'] = 'changed'
    assert d['metadata'][0]['raw_line'] == 'FormatVersion\t4'


@pytest.mark.parametrize('body,expected', [
    ('GappedAlignment\n4 1 1\nACGT\n', 'missing_sequence_row'),
    ('GappedAlignment\n4 1 1\nACGT\nACGT\nACGT\n', 'extra_sequence_row'),
    ('GappedAlignment\n4 1 1\nACG\nACGT\n', 'width_conflict'),
    ('GappedAlignment\n4 0 1\nACGT\nACGT\n', 'zero_member_has_residues'),
    ('GappedAlignment\n4 1 1\nAXGT\nACGT\n', 'sequence_symbol_invalid'),
    ('-3 1 1\n', 'segment_header_malformed'),
    ('3 NaN 1\n', 'coordinate_invalid'),
    ('1e3 1 1\n', 'segment_header_malformed'),
    ('GappedAlignment\n', 'segment_header_malformed'),
])
def test_recoverable_local_malformation_keeps_segment_and_raw_tokens(body, expected):
    r = parse(native(body))
    assert r['status'] == 'partial' and expected in codes(r)
    assert r['value']['intervals'][0]['segments']
    assert validate_mauve_v4_document(r['value']) == r['value']


def test_partial_gapped_section_stops_at_coordinate_header_and_preserves_ordinal():
    r = parse(native('GappedAlignment\n4 1 1\nunknown row\nACGT\n4 8 8\n'))
    segments = r['value']['intervals'][0]['segments']
    assert len(segments) == 2 and segments[0]['completeness'] == 'partial'
    assert segments[0]['sequence_rows'][0]['member_index_0based'] == 1
    assert segments[1]['native_length']['value'] == 4 and segments[1]['completeness'] == 'complete'
    assert r['value']['intervals'][0]['unparsed'][0]['raw_line'] == 'unknown row'


@pytest.mark.parametrize('mutator', [
    lambda s: s.replace('SequenceCount\t2', 'SequenceCount\t2\nSequenceCount\t3'),
    lambda s: s.replace('SequenceCount\t2\n', ''),
    lambda s: s.replace('Sequence0Length\t12', 'Sequence0Length\t12\nSequence0Length\t13'),
    lambda s: s.replace('IntervalCount\t1', 'IntervalCount\t2'),
    lambda s: s + 'Interval 0\n4 1 1\n',
])
def test_conflicting_or_missing_declarations_never_win_by_position(mutator):
    r = parse(mutator(native('GappedAlignment\n4 1 1\nACGT\nACGT\n')))
    assert r['status'] == 'partial'
    assert validate_mauve_v4_document(r['value']) == r['value']


def test_identical_duplicate_native_declarations_are_retained():
    r = parse(native().replace('SequenceCount\t2', 'SequenceCount\t2\nSequenceCount\t2'))
    assert r['status'] == 'ok' and 'metadata_duplicate' in codes(r)
    assert len(r['value']['metadata']) == 8


def test_unicode_filenames_preserve_byte_offsets_and_entire_value():
    raw = native(paths=('/staged/α path.fasta', '/staged/β path.fasta'))
    r = parse(raw, encoding='utf-8'); assert r['status'] == 'ok'
    assert r['value']['metadata'][2]['value_token'] == '/staged/α path.fasta'
    assert validate_mauve_v4_document(r['value']) == r['value']


@pytest.mark.parametrize('raw,code', [(b'', 'empty_input'), (b'#FormatVersion Mauve1\n', 'format_unrecognized'),
    (b'FormatVersion\t5\n', 'version_unsupported'), (b'FormatVersion\t4\n\xff', 'encoding_invalid')])
def test_invalid_primary_is_not_a_measured_empty_result(raw, code):
    r = parse(raw); assert r['status'] == 'invalid' and r['value'] is None and code in codes(r)


def test_bad_function_arguments_are_contract_errors():
    a = {'source_ref': 's', 'raw_artifact_ref': 'a', 'sha256': '0' * 64}
    with pytest.raises(ValueError, match='mauve_v4_bytes_required'): parse_mauve_v4('', artifact=a, encoding='ascii')
    with pytest.raises(ValueError, match='mauve_v4_encoding_unsupported'): parse_mauve_v4(b'', artifact=a, encoding='latin-1')
    with pytest.raises(ValueError, match='mauve_v4_artifact_invalid'): parse_mauve_v4(b'', artifact={}, encoding='ascii')
    r = parse_mauve_v4(b'FormatVersion\t4', artifact=a, encoding='ascii')
    assert r['status'] == 'invalid' and 'digest_mismatch' in codes(r)


@pytest.mark.parametrize('mutation', ['extra_key', 'wrong_location', 'changed_number', 'changed_identity', 'changed_ordinal', 'invented_complete'])
def test_saved_document_validation_rejects_corruption(mutation):
    d = parse(native())['value']
    if mutation == 'extra_key': d['trust'] = True
    elif mutation == 'wrong_location': d['intervals'][0]['segments'][0]['header_location']['byte_end_0based_exclusive'] += 1
    elif mutation == 'changed_number': d['intervals'][0]['segments'][0]['native_length']['value'] = 50
    elif mutation == 'changed_identity': d['document_id'] += 'x'
    elif mutation == 'changed_ordinal': d['intervals'][0]['interval_index'] = True
    else:
        d = parse(native('GappedAlignment\n4 1 1\nACGT\n'))['value']
        d['intervals'][0]['segments'][0]['completeness'] = 'complete'
    with pytest.raises(ValueError): validate_mauve_v4_document(d)


def test_large_native_count_is_retained_without_allocating_missing_members():
    r = parse(native().replace('SequenceCount\t2', 'SequenceCount\t1000000000000'))
    assert r['status'] == 'partial' and len(r['value']['intervals']) == 1

