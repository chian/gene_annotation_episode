"""Constructed pixels and synthetic labels only; no paper or runtime coverage."""
from copy import deepcopy
import errno
from io import BytesIO
import json
import math
from pathlib import Path
from PIL import Image
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_figure_inputs as reader
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
ROOT = Path(__file__).resolve().parents[5]
IMAGE_REF = 'source_' + 'a' * 24
TEXT_REF = 'source_' + 'b' * 24
CROP_REF = 'source_' + 'c' * 24
EXTRA_REF = 'source_' + 'd' * 24

def encode(image, fmt='PNG', **kwargs):
    stream = BytesIO()
    image.save(stream, format=fmt, **kwargs)
    return stream.getvalue()


def count_recipe(width=10, height=4, **kwargs):
    return {'roi': {'left': 0, 'top': 0, 'right': width, 'bottom': height}, 'rgb_min': [0, 0, 0], 'rgb_max': [30, 30, 30], 'minimum_row_fraction': 0.1, 'minimum_run_rows': 1, **kwargs}


def fixture(*, runs=((60, 80),), ticks=('4', '0'), unit='µmol/min', mode='RGB', size=(30, 110)):
    image = Image.new(mode, size, (255, 255, 255, 255) if mode == 'RGBA' else 255 if mode == 'L' else 'white')
    for top, bottom in runs:
        for y in range(top, bottom):
            for x in range(10, 20):
                image.putpixel((x, y), (0, 0, 0, 255) if mode == 'RGBA' else 0 if mode == 'L' else (0, 0, 0))
    labels = '<td>' + ticks[0] + '</td><td>' + ticks[1] + '</td><td>' + unit + '</td><td>linear axis</td>'
    raw = labels.encode()

    def text(quote):
        start = raw.index(b'<td>' + quote.encode() + b'</td>') + 4
        return {'kind': 'text', 'source_ref': TEXT_REF, 'representation': 'text', 'start': start, 'end': start + len(quote.encode()), 'quote': quote}

    def literal(quote):
        return {'status': 'exact', 'candidates': [text(quote)], 'fragments': []}
    arguments = {'version': 'controlled_response_rate_figure_selection_v1', 'images': [{'image_id': 'panel', 'source_ref': IMAGE_REF, 'original_source_ref': IMAGE_REF, 'mapping': None}], 'measurement': {'kind': 'linear_bar', 'image_id': 'panel', 'terminal_edge': 'lower', 'bar_selection': {'roi': {'left': 10, 'top': 5, 'right': 20, 'bottom': 105}, 'rgb_min': [0, 0, 0], 'rgb_max': [30, 30, 30], 'minimum_row_fraction': 0.5, 'minimum_run_rows': 2, 'edge_tolerance_pixels': 0.5}, 'axis': {'first': {'pixel': 20, 'tick': literal(ticks[0])}, 'second': {'pixel': 60, 'tick': literal(ticks[1])}, 'unit': literal(unit), 'scale': {'status': 'known', 'kind': 'linear', 'basis': 'source_text_literal', 'witnesses': [text('linear axis')]}}}}
    sources = {(IMAGE_REF, 'original'): {'artifact_ref': 'artifact-original', 'content': encode(image)}, (TEXT_REF, 'text'): {'artifact_ref': 'artifact-labels', 'content': raw}}
    image.close()
    return (arguments, sources)








@pytest.mark.parametrize('changes,code', [({'width': True}, 'invalid_count_dimensions'), ({'height': 0}, 'invalid_count_dimensions'), ({'rgb_bytes': bytearray(120)}, 'immutable_rgb_bytes_required'), ({'rgb_bytes': bytes(121)}, 'count_raster_length_mismatch'), ({'rgb_bytes': bytes(119)}, 'count_raster_length_mismatch')])
def test_bad_raster(changes, code):
    kwargs = {'rgb_bytes': bytes(120), 'width': 10, 'height': 4, 'selection': count_recipe(), **changes}
    with pytest.raises(ExperimentalContractError) as error:
        reader._count_bar_runs(**kwargs)
    assert error.value.code == code





@pytest.mark.parametrize('error', [ContractError('source_access_denied'), ExperimentalContractError('source_read_failed', 'authorization'), PermissionError(errno.EACCES, 'denied'), OSError(errno.EPERM, 'denied'), RuntimeError('unexpected')])
def test_caller_denial_and_unexpected_errors_precede_helpers(monkeypatch, error):
    arguments, sources = fixture()

    def callback(ref, representation):
        if ref == TEXT_REF:
            raise error
        return sources[ref, representation]

    def forbidden(*args, **kwargs):
        pytest.fail('helper called before actual callback closure was authorized')
    monkeypatch.setattr(reader, '_strict_decode', forbidden)
    monkeypatch.setattr(reader, '_Inputs', forbidden)
    monkeypatch.setattr(reader, '_count_bar_runs', forbidden)
    with pytest.raises(type(error)) as raised:
        reader.read_controlled_response_rate_figure(arguments, read_source=callback)
    assert raised.value is error

@pytest.mark.parametrize('bad', [None, {}, {'artifact_ref': 'x', 'content': bytearray()}, {'artifact_ref': '', 'content': b''}, {'artifact_ref': 'x', 'content': b'', 'extra': 1}])
def test_malformed_callback_precedes_helpers(monkeypatch, bad):
    arguments, _ = fixture()
    monkeypatch.setattr(reader, '_Inputs', lambda *a: pytest.fail('broad catch entered'))
    with pytest.raises(ExperimentalContractError):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *args: bad)



@pytest.mark.parametrize('change,code', [('quote', 'source_quote_mismatch'), ('extent', 'source_span_out_of_bounds'), ('utf8', 'source_span_utf8_boundary_required')])
def test_text_authentication_errors_propagate(change, code):
    arguments, sources = fixture()
    witness = arguments['measurement']['axis']['unit']['candidates'][0]
    if change == 'quote':
        witness['quote'] = 'nmol/min'
    elif change == 'extent':
        witness['end'] = 10000
    else:
        witness['start'] += 1
    with pytest.raises(ExperimentalContractError) as error:
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    assert error.value.code == code

def crop_fixture(*, hidden_alpha=False, transparent_outside=False):
    arguments, sources = fixture(mode='RGBA')
    with Image.open(BytesIO(sources[IMAGE_REF, 'original']['content'])) as source:
        original = source.copy()
    if hidden_alpha:
        original.putpixel((12, 65), (0, 0, 0, 0))
    if transparent_outside:
        original.putpixel((0, 0), (0, 0, 0, 0))
    with original.crop((5, 0, 25, 110)) as cropped:
        with cropped.convert('RGB') as rgb:
            cropped_bytes = encode(rgb)
    sources[IMAGE_REF, 'original']['content'] = encode(original)
    sources[CROP_REF, 'original'] = {'artifact_ref': 'artifact-crop', 'content': cropped_bytes}
    original.close()
    arguments['images'][0].update(source_ref=CROP_REF, mapping={'original_region': [5, 0, 25, 110], 'colour_conversion': 'rgb'})
    arguments['measurement']['bar_selection']['roi'].update(left=5, right=15)
    return (arguments, sources)




def test_wrong_crop_pixels_and_region_are_repairable():
    arguments, sources = crop_fixture()
    with Image.open(BytesIO(sources[CROP_REF, 'original']['content'])) as image:
        frame = image.copy()
    frame.putpixel((0, 0), (1, 2, 3))
    sources[CROP_REF, 'original']['content'] = encode(frame)
    frame.close()
    with pytest.raises(ExperimentalContractError, match='image_mapping_pixels_mismatch'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments['images'][0]['mapping']['original_region'][2] = 300
    with pytest.raises(ExperimentalContractError, match='image_region_out_of_bounds'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])











def test_partial_unit_is_repairable():
    arguments, sources = fixture(unit='µmol/min/mg')
    unit = arguments['measurement']['axis']['unit']['candidates'][0]
    unit.update(quote='µmol/min', end=unit['start'] + len('µmol/min'.encode()))
    with pytest.raises(ExperimentalContractError, match='partial_source_rate_unit'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])





@pytest.mark.parametrize('change', ['extra_root', 'extra_tick_value', 'bool_pixel', 'nan_pixel', 'infinite_tolerance', 'unknown_image', 'duplicate_image', 'empty_box', 'bad_cardinality', 'scale_without_witness', 'malformed_witness', 'injected_calibration'])
def test_malformed_requests_reject_before_callback(change):
    arguments, _ = fixture()
    measurement = arguments['measurement']
    if change == 'extra_root':
        arguments['ordinate'] = 1
    elif change == 'extra_tick_value':
        measurement['axis']['first']['value'] = 4
    elif change == 'bool_pixel':
        measurement['axis']['first']['pixel'] = True
    elif change == 'nan_pixel':
        measurement['axis']['first']['pixel'] = float('nan')
    elif change == 'infinite_tolerance':
        measurement['bar_selection']['edge_tolerance_pixels'] = math.inf
    elif change == 'unknown_image':
        measurement['image_id'] = 'missing'
    elif change == 'duplicate_image':
        arguments['images'].append(deepcopy(arguments['images'][0]))
    elif change == 'empty_box':
        measurement['bar_selection']['roi']['right'] = 10
    elif change == 'bad_cardinality':
        measurement['axis']['first']['tick']['candidates'] = []
    elif change == 'scale_without_witness':
        measurement['axis']['scale']['witnesses'] = []
    elif change == 'malformed_witness':
        measurement['axis']['first']['tick']['candidates'] = [{'kind': 'other'}]
    else:
        measurement['bar_selection']['calibration'] = {}
    with pytest.raises(ExperimentalContractError):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *a: pytest.fail('callback reached'))



def test_full_declared_dependency_closure_authorized_before_decode(monkeypatch):
    arguments, sources = fixture()
    arguments['images'].append({'image_id': 'unselected', 'source_ref': EXTRA_REF, 'original_source_ref': EXTRA_REF, 'mapping': None})
    denied = PermissionError(errno.EACCES, 'unselected declared image denied')

    def read(ref, representation):
        if ref == EXTRA_REF:
            raise denied
        return sources[ref, representation]
    monkeypatch.setattr(reader, '_strict_decode', lambda *args: pytest.fail('closure not authorized'))
    with pytest.raises(PermissionError) as error:
        reader.read_controlled_response_rate_figure(arguments, read_source=read)
    assert error.value is denied



def test_partial_numeric_tick_and_actual_geometry_reject():
    arguments, sources = fixture(ticks=('14', '0'))
    witness = arguments['measurement']['axis']['first']['tick']['candidates'][0]
    witness.update(start=witness['start'] + 1, quote='4')
    with pytest.raises(ExperimentalContractError, match='partial_source_numeric_token'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments, sources = fixture()
    arguments['measurement']['axis']['first']['pixel'] = 110
    with pytest.raises(ExperimentalContractError, match='calibration_outside_image'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments['measurement']['axis']['first']['pixel'] = 20
    arguments['measurement']['bar_selection']['roi']['right'] = 31
    with pytest.raises(ExperimentalContractError, match='invalid_count_roi_bounds'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])

def test_image_label_region_and_scale_nomination_cardinalities():
    arguments, sources = fixture()
    arguments['measurement']['axis']['first']['tick']['candidates'] = [{'kind': 'image', 'image_id': 'panel', 'region': [0, 0, 31, 5], 'quote': '4'}]
    with pytest.raises(ExperimentalContractError, match='image_region_out_of_bounds'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    for value in ('ambiguous', 'conflicting'):
        arguments, sources = fixture()
        literal = arguments['measurement']['axis']['unit']
        literal.update(status=value, candidates=literal['candidates'] * 2)
        with pytest.raises(ExperimentalContractError, match='distinct_transcription_candidates_required'):
            reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments, sources = fixture()
    scale = arguments['measurement']['axis']['scale']
    scale.update(status='conflicting', kind=None, basis='unresolved')
    with pytest.raises(ExperimentalContractError, match='distinct_scale_witnesses_required'):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])




