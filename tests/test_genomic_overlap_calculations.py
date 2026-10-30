"""Hand-checked quantities, explicit native-derived fixtures, and pure replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
from gene_annotation_episode.genomic_overlap_contracts import canonical_genomic_overlap_sheet_sha256
from test_genomic_overlap_inputs import (
    PARAMETERS, ROOT, ROW, WORKED, inputs, make_sheet, parsed_pairs,
    reference, contig, sheet_from,
)


def calculate(sheet, **overrides):
    return calculate_genomic_overlap_components(sheet, parameters={**deepcopy(PARAMETERS), **overrides})


def edge_row(a, b, width, *, ai=0, bi=0):
    return f'{a[0]}\t{a[1]}\t{a[2]}\ts0_r{ai}\t{b[0]}\t{b[1]}\t{b[2]}\ts1_r{bi}\t{width}\n'.encode()


def bed(rows):
    return ''.join('\t'.join(map(str, row)) + '\n' for row in rows).encode()


def test_exact_worked_numerical_snapshot():
    result = calculate_genomic_overlap_components(WORKED['sheet'], parameters=WORKED['components']['parameters'])
    assert result == WORKED['components']


@pytest.mark.parametrize('a,b,edges,expected', [
    ([('chr1',0,10),('chr1',5,15)], [('chr1',7,12)], [(0,0,3),(1,0,5)], (2,8,15,5,5,15)),
    ([('chr1',0,10),('chr1',5,15)], [('chr1',7,12),('chr1',10,20)], [(0,0,3),(1,0,5),(1,1,5)], (3,13,15,13,8,20)),
    ([('chr1',0,10),('chr1',0,10)], [('chr1',5,15),('chr1',5,15)], [(0,0,5),(0,1,5),(1,0,5),(1,1,5)], (4,20,10,10,5,15)),
    ([('chr1',0,10)], [('chr1',10,20)], [], (0,0,10,10,0,20)),
    ([('chr1',0,10)], [('chr2',0,10)], [], (0,0,10,10,0,20)),
    ([('chr1',0,8),('chr1',20,30,'name')], [('chr1',3,12,'same',42,'+'),('chr1',25,28,'same',0,'-')], [(0,0,5),(1,1,3)], (2,8,18,12,8,22)),
    ([('chr1',0,2000000000)], [('chr1',1999999999,2000000000)], [(0,0,1)], (1,1,2000000000,1,1,2000000000)),
    ([('chr1',0,9223372036854775807)], [('chr1',9223372036854775806,9223372036854775807)], [(0,0,1)], (1,1,9223372036854775807,1,1,9223372036854775807)),
])
def test_hand_checked_union_multiplicity_boundaries(a, b, edges, expected):
    raw = b''.join(edge_row(a[ai], b[bi], width, ai=ai, bi=bi) for ai, bi, width in edges)
    result = calculate(make_sheet(bed(a), bed(b), raw))
    pair = result['pairs'][0]
    u = pair['unfiltered']
    count, summed, ua, ub, shared, combined = expected
    assert [s['union_bp'] for s in result['sets']] == [ua, ub]
    assert (u['native_pair_count'],u['pairwise_overlap_bp_sum'],u['intersection_union_bp'],u['combined_union_bp']) == (count,summed,shared,combined)
    assert u['jaccard_bp'] == {'numerator':shared,'denominator':combined,'value':shared/combined,'missing_reason':None}
    assert u['a_union_coverage_fraction']['denominator'] == ua
    assert u['b_union_coverage_fraction']['denominator'] == ub
    assert u['a_regions_with_overlap'] == len({ai for ai,_,_ in edges})
    assert u['b_regions_with_overlap'] == len({bi for _,bi,_ in edges})
    assert pair['observed']['interpretation'] == 'exact_complete_result'
    if count == 4:
        assert [s['duplicate_coordinate_excess'] for s in result['sets']] == [1,1]
        assert [o['covered_bp'] for o in pair['occurrences']] == [5] * 8
        assert u['pairwise_overlap_bp_sum'] > combined


def test_bed12_metadata_is_retained_but_only_outer_span_is_measured():
    b = b'chr1\t7\t12\tfeature\t960\t-\t7\t12\t0\t2\t1,1\t0,4\n'
    sheet = make_sheet(b'chr1\t0\t10\n', b, ROW)
    result = calculate(sheet)
    assert sheet['sets'][1]['regions'][0]['original_fields'][9:] == ['2','1,1','0,4']
    assert result['sets'][1]['union_bp'] == 5
    assert result['pairs'][0]['unfiltered']['intersection_union_bp'] == 3


@pytest.mark.parametrize('a,b,combined,jaccard', [(b'',b'chr1\t0\t10\n',10,0.0),(b'',b'',0,None)])
def test_analytic_empty_has_exact_zero_and_null_zero_denominators(a,b,combined,jaccard):
    result = calculate(make_sheet(a,b,None,derivation='validated_empty_input'))
    pair = result['pairs'][0]
    assert pair['unfiltered']['native_pair_count'] == 0
    assert pair['unfiltered']['combined_union_bp'] == combined
    assert pair['unfiltered']['jaccard_bp']['value'] == jaccard
    assert pair['unfiltered']['a_region_overlap_fraction']['missing_reason'] == 'zero_denominator'
    assert pair['unfiltered']['a_union_coverage_fraction']['denominator'] == 0
    assert any(i['code'] == 'zero_denominator' for i in pair['issues'])


def test_partial_output_preserves_observed_lower_bounds_without_complete_ratios():
    request, sets = inputs([b'chr1\t0\t10\nchr1\t5\t15\n', b'chr1\t7\t12\n'])
    raw = ROW + b'chr1\t5\t15\ts0_r1\tchr1\t7'
    parsed = parsed_pairs(request,sets,raw,changes={'native_result_extent':'partial','completeness_basis':'partial_native_result'})
    result = calculate(sheet_from(request,sets,[parsed]))
    pair = result['pairs'][0]
    assert [s['union_bp'] for s in result['sets']] == [15,5]
    assert pair['observed'] == {'observed_pair_count':1,'observed_pairwise_bp_sum':3,
                                'observed_intersection_union_bp':3,'interpretation':'lower_bound_subset'}
    assert pair['result_extent'] == 'partial'
    assert pair['unfiltered']['native_pair_count'] is None
    assert pair['unfiltered']['jaccard_bp']['value'] is None
    assert pair['unfiltered']['jaccard_bp']['missing_reason'] == 'incomplete_native_result'
    assert pair['unfiltered']['a_union_coverage_fraction']['denominator'] == 15
    assert all(o['covered_bp'] is None for o in pair['occurrences'])
    assert pair['edges'][0]['a_overlap_fraction']['value'] == 0.3
    assert any(i['field_path'] == '/pairs/0/unfiltered/jaccard_bp' for i in pair['issues'])


def test_wrong_width_and_duplicate_rows_never_add_to_observed_totals():
    bad = ROW.replace(b'\t3\n', b'\t4\n')
    result = calculate(make_sheet(b'chr1\t0\t10\n',b'chr1\t7\t12\n',ROW + bad + ROW))
    pair = result['pairs'][0]
    assert pair['observed']['observed_pair_count'] == 1
    assert pair['observed']['observed_pairwise_bp_sum'] == 3
    assert pair['unfiltered']['pairwise_overlap_bp_sum'] is None


def test_changed_native_bytes_cannot_claim_genuine_subset_lower_bounds():
    sheet = make_sheet(b'chr1\t0\t10\n',b'chr1\t7\t12\n',ROW)
    request, sets = sheet['request'], sheet['sets']
    metadata = deepcopy(sheet['comparisons'][0]['receipt'])
    metadata['stdout']['sha256'] = '0' * 64
    from gene_annotation_episode.genomic_overlap_inputs import parse_bedtools_intersect_wo
    parsed = parse_bedtools_intersect_wo(ROW,pair=request['comparisons'][0],sets={s['set_key']:s for s in sets},native=metadata)
    result = calculate(sheet_from(request,sets,[parsed]))
    assert result['pairs'][0]['observed']['interpretation'] == 'unavailable'
    assert result['pairs'][0]['observed']['observed_pair_count'] is None
    assert len(result['pairs'][0]['edges']) == 1


def test_saved_recalculation_has_no_acquisition_or_execution_and_preserves_history(monkeypatch,tmp_path):
    sheet_path = tmp_path / 'source_sheet.json'
    sheet_path.write_text(json.dumps(WORKED['sheet'],sort_keys=True))
    saved = json.loads(sheet_path.read_text())
    original = deepcopy(saved)
    old = calculate(saved)
    old_snapshot = json.dumps(old,sort_keys=True)
    def forbidden(*args,**kwargs):
        raise AssertionError('saved calculation attempted acquisition or execution')
    import builtins
    monkeypatch.setattr(builtins,'open',forbidden)
    monkeypatch.setattr(Path,'open',forbidden)
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    changed = calculate(saved,minimum_overlap_bp=4)
    fraction = calculate(saved,minimum_a_fraction={'numerator':1,'denominator':2},minimum_b_fraction={'numerator':1,'denominator':1})
    assert changed['pairs'][0]['selected']['selected_pair_count'] == 1
    assert changed['pairs'][0]['selected']['selected_pairwise_bp_sum'] == 5
    assert changed['pairs'][0]['selected']['a_region_overlap_fraction']['value'] == .5
    assert fraction['pairs'][0]['selected'] == changed['pairs'][0]['selected']
    assert changed['pairs'][0]['unfiltered'] == old['pairs'][0]['unfiltered']
    assert changed['source_sheet_sha256'] == old['source_sheet_sha256']
    assert saved == original and json.dumps(old,sort_keys=True) == old_snapshot
    changed['edges'] = []
    changed['sets'][0]['region_geometry'][0]['span_bp'] = 900
    assert old['sets'][0]['region_geometry'][0]['span_bp'] == 10


def test_threshold_rationals_use_exact_integer_cross_products():
    result = calculate(WORKED['sheet'],minimum_a_fraction={'numerator':5*10**30,'denominator':10*10**30})
    assert [e['selected'] for e in result['pairs'][0]['edges']] == [False,True]
    result = calculate(WORKED['sheet'],minimum_a_fraction={'numerator':5*10**30+1,'denominator':10*10**30})
    assert [e['selected'] for e in result['pairs'][0]['edges']] == [False,False]
    with pytest.raises(ValueError,match='fraction_threshold'):
        calculate(WORKED['sheet'],minimum_a_fraction={'numerator':2,'denominator':1})


def test_cannot_fabricate_missing_pairs_by_recomputing_input_geometry():
    # Deliberately supplied assertion of a complete empty native table. The pure
    # calculator preserves source-declared scope and does not execute intersection.
    result = calculate(make_sheet(b'chr1\t0\t10\n', b'chr1\t7\t12\n', b''))
    assert result['pairs'][0]['unfiltered']['native_pair_count'] == 0
    assert result['pairs'][0]['edges'] == []


def test_missing_reference_and_explicit_conflict_do_not_change_coordinate_geometry():
    first = calculate(make_sheet(b'chr1\t0\t10\n',b'chr1\t7\t12\n',ROW))
    second = calculate(make_sheet(b'chr1\t0\t10\n',b'chr1\t7\t12\n',ROW,
        references=[reference('A.1'),reference('A.2')]))
    assert first['pairs'][0]['unfiltered'] == second['pairs'][0]['unfiltered']
    assert first['pairs'][0]['reference_relation'] == 'unknown'
    assert second['pairs'][0]['reference_relation'] == 'different_supplied_references'


def test_independent_pair_is_numerical_beside_invalid_input():
    request,sets = inputs([b'chr1\t0\t10\n',b'chr1\t7\t12\n',b'chr1\t3\t3\n'])
    pairs = [parsed_pairs(request,sets,ROW)] + [parsed_pairs(request,sets,None,
        derivation='not_executed_invalid_input',pair_index=i) for i in (1,2)]
    result = calculate(sheet_from(request,sets,pairs))
    assert result['pairs'][0]['unfiltered']['intersection_union_bp'] == 3
    assert result['pairs'][1]['unfiltered']['native_pair_count'] is None
    assert result['pairs'][2]['unfiltered']['jaccard_bp']['missing_reason'] == 'incomplete_input'
    assert result['sets'][2]['valid_region_count'] == 0 and result['sets'][2]['region_count'] is None


def test_calculator_rechecks_saved_sheet_semantics():
    sheet = deepcopy(WORKED['sheet'])
    sheet['comparisons'][0]['valid_pairs'][0]['native_overlap_bp'] = 4
    with pytest.raises(ValueError,match='pair_width'):
        calculate(sheet)


@pytest.mark.parametrize('case,count,summed,shared',[
    ('overlapping_a',2,8,5),('overlapping_both',3,13,8),('duplicate_occurrences',4,20,5),
    ('touching_endpoints',0,0,0),('different_chromosomes',0,0,0),
    ('long_interval_one_bp',1,1,1),('signed_64bit_endpoint',1,1,1),
])
def test_explicitly_derived_token_mapping_from_retained_native_421(case,count,summed,shared):
    # Actual 421 bytes remain unchanged. This test fixture explicitly replaces
    # legacy A1/B1 tokens with frozen G1 tokens; it is not a new native result.
    path = ROOT / 'verification/tool_graders_genomic_overlap_native_2026-10-27_421/run002/work'
    a,b = [(path / f'{case}.{side}.bed').read_bytes() for side in ('A','B')]
    original = (path / f'{case}.stdout').read_bytes()
    request,sets = inputs([a,b])
    mapping = {}
    for parsed in sets:
        for row in parsed['regions']:
            mapping[row['name']] = row['native_token']
    remapped = []
    for line in original.decode().splitlines():
        fields = line.split('\t')
        fields[3],fields[7] = mapping[fields[3]],mapping[fields[7]]
        remapped.append('\t'.join(fields)+'\n')
    derived = ''.join(remapped).encode()
    parsed = parsed_pairs(request,sets,derived)
    result = calculate(sheet_from(request,sets,[parsed]))
    metrics = result['pairs'][0]['unfiltered']
    assert (metrics['native_pair_count'],metrics['pairwise_overlap_bp_sum'],metrics['intersection_union_bp']) == (count,summed,shared)
    assert (path / f'{case}.stdout').read_bytes() == original


def test_sparse_many_regions_keeps_zero_coverage_and_ordered_partner_joins():
    a = [('chr1',i*10,i*10+8) for i in range(2048)]
    hit_ordinals = list(range(0,len(a),128))
    b = [('chr1',i*10+4,i*10+10) for i in hit_ordinals]
    # Descending native order remains visible in edge and adjacency lists.
    raw = b''.join(edge_row(a[ai],b[bi],4,ai=ai,bi=bi)
                   for bi,ai in reversed(list(enumerate(hit_ordinals))))
    result = calculate(make_sheet(bed(a),bed(b),raw),minimum_overlap_bp=5)
    pair = result['pairs'][0]
    assert pair['unfiltered']['native_pair_count'] == 16
    assert pair['unfiltered']['intersection_union_bp'] == 64
    assert pair['unfiltered']['combined_union_bp'] == 16416
    assert pair['unfiltered']['a_region_overlap_fraction']['numerator'] == 16
    assert pair['unfiltered']['a_region_overlap_fraction']['denominator'] == 2048
    assert pair['selected']['selected_pair_count'] == 0
    occurrences = pair['occurrences']
    unfiltered_a = occurrences[:2048]
    assert [row['occurrence_key'] for row in unfiltered_a] == [f'r{i}' for i in range(2048)]
    assert sum(row['covered_bp'] for row in unfiltered_a) == 64
    assert sum(row['partner_count'] for row in unfiltered_a) == 16
    assert unfiltered_a[1]['covered_bp'] == 0 and unfiltered_a[1]['pair_keys'] == []
    assert unfiltered_a[128]['pair_keys'] == ['p0:a128:b1']
    assert all(row['covered_bp'] == 0 for row in occurrences[2064:])


def test_incompatible_supplied_invocation_preserves_only_genuine_subset_totals():
    sheet = make_sheet(b'chr1\t0\t10\n',b'chr1\t7\t12\n',ROW,
        changes={'realized_argv':['bedtools','intersect','-a','A','-b','B','-wo','-s']})
    result = calculate(sheet)
    pair = result['pairs'][0]
    assert pair['result_extent'] == 'partial'
    assert pair['observed']['interpretation'] == 'lower_bound_subset'
    assert pair['observed']['observed_pairwise_bp_sum'] == 3
    assert pair['unfiltered']['native_pair_count'] is None
    forged = deepcopy(WORKED['sheet'])
    forged['comparisons'][0]['receipt']['realized_argv'].append('-s')
    with pytest.raises(ValueError,match='incompatible_supplied_invocation'):
        calculate(forged)
