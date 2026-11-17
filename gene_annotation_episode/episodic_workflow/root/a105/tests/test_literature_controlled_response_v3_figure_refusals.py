"""Linear-bar figure reader (controlled_response_rate_figure_selection_v1) refusals and partials.

The figure reader is the live graph reader every v3 graph nomination runs through
(`v3_inputs._read_graph`, `validate_controlled_response_v3_selection`). Constructed
pixels and labels only (the figure-reader test fixture); no paper, model or
native execution. One refusal or one diagnostic per test.
"""
from copy import deepcopy
from fractions import Fraction
from io import BytesIO
from PIL import Image
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_figure_inputs as reader
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_controlled_response_figure_inputs import fixture, encode, IMAGE_REF, TEXT_REF


def read(arguments, sources):
    return reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])


def refused(arguments, sources, code):
    with pytest.raises(ExperimentalContractError) as error:
        read(arguments, sources)
    assert error.value.code == code


def codes(result):
    return [d['code'] for d in result['diagnostics']]


def label(sources, cell, quote):
    """Append a constructed label cell; return a text witness on `quote` inside it."""
    raw = sources[TEXT_REF, 'text']['content']
    at = len(raw) + len('<td>'.encode()) + cell.encode().index(quote.encode())
    sources[TEXT_REF, 'text']['content'] = raw + ('<td>' + cell + '</td>').encode()
    return {'kind': 'text', 'source_ref': TEXT_REF, 'representation': 'text', 'start': at, 'end': at + len(quote.encode()), 'quote': quote}


def image_witness(quote, region=(0, 0, 10, 10)):
    return {'kind': 'image', 'image_id': 'panel', 'region': list(region), 'quote': quote}


def test_constructed_bar_reads_and_its_ordinate_is_computed_by_hand():
    # Ticks: pixel 20 -> 4, pixel 60 -> 0, slope = (0 - 4) / (60 - 20) = -1/10 per row.
    # Lower edge of the run rows 60..80: nominal row 79.5, ordinate = 4 + (79.5 - 20) * -1/10 = -1.95.
    arguments, sources = fixture()
    result = read(arguments, sources)
    pixels = result['measurement']['pixel_result']
    assert result['measurement']['reading_status'] == 'graph_digitized'
    assert reader._fraction(pixels['native_ordinate']) == Fraction(-39, 20)
    assert result['operand_projection']['value'] == -1.95


REQUESTS = {
    'unsupported_value': lambda a: a['measurement'].update(terminal_edge='middle'),
    'malformed_count_roi': lambda a: a['measurement']['bar_selection']['roi'].update(left=10.0),
    'malformed_count_rgb_bounds': lambda a: a['measurement']['bar_selection'].update(rgb_min=[0, 0, 256]),
    'invalid_count_rgb_range': lambda a: a['measurement']['bar_selection'].update(rgb_min=[40, 0, 0]),
    'invalid_count_row_fraction': lambda a: a['measurement']['bar_selection'].update(minimum_row_fraction=1.5),
    'positive_count_run_rows_required': lambda a: a['measurement']['bar_selection'].update(minimum_run_rows=0),
    'list_required-images': lambda a: a.update(images={}),
    'invalid_source_reference-image': lambda a: a['images'][0].update(source_ref='not_a_reference', original_source_ref='not_a_reference'),
    'unmapped_original_source_mismatch': lambda a: a['images'][0].update(original_source_ref='source_' + 'f' * 24),
    'nonnegative_tolerance_required': lambda a: a['measurement']['bar_selection'].update(edge_tolerance_pixels=-0.5),
    'nonnegative_pixel_required': lambda a: a['measurement']['axis']['first'].update(pixel=-1),
    'list_required-candidates': lambda a: a['measurement']['axis']['first']['tick'].update(candidates={}),
    'unreadable_has_no_candidate': lambda a: a['measurement']['axis']['first']['tick'].update(status='unreadable'),
    'list_required-scale': lambda a: a['measurement']['axis']['scale'].update(witnesses={}),
    'text_scale_witness_required': lambda a: a['measurement']['axis']['scale']['witnesses'].append(image_witness('linear axis')),
    'image_scale_witness_required': lambda a: a['measurement']['axis']['scale'].update(basis='image_episode_interpretation'),
    'unresolved_scale_contract_required': lambda a: a['measurement']['axis']['scale'].update(status='unknown'),
    'undeclared_image_id': lambda a: a['measurement']['axis']['scale'].update(basis='image_episode_interpretation', witnesses=[dict(image_witness('linear axis'), image_id='other')]),
    'invalid_source_reference-witness': lambda a: a['measurement']['axis']['scale']['witnesses'][0].update(source_ref='not_a_reference'),
}


@pytest.mark.parametrize('name', list(REQUESTS))
def test_malformed_figure_request_is_refused_before_any_source_read(name):
    arguments, sources = fixture()
    REQUESTS[name](arguments)
    calls = []

    def tracked(*key):
        calls.append(key)
        return sources[key]
    with pytest.raises(ExperimentalContractError) as error:
        reader.read_controlled_response_rate_figure(arguments, read_source=tracked)
    assert error.value.code == name.split('-')[0]
    assert calls == []


def test_source_reader_must_be_callable():
    arguments, _ = fixture()
    with pytest.raises(ExperimentalContractError, match='source_reader_required'):
        reader.read_controlled_response_rate_figure(arguments, read_source=None)


def blank(mode='RGB'):
    return Image.new(mode, (30, 110), 'white')


def two_frames():
    first, second = (blank(), blank())
    return encode(first, save_all=True, append_images=[second])


def rotated():
    exif = Image.Exif()
    exif[274] = 6
    return encode(blank(), exif=exif)


def corrupt_but_terminated():
    content = bytearray(encode(blank()))
    content[40] ^= 0xFF
    return bytes(content)


@pytest.mark.parametrize('content,code', [
    (lambda: encode(blank(), 'GIF'), 'unsupported_image_format'),
    (lambda: encode(blank().convert('P')), 'unsupported_image_mode'),
    (two_frames, 'single_frame_required'),
    (lambda: encode(blank()) + b'x', 'image_decode_failed'),
    (rotated, 'unsupported_image_orientation'),
    (lambda: b'constructed bytes that are not an image', 'image_decode_failed'),
    (corrupt_but_terminated, 'image_decode_failed'),
], ids=['gif', 'palette', 'two_frames', 'trailing_bytes', 'exif_rotation', 'not_an_image', 'corrupt_chunk'])
def test_undecodable_image_is_an_unsupported_reading_not_an_ordinate(content, code):
    arguments, sources = fixture()
    sources[IMAGE_REF, 'original']['content'] = content()
    result = read(arguments, sources)
    assert result['images'][0]['error']['code'] == code
    assert result['measurement']['reading_status'] == 'unsupported'
    assert result['operand_projection']['value'] is None and 'graph_image_unsupported' in codes(result)


def tick(arguments, witness, name='second'):
    arguments['measurement']['axis'][name]['tick'] = {'status': 'exact', 'candidates': [witness], 'fragments': []}


@pytest.mark.parametrize('cell,quote,code', [
    ('four', 'four', 'graph_tick_literal_unsupported'),
    ('1e309', '1e309', 'graph_tick_literal_numeric_range'),
], ids=['word', 'overflow'])
def test_unusable_text_tick_leaves_the_axis_uncalibrated(cell, quote, code):
    arguments, sources = fixture()
    tick(arguments, label(sources, cell, quote))
    result = read(arguments, sources)
    assert result['axis_literals']['second']['status'] == 'unsupported'
    assert code in codes(result['axis_literals']['second'])
    assert result['measurement']['reading_status'] == 'unsupported' and result['measurement']['pixel_result']['axis'] is None


@pytest.mark.parametrize('cell', ['about 9', 'approx. 9', '~9', 'ca. 9'])
def test_approximate_tick_is_read_at_its_exact_value(cell):
    # Owner decision 2026-11-16: an approximate axis tick calibrates the axis at its printed value.
    arguments, sources = fixture()
    tick(arguments, label(sources, cell, '9'))
    literal = read(arguments, sources)['axis_literals']['second']
    assert literal['status'] == 'parsed' and reader._fraction(literal['exact_value']) == 9
    assert 'graph_tick_literal_unsupported' not in codes(literal)


def test_bounded_tick_still_leaves_the_axis_uncalibrated():
    arguments, sources = fixture()
    tick(arguments, label(sources, '< 9', '9'))
    literal = read(arguments, sources)['axis_literals']['second']
    assert literal['status'] == 'unsupported' and 'graph_tick_literal_unsupported' in codes(literal)


def test_image_transcribed_tick_beyond_double_range_stays_exact_and_the_ordinate_is_unsupported():
    # An image transcription carries no source-text range diagnostic; its exact value 10^309 is kept,
    # and the ordinate computed from it (about 10^308 per row) is beyond double range.
    arguments, sources = fixture()
    tick(arguments, image_witness('1e309'))
    result = read(arguments, sources)
    literal = result['axis_literals']['second']
    assert literal['status'] == 'parsed' and reader._fraction(literal['exact_value']) == 10 ** 309
    assert literal['qualification'] == 'episode_image_transcription' and 'graph_tick_literal_numeric_range' not in codes(literal)
    assert result['measurement']['reading_status'] == 'unsupported' and 'graph_numerical_model_range' in codes(result)


def test_tick_with_digits_beyond_double_precision_is_kept_exact():
    arguments, sources = fixture()
    tick(arguments, label(sources, '4.00000000000000000001', '4.00000000000000000001'), name='first')
    literal = read(arguments, sources)['axis_literals']['first']
    assert literal['status'] == 'parsed' and reader._fraction(literal['exact_value']) == 4 + Fraction(1, 10 ** 20)
    assert 'graph_tick_projection_rounded' in codes(literal)


def test_logarithmic_axis_is_read_but_not_calibrated():
    arguments, sources = fixture()
    arguments['measurement']['axis']['scale'].update(kind='logarithmic', witnesses=[label(sources, 'log axis', 'log axis')])
    result = read(arguments, sources)
    assert result['axis_scale']['support'] == 'literal_source_text' and 'graph_scale_unsupported' in codes(result['axis_scale'])
    assert result['measurement']['pixel_result']['axis'] is None and result['measurement']['reading_status'] == 'unsupported'


@pytest.mark.parametrize('kind', ['text', 'image'])
def test_axis_unit_with_a_power_of_ten_multiplier_is_unsupported(kind):
    arguments, sources = fixture()
    witness = label(sources, '×10^3 nmol/min', 'nmol/min') if kind == 'text' else image_witness('×10^3 nmol/min')
    arguments['measurement']['axis']['unit'] = {'status': 'exact', 'candidates': [witness], 'fragments': []}
    result = read(arguments, sources)
    assert result['measurement']['unit']['status'] == 'unsupported'
    assert codes(result['measurement']['unit']) == ['graph_axis_multiplier_unsupported']
    assert result['operand_projection']['unit'] is None and result['measurement']['reading_status'] == 'unsupported'


def test_transparent_pixel_inside_the_bar_region_stops_the_count():
    arguments, sources = fixture(mode='RGBA')
    with Image.open(BytesIO(sources[IMAGE_REF, 'original']['content'])) as source:
        frame = source.copy()
    frame.putpixel((12, 65), (0, 0, 0, 0))
    sources[IMAGE_REF, 'original']['content'] = encode(frame)
    frame.close()
    pixels = read(arguments, sources)['measurement']['pixel_result']
    assert pixels['status'] == 'unsupported' and pixels['qualifying_runs'] == []
    assert [d['code'] for d in pixels['diagnostics']] == ['graph_nonopaque_roi']


def test_bar_reaching_the_terminal_edge_of_the_region_is_unreadable():
    arguments, sources = fixture(runs=((60, 105),))
    pixels = read(arguments, sources)['measurement']['pixel_result']
    assert pixels['status'] == 'unreadable' and pixels['pixel_edge'] is None
    assert [d['code'] for d in pixels['diagnostics']] == ['graph_terminal_edge_clipped']


def test_bar_clipped_on_its_opposite_edge_is_still_measured_with_a_qualification():
    # Lower terminal edge row 79.5 is unchanged: ordinate 4 + (79.5 - 20) * -1/10 = -1.95.
    arguments, sources = fixture(runs=((5, 80),))
    result = read(arguments, sources)
    pixels = result['measurement']['pixel_result']
    assert pixels['status'] == 'measured' and 'graph_opposite_edge_clipped' in [d['code'] for d in pixels['diagnostics']]
    assert result['operand_projection']['value'] == -1.95


def test_two_ticks_at_one_pixel_give_no_axis():
    arguments, sources = fixture()
    arguments['measurement']['axis']['second']['pixel'] = 20
    pixels = read(arguments, sources)['measurement']['pixel_result']
    assert pixels['status'] == 'unsupported' and pixels['axis'] is None
    assert 'graph_axis_degenerate' in [d['code'] for d in pixels['diagnostics']]


def test_ordinate_that_is_not_a_double_is_rounded_with_a_diagnostic():
    # Ticks at pixels 20 -> 4 and 50 -> 0: slope -4/30 = -2/15; ordinate at row 79.5 is
    # 4 - 59.5 * 2/15 = -59/15, which has no exact double.
    arguments, sources = fixture()
    arguments['measurement']['axis']['second']['pixel'] = 50
    result = read(arguments, sources)
    assert reader._fraction(result['measurement']['pixel_result']['native_ordinate']) == Fraction(-59, 15)
    assert result['operand_projection']['value'] == float(Fraction(-59, 15))
    assert 'graph_ordinate_projection_rounded' in codes(result)
