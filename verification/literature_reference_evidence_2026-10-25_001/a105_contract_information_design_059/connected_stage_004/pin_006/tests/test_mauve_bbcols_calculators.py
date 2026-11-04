"""BBCols numeric families with explicit synthetic task/member/block joins."""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.mauve_backbone_formats import parse_mauve_bbcols
from gene_annotation_episode.mauve_backbone_calculators import calculate_mauve_bbcols_components
from gene_annotation_episode.mauve_backbone_contracts import (
    validate_mauve_bbcols_document, validate_mauve_bbcols_selection, validate_mauve_bbcols_components,
    BBCOLS_DIALECT,
)
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_associations
from test_bvbrc_genome_alignment_input_contracts import artifact_member, original_task, evidence, native_member
from test_mauve_backbone_formats import bbcols, selection, members, artifact, NATIVE, assert_locations
from test_mauve_backbone_calculators import forbid_io


def xmfa(raw=None):
    if raw is None: raw = (NATIVE / 'separate.xmfa').read_bytes()
    result = parse_mauve_xmfa(raw, artifact=artifact(raw, 'xmfa'), dialect='mauve1', alphabet='dna', encoding='ascii')
    assert result['status'] in ('ok', 'partial')
    return result['value']


def associations(doc, primary, *, indices=(0, 1, 2), mapping=None):
    """Fabricated test custody, explicitly not a native service receipt."""
    value = {'schema_version': 'bvbrc_genome_alignment_associations_v1',
        'original_task': original_task(['synthetic:g0', 'synthetic:g1', 'synthetic:g2']),
        'artifacts': [], 'native_member_joins': [], 'bbcols_interval_joins': [],
        'duplicate_representations': [], 'requirements': [], 'diagnostics': []}
    for source, role, fmt, name in ((doc, 'genome_alignment_bbcols', 'mauve_bbcols', 'bbcols'),
                                   (primary, 'genome_alignment_primary', 'mauve1_xmfa', 'xmfa')):
        a = artifact_member(role, fmt, name)
        a.update(source['artifact'])
        a['declared_format']['version'] = BBCOLS_DIALECT if name == 'bbcols' else 'Mauve1'
        value['artifacts'].append({'artifact': a, 'role': role, 'observed_format': fmt,
            'document_id': source['document_id'], 'state': 'bound', 'evidence': [evidence()], 'requirement_ids': []})
        for index in indices:
            value['native_member_joins'].append({'artifact': deepcopy(source['artifact']),
                'member': members(index)[0] if name == 'bbcols' else native_member(index + 1),
                'input_member': native_member(index + 1), 'state': 'bound', 'evidence': [evidence()], 'requirement_ids': []})
    if mapping is None:
        mapping = {0: 0}
    for native, block in mapping.items():
        value['bbcols_interval_joins'].append({'bbcols_document_id': doc['document_id'],
            'native_interval_index_0based': native, 'xmfa_document_id': primary['document_id'],
            'xmfa_block_index': block, 'state': 'bound', 'evidence': [evidence()], 'requirement_ids': []})
    assert validate_genome_alignment_associations(value) == value
    return value


def calculate(doc, *, primary=None, joins=None, **options):
    return calculate_mauve_bbcols_components(doc, selection=selection(doc, **options),
        xmfa_document=primary, associations=joins)


def test_official_native_bbcols_receipt_and_column_mapping():
    raw = (NATIVE / 'separate.xmfa.bbcols').read_bytes()
    receipts = json.loads((NATIVE.parent / 'SOURCE_RECEIPTS.json').read_text())
    receipt = next(r for r in receipts if r['path'] == 'native_examples/separate.xmfa.bbcols')
    assert hashlib.sha256(raw).hexdigest() == receipt['sha256'] == '02705f27d4a468ca5736997daf28846ec26c607d0f156da918ed71e3d3be316b'
    result = bbcols(); doc = result['value']
    assert result['status'] == 'ok'; assert_locations(doc, raw)
    assert [r['columns_0based_half_open'] for r in doc['rows']] == [[33, 52], [0, 33]]
    assert [[n['value'] for n in r['native_member_indices_0based']] for r in doc['rows']] == [[0, 1, 2], [0, 1]]


@pytest.mark.parametrize('threshold,width,contributing', [(1, 52, [0, 1]), (2, 52, [0, 1]), (3, 19, [0])])
def test_official_filled_native_union_and_explicit_bound_fraction(threshold, width, contributing):
    doc = bbcols()['value']; primary = xmfa(); joins = associations(doc, primary)
    result = calculate(doc, primary=primary, joins=joins, threshold=threshold, fraction=True)
    assert result['status'] == 'ok'
    row = result['intervals'][0]
    assert [r['column_count']['value'] for r in result['rows']] == [19, 33]
    assert [r['selected_member_count']['value'] for r in result['rows']] == [3, 2]
    assert row['contributing_row_indices'] == contributing
    assert row['union_columns']['value'] == row['column_placements']['value'] == width
    assert row['bound_block_width']['value'] == 52
    assert row['selected_block_fraction']['value'] == width / 52
    assert row['multiply_represented_columns']['value'] == row['excess_column_placements']['value'] == 0


def test_unknown_join_retains_native_union_but_does_not_assume_interval_is_block_index():
    doc = bbcols()['value']; primary = xmfa()
    result = calculate(doc, primary=primary, fraction=True)
    row = result['intervals'][0]
    assert row['union_columns']['value'] == 52
    assert row['selected_block_fraction']['state'] == 'missing'
    assert row['xmfa_block_index'] is None
    assert result['requirements']
    assert all(r['join_state'] == 'missing' for r in result['rows'])


def test_internal_interval_seven_can_explicitly_join_exported_block_zero():
    doc = bbcols(b'7 1 4 0 1\n')['value']; primary = xmfa()
    result = calculate(doc, primary=primary, joins=associations(doc, primary, mapping={7: 0}), fraction=True)
    assert result['intervals'][0]['native_interval_index_0based'] == 7
    assert result['intervals'][0]['xmfa_block_index'] == 0
    assert result['intervals'][0]['selected_block_fraction']['value'] == 4 / 52


def test_overlapping_column_ranges_and_repeated_rows_keep_unique_and_sum_separate():
    doc = bbcols(b'7 1 5 0 1\n7 3 5 0 1\n7 1 5 0 1\n7 8 2 0 1\n')['value']
    result = calculate(doc, chosen=members(0, 1), threshold=2)
    row = result['intervals'][0]
    assert row['contributing_row_indices'] == [0, 1, 2, 3]
    assert row['known_union_intervals'] == [[0, 9]]
    assert [row[k]['value'] for k in ('union_columns', 'column_placements', 'multiply_represented_columns', 'excess_column_placements')] == [9, 17, 5, 8]
    assert row['selected_block_fraction']['state'] == 'not_measured'


@pytest.mark.parametrize('raw,state,code', [(b'-1 1 3 0\n', 'incompatible', 'interval_ordinal_invalid'),
    (b'0 0 3 0\n', 'incompatible', 'coordinate_invalid'), (b'0 1 0 0\n', 'incompatible', 'count_invalid'),
    (b'0 1 -3 0\n', 'incompatible', 'count_invalid'), (b'0 1 3 -1\n', 'incompatible', 'member_invalid'),
    (b'0 1 3 0 0\n', 'incompatible', 'member_duplicate'), (b'0 1 3 x\n', 'incompatible', 'member_invalid'),
    (b'0 1\n', 'incomplete', 'row_incomplete'), (b'0 1 3\n', 'incomplete', 'row_incomplete'),
    (b'0 1 3.0 0\n', 'incompatible', 'count_invalid'), (b'0 1 NaN 0\n', 'incompatible', 'count_invalid'),
    (b'0 1 3 1.0\n', 'incompatible', 'member_invalid')])
def test_headerless_invalid_native_tokens_are_retained(raw, state, code):
    result = bbcols(raw); doc = result['value']
    assert result['status'] == 'partial'; assert doc['rows'][0]['state'] == state
    assert any(d['code'] == 'mauve_bbcols_' + code for d in result['diagnostics'])
    assert_locations(doc, raw)
    counts = calculate(doc, chosen=members(0, 1))
    assert counts['status'] == 'partial'


def test_native_empty_is_unknown_not_zero_backbone_coverage():
    result = bbcols(b''); doc = result['value']
    assert result['status'] == 'ok' and doc['completeness'] == 'unknown' and doc['rows'] == []
    counts = calculate(doc)
    assert counts['status'] == 'partial' and counts['rows'] == counts['intervals'] == []
    assert counts['requirements']


def test_partial_rows_keep_independent_numbers_and_use_unknown_eligibility():
    doc = bbcols(b'0 1 3 0 1\n0 4 7 0 x\n')['value']
    result = calculate(doc, chosen=members(0, 1), threshold=2)
    assert result['rows'][1]['column_count']['value'] == 7
    assert result['rows'][1]['selected_by_multiplicity'] is None
    assert result['rows'][1]['unresolved_member_tokens'][0]['raw_token'] == 'x'
    assert result['intervals'][0]['union_columns']['value'] == 3
    assert result['intervals'][0]['population_state'] == 'partial_selected'


def test_duplicate_member_tokens_do_not_inflate_multiplicity_or_create_false_zero():
    doc = bbcols(b'0 1 3 0 0\n')['value']
    result = calculate(doc, chosen=members(0, 1), threshold=2)
    assert result['rows'][0]['selected_member_count']['value'] == 1
    assert result['rows'][0]['selected_by_multiplicity'] is None
    assert len(result['rows'][0]['unresolved_member_tokens']) == 2
    assert result['intervals'][0]['union_columns']['value'] is None


@pytest.mark.parametrize('change', ['range', 'block', 'member', 'other_document', 'wrong_input_member'])
def test_wrong_joins_cannot_supply_fraction_but_native_counts_survive(change):
    doc = bbcols(b'0 34 20 0 1 2\n' if change == 'range' else b'0 1 3 0 1\n')['value']
    primary = xmfa(); joins = associations(doc, primary)
    supplied = primary
    if change == 'block': joins['bbcols_interval_joins'][0]['xmfa_block_index'] = 999
    elif change == 'member':
        # Member 1 is absent from exported singleton block 1.
        joins['bbcols_interval_joins'][0]['xmfa_block_index'] = 1
    elif change == 'other_document':
        supplied = xmfa(b'#FormatVersion Mauve1\n> 1:1-4 + other\nACGT\n=\n')
    elif change == 'wrong_input_member':
        joins['native_member_joins'][0]['input_member'] = native_member(8)
    result = calculate(doc, primary=supplied, joins=joins, fraction=True)
    assert result['intervals'][0]['union_columns']['value'] == (20 if change == 'range' else 3)
    assert result['intervals'][0]['selected_block_fraction']['state'] == 'incompatible'
    assert result['rows'][0]['join_state'] == 'conflicting'


def test_missing_unselected_member_join_does_not_block_selected_fraction_but_requirement_survives():
    doc = bbcols()['value']; primary = xmfa()
    joins = associations(doc, primary, indices=(0, 1))
    result = calculate(doc, primary=primary, joins=joins, chosen=members(0, 1), threshold=2, fraction=True)
    assert result['intervals'][0]['selected_block_fraction']['value'] == 1
    assert any(r['reason_code'] == 'bvbrc_genome_alignment_member_join_missing' for r in result['requirements'])


def test_missing_selected_member_join_prevents_fraction_and_retains_counts():
    doc = bbcols()['value']; primary = xmfa()
    joins = associations(doc, primary, indices=(0, 1))
    result = calculate(doc, primary=primary, joins=joins, threshold=3, fraction=True)
    assert result['intervals'][0]['union_columns']['value'] == 19
    assert result['intervals'][0]['selected_block_fraction']['state'] == 'missing'


def test_missing_noncontributing_member_join_does_not_invalidate_known_selected_fraction():
    doc = bbcols()['value']; primary = xmfa()
    joins = associations(doc, primary, indices=(0, 2))
    # Row 1 has multiplicity 1 in this subset, and therefore contributes nothing.
    result = calculate(doc, primary=primary, joins=joins, chosen=members(0, 2), threshold=2, fraction=True)
    assert result['intervals'][0]['selected_block_fraction']['value'] == 19 / 52
    assert any(r['reason_code'] == 'bvbrc_genome_alignment_member_join_missing' for r in result['requirements'])


def test_partial_xmfa_block_does_not_become_complete_bound_denominator():
    doc = bbcols(b'0 1 3 0\n')['value']
    primary = xmfa(b'#FormatVersion Mauve1\n> 1:1-4 + synthetic\nACGT\n')
    joins = associations(doc, primary, indices=(0,))
    result = calculate(doc, primary=primary, joins=joins, chosen=members(0), fraction=True)
    assert result['intervals'][0]['union_columns']['value'] == 3
    assert result['intervals'][0]['selected_block_fraction']['state'] == 'truncated'


def test_two_native_intervals_remain_separate_union_axes():
    doc = bbcols(b'0 1 5 0 1\n7 1 5 0 1\n')['value']
    result = calculate(doc, chosen=members(0, 1))
    assert [r['native_interval_index_0based'] for r in result['intervals']] == [0, 7]
    assert [r['union_columns']['value'] for r in result['intervals']] == [5, 5]


@pytest.mark.parametrize('change', ['bool_member', 'extra_key', 'threshold', 'wrong_namespace', 'bad_flag', 'duplicate_row'])
def test_invalid_selection_cannot_supply_trusted_population(change):
    v = selection(bbcols()['value'])
    if change == 'bool_member': v['members'][0]['index'] = False
    elif change == 'extra_key': v['complete'] = True
    elif change == 'threshold': v['minimum_selected_multiplicity'] = 4
    elif change == 'wrong_namespace': v['members'][0]['namespace'] = 'mauve_v4_member_0based'
    elif change == 'bad_flag': v['calculate_bound_block_fraction'] = 1
    else: v['row_indices'] = [0, 0]
    with pytest.raises(ValueError, match='mauve_bbcols_selection_invalid'):
        validate_mauve_bbcols_selection(v)


@pytest.mark.parametrize('change', ['interval', 'state', 'value', 'extra_key', 'location', 'member_tokens'])
def test_saved_bbcols_document_relationship_mutations_fail(change):
    v = bbcols()['value']; row = v['rows'][0]
    if change == 'interval': row['columns_0based_half_open'] = [34, 53]
    elif change == 'state': row['state'] = 'incompatible'
    elif change == 'value': row['native_column_count']['value'] = 20
    elif change == 'extra_key': row['posterior'] = 1
    elif change == 'location': row['source_location']['byte_end_0based_exclusive'] -= 1
    else: row['native_member_indices_0based'].pop()
    with pytest.raises(ValueError, match='mauve_bbcols_'):
        validate_mauve_bbcols_document(v)


@pytest.mark.parametrize('change', ['union', 'sum', 'multiple', 'fraction', 'numerator', 'units',
    'eligibility', 'join', 'requirements', 'extra_key'])
def test_saved_bbcols_components_reject_corrupted_values(change):
    doc = bbcols()['value']; primary = xmfa(); joins = associations(doc, primary)
    v = calculate(doc, primary=primary, joins=joins, fraction=True); row = v['intervals'][0]
    if change == 'union': row['union_columns']['value'] = 51
    elif change == 'sum': row['column_placements']['value'] = 100
    elif change == 'multiple': row['multiply_represented_columns']['value'] = 1
    elif change == 'fraction': row['selected_block_fraction']['value'] = 0.5
    elif change == 'numerator': row['selected_block_fraction']['numerator'] = 12
    elif change == 'units': row['union_columns']['unit'] = 'nucleotides'
    elif change == 'eligibility': v['rows'][0]['selected_by_multiplicity'] = False
    elif change == 'join': v['rows'][0]['xmfa_block_index'] = 1
    elif change == 'requirements': row['requirement_ids'] = ['invented']
    else: row['hmm_posterior'] = 0.99
    with pytest.raises(ValueError, match='mauve_bbcols_'):
        validate_mauve_bbcols_components(v)


def test_nonnull_associations_require_the_exact_c_contract():
    with pytest.raises(ValueError, match='bvbrc_genome_alignment_'):
        calculate(bbcols()['value'], joins={'bbcols_interval_joins': []})


def test_saved_recalculation_changes_subset_without_io_or_any_native_analysis(monkeypatch):
    doc = json.loads(json.dumps(bbcols()['value'])); primary = xmfa(); joins = associations(doc, primary)
    before = deepcopy((doc, primary, joins))
    first = calculate(doc, primary=primary, joins=joins, threshold=2, fraction=True)
    forbidden = forbid_io(monkeypatch)
    second = calculate(doc, primary=primary, joins=joins, threshold=3, fraction=True)
    assert first['intervals'][0]['selected_block_fraction']['value'] == 1
    assert second['intervals'][0]['selected_block_fraction']['value'] == 19 / 52
    monkeypatch.setattr('gene_annotation_episode.mauve_backbone_calculators.calculate_mauve_bbcols_components', forbidden)
    assert validate_mauve_bbcols_components(first) == first
    assert (doc, primary, joins) == before
