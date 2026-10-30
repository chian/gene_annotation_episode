"""Engineering fixtures only: constructed pixels/receipts are NOT native custody."""
from copy import deepcopy
import errno
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, __version__ as PILLOW_VERSION
import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_ratio_source_inputs import (
    relative_signal_source_arguments_schema, validate_relative_signal_source_selection,
    validate_relative_signal_source_extraction, read_relative_signal_source_inputs,
)

SOURCE = 'source_' + 'a' * 24
TEXT = 'source_' + 'b' * 24
VIEW = 'image_view_' + 'c' * 24
VIEW2 = 'image_view_' + 'd' * 24
FIELDS = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
    'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment', 'condition',
    'endpoint', 'normalization', 'signal_kind', 'reference_role', 'arrangement', 'signal_use')


def unknown():
    return {'status': 'unknown', 'value': None, 'witnesses': []}


def image(quote, *, ref=False, view=VIEW):
    return {'kind': 'image', 'view_ref': view, 'region': [110, 40, 180, 65] if ref else [10, 40, 80, 65], 'quote': quote}


def visual(label='0.60', denominator='1.00', *, ident='v1', kind='visual_signal_pair', state='exact', relation='supported', scale='supported', view=VIEW):
    w = image(label, view=view)
    return {'representation_id': ident, 'kind': kind, 'selection': {'reading_state': state,
        'candidates': [] if state == 'unreadable' else [{'numerator': w,
            'denominator': image(denominator, ref=True, view=view) if kind == 'visual_signal_pair' else None}],
        'fragments': [{'view_ref': view, 'region': [10, 40, 80, 65], 'raw_fragment': None}] if state == 'unreadable' else [],
        'signal_scale': {'value': scale if kind == 'visual_signal_pair' else 'not_applicable',
            'witnesses': [w] if kind == 'visual_signal_pair' and scale != 'unknown' else []}},
        'comparison_relation': {'value': relation, 'witnesses': [w] if relation != 'unknown' else []},
        'physical_measurement': unknown(), 'reference_measurement': unknown()}


def prose():
    return {'representation_id': 'p1', 'kind': 'jats_percent', 'selection': {'source_ref': TEXT,
        'section_id': 's1', 'paragraph_index': 0, 'expected_subject': 'SyntheticProtein', 'variant': 'V', 'reference_literal': 'WT levels'},
        'comparison_relation': {'value': 'supported', 'witnesses': [image('0.60')]},
        'physical_measurement': unknown(), 'reference_measurement': unknown()}


def request(rows=None):
    return {'version': 'relative_signal_source_selection_v2', 'source_ref': SOURCE,
        'comparison': {field: unknown() for field in FIELDS}, 'representations': [visual()] if rows is None else rows}


def view_callback(*, view=VIEW, fmt='PNG', frame=0, rgb=False):
    im = Image.new('L', (200, 100), 255)
    ImageDraw.Draw(im).text((10, 40), 'synthetic fixture 0.60 1.00', fill=0)
    stream = BytesIO()
    if fmt == 'TIFF':
        im.save(stream, format=fmt, save_all=True, append_images=[Image.new('L', im.size, 123)])
    else:
        im.save(stream, format=fmt)
    original = stream.getvalue()
    with Image.open(BytesIO(original)) as native:
        initial, count = native.mode, getattr(native, 'n_frames', 1)
        native.seek(frame)
        native.load()
        selected_mode = native.mode
        selected = native.convert('RGB') if rgb else native
        output = BytesIO()
        selected.save(output, format='PNG')
        display = output.getvalue()
        display_mode = selected.mode
    m = {'id': view, 'record_type': 'image_view', 'origin': 'tool', 'representation': 'selected_native_image_frame_v1',
        'source_ref': 'source_' + ('e' if view == VIEW else 'f') * 24, 'input_source_ref': SOURCE,
        'original_artifact_ref': 'artifact_' + hashlib.sha256(original).hexdigest()[:24],
        'image_artifact_ref': 'artifact_' + hashlib.sha256(display).hexdigest()[:24],
        'native_format': fmt, 'native_initial_mode': initial, 'selected_mode': selected_mode, 'display_mode': display_mode,
        'frame': frame, 'frame_count': count, 'width': 200, 'height': 100,
        'colour_conversion': 'rgb' if rgb else 'preserve', 'software': 'Pillow', 'software_version': PILLOW_VERSION,
        'geometric_transform': 'identity', 'contrast_transform': 'identity', 'orientation': 'stored_pixel_axis_no_exif_rotation'}
    return {'metadata': m, 'original_bytes': original, 'display_bytes': display, 'own_action_receipt': {
        'run_id': 'synthetic_run', 'episode_id': 'synthetic_episode', 'decision_index': 0,
        'operation_ref': 'operation_' + 'a' * 24, 'result_sha256': 'a' * 64, 'view_ref': view}}


def callbacks(*, xml=None, views=None, text=b'\xce\xbc exact words'):
    xml = xml if xml is not None else b'<article><body><sec id="s1"><p>SyntheticProtein 60% (V) of WT levels.</p></sec></body></article>'
    mapping = {VIEW: view_callback(), VIEW2: view_callback(view=VIEW2)} if views is None else views
    calls = []
    def source(ref, representation):
        calls.append(('source', ref, representation))
        content = xml if representation == 'original' else text
        return {'artifact_ref': 'artifact_' + hashlib.sha256(content).hexdigest()[:24], 'content': content}
    def view(ref):
        calls.append(('view', ref))
        return deepcopy(mapping[ref])
    return source, view, calls


def extract(selected=None, **options):
    source, view, calls = callbacks(**options)
    result = read_relative_signal_source_inputs(request() if selected is None else selected,
        read_source=source, read_view=view, evidence_origin='synthetic_fixture')
    return result, calls


def test_visual_only_mixed_percent_and_joint_pairs():
    for rows in ([visual()], [visual(kind='visual_ratio')], [visual('60%', kind='visual_percent')], [prose(), visual()]):
        out, calls = extract(request(rows))
        assert [r['ratio'] for row in out['representations'] for r in row['readings']] == [.6] * len(rows)
        assert all(row['origin'] == 'synthetic' for row in out['representations'])
        assert out['evidence_origin'] == 'synthetic_fixture'
        assert not out['sources'] if len(rows) == 1 else out['sources'][0]['source_ref'] == TEXT
        detached = validate_relative_signal_source_extraction(out)
        detached['selection']['source_ref'] = 'changed'
        assert out['selection']['source_ref'] == SOURCE
    a = visual('0.60', '2', state='ambiguous')
    a['selection']['candidates'].append({'numerator': image('0.80'), 'denominator': image('4', ref=True)})
    out, _ = extract(request([a]))
    assert [r['ratio'] for r in out['representations'][0]['readings']] == [.3, .2]


def test_schema_exact_detached_and_selection_contract():
    base = Path(__file__).resolve().parents[1]
    normative = base / 'verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_reader_070/normative'
    assert relative_signal_source_arguments_schema() == json.loads((normative / 'REQUEST_SCHEMA_008.json').read_text())
    schema = relative_signal_source_arguments_schema()
    schema['properties'].clear()
    assert relative_signal_source_arguments_schema()['properties']
    for edit in (lambda s: s.update(extra=1), lambda s: s['representations'].append(deepcopy(s['representations'][0])),
                 lambda s: s['comparison']['subject'].update(status='known', value='P'),
                 lambda s: s['representations'][0]['selection']['candidates'][0]['numerator']['region'].__setitem__(0, True),
                 lambda s: s['representations'][0]['selection']['candidates'][0]['numerator']['region'].__setitem__(0, 10.0),
                 lambda s: s['representations'][0]['selection'].update(reading_state='ambiguous')):
        selected = request()
        edit(selected)
        with pytest.raises(ExperimentalContractError):
            validate_relative_signal_source_selection(selected)


@pytest.mark.parametrize('fmt,frame,rgb', [('TIFF', 1, True), ('JPEG', 0, False), ('PNG', 0, True)])
def test_native_frame_rgb_and_jpeg(fmt, frame, rgb):
    out, _ = extract(views={VIEW: view_callback(fmt=fmt, frame=frame, rgb=rgb)})
    assert out['views'][0]['metadata']['frame'] == frame
    assert out['representations'][0]['readings'][0]['ratio'] == .6


def test_all_dependencies_before_decode_and_permission_propagates(monkeypatch):
    from gene_annotation_episode import literature_ratio_source_inputs as mod
    selected = request([visual(), visual('0.8', ident='v2', view=VIEW2), prose()])
    source, view, calls = callbacks()
    original = mod._view_bytes
    def guarded(*a):
        assert {c[1] for c in calls} == {TEXT, VIEW, VIEW2}
        return original(*a)
    monkeypatch.setattr(mod, '_view_bytes', guarded)
    read_relative_signal_source_inputs(selected, read_source=source, read_view=view, evidence_origin='synthetic_fixture')
    for error in (PermissionError(errno.EACCES, 'scope'), RuntimeError('provider bug'), ExperimentalContractError('denied', 'scope')):
        def denied(_):
            raise error
        with pytest.raises(type(error)):
            read_relative_signal_source_inputs(request(), read_source=source, read_view=denied, evidence_origin='synthetic_fixture')


@pytest.mark.parametrize('number', [errno.ENOENT, errno.EIO, errno.ETIMEDOUT])
def test_availability_is_dependency_partial(number):
    selected = request([visual(), visual('0.8', ident='v2', view=VIEW2)])
    source, view, _ = callbacks()
    def partial(ref):
        if ref == VIEW2:
            raise OSError(number, 'explicit fixture availability failure')
        return view(ref)
    out = read_relative_signal_source_inputs(selected, read_source=source, read_view=partial, evidence_origin='synthetic_fixture')
    assert out['representations'][0]['readings'][0]['ratio'] == .6
    assert out['representations'][1]['reading_state'] == 'exact'
    assert out['representations'][1]['parse_status'] == 'unavailable'


def test_utf8_exact_boundaries_and_geometry_receipt_hash_failures():
    selected = request()
    selected['comparison']['subject'] = {'status': 'known', 'value': 'fixture', 'witnesses': [
        {'kind': 'text', 'source_ref': TEXT, 'representation': 'text', 'start': 0, 'end': 2, 'quote': '\u03bc'}]}
    out, _ = extract(selected)
    assert out['comparison']['subject']['witnesses'][0]['authentication'] == 'exact_utf8_span'
    for end, quote in ((1, '\u03bc'), (2, 'x')):
        bad = deepcopy(selected)
        bad['comparison']['subject']['witnesses'][0].update(end=end, quote=quote)
        with pytest.raises(ExperimentalContractError):
            extract(bad)
    for mutate in (lambda v: v['metadata'].update(width=199), lambda v: v['metadata'].update(frame=1),
                   lambda v: v['own_action_receipt'].update(view_ref=VIEW2),
                   lambda v: v['metadata'].update(image_artifact_ref=v['metadata']['original_artifact_ref']) if v['original_bytes'] != v['display_bytes'] else v.update(display_bytes=b'bad'),
                   lambda v: v.update(extra='no'), lambda v: v.update(original_bytes=bytearray(v['original_bytes']))):
        raw = view_callback(fmt='JPEG')
        mutate(raw)
        with pytest.raises(ExperimentalContractError):
            extract(views={VIEW: raw})
    bad = request()
    bad['representations'][0]['selection']['candidates'][0]['numerator']['region'][2] = 201
    with pytest.raises(ExperimentalContractError):
        extract(bad)


def test_unreadable_ambiguous_fragments_and_jats_capability_separate():
    out, _ = extract(request([visual(state='unreadable')]))
    row = out['representations'][0]
    assert row['reading_state'] == 'unreadable' and row['parse_status'] == 'partial'
    assert row['fragments'][0]['locator']['quote'] is None
    out, _ = extract(request([prose(), visual()]), xml=b'<article><body><sec id="s1"><p>unsupported</p></sec></body></article>')
    assert out['representations'][0]['reading_state'] == 'not_applicable'
    assert out['representations'][0]['diagnostics'][0]['code'] == 'jats_expression_capability_partial'
    assert out['representations'][1]['readings'][0]['ratio'] == .6


def test_malformed_callback_none_and_same_handle_unequal_bytes_reject():
    source, _, _ = callbacks()
    with pytest.raises(ExperimentalContractError):
        read_relative_signal_source_inputs(request(), read_source=source, read_view=lambda _: None, evidence_origin='synthetic_fixture')
    raw, other = view_callback(), view_callback(view=VIEW2)
    other['metadata']['original_artifact_ref'] = raw['metadata']['original_artifact_ref']
    other['original_bytes'] = b'different'
    with pytest.raises(ExperimentalContractError, match='artifact_bytes_mismatch'):
        extract(request([visual(), visual(ident='v2', view=VIEW2)]), views={VIEW: raw, VIEW2: other})


def test_source_availability_preserves_visual_and_origin_is_explicit():
    source, view, _ = callbacks()
    def missing(ref, representation):
        raise FileNotFoundError(errno.ENOENT, 'authorized fixture bytes absent')
    out = read_relative_signal_source_inputs(request([prose(), visual()]), read_source=missing, read_view=view, evidence_origin='synthetic_fixture')
    assert out['representations'][0]['parse_status'] == 'unavailable'
    assert out['representations'][0]['reading_state'] == 'not_applicable'
    assert out['representations'][1]['readings'][0]['ratio'] == .6
    reported = read_relative_signal_source_inputs(request([prose(), visual()]), read_source=source, read_view=view, evidence_origin='reported_source')
    # This checks the API's declared propagation only; the callbacks here remain
    # engineering fixtures and do not constitute actual reported-source custody.
    assert [r['origin'] for r in reported['representations']] == ['reported', 'visual_transcription']
    assert out['representations'][0]['origin'] == 'synthetic'


def test_conflicting_interpretations_need_distinct_authenticated_witnesses():
    selected = request()
    w1, w2 = image('reference A'), image('reference B', ref=True)
    selected['comparison']['reference'] = {'status': 'conflicting', 'value': None, 'witnesses': [w1, w2]}
    row = selected['representations'][0]
    row['physical_measurement'] = {'status': 'known', 'value': 'fixture measurement', 'witnesses': [w1]}
    row['reference_measurement'] = {'status': 'conflicting', 'value': None, 'witnesses': [w1, w2]}
    out, _ = extract(selected)
    assert out['comparison']['reference']['status'] == 'conflicting'
    assert out['representations'][0]['physical_measurement']['value'] == 'fixture measurement'
    assert all(w['authentication'] == 'native_view_bytes_and_geometry' for w in out['comparison']['reference']['witnesses'])
    for field in ('comparison_relation',):
        bad = request()
        bad['representations'][0][field] = {'value': 'conflicting', 'witnesses': [w1, w1]}
        with pytest.raises(ExperimentalContractError):
            extract(bad)
    for scale in ('unknown', 'conflicting'):
        bad = request()
        bad['representations'][0]['selection']['signal_scale'] = {'value': scale, 'witnesses': [] if scale == 'unknown' else [w1, w2]}
        out, _ = extract(bad)
        assert out['representations'][0]['readings'][0]['ratio'] is None
        assert out['representations'][0]['readings'][0]['numerator']['value'] == .6
        assert out['representations'][0]['readings'][0]['diagnostics'][0]['code'] == 'signal_scale_unresolved'


def test_nomination_identity_includes_regions_even_with_equal_literals():
    row = visual(state='ambiguous')
    alternate = deepcopy(row['selection']['candidates'][0])
    alternate['numerator']['region'] = [20, 40, 90, 65]
    row['selection']['candidates'].append(alternate)
    out, _ = extract(request([row]))
    readings = out['representations'][0]['readings']
    assert [r['ratio'] for r in readings] == [.6, .6]
    assert readings[0]['source_reading_key'] != readings[1]['source_reading_key']
    from gene_annotation_episode.literature_ratio_source_calculations import populate_relative_signal_v2
    sheet = populate_relative_signal_v2(out)
    assert sheet['cells']['reported_ratio']['value'] is None
    assert not sheet['selected_roster_resolved'] and not sheet['point_candidate_set_complete']
    row['selection']['candidates'][1] = deepcopy(row['selection']['candidates'][0])
    with pytest.raises(ExperimentalContractError, match='distinct_transcription_candidates_required'):
        extract(request([row]))
