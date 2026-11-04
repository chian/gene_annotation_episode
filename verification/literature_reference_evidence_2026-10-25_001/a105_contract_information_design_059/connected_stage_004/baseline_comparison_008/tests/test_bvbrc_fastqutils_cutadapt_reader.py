"""Cutadapt 4.9 actual-producer oracles and separately synthetic corruptions.

Native fixtures are immutable evidence in the assigned parser workload, not
remote BV-BRC artifacts. Their JSON reports are verification oracles only.
"""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, json_sha256, validate_native_document,
)
from gene_annotation_episode.bvbrc_fastqutils_cutadapt_reader import append_cutadapt_report
from gene_annotation_episode.bvbrc_fastqutils_cutadapt_specs import CUTADAPT_METRICS
from gene_annotation_episode.bvbrc_fastqutils_fastqc_reader import _Report
from gene_annotation_episode.bvbrc_fastqutils_trim_reader import parse_trim_galore_report

WORK = Path(__file__).resolve().parents[2]
INITIAL = WORK / 'native_examples_001'
ADDITIONAL = WORK / 'parser_205/native_examples_001'
MORE = WORK / 'parser_205/native_examples_002'
WARNINGS = WORK / 'parser_205/native_examples_003'
CASES = [p for base in (INITIAL, ADDITIONAL, MORE, WARNINGS) for p in sorted(base.iterdir())
         if p.is_dir() and (p / 'native.json').is_file()]


def context(raw, *, scope='complete', identity='source_executed_synthetic', outer=False):
    return dict(analysis_id='cutadapt_test', document_id='report', task_ref='task:synthetic',
        content=dict(source_ref='source:synthetic', artifact_field='artifact_ref',
            artifact_ref='content:synthetic', sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw)),
        native_name=None, declared_format='trim_galore_report_0_6_10' if outer else 'native_text',
        producer_version='0.6.10' if outer else '4.9',
        transfer_scope=scope, identity=identity)


def parse(raw, *, start=0, end=None, scope='complete', identity='source_executed_synthetic'):
    report = _Report(raw, context(raw, scope=scope, identity=identity), 'native_text', 'Cutadapt')
    append_cutadapt_report(report, raw, start=start, end=len(raw) if end is None else end)
    doc = report.finish()
    validate_native_document(doc)
    return doc


def native(case='cutadapt_single', base=INITIAL):
    return (base / case / 'stdout.log').read_bytes()


def cells(doc, metric, *, section=None):
    return [c for c in doc['cells'] if c['metric'] == metric and (section is None or
        (c['section_key'], c['section_ordinal']) == (section['key'], section['ordinal']))]


def values(doc, metric, *, section=None):
    return [c['value'] for c in cells(doc, metric, section=section)]


def total(doc, metric):
    rows = [c for c in cells(doc, metric) if c['axis']['kind'] == 'none']
    assert len(rows) == 1
    return rows[0]


def sections(doc, key, within=None):
    return [s for s in doc['sections'] if s['key'] == key and (within is None or
        within['locator']['byte_start'] <= s['locator']['byte_start'] < within['locator']['byte_end'])]


@pytest.mark.parametrize('case', CASES, ids=lambda p: p.name)
def test_actual_native_summary_and_table_oracles(case):
    raw = (case / 'stdout.log').read_bytes()
    expected = json.loads((case / 'native.json').read_text())
    receipt = json.loads((case / 'receipt.json').read_text())
    assert receipt['exit_code'] == 0 and receipt['native_executable_run'] and not receipt['BV_BRC_service_run']
    for name, binding in receipt['files'].items():
        retained = (case / name).read_bytes()
        assert len(retained) == binding['byte_count']
        assert hashlib.sha256(retained).hexdigest() == binding['sha256']
    doc = parse(raw)
    assert doc['parse_scope'] == 'complete'
    assert all(c['state'] == 'available' for c in doc['cells'])
    assert {d['code'] for d in doc['diagnostics']} <= {'native_report_local_lineage'}
    assert doc['artifact']['producer_name'] == 'Cutadapt'
    assert doc['artifact']['producer_version'] == '4.9'
    assert doc['artifact']['declared_format'] == 'native_text'  # Direct helper test, no standalone dispatch claim.
    assert [l['value'] for l in doc['labels'] if l['kind'] == 'producer_version'] == ['4.9']
    unit = 'pairs' if expected['input']['paired'] else 'reads'
    assert total(doc, 'cutadapt_processed_count')['unit'] == unit
    assert values(doc, 'cutadapt_processed_count') == [expected['read_counts']['input']]
    if expected['read_counts']['input'] == 0:
        assert len(doc['cells']) == 1 and not doc['native_lineage']
        assert total(doc, 'cutadapt_processed_count')['native_token'] == 'No reads processed!'
        return  # JSON's omitted text counters must NOT populate this sheet.
    assert total(doc, 'cutadapt_written_count')['value'] == expected['read_counts']['output']
    assert total(doc, 'cutadapt_written_count')['unit'] == unit
    assert values(doc, 'cutadapt_adapter_containing_reads') == [expected['read_counts'][name]
        for name in ('read1_with_adapter', 'read2_with_adapter') if expected['read_counts'][name] is not None]
    reverse = expected['read_counts']['reverse_complemented']
    assert values(doc, 'cutadapt_reverse_complemented_count') == ([] if reverse is None else [reverse])
    for metric, prefix in [('cutadapt_processed_bases', 'input'), ('cutadapt_written_bases', 'output'),
                           ('cutadapt_quality_trimmed_bases', 'quality_trimmed'),
                           ('cutadapt_poly_a_trimmed_bases', 'poly_a_trimmed')]:
        keys = [prefix] + ([prefix + '_read1', prefix + '_read2'] if unit == 'pairs' else [])
        numbers = [expected['basepair_counts'][k] for k in keys if expected['basepair_counts'][k] is not None]
        assert values(doc, metric) == numbers
    assert values(doc, 'cutadapt_filtered_count') == [n for n in expected['read_counts']['filtered'].values() if n is not None]
    adapters = expected['adapters_read1'] + (expected['adapters_read2'] or [])
    adapter_sections = sections(doc, 'cutadapt_adapter')
    assert len(adapter_sections) == len(adapters)
    for section, adapter in zip(adapter_sections, adapters):
        labels = [l for l in doc['labels'] if l['id'] in section['label_refs']]
        assert [l['value'] for l in labels if l['locator']['field'] == 'Adapter name'] == [adapter['name']]
        native_ends = [e for e in (adapter['five_prime_end'], adapter['three_prime_end']) if e is not None]
        assert values(doc, 'cutadapt_adapter_length', section=section) == (
            [len(e['sequence']) for e in native_ends] if adapter['linked'] else [len(native_ends[0]['sequence'])])
        if adapter['linked']:
            assert values(doc, 'cutadapt_adapter_trimmed_count', section=section) == [e['matches'] for e in native_ends]
        elif len(native_ends) == 2:
            assert values(doc, 'cutadapt_adapter_trimmed_count', section=section) == [adapter['total_matches'], *[e['matches'] for e in native_ends]]
        else:
            assert values(doc, 'cutadapt_adapter_trimmed_count', section=section) == [adapter['total_matches']]
        histograms = sections(doc, 'cutadapt_adapter_histogram', within=section)
        if adapter['total_matches'] == 0:
            assert not histograms
            continue
        assert len(histograms) == len(native_ends)
        hist_pops = []
        for histogram, native_end in zip(histograms, native_ends):
            rows = defaultdict(list)
            for c in doc['cells']:
                if c['id'] in histogram['cell_refs']:
                    rows[c['locator']['row_ordinal']].append(c)
            assert len(rows) == len(native_end['trimmed_lengths'])
            for actual, wanted in zip(rows.values(), native_end['trimmed_lengths']):
                by_metric = defaultdict(list)
                for cell in actual:
                    by_metric[cell['metric']].append(cell)
                assert [c['value'] for c in by_metric['cutadapt_histogram_length']] == [wanted['len']]
                assert [c['value'] for c in by_metric['cutadapt_histogram_count']] == [sum(wanted['counts'])]
                assert [c['value'] for c in by_metric['cutadapt_histogram_expected_count']] == [wanted['expect']]
                bins = by_metric['cutadapt_histogram_error_count']
                assert [c['value'] for c in bins] == wanted['counts']
                assert [c['axis']['lower'] for c in bins] == list(range(len(wanted['counts'])))
                assert all(c['axis']['kind'] == 'edit_error_count' for c in bins)
                # All fixtures have plain A/C/G/T adapter sequences, so the
                # native source's effective length equals this sequence length.
                nominal = int(native_end['error_rate'] * min(wanted['len'], len(native_end['sequence'])))
                assert [c['value'] for c in by_metric['cutadapt_histogram_max_errors']] == [nominal]
                assert len({c['population_ref'] for c in actual}) == 1
                assert len({(c['locator']['byte_start'], c['locator']['byte_end']) for c in actual}) == 1
                hist_pops.append(actual[0]['population_ref'])
            assert len(set(hist_pops)) <= len(native_ends)
        adjacent = sections(doc, 'cutadapt_adjacent_bases', within=section)
        if adjacent:
            counts = native_ends[-1]['adjacent_bases']
            denominator = sum(counts.values())
            assert values(doc, 'cutadapt_adjacent_base_percent', section=adjacent[0]) == [
                float(f'{100 * counts[b] / denominator:.1f}') for b in ('A', 'C', 'G', 'T', '')]
    polys = sections(doc, 'cutadapt_poly_a')
    expected_polys = [expected[k] for k in ('poly_a_trimmed_read1', 'poly_a_trimmed_read2') if expected[k] is not None]
    assert len(polys) == len(expected_polys)
    for section, table in zip(polys, expected_polys):
        assert values(doc, 'cutadapt_poly_a_length', section=section) == [r['len'] for r in table]
        assert values(doc, 'cutadapt_poly_a_count', section=section) == [r['count'] for r in table]
    populations = {p['id']: p for p in doc['populations']}
    input_pop = populations[total(doc, 'cutadapt_processed_count')['population_ref']]
    for pop in populations.values():
        assert pop['association_ref'] is None and pop['scope'] == 'complete'
        if pop['population_key'] in ('cutadapt_adapter_events', 'cutadapt_adapter_reads', 'cutadapt_poly_a_events', 'cutadapt_filtered'):
            assert pop['parent_population_refs'] == [input_pop['id']]
    for cell in doc['cells']:
        loc = cell['locator']
        assert raw[loc['byte_start']:loc['byte_end']]
        assert cell['association_ref'] is None
    assert len(doc['native_lineage']) == (4 if unit == 'pairs' else 2)
    for edge in doc['native_lineage']:
        assert edge['scope'] == 'artifact_local' and edge['task_stage_ref'] is None


def test_all_registered_native_fields_have_filled_actual_examples():
    observed = {c['metric'] for case in CASES for c in parse((case / 'stdout.log').read_bytes())['cells']}
    assert observed == set(CUTADAPT_METRICS)


def test_genuine_trim_galore_retains_cutadapt_before_its_own_filter():
    case = INITIAL / 'trimgalore_single'
    raw = (case / 'synthetic.fastq_trimming_report.txt').read_bytes()
    doc = parse_trim_galore_report(raw, context=context(raw, outer=True))
    assert total(doc, 'cutadapt_written_count')['value'] == 4
    assert total(doc, 'cutadapt_written_bases')['value'] == 28
    fastq = (case / 'synthetic_trimmed.fq').read_text().splitlines()
    assert len(fastq) // 4 == 3
    assert sum(map(len, fastq[1::4])) == 24
    assert values(doc, 'trim_removed_short_count') == [1]
    assert all(p['population_key'].startswith('cutadapt') for p in doc['populations']
               if any(p['id'] in (e['before_population_ref'], e['after_population_ref']) for e in doc['native_lineage']))


def test_no_match_omits_histogram_and_configuration_without_fabricated_zero_bins():
    doc = parse(native('no_matches', ADDITIONAL))
    assert values(doc, 'cutadapt_adapter_trimmed_count') == [0]
    assert not cells(doc, 'cutadapt_histogram_count')
    assert not cells(doc, 'cutadapt_minimum_overlap')
    assert not cells(doc, 'cutadapt_adjacent_base_percent')


@pytest.mark.parametrize('field', ['discarded as trimmed', 'discarded as untrimmed'])
@pytest.mark.parametrize('case,unit', [('cutadapt_single', 'reads'), ('cutadapt_paired', 'pairs')])
def test_source_defined_discard_filter_labels_preserve_native_unit(field, case, unit):
    # These are deliberate source-grammar fixtures. The actual discard-option
    # executions omit the filter counter in both text and JSON.
    prefix = b'Reads' if unit == 'reads' else b'Pairs'
    marker = prefix + b' written (passing filters):'
    row = b'== Read fate breakdown ==\n' + prefix + b' ' + field.encode() + b': 0 (0.0%)\n'
    raw = native(case).replace(marker, row + marker)
    doc = parse(raw, identity='handcrafted_synthetic')
    counter = cells(doc, 'cutadapt_filtered_count')[0]
    assert counter['value'] == 0 and counter['unit'] == unit
    assert counter['axis']['label'] == prefix.decode() + ' ' + field
    assert counter['state'] == 'available'


def test_repeated_events_and_indel_error_index_are_not_unique_read_counts_or_nominal_bounds():
    repeated = parse(native('repeated', ADDITIONAL))
    assert values(repeated, 'cutadapt_processed_count') == [2]
    assert values(repeated, 'cutadapt_adapter_trimmed_count') == [5]
    assert values(repeated, 'cutadapt_histogram_count') == [5]
    indel = parse(native('indel_beyond_nominal', MORE))
    assert values(indel, 'cutadapt_histogram_length') == [9, 10]
    assert values(indel, 'cutadapt_histogram_max_errors') == [0, 1]
    assert [(c['axis']['lower'], c['value']) for c in cells(indel, 'cutadapt_histogram_error_count')] == [(0, 0), (1, 1), (0, 1)]
    assert not any(d['code'] == 'count_inconsistent' for d in indel['diagnostics'])


def test_shared_anywhere_configuration_and_distinct_endpoint_populations():
    doc = parse(native('anywhere', ADDITIONAL))
    errors = sections(doc, 'cutadapt_adapter_errors')
    assert len(errors) == 2 and errors[0]['locator']['byte_start'] == errors[1]['locator']['byte_start']
    allowed = cells(doc, 'cutadapt_allowed_errors')
    assert len(allowed) == 2 and len({c['population_ref'] for c in allowed}) == 2
    assert allowed[0]['locator']['byte_start'] == allowed[1]['locator']['byte_start']
    assert values(doc, 'cutadapt_adapter_trimmed_count') == [3, 1, 2]
    assert len({c['population_ref'] for c in cells(doc, 'cutadapt_adapter_trimmed_count')}) == 3


@pytest.mark.parametrize('case', ['warning_poly_a', 'warning_paired_poly_a'])
def test_native_global_warning_after_poly_a_is_text_not_numeric_data(case):
    raw = native(case, WARNINGS)
    doc = parse(raw)
    assert doc['parse_scope'] == 'complete'
    assert all('WARNING' not in (c['native_token'] or '') for c in doc['cells'])
    global_warning = next(l for l in doc['labels'] if 'One or more of your adapter sequences' in l['value'])
    assert global_warning['section_key'] == 'cutadapt_poly_a'
    location = global_warning['locator']
    assert global_warning['value'].encode() in raw[location['byte_start']:location['byte_end']]
    assert values(doc, 'cutadapt_poly_a_count') == ([20] if case == 'warning_poly_a' else [20, 20])


def test_repeated_adapter_names_preserve_occurrence_and_byte_containment():
    doc = parse(native('repeated_names', ADDITIONAL))
    adapters = sections(doc, 'cutadapt_adapter')
    assert [s['ordinal'] for s in adapters] == [0, 1]
    assert len({c['population_ref'] for c in cells(doc, 'cutadapt_adapter_trimmed_count')}) == 2
    assert [l['value'] for l in doc['labels'] if l['locator']['field'] == 'Sequence'] == ['AGATCG', 'GATTAC']
    assert all(len(sections(doc, 'cutadapt_adapter_histogram', within=s)) == 1 for s in adapters)


def test_repeated_invocations_never_cross_lineage_even_with_identical_names():
    part = native()
    raw = part + part
    report = _Report(raw, context(raw, identity='handcrafted_synthetic'), 'native_text', 'Cutadapt')
    for begin, end in ((0, len(part)), (len(part), len(raw))):
        append_cutadapt_report(report, raw, start=begin, end=end)
    doc = report.finish()
    assert [p['population_ordinal'] for p in doc['populations'] if p['population_key'] == 'cutadapt_input_reads'] == [0, 1]
    populations = {p['id']: p for p in doc['populations']}
    for edge in doc['native_lineage']:
        assert populations[edge['before_population_ref']]['section_ordinal'] == populations[edge['after_population_ref']]['section_ordinal']
    assert len(doc['native_lineage']) == 4


@pytest.mark.parametrize('mutation,code', [
    (lambda b: b.replace(b'This is cutadapt 4.9', b'This is cutadapt 4.8'), 'unsupported_version'),
    (lambda b: b.split(b'\n', 1)[1], 'producer_version_unproven'),
])
def test_unverified_version_retains_bytes_without_native_measurements(mutation, code):
    raw = mutation(native())
    doc = parse(raw, identity='handcrafted_synthetic')
    assert not doc['cells'] and not doc['populations']
    assert any(r['code'] == code for r in doc['requirements'])
    assert any(b['parse_status'] == 'unsupported' and b['locator']['byte_start'] == 0
               and b['locator']['byte_end'] == len(raw) for b in doc['raw_blocks'])
    assert doc['artifact']['producer_version'] == '4.9'


@pytest.mark.parametrize('token', ['nonsense', '-1', '1.5', '1,23', '9' * 5000])
def test_malformed_count_tokens_preserve_independent_fields(token):
    raw = native().replace(b'Total reads processed:                       4', f'Total reads processed: {token}'.encode())
    doc = parse(raw, identity='handcrafted_synthetic')
    cell = total(doc, 'cutadapt_processed_count')
    assert cell['state'] == 'malformed' and cell['native_token'] == token and cell['value'] is None
    assert total(doc, 'cutadapt_written_bases')['value'] == 28
    assert total(doc, 'cutadapt_written_bases')['state'] == 'available'
    assert values(doc, 'cutadapt_histogram_count') == [2]


def test_native_grouped_count_token_preserves_display_and_numeric_value():
    raw = native().replace(b'Total reads processed:                       4', b'Total reads processed: 1,234')
    cell = total(parse(raw, identity='handcrafted_synthetic'), 'cutadapt_processed_count')
    assert (cell['value'], cell['native_token']) == (1234, '1,234')


@pytest.mark.parametrize('other', [4, 9])
def test_duplicate_summary_counts_are_ambiguous_even_when_equal(other):
    raw = native().replace(b'Total reads processed:                       4\n',
        f'Total reads processed: 4\nTotal reads processed: {other}\n'.encode())
    doc = parse(raw, identity='handcrafted_synthetic')
    actual = cells(doc, 'cutadapt_processed_count')
    assert len(actual) == 2 and all(c['state'] == 'incompatible' for c in actual)
    assert all('selection_ambiguous' in c['diagnostic_codes'] for c in actual)
    assert total(doc, 'cutadapt_processed_bases')['value'] == 58
    assert len(doc['native_lineage']) == 1  # The independent base relation remains.


def test_competing_summary_sections_do_not_choose_origin_or_leave_stale_lineage_refs():
    raw = native()
    begin, end = raw.index(b'=== Summary ==='), raw.index(b'=== Adapter 1 ===')
    raw = raw[:end] + raw[begin:end] + raw[end:]
    doc = parse(raw, identity='handcrafted_synthetic')
    assert len(cells(doc, 'cutadapt_processed_count')) == 2
    assert all(c['state'] == 'incompatible' for c in cells(doc, 'cutadapt_processed_count'))
    assert not doc['native_lineage']
    assert not any(d['code'] == 'native_report_local_lineage' for d in doc['diagnostics'])
    assert values(doc, 'cutadapt_adapter_trimmed_count') == [2]
    assert all(not p['parent_population_refs'] for p in doc['populations'] if p['population_key'] == 'cutadapt_adapter_events')


@pytest.mark.parametrize('old,new', [(b'Processing single-end', b'Processing paired-end'),
                                    (b'Reads written (passing filters)', b'Pairs written (passing filters)')])
def test_conflicting_native_modes_have_no_fabricated_before_after_relation(old, new):
    doc = parse(native().replace(old, new), identity='handcrafted_synthetic')
    assert any(d['code'] == 'native_header_conflict' for d in doc['diagnostics'])
    assert not doc['native_lineage']
    assert total(doc, 'cutadapt_processed_count')['native_token'] == '4'
    assert total(doc, 'cutadapt_processed_count')['state'] == 'incompatible'
    assert values(doc, 'cutadapt_histogram_count') == [2]


def test_conflicting_percentage_is_retained_with_exact_count_and_diagnostic():
    doc = parse(native().replace(b'2 (50.0%)', b'2 (12.3%)'), identity='handcrafted_synthetic')
    assert values(doc, 'cutadapt_adapter_containing_reads') == [2]
    percentage = next(c for c in cells(doc, 'cutadapt_reported_percent') if c['axis']['label'] == 'Reads with adapters')
    assert percentage['value'] == 12.3 and percentage['native_token'] == '12.3'
    assert 'count_inconsistent' in percentage['diagnostic_codes']
    assert 'count_inconsistent' in cells(doc, 'cutadapt_adapter_containing_reads')[0]['diagnostic_codes']


def test_duplicate_percentage_rows_are_ambiguous_without_choosing_first():
    raw = native().replace(b'Reads with adapters:                         2 (50.0%)\n',
        b'Reads with adapters: 2 (50.0%)\nReads with adapters: 2 (12.3%)\n')
    doc = parse(raw, identity='handcrafted_synthetic')
    percentages = [c for c in cells(doc, 'cutadapt_reported_percent') if c['axis']['label'] == 'Reads with adapters']
    assert [c['native_token'] for c in percentages] == ['50.0', '12.3']
    assert all(c['state'] == 'incompatible' and 'selection_ambiguous' in c['diagnostic_codes'] for c in percentages)


def test_truncated_histogram_retains_prefix_and_marks_only_its_population_partial():
    raw = native('front', ADDITIONAL).replace(b'8\t1\t0.0\t1\t1\n', b'')
    doc = parse(raw, identity='handcrafted_synthetic')
    assert values(doc, 'cutadapt_histogram_count') == [1]
    assert cells(doc, 'cutadapt_histogram_count')[0]['state'] == 'partial'
    assert total(doc, 'cutadapt_processed_bases')['state'] == 'available'
    assert any(d['code'] == 'count_inconsistent' for d in doc['diagnostics'])


def test_bounded_malformed_adapter_table_preserves_later_adapter():
    raw = native('repeated_names', ADDITIONAL).replace(b'6\t1\t0.0\t0\t1', b'6\tBAD\t0.0\t0\t1', 1)
    doc = parse(raw, identity='handcrafted_synthetic')
    rows = cells(doc, 'cutadapt_histogram_count')
    assert [c['value'] for c in rows] == [None, 1]
    assert [c['state'] for c in rows] == ['malformed', 'available']


def test_inconsistent_bins_remain_actual_numbers_with_diagnostic():
    raw = native().replace(b'13\t2\t0.0\t1\t2', b'13\t2\t0.0\t1\t1')
    doc = parse(raw, identity='handcrafted_synthetic')
    assert values(doc, 'cutadapt_histogram_count') == [2]
    assert values(doc, 'cutadapt_histogram_error_count') == [1]
    assert any(d['code'] == 'count_inconsistent' for d in doc['diagnostics'])


@pytest.mark.parametrize('replacement', [b'13\t2', b'BAD\t2\t0.0\t1\t2', b'9' * 5000 + b'\t2\t0.0\t1\t2'])
def test_malformed_or_cutoff_histogram_row_has_typed_failure_and_no_crash(replacement):
    raw = native().replace(b'13\t2\t0.0\t1\t2', replacement)
    doc = parse(raw, identity='handcrafted_synthetic')
    assert doc['parse_scope'] == 'partial'
    assert total(doc, 'cutadapt_written_bases')['value'] == 28


def test_unknown_section_retains_full_bytes_and_valid_siblings():
    raw = native() + b'\n=== Future mode ===\nMystery quantity: 99\nall native data\n'
    doc = parse(raw, identity='handcrafted_synthetic')
    block = next(b for b in doc['raw_blocks'] if b['native_name'] == '=== Future mode ===' and b['parse_status'] == 'unsupported')
    loc = block['locator']
    assert raw[loc['byte_start']:loc['byte_end']].endswith(b'all native data\n')
    assert not any(c['value'] == 99 for c in doc['cells'])
    assert total(doc, 'cutadapt_written_bases')['state'] == 'available'


def test_missing_minimum_overlap_and_truncated_error_ranges_remain_local_failures():
    raw = native().replace(b'Minimum overlap: 3\n', b'').replace(b'10-13 bp: 1', b'10-13 bp:')
    doc = parse(raw, identity='handcrafted_synthetic')
    assert values(doc, 'cutadapt_allowed_errors') == [0]
    assert cells(doc, 'cutadapt_allowed_errors')[0]['state'] == 'partial'
    assert total(doc, 'cutadapt_written_bases')['state'] == 'available'


def test_original_byte_offsets_with_multibyte_prefix_and_crlf():
    prefix = 'Préfixe µ\r\n'.encode()
    report = native().replace(b'\n', b'\r\n')
    suffix = b'after report\r\n'
    raw = prefix + report + suffix
    doc = parse(raw, start=len(prefix), end=len(raw) - len(suffix), identity='handcrafted_synthetic')
    assert doc['artifact']['sha256'] == hashlib.sha256(raw).hexdigest()
    for cell in doc['cells']:
        loc = cell['locator']
        assert len(prefix) <= loc['byte_start'] < loc['byte_end'] <= len(prefix) + len(report)
        assert raw[loc['byte_start']:loc['byte_end']].endswith(b'\r\n')
    assert b'Total basepairs processed:' in raw[total(doc, 'cutadapt_processed_bases')['locator']['byte_start']:
                                             total(doc, 'cutadapt_processed_bases')['locator']['byte_end']]


@pytest.mark.parametrize('start,end', [(1, None), (0, 5), (-1, None), (True, None), (0, 0)])
def test_invalid_selected_byte_ranges_are_contract_failures(start, end):
    raw = native()
    with pytest.raises(FastqUtilsContractError, match='shape_invalid'):
        parse(raw, start=start, end=end)


def test_complete_artifact_binding_cannot_be_replaced_by_substring():
    raw = b'prefix\n' + native()
    report = _Report(raw, context(raw, identity='handcrafted_synthetic'), 'native_text', 'Cutadapt')
    with pytest.raises(FastqUtilsContractError, match='binding_conflict'):
        append_cutadapt_report(report, raw[7:], start=0, end=len(raw) - 7)


@pytest.mark.parametrize('scope', ['unknown', 'partial'])
def test_native_transfer_scope_is_not_invented_from_report_completeness(scope):
    doc = parse(native(), scope=scope)
    assert {p['scope'] for p in doc['populations']} == {scope}
    assert total(doc, 'cutadapt_processed_count')['state'] == ('partial' if scope == 'partial' else 'available')


def test_append_is_pure_and_does_not_finish_or_replace_outer_version(monkeypatch):
    raw = (INITIAL / 'trimgalore_single/synthetic.fastq_trimming_report.txt').read_bytes()
    start, end = raw.index(b'This is cutadapt'), raw.index(b'RUN STATISTICS FOR INPUT FILE:')
    report = _Report(raw, context(raw, outer=True), 'trim_galore_report_0_6_10', 'Trim Galore')
    def denied(*args, **kwargs):
        pytest.fail('native parser attempted external work or outer finish/version')
    monkeypatch.setattr(report, 'finish', denied)
    monkeypatch.setattr(report, 'version', denied)
    monkeypatch.setattr(subprocess, 'run', denied)
    monkeypatch.setattr(socket, 'socket', denied)
    monkeypatch.setattr(Path, 'read_bytes', denied)
    monkeypatch.setattr(Path, 'read_text', denied)
    append_cutadapt_report(report, raw, start=start, end=end)
    validate_native_document(report.doc)
    assert report.doc['artifact']['producer_version'] == '0.6.10'


def test_saved_sheet_calculates_exact_retention_without_parsing_acquisition_or_programs(monkeypatch):
    from gene_annotation_episode.bvbrc_fastqutils_metadata import extract_fastqutils_metadata
    from gene_annotation_episode.bvbrc_fastqutils_sheet import populate_fastqutils_sheet
    from gene_annotation_episode.bvbrc_fastqutils_retention import calculate_retention
    from gene_annotation_episode import bvbrc_fastqutils_native, bvbrc_fastqutils_cutadapt_reader
    # Reuse an original task shape solely as synthetic metadata. No sample,
    # reference, stage completion or remote execution is inferred from it.
    template = json.loads((Path(__file__).parent / 'fixtures/bvbrc_fastqutils/reports/saved_native_sheet.json').read_text())
    saved = []
    for case, base in [('cutadapt_single', INITIAL), ('cutadapt_filtered', INITIAL), ('zero_bases', WARNINGS)]:
        doc = parse(native(case, base))
        original = deepcopy(template['original_task'])
        original['submission_receipt_ref'] = doc['artifact']['task_ref']
        metadata = extract_fastqutils_metadata(original, analysis_id=doc['analysis_id'],
            metadata_bindings=[], supplied_values=[], documents=[doc])
        resolution = dict(document_id=doc['document_id'], selection=dict(kind='possessed_content',
            content=doc['artifact']['content_binding']), state='available',
            matched_contents=[doc['artifact']['content_binding']], artifact_ref=doc['artifact']['id'],
            requirement_refs=[], diagnostic_codes=[])
        sheet = populate_fastqutils_sheet([doc], metadata=metadata, document_resolutions=[resolution])
        before, after = total(doc, 'cutadapt_processed_bases'), total(doc, 'cutadapt_written_bases')
        edge = next(e for e in doc['native_lineage'] if e['before_population_ref'] == before['population_ref'])
        job = dict(calculation_id='base_retention', method='retention_v1', state='ready',
            population_refs=[before['population_ref'], after['population_ref']],
            operand_measurement_refs=[before['id'], after['id']], comparison_kind='base_retention',
            quality_thresholds=[], read_key_rule=None, lineage_ref=edge['id'],
            lineage_basis=dict(basis='native_report', metadata_id=None, evidence=None, declaration=None,
                               native_lineage_ref=edge['id']), requirement_refs=[], diagnostic_codes=[])
        saved.append(json.loads(json.dumps([sheet, job])))
    def denied(*args, **kwargs):
        pytest.fail('saved calculation attempted acquisition, native parsing, or execution')
    monkeypatch.setattr(bvbrc_fastqutils_native, 'parse_fastqutils_artifact', denied)
    monkeypatch.setattr(bvbrc_fastqutils_cutadapt_reader, 'append_cutadapt_report', denied)
    monkeypatch.setattr(subprocess, 'run', denied)
    monkeypatch.setattr(socket, 'socket', denied)
    for (sheet, job), (before, output) in zip(saved, ((58, 28), (58, 24), (0, 0))):
        parameters = dict(version='fastqutils_calculators_v2', analysis_id=sheet['analysis_id'], calculations=[job])
        rows = calculate_retention(sheet, job=job, parameters_sha256=json_sha256(parameters))
        by_metric = {r['metric']: r for r in rows}
        assert by_metric['base_retention_fraction']['value'] == (output / before if before else None)
        assert by_metric['base_retention_fraction']['state'] == ('available' if before else 'undefined')
        assert by_metric['removed_count']['value'] == before - output
        assert by_metric['base_retention_fraction']['denominator'] == before
        assert by_metric['base_retention_fraction']['numerator'] == output
