"""Saved D sheets: retained native bytes, explicitly synthetic C witnesses."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_genome_alignment_sheet import (
    build_genome_alignment_data, validate_genome_alignment_data,
    build_genome_alignment_sheet, validate_genome_alignment_sheet)
from gene_annotation_episode.bvbrc_genome_alignment_calculators import calculate_genome_alignment_components
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_inputs

ROOT = Path(__file__).parents[1]
VERIFY = ROOT / 'verification'
OUTPUT = VERIFY / 'tool_graders_bvbrc_genome_alignment_sheet_2026-10-25'


def read(path):
    return json.loads((VERIFY / path).read_text())


def native_examples():
    b = read('tool_graders_mauve_sidecars_2026-10-25/FILLED_EXAMPLES_001.json')
    v = read('tool_graders_mauve_v4_2026-10-25/official_small.document.json')
    vc = read('tool_graders_mauve_v4_2026-10-25/official_small.components.json')
    return b, v, vc


def synthetic_inputs(b):
    """Explicit test-only C aliases/projection; no authenticated service claim."""
    inputs = deepcopy(b['synthetic_source_inputs'])
    for member in list(inputs['member_bindings']):
        alias = deepcopy(member)
        alias['member'] = {'namespace': 'mauve1_member_1based', 'index': member['member']['index'] + 1}
        inputs['member_bindings'].append(alias)
    inputs['xmfa_source_inputs'] = {'schema_version': 'mauve_xmfa_source_inputs_v1',
        'invocation': {k: deepcopy(inputs['invocation'][k]) for k in ('mode', 'ordered_file_ids', 'evidence')},
        'files': [{k: deepcopy(f[k]) for k in ('file_id', 'native_path_token', 'artifact', 'format',
            'record_completeness', 'records')} | {'path_binding_evidence': deepcopy(f['path_evidence'])}
            for f in inputs['files']], 'original_maps': deepcopy(inputs['original_maps'])}
    return validate_genome_alignment_inputs(inputs)


def slot(sid, fmt, document=None):
    reader = {'format': fmt, 'encoding': 'ascii'}
    if fmt == 'mauve1_xmfa':
        reader.update(dialect='mauve1', alphabet='dna')
    elif fmt == 'mauve_backbone':
        reader['dialect'] = 'libmems_signed_coordinate_pairs_v1'
    elif fmt == 'mauve_bbcols':
        reader['dialect'] = 'libmems_interval_columns_members_v1'
    role = {'mauve_backbone': 'genome_alignment_backbone', 'mauve_bbcols': 'genome_alignment_bbcols'}.get(fmt, 'genome_alignment_primary')
    return {'slot_id': sid, 'role': role, 'source_ref': None if document is None else document['artifact']['source_ref'],
        'raw_artifact_ref': None if document is None else document['artifact']['raw_artifact_ref'], 'reader': reader}


def parsed(document, fmt, *, diagnostics=(), status='ok'):
    return {'artifact': deepcopy(document['artifact']), 'format': fmt, 'parse_status': status,
        'document': deepcopy(document), 'diagnostics': list(diagnostics)}


def resolution(sid, document=None, *, state=None):
    return {'slot_id': sid, 'state': state or ('missing' if document is None else 'resolved'),
        'artifact': deepcopy(document['artifact']) if document is not None else None,
        'document_id': document['document_id'] if document is not None else None,
        'candidate_artifacts': [deepcopy(document['artifact'])] if document is not None else [],
        'requirements': [], 'diagnostics': []}


def fixture_data(*, with_inputs=True, with_associations=True, include_missing=False):
    b, v, _ = native_examples()
    docs = [('v4', 'mauve_v4', v), ('backbone', 'mauve_backbone', b['backbone_document']),
            ('bbcols', 'mauve_bbcols', b['bbcols_document']), ('xmfa', 'mauve1_xmfa', b['xmfa_document'])]
    slots = [slot(sid, fmt, doc) for sid, fmt, doc in docs]
    resolutions = [resolution(sid, doc) for sid, fmt, doc in docs]
    if include_missing:
        slots.append(slot('missing', 'mauve1_xmfa')); resolutions.append(resolution('missing'))
    return build_genome_alignment_data(analysis_id='D-offline-native-example',
        original_task=b['synthetic_source_inputs']['original_task'], document_slots=tuple(slots),
        inputs=synthetic_inputs(b) if with_inputs else None,
        associations=b['synthetic_associations'] if with_associations else None,
        parsed_artifacts=tuple(parsed(doc, fmt) for sid, fmt, doc in docs),
        slot_resolutions=tuple(resolutions), requirements=(), diagnostics=())


def template(selection):
    return {k: deepcopy(v) for k, v in selection.items() if k != 'document_id'}


def plan(requests):
    return {'schema_version': 'bvbrc_genome_alignment_calculation_plan_v1', 'requests': deepcopy(requests)}


def all_requests():
    b, _, vc = native_examples()
    xs = {'population_id': 'explicit-native-columns', 'member_numbers': [1, 2, 3],
        'block_columns': [{'block_index': i, 'columns_0based': list(range(max(len(r['sequence']) for r in block['records'])))}
            for i, block in enumerate(b['xmfa_document']['blocks'])], 'completeness': 'complete', 'evidence': []}
    return [
        {'request_id': 'anchors', 'kind': 'mauve_v4_segments', 'document_slot_id': 'v4', 'selection': template(vc['selection']), 'use_inputs': False},
        {'request_id': 'backbone', 'kind': 'mauve_backbone', 'document_slot_id': 'backbone',
         'selection': template(b['backbone_k2']['selection']), 'use_inputs': True},
        {'request_id': 'columns', 'kind': 'mauve_bbcols', 'document_slot_id': 'bbcols',
         'selection': template(b['bbcols_k2']['selection']), 'xmfa_document_slot_id': 'xmfa'},
        {'request_id': 'pairs', 'kind': 'xmfa_alignment', 'document_slot_id': 'xmfa', 'selection': deepcopy(xs),
         'selected_pairs': [[1, 2], [1, 3], [2, 3]], 'case_policy': 'uppercase'},
        {'request_id': 'coverage', 'kind': 'xmfa_coverage', 'document_slot_id': 'xmfa', 'selection': deepcopy(xs),
         'basis': 'represented', 'use_source_bindings': True},
        {'request_id': 'cell', 'kind': 'xmfa_coordinates', 'document_slot_id': 'xmfa',
         'cells': [{'block_index': 0, 'record_index': 0, 'column_0based': 0}], 'use_source_bindings': True},
        {'request_id': 'inverse', 'kind': 'xmfa_inverse_coordinates', 'document_slot_id': 'xmfa',
         'queries': [{'member_number': 1, 'position_0based': 49}], 'use_source_bindings': True},
    ]


def fixture_sheet(**kwargs):
    data = fixture_data(**kwargs)
    components = calculate_genome_alignment_components(data, calculation_plan=plan(all_requests()))
    return build_genome_alignment_sheet(data=data, components=components)


def test_all_real_native_results_survive_saved_validation_and_detachment():
    sheet = fixture_sheet()
    assert validate_genome_alignment_sheet(sheet) == sheet
    assert [o['state'] for o in sheet['components']['outcomes']] == ['calculated'] * 7
    assert len(sheet['components']['source_bindings']) == 1
    detached = validate_genome_alignment_sheet(sheet)
    detached['components']['outcomes'][0]['measurement']['value']['coverage'][0]['known_union_bases']['value'] = -1
    assert sheet['components']['outcomes'][0]['measurement']['value']['coverage'][0]['known_union_bases']['value'] == 690


@pytest.mark.parametrize('field', ['analysis_id', 'original_task', 'artifact', 'resolution', 'reader', 'slot_order'])
def test_saved_data_identity_corruption_rejects(field):
    data = fixture_data()
    if field == 'analysis_id':
        data['analysis_id'] = ''
    elif field == 'original_task':
        data['original_task']['task_id'] = 'different-task'
    elif field == 'artifact':
        data['parsed_artifacts'][0]['artifact']['source_ref'] = 'different-source'
    elif field == 'resolution':
        data['slot_resolutions'][0]['document_id'] = data['slot_resolutions'][1]['document_id']
    elif field == 'reader':
        data['document_slots'][0]['reader']['encoding'] = 'utf-8'
    else:
        data['slot_resolutions'].reverse()
    with pytest.raises(ValueError):
        validate_genome_alignment_data(data)


@pytest.mark.parametrize('field', ['outcome_id', 'outcome_order', 'plan', 'selected_target', 'source_document',
    'source_record', 'source_check', 'C_witness', 'bbcols_contributor', 'bbcols_width', 'bbcols_block', 'component_analysis'])
def test_saved_cross_record_corruption_rejects(field):
    sheet = fixture_sheet(); comp = sheet['components']; outcomes = comp['outcomes']
    if field == 'outcome_id': outcomes[0]['request_id'] = 'wrong'
    elif field == 'outcome_order': outcomes.reverse()
    elif field == 'plan': comp['calculation_plan']['requests'][3]['selected_pairs'] = [[2, 3]]
    elif field == 'selected_target': outcomes[3]['measurement']['value']['blocks'][0]['record_refs'][0]['record_index'] = 2
    elif field == 'source_document': comp['source_bindings'][0]['document_id'] = outcomes[0]['document_id']
    elif field == 'source_record': comp['source_bindings'][0]['bindings']['members'][0]['components'][0]['record_id'] = 'wrong'
    elif field == 'source_check': comp['source_bindings'][0]['bindings']['source_checks'][0]['record']['block_index'] = 99
    elif field == 'C_witness': sheet['data']['associations']['bbcols_interval_joins'][0]['xmfa_block_index'] = 1
    elif field == 'bbcols_contributor': outcomes[2]['measurement']['value']['intervals'][0]['contributing_row_indices'] = []
    elif field == 'bbcols_width': outcomes[2]['measurement']['value']['rows'][0]['column_count']['value'] += 1
    elif field == 'bbcols_block': outcomes[2]['measurement']['value']['rows'][0]['xmfa_block_index'] = 1
    else: comp['analysis_id'] = 'wrong'
    with pytest.raises(ValueError):
        validate_genome_alignment_sheet(sheet)


def test_all_nested_requirements_retained_and_conflicting_ids_reject():
    from gene_annotation_episode.bvbrc_alignment_values import requirement, diagnostic
    data = fixture_data(with_inputs=False, with_associations=False)
    r = requirement('unselected-gap', kind='input_bytes', role='genome_alignment_staged_input',
        reason_code='bvbrc_genome_alignment_staged_file_missing')
    d = diagnostic(r['reason_code'], path='/unselected')
    data['slot_resolutions'][0]['requirements'] = [r]
    data['slot_resolutions'][0]['diagnostics'] = [d]
    data['requirements'] = [r]; data['diagnostics'] = [d]
    components = calculate_genome_alignment_components(data, calculation_plan=plan([all_requests()[3]]))
    assert components['requirements'] == [r]
    assert components['outcomes'][0]['requirements'] == []
    data['requirements'][0] = r | {'role': 'conflicting-role'}
    with pytest.raises(ValueError, match='requirement_identity_conflict'):
        validate_genome_alignment_data(data)


@pytest.mark.parametrize('field,bad', [('inputs', {}), ('associations', {}), ('parsed_artifacts', ({},)),
    ('slot_resolutions', ({},)), ('requirements', ({},)), ('document_slots', ({},)),
    ('parsed_artifacts', []), ('diagnostics', [None])])
def test_malformed_builder_operands_raise_contract_errors(field, bad):
    data = fixture_data()
    arguments = {k: data[k] for k in ('analysis_id', 'original_task', 'inputs', 'associations')}
    for key in ('document_slots', 'parsed_artifacts', 'slot_resolutions', 'requirements', 'diagnostics'):
        arguments[key] = tuple(data[key])
    arguments[field] = bad
    with pytest.raises(ValueError):
        build_genome_alignment_data(**arguments)


@pytest.mark.parametrize('state', ['missing', 'ambiguous', 'incompatible'])
def test_unavailable_slot_state_preserves_candidates_and_local_outcome(state):
    data = fixture_data(with_inputs=False, with_associations=False)
    selected = data['slot_resolutions'][3]
    selected['state'] = state; selected['document_id'] = None
    if state == 'ambiguous':
        selected['candidate_artifacts'].append(selected['artifact'] | {'raw_artifact_ref': 'another:bytes', 'source_ref': 'another:source'})
        selected['artifact'] = None
        data['document_slots'][3]['raw_artifact_ref'] = data['document_slots'][3]['source_ref'] = None
    comp = calculate_genome_alignment_components(data, calculation_plan=plan([all_requests()[3], all_requests()[0]]))
    assert comp['outcomes'][0]['state'] == ('incompatible' if state == 'incompatible' else 'missing')
    assert comp['outcomes'][0]['measurement'] is comp['outcomes'][0]['call'] is None
    assert comp['outcomes'][1]['state'] == 'calculated'
    assert validate_genome_alignment_data(data)['slot_resolutions'][3]['candidate_artifacts'] == selected['candidate_artifacts']


def test_two_slots_can_reference_one_parsed_document_and_one_source_snapshot():
    data = fixture_data()
    alias = deepcopy(data['document_slots'][3]); alias['slot_id'] = 'xmfa-alias'
    resolved = deepcopy(data['slot_resolutions'][3]); resolved['slot_id'] = 'xmfa-alias'
    data['document_slots'].append(alias); data['slot_resolutions'].append(resolved)
    requests = [all_requests()[4], all_requests()[4] | {'request_id': 'alias-request', 'document_slot_id': 'xmfa-alias'}]
    comp = calculate_genome_alignment_components(data, calculation_plan=plan(requests))
    assert len(comp['source_bindings']) == 1
    assert len(data['parsed_artifacts']) == 4
    assert comp['outcomes'][0]['measurement'] == comp['outcomes'][1]['measurement']


def test_matching_bytes_with_distinct_candidate_identities_stay_ambiguous():
    data = fixture_data(with_inputs=False, with_associations=False)
    selected = data['slot_resolutions'][3]
    other = selected['artifact'] | {'raw_artifact_ref': 'copy:artifact', 'source_ref': 'copy:source'}
    selected.update(state='ambiguous', artifact=None, document_id=None)
    selected['candidate_artifacts'].append(other)
    data['document_slots'][3]['source_ref'] = data['document_slots'][3]['raw_artifact_ref'] = None
    comp = calculate_genome_alignment_components(data, calculation_plan=plan([all_requests()[4]]))
    assert comp['outcomes'][0]['state'] == 'missing' and comp['source_bindings'] == []
    assert comp['outcomes'][0]['requirements'][0]['reason_code'].endswith('document_ambiguous')


def test_unknown_requirement_reference_is_rejected_without_scientific_recalculation():
    sheet = fixture_sheet()
    sheet['components']['outcomes'][0]['measurement']['value']['coverage'][0]['known_union_bases']['requirement_ids'] = ['invented']
    with pytest.raises(ValueError): validate_genome_alignment_sheet(sheet)
