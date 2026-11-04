"""Native fixtures and deliberately synthetic coordinate counterexamples."""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.xmfa_coordinates import xmfa_column_coordinates, xmfa_source_positions
from gene_annotation_episode.xmfa_calculation_contracts import (
    validate_xmfa_coordinates, validate_xmfa_inverse_coordinates)
from test_xmfa_sources import BASE, native_document, supplied, bind, input_file, evidence, mapping


def cell(block, record, column):
    return {'block_index': block, 'record_index': record, 'column_0based': column}


def all_cells(document):
    return tuple(cell(b['block_index'], r['record_index'], i) for b in document['blocks']
                 for r in b['records'] for i in range(len(r['sequence'])))


def toy(data, sequences=None, *, original_maps=()):
    document = native_document('synthetic-coordinate.xmfa', data)
    if sequences is None:
        return document, None
    files = [input_file(name, sequence) for name, sequence in sequences]
    inputs = {'schema_version': 'mauve_xmfa_source_inputs_v1', 'invocation': {
        'mode': 'multiple_files_concatenated', 'ordered_file_ids': [f['file_id'] for f in files],
        'evidence': evidence(b'explicit synthetic native argv', 'synthetic-argv')},
        'files': files, 'original_maps': list(original_maps)}
    return document, bind(document, inputs)


def original(file, record, start, end, *, member='original', occurrence=0, original_start=10,
             length=100, strand='+', transformation='explicit-map'):
    return {'file_id': file, 'record_id': record, 'staged_interval_0based_half_open': [start, end],
        'original_member': {'input_binding_id': 'original-input', 'member_id': member, 'occurrence_index': occurrence},
        'original_length': length, 'original_interval_0based_half_open': [original_start, original_start + end - start],
        'strand': strand, 'transformation_id': transformation,
        'evidence': evidence(b'explicit synthetic coordinate transform', 'synthetic-transform')}


def concat_case(maps=None):
    data = (b'#FormatVersion Mauve1\n#Sequence1File left.fa\n#Sequence1Format FastA\n'
            b'#Sequence2File right.fa\n#Sequence2Format FastA\n'
            b'>1:2-5 +\nCGTA\n>2:1-4 -\nCGTA\n=\n')
    if maps is None:
        maps = [original('left.fa', 'row:0', 0, 3, member='contig', occurrence=0),
                original('left.fa', 'row:1', 0, 3, member='contig', occurrence=1, original_start=1, length=8, strand='-'),
                original('right.fa', 'row:0', 0, 4, member='reverse', original_start=2, length=10, strand='-')]
    return toy(data, [('left.fa', b'>repeat\nACG\n>repeat\nTAA\n'), ('right.fa', b'>repeat\nTACG\n')], original_maps=maps)


@pytest.mark.parametrize('name,mode', [('combined.xmfa', 'single_file_entries'),
                                     ('separate.xmfa', 'multiple_files_concatenated')])
def test_every_native_cell_matches_retained_arithmetic_and_actual_source_bytes(name, mode):
    document = native_document(name); bindings = bind(document, supplied(mode))
    result = xmfa_column_coordinates(document, cells=all_cells(document), bindings=bindings)
    arithmetic = json.loads((BASE.parent / 'NATIVE_ARITHMETIC.json').read_text())
    expected = next(example for example in arithmetic['examples'] if example['fixture'] == name)
    lookup = {(b['block_index'], r['row_index']): r for b in expected['blocks'] for r in b['rows']}
    originals = {m['member_number']: m['source_sequence'] for m in bindings['members']}
    for item in result['cells']:
        bi, ri, column = item['cell'].values()
        expected_position = lookup[bi, ri]['column_positions_0based'][column]
        assert item['native_position_0based'] == expected_position
        if expected_position is not None:
            assert item['forward_symbol'].upper() == originals[item['member_number']][expected_position].upper()
            assert item['source_coordinate']['position_0based'] == expected_position
            assert item['native_position_1based'] == expected_position + 1
        else:
            assert item['source_coordinate'] is None
    # Each nucleotide in these two retained examples has exactly one native
    # placement, independently of row orientation and position within a block.
    queries = tuple({'member_number': m['member_number'], 'position_0based': p}
                    for m in bindings['members'] for p in range(m['source_length']))
    inverse = xmfa_source_positions(document, queries=queries, bindings=bindings)
    assert all(q['state'] == 'unique' and len(q['matches']) == 1 for q in inverse['queries'])
    by_cell = {tuple(x['cell'].values()): x for x in result['cells']}
    for query in inverse['queries']:
        match = by_cell[tuple(query['matches'][0].values())]
        assert (match['member_number'], match['native_position_0based']) == (query['member_number'], query['position_0based'])


def test_plus_minus_endpoints_subset_invariance_and_iupac_forward_complement():
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:2-5 -\n-A-RYN-\n>2:1-4 +\n-A-RYN-\n=\n')
    full = xmfa_column_coordinates(doc, cells=all_cells(doc), bindings=None)
    subset = (cell(0, 0, 5), cell(0, 1, 1), cell(0, 0, 1), cell(0, 0, 3))
    observed = xmfa_column_coordinates(doc, cells=subset, bindings=None)['cells']
    assert [r['native_position_0based'] for r in observed] == [1, 0, 4, 3]
    assert [r['forward_symbol'] for r in observed] == ['N', 'A', 'T', 'Y']
    indexed = {tuple(row['cell'].values()): row for row in full['cells']}
    for row in observed:
        assert row == indexed[tuple(row['cell'].values())]


def test_original_projection_splits_concat_boundaries_and_composes_strands():
    document, bindings = concat_case()
    result = xmfa_column_coordinates(document, cells=all_cells(document), bindings=bindings)
    first = result['cells'][:4]
    assert [row['source_coordinate']['record_id'] for row in first] == ['row:0', 'row:0', 'row:1', 'row:1']
    assert [row['source_coordinate']['position_0based'] for row in first] == [1, 2, 0, 1]
    assert [row['original_coordinates'][0]['position_0based'] for row in first] == [11, 12, 3, 2]
    assert [row['original_coordinates'][0]['strand'] for row in first] == ['+', '+', '-', '-']
    assert [row['original_coordinates'][0]['strand'] for row in result['cells'][4:]] == ['+'] * 4
    assert [row['original_coordinates'][0]['position_0based'] for row in result['cells'][4:]] == [2, 3, 4, 5]
    assert result['status'] == 'ok'


def test_conflicting_original_occurrence_does_not_erase_distinct_consistent_occurrence():
    maps = [original('left.fa', 'row:0', 0, 3, occurrence=0),
            original('left.fa', 'row:0', 0, 3, occurrence=0, original_start=20),
            original('left.fa', 'row:0', 0, 3, occurrence=1)]
    document, bindings = concat_case(maps)
    result = xmfa_column_coordinates(document, cells=(cell(0, 0, 0),), bindings=bindings)
    row = result['cells'][0]
    assert row['source_state'] == 'resolved'
    assert [o['original_member']['occurrence_index'] for o in row['original_coordinates']] == [1]
    assert any(d['code'] == 'xmfa_original_map_conflict' for d in result['diagnostics'])


def test_partial_original_map_reports_missing_without_inventing_coordinate():
    doc, binding = concat_case([original('left.fa', 'row:0', 0, 2)])
    result = xmfa_column_coordinates(doc, cells=(cell(0, 0, 0), cell(0, 0, 1)), bindings=binding)
    assert len(result['cells'][0]['original_coordinates']) == 1
    assert result['cells'][1]['original_coordinates'] == []
    assert any(r['role'] == 'xmfa_original_map' for r in result['requirements'])


def test_source_mismatch_keeps_literal_and_native_but_never_source_coordinates():
    document = native_document(); inputs = supplied()
    inputs['files'][0]['records'][0]['sequence'] = 'A' + inputs['files'][0]['records'][0]['sequence'][1:]
    bindings = bind(document, inputs)
    row = xmfa_column_coordinates(document, cells=(cell(1, 0, 0),), bindings=bindings)['cells'][0]
    assert row['native_position_0based'] == 0 and row['aligned_symbol'] == 'G'
    assert row['source_state'] == 'conflicting' and row['source_coordinate'] is None


def test_saved_match_flag_is_rechecked_in_both_coordinate_functions():
    document = native_document(); bindings = bind(document)
    bindings['members'][0]['source_sequence'] = 'A' + bindings['members'][0]['source_sequence'][1:]
    for function, args in ((xmfa_column_coordinates, {'cells': (cell(0, 0, 0),)}),
                           (xmfa_source_positions, {'queries': ({'member_number': 1, 'position_0based': 0},)})):
        with pytest.raises(ValueError, match='xmfa_source_checks_conflict'):
            function(document, bindings=bindings, **args)


def test_zero_empty_ragged_and_unusable_row_coordinates_keep_actual_row_boundaries():
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:1-2 +\nAC\n>2:0-0 +\n\n>3:1-1 +\nG\n>4:1-3 +\nAC\n=\n')
    result = xmfa_column_coordinates(doc, cells=(cell(0, 0, 1), cell(0, 2, 0), cell(0, 3, 0)), bindings=None)
    assert [r['state'] for r in result['cells']] == ['residue', 'residue', 'incompatible']
    assert [r['native_position_0based'] for r in result['cells']] == [1, 0, None]
    with pytest.raises(ValueError, match='cell_column_outside_record'):
        xmfa_column_coordinates(doc, cells=(cell(0, 1, 0),), bindings=None)


@pytest.mark.parametrize('tail', [b'', b'\n'])
def test_truncated_search_keeps_all_known_matches_without_claiming_unique(tail):
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:1-2 +\nAC\n=\n>1:1-2 +\nAC' + tail)
    result = xmfa_source_positions(doc, queries=({'member_number': 1, 'position_0based': 0},
        {'member_number': 1, 'position_0based': 100}), bindings=None)
    assert [q['state'] for q in result['queries']] == ['unknown', 'unknown']
    assert [len(q['matches']) for q in result['queries']] == [2, 0]
    assert all(q['search_completeness'] == 'truncated' for q in result['queries'])


def test_inverse_distinguishes_every_repeated_placement_and_none_in_document():
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:1-3 +\nACG\n=\n>1:1-3 -\nCGT\n=\n')
    result = xmfa_source_positions(doc, queries=({'member_number': 1, 'position_0based': 0},
        {'member_number': 1, 'position_0based': 3}), bindings=None)
    assert result['queries'][0]['matches'] == [cell(0, 0, 0), cell(1, 0, 2)]
    assert [q['state'] for q in result['queries']] == ['multiple', 'none_in_document']


@pytest.mark.parametrize('query', [{'member_number': 1, 'position_0based': 50},
    {'member_number': 99, 'position_0based': 0}, {'member_number': True, 'position_0based': 0},
    {'member_number': 1, 'position_0based': -1}, {'member_number': 1, 'position_0based': 0, 'extra': 0}])
def test_inverse_rejects_misuse_instead_of_returning_zero(query):
    document = native_document()
    with pytest.raises(ValueError, match='xmfa_'):
        xmfa_source_positions(document, queries=(query,), bindings=bind(document))


@pytest.mark.parametrize('cells', [(cell(0, 0, 0), cell(0, 0, 0)), (cell(6, 0, 0),),
    (cell(0, 3, 0),), (cell(0, 0, 49),), (cell(True, 0, 0),), [cell(0, 0, 0)]])
def test_cell_callers_cannot_invent_or_duplicate_positions(cells):
    with pytest.raises(ValueError, match='xmfa_'):
        xmfa_column_coordinates(native_document(), cells=cells, bindings=None)


@pytest.mark.parametrize('field,replacement', [('native_position_1based', 99), ('forward_symbol', 'A'),
    ('source_state', 'resolved'), ('aligned_symbol', 'AA'), ('state', 'gap'), ('native_position_0based', True)])
def test_detached_coordinate_validator_rejects_redundant_field_tampering(field, replacement):
    document = native_document()
    value = xmfa_column_coordinates(document, cells=(cell(0, 0, 0),), bindings=None)
    value['cells'][0][field] = replacement
    with pytest.raises(ValueError, match='xmfa_'):
        validate_xmfa_coordinates(value)


def test_saved_recalculation_is_detached_and_no_parser_acquisition_or_native_call(monkeypatch):
    document, bindings = concat_case()
    refs = all_cells(document)
    queries = ({'member_number': 1, 'position_0based': 2},)
    expected = xmfa_column_coordinates(document, cells=refs, bindings=bindings)
    inverse = xmfa_source_positions(document, queries=queries, bindings=bindings)
    saved_doc, saved_binding = json.loads(json.dumps([document, bindings]))
    before = deepcopy((saved_doc, saved_binding))
    def forbidden(*args, **kwargs):
        raise AssertionError('Acquisition, parser, and native execution disabled')
    with monkeypatch.context() as locked:
        for target, name in ((builtins, 'open'), (Path, 'open'), (Path, 'read_bytes'),
                             (socket, 'socket'), (subprocess, 'Popen')):
            locked.setattr(target, name, forbidden)
        locked.setattr('gene_annotation_episode.xmfa_formats.parse_mauve_xmfa', forbidden)
        locked.setattr('gene_annotation_episode.xmfa_sources.bind_xmfa_sources', forbidden)
        assert xmfa_column_coordinates(saved_doc, cells=refs, bindings=saved_binding) == expected
        assert xmfa_source_positions(saved_doc, queries=queries, bindings=saved_binding) == inverse
        assert validate_xmfa_coordinates(json.loads(json.dumps(expected))) == expected
        assert validate_xmfa_inverse_coordinates(json.loads(json.dumps(inverse))) == inverse
    assert (saved_doc, saved_binding) == before
    detached = validate_xmfa_coordinates(expected); detached['cells'][0]['cell']['column_0based'] = 999
    assert expected['cells'][0]['cell']['column_0based'] == 0


@pytest.mark.parametrize('native', [b'#FormatVersion Mauve1\n> 1:1-2 + comment with spaces\nAC\n=',
    b'#FormatVersion Mauve1\r\n>\t1:1-2 + comment with spaces\r\nA\r\n# intervening comment\r\nC\r\n=\r\n'])
def test_native_spacing_line_endings_comments_and_no_final_newline_preserve_coordinates(native):
    doc, _ = toy(native)
    rows = xmfa_column_coordinates(doc, cells=(cell(0, 0, 0), cell(0, 0, 1)), bindings=None)['cells']
    assert [r['native_position_0based'] for r in rows] == [0, 1]
    result = xmfa_source_positions(doc, queries=({'member_number': 1, 'position_0based': 1},), bindings=None)
    assert result['queries'][0]['state'] == 'unique'


def test_unknown_version_retains_literal_cells_without_native_coordinate_claim():
    doc, _ = toy(b'#FormatVersion Unknown\n>1:1-2 +\nAC\n=\n')
    row = xmfa_column_coordinates(doc, cells=(cell(0, 0, 0),), bindings=None)['cells'][0]
    assert row['aligned_symbol'] == 'A' and row['state'] == 'incompatible'
    assert row['native_position_0based'] is None
    inverse = xmfa_source_positions(doc, queries=({'member_number': 1, 'position_0based': 0},), bindings=None)
    assert inverse['queries'][0]['state'] == 'unknown'


def test_inverse_duplicate_native_member_records_are_all_retained_but_not_unique():
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:1-2 +\nAC\n>1:1-2 +\nAC\n=\n')
    row = xmfa_source_positions(doc, queries=({'member_number': 1, 'position_0based': 1},), bindings=None)['queries'][0]
    assert row['matches'] == [cell(0, 0, 1), cell(0, 1, 1)]
    assert row['state'] == 'unknown' and row['search_completeness'] == 'partial'


@pytest.mark.parametrize('change', ['state', 'completeness', 'duplicate', 'foreign_field', 'bool_position'])
def test_inverse_detached_validator_rejects_false_uniqueness_and_invalid_records(change):
    doc, _ = toy(b'#FormatVersion Mauve1\n>1:1-2 +\nAC\n=\n')
    result = xmfa_source_positions(doc, queries=({'member_number': 1, 'position_0based': 0},), bindings=None)
    row = result['queries'][0]
    if change == 'state': row['state'] = 'none_in_document'
    if change == 'completeness': row['search_completeness'] = 'truncated'
    if change == 'duplicate': row['matches'].append(deepcopy(row['matches'][0]))
    if change == 'foreign_field': row['extra'] = None
    if change == 'bool_position': row['position_0based'] = False
    with pytest.raises(ValueError, match='xmfa_'):
        validate_xmfa_inverse_coordinates(result)


def test_every_larger_native_coordinate_agrees_with_independent_retained_arithmetic():
    doc = native_document('simple.xmfa')
    arithmetic = json.loads((BASE.parent / 'NATIVE_ARITHMETIC.json').read_text())
    expected = next(example for example in arithmetic['examples'] if example['fixture'] == 'simple.xmfa')
    positions = {(b['block_index'], r['row_index']): r['column_positions_0based']
                 for b in expected['blocks'] for r in b['rows']}
    result = xmfa_column_coordinates(doc, cells=all_cells(doc), bindings=None)
    for row in result['cells']:
        bi, ri, column = row['cell'].values()
        assert row['native_position_0based'] == positions[bi, ri][column]
    assert {row['source_state'] for row in result['cells']} == {'missing', 'not_applicable'}
    assert len(result['requirements']) == 2


@pytest.mark.parametrize('change', ['wrong_length', 'wrong_strand', 'no_source', 'extra_field', 'conflicting_occurrence'])
def test_original_coordinate_validator_rejects_inconsistent_occurrence_records(change):
    doc, binding = concat_case()
    result = xmfa_column_coordinates(doc, cells=(cell(0, 0, 0),), bindings=binding)
    row = result['cells'][0]; mapped = row['original_coordinates'][0]
    if change == 'wrong_length': mapped['original_length'] = mapped['position_0based']
    if change == 'wrong_strand': mapped['strand'] = 'unknown'
    if change == 'no_source': row['source_coordinate'] = None
    if change == 'extra_field': mapped['confidence'] = 1
    if change == 'conflicting_occurrence':
        duplicate = deepcopy(mapped); duplicate['position_0based'] += 1; row['original_coordinates'].append(duplicate)
    with pytest.raises(ValueError, match='xmfa_'):
        validate_xmfa_coordinates(result)
