"""Saved numerical projection, separate from native calculation and custody."""
from copy import deepcopy
import builtins
import importlib
import math
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_genome_alignment_bundle_contracts as c
from gene_annotation_episode import bvbrc_genome_alignment_bundle_projection as projection
from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as facade
from test_bvbrc_genome_alignment_bundle_resolution import arguments, measurement, member, scientific_artifact, replace_native
from test_bvbrc_genome_alignment_sheet import fixture_sheet, fixture_data, all_requests, plan


CELL = {'block_index': 0, 'record_index': 0, 'column_0based': 0}


def saved_arguments(sheet, fields):
    return {'sheet': sheet, 'components': deepcopy(sheet['components']),
        'missing_requirements': tuple(sheet['requirements']), 'diagnostics': tuple(sheet['diagnostics']),
        'parameters': {'schema_version': 'bvbrc_genome_alignment_parameters_v1', 'analysis_id': sheet['analysis_id'],
            'document_slots': sheet['data']['document_slots'], 'calculation_plan': sheet['components']['calculation_plan']},
        'requested_form': c.requested_form_schema(fields)}


def replay_arguments(result, original):
    return {k: original[k] for k in ('parameters', 'requested_form')} | {
        'sheet': result['sheet'], 'components': result['components'],
        'missing_requirements': tuple(result['missing_requirements']), 'diagnostics': tuple(result['diagnostics'])}


def synthetic_original_sheet():
    """Test-only feature witness over actual source/native bytes, not C custody."""
    from gene_annotation_episode.bvbrc_genome_alignment_calculators import calculate_genome_alignment_components
    from gene_annotation_episode.bvbrc_genome_alignment_sheet import build_genome_alignment_sheet
    data = fixture_data(); inputs = data['inputs']; file = inputs['files'][0]; record = file['records'][0]
    original = {'input_binding_id': 'synthetic-feature-input', 'member_id': 'synthetic-feature', 'occurrence_index': 0}
    ev = deepcopy(file['path_evidence'])
    segment = {'segment_id': 'synthetic-segment', 'file_id': file['file_id'], 'record_id': record['record_id'],
        'feature_interval_0based_half_open': [10, 60], 'record_interval_0based_half_open': [0, 50],
        'strand': '+', 'transformation_id': 'synthetic-feature-map', 'evidence': ev}
    inputs['feature_bindings'].append({'feature': original, 'original_length': 100,
        'genome_occurrence_index': file['genome_occurrence_indices'][0], 'segments': [segment],
        'state': 'bound', 'evidence': ev, 'requirement_ids': []})
    mapping = {'file_id': file['file_id'], 'record_id': record['record_id'],
        'staged_interval_0based_half_open': [0, 50], 'original_member': original,
        'original_length': 100, 'original_interval_0based_half_open': [10, 60],
        'strand': '+', 'transformation_id': 'synthetic-feature-map', 'evidence': ev}
    inputs['original_maps'].append(mapping)
    inputs['xmfa_source_inputs']['original_maps'].append(deepcopy(mapping))
    components = calculate_genome_alignment_components(data, calculation_plan=plan(all_requests()))
    return build_genome_alignment_sheet(data=data, components=components), original


@pytest.mark.parametrize('request_id,family,field,location,expected', [
    ('anchors', 'v4_member', 'alignment_columns', dict(interval_index=0, segment_index=0, member=member()), 13),
    ('anchors', 'v4_pair', 'identity_fraction', dict(interval_index=0, segment_index=0,
        pair={'member_a': member(), 'member_b': member(1)}), None),
    ('anchors', 'v4_coverage', 'coverage_fraction', dict(member=member()), 690 / 693),
    ('backbone', 'backbone_row', 'selected_member_count', dict(row_index=0), 2),
    ('backbone', 'backbone_span', 'span_bases', dict(row_index=0, member=member(0, 'mauve_sidecar_member_0based')), 32),
    ('backbone', 'backbone_coverage', 'known_union_bases', dict(member=member(0, 'mauve_sidecar_member_0based')), 50),
    ('columns', 'bbcols_row', 'column_count', dict(row_index=0), 19),
    ('columns', 'bbcols_interval', 'union_columns', dict(native_interval_index_0based=0), 52),
    ('pairs', 'xmfa_block', 'selected_column_count', dict(block_index=0), 52),
    ('pairs', 'xmfa_site', 'canonical_count', dict(block_index=0, column_0based=0), 2),
    ('pairs', 'xmfa_symbol', 'count', dict(block_index=0, column_0based=0, symbol='T'), 1),
    ('pairs', 'xmfa_pair', 'identity_fraction', dict(block_index=0, member_a=1, member_b=2), 40 / 48),
    ('coverage', 'xmfa_coverage', 'source_length', dict(member_number=1), 50),
])
def test_numeric_families_from_real_native_saved_values(request_id, family, field, location, expected):
    args = saved_arguments(fixture_sheet(), {'value': measurement(request_id, family, field, **location)})
    result = projection.project_genome_alignment_facts(**args)
    assert result['facts']['value']['value']['value'] == expected
    assert result['facts']['value']['state'] == 'resolved'
    assert projection.validate_projected_facts(result['facts'], **args) == result['facts']


def test_saved_all_geometry_and_coordinate_projections():
    fields = {'v4': {'kind': 'v4_segment', 'request_id': 'anchors', 'interval_index': 0, 'segment_index': 0, 'member': member()},
        'span': {'kind': 'backbone_span', 'request_id': 'backbone', 'row_index': 0, 'member': member(0, 'mauve_sidecar_member_0based')},
        'interval': {'kind': 'bbcols_interval', 'request_id': 'columns', 'native_interval_index_0based': 0},
        'coverage': {'kind': 'coverage_intervals', 'request_id': 'coverage', 'member': member(1, 'mauve1_member_1based'), 'part': 'union'},
        'complement': {'kind': 'coverage_intervals', 'request_id': 'anchors', 'member': member(), 'part': 'complement'},
        **{key: {'kind': kind, 'request_id': 'cell', 'cell': CELL} for key, kind in (
            ('native', 'xmfa_native_coordinate'), ('source', 'xmfa_source_coordinate'), ('original', 'xmfa_original_coordinates'))},
        'inverse': {'kind': 'xmfa_inverse_coordinates', 'request_id': 'inverse', 'query': {'member_number': 1, 'position_0based': 49}},
        'status': {'kind': 'request_status', 'request_id': 'anchors'},
        'requirements': {'kind': 'missing_requirements', 'scope': 'all', 'request_id': None},
        'qualifications': {'kind': 'qualifications', 'scope': 'request', 'request_id': 'anchors'}}
    args = saved_arguments(fixture_sheet(), fields); result = projection.project_genome_alignment_facts(**args)
    facts = result['facts']; assert set(facts) == set(fields)
    assert facts['complement']['value']['intervals'] == [[578, 581]]
    assert facts['interval']['value']['known_union_intervals'] == [[0, 52]]
    assert facts['coverage']['value']['intervals'] == [[0, 50]]
    assert facts['native']['value']['native_position_0based'] == 49
    assert facts['native']['value']['native_strand'] == '-'
    assert facts['native']['value']['aligned_symbol'] == 'T' and facts['native']['value']['forward_symbol'] == 'A'
    assert facts['source']['value']['source_coordinate']['position_0based'] == 49
    assert c.decode_reference(facts['source']['value']['source_coordinate']['record_ref'])[0] == 'record'
    assert facts['original']['value']['original_coordinates'] == []
    assert facts['inverse']['value']['matches'] == [CELL]
    assert facts['status']['state'] == 'calculated'
    assert projection.validate_projected_facts(facts, **args) == facts


def test_original_coverage_and_original_coordinate_use_only_the_actual_saved_map():
    sheet, original = synthetic_original_sheet()
    fields = {field: measurement('coverage', 'xmfa_original_coverage', field,
        member_number=1, original_member=original) for field in ('original_length', 'known_union_bases', 'coverage_fraction')}
    fields['coordinate'] = {'kind': 'xmfa_original_coordinates', 'request_id': 'cell', 'cell': CELL}
    args = saved_arguments(sheet, fields); result = projection.project_genome_alignment_facts(**args)
    assert [result['facts'][f]['value']['value'] for f in ('original_length', 'known_union_bases', 'coverage_fraction')] == [100, 50, 0.5]
    mapped = result['facts']['coordinate']['value']['original_coordinates']
    assert len(mapped) == 1 and mapped[0]['position_0based'] == 59 and mapped[0]['original_length'] == 100
    assert c.decode_reference(mapped[0]['member_ref'])[2] == c._canonical(original)
    assert projection.requested_projection_status(result['facts'], **args) == 'ok'


def test_native_source_original_coordinates_have_distinct_completion():
    args = arguments('mauve1_xmfa', {'cell': {'kind': 'xmfa_native_coordinate', 'request_id': 'cell', 'cell': CELL}})
    native = facade.consume_bundle(**args)
    assert native['status'] == 'ok' and native['facts']['cell']['value']['native_position_0based'] == 49
    for kind in ('xmfa_source_coordinate', 'xmfa_original_coordinates'):
        args['requested_form'] = c.requested_form_schema({'cell': {'kind': kind, 'request_id': 'cell', 'cell': CELL}})
        other = facade.consume_bundle(**args)
        assert other['status'] == 'partial'
        assert other['missing_requirements'] == native['missing_requirements']


def test_absent_symbol_and_original_coverage_are_missing_not_zero_and_replay_causes_are_outside_d():
    fields = {'missing': measurement('pairs', 'xmfa_symbol', 'count', block_index=0, column_0based=0, symbol='N'),
        'original': measurement('coverage', 'xmfa_original_coverage', 'original_length', member_number=1,
            original_member={'input_binding_id': 'prospective', 'member_id': 'feature', 'occurrence_index': 0}),
        'requirements': {'kind': 'missing_requirements', 'scope': 'all', 'request_id': None},
        'qualifications': {'kind': 'qualifications', 'scope': 'all', 'request_id': None}}
    sheet = fixture_sheet(); before = deepcopy(sheet)
    args = saved_arguments(sheet, fields); result = projection.project_genome_alignment_facts(**args)
    assert result['facts']['missing']['value'] is result['facts']['original']['value'] is None
    assert len(result['missing_requirements']) == len(sheet['requirements']) + 2
    assert sheet == before
    args['missing_requirements'] = tuple(result['missing_requirements']); args['diagnostics'] = tuple(result['diagnostics'])
    assert projection.project_genome_alignment_facts(**args) == result
    assert projection.validate_projected_facts(result['facts'], **args) == result['facts']
    assert projection.requested_projection_status(result['facts'], **args) == 'partial'
    duplicate = dict(args, missing_requirements=args['missing_requirements'] + (args['missing_requirements'][-1],),
                     diagnostics=args['diagnostics'] + (args['diagnostics'][-1],))
    assert projection.project_genome_alignment_facts(**duplicate) == result
    # Stored replay envelopes still require the exact canonical report union.
    with pytest.raises(ValueError, match='saved_reports_conflict'):
        projection.validate_projected_facts(result['facts'], **duplicate)
    args['missing_requirements'] = tuple(sheet['requirements']); args['diagnostics'] = tuple(sheet['diagnostics'])
    with pytest.raises(ValueError, match='saved_reports_conflict'):
        projection.validate_projected_facts(result['facts'], **args)


def test_status_only_is_fulfilled_when_all_primary_documents_are_missing():
    args = arguments(fields={'status': {'kind': 'request_status', 'request_id': 'anchors'},
        'missing': {'kind': 'missing_requirements', 'scope': 'request', 'request_id': 'anchors'}})
    args['bundle']['artifacts'] = []
    result = facade.consume_bundle(**args)
    assert result['status'] == 'ok' and result['facts']['status']['state'] == 'missing'
    assert result['facts']['missing']


@pytest.mark.parametrize('target', ['facts', 'reference', 'component', 'plan', 'analysis', 'missing_row', 'orphan_report', 'report_conflict'])
def test_forged_saved_values_references_plan_and_reports_rejected(target):
    original = arguments(); result = facade.consume_bundle(**original); args = replay_arguments(result, original)
    facts = deepcopy(result['facts'])
    if target == 'facts': facts['native']['value']['value'] = 0
    elif target == 'reference': facts['native']['request_ref'] = c.encode_reference('request', 'other', 'anchors')
    elif target == 'component': args['components']['analysis_id'] = 'other'
    elif target == 'plan': args['parameters']['calculation_plan']['requests'][0]['request_id'] = 'other'
    elif target == 'analysis': args['parameters']['analysis_id'] = 'other'
    elif target == 'missing_row': args['sheet']['components']['outcomes'][0]['measurement']['value']['coverage'].pop()
    elif target == 'orphan_report':
        args['missing_requirements'] += ({'requirement_id': 'orphan', 'kind': 'parser_binding', 'role': None,
            'source_refs': [], 'reason_code': c.PREFIX + 'projection_target_missing'},)
    else:
        rows = list(args['missing_requirements']); rows.append(rows[0] | {'role': 'wrong'}); args['missing_requirements'] = tuple(rows)
    with pytest.raises(ValueError): projection.validate_projected_facts(facts, **args)


def test_bbcols_prospective_interval_deferred_when_document_missing_and_outside_selection_rejected_when_known():
    original = arguments('mauve_bbcols', {'i': {'kind': 'bbcols_interval', 'request_id': 'columns', 'native_interval_index_0based': 999}})
    result = facade.consume_bundle(**original)
    assert result['facts']['i']['state'] == 'missing' and result['facts']['i']['value'] is None
    original['parameters']['calculation_plan']['requests'][0]['selection'].update(row_indices=[], population_scope='selected_rows')
    original['requested_form'] = c.requested_form_schema({'i': {'kind': 'bbcols_interval', 'request_id': 'columns', 'native_interval_index_0based': 0}})
    with pytest.raises(ValueError, match='selector_outside_request'): facade.consume_bundle(**original)
    original['bundle']['artifacts'] = []
    assert facade.consume_bundle(**original)['facts']['i']['state'] == 'missing'


def forbid_replay_work(monkeypatch):
    def forbidden(*a, **k): raise AssertionError('scientific work or I/O during saved replay')
    functions = {
        'bvbrc_genome_alignment_bundle_resolution': ['consume_bundle', '_parse', 'extract_genome_alignment_inputs', 'bind_genome_alignment_artifacts', 'calculate_genome_alignment_components'],
        'bvbrc_genome_alignment_calculators': ['calculate_genome_alignment_components', '_dispatch', 'bind_xmfa_sources'],
        'mauve_v4_formats': ['parse_mauve_v4'], 'mauve_backbone_formats': ['parse_mauve_backbone', 'parse_mauve_bbcols'],
        'xmfa_formats': ['parse_mauve_xmfa'], 'mauve_v4_calculators': ['calculate_mauve_v4_segments'],
        'mauve_backbone_calculators': ['calculate_mauve_backbone_components', 'calculate_mauve_bbcols_components'],
        'xmfa_calculators': ['xmfa_alignment_components', 'xmfa_interval_coverage'],
        'xmfa_coordinates': ['xmfa_column_coordinates', 'xmfa_source_positions'],
        'xmfa_sources': ['bind_xmfa_sources', 'validate_xmfa_bindings_for_document'],
        'bvbrc_genome_alignment_inputs': ['extract_genome_alignment_inputs'],
        'bvbrc_genome_alignment_associations': ['bind_genome_alignment_artifacts'],
    }
    for name, attrs in functions.items():
        module = importlib.import_module('gene_annotation_episode.' + name)
        for attr in attrs: monkeypatch.setattr(module, attr, forbidden)
    for module, attr in ((builtins, 'open'), (Path, 'open'), (socket, 'socket'), (subprocess, 'Popen')):
        monkeypatch.setattr(module, attr, forbidden)


def test_projection_has_no_parser_extraction_source_comparison_calculation_or_io(monkeypatch):
    sheet = fixture_sheet()
    args = saved_arguments(sheet, {'source': {'kind': 'xmfa_source_coordinate', 'request_id': 'cell', 'cell': CELL},
        'number': measurement('pairs', 'xmfa_pair', 'identity_fraction', block_index=0, member_a=1, member_b=2)})
    expected = projection.project_genome_alignment_facts(**args)
    forbid_replay_work(monkeypatch)
    assert projection.project_genome_alignment_facts(**args) == expected
    assert projection.validate_projected_facts(expected['facts'], **args) == expected['facts']
    assert projection.requested_projection_status(expected['facts'], **args) == 'ok'


def test_malformed_native_symbol_is_local_incompatible_with_distinct_cause_and_saved_only_replay(monkeypatch):
    fields = {'bad': {'kind': 'xmfa_native_coordinate', 'request_id': 'cell', 'cell': CELL},
        'number': measurement('pairs', 'xmfa_block', 'selected_column_count', block_index=0),
        'source': {'kind': 'xmfa_source_coordinate', 'request_id': 'cell', 'cell': CELL},
        'original': {'kind': 'xmfa_original_coordinates', 'request_id': 'cell', 'cell': CELL},
        'requirements': {'kind': 'missing_requirements', 'scope': 'request', 'request_id': 'cell'}}
    original = arguments('mauve1_xmfa', fields); artifact = scientific_artifact(original)
    raw = original['artifact_bytes'][artifact['raw_artifact_ref']]
    replace_native(original, raw.replace(b'TAAGCCCTCCTAG', b'?AAGCCCTCCTAG', 1))
    result = facade.consume_bundle(**original); before = deepcopy(result)
    assert result['status'] == 'partial'
    assert result['facts']['bad']['state'] == 'incompatible' and result['facts']['bad']['value'] is None
    assert result['facts']['bad']['document_ref'] is not None
    assert result['facts']['number']['value']['value'] == 52
    assert result['facts']['source']['value']['source_state'] == 'not_applicable'
    assert result['facts']['original']['value']['state'] == 'incompatible'
    native = result['sheet']['data']['parsed_artifacts'][0]['document']
    assert native['blocks'][0]['records'][0]['sequence'].startswith('?')
    coordinate = next(o for o in result['components']['outcomes'] if o['request_id'] == 'cell')['measurement']['value']['cells'][0]
    assert coordinate['aligned_symbol'] == '?' and coordinate['state'] == 'incompatible'
    code = c.PREFIX + 'projection_target_incompatible'
    assert len([r for r in result['missing_requirements'] if r['reason_code'] == code]) == 1
    assert not any(r['reason_code'] == code for r in result['sheet']['requirements'])
    args = replay_arguments(result, original)
    forbid_replay_work(monkeypatch)
    assert projection.validate_projected_facts(result['facts'], **args) == result['facts']
    assert projection.requested_projection_status(result['facts'], **args) == 'partial'
    assert result == before
    # The local exception does not admit unrelated altered saved fact values.
    corrupt = deepcopy(result['facts']); corrupt['number']['value']['value'] = 0
    with pytest.raises(ValueError, match='saved_facts_conflict'):
        projection.validate_projected_facts(corrupt, **args)


@pytest.mark.parametrize('operation', ['project_genome_alignment_facts', 'validate_projected_facts', 'requested_projection_status'])
def test_strict_saved_boundary_never_recomputes_union_coverage_or_entropy(monkeypatch, operation):
    """Regression: blocked by current D/native validators; root owns the repair.

    Keep this barrier strict. Passing only the public calculator/parser barrier
    does not establish saved-only projection when validators redo arithmetic.
    """
    sheet, original = synthetic_original_sheet()
    args = saved_arguments(sheet, {'original': measurement('coverage', 'xmfa_original_coverage', 'coverage_fraction',
                                                         member_number=1, original_member=original)})
    expected = projection.project_genome_alignment_facts(**args)
    forbid_replay_work(monkeypatch)
    def forbidden(*a, **k):
        raise AssertionError('scientific numerical recomputation during saved replay')
    for name in ('mauve_v4_calculation_contracts', 'mauve_backbone_contracts', 'xmfa_calculation_contracts'):
        module = importlib.import_module('gene_annotation_episode.' + name)
        for helper in ('union_intervals', 'interval_length', 'multiplicity_bases', 'complement_intervals'):
            monkeypatch.setattr(module, helper, forbidden)
    monkeypatch.setattr(math, 'log2', forbidden)
    method = getattr(projection, operation)
    if operation == 'project_genome_alignment_facts':
        assert method(**args) == expected
    elif operation == 'validate_projected_facts':
        assert method(expected['facts'], **args) == expected['facts']
    else:
        assert method(expected['facts'], **args) == 'ok'
