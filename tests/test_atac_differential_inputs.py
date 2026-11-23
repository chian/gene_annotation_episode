"""Native bytes are retained packet460 outputs; other cases are explicit fixtures."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shlex
import tracemalloc

import pytest

from gene_annotation_episode.atac_differential_contracts import (
    AtacTableReadError, BEDGRAPH_COLUMNS, validate_atac_callpeak_binding, validate_atac_parsed_table,
)
from gene_annotation_episode.atac_differential_inputs import (
    iter_atac_bedgraph_records, iter_atac_track_rows, iter_atac_track_table_rows,
    parse_atac_bedgraph, parse_macs2_bdgdiff_bed, parse_macs2_narrowpeak,
    parse_macs2_peaks_xls, parse_macs2_summits_bed,
)


XLS_HEADER = b'chr\tstart\tend\tlength\tabs_summit\tpileup\t-log10(pvalue)\tfold_enrichment\t-log10(qvalue)\tname\n'


def artifact(content, ref='input.bdg', fmt='bedgraph4', producer=None):
    return dict(artifact_ref=ref, format=fmt,
                expected_sha256=hashlib.sha256(content).hexdigest() if content is not None else None,
                expected_size_bytes=len(content) if content is not None else None,
                supplied_extent='complete', producer_run_ref=producer,
                producer_outcome='succeeded' if producer else 'not_run', writer_closed=True if producer else None,
                producer_name='MACS2' if producer else None, producer_version='2.2.9.1' if producer else None,
                producer_source_ref='MACS2-2.2.9.1' if producer else None,
                origin='synthetic_engineering_fixture')


def track_binding(role='signal1', ref='input.bdg', *, native=False):
    signal = role.startswith('signal')
    return dict(track_key=role, condition_id='c' + role[-1], sample_ids=['s' + role[-1]],
                role='signal' if signal else 'model_background',
                callpeak_run_key='callpeak-' + role[-1] if native else None,
                reference_id='toy', value_unit=('extended_tag_pileup' if signal else 'model_expected_extended_tag_pileup') if native else ('supplied_signal' if signal else 'supplied_model_background'),
                normalization='raw_pileup', background_origin='unknown' if signal else 'self_model' if native else 'explicit_supplied_track',
                source_artifact_ref=ref)


def comparison():
    return dict(comparison_key='comparison', condition1_id='c1', condition2_id='c2', reference_id='toy',
                track_keys={r: r for r in ('signal1', 'background1', 'signal2', 'background2')}, selected_argv=[],
                selected_parameters=dict(depth1_lexeme='0.0001', depth2_lexeme='0.0002', depth_unit='million_tags',
                                         cutoff_log10_lr=3, minimum_length_bp=50, maximum_gap_bp=0, native_pseudocount=0.01),
                artifact_roles=dict(condition1='condition1_differential.bed', condition2='condition2_differential.bed', common='common.bed'),
                producer_ref='native-bdgdiff')


def codes(result):
    return {i['code'] for i in result['issues']}


def parse_track(data, **changes):
    a = artifact(data)
    a.update(changes)
    return parse_atac_bedgraph(data, artifact=a, binding=track_binding())


def table_bytes(rows, *, order='native_file_order'):
    raw = b''.join((json.dumps(list(row), allow_nan=False, separators=(',', ':')) + '\n').encode() for row in rows)
    manifest = dict(storage='retained_table', artifact_ref='numeric.jsonl', format='atac_bedgraph_rows_jsonl',
                    columns=list(BEDGRAPH_COLUMNS), row_count=len(rows), sha256=hashlib.sha256(raw).hexdigest(),
                    byte_count=len(raw), order=order, source_artifact_ref='input.bdg')
    return raw, manifest


def test_headers_crlf_final_nonterminated_row_and_arbitrary_chunk_boundaries():
    raw = b'# original\r\ntrack name="x"\r\nbrowser position chrT\r\n\r\nchrT\t0\t5\t-0.00000\r\nchrT\t5\t9\t5.42506e-07'
    events = list(iter_atac_bedgraph_records((raw[i:i + 1] for i in range(len(raw))), artifact=artifact(raw), binding=track_binding()))
    assert [e['header']['kind'] for e in events if e['kind'] == 'header'] == ['comment', 'track', 'browser', 'blank']
    rows = [e['row'] for e in events if e['kind'] == 'row']
    assert rows[0][1] == 5
    assert rows[0][7:9] == (-0.0, '-0.00000')
    assert raw[rows[0][2]:rows[0][3]].endswith(b'\r\n')
    assert rows[1][8] == '5.42506e-07'
    assert events[-1]['summary']['state']['output_extent'] == 'complete'
    assert events[-1]['summary']['physical_line_count'] == 6


def test_gaps_duplicates_overlaps_and_unsorted_rows_remain_occurrences():
    raw = b'chrT\t100\t200\t2\nchrT\t0\t50\t1\nchrT\t0\t50\t1\nchrT\t40\t60\t3\n'
    result = parse_track(raw)
    assert len(result['rows']) == 4
    assert result['ordered_row_index'] == [1, 2, 3, 0]
    assert result['overlap_groups'] == [[1, 2, 3]]
    assert result['chromosome_extents'][0]['has_unreported_internal_span'] is True
    assert result['geometry_inspection'] == 'complete'
    assert 'unsorted_track_rows' in codes(result)
    assert [r[0] for r in iter_atac_track_rows(result, chromosome='chrT')] == [1, 2, 3, 0]
    streamed = list(iter_atac_bedgraph_records([raw], artifact=artifact(raw), binding=track_binding()))[-1]['summary']
    assert streamed['geometry_inspection'] == 'partial'


@pytest.mark.parametrize('token,expected,code', [
    ('NaN', None, 'nonfinite_number'), ('Inf', None, 'nonfinite_number'), ('1e999', None, 'numeric_out_of_range'),
    ('1e-999', None, 'numeric_out_of_range'), ('-2.50', -2.5, 'negative_pileup'), ('oops', None, 'invalid_number'),
])
def test_invalid_number_preserves_exact_token_and_locatable_span(token, expected, code):
    result = parse_track(('chrT\t0\t4\t' + token + '\n').encode())
    assert result['rows'][0][7:] == (expected, token)
    assert result['ordered_row_index'] == [0]
    assert result['unlocated_invalid_row_count'] == 0
    assert code in codes(result)


@pytest.mark.parametrize('start,end', [('0.0', '10'), ('-1', '10'), ('10', '10'), ('11', '10'), ('0', str(2**63))])
def test_unusable_geometry_stays_retained_and_never_enters_ordered_port(start, end):
    result = parse_track(f'chrT\t{start}\t{end}\t1\nchrT\t20\t30\t2\n'.encode())
    assert len(result['rows']) == 2
    assert result['unlocated_invalid_row_count'] == 1
    assert result['ordered_row_index'] == [1]
    assert [r[0] for r in iter_atac_track_rows(result, chromosome='chrT')] == [1]
    assert 'invalid_coordinate' in codes(result)


def test_malformed_middle_and_invalid_utf8_preserve_other_occurrences():
    raw = b'chrT\t0\t1\t1\nwrong columns\n\xff\t2\t3\t4\nchrT\t4\t5\t2\n'
    result = parse_track(raw)
    assert [r[0] for r in result['rows']] == [0, 3]
    assert [r['row_ordinal'] for r in result['invalid_records']] == [1, 2]
    assert result['unlocated_invalid_row_count'] == 2
    assert result['data_row_count'] == 4
    assert result['state']['output_extent'] == 'partial'
    assert {'wrong_column_count', 'invalid_utf8'} <= codes(result)


def test_strict_tabs_and_empty_versus_missing():
    assert parse_track(b'chrT 0 1 2\n')['rows'] == []
    empty = parse_track(b'')
    missing = parse_atac_bedgraph(None, artifact=artifact(None), binding=track_binding())
    assert empty['data_row_count'] == 0
    assert empty['chromosome_extents'] == []
    assert missing['data_row_count'] is None
    assert missing['state']['availability'] == 'missing'


def test_partial_bytes_and_hash_size_mismatch_do_not_seal_complete_population():
    raw = b'chrT\t0\t10\t1\nchrT\t10\t20\t2'
    result = parse_track(raw, supplied_extent='partial')
    assert len(result['rows']) == 2
    assert result['data_row_count'] is None
    assert result['state']['output_extent'] == 'partial'
    wrong = parse_track(raw, expected_size_bytes=len(raw) + 5, expected_sha256='0' * 64)
    assert wrong['state']['identity'] == 'mismatch'
    assert wrong['state']['output_extent'] == 'partial'
    assert len(wrong['rows']) == 2


class BrokenStream:
    def __init__(self, prefix):
        self.prefix = prefix

    def read(self, size):
        if self.prefix is not None:
            raw, self.prefix = self.prefix, None
            return raw
        raise OSError('fixture interruption')


def test_failed_native_stream_preserves_rows_and_never_emits_summary():
    raw = b'chrT\t0\t10\t1\n'
    def chunks():
        yield raw
        raise OSError('fixture interruption')
    events = []
    with pytest.raises(AtacTableReadError) as error:
        for event in iter_atac_bedgraph_records(chunks(), artifact=artifact(raw), binding=track_binding()):
            events.append(event)
    assert [e['kind'] for e in events] == ['row']
    assert error.value.rows_read == 1
    assert error.value.bytes_read == len(raw)
    recovered = parse_atac_bedgraph(BrokenStream(raw), artifact=artifact(raw), binding=track_binding())
    assert len(recovered['rows']) == 1
    assert recovered['state']['output_extent'] == 'partial'
    assert 'stream_read_failed' in codes(recovered)


def test_track_jsonl_round_trip_and_identity_check_occurs_after_last_row():
    track = parse_track(b'chrT\t0\t10\t1\nchrT\t10\t20\t2\n')
    raw, manifest = table_bytes(track['rows'])
    assert list(iter_atac_track_table_rows((raw[i:i + 3] for i in range(0, len(raw), 3)), table=manifest)) == track['rows']
    wrong = dict(manifest, sha256='0' * 64)
    iterator = iter_atac_track_table_rows([raw], table=wrong)
    assert next(iterator) == track['rows'][0]
    assert next(iterator) == track['rows'][1]
    with pytest.raises(AtacTableReadError, match='identity_mismatch') as error:
        next(iterator)
    assert error.value.rows_read == 2
    assert error.value.bytes_read == len(raw)


@pytest.mark.parametrize('change', ['size', 'count', 'no_newline', 'bool', 'nan', 'order'])
def test_track_jsonl_rejects_changed_physical_or_structural_contract(change):
    rows = parse_track(b'chrT\t0\t10\t1\nchrT\t10\t20\t2\n')['rows']
    if change == 'bool':
        rows[0] = (True, *rows[0][1:])
    if change == 'order':
        rows.reverse()
    raw, manifest = table_bytes(rows)
    if change == 'size':
        manifest['byte_count'] += 1
    if change == 'count':
        manifest['row_count'] += 1
    if change == 'no_newline':
        raw = raw[:-1]
        manifest.update(byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if change == 'nan':
        raw = raw.replace(b'1.0', b'NaN')
        manifest.update(byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(AtacTableReadError):
        list(iter_atac_track_table_rows([raw], table=manifest))


def test_chromosome_filter_exhausts_remainder_before_complete_return():
    rows = parse_track(b'chrA\t0\t10\t1\nchrB\t0\t10\t2\n')['rows']
    raw, manifest = table_bytes(rows, order='chromosome_start_end_source_ordinal')
    manifest['sha256'] = '0' * 64
    track = dict(rows=manifest, ordered_row_index=None)
    iterator = iter_atac_track_rows(track, chromosome='chrA', ordered_rows=iter_atac_track_table_rows([raw], table=manifest))
    assert next(iterator) == rows[0]
    with pytest.raises(AtacTableReadError):
        next(iterator)


def test_large_stream_has_bounded_parsing_memory_and_all_rows():
    count = 30000
    def chunks():
        for i in range(count):
            yield f'chrT\t{i}\t{i + 1}\t0.00000\n'.encode()
    # Expected identity is calculated with a separate constant-memory pass.
    digest = hashlib.sha256()
    size = 0
    for raw in chunks():
        digest.update(raw)
        size += len(raw)
    a = artifact(b'')
    a.update(expected_sha256=digest.hexdigest(), expected_size_bytes=size)
    tracemalloc.start()
    observed, summary = 0, None
    for event in iter_atac_bedgraph_records(chunks(), artifact=a, binding=track_binding()):
        if event['kind'] == 'row':
            observed += 1
        elif event['kind'] == 'summary':
            summary = event['summary']
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert observed == summary['data_row_count'] == count
    assert peak < 2_000_000


def test_no_producer_context_does_not_make_empty_native_bed_a_completed_zero():
    cp = comparison()
    raw = b''
    result = parse_macs2_bdgdiff_bed(raw, artifact=artifact(raw, 'common.bed', 'macs2_bdgdiff_bed5'),
                                    comparison=cp, category='common')
    assert result['data_row_count'] is None
    assert result['state']['output_extent'] == 'unknown'


def test_ordered_duplicate_records_keep_both_source_locations():
    result = parse_track(b'chrT\t0\t10\t1\nchrT\t0\t10\t1\n')
    duplicate = next(i for i in result['issues'] if i['code'] == 'duplicate_record')
    assert duplicate['row_ordinals'] == [0, 1]
    assert [p['line_number'] for p in duplicate['locations']] == [1, 2]
    assert result['overlap_groups'] == [[0, 1]]
    assert len(list(iter_atac_track_rows(result, chromosome='chrT'))) == 2


@pytest.mark.parametrize('field', ['parsed_byte_count', 'data_row_count', 'unlocated_invalid_row_count'])
def test_parsed_record_boolean_counters_fail_structural_validation(field):
    result = parse_track(b'chrT\t0\t10\t1\n')
    result[field] = True
    with pytest.raises(ValueError, match='invalid_atac_parsed_table'):
        validate_atac_parsed_table(result)


def test_retained_table_stream_io_failure_keeps_already_emitted_row():
    row = parse_track(b'chrT\t0\t10\t1\n')['rows'][0]
    raw, manifest = table_bytes([row])
    def failed():
        yield raw
        raise OSError('retained table source failed')
    iterator = iter_atac_track_table_rows(failed(), table=manifest)
    assert next(iterator) == row
    with pytest.raises(AtacTableReadError, match='stream_read_failed') as error:
        next(iterator)
    assert error.value.rows_read == 1
    assert error.value.bytes_read == len(raw)


def test_wrong_declared_track_format_stays_unsupported_with_partial_readable_rows():
    raw = b'chrT\t0\t10\t1.25000\nbad\nchrT\t20\t30\tNaN\n'
    result = parse_track(raw, format='macs2_bdgdiff_bed5')
    assert result['state']['format'] == 'unsupported'
    assert result['state']['output_extent'] == 'partial'
    assert result['rows'][0][4:] == ('chrT', 0, 10, 1.25, '1.25000')
    assert result['rows'][1][7:] == (None, 'NaN')
    assert result['malformed_data_row_count'] == 2
    assert len(result['invalid_records']) == 1
    assert {'unsupported_format', 'wrong_column_count', 'nonfinite_number'} <= codes(result)


