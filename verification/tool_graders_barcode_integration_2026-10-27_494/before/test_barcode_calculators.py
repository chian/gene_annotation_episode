from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.barcode_calculators import calculate_barcode_components, recut_barcode_linkage
from gene_annotation_episode.barcode_contracts import canonical
from gene_annotation_episode.barcode_formats import parse_barcode_native_bundle
from gene_annotation_episode.barcode_metadata import join_barcode_metadata
from test_barcode_formats import make_bundle, pack, unpack
from test_barcode_metadata import build, parameters


def value(result, key):
    return result['summary'][key]['value']


def test_hand_calculated_twelve_read_case_every_abundance_and_distance_component():
    sheet = build()
    result = calculate_barcode_components(sheet, parameters=parameters(sheet))
    assert [value(result, k) for k in ('total_records', 'extracted_records', 'distinct_barcode_count',
        'retained_barcode_count', 'retained_read_count', 'discarded_read_count')] == [12, 10, 4, 3, 9, 1]
    assert value(result, 'extraction_fraction') == 5 / 6
    assert value(result, 'retained_fraction_extracted') == 9 / 10
    assert value(result, 'retained_fraction_all_reads') == 3 / 4
    assert value(result, 'mean_pair_distance') == 8 / 3
    assert value(result, 'max_pair_distance') == 4
    assert [r['measurements']['fraction_all_reads']['value'] for r in result['barcodes']] == [1 / 3, 1 / 4, 1 / 6, 1 / 12]
    assert [r['measurements']['fraction_extracted_reads']['value'] for r in result['barcodes']] == [2 / 5, 3 / 10, 1 / 5, 1 / 10]
    assert [r['measurements']['fraction_retained_reads']['value'] for r in result['barcodes']] == [4 / 9, 1 / 3, 2 / 9, None]
    assert result['barcodes'][3]['measurements']['fraction_retained_reads']['state'] == 'not_applicable'
    assert [r['measurements']['distance_fraction']['value'] for r in result['distances']] == [1 / 4, 1, 3 / 4]
    assert [r['measurements']['cluster_read_count']['value'] for r in result['clusters']] == [7, 2]
    assert [r['measurements']['cluster_fraction_all_reads']['value'] for r in result['clusters']] == [7 / 12, 1 / 6]
    assert [r['measurements']['cluster_fraction_retained_reads']['value'] for r in result['clusters']] == [7 / 9, 2 / 9]


def test_recut_boundary_and_direct_three_mismatch_bug_counterexample():
    sheet = build()
    before = deepcopy(sheet)
    low = calculate_barcode_components(sheet, parameters=parameters(sheet, threshold=3))
    high = calculate_barcode_components(sheet, parameters=parameters(sheet, threshold=3.5))
    assert value(low, 'cluster_count') == 2 and value(high, 'cluster_count') == 1
    assert value(high, 'largest_cluster_read_count') == 9
    assert sheet == before
    sheet = build(barcodes=['AAAA', 'ATTT'], min_count=1)
    result = calculate_barcode_components(sheet, parameters=parameters(sheet, threshold=3))
    assert value(result, 'mean_pair_distance') == 3
    assert value(result, 'cluster_count') == 1
    assert value(result, 'largest_cluster_read_count') == 2


@pytest.mark.parametrize('minimum,reads,types', [(1, 10, 4), (3, 7, 2), (5, 0, 0)])
def test_changed_count_population_recalculates_counts_without_deriving_new_distances(minimum, reads, types):
    sheet = build()
    result = calculate_barcode_components(sheet, parameters=parameters(sheet, min_count=minimum))
    assert value(result, 'retained_read_count') == reads
    assert value(result, 'retained_barcode_count') == types
    assert value(result, 'discarded_read_count') == 10 - reads
    assert len(result['barcodes']) == 4
    assert value(result, 'cluster_count') is None
    assert 'missing_distance_population' in {r['code'] for r in result['issues']}


def test_same_retained_population_can_change_display_threshold_without_losing_tree():
    sheet = build(barcodes=['AAAA'] * 3 + ['ATTT'] * 3, min_count=2)
    result = calculate_barcode_components(sheet, parameters=parameters(sheet, min_count=3))
    assert value(result, 'cluster_count') == 1


def test_zero_denominators_k0_k1_and_complete_zero_numerators():
    empty = build(barcodes=[])
    result = calculate_barcode_components(empty, parameters=parameters(empty))
    assert value(result, 'total_records') == 0
    assert result['summary']['extraction_fraction']['state'] == 'zero_denominator'
    assert result['summary']['cluster_count']['state'] == 'not_applicable'
    unmatched = build(barcodes=[None, None])
    result = calculate_barcode_components(unmatched, parameters=parameters(unmatched))
    assert value(result, 'extraction_fraction') == 0
    assert result['summary']['extraction_fraction']['state'] == 'available'
    one = build(barcodes=['AAAA'], min_count=1)
    result = calculate_barcode_components(one, parameters=parameters(one))
    assert value(result, 'retained_read_count') == 1
    assert value(result, 'pair_count') == 0
    assert result['summary']['mean_pair_distance']['state'] == 'not_applicable'
    assert result['summary']['cluster_count']['value'] is None


def test_prefix_denominators_remain_prefix_and_failed_pairs_do_not_enter_mean():
    sheet = build(extent='prefix')
    result = calculate_barcode_components(sheet, parameters=parameters(sheet))
    assert result['summary']['extraction_fraction']['value'] == 5 / 6
    assert result['summary']['extraction_fraction']['state'] == 'partial_population'
    assert result['summary']['extraction_fraction']['extent'] == 'prefix'
    sheet = build(barcodes=['AA', 'AAA'], min_count=1)
    result = calculate_barcode_components(sheet, parameters=parameters(sheet))
    assert value(result, 'mean_pair_distance') is None
    assert result['summary']['mean_pair_distance']['state'] == 'invalid'
    assert result['distances'][0]['measurements']['distance_fraction']['state'] == 'invalid'
    assert value(result, 'extracted_records') == 2


def test_saved_sheet_recalculation_works_with_original_analysis_and_input_unavailable(tmp_path, monkeypatch):
    sheet = build()
    path = tmp_path / 'saved-sheet.json'
    path.write_bytes(canonical(sheet))
    saved = json.loads(path.read_bytes())
    # Only the complete saved sheet is supplied. No original input path exists.
    def forbidden(*args, **kwargs):
        raise AssertionError('acquisition or execution is forbidden during saved recalculation')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('gene_annotation_episode.barcode_formats.parse_barcode_native_bundle', forbidden)
    import Bio.SeqIO
    monkeypatch.setattr(Bio.SeqIO, 'parse', forbidden)
    result = calculate_barcode_components(saved, parameters=parameters(saved, threshold=3.5))
    assert value(result, 'cluster_count') == 1 and value(result, 'largest_cluster_read_count') == 9


def test_absent_linkage_does_not_discard_count_or_pair_components():
    request, files = make_bundle()
    payloads = unpack(files)
    del payloads['linkage'], payloads['clusters']
    files = pack(request, payloads, status='partial', stages=dict(input='complete', extract='complete',
        count='complete', distance='complete', cluster='failed'))
    parsed = parse_barcode_native_bundle(files, request=request)
    sheet = join_barcode_metadata(parsed, sample=request['sample'], target_rows=())['sheet']
    result = calculate_barcode_components(sheet, parameters=parameters(sheet))
    assert value(result, 'retained_read_count') == 9 and value(result, 'mean_pair_distance') == 8 / 3
    assert value(result, 'cluster_count') is None


def test_invalid_tree_nodes_and_changed_saved_count_are_rejected():
    sheet = build()
    tree = deepcopy(sheet['linkage'])
    tree['merges'][0]['leaf_count'] = 3
    with pytest.raises(ValueError, match='invalid_linkage_membership'):
        recut_barcode_linkage(tree, threshold=3)
    sheet['counts'][0]['read_count'] = 20
    with pytest.raises(ValueError, match='counts_population_mismatch'):
        calculate_barcode_components(sheet, parameters=parameters(sheet))


def test_filled_example_is_saved_with_stage_outcomes_and_both_recut_variants():
    from gene_annotation_episode.barcode_result_views import project_barcode_result
    from test_barcode_metadata import mapping
    from test_barcode_result_views import selector
    sheet = build(target_rows=[mapping('AAAA', 'targetX'), mapping('AAAT', 'targetX'), mapping('TTTT', 'targetY')])
    original = calculate_barcode_components(sheet, parameters=parameters(sheet, targets='unique_mapping_only'))
    recut = calculate_barcode_components(sheet, parameters=parameters(sheet, threshold=3.5, targets='unique_mapping_only'))
    assert sheet['manifest']['stages'] == dict(input='complete', extract='complete', count='complete',
                                             distance='complete', cluster='complete')
    projection = project_barcode_result(sheet, original, request=selector(fields=['extraction_fraction',
        'retained_read_count', 'retained_fraction_extracted', 'retained_fraction_all_reads', 'mean_pair_distance', 'cluster_count']))
    assert projection['rows'][0]['measurements']['mean_pair_distance']['value'] == 8 / 3
    if 'BARCODE491_ATTEMPT' in os.environ:
        (Path(os.environ['BARCODE491_ATTEMPT']) / 'filled_barcode_example.json').write_bytes(canonical({
            'evidence_kind': 'synthetic_hand_checkable', 'sheet': sheet, 'original_components': original,
            'recut_components': recut, 'projection': projection}))
