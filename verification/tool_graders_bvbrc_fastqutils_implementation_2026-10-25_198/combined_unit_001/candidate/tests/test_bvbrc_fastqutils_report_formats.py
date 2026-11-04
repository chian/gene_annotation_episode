"""Native report grammar checks. Fixtures are explicitly synthetic, not live jobs."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError, validate_native_document
from gene_annotation_episode.bvbrc_fastqutils_fastqc_reader import parse_fastqc_data, parse_fastqc_html, parse_fastqc_zip
from gene_annotation_episode.bvbrc_fastqutils_trim_reader import parse_trim_galore_report
from gene_annotation_episode.bvbrc_fastqutils_pair_report_reader import parse_fastq_pair_stderr
from gene_annotation_episode.bvbrc_fastqutils_hostile_reader import parse_hostile_json

FIXTURES = Path(__file__).parent / 'fixtures/bvbrc_fastqutils/reports'


def context(raw, fmt, version=None, scope='complete', identity='handcrafted_synthetic'):
    return {'analysis_id': 'report_test', 'document_id': 'report', 'task_ref': 'task:test',
        'content': {'source_ref': 'source:test', 'artifact_field': 'artifact_ref', 'artifact_ref': 'content:test',
                    'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)},
        'native_name': None, 'declared_format': fmt, 'producer_version': version,
        'transfer_scope': scope, 'identity': identity}


def parse(raw, parser=parse_fastqc_data, fmt='fastqc_data_0_12_1', version='0.12.1', **kwargs):
    result = parser(raw, context=context(raw, fmt, version, **kwargs))
    validate_native_document(result)
    return result


def cells(doc, metric):
    return [cell for cell in doc['cells'] if cell['metric'] == metric]


def one(doc, metric):
    rows = cells(doc, metric)
    assert len(rows) == 1
    return rows[0]


def archive(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as writer:
        for name, data in members: writer.writestr(name, data)
    return output.getvalue()


def hostile(rows=None):
    if rows is None:
        return (FIXTURES / 'hostile_source_executed_synthetic.json').read_bytes()
    return json.dumps(rows, ensure_ascii=False).encode()


def parse_hostile(raw, **kwargs):
    return parse(raw, parse_hostile_json, 'hostile_json_1_1_0', '1.1.0', **kwargs)


def test_all_twelve_modules_and_native_numerical_meanings():
    raw = (FIXTURES / 'fastqc_all_modules.txt').read_bytes()
    doc = parse(raw)
    assert len(doc['populations']) == 12
    assert [p['population_ordinal'] for p in doc['populations']] == list(range(12))
    assert len(doc['cells']) == 32
    assert len(doc['categories']) == 12
    assert one(doc, 'fastqc_total_sequences')['value'] == 200
    display = one(doc, 'fastqc_total_bases_display')
    assert (display['value'], display['unit'], display['native_token'], display['precision']) == (1.2, 'kbp', '1.2 kbp', 'native_truncated_display')
    assert one(doc, 'fastqc_base_quality_mean')['axis'] == {'kind': 'base_closed_1', 'label': '1-5', 'lower': 1, 'upper': 5}
    assert one(doc, 'fastqc_base_quality_lower_quartile')['state'] == 'undefined'
    assert one(doc, 'fastqc_base_quality_lower_quartile')['native_token'] == 'NaN'
    assert one(doc, 'fastqc_tile_quality_deviation')['value'] == -2.25
    assert one(doc, 'fastqc_tile_quality_deviation')['axis']['label'] == '1101'
    assert one(doc, 'fastqc_sequence_quality_count')['value'] == 200
    assert [(r['axis']['label'], r['value']) for r in cells(doc, 'fastqc_base_content_percent')] == [('G', 30), ('A', 25), ('T', 20), ('C', 25)]
    assert [r['value'] for r in cells(doc, 'fastqc_sequence_gc_smoothed_count')] == [.75, 1.25]
    assert one(doc, 'fastqc_n_percent')['unit'] == 'percent'
    assert one(doc, 'fastqc_length_bin_count')['axis']['upper'] == 10
    assert cells(doc, 'fastqc_duplication_bin_percent')[1]['axis']['label'] == '>10k+'
    assert one(doc, 'fastqc_kmer_scaled_count')['value'] == 15
    assert one(doc, 'fastqc_kmer_scaled_count')['unit'] == 'scaled_native_count'
    assert one(doc, 'fastqc_kmer_pvalue')['value'] == .0002
    assert one(doc, 'fastqc_kmer_obs_exp_max')['value'] == 7.5
    assert any(label['value'] == '1-5' and label['locator']['field'] == 'Max Obs/Exp Position' for label in doc['labels'])
    assert [r['axis']['label'] for r in cells(doc, 'fastqc_adapter_percent')] == ['Illumina Universal Adapter', 'Nextera Transposase Sequence']
    assert all(p['quality_encoding'] == 'unknown' for p in doc['populations'])
    for row in doc['cells']:
        location = row['locator']
        assert raw[location['byte_start']:location['byte_end']]


def test_absent_and_repeated_modules_do_not_renumber_population_slots():
    raw = b'##FastQC\t0.12.1\n' + b'>>Per base N content\tpass\n#Base\tN-Count\n1\t0\n>>END_MODULE\n' * 2
    doc = parse(raw)
    assert [p['population_ordinal'] for p in doc['populations']] == [6, 18]
    assert [p['section_ordinal'] for p in doc['populations']] == [0, 1]
    assert len({r['id'] for r in doc['cells']}) == 2
    assert not cells(doc, 'fastqc_total_sequences')


@pytest.mark.parametrize('name', ['Overrepresented sequences', 'Kmer Content', 'Adapter Content'])
def test_complete_empty_native_modules_have_no_invented_rows(name):
    raw = f'##FastQC\t0.12.1\n>>{name}\tpass\n>>END_MODULE\n'.encode()
    doc = parse(raw)
    assert doc['parse_scope'] == 'complete'
    assert len(doc['populations']) == 1 and not doc['cells']


def test_malformed_native_row_preserves_sibling_and_unknown_section_bytes():
    raw = b'##FastQC\t0.12.1\n>>Per base N content\twarn\n#Base\tN-Count\nBAD\t3\n2-3\t4\n>>END_MODULE\n>>Future module\twarn\n#Something\nkeep all of me\n>>END_MODULE\n'
    doc = parse(raw)
    assert one(doc, 'fastqc_n_percent')['value'] == 4
    assert one(doc, 'fastqc_n_percent')['locator']['row_ordinal'] == 1
    assert doc['parse_scope'] == 'partial'
    raw_future = next(r for r in doc['raw_blocks'] if r['native_name'] == 'Future module')
    loc = raw_future['locator']
    assert b'keep all of me' in raw[loc['byte_start']:loc['byte_end']]
    assert any(r['required_data'] == 'supported_parser' for r in doc['requirements'])


def test_wrong_table_header_is_local_and_does_not_relabel_columns():
    raw = b'##FastQC\t0.12.1\n>>Per base N content\tpass\n#Base\tCount\n1\t4\n>>END_MODULE\n>>Basic Statistics\tpass\n#Measure\tValue\nTotal Sequences\t10\n>>END_MODULE\n'
    doc = parse(raw)
    assert not cells(doc, 'fastqc_n_percent')
    assert one(doc, 'fastqc_total_sequences')['value'] == 10


def test_unclosed_module_retains_partial_numeric_population():
    doc = parse(b'##FastQC\t0.12.1\n>>Per base N content\tpass\n#Base\tN-Count\n1\t4\n')
    assert doc['parse_scope'] == 'partial'
    assert doc['populations'][0]['scope'] == 'partial'
    assert one(doc, 'fastqc_n_percent')['state'] == 'partial'


@pytest.mark.parametrize('scope', ['unknown', 'partial'])
def test_matching_hash_does_not_prove_transfer_or_population_completeness(scope):
    raw = (FIXTURES / 'fastqc_all_modules.txt').read_bytes()
    doc = parse(raw, scope=scope)
    assert {p['scope'] for p in doc['populations']} == {scope}
    assert one(doc, 'fastqc_total_sequences')['value'] == 200
    assert one(doc, 'fastqc_total_sequences')['state'] == ('partial' if scope == 'partial' else 'available')


def test_html_real_tables_and_graph_only_limitations():
    raw = (FIXTURES / 'fastqc_tables_graph.html').read_bytes()
    doc = parse(raw, parse_fastqc_html, 'fastqc_html_0_12_1')
    assert one(doc, 'fastqc_total_sequences')['value'] == 200
    assert one(doc, 'fastqc_overrepresented_count')['value'] == 4
    assert one(doc, 'fastqc_kmer_scaled_count')['value'] == 15
    assert not cells(doc, 'fastqc_base_quality_mean')
    assert any(r['required_data'] == 'full_fastqc_data' for r in doc['requirements'])
    assert any(l['value'] == 'é_R1.fastq' for l in doc['labels'])
    loc = one(doc, 'fastqc_total_sequences')['locator']
    assert b'Total Sequences' in raw[loc['byte_start']:loc['byte_end']]
    assert doc['categories'][0]['native_token'] == '[OK]'
    assert doc['categories'][0]['value'] == 'pass'


def test_zip_multiple_native_data_members_and_exact_logical_locations():
    source = (FIXTURES / 'fastqc_all_modules.txt').read_bytes()
    raw = archive([('a/fastqc_report.html', b'<html>retained repeated representation</html>'), ('a/fastqc_data.txt', source),
                   ('a/Images/plot.png', b'PNG'), ('b/fastqc_data.txt', source)])
    doc = parse(raw, parse_fastqc_zip, 'fastqc_zip_0_12_1')
    assert len(cells(doc, 'fastqc_total_sequences')) == 2
    assert [c['locator']['member'] for c in cells(doc, 'fastqc_total_sequences')] == ['a/fastqc_data.txt', 'b/fastqc_data.txt']
    assert [p['population_ordinal'] for p in doc['populations'] if p['section_key'] == 'fastqc_basic_statistics'] == [0, 12]
    assert any(r['native_name'] == 'a/fastqc_report.html' for r in doc['raw_blocks'])
    for cell in doc['cells']:
        loc = cell['locator']; assert source[loc['byte_start']:loc['byte_end']]


@pytest.mark.parametrize('bad_name', ['../fastqc_data.txt', '/fastqc_data.txt', 'x/../fastqc_data.txt', 'C:/fastqc_data.txt', 'x\\fastqc_data.txt'])
def test_zip_path_traversal_is_never_extracted_or_parsed(bad_name, monkeypatch):
    monkeypatch.setattr(zipfile.ZipFile, 'extract', lambda *args, **kwargs: pytest.fail('archive extraction'))
    monkeypatch.setattr(zipfile.ZipFile, 'extractall', lambda *args, **kwargs: pytest.fail('archive extraction'))
    body = (FIXTURES / 'fastqc_all_modules.txt').read_bytes()
    doc = parse(archive([(bad_name, body), ('good/fastqc_data.txt', body)]), parse_fastqc_zip, 'fastqc_zip_0_12_1')
    assert len(cells(doc, 'fastqc_total_sequences')) == 1
    assert doc['parse_scope'] == 'partial'


def test_zip_duplicate_member_name_is_ambiguous_not_first_match():
    body = (FIXTURES / 'fastqc_all_modules.txt').read_bytes()
    with pytest.warns(UserWarning): raw = archive([('x/fastqc_data.txt', body), ('x/fastqc_data.txt', body)])
    doc = parse(raw, parse_fastqc_zip, 'fastqc_zip_0_12_1')
    assert not doc['cells']
    assert any(r['code'] == 'artifact_collision' for r in doc['diagnostics'])


def test_zip_html_fallback_and_corrupt_archive():
    html = (FIXTURES / 'fastqc_tables_graph.html').read_bytes()
    doc = parse(archive([('x/fastqc_report.html', html)]), parse_fastqc_zip, 'fastqc_zip_0_12_1')
    assert one(doc, 'fastqc_total_sequences')['value'] == 200
    bad = parse(b'PK\x03\x04bad', parse_fastqc_zip, 'fastqc_zip_0_12_1')
    assert bad['parse_scope'] == 'malformed' and not bad['cells']


def test_trim_reports_separate_first_and_second_mates_and_cutadapt():
    first = parse((FIXTURES / 'trim_first.txt').read_bytes(), parse_trim_galore_report, 'trim_galore_report_0_6_10', '0.6.10')
    second = parse((FIXTURES / 'trim_second.txt').read_bytes(), parse_trim_galore_report, 'trim_galore_report_0_6_10', '0.6.10')
    assert one(first, 'trim_processed_count')['value'] == 8
    assert not cells(first, 'trim_validation_pair_count')
    assert one(second, 'trim_validation_pair_count')['value'] == 8
    removed = one(second, 'trim_removed_pair_count')
    assert removed['value'] == 2 and removed['unit'] == 'pairs'
    assert 'trim_pair_counter_mixed' in removed['diagnostic_codes']
    assert one(second, 'trim_removed_pair_percent')['native_token'] == '25.00'
    assert not second['native_lineage']  # Mixed counter cannot invent surviving pairs.
    assert not cells(second, 'trim_removed_n_count')
    assert not cells(second, 'trim_removed_long_count')
    assert any(r['code'] == 'unsupported_report_section' for r in second['requirements'])
    block = next(r for r in second['raw_blocks'] if r['native_name'] == 'cutadapt_embedded')
    raw = (FIXTURES / 'trim_second.txt').read_bytes(); loc = block['locator']
    retained = raw[loc['byte_start']:loc['byte_end']]
    assert b'=== Summary ===' in retained and b'Reads with adapters: 4' in retained
    assert not any(c['metric'].startswith('cutadapt') for c in second['cells'])
    assert [(r['axis']['label'], r['value']) for r in cells(first, 'trim_adapter_detection_count')] == [('Illumina', 12), ('Nextera', 2)]
    assert any(c['value'] == .1 and c['meaning'] == 'native_configuration' for c in cells(first, 'trim_native_option'))


def test_trim_single_native_percent_and_empty_na():
    raw = (FIXTURES / 'trim_single.txt').read_bytes()
    doc = parse(raw, parse_trim_galore_report, 'trim_galore_report_0_6_10', '0.6.10')
    assert [one(doc, f'trim_removed_{key}_count')['value'] for key in ('short', 'n', 'long')] == [2, 1, 1]
    assert one(doc, 'trim_removed_short_percent')['native_token'] == '25.0'
    empty = raw.replace(b'8 sequences processed', b'0 sequences processed').replace(b'2 (25.0%)', b'0 (N/A%)')
    parsed = parse(empty, parse_trim_galore_report, 'trim_galore_report_0_6_10', '0.6.10')
    assert one(parsed, 'trim_removed_short_count')['value'] == 0
    assert one(parsed, 'trim_removed_short_percent')['value'] is None
    assert one(parsed, 'trim_removed_short_percent')['native_token'] == 'N/A'


def test_fastq_pair_four_read_counts_no_invented_pair_or_version():
    doc = parse((FIXTURES / 'pair_stderr.txt').read_bytes(), parse_fastq_pair_stderr, 'fastq_pair_stderr_0_3', '0.3')
    assert [c['value'] for c in doc['cells']] == [6, 6, 2, 1]
    assert {c['unit'] for c in doc['cells']} == {'reads'}
    assert len(doc['populations']) == 4 and not doc['native_lineage']
    assert all(p['kind'] != 'verified_read_pairs' for p in doc['populations'])
    assert any(d['code'] == 'producer_version_unproven' for d in doc['diagnostics'])


@pytest.mark.parametrize('token', ['-1', '2147483648', 'nonsense'])
def test_fastq_pair_invalid_native_counter_retains_siblings(token):
    raw = f'Left paired: {token}\t\tRight paired: 6\nLeft single: 2\t\tRight single: 1\n'.encode()
    doc = parse(raw, parse_fastq_pair_stderr, 'fastq_pair_stderr_0_3', '0.3')
    assert one(doc, 'fastq_pair_left_paired')['value'] is None
    assert one(doc, 'fastq_pair_right_single')['value'] == 1


def test_fastq_pair_unequal_counts_retain_facts_with_diagnostic():
    raw = b'Left paired: 7\t\tRight paired: 6\nLeft single: 2\t\tRight single: 1\n'
    doc = parse(raw, parse_fastq_pair_stderr, 'fastq_pair_stderr_0_3', '0.3')
    assert [c['value'] for c in doc['cells']] == [7, 6, 2, 1]
    assert any(d['code'] == 'count_inconsistent' for d in doc['diagnostics'])


def test_retained_source_executed_hostile_rows_and_zero_fallback():
    doc = parse_hostile(hostile(), identity='source_executed_synthetic')
    assert [c['value'] for c in doc['cells']] == [8, 6, 2, .25, 0, 0, 0, 0.0]
    assert [p['population_ordinal'] for p in doc['populations']] == [0, 0, 0, 1, 1, 1]
    assert len(doc['native_lineage']) == 2
    assert all(e['task_stage_ref'] is None and e['scope'] == 'artifact_local' for e in doc['native_lineage'])
    assert 'native_fallback_value' in cells(doc, 'hostile_removed_proportion')[1]['diagnostic_codes']
    assert all(c['unit'] == 'reads' for c in cells(doc, 'hostile_reads_in'))


def test_hostile_bounded_bad_row_and_partial_tail_keep_intact_siblings():
    row = json.loads(hostile())[0]
    raw = b'[' + json.dumps(row).encode() + b', {"reads_in": BROKEN}, ' + json.dumps(row).encode() + b']'
    doc = parse_hostile(raw)
    assert [c['value'] for c in cells(doc, 'hostile_reads_in')] == [8, 8]
    assert [p['population_ordinal'] for p in doc['populations'] if p['population_key'] == 'hostile_in'] == [0, 2]
    partial = parse_hostile(b'[' + json.dumps(row).encode() + b', {"reads_in":', scope='partial')
    assert one(partial, 'hostile_reads_in')['value'] == 8
    assert one(partial, 'hostile_reads_in')['state'] == 'partial'
    assert partial['parse_scope'] == 'partial'


@pytest.mark.parametrize('value', [True, '8', -1, 1.5, None])
def test_hostile_count_json_type_and_domain_are_not_coerced(value):
    row = json.loads(hostile())[0]; row['reads_in'] = value
    doc = parse_hostile(hostile([row]))
    assert one(doc, 'hostile_reads_in')['value'] is None
    assert one(doc, 'hostile_reads_out')['value'] == 6


def test_hostile_duplicate_keys_nonfinite_and_inconsistent_counts():
    raw = b'[{"version":"1.1.0","reads_in":8,"reads_in":9,"reads_out":6,"reads_removed":2,"reads_removed_proportion":NaN}]'
    doc = parse_hostile(raw)
    assert one(doc, 'hostile_reads_in')['state'] == 'malformed'
    assert one(doc, 'hostile_reads_out')['value'] == 6
    assert one(doc, 'hostile_removed_proportion')['value'] is None
    row = json.loads(hostile())[0]; row['reads_out'] = 9
    doc = parse_hostile(hostile([row]))
    assert one(doc, 'hostile_reads_out')['value'] == 9
    assert any(d['code'] == 'count_inconsistent' for d in doc['diagnostics'])


def test_hostile_missing_unrelated_metadata_preserves_native_counts():
    doc = parse_hostile(hostile([{'version': '1.1.0', 'reads_in': 8, 'reads_out': 6,
                                 'reads_removed': 2, 'reads_removed_proportion': .25}]))
    assert [c['value'] for c in doc['cells']] == [8, 6, 2, .25]
    assert len(doc['native_lineage']) == 1


def test_overwritten_probe_stub_does_not_become_scientific_counts():
    doc = parse_hostile((FIXTURES / 'hostile_overwritten_stub.json').read_bytes(), identity='source_executed_synthetic')
    assert all(c['value'] is None for c in doc['cells'])
    assert not doc['native_lineage']
    assert any(b['kind'] == 'record' for b in doc['raw_blocks'])


@pytest.mark.parametrize('parser,fmt,version,raw', [
    (parse_fastqc_data, 'fastqc_data_0_12_1', '0.12.1', b'##FastQC\t0.11.9\n>>Basic Statistics\tpass\n#Measure\tValue\nTotal Sequences\t8\n>>END_MODULE\n'),
    (parse_hostile_json, 'hostile_json_1_1_0', '1.1.0', b'[{"version":"2.0.2","reads_in":8,"reads_out":6,"reads_removed":2,"reads_removed_proportion":0.25}]'),
])
def test_explicit_native_version_mismatch_is_not_supported_execution(parser, fmt, version, raw):
    doc = parse(raw, parser, fmt, version)
    assert any(d['code'] == 'unsupported_version' for d in doc['diagnostics'])
    assert all(c['state'] == 'incompatible' for c in doc['cells'])
    assert any(l['kind'] == 'producer_version' for l in doc['labels'])


@pytest.mark.parametrize('raw', [b'\xff', b'', b'{"not_an_array":1}', b'[', b'[{}] trailing'])
def test_hostile_malformed_bytes_are_local_failures(raw):
    result = parse_hostile(raw)
    assert result['parse_scope'] in ('partial', 'malformed')
    assert result['diagnostics']


def test_global_argument_and_hash_errors_are_contract_errors():
    raw = b'##FastQC\t0.12.1\n'
    ctx = context(raw, 'fastqc_data_0_12_1')
    with pytest.raises(FastqUtilsContractError): parse_fastqc_data('not bytes', context=ctx)
    wrong = deepcopy(ctx); wrong['content']['byte_count'] += 1
    with pytest.raises(FastqUtilsContractError): parse_fastqc_data(raw, context=wrong)
    wrong = deepcopy(ctx); wrong['content']['sha256'] = '0' * 64
    with pytest.raises(FastqUtilsContractError): parse_fastqc_data(raw, context=wrong)
    wrong = deepcopy(ctx); wrong['declared_format'] = 'unknown'
    with pytest.raises(FastqUtilsContractError): parse_fastqc_data(raw, context=wrong)


def test_hostile_native_column_order_is_preserved():
    raw = b'[{"version":"1.1.0","reads_out":6,"reads_in":8,"reads_removed_proportion":0.25,"reads_removed":2}]'
    doc = parse_hostile(raw)
    assert [c['metric'] for c in doc['cells']] == ['hostile_reads_out', 'hostile_reads_in', 'hostile_removed_proportion', 'hostile_reads_removed']
    assert len(doc['native_lineage']) == 1


@pytest.mark.parametrize('fragment', [b'"version":"\\ud800"', b'"\\ud800":1', b'"aligner":"\\ud800"'])
def test_native_json_invalid_unicode_never_causes_global_contract_failure(fragment):
    raw = b'[{' + fragment + b',"reads_in":8,"reads_out":6,"reads_removed":2,"reads_removed_proportion":0.25}]'
    doc = parse_hostile(raw)
    assert one(doc, 'hostile_reads_in')['value'] == 8
    assert doc['diagnostics']


def test_empty_module_name_is_local_native_failure():
    doc = parse(b'##FastQC\t0.12.1\n>>\tpass\n>>END_MODULE\n')
    assert not doc['categories'] and doc['diagnostics']


def test_zip_decompression_error_is_local_with_good_sibling_retained():
    source = (FIXTURES / 'fastqc_all_modules.txt').read_bytes()
    raw = bytearray(archive([('broken/fastqc_data.txt', source), ('good/fastqc_data.txt', source)]))
    with zipfile.ZipFile(io.BytesIO(raw)) as reader:
        first = reader.infolist()[0]
        start = first.header_offset + 30 + len(first.filename.encode()) + len(first.extra)
        raw[start:start+min(12, first.compress_size)] = b'\xff' * min(12, first.compress_size)
    doc = parse(bytes(raw), parse_fastqc_zip, 'fastqc_zip_0_12_1')
    assert one(doc, 'fastqc_total_sequences')['value'] == 200
    assert doc['parse_scope'] == 'partial'
