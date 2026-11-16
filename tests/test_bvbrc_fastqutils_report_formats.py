"""Native report grammar checks. Fixtures are explicitly synthetic, not live jobs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError, validate_native_document
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_fastqutils_fastqc_reader import parse_fastqc_data
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_fastqutils_hostile_reader import parse_hostile_json

FIXTURES = Path(__file__).resolve().parents[1] / 'gene_annotation_episode/episodic_workflow/root/tests/fixtures/bvbrc_fastqutils/reports'


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


