"""Native numerical answers and saved recalculation/replay barriers for D."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
from unittest.mock import patch

import pytest

from gene_annotation_episode.bvbrc_genome_alignment_calculators import (
    calculate_genome_alignment_components, recalculate_genome_alignment_sheet)
from gene_annotation_episode.bvbrc_genome_alignment_sheet import (
    build_genome_alignment_sheet, build_genome_alignment_data, validate_genome_alignment_sheet)
from test_bvbrc_genome_alignment_sheet import (fixture_data, fixture_sheet, all_requests, plan,
    native_examples, slot, resolution, parsed, template, read, VERIFY)


def values(comp):
    return {o['request_id']: o['measurement']['value'] for o in comp['outcomes'] if o['measurement'] is not None}


def test_actual_native_numerical_examples_and_explicit_recalculation():
    sheet = fixture_sheet(); original = deepcopy(sheet)
    measured = values(sheet['components']); b, _, vc = native_examples()
    assert measured['anchors'] == vc
    assert measured['backbone'] == b['backbone_k2']
    assert measured['columns'] == b['bbcols_k2']
    assert measured['pairs']['blocks'][0]['pairs'][0]['identity_fraction']['value'] == 40 / 48
    assert [m['known_union_bases']['value'] for m in measured['coverage']['members']] == [50, 49, 41]
    cell = measured['cell']['cells'][0]
    assert (cell['aligned_symbol'], cell['native_position_0based'], cell['native_strand'], cell['forward_symbol']) == ('T', 49, '-', 'A')
    assert cell['source_coordinate']['position_0based'] == 49 and cell['original_coordinates'] == []
    assert measured['inverse']['queries'][0]['matches'] == [{'block_index': 0, 'record_index': 0, 'column_0based': 0}]
    requests = all_requests()
    requests[1]['selection']['minimum_selected_multiplicity'] = 3
    requests[2]['selection']['minimum_selected_multiplicity'] = 3
    requests[4]['basis'] = 'cooccupied_column'
    new = recalculate_genome_alignment_sheet(sheet, calculation_plan=plan(requests)); changed = values(new['components'])
    assert changed['backbone'] == b['backbone_k3']
    assert changed['columns'] == b['bbcols_k3']
    assert [r['known_union_bases']['value'] for r in changed['coverage']['members']] == [48, 48, 18]
    assert [r['selected_coverage_fraction']['value'] for r in changed['coverage']['members']] == [48 / 50, 48 / 49, 18 / 41]
    assert sheet == original and new['data'] == sheet['data'] and new['data'] is not sheet['data']
    requests[4]['basis'] = 'multi_member_block'
    multi = values(recalculate_genome_alignment_sheet(sheet, calculation_plan=plan(requests))['components'])
    assert [r['known_union_bases']['value'] for r in multi['coverage']['members']] == [50, 49, 19]


def test_missing_C_and_secondary_witness_preserve_native_counts_and_global_needs():
    data = fixture_data(with_inputs=False, with_associations=False, include_missing=True)
    requests = all_requests(); requests[2]['xmfa_document_slot_id'] = 'missing'
    comp = calculate_genome_alignment_components(data, calculation_plan=plan(requests)); measured = values(comp)
    assert [o['state'] for o in comp['outcomes']] == ['calculated'] * 7
    assert measured['anchors']['coverage'][0]['coverage_fraction']['value'] == 690 / 693
    assert measured['anchors']['pair_segments'][0]['state'] == 'missing_symbols'
    assert measured['anchors']['member_segments'][0]['selected_gap_count']['value'] == 0
    assert [r['known_union_bases']['value'] for r in measured['backbone']['coverage']] == [50, 49, 19]
    assert all(r['coverage_fraction']['state'] == 'missing' for r in measured['backbone']['coverage'])
    interval = measured['columns']['intervals'][0]
    assert interval['union_columns']['value'] == 52
    assert interval['bound_block_width']['state'] == interval['selected_block_fraction']['state'] == 'missing'
    assert comp['source_bindings'] == []
    assert any(r['reason_code'].endswith('secondary_document_missing') for r in comp['requirements'])
    assert any(r['reason_code'].endswith('source_inputs_missing') for r in comp['requirements'])


IO_AND_PARSERS = ['builtins.open', 'io.open', 'os.open', 'pathlib.Path.read_bytes', 'pathlib.Path.read_text',
    'subprocess.Popen', 'socket.create_connection', 'socket.socket', 'urllib.request.urlopen',
    'gene_annotation_episode.mauve_v4_formats.parse_mauve_v4',
    'gene_annotation_episode.mauve_backbone_formats.parse_mauve_backbone',
    'gene_annotation_episode.mauve_backbone_formats.parse_mauve_bbcols',
    'gene_annotation_episode.xmfa_formats.parse_mauve_xmfa']
SCIENCE = [
    'gene_annotation_episode.mauve_v4_calculators.calculate_mauve_v4_segments',
    'gene_annotation_episode.mauve_v4_calculators._extract',
    'gene_annotation_episode.mauve_backbone_calculators.calculate_mauve_backbone_components',
    'gene_annotation_episode.mauve_backbone_calculators.calculate_mauve_bbcols_components',
    'gene_annotation_episode.xmfa_calculators.xmfa_alignment_components',
    'gene_annotation_episode.xmfa_calculators.xmfa_interval_coverage',
    'gene_annotation_episode.xmfa_calculators._entropy',
    'gene_annotation_episode.xmfa_calculators._selected_placements',
    'gene_annotation_episode.xmfa_coordinates.xmfa_column_coordinates',
    'gene_annotation_episode.xmfa_coordinates.xmfa_source_positions',
    'gene_annotation_episode.xmfa_coordinates._row_positions',
    'gene_annotation_episode.xmfa_coordinates.validate_xmfa_bindings_for_document',
    'gene_annotation_episode.xmfa_sources.bind_xmfa_sources',
    'gene_annotation_episode.xmfa_sources.validate_xmfa_bindings_for_document',
    'gene_annotation_episode.xmfa_sources._check_record',
] + ['gene_annotation_episode.bvbrc_genome_alignment_calculators.' + name for name in (
    'calculate_mauve_v4_segments', 'calculate_mauve_backbone_components', 'calculate_mauve_bbcols_components',
    'xmfa_alignment_components', 'xmfa_interval_coverage', 'xmfa_column_coordinates', 'xmfa_source_positions',
    'bind_xmfa_sources', 'calculate_genome_alignment_components')]


def forbidden(*args, **kwargs):
    raise AssertionError('forbidden acquisition/parser/scientific function at saved boundary')


def test_recalculation_without_io_or_any_native_parser():
    sheet = fixture_sheet(); requests = all_requests(); requests[4]['basis'] = 'cooccupied_column'
    # Imports/schema configuration and fixture acquisition precede this barrier.
    with ExitStack() as stack:
        for target in IO_AND_PARSERS: stack.enter_context(patch(target, forbidden))
        new = recalculate_genome_alignment_sheet(sheet, calculation_plan=plan(requests))
    assert values(new['components'])['coverage']['members'][2]['selected_coverage_fraction']['value'] == 18 / 41


def test_saved_validation_and_builder_without_scientific_recalculation():
    sheet = fixture_sheet()
    with ExitStack() as stack:
        for target in IO_AND_PARSERS + SCIENCE: stack.enter_context(patch(target, forbidden))
        assert validate_genome_alignment_sheet(sheet) == sheet
        assert build_genome_alignment_sheet(data=sheet['data'], components=sheet['components']) == sheet
        broken = deepcopy(sheet)
        broken['data']['associations']['bbcols_interval_joins'][0]['xmfa_block_index'] = 1
        with pytest.raises(ValueError): validate_genome_alignment_sheet(broken)


def one_document_data(raw, fmt, *, sid='selected'):
    from gene_annotation_episode.mauve_v4_formats import parse_mauve_v4
    from gene_annotation_episode.mauve_backbone_formats import parse_mauve_backbone, parse_mauve_bbcols
    from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
    artifact = {'raw_artifact_ref': 'synthetic:raw:' + fmt, 'source_ref': 'synthetic:source:' + fmt,
                'sha256': hashlib.sha256(raw).hexdigest()}
    reader = slot(sid, fmt)['reader']
    parsers = {'mauve_v4': parse_mauve_v4, 'mauve_backbone': parse_mauve_backbone,
               'mauve_bbcols': parse_mauve_bbcols, 'mauve1_xmfa': parse_mauve_xmfa}
    result = parsers[fmt](raw, artifact=artifact, **{k: v for k, v in reader.items() if k != 'format'})
    doc = result['value']; original = native_examples()[0]['synthetic_source_inputs']['original_task']
    return build_genome_alignment_data(analysis_id='synthetic-partial-document', original_task=original,
        document_slots=(slot(sid, fmt, doc),), inputs=None, associations=None,
        parsed_artifacts=(parsed(doc, fmt, status=result['status'], diagnostics=result['diagnostics']),),
        slot_resolutions=(resolution(sid, doc),), requirements=(), diagnostics=()), doc


def test_backbone_singleton_and_selected_good_rows_survive_unselected_malformed_row():
    raw = b'seq0_leftend seq0_rightend seq1_leftend seq1_rightend\n1 4 0 0\n5 6 1 2\n9\n'
    data, doc = one_document_data(raw, 'mauve_backbone')
    request = {'request_id': 'selected-rows', 'kind': 'mauve_backbone', 'document_slot_id': 'selected', 'use_inputs': False,
        'selection': {'schema_version': 'mauve_backbone_selection_v1', 'population_id': 'explicit-selected-rows',
        'members': [{'namespace': 'mauve_sidecar_member_0based', 'index': i} for i in [0, 1]],
        'row_indices': [0, 1], 'minimum_selected_multiplicity': 1, 'denominator': 'none',
        'population_scope': 'selected_rows', 'evidence': []}}
    first = calculate_genome_alignment_components(data, calculation_plan=plan([request]))
    assert [r['known_union_bases']['value'] for r in values(first)['selected-rows']['coverage']] == [6, 2]
    assert first['diagnostics'] and first['outcomes'][0]['measurement']['value']['status'] == 'ok'
    request['selection']['minimum_selected_multiplicity'] = 2
    second = calculate_genome_alignment_components(data, calculation_plan=plan([request]))
    assert [r['known_union_bases']['value'] for r in values(second)['selected-rows']['coverage']] == [2, 2]


def test_real_retained_native_bytes_parse_into_the_saved_D_data():
    from gene_annotation_episode.mauve_backbone_formats import parse_mauve_backbone, parse_mauve_bbcols
    from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
    b, _, _ = native_examples(); data = fixture_data()
    native = VERIFY / 'tool_graders_mauve_sidecars_2026-10-25/native_examples'
    checks = [('separate.xmfa.backbone', b['backbone_document'], parse_mauve_backbone, {'dialect': 'libmems_signed_coordinate_pairs_v1'}),
        ('separate.xmfa.bbcols', b['bbcols_document'], parse_mauve_bbcols, {'dialect': 'libmems_interval_columns_members_v1'}),
        ('separate.xmfa', b['xmfa_document'], parse_mauve_xmfa, {'dialect': 'mauve1', 'alphabet': 'dna'})]
    for name, document, parser, options in checks:
        raw = (native / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == document['artifact']['sha256']
        assert parser(raw, artifact=document['artifact'], encoding='ascii', **options)['value'] == document
    assert values(calculate_genome_alignment_components(data, calculation_plan=plan(all_requests())))['columns']['intervals'][0]['union_columns']['value'] == 52


def test_v4_retained_synthetic_reverse_overlap_source_extraction_and_denominators():
    prefix = 'tool_graders_mauve_v4_2026-10-25/'
    document = read(prefix + 'synthetic_reverse_overlap.document.json')
    expected = read(prefix + 'synthetic_reverse_overlap.components.json')
    inputs = read(prefix + 'synthetic_supplied_inputs.json')
    data = build_genome_alignment_data(analysis_id='synthetic-v4-geometry', original_task=inputs['original_task'],
        document_slots=(slot('v4', 'mauve_v4', document),), inputs=inputs, associations=None,
        parsed_artifacts=(parsed(document, 'mauve_v4'),), slot_resolutions=(resolution('v4', document),),
        requirements=(), diagnostics=())
    request = {'request_id': 'reverse-overlap', 'kind': 'mauve_v4_segments', 'document_slot_id': 'v4',
               'selection': template(expected['selection']), 'use_inputs': True}
    components = calculate_genome_alignment_components(data, calculation_plan=plan([request]))
    assert values(components)['reverse-overlap'] == expected
    member = expected['coverage'][0]
    assert [member[k]['value'] for k in ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')] == [5, 12, 4, 7]
    sheet = build_genome_alignment_sheet(data=data, components=components)
    request['use_inputs'] = False; request['selection']['denominator'] = 'native_declared_length'
    native_only = values(recalculate_genome_alignment_sheet(sheet, calculation_plan=plan([request]))['components'])['reverse-overlap']
    assert native_only['coverage'][0]['known_union_bases']['value'] == 5
    assert native_only['member_segments'][0]['symbols_origin'] == 'unavailable'
    assert native_only['pair_segments'][0]['counts']['identity_fraction']['state'] == 'missing'


def test_v4_case_ambiguity_reverse_subset_and_absent_zero_are_distinct():
    raw = (b'FormatVersion\t4\nSequenceCount\t2\nSequence0File\ta\nSequence0Length\t20\n'
        b'Sequence1File\tb\nSequence1Length\t20\nIntervalCount\t1\nInterval\t0\n'
        b'GappedAlignment\n6 -5 9\nAC-Nt-\nATGNa-\n3 0 1\n')
    data, document = one_document_data(raw, 'mauve_v4')
    members = [{'namespace': 'mauve_v4_member_0based', 'index': i} for i in [0, 1]]
    request = {'request_id': 'reverse-case', 'kind': 'mauve_v4_segments', 'document_slot_id': 'selected', 'use_inputs': False,
        'selection': {'schema_version': 'mauve_v4_selection_v1', 'population_id': 'reverse-subset', 'members': members,
            'segments': [{'interval_index': 0, 'segment_index': 0, 'column_ranges_0based_half_open': [[1, 5]]},
                         {'interval_index': 0, 'segment_index': 1, 'column_ranges_0based_half_open': [[0, 3]]}],
            'pairs': [{'member_a': members[0], 'member_b': members[1]}], 'case_policy': 'uppercase', 'denominator': 'none',
            'population_scope': 'selected_segments', 'evidence': []}}
    upper = values(calculate_genome_alignment_components(data, calculation_plan=plan([request])))['reverse-case']
    assert upper['member_segments'][0]['native_interval_0based_half_open'] == [4, 8]
    assert upper['member_segments'][0]['selected_canonical_count']['value'] == 2
    assert upper['member_segments'][0]['selected_ambiguity_count']['value'] == 1
    assert upper['member_segments'][0]['selected_gap_count']['value'] == 1
    assert upper['member_segments'][2]['state'] == 'absent_zero' and upper['member_segments'][2]['native_interval_0based_half_open'] is None
    assert upper['pair_segments'][1]['counts']['identity_fraction']['state'] == 'not_measured'
    request['selection']['case_policy'] = 'preserve'
    lower = values(calculate_genome_alignment_components(data, calculation_plan=plan([request])))['reverse-case']
    assert lower['member_segments'][0]['selected_canonical_count']['value'] == 1
    assert lower['member_segments'][0]['selected_other_count']['value'] == 1


def internal_seven_data():
    """Altered native test bytes plus explicit synthetic internal7→exported0 witness."""
    from gene_annotation_episode.mauve_backbone_formats import parse_mauve_bbcols
    data = fixture_data(); old = data['parsed_artifacts'][2]['document']; old_id = old['document_id']
    raw = (VERIFY / 'tool_graders_mauve_sidecars_2026-10-25/native_examples/separate.xmfa.bbcols').read_bytes()
    altered = b'\n'.join(b'7' + line[1:] if line else line for line in raw.split(b'\n'))
    artifact = old['artifact'] | {'sha256': hashlib.sha256(altered).hexdigest()}
    document = parse_mauve_bbcols(altered, artifact=artifact, dialect='libmems_interval_columns_members_v1', encoding='ascii')['value']
    data['parsed_artifacts'][2] = parsed(document, 'mauve_bbcols')
    data['slot_resolutions'][2] = resolution('bbcols', document)
    for assoc in data['associations']['artifacts']:
        if assoc['document_id'] == old_id:
            assoc['document_id'] = document['document_id']; assoc['artifact']['sha256'] = artifact['sha256']
    for join in data['associations']['native_member_joins']:
        if join['artifact'] == old['artifact']: join['artifact'] = deepcopy(artifact)
    for join in data['associations']['bbcols_interval_joins']:
        if join['bbcols_document_id'] == old_id:
            join['bbcols_document_id'] = document['document_id']; join['native_interval_index_0based'] = 7
    return data


@pytest.mark.parametrize('witness', ['bound', 'missing', 'conflicting'])
def test_explicit_internal_seven_to_exported_zero_not_ordinal_guess(witness):
    data = internal_seven_data()
    join = data['associations']['bbcols_interval_joins'][0]; join['state'] = witness
    if witness == 'missing': join['xmfa_document_id'] = join['xmfa_block_index'] = None
    result = values(calculate_genome_alignment_components(data, calculation_plan=plan([all_requests()[2]])))['columns']
    interval = result['intervals'][0]
    assert interval['native_interval_index_0based'] == 7 and interval['union_columns']['value'] == 52
    assert interval['selected_block_fraction']['state'] == {'bound': 'available', 'missing': 'missing', 'conflicting': 'incompatible'}[witness]
    if witness == 'bound':
        assert interval['xmfa_block_index'] == 0 and interval['bound_block_width']['value'] == 52


def original_map_data():
    data = fixture_data(); inputs = data['inputs']; file = inputs['files'][0]; record = file['records'][0]
    evidence = deepcopy(file['path_evidence'])
    occurrence = {'input_binding_id': 'synthetic:feature-binding', 'member_id': 'synthetic:feature', 'occurrence_index': 0}
    segment = {'segment_id': 'synthetic:segment', 'file_id': file['file_id'], 'record_id': record['record_id'],
        'feature_interval_0based_half_open': [10, 60], 'record_interval_0based_half_open': [0, 50],
        'strand': '+', 'transformation_id': 'synthetic:explicit-offset', 'evidence': evidence}
    inputs['feature_bindings'] = [{'feature': occurrence, 'original_length': 60, 'genome_occurrence_index': 0,
        'segments': [segment], 'state': 'bound', 'evidence': evidence, 'requirement_ids': []}]
    mapping = {'file_id': file['file_id'], 'record_id': record['record_id'], 'staged_interval_0based_half_open': [0, 50],
        'original_member': occurrence, 'original_length': 60, 'original_interval_0based_half_open': [10, 60],
        'strand': '+', 'transformation_id': segment['transformation_id'], 'evidence': evidence}
    inputs['original_maps'] = [mapping]; inputs['xmfa_source_inputs']['original_maps'] = [deepcopy(mapping)]
    return data


def test_source_and_original_mapping_are_retained_and_tied_to_saved_C():
    data = original_map_data(); comp = calculate_genome_alignment_components(data, calculation_plan=plan(all_requests()[4:]))
    measured = values(comp)
    original = measured['cell']['cells'][0]['original_coordinates'][0]
    assert (original['position_0based'], original['original_length'], original['strand']) == (59, 60, '-')
    coverage = measured['coverage']['members'][0]['original_coverage'][0]
    assert coverage['known_union_intervals'] == [[10, 60]]
    assert coverage['coverage_fraction']['value'] == 50 / 60
    saved = build_genome_alignment_sheet(data=data, components=comp)
    with ExitStack() as stack:
        for target in SCIENCE: stack.enter_context(patch(target, forbidden))
        assert validate_genome_alignment_sheet(saved) == saved
        broken = deepcopy(saved)
        broken['components']['outcomes'][1]['measurement']['value']['cells'][0]['original_coordinates'][0]['position_0based'] = 58
        with pytest.raises(ValueError, match='source_binding_conflict'): validate_genome_alignment_sheet(broken)


def test_source_mismatch_is_qualified_science_not_erasure_of_native_counts():
    data = fixture_data(); inputs = data['inputs']; old = inputs['files'][0]['records'][0]['sequence']
    changed = ('C' if old[0].upper() != 'C' else 'A') + old[1:]
    inputs['files'][0]['records'][0]['sequence'] = changed
    inputs['xmfa_source_inputs']['files'][0]['records'][0]['sequence'] = changed
    comp = calculate_genome_alignment_components(data, calculation_plan=plan([all_requests()[4]]))
    result = values(comp)['coverage']['members'][0]
    assert result['known_union_bases']['value'] == 50
    assert result['selected_coverage_fraction']['state'] == 'incompatible'
    assert any(check['state'] == 'mismatch' for check in comp['source_bindings'][0]['bindings']['source_checks'])


def test_explicit_native_only_source_flags_make_no_binding_snapshot():
    data = fixture_data(); requests = all_requests()[4:]
    for request in requests: request['use_source_bindings'] = False
    comp = calculate_genome_alignment_components(data, calculation_plan=plan(requests))
    assert comp['source_bindings'] == []
    assert values(comp)['cell']['cells'][0]['source_state'] == 'missing'
    assert values(comp)['coverage']['members'][0]['source_length']['state'] == 'missing'


def test_bbcols_explicit_nonobserved_member_is_not_invented_census_or_target_error():
    data = fixture_data(with_inputs=False, with_associations=False)
    request = all_requests()[2]
    request['selection']['members'] = [{'namespace': 'mauve_sidecar_member_0based', 'index': 99}]
    request['selection']['minimum_selected_multiplicity'] = 1
    request['selection']['calculate_bound_block_fraction'] = False
    request['xmfa_document_slot_id'] = None
    comp = calculate_genome_alignment_components(data, calculation_plan=plan([request]))
    result = values(comp)['columns']
    assert comp['outcomes'][0]['state'] == 'calculated'
    assert all(r['selected_member_count']['value'] == 0 for r in result['rows'])
    assert result['intervals'][0]['union_columns']['value'] == 0
    assert result['intervals'][0]['union_columns']['state'] == 'available'
    assert result['intervals'][0]['selected_block_fraction']['state'] == 'not_measured'


def test_empty_explicit_bbcols_rows_remain_unknown_and_not_measured_zero():
    data, doc = one_document_data(b'', 'mauve_bbcols')
    request = all_requests()[2]; request['document_slot_id'] = 'selected'
    request['selection']['row_indices'] = []; request['selection']['calculate_bound_block_fraction'] = False
    request['xmfa_document_slot_id'] = None
    comp = calculate_genome_alignment_components(data, calculation_plan=plan([request]))
    result = values(comp)['columns']
    assert doc['completeness'] == 'unknown' and result['rows'] == result['intervals'] == []
    assert result['status'] == 'partial' and result['requirements']


def test_unselected_partial_input_does_not_erase_selected_source_fractions():
    data = fixture_data(with_associations=False); inputs = data['inputs']
    inputs['files'][2]['record_completeness'] = 'partial'
    inputs['xmfa_source_inputs']['files'][2]['record_completeness'] = 'partial'
    for member in inputs['member_bindings']:
        if member['genome_occurrence_indices'] == [2]: member.update(state='unverified', source_length=None)
    request = all_requests()[4]; request['selection']['member_numbers'] = [1, 2]
    comp = calculate_genome_alignment_components(data, calculation_plan=plan([request]))
    result = values(comp)['coverage']
    assert [m['selected_coverage_fraction']['value'] for m in result['members']] == [1.0, 1.0]
    assert any(r['reason_code'] == 'xmfa_input_population_partial' for r in comp['requirements'])
    assert comp['source_bindings'][0]['bindings']['members'][2]['state'] == 'missing'


def test_valid_xmfa_cell_from_truncated_output_remains_independent():
    raw = b'#FormatVersion\tMauve1\n>1:1-2 + first\nAC\n>2:1-2 + second\nAT\n'
    data, doc = one_document_data(raw, 'mauve1_xmfa')
    request = all_requests()[5]; request['document_slot_id'] = 'selected'; request['use_source_bindings'] = False
    comp = calculate_genome_alignment_components(data, calculation_plan=plan([request]))
    row = values(comp)['cell']['cells'][0]
    assert doc['completeness'] == 'truncated'
    assert row['state'] == 'residue' and row['native_position_0based'] == 0
    assert row['source_state'] == 'missing'
    assert any(d['code'] == 'xmfa_missing_block_terminator' for d in comp['diagnostics'])
