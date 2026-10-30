"""Actual retained BAM headers plus explicitly synthetic dictionary counterexamples."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.atac_differential_contracts import validate_atac_parsed_table
from gene_annotation_episode.atac_differential_sheet import build_atac_differential_sheet
from gene_annotation_episode.atac_reference_observations import parse_atac_bam_reference
from test_atac_differential_inputs import NATIVE, artifact, codes
from test_atac_differential_sheet import explicit_inputs, native_inputs


HEADERS = (Path(__file__).resolve().parents[1]
           / 'verification/tool_graders_atac_bam_references_2026-10-27_468/native001')


def parse_header(raw, *, run='callpeak-1', ordinal=0, input_ref='condition1.bam', **changes):
    source = artifact(raw if type(raw) is bytes else None, 'header.sam', 'sam_header_text',
                      'actual-header-inspection')
    source.update(producer_name='pysam', producer_version='0.23.3', producer_source_ref='bound-pysam')
    source.update(changes)
    return parse_atac_bam_reference(raw, artifact=source, callpeak_run_key=run,
                                    input_ordinal=ordinal, input_artifact_ref=input_ref)


def native_headers():
    observations = json.loads((HEADERS / 'BAM_HEADER_OBSERVATIONS.json').read_text())['observations']
    records = []
    for number, observed in enumerate(observations, 1):
        raw = (HEADERS / f'condition{number}.sam_header.txt').read_bytes()
        records.append(parse_header(raw, run=f'callpeak-{number}', input_ref=f'condition{number}.bam',
                                    artifact_ref='sha256:' + observed['header']['sha256']))
    return records


def sheet_arguments(sheet):
    return {field: deepcopy(sheet[field]) for field in (
        'reference', 'samples', 'conditions', 'callpeak_bindings', 'comparison', 'tracks',
        'peaks_xls', 'narrowpeaks', 'summits', 'native_differential', 'depth_selection', 'bam_references')}


@pytest.mark.parametrize('number', [1, 2])
def test_actual_retained_bam_header_bytes_numbers_and_complete_locations(number):
    observed = json.loads((HEADERS / 'BAM_HEADER_OBSERVATIONS.json').read_text())['observations'][number - 1]
    raw = (HEADERS / f'condition{number}.sam_header.txt').read_bytes()
    bam = (NATIVE / f'bam_inputs/condition{number}.bam').read_bytes()
    assert hashlib.sha256(bam).hexdigest() == observed['input_before']['sha256']
    assert len(bam) == observed['input_before']['size_bytes']
    assert observed['input_before'] == observed['input_after']
    assert observed['raw_bam_text_equals_reader_text'] is True
    assert len(raw) == observed['header']['size_bytes'] == 48
    assert hashlib.sha256(raw).hexdigest() == observed['header']['sha256']
    result = native_headers()[number - 1]
    validate_atac_parsed_table(result, version='atac_bam_reference_parsed_v1')
    assert result['state'] == dict(availability='present', byte_extent='complete',
                                  identity='verified', format='compatible', output_extent='complete')
    assert result['binding_key'] == f'callpeak-{number}:input:0'
    assert result['physical_line_count'] == 2
    assert result['data_row_count'] == result['readable_data_row_count'] == 1
    assert result['malformed_data_row_count'] == 0
    assert result['headers'] == [dict(locator=dict(line_number=1, byte_start=0, byte_end=25),
                                      kind='sam_header', text='@HD\tVN:1.6\tSO:coordinate')]
    assert result['rows'] == [dict(row_ordinal=0, locator=dict(line_number=2, byte_start=25, byte_end=48),
                                   chromosome='chrToy', length_bp=12000, sequence_md5=None,
                                   original_fields=['@SQ', 'SN:chrToy', 'LN:12000'])]
    assert [{'chromosome': row['chromosome'], 'length_bp': row['length_bp']}
            for row in result['rows']] == observed['native_dictionary']
    assert result['issues'] == []


def test_binary_stream_crlf_final_line_and_other_sam_headers_preserve_original_tokens():
    raw = (b'@HD\tVN:1.6\r\n@RG\tID:sample\r\n@PG\tID:aligner\n'
           b'@CO\toriginal comment\n\n@SQ\tSN:chr1\tLN:000123\tAS:explicit\tM5:' + b'A1' * 16)
    result = parse_header(io.BytesIO(raw), expected_sha256=hashlib.sha256(raw).hexdigest(),
                          expected_size_bytes=len(raw))
    assert result == parse_header(raw)
    assert [h['kind'] for h in result['headers']] == ['sam_header'] * 4 + ['blank']
    row = result['rows'][0]
    assert row['locator'] == dict(line_number=6, byte_start=raw.index(b'@SQ'), byte_end=len(raw))
    assert row['length_bp'] == 123
    assert row['original_fields'][2] == 'LN:000123'
    assert row['sequence_md5'] == 'A1' * 16
    assert 'sequence_sha256' not in row
    assert result['state']['output_extent'] == 'complete'
    validate_atac_parsed_table(result)


@pytest.mark.parametrize('fields,field,value,code', [
    (b'LN:100', 'chromosome', None, 'metadata_missing'),
    (b'SN:chr1', 'length_bp', None, 'metadata_missing'),
    (b'SN:\tLN:100', 'chromosome', None, 'metadata_conflict'),
    (b'SN:chr 1\tLN:100', 'chromosome', None, 'metadata_conflict'),
    (b'SN:*\tLN:100', 'chromosome', None, 'metadata_conflict'),
    (b'SN:=chr1\tLN:100', 'chromosome', None, 'metadata_conflict'),
    (b'SN:chr1\tLN:', 'length_bp', None, 'invalid_number'),
    (b'SN:chr1\tLN:1.5', 'length_bp', None, 'invalid_number'),
    (b'SN:chr1\tLN:1e2', 'length_bp', None, 'invalid_number'),
    (b'SN:chr1\tLN:-100', 'length_bp', -100, 'numeric_out_of_range'),
    (b'SN:chr1\tLN:0', 'length_bp', 0, 'numeric_out_of_range'),
    (b'SN:chr1\tLN:100\tM5:', 'sequence_md5', None, 'metadata_conflict'),
    (b'SN:chr1\tLN:100\tM5:' + b'g' * 32, 'sequence_md5', None, 'metadata_conflict'),
    (b'SN:chr1\tLN:100\tM5:' + b'a' * 64, 'sequence_md5', None, 'metadata_conflict'),
])
def test_synthetic_missing_invalid_and_negative_fields_retain_each_original(fields, field, value, code):
    raw = b'@SQ\t' + fields + b'\n'
    result = parse_header(raw)
    assert result['rows'][0][field] == value
    assert result['rows'][0]['original_fields'] == raw[:-1].decode().split('\t')
    assert result['readable_data_row_count'] == result['malformed_data_row_count'] == 1
    assert result['state']['format'] == 'malformed'
    assert code in codes(result)
    assert all(i['locations'] == [dict(line_number=1, byte_start=0, byte_end=len(raw))]
               for i in result['issues'])
    validate_atac_parsed_table(result)


@pytest.mark.parametrize('tag,field,first,second', [
    ('SN', 'chromosome', 'chr1', 'chr1'), ('SN', 'chromosome', 'chr1', 'chr2'),
    ('LN', 'length_bp', '100', '100'), ('LN', 'length_bp', '100', '200'),
    ('M5', 'sequence_md5', 'a' * 32, 'a' * 32), ('M5', 'sequence_md5', 'a' * 32, 'b' * 32),
])
def test_repeated_tags_never_choose_the_first_even_when_equal(tag, field, first, second):
    tokens = ['@SQ', 'SN:chr1', 'LN:100', 'M5:' + 'c' * 32]
    tokens = [token for token in tokens if not token.startswith(tag + ':')]
    tokens.extend([tag + ':' + first, tag + ':' + second])
    result = parse_header(('\t'.join(tokens) + '\n').encode())
    assert result['rows'][0]['original_fields'] == tokens
    assert result['rows'][0][field] is None
    assert any(i['code'] == 'metadata_conflict' and i['field'] == field for i in result['issues'])
    assert result['malformed_data_row_count'] == 1
    validate_atac_parsed_table(result)


def test_malformed_tag_then_valid_occurrence_cannot_select_later_value():
    result = parse_header(b'@SQ\tSN\tSN:chr1\tLN\tLN:100\tM5\tM5:' + b'a' * 32 + b'\n')
    assert all(result['rows'][0][field] is None for field in ('chromosome', 'length_bp', 'sequence_md5'))
    assert result['malformed_data_row_count'] == 1
    validate_atac_parsed_table(result)


def test_duplicate_chromosome_occurrences_retain_all_values_and_both_locations():
    raw = b'@SQ\tSN:chr1\tLN:100\n@SQ\tSN:chr2\tLN:250\n@SQ\tSN:chr1\tLN:200\n'
    result = parse_header(raw)
    assert [row['length_bp'] for row in result['rows']] == [100, 250, 200]
    duplicates = [i for i in result['issues'] if i['code'] == 'duplicate_record']
    assert len(duplicates) == 1
    assert duplicates[0]['row_ordinals'] == [0, 2]
    assert duplicates[0]['locations'] == [result['rows'][i]['locator'] for i in (0, 2)]
    assert result['malformed_data_row_count'] == 2
    assert result['data_row_count'] == 3
    validate_atac_parsed_table(result)


def test_unsupported_format_survives_later_malformed_rows():
    result = parse_header(b'@SQ\tSN:chr1\tLN:100\n@SQ\tSN:chr2\tLN:bad\nnot-a-header\n', format='bam')
    assert result['state']['format'] == 'unsupported'
    assert result['rows'][0]['length_bp'] == 100
    assert result['rows'][1]['length_bp'] is None
    assert result['invalid_records'][0]['fields'] == ['not-a-header']
    assert {'unsupported_format', 'invalid_number', 'metadata_conflict'} <= codes(result)
    validate_atac_parsed_table(result)


def test_invalid_utf8_and_nonheader_occurrences_preserve_readable_surroundings():
    raw = b'@SQ\tSN:chr1\tLN:100\n\xff\nnot-a-header\n@SQ\tSN:chr2\tLN:200\n'
    result = parse_header(raw)
    assert [row['row_ordinal'] for row in result['rows']] == [0, 3]
    assert [row['row_ordinal'] for row in result['invalid_records']] == [1, 2]
    assert result['invalid_records'][0]['fields'] is None
    assert result['data_row_count'] == 4
    assert result['malformed_data_row_count'] == 2
    assert result['parsed_sha256'] == hashlib.sha256(raw).hexdigest()
    validate_atac_parsed_table(result)


def test_missing_empty_no_sq_and_failed_inspection_are_distinct():
    missing = parse_header(None, artifact_ref=None)
    empty = parse_header(b'')
    no_sq = parse_header(b'@HD\tVN:1.6\n')
    failed = parse_header(b'@SQ\tSN:chr1\tLN:100\n', producer_outcome='failed')
    assert missing['state']['availability'] == 'missing'
    assert missing['parsed_sha256'] is None
    assert 'artifact_missing' in codes(missing)
    assert empty['state']['availability'] == no_sq['state']['availability'] == 'present'
    assert empty['parsed_byte_count'] == 0 < no_sq['parsed_byte_count']
    assert empty['headers'] == [] and len(no_sq['headers']) == 1
    assert all(any(i['code'] == 'metadata_missing' and i['field'] == 'SQ' for i in r['issues'])
               for r in (empty, no_sq))
    assert 'producer_failed' in codes(failed)
    assert failed['rows'][0]['length_bp'] == 100
    assert failed['state']['output_extent'] != 'complete'
    for record in (missing, empty, no_sq, failed):
        validate_atac_parsed_table(record)


def test_optional_unknown_m5_never_becomes_a_digest_or_reference_mismatch():
    result = parse_header(b'@SQ\tSN:chr1\tLN:100\n')
    assert result['rows'][0]['sequence_md5'] is None
    assert result['issues'] == []
    assert result['state']['format'] == 'compatible'


def test_partial_and_failed_stream_preserve_prefix_and_exact_read_extent():
    raw = b'@SQ\tSN:chr1\tLN:100\n'
    partial = parse_header(raw, supplied_extent='partial')
    assert partial['state']['identity'] == 'verified'
    assert partial['state']['byte_extent'] == partial['state']['output_extent'] == 'partial'
    assert partial['data_row_count'] is None
    class FailingStream:
        def __init__(self):
            self.reads = 0
        def read(self, size):
            self.reads += 1
            if self.reads == 1:
                return raw + b'@SQ\tSN:chr2\tLN:'
            raise OSError('synthetic interrupted supplied stream')
    stream = FailingStream()
    failed = parse_header(stream)
    assert failed['parsed_byte_count'] == len(raw + b'@SQ\tSN:chr2\tLN:')
    assert failed['parsed_sha256'] == hashlib.sha256(raw + b'@SQ\tSN:chr2\tLN:').hexdigest()
    assert failed['physical_line_count'] == 1
    assert failed['rows'] == partial['rows']
    assert failed['data_row_count'] is None
    assert {'captured_bytes_partial', 'stream_read_failed'} <= codes(failed)
    assert failed['state']['byte_extent'] == failed['state']['output_extent'] == 'partial'
    assert stream.reads == 2
    validate_atac_parsed_table(partial)
    validate_atac_parsed_table(failed)


@pytest.mark.parametrize('changes', [dict(expected_sha256='0' * 64), dict(expected_size_bytes=999),
                                   dict(expected_size_bytes=None, expected_sha256=None)])
def test_mismatched_and_unknown_input_identity_never_become_verified(changes):
    result = parse_header(b'@SQ\tSN:chr1\tLN:100\n', **changes)
    assert result['rows'][0]['length_bp'] == 100
    assert result['state']['identity'] == ('unverified' if changes.get('expected_sha256', '') is None else 'mismatch')
    assert result['state']['output_extent'] != 'complete'
    validate_atac_parsed_table(result)


@pytest.mark.parametrize('changes', [dict(ordinal=True), dict(ordinal=-1), dict(ordinal=1.0),
                                   dict(run=''), dict(input_ref=None)])
def test_impossible_binding_arguments_raise_without_acquisition(changes):
    with pytest.raises(ValueError, match='invalid_atac_bam_reference_binding'):
        parse_header(b'', **changes)


@pytest.mark.parametrize('content', ['a/path.bam', Path('a/path.bam'), io.StringIO('@SQ\tSN:chr1\tLN:1')])
def test_path_and_text_stream_are_not_acquired_as_supplied_binary_content(content):
    with pytest.raises(ValueError, match='atac_.*required'):
        parse_header(content)


@pytest.mark.parametrize('field,value', [('length_bp', True), ('sequence_md5', 'a' * 64),
                                       ('chromosome', 2), ('original_fields', ['@HD']), ('extra', 1)])
def test_exact_reference_row_validation_rejects_wrong_types_and_extra_fields(field, value):
    result = parse_header(b'@SQ\tSN:chr1\tLN:100\n')
    result['rows'][0][field] = value
    with pytest.raises(ValueError, match='invalid_atac_bam_reference_row'):
        validate_atac_parsed_table(result)


def test_parsed_binding_key_and_header_kind_are_validated():
    result = native_headers()[0]
    result['binding_key'] = 'callpeak-1:input:1'
    with pytest.raises(ValueError, match='invalid_atac_parsed_table'):
        validate_atac_parsed_table(result)
    result = native_headers()[0]
    result['headers'][0]['kind'] = 'unrestricted_header_kind'
    with pytest.raises(ValueError, match='invalid_atac_parsed_table'):
        validate_atac_parsed_table(result)


def test_actual_native_headers_reach_sheet_unchanged_with_distinct_input_occurrences(tmp_path):
    inputs = native_inputs()
    inputs['bam_references'] = native_headers()
    original = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == original
    assert sheet['bam_references'] == original['bam_references']
    assert [r['input_artifact_ref'] for r in sheet['bam_references']] == ['condition1.bam', 'condition2.bam']
    assert [r['rows'][0]['length_bp'] for r in sheet['bam_references']] == [12000, 12000]
    assert sheet['bam_references'][0]['artifact']['artifact_ref'] == sheet['bam_references'][1]['artifact']['artifact_ref']
    assert sheet['bam_references'][0]['artifact']['producer_run_ref'] != inputs['callpeak_bindings'][0]['producer_ref']
    assert [d['count'] for d in sheet['depth_selection']['conditions']] == [100, 200]
    assert sheet['data_status'] == 'complete_reported_data'
    assert not any(i['field'] == 'bam_references' for i in sheet['issues'])
    (tmp_path / 'filled_bam_reference_sheet.json').write_text(json.dumps(sheet, indent=2, allow_nan=False) + '\n')
    sheet['bam_references'][0]['rows'][0]['length_bp'] = 1
    assert inputs == original


@pytest.mark.parametrize('change,field', [('run', 'callpeak_run_key'), ('ordinal', 'input_ordinal'), ('ref', 'input_artifact_ref')])
def test_wrong_run_input_ordinal_and_source_ref_remain_bound_qualifications(change, field):
    inputs = native_inputs()
    kwargs = {'run': 'unknown-run'} if change == 'run' else {'ordinal': 3} if change == 'ordinal' else {'input_ref': 'condition2.bam'}
    record = parse_header((HEADERS / 'condition1.sam_header.txt').read_bytes(), **kwargs)
    inputs['bam_references'] = [record, native_headers()[1]]
    before = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == before and sheet['bam_references'][0] == record
    assert any(i['code'] == 'condition_binding_conflict' and i['field'] == field
               and i['binding_key'] == record['binding_key'] for i in sheet['issues'])
    assert any(i['code'] == 'metadata_missing' and i['binding_key'] == 'callpeak-1:input:0'
               and i['field'] == 'bam_references' for i in sheet['issues'])


def test_duplicate_occurrence_never_deduplicates_or_selects_a_dictionary():
    inputs = native_inputs()
    inputs['bam_references'] = native_headers()
    inputs['bam_references'].append(deepcopy(inputs['bam_references'][0]))
    before = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == before and sheet['bam_references'] == before['bam_references']
    assert sum(i['code'] == 'metadata_conflict' and i['field'] == 'bam_references'
               for i in sheet['issues']) == 2


def test_identical_header_and_input_content_in_different_selected_positions_is_not_a_conflict():
    inputs = native_inputs()
    inputs['callpeak_bindings'][0]['treatment_input_refs'].append('condition1.bam')
    inputs['samples'][0]['input_artifact_refs'].append('condition1.bam')
    inputs['bam_references'] = native_headers()
    second = deepcopy(inputs['bam_references'][0])
    second.update(input_ordinal=1, binding_key='callpeak-1:input:1')
    inputs['bam_references'].append(second)
    sheet = build_atac_differential_sheet(**inputs)
    assert len(sheet['bam_references']) == 3
    assert sheet['bam_references'][0]['artifact'] == sheet['bam_references'][2]['artifact']
    assert not any(i['field'] == 'bam_references' for i in sheet['issues'])


def test_explicit_tracks_and_historical_native_data_do_not_gain_invented_headers():
    explicit = build_atac_differential_sheet(**explicit_inputs())
    assert explicit['bam_references'] == []
    assert not any(i['field'] == 'bam_references' for i in explicit['issues'])
    native = build_atac_differential_sheet(**native_inputs())
    assert native['bam_references'] == []
    assert [(i['code'], i['binding_key']) for i in native['issues'] if i['field'] == 'bam_references'] == [
        ('metadata_missing', 'callpeak-1:input:0'), ('metadata_missing', 'callpeak-2:input:0')]
    assert [d['count'] for d in native['depth_selection']['conditions']] == [100, 200]


def test_length_md5_alias_and_extra_contigs_remain_native_facts_for_the_separate_bridge():
    inputs = native_inputs()
    inputs['reference']['aliases'] = [dict(source_chromosome='Toy', target_chromosome='chrToy',
                                          reference_id='toy', source_refs=['explicit-alias'])]
    inputs['bam_references'] = [parse_header(
        (f'@SQ\tSN:Toy\tLN:{length}\tM5:{md5}\n@SQ\tSN:extra\tLN:99\n').encode(),
        run=f'callpeak-{number}', input_ref=f'condition{number}.bam')
        for number, length, md5 in ((1, 11000, 'a' * 32), (2, 12000, 'b' * 32))]
    before = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == before
    assert sheet['bam_references'] == before['bam_references']
    assert sheet['reference_relation'] == 'same_supplied_reference'
    assert 'reference_conflict' not in codes(sheet)
    assert [r['rows'][0]['length_bp'] for r in sheet['bam_references']] == [11000, 12000]
    assert [r['rows'][0]['sequence_md5'] for r in sheet['bam_references']] == ['a' * 32, 'b' * 32]
    assert all(r['rows'][1]['chromosome'] == 'extra' for r in sheet['bam_references'])


def test_saved_only_parsing_and_assembly_after_selected_bam_copies_are_absent(monkeypatch, tmp_path):
    inputs = native_inputs()
    inputs['bam_references'] = native_headers()
    selected_paths = []
    for number in (1, 2):
        path = tmp_path / f'selected-condition{number}.bam'
        path.write_bytes((NATIVE / f'bam_inputs/condition{number}.bam').read_bytes())
        selected_paths.append(path)
        ref = str(path)
        inputs['samples'][number - 1]['input_artifact_refs'] = [ref]
        inputs['callpeak_bindings'][number - 1]['treatment_input_refs'] = [ref]
        inputs['bam_references'][number - 1]['input_artifact_ref'] = ref
    sheet = build_atac_differential_sheet(**inputs)
    saved = tmp_path / 'saved_bam_reference_sheet.json'
    saved.write_text(json.dumps(sheet, allow_nan=False))
    restored = json.loads(saved.read_text())
    raw_headers = [(HEADERS / f'condition{n}.sam_header.txt').read_bytes() for n in (1, 2)]
    for path in selected_paths:
        path.unlink()
        assert not path.exists()
    def forbidden(*args, **kwargs):
        raise AssertionError('saved-only parser/assembly must not reopen inputs or execute acquisition')
    monkeypatch.setattr('builtins.open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    before = deepcopy(restored)
    for number, raw in enumerate(raw_headers):
        old = restored['bam_references'][number]
        reparsed = parse_atac_bam_reference(raw, artifact=old['artifact'],
            callpeak_run_key=old['callpeak_run_key'], input_ordinal=old['input_ordinal'],
            input_artifact_ref=old['input_artifact_ref'])
        assert reparsed == old
    rebuilt = build_atac_differential_sheet(**sheet_arguments(restored))
    assert restored == before
    assert rebuilt['bam_references'] == restored['bam_references']
    assert [r['rows'][0]['length_bp'] for r in rebuilt['bam_references']] == [12000, 12000]
    # Assembly may repeat its existing source qualifications on an already
    # assembled table. Its native numerical rows and supplied input stay intact.
    assert [track['rows'] for track in rebuilt['tracks']] == [track['rows'] for track in restored['tracks']]
