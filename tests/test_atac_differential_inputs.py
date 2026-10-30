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


NATIVE = Path(__file__).resolve().parents[1] / 'verification/tool_graders_atac_differential_plan_2026-10-27_460/native001'
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


def callpeak(number=1):
    name = 'condition' + str(number)
    original = (NATIVE / 'bam_outputs' / (name + '_peaks.xls')).read_text()
    command = next(line[len('# Command line: '):] for line in original.splitlines() if line.startswith('# Command line: '))
    return dict(run_key='callpeak-' + str(number), condition_id='c' + str(number), sample_ids=['s' + str(number)],
                reference_id='toy', treatment_input_refs=[name + '.bam'],
                supplied_control_sample_ids=[], supplied_control_input_refs=[], selected_format='BAM', paired_end=False,
                selected_argv=shlex.split(command), selected_parameters=dict(
                    genome_size_argument='12000', effective_genome_size_bp=12000, keep_duplicates=1,
                    nomodel=True, shift_bp=-100, extension_size_bp=200, qvalue_cutoff=0.05, pvalue_cutoff=None,
                    store_bedgraph=True, spmr=False, broad=False, downsample=False,
                    small_local_window_bp=None, large_local_window_bp=10000),
                artifact_roles=dict(peaks_xls=name + '_peaks.xls', narrowpeak=name + '_peaks.narrowPeak',
                                    summits=name + '_summits.bed', signal_track=name + '_treat_pileup.bdg',
                                    background_track=name + '_control_lambda.bdg'), producer_ref='native-callpeak-' + str(number))


def comparison():
    return dict(comparison_key='comparison', condition1_id='c1', condition2_id='c2', reference_id='toy',
                track_keys={r: r for r in ('signal1', 'background1', 'signal2', 'background2')}, selected_argv=[],
                selected_parameters=dict(depth1_lexeme='0.0001', depth2_lexeme='0.0002', depth_unit='million_tags',
                                         cutoff_log10_lr=3, minimum_length_bp=50, maximum_gap_bp=0, native_pseudocount=0.01),
                artifact_roles=dict(condition1='condition1_differential.bed', condition2='condition2_differential.bed', common='common.bed'),
                producer_ref='native-bdgdiff')


def native_report(number=1, kind='xls'):
    cp = callpeak(number)
    role, fmt, parser = {'xls': ('peaks_xls', 'macs2_peaks_xls_narrow', parse_macs2_peaks_xls),
                         'narrowpeak': ('narrowpeak', 'macs2_narrowpeak10', parse_macs2_narrowpeak),
                         'summits': ('summits', 'macs2_summits_bed5', parse_macs2_summits_bed)}[kind]
    filename = cp['artifact_roles'][role]
    data = (NATIVE / 'bam_outputs' / filename).read_bytes()
    return parser(data, artifact=artifact(data, filename, fmt, cp['producer_ref']), callpeak=cp)


def codes(result):
    return {i['code'] for i in result['issues']}


def parse_track(data, **changes):
    a = artifact(data)
    a.update(changes)
    return parse_atac_bedgraph(data, artifact=a, binding=track_binding())


def table_bytes(rows, *, order='native_file_order'):
    raw = b''.join((json.dumps(list(row), allow_nan=False, separators=(',', ':')) + '\n').encode() for row in rows)
    manifest = dict(storage='retained_table', artifact_ref='numeric.jsonl', format='atac_bedgraph_rows_jsonl_v1',
                    columns=list(BEDGRAPH_COLUMNS), row_count=len(rows), sha256=hashlib.sha256(raw).hexdigest(),
                    byte_count=len(raw), order=order, source_artifact_ref='input.bdg')
    return raw, manifest


def test_all_original_30_byte_identities_are_pinned():
    # This establishes original fixture custody, distinct from the parser tests.
    manifest = json.loads((NATIVE / 'NATIVE_FILES.json').read_text())
    assert len(manifest['files']) == 30
    for row in manifest['files']:
        data = (NATIVE / row['path']).read_bytes()
        assert len(data) == row['size_bytes']
        assert hashlib.sha256(data).hexdigest() == row['sha256']


@pytest.mark.parametrize('name,role,count,last', [
    ('condition1_treat_pileup.bdg', 'signal1', 110, 8060),
    ('condition1_control_lambda.bdg', 'background1', 35, 8060),
    ('condition2_treat_pileup.bdg', 'signal2', 210, 10060),
    ('condition2_control_lambda.bdg', 'background2', 69, 10060),
])
def test_retained_native_track_occurrences_and_byte_locations(name, role, count, last):
    raw = (NATIVE / 'bam_outputs' / name).read_bytes()
    result = parse_atac_bedgraph(io.BytesIO(raw), artifact=artifact(raw, name, producer='native-callpeak-' + role[-1]),
                                binding=track_binding(role, name, native=True))
    assert result['data_row_count'] == result['readable_data_row_count'] == count
    assert result['state'] == dict(availability='present', byte_extent='complete', identity='verified', format='compatible', output_extent='complete')
    assert result['rows'][-1][6] == last
    assert result['chromosome_extents'][0]['reference_length_bp'] is None
    assert result['chromosome_extents'][0]['has_unreported_tail'] is None
    assert result['native_writer_precision'] == 'fixed_5_decimal_places'
    for row, line in zip(result['rows'], raw.splitlines(keepends=True), strict=True):
        assert raw[row[2]:row[3]] == line
        assert row[8] == line.decode().strip().split('\t')[3]
    if role == 'signal1':
        assert result['rows'][50][4:] == ('chrToy', 949, 1100, 50.0, '50.00000')


def test_retained_explicit_track_exact_tuple():
    raw = (NATIVE / 'explicit_tracks/t1.bdg').read_bytes()
    result = parse_track(raw)
    assert result['rows'][1] == (1, 2, 15, 33, 'chrToy', 100, 200, 20.0, '20')
    assert result['rows'][0][7:9] == (0.0, '0')


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


def test_native_xls_counts_geometry_precision_and_control_meaning():
    result = native_report(1)
    numbers = result['reported_numbers']
    assert numbers['treatment_total_tags']['value'] == 105
    assert numbers['treatment_postfilter_tags'] == dict(value=100, lexeme='100', state='present',
        locations=[dict(line_number=21, byte_start=1320, byte_end=1361)])
    assert numbers['treatment_redundant_rate']['value'] == 0.05
    assert numbers['treatment_redundant_rate']['lexeme'] == '0.05'
    assert numbers['shift_bp']['value'] == -100
    assert numbers['shift_bp']['lexeme'] == '100'
    assert result['peak_geometry'][0] == dict(row_ordinal=0, start0=906, end0=1143, summit0=1020, span_bp=237, status='valid')
    assert result['rows'][0]['start1'] == 907
    assert result['rows'][0]['pileup'] == 50
    assert result['reported_metadata']['control_presence'] == 'absent'
    assert result['reported_metadata']['paired_end'] is False
    assert numbers['control_total_tags']['state'] == 'not_measured'
    assert numbers['treatment_total_fragments']['state'] == 'not_measured'
    assert result['data_row_count'] == 1
    assert result['state']['output_extent'] == 'complete'


def test_native_narrowpeak_1045_is_not_capped_and_summit_agrees():
    result, summits = native_report(2, 'narrowpeak'), native_report(2, 'summits')
    row = result['rows'][0]
    assert row['display_score'] == 1045
    assert row['signal_value'] == 23.3077
    assert row['summit_offset0'] == 111
    assert row['start0'] + row['summit_offset0'] == summits['rows'][0]['start0'] == 3020
    assert row['minus_log10_qvalue'] == summits['rows'][0]['score'] == 104.594
    assert result['score_basis'] == 'minus_log10_qvalue'
    assert not result['issues']


def test_native_bdgdiff_reported_coordinates_and_rounded_scores_unchanged():
    cp = comparison()
    raw = (NATIVE / 'explicit_tracks/condition1.bed').read_bytes()
    cp['artifact_roles']['condition1'] = 'condition1.bed'
    result = parse_macs2_bdgdiff_bed(raw, artifact=artifact(raw, 'condition1.bed', 'macs2_bdgdiff_bed5', cp['producer_ref']), comparison=cp, category='condition1')
    assert result['rows'][0]['reported_start0'] == 0
    assert result['rows'][0]['reported_end0'] == 100
    assert result['rows'][0]['reported_score'] == 17.7408
    assert result['rows'][0]['original_fields'][4] == '17.7408'
    assert 'native_bdgdiff_coordinate_displacement' in codes(result)
    assert result['coordinate_qualification'] == 'macs2_2_2_9_1_native_endpos_displacement_demonstrated'


def test_native_header_only_is_zero_only_with_complete_source_context():
    cp = comparison()
    raw = (NATIVE / 'bam_outputs/common.bed').read_bytes()
    assert len(raw) == 89
    a = artifact(raw, 'common.bed', 'macs2_bdgdiff_bed5', cp['producer_ref'])
    result = parse_macs2_bdgdiff_bed(raw, artifact=a, comparison=cp, category='common')
    assert result['data_row_count'] == 0
    assert len(result['headers']) == 1
    a.update(producer_outcome='unknown', writer_closed=False)
    result = parse_macs2_bdgdiff_bed(raw, artifact=a, comparison=cp, category='common')
    assert result['data_row_count'] is None
    assert result['state']['output_extent'] == 'unknown'


def test_native_sentinels_missing_header_and_partial_geometry_preserve_scores():
    cp = callpeak()
    raw = b'chrToy\t1\t5\tpeak\t1045\t.\t2\t-1\t-1\t-1\n'
    np = parse_macs2_narrowpeak(raw, artifact=artifact(raw, cp['artifact_roles']['narrowpeak'], 'macs2_narrowpeak10', cp['producer_ref']), callpeak=cp)
    assert np['rows'][0]['minus_log10_pvalue'] is None
    assert np['rows'][0]['minus_log10_qvalue'] is None
    assert np['rows'][0]['summit_offset0'] is None
    assert np['rows'][0]['display_score'] == 1045
    row = b'chrToy\t1\t10\t9\t0\t5\t3\t2\t1\tpeak\n'
    xls = parse_macs2_peaks_xls(XLS_HEADER + row, artifact=artifact(XLS_HEADER + row, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    assert xls['peak_geometry'][0]['status'] == 'invalid'
    assert xls['peak_geometry'][0]['summit0'] is None
    assert xls['rows'][0]['pileup'] == 5
    no_header = parse_macs2_peaks_xls(row, artifact=artifact(row, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    assert 'missing_column_header' in codes(no_header)
    assert no_header['rows'][0]['pileup'] == 5


def test_xls_conflicting_equal_repeated_metadata_and_nonexecuting_path_reader():
    cp = callpeak()
    raw = (b'# tags after filtering in treatment: 100\n# tags after filtering in treatment: 100\n'
           b'# tags after filtering in treatment: 101\n# control file = __import__("os").system("false")\n' + XLS_HEADER)
    result = parse_macs2_peaks_xls(raw, artifact=artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    number = result['reported_numbers']['treatment_postfilter_tags']
    assert number['state'] == 'conflicting'
    assert number['value'] is None
    assert len(number['locations']) == 3
    assert 'metadata_conflict' in codes(result)


def test_mode_metadata_conflict_and_fragment_counts_are_not_tags():
    cp = callpeak()
    raw = b'# format = BAMPE\n# Paired-End mode is on\n# total fragments in treatment: 20\n# fragments after filtering in treatment: 19\n' + XLS_HEADER
    result = parse_macs2_peaks_xls(raw, artifact=artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    assert result['reported_numbers']['treatment_postfilter_fragments']['value'] == 19
    assert result['reported_numbers']['treatment_postfilter_tags']['state'] == 'not_measured'
    assert 'metadata_conflict' in codes(result)


def test_boolean_selected_numeric_parameter_rejected_without_mutation():
    cp = callpeak()
    cp['selected_parameters']['extension_size_bp'] = True
    before = deepcopy(cp)
    with pytest.raises(ValueError, match='invalid_atac_callpeak_binding'):
        validate_atac_callpeak_binding(cp)
    assert cp == before


def test_no_producer_context_does_not_make_empty_native_bed_a_completed_zero():
    cp = comparison()
    raw = b''
    result = parse_macs2_bdgdiff_bed(raw, artifact=artifact(raw, 'common.bed', 'macs2_bdgdiff_bed5'),
                                    comparison=cp, category='common')
    assert result['data_row_count'] is None
    assert result['state']['output_extent'] == 'unknown'


def test_rounded_reported_cutoff_is_distinct_from_selected_parameter():
    cp = callpeak()
    cp['selected_parameters']['qvalue_cutoff'] = 0.005555555
    raw = (NATIVE / 'bam_outputs/condition1_peaks.xls').read_bytes().replace(b'# qvalue cutoff = 5.00e-02', b'# qvalue cutoff = 5.56e-03')
    result = parse_macs2_peaks_xls(raw, artifact=artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    assert result['reported_numbers']['qvalue_cutoff']['value'] == 0.00556
    assert result['reported_numbers']['qvalue_cutoff']['lexeme'] == '5.56e-03'
    assert not any(i['code'] == 'metadata_conflict' and i['field'] == 'qvalue_cutoff' for i in result['issues'])
    assert cp['selected_parameters']['qvalue_cutoff'] == 0.005555555


def test_spmr_and_downsampling_native_comments_qualify_selected_raw_claim():
    cp = callpeak()
    raw = (NATIVE / 'bam_outputs/condition1_peaks.xls').read_bytes()
    raw = b'# MACS will save fragment pileup signal per million reads\n# Larger dataset will be randomly sampled towards smaller dataset.\n' + raw
    result = parse_macs2_peaks_xls(raw, artifact=artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    assert {'unsupported_normalization', 'unsupported_mode'} <= codes(result)
    assert result['reported_numbers']['treatment_postfilter_tags']['value'] == 100


def test_ordered_duplicate_records_keep_both_source_locations():
    result = parse_track(b'chrT\t0\t10\t1\nchrT\t0\t10\t1\n')
    duplicate = next(i for i in result['issues'] if i['code'] == 'duplicate_record')
    assert duplicate['row_ordinals'] == [0, 1]
    assert [p['line_number'] for p in duplicate['locations']] == [1, 2]
    assert result['overlap_groups'] == [[0, 1]]
    assert len(list(iter_atac_track_rows(result, chromosome='chrT'))) == 2


def test_selected_bdgdiff_category_is_not_rewritten_from_conflicting_header():
    cp = comparison()
    raw = (NATIVE / 'explicit_tracks/condition1.bed').read_bytes()
    result = parse_macs2_bdgdiff_bed(raw, artifact=artifact(raw, cp['artifact_roles']['condition2'], 'macs2_bdgdiff_bed5', cp['producer_ref']), comparison=cp, category='condition2')
    assert result['category'] == 'condition2'
    assert 'condition_binding_conflict' in codes(result)
    assert result['rows'][0]['reported_score'] == 17.7408


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


def test_native_control_header_cannot_reassign_second_condition_as_matched_control():
    cp = callpeak(2)
    raw = (NATIVE / 'bam_outputs/condition2_peaks.xls').read_bytes()
    raw = raw.replace(b'# control file = None', b"# control file = ['unselected-control.bam']")
    result = parse_macs2_peaks_xls(raw, artifact=artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    assert result['reported_metadata']['control_presence'] == 'present'
    assert result['reported_numbers']['treatment_postfilter_tags']['value'] == 200
    assert cp['condition_id'] == 'c2'
    assert cp['supplied_control_input_refs'] == []
    assert any(i['code'] == 'metadata_conflict' and i['field'] == 'control_presence' for i in result['issues'])


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


def test_wrong_declared_peak_format_stays_unsupported_with_partial_readable_rows():
    cp = callpeak()
    raw = (NATIVE / 'bam_outputs/condition1_peaks.xls').read_bytes().replace(XLS_HEADER, XLS_HEADER + b'bad\n')
    result = parse_macs2_peaks_xls(raw, artifact=artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_narrowpeak10', cp['producer_ref']), callpeak=cp)
    assert result['state']['format'] == 'unsupported'
    assert result['state']['output_extent'] == 'partial'
    assert result['rows'][0]['pileup'] == 50
    assert result['rows'][0]['original_fields'][5] == '50'
    assert result['malformed_data_row_count'] == 1
    assert result['readable_data_row_count'] == 1
    assert result['invalid_records'][0]['fields'] == ['bad']
    assert {'unsupported_format', 'wrong_column_count'} <= codes(result)
