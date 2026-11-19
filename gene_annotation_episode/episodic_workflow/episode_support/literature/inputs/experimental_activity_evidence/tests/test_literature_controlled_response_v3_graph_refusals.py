"""Saved v3 graph readings: one tampered field per test is refused with its own code.

Constructed source text and pixels only (the v3 constructed selections); no paper,
model or native execution. Each tamper starts from a graph reading the live reader
produced for the constructed bar (empty_condition0 of case 0).
"""
from copy import deepcopy as cp
from fractions import Fraction
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_v3_inputs as source
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_controlled_response_v3_inputs import Fixture
ROLES = shared.PRIMITIVE_ORDER
BAR = ROLES[3]


def read(modify=None):
    f = Fixture(0)
    if modify is not None:
        modify(f)
    return f, f.read()


def details(result):
    return cp(result['arms'][BAR]['graph_details'])


def check(f, result, graph):
    sources = {(s['source_ref'], s['representation']): s for s in result['sources']}
    return source._validate_graph(f.args['arms'][BAR]['measurement'], graph, sources=sources, images=result['images'], request=f.args)


@pytest.fixture(scope='module')
def measured():
    return read()


def test_live_bar_reading_round_trips_and_its_ordinate_follows_the_pixel_rows(measured):
    f, result = measured
    graph = details(result)
    pixels = graph['measurement']['pixel_result']
    assert graph['measurement']['reading_status'] == 'graph_digitized'
    assert len(pixels['qualifying_runs']) == 1
    top = pixels['qualifying_runs'][0]['top']
    # Calibration: pixel 200 -> 0 and pixel 0 -> 20, so slope = (20 - 0) / (0 - 200) = -1/10 per row.
    # Upper terminal edge: nominal row = top + 1/2, bounds = [top - 0.5, top + 1 + 0.5] (tolerance 0.5).
    slope = Fraction(-1, 10)
    nominal = Fraction(top) + Fraction(1, 2)
    assert shared._fraction(pixels['axis']['slope']) == slope
    assert shared._fraction(pixels['native_ordinate']) == (nominal - 200) * slope
    assert shared._fraction(pixels['native_bounds']['lower']) == (Fraction(top) + Fraction(3, 2) - 200) * slope
    assert shared._fraction(pixels['native_bounds']['upper']) == (Fraction(top) - Fraction(1, 2) - 200) * slope
    assert check(f, result, graph)['graph_details'] == graph


def tamper_runs_two(g):
    run = g['measurement']['pixel_result']['qualifying_runs'][0]
    g['measurement']['pixel_result']['qualifying_runs'] = [dict(run), {'top': run['bottom'] + 1, 'bottom': run['bottom'] + 3}]


def tamper_witness_unavailable(g):
    literal = g['axis_literals']['first']
    literal['candidates'][0].update(artifact_ref=None, byte_sha256=None, canonical_locator=None, authentication='unavailable')
    literal['status'] = 'unreadable'


TAMPERS = {
    'saved_graph_selection_mismatch': lambda g: g['selection']['measurement'].update(terminal_edge='lower'),
    'saved_graph_source_roster_mismatch': lambda g: g['sources'].append(cp(g['sources'][0])),
    'saved_graph_source_identity_mismatch': lambda g: g['sources'][0].update(byte_sha256='0' * 64),
    'saved_image_roster_mismatch': lambda g: g.update(images=[]),
    'saved_image_selection_mismatch': lambda g: g['images'][0].update(mapping={'original_region': [0, 0, 10, 10], 'colour_conversion': 'rgb'}),
    'saved_image_source_mismatch': lambda g: g['images'][0].update(artifact_ref='artifact_other'),
    'saved_image_geometry_mismatch': lambda g: g['images'][0].update(frame_count=2),
    'saved_graph_literal_selection_mismatch': lambda g: g['axis_literals']['first']['selection'].update(status='unreadable'),
    'saved_graph_literal_selection_mismatch-count': lambda g: g['axis_literals']['second'].update(candidates=[]),
    'saved_witness_identity_mismatch': lambda g: g['axis_literals']['first']['candidates'][0]['canonical_locator'].update(start=986),
    'saved_graph_literal_mismatch': lambda g: g['axis_literals']['second'].update(raw_literal='21'),
    'saved_graph_literal_mismatch-qualification': lambda g: g['axis_literals']['second'].update(qualification='episode_image_transcription'),
    'saved_graph_tick_mismatch': lambda g: g['axis_literals']['second'].update(exact_value={'numerator': '21', 'denominator': '1'}),
    'saved_graph_literal_availability_mismatch': tamper_witness_unavailable,
    'saved_graph_scale_mismatch': lambda g: g['axis_scale']['selection'].update(kind='logarithmic'),
    'saved_graph_scale_mismatch-witnesses': lambda g: g['axis_scale'].update(witnesses=[]),
    'saved_graph_scale_mismatch-support': lambda g: g['axis_scale'].update(support='episode_image_interpretation'),
    'saved_graph_scale_mismatch-kind': lambda g: g['axis_scale'].update(effective_kind='nonlinear'),
    'saved_graph_unit_mismatch': lambda g: g['measurement']['unit'].update(raw_unit='umol/min'),
    'saved_graph_unit_mismatch-scale': lambda g: g['measurement']['unit'].update(exact_scale={'numerator': '1', 'denominator': '1'}),
    'saved_graph_unit_mismatch-registry': lambda g: g['measurement']['unit'].update(native_registry_unit='umol/min'),
    'saved_graph_recipe_mismatch': lambda g: g['measurement']['pixel_result'].update(terminal_edge='lower'),
    'saved_graph_image_identity_mismatch': lambda g: g['measurement']['pixel_result'].update(image_sha256='0' * 64),
    'saved_graph_runs_mismatch': lambda g: g['measurement']['pixel_result']['qualifying_runs'][0].update(top=9),
    'saved_graph_mapping_mismatch': lambda g: g['measurement']['pixel_result']['mapped_roi']['region'].__setitem__(0, 21),
    'saved_graph_mapping_mismatch-size': lambda g: g['measurement']['pixel_result']['image_size'].update(width=101),
    'saved_graph_edge_mismatch': tamper_runs_two,
    'saved_graph_edge_mismatch-nominal': lambda g: g['measurement']['pixel_result']['pixel_edge'].update(nominal={'numerator': '1', 'denominator': '1'}),
    'saved_graph_terminal_clipping_mismatch': lambda g: g['measurement']['pixel_result']['qualifying_runs'][0].update(top=10),
    'saved_graph_calibration_mismatch': lambda g: g['measurement']['pixel_result'].update(pixel_edge=None),
    'saved_graph_ordinate_mismatch': lambda g: g['measurement']['pixel_result'].update(native_ordinate={'numerator': '1', 'denominator': '1'}),
    'saved_graph_status_mismatch': lambda g: g['measurement'].update(reading_status='ambiguous'),
    'saved_graph_projection_mismatch': lambda g: g['operand_projection'].update(approximate=False),
    'saved_graph_measurement_mismatch': lambda g: g['measurement'].update(graph_witnesses=[]),
    'saved_graph_projection_mismatch-value': lambda g: g['operand_projection'].update(value=g['operand_projection']['value'] + 1),
    'saved_graph_identity_mismatch': lambda g: g['measurement'].update(source_observation_id='controlled_response_graph_' + '0' * 64),
    'saved_graph_display_mismatch': lambda g: g['measurement']['canonical_display'].update(value=1.0),
}


@pytest.mark.parametrize('name', list(TAMPERS))
def test_one_tampered_saved_graph_field_is_refused(measured, name):
    f, result = measured
    graph = details(result)
    TAMPERS[name](graph)
    with pytest.raises(ExperimentalContractError) as error:
        check(f, result, graph)
    assert error.value.code == name.split('-')[0]


def test_saved_image_witness_region_is_checked_against_the_saved_image(measured):
    """An image-transcribed tick is bound to the retained image geometry and identity."""
    def image_tick(f):
        f.args['arms'][BAR]['measurement']['axis']['first']['tick']['candidates'] = [{'kind': 'image', 'image_id': 'constructed', 'region': [0, 195, 10, 205], 'quote': '0'}]
    f, result = read(image_tick)
    graph = details(result)
    first = graph['axis_literals']['first']
    assert first['qualification'] == 'episode_image_transcription' and first['candidates'][0]['authentication'] == 'image_bytes_and_geometry_only'
    assert check(f, result, graph)['graph_details'] == graph
    moved = cp(graph)
    moved['axis_literals']['first']['candidates'][0]['canonical_locator']['region'] = [1, 195, 11, 205]
    with pytest.raises(ExperimentalContractError, match='saved_image_identity_mismatch'):
        check(f, result, moved)
    textual = cp(graph)
    textual['axis_literals']['first']['candidates'][0]['authentication'] = 'exact_utf8_byte_span'
    with pytest.raises(ExperimentalContractError, match='saved_image_authentication_mismatch'):
        check(f, result, textual)
    narrow = cp(graph)
    narrow['images'][0]['width'] = 5
    with pytest.raises(ExperimentalContractError, match='saved_image_geometry_mismatch'):
        check(f, result, narrow)


def test_scale_phrase_must_name_the_saved_literal_kind():
    def logarithmic(f):
        f.args['arms'][BAR]['measurement']['axis']['scale']['kind'] = 'logarithmic'
    f, result = read(logarithmic)
    graph = details(result)
    assert graph['axis_scale']['support'] == 'unresolved'
    assert check(f, result, graph)['graph_details'] == graph
    graph['axis_scale'].update(support='literal_source_text', effective_kind='logarithmic')
    with pytest.raises(ExperimentalContractError, match='saved_graph_scale_literal_mismatch'):
        check(f, result, graph)


def test_pixel_bounds_outside_the_image_cannot_be_saved_as_measured():
    def wide(f):
        f.args['arms'][BAR]['measurement']['bar_selection']['edge_tolerance_pixels'] = 500
    f, result = read(wide)
    graph = details(result)
    pixels = graph['measurement']['pixel_result']
    assert pixels['status'] == 'unsupported' and pixels['pixel_edge'] is not None
    assert {'code': 'graph_pixel_bounds_outside_image', 'field': 'measurement.bar_selection.edge_tolerance_pixels', 'domain': 'reader_capability', 'source_refs': []} in pixels['diagnostics']
    assert check(f, result, graph)['graph_details'] == graph
    pixels['status'] = 'measured'
    with pytest.raises(ExperimentalContractError, match='saved_graph_calibration_mismatch'):
        check(f, result, graph)


def test_unread_bar_keeps_an_empty_projection():
    def no_bar(f):
        f.args['arms'][BAR]['measurement']['bar_selection'].update(rgb_min=[255, 0, 0], rgb_max=[255, 0, 0])
    f, result = read(no_bar)
    graph = details(result)
    assert graph['measurement']['reading_status'] == 'unreadable'
    assert graph['operand_projection']['status'] == 'missing' and graph['operand_projection']['value'] is None
    assert check(f, result, graph)['graph_details'] == graph
    graph['operand_projection']['value'] = 1.0
    with pytest.raises(ExperimentalContractError, match='saved_graph_projection_mismatch'):
        check(f, result, graph)


def test_conflicting_axis_scale_is_a_conflicting_reading_live_and_saved():
    def conflicting(f):
        scale = f.args['arms'][BAR]['measurement']['axis']['scale']
        scale.update(status='conflicting', kind=None, basis='unresolved', witnesses=[scale['witnesses'][0], f.witness('Plot unit: nmol/min.')])
    f, result = read(conflicting)
    arm = result['arms'][BAR]
    assert arm['measurement']['reading_status'] == 'conflicting'
    assert arm['graph_details']['operand_projection']['status'] == 'conflicting'
    assert arm['calculation_operand']['status'] == 'conflicting' and arm['calculation_operand']['value'] is None
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    graph = details(result)
    graph['measurement']['reading_status'] = 'unreadable'
    with pytest.raises(ExperimentalContractError, match='saved_graph_status_mismatch'):
        check(f, result, graph)


def test_saved_graph_must_be_the_measurement_saved_on_the_arm(measured):
    f, result = measured
    tampered = cp(result)
    tampered['arms'][BAR]['graph_details']['measurement']['diagnostics'] = []
    with pytest.raises(ExperimentalContractError, match='saved_graph_measurement_mismatch'):
        source.validate_controlled_response_v3_extraction(f.args, tampered)


def huge_axis(second_tick, second_pixel, unit):
    def modify(f):
        f.append('Plot huge tick: ' + second_tick + '.')
        f.append('Plot huge unit: ' + unit + '.')
        raw = f.data[f.main_ref].decode()
        axis = f.args['arms'][BAR]['measurement']['axis']
        axis['second'] = {'pixel': second_pixel, 'tick': {'status': 'exact', 'candidates': [f.witness(second_tick, start=raw.index('Plot huge tick'))], 'fragments': []}}
        axis['unit'] = {'status': 'exact', 'candidates': [f.witness(unit, start=raw.index('Plot huge unit'))], 'fragments': []}
    return modify


def test_graph_ordinate_whose_canonical_display_overflows_keeps_its_native_operand(measured):
    """Bar edge row 159.5 (measured fixture). Ticks: pixel 200 -> 0, pixel 0 -> 2e306 mmol/min.

    slope = 2e306 / (0 - 200) = -1e304 per row; ordinate = (159.5 - 200) * -1e304 = 4.05e305 mmol/min,
    a finite double; in canonical umol/min it is 4.05e308, beyond the double range (about 1.8e308).
    """
    top = measured[1]['arms'][BAR]['graph_details']['measurement']['pixel_result']['qualifying_runs'][0]['top']
    assert Fraction(top) + Fraction(1, 2) == Fraction(319, 2)
    f, result = read(huge_axis('2e306', 0, 'mmol/min'))
    graph = details(result)
    assert graph['measurement']['reading_status'] == 'graph_digitized'
    assert shared._fraction(graph['measurement']['pixel_result']['native_ordinate']) == Fraction(405, 10) * 10 ** 304
    assert graph['operand_projection']['value'] == 4.05e305 and graph['operand_projection']['unit'] == 'mmol/min'
    assert graph['measurement']['canonical_display']['value'] is None
    assert [d['code'] for d in graph['measurement']['canonical_display']['diagnostics']] == ['graph_canonical_display_range']
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result


def test_graph_ordinate_beyond_double_range_is_unsupported_live_and_saved():
    """Ticks: pixel 200 -> 0, pixel 199 -> 1e308 nmol/min; slope = -1e308 per row,
    ordinate = (159.5 - 200) * -1e308 = 4.05e309, which no double represents."""
    f, result = read(huge_axis('1e308', 199, 'nmol/min'))
    graph = details(result)
    assert graph['measurement']['pixel_result']['status'] == 'measured'
    assert graph['measurement']['reading_status'] == 'unsupported' and graph['operand_projection']['status'] == 'unsupported'
    assert 'graph_numerical_model_range' in [d['code'] for d in graph['diagnostics']]
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    graph['measurement']['reading_status'] = 'graph_digitized'
    with pytest.raises(ExperimentalContractError, match='saved_graph_status_mismatch'):
        check(f, result, graph)
