"""Numerical backbone examples; source/task bindings here are synthetic."""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.mauve_backbone_calculators import calculate_mauve_backbone_components
from gene_annotation_episode.mauve_backbone_contracts import (
    validate_mauve_backbone_components, validate_mauve_backbone_selection,
)
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_inputs
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta
from test_bvbrc_genome_alignment_input_contracts import input_fixture, original_task, content, evidence
from test_mauve_backbone_formats import backbone, selection, members, NATIVE, HEADER


def source_inputs(*, official=False, zero=False):
    v, _ = input_fixture()
    if not official:
        for i, m in enumerate(v['member_bindings']): m['member'] = members(i)[0]
        return v
    filenames = ('equCab1.fa', 'canFam2.fa', 'mm9.fa')
    v['original_task'] = original_task(['synthetic:g0', 'synthetic:g1', 'synthetic:g2'])
    v['genome_occurrences'] = [{'occurrence_index': i, 'genome_id': 'synthetic:g' + str(i),
        'parameter_pointer': '/genome_ids/' + str(i), 'input_binding_id': None, 'evidence': [evidence()]}
        for i in range(3)]
    v['files'] = []; v['member_bindings'] = []
    v['invocation']['ordered_file_ids'] = list(filenames)
    v['invocation']['observed_argv'] = ['progressiveMauve', *filenames]
    for i, name in enumerate(filenames):
        raw = (NATIVE / name).read_bytes(); b = content(raw, name)
        a = {'raw_artifact_ref': b['artifact_ref'], 'source_ref': b['source_ref'], 'sha256': b['sha256']}
        parsed = parse_aligned_fasta(raw, artifact=a, id_rule='first_whitespace_token', encoding='ascii')['value']['rows']
        records = [{'record_id': name + ':' + str(r['row_index']), 'entry_1based': r['row_index'] + 1,
            'header': r['raw_header'], 'sequence': r['sequence'], 'source_location': r['source_location']} for r in parsed]
        v['files'].append({'file_id': name, 'native_path_token': name, 'path_state': 'bound',
            'artifact': a, 'content': b, 'format': 'FastA', 'genome_occurrence_indices': [i],
            'same_run_state': 'bound', 'record_completeness': 'complete', 'records': records,
            'retrieval': {'query': None, 'requested_record_limit': None, 'reported_total_records': None,
                'returned_records': len(records), 'state': 'unknown', 'evidence': []},
            'path_evidence': [evidence()], 'same_run_evidence': [evidence()], 'requirement_ids': []})
        offset = 0; components = []
        for r in records:
            length = len(r['sequence']); components.append({'file_id': name, 'record_id': r['record_id'],
                'member_interval_0based_half_open': [offset, offset + length], 'record_interval_0based_half_open': [0, length]})
            offset += length
        v['member_bindings'].append({'member': members(i)[0], 'state': 'bound', 'genome_occurrence_indices': [i],
            'components': components, 'source_length': offset, 'evidence': [evidence()], 'requirement_ids': []})
    assert validate_genome_alignment_inputs(v) == v
    return v


def calculate(doc, **options):
    inputs = options.pop('inputs', None)
    return calculate_mauve_backbone_components(doc, selection=selection(doc, **options), inputs=inputs)


@pytest.mark.parametrize('threshold,counts', [(1, [50, 49, 19]), (2, [50, 49, 19]), (3, [18, 18, 19])])
def test_official_filled_spans_unions_and_source_fractions(threshold, counts):
    doc = backbone()['value']; sources = source_inputs(official=True)
    result = calculate(doc, threshold=threshold, denominator='validated_staged_length', inputs=sources)
    assert result['status'] == 'ok'
    coverage = result['coverage']
    assert [r['known_union_bases']['value'] for r in coverage] == counts
    assert [r['placement_bases']['value'] for r in coverage] == counts
    assert [r['denominator_bases']['value'] for r in coverage] == [50, 49, 41]
    assert [r['coverage_fraction']['value'] for r in coverage] == [n / d for n, d in zip(counts, (50, 49, 41))]
    assert [r['complement_bases']['value'] for r in coverage] == [d - n for n, d in zip(counts, (50, 49, 41))]
    assert [r['selected_member_count']['value'] for r in result['rows']] == [2, 3]
    assert result['rows'][0]['member_spans'][0]['span_bases']['value'] == 32
    assert result['rows'][0]['member_spans'][2]['state'] == 'absent_zero'
    assert result['rows'][0]['member_spans'][2]['span_bases']['value'] == 0
    assert coverage[0]['placements'][0]['strand'] == '-'
    assert sources['genome_census_state'] == 'unknown'  # staged length is not genome census


def test_selected_subset_changes_multiplicity_without_using_whole_population():
    doc = backbone()['value']
    result = calculate(doc, chosen=members(0, 2), threshold=2)
    assert [r['selected_member_count']['value'] for r in result['rows']] == [1, 2]
    assert [r['known_union_bases']['value'] for r in result['coverage']] == [18, 19]


def test_singletons_are_explicitly_selected_and_never_automatic_shared_core():
    doc = backbone(HEADER + b'1 4 0 0\n5 6 1 2\n')['value']
    single = calculate(doc, chosen=members(0, 1), threshold=1)
    shared = calculate(doc, chosen=members(0, 1), threshold=2)
    assert [r['selected_member_count']['value'] for r in single['rows']] == [1, 2]
    assert [r['known_union_bases']['value'] for r in single['coverage']] == [6, 2]
    assert [r['known_union_bases']['value'] for r in shared['coverage']] == [2, 2]


def test_overlap_repeats_and_adjacent_ranges_preserve_placement_multiplicity():
    doc = backbone(b'seq0_leftend seq0_rightend\n1 5\n-3 -7\n1 5\n8 9\n')['value']
    result = calculate(doc, chosen=members(0)); r = result['coverage'][0]
    assert len(r['placements']) == 4
    assert r['known_union_intervals'] == [[0, 9]]
    assert [r[k]['value'] for k in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')] == [9, 17, 5, 8]
    assert any(d['code'] == 'mauve_backbone_overlapping_placement' for d in result['diagnostics'])
    assert all(r[k]['state'] == 'not_measured' for k in ('denominator_bases', 'coverage_fraction', 'complement_bases'))


def test_missing_source_denominators_preserve_counts_and_requirements():
    result = calculate(backbone()['value'], denominator='validated_staged_length')
    assert [r['known_union_bases']['value'] for r in result['coverage']] == [50, 49, 19]
    assert all(r['coverage_fraction']['state'] == 'missing' and r['coverage_fraction']['value'] is None for r in result['coverage'])
    assert len(result['requirements']) == 3


def test_conflicting_source_denominator_does_not_erase_native_geometry():
    sources = source_inputs(); sources['member_bindings'][0].update(state='conflicting', source_length=None)
    doc = backbone(HEADER + b'1 4 1 4\n')['value']
    result = calculate(doc, chosen=members(0, 1), denominator='validated_staged_length', inputs=sources)
    assert result['coverage'][0]['known_union_bases']['value'] == 4
    assert result['coverage'][0]['coverage_fraction']['state'] == 'incompatible'
    assert result['coverage'][1]['coverage_fraction']['value'] == 1


def test_out_of_range_coordinates_preserve_counts_but_prevent_source_fraction():
    doc = backbone(HEADER + b'1 7 1 4\n')['value']
    result = calculate(doc, chosen=members(0, 1), denominator='validated_staged_length', inputs=source_inputs())
    r = result['coverage'][0]
    assert r['known_union_bases']['value'] == 7
    assert r['denominator_bases']['value'] == 6
    assert r['coverage_fraction']['state'] == 'incompatible' and r['complement_intervals'] is None
    assert any(d['code'] == 'bvbrc_genome_alignment_source_span_outside_input' for d in result['diagnostics'])


def test_unresolved_row_does_not_count_as_false_or_zero_and_keeps_valid_partial_work():
    doc = backbone(HEADER + b'1 4 1 4\n5 6 0 2\n')['value']
    result = calculate(doc, chosen=members(0, 1), threshold=2, denominator='validated_staged_length', inputs=source_inputs())
    assert result['rows'][1]['selected_by_multiplicity'] is None
    assert result['rows'][1]['selected_member_count']['value'] == 1
    assert result['coverage'][0]['known_union_bases']['value'] == 4
    assert result['coverage'][0]['population_state'] == 'partial_selected'
    assert result['coverage'][0]['coverage_fraction']['state'] == 'truncated'
    assert result['coverage'][0]['complement_intervals'] is None


def test_explicit_unaffected_subset_is_usable_despite_other_bad_document_row():
    doc = backbone(HEADER + b'1 4 1 4\n5 6 0 2\n')['value']
    result = calculate(doc, chosen=members(0, 1), rows=[0], all_rows=False,
        denominator='validated_staged_length', inputs=source_inputs())
    assert [r['coverage_fraction']['value'] for r in result['coverage']] == [4 / 6, 1]


def test_malformed_separately_identified_unselected_pair_does_not_block_subset_fraction():
    doc = backbone(HEADER + b'1 4 0 2\n')['value']
    result = calculate(doc, chosen=members(0), denominator='validated_staged_length', inputs=source_inputs())
    assert result['coverage'][0]['population_state'] == 'complete_selected'
    assert result['coverage'][0]['coverage_fraction']['value'] == 4 / 6
    assert result['coverage'][0]['complement_intervals'] == [[4, 6]]
    assert any(d['code'] == 'mauve_backbone_coordinate_invalid' for d in result['diagnostics'])
    assert result['requirements']


def test_unresolved_selected_header_pair_prevents_subset_fraction():
    doc = backbone(b'seq0_leftend seq0_leftend seq0_rightend seq1_leftend seq1_rightend\n1 2 4 1 4\n')['value']
    result = calculate(doc, chosen=members(0), denominator='validated_staged_length', inputs=source_inputs())
    assert result['rows'][0]['selected_by_multiplicity'] is None
    assert result['coverage'][0]['population_state'] == 'partial_selected'
    assert result['coverage'][0]['coverage_fraction']['state'] == 'truncated'
    assert result['coverage'][0]['complement_intervals'] is None


def test_complete_selected_absence_is_zero_but_unresolved_only_and_unknown_empty_are_not():
    absent = calculate(backbone(HEADER + b'0 0 0 0\n')['value'], chosen=members(0, 1))
    assert absent['coverage'][0]['known_union_bases']['value'] == 0
    malformed = calculate(backbone(HEADER + b'1 0 0 0\n')['value'], chosen=members(0, 1))
    assert malformed['coverage'][0]['known_union_bases']['state'] == 'truncated'
    assert malformed['coverage'][0]['known_union_bases']['value'] is None
    empty = calculate(backbone(HEADER)['value'], chosen=members(0, 1))
    assert empty['coverage'][0]['population_state'] == 'unknown'
    assert empty['coverage'][0]['known_union_bases']['value'] is None


def test_zero_length_input_is_zero_denominator_not_zero_fraction():
    v = source_inputs()
    f = v['files'][0]
    raw = b'>one\n>two\n'
    b = content(raw, 'zero-length-input')
    a = {'raw_artifact_ref': b['artifact_ref'], 'source_ref': b['source_ref'], 'sha256': b['sha256']}
    f.update(content=b, artifact=a)
    for index, record in enumerate(f['records']):
        record['sequence'] = ''
        record['source_location'] = {'artifact': a, 'byte_start_0based': index * 5,
            'byte_end_0based_exclusive': index * 5 + 4, 'line_start_1based': index + 1,
            'line_end_1based_inclusive': index + 1, 'xml_path': None}
    m = v['member_bindings'][0]; m['source_length'] = 0
    for component in m['components']:
        component['member_interval_0based_half_open'] = component['record_interval_0based_half_open'] = [0, 0]
    doc = backbone(HEADER + b'0 0 1 4\n')['value']
    result = calculate(doc, chosen=members(0, 1), denominator='validated_staged_length', inputs=v)
    assert result['coverage'][0]['coverage_fraction']['state'] == 'not_measured'
    assert result['coverage'][0]['coverage_fraction']['denominator'] == 0
    assert result['coverage'][0]['complement_bases']['value'] == 0


@pytest.mark.parametrize('change', ['bool_member', 'wrong_namespace', 'duplicates', 'threshold_zero', 'threshold_too_big',
    'extra_key', 'unknown_denominator', 'bool_row', 'row_duplicate'])
def test_bad_closed_selections_raise(change):
    v = selection(backbone()['value'])
    if change == 'bool_member': v['members'][0]['index'] = True
    elif change == 'wrong_namespace': v['members'][0]['namespace'] = 'mauve1_member_1based'
    elif change == 'duplicates': v['members'].append(deepcopy(v['members'][0]))
    elif change == 'threshold_zero': v['minimum_selected_multiplicity'] = 0
    elif change == 'threshold_too_big': v['minimum_selected_multiplicity'] = 4
    elif change == 'extra_key': v['complete'] = True
    elif change == 'unknown_denominator': v['denominator'] = 'genome_length'
    elif change == 'bool_row': v['row_indices'][0] = True
    else: v['row_indices'].append(0)
    with pytest.raises(ValueError, match='mauve_backbone_selection_invalid'):
        validate_mauve_backbone_selection(v)


@pytest.mark.parametrize('change,code', [('document', 'selection_document_conflict'), ('member', 'selection_member_unknown'),
    ('row', 'selection_record_unknown'), ('population', 'selection_population_incomplete')])
def test_selection_relationships_are_validated_against_actual_document(change, code):
    doc = backbone()['value']; v = selection(doc)
    if change == 'document': v['document_id'] = 'other'
    elif change == 'member': v['members'][0]['index'] = 8
    elif change == 'row': v['row_indices'] = [9]
    else: v['row_indices'] = [0]
    with pytest.raises(ValueError, match=code):
        calculate_mauve_backbone_components(doc, selection=v, inputs=None)


@pytest.mark.parametrize('change', ['wrong_count', 'wrong_union', 'wrong_sum', 'wrong_fraction', 'wrong_complement',
    'wrong_member', 'wrong_units', 'false_zero', 'lost_requirement', 'extra_key', 'bad_population'])
def test_saved_components_reject_modified_numerical_relationships(change):
    v = calculate(backbone()['value'], denominator='validated_staged_length', inputs=source_inputs(official=True))
    r = v['coverage'][0]
    if change == 'wrong_count': v['rows'][0]['selected_member_count']['value'] = 1
    elif change == 'wrong_union': r['known_union_intervals'] = [[0, 49]]
    elif change == 'wrong_sum': r['placement_bases']['value'] = 51
    elif change == 'wrong_fraction': r['coverage_fraction']['value'] = 0.5
    elif change == 'wrong_complement': r['complement_intervals'] = [[0, 1]]
    elif change == 'wrong_member': r['placements'][0]['member'] = members(2)[0]
    elif change == 'wrong_units': r['known_union_bases']['unit'] = 'confidence'
    elif change == 'false_zero': v['rows'][0]['member_spans'][2]['span_bases']['value'] = 1
    elif change == 'lost_requirement': r['coverage_fraction']['requirement_ids'] = ['missing']
    elif change == 'extra_key': r['posterior'] = 1
    else: r['population_state'] = 'partial_selected'
    with pytest.raises(ValueError, match='mauve_backbone_'):
        validate_mauve_backbone_components(v)


def forbid_io(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('saved recalculation attempted I/O or native execution')
    for owner, field in ((builtins, 'open'), (Path, 'open'), (socket, 'socket'), (socket, 'create_connection'),
                         (subprocess, 'Popen'), (subprocess, 'run')):
        monkeypatch.setattr(owner, field, forbidden)
    monkeypatch.setattr('gene_annotation_episode.mauve_backbone_formats.parse_mauve_backbone', forbidden)
    monkeypatch.setattr('gene_annotation_episode.mauve_backbone_formats.parse_mauve_bbcols', forbidden)
    monkeypatch.setattr('gene_annotation_episode.phylogeny_formats.parse_aligned_fasta', forbidden)
    return forbidden


def test_saved_data_recalculate_changed_threshold_without_io_and_validator_never_recalculates(monkeypatch):
    doc = json.loads(json.dumps(backbone()['value'])); sources = json.loads(json.dumps(source_inputs(official=True)))
    original = deepcopy(doc); sources_before = deepcopy(sources)
    first = calculate(doc, threshold=2, denominator='validated_staged_length', inputs=sources)
    forbidden = forbid_io(monkeypatch)
    second = calculate(doc, threshold=3, denominator='validated_staged_length', inputs=sources)
    assert [r['known_union_bases']['value'] for r in first['coverage']] == [50, 49, 19]
    assert [r['known_union_bases']['value'] for r in second['coverage']] == [18, 18, 19]
    monkeypatch.setattr('gene_annotation_episode.mauve_backbone_calculators.calculate_mauve_backbone_components', forbidden)
    assert validate_mauve_backbone_components(first) == first
    assert doc == original and sources == sources_before


def test_all_upstream_missing_requirements_survive_even_unrequested_denominator():
    v = source_inputs()
    v['requirements'] = [{'requirement_id': 'native-exit-unverified', 'kind': 'output_metadata',
        'role': 'genome_alignment_primary', 'source_refs': [],
        'reason_code': 'bvbrc_genome_alignment_native_execution_unverified'}]
    result = calculate(backbone(HEADER + b'1 4 1 4\n')['value'], chosen=members(0, 1), inputs=v)
    assert result['requirements'] == v['requirements']


def test_nonnull_inputs_require_exact_c_contract():
    doc = backbone()['value']
    with pytest.raises(ValueError, match='bvbrc_genome_alignment_'):
        calculate(doc, inputs={'member_bindings': []})
