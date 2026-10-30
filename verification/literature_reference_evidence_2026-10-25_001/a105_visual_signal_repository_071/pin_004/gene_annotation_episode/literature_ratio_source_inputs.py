"""Pure printed relative-signal source reader. Host authorizes actual custody.
Visual literals remain episode interpretations, never verified OCR text.
No Store/model/workflow/observation is performed here.
"""
from __future__ import annotations
from copy import deepcopy
import errno
import hashlib
from io import BytesIO
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image
from jsonschema import Draft202012Validator
from .literature_experimental_contracts import ExperimentalContractError
from .literature_prose_reader import _check_declarations, _direct_paragraph_text, _tag
from .literature_ratio_reader import _PERCENT, _contains_literal, _sentence_end, _LIMIT_PREFIX, _RANGE_PREFIX
def _build_schemas():
    """Exact008 type graph, including association, origin and text-span corrections.

    Kept local to avoid mutable public type fragments. No design-artifact import
    is required at runtime; tests independently compare all three full schemas.
    """
    def obj(fields):
        return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


    def arr(item, **extra):
        return {'type': 'array', 'items': item, **extra}


    def choice(*values):
        return {'type': 'string', 'enum': list(values)}


    def nullable(value):
        return {'anyOf': [value, {'type': 'null'}]}


    TEXT = {'type': 'string', 'minLength': 1}
    REF = {'type': 'string', 'format': 'reference'}
    NUMBER = {'type': ['number', 'null']}
    BOOL = {'type': 'boolean'}
    INDEX = {'type': 'integer', 'minimum': 0}
    BOX = {'type': 'array', 'minItems': 4, 'maxItems': 4, 'items': INDEX}
    READING = ('exact', 'ambiguous', 'unreadable', 'conflicting')
    COMPONENTS = ('reported_ratio', 'difference_from_reference', 'log_reported_ratio',
                  'calibrated_amount_ratio', 'amount_adjusted_effect', 'source_profile_log_ratio', 'source_signed_index')
    REASONS = ('no_selected_representations', 'source_dependency_unavailable', 'unreadable_transcription',
        'ambiguous_transcription', 'source_representation_conflict', 'incomplete_conflicting_representations',
        'comparison_association_unresolved', 'signal_scale_unresolved', 'unsupported_expression',
        'negative_reported_signal_unsupported', 'reported_limit_not_point', 'positive_denominator_not_established',
        'zero_reported_ratio', 'numerical_model_range', 'jats_expression_capability_partial',
        'calibrated_amount_conversion_unimplemented', 'functional_response_conversion_unimplemented',
        'observation_model_unimplemented')
    TW = obj({'kind': {'const': 'text'}, 'source_ref': REF, 'representation': choice('original', 'text'),
              'start': INDEX, 'end': {'type': 'integer', 'minimum': 1}, 'quote': TEXT})
    IW = obj({'kind': {'const': 'image'}, 'view_ref': REF, 'region': BOX, 'quote': TEXT})
    WITNESS = {'oneOf': [TW, IW]}
    FRAGMENT = obj({'view_ref': REF, 'region': BOX, 'raw_fragment': {'type': ['string', 'null']}})


    def meaning(values=None):
        value = {'type': ['string', 'null']}
        if values:
            value['enum'] = [*values, None]
        return obj({'status': choice('known', 'unknown', 'conflicting'), 'value': value,
                    'witnesses': arr(WITNESS)})


    RELATION = obj({'value': choice('supported', 'unknown', 'conflicting'), 'witnesses': arr(WITNESS)})
    COMPARISON_FIELDS = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
        'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment', 'condition',
        'endpoint', 'normalization')
    comparison = {name: meaning() for name in COMPARISON_FIELDS}
    comparison.update(signal_kind=meaning(('protein_band', 'transcript_signal', 'other_reported_signal')),
        reference_role=meaning(('tagged_wt_complementation', 'endogenous_wt', 'other_reported_reference')),
        arrangement=meaning(('single_preparation', 'replacement', 'coexistence', 'not_applicable')),
        signal_use=meaning(('experimental_comparability', 'measured_endpoint', 'other')))
    pair = obj({'numerator': IW, 'denominator': nullable(IW)})
    visual_selection = obj({'reading_state': choice(*READING), 'candidates': arr(pair), 'fragments': arr(FRAGMENT),
                            'signal_scale': RELATION})
    jats_selection = obj({'source_ref': REF, 'section_id': TEXT, 'paragraph_index': INDEX,
        'expected_subject': TEXT, 'variant': TEXT, 'reference_literal': TEXT})


    def representation(kind, selection):
        return obj({'representation_id': TEXT, 'kind': {'const': kind}, 'selection': selection,
            'comparison_relation': RELATION, 'physical_measurement': meaning(), 'reference_measurement': meaning()})


    REQUEST = obj({'version': {'const': 'relative_signal_source_selection_v2'}, 'source_ref': REF,
        'comparison': obj(comparison), 'representations': arr({'oneOf': [representation('jats_percent', jats_selection),
            *[representation(kind, visual_selection) for kind in ('visual_ratio', 'visual_percent', 'visual_signal_pair')]]})})
    RATIONAL = obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
                    'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})
    DOMAIN = obj({'lower': NUMBER, 'lower_infinite': BOOL, 'lower_closed': BOOL,
                  'upper': NUMBER, 'upper_infinite': BOOL, 'upper_closed': BOOL,
                  'meaning': {'const': 'reported_estimate_domain'}})
    JATS_LOCATOR = obj({'kind': {'const': 'jats'}, 'source_ref': REF, 'artifact_ref': REF,
        'section_id': TEXT, 'paragraph_index': INDEX, 'paragraph_text': TEXT, 'expression': TEXT,
        'expression_start': INDEX, 'expression_end': {'type': 'integer', 'minimum': 1}})
    IMAGE_LOCATOR = obj({'kind': {'const': 'image'}, 'view_ref': REF, 'source_ref': REF, 'artifact_ref': REF,
        'original_source_ref': REF, 'original_artifact_ref': REF, 'frame': INDEX, 'region': BOX, 'quote': TEXT})
    LOCATOR = {'oneOf': [JATS_LOCATOR, IMAGE_LOCATOR]}
    DIAGNOSTIC = obj({'code': choice(*REASONS), 'field': TEXT, 'source_refs': arr(REF, uniqueItems=True)})
    AUTH_WITNESS = obj({'selection': WITNESS, 'locator': nullable(LOCATOR),
        'authentication': choice('exact_utf8_span', 'native_view_bytes_and_geometry', 'unavailable'),
        'attribution': choice('literal_source_record', 'investigating_episode_interpretation'),
        'diagnostics': arr(DIAGNOSTIC)})


    def extracted_meaning(selected):
        fields = deepcopy(selected['properties'])
        fields['witnesses'] = arr(AUTH_WITNESS)
        fields['interpretation_kind'] = {'const': 'episode_source_interpretation'}
        return obj(fields)


    view_fields = {'id': REF, 'record_type': {'const': 'image_view'}, 'origin': {'const': 'tool'},
        'representation': {'const': 'selected_native_image_frame_v1'}, 'source_ref': REF, 'input_source_ref': REF,
        'original_artifact_ref': REF, 'image_artifact_ref': REF, 'native_format': TEXT, 'native_initial_mode': TEXT,
        'selected_mode': TEXT, 'display_mode': TEXT, 'frame': INDEX,
        'frame_count': {'type': 'integer', 'minimum': 1}, 'width': {'type': 'integer', 'minimum': 1},
        'height': {'type': 'integer', 'minimum': 1}, 'colour_conversion': choice('preserve', 'rgb'),
        'software': {'const': 'Pillow'}, 'software_version': TEXT, 'geometric_transform': {'const': 'identity'},
        'contrast_transform': {'const': 'identity'}, 'orientation': {'const': 'stored_pixel_axis_no_exif_rotation'}}
    OWN_VIEW_RECEIPT = obj({'run_id': TEXT, 'episode_id': TEXT, 'decision_index': INDEX,
        'operation_ref': REF, 'result_sha256': TEXT, 'view_ref': REF})
    view = obj({'view_ref': REF, 'metadata': nullable(obj(view_fields)),
        'original_sha256': {'type': ['string', 'null']}, 'display_sha256': {'type': ['string', 'null']},
        'own_action_receipt': nullable(OWN_VIEW_RECEIPT), 'state': choice('available', 'unavailable'),
        'diagnostics': arr(DIAGNOSTIC)})
    parsed_number = obj({'literal': TEXT, 'relation': choice('point', 'lt', 'le', 'gt', 'ge', 'unavailable'),
        'value': NUMBER, 'exact': nullable(RATIONAL), 'locator': nullable(LOCATOR), 'diagnostics': arr(DIAGNOSTIC)})
    reading = obj({'candidate_index': INDEX, 'numerator': parsed_number, 'denominator': nullable(parsed_number),
        'ratio': NUMBER, 'ratio_exact': nullable(RATIONAL), 'reported_domains': arr(DOMAIN),
        'source_reading_key': {'type': ['string', 'null']}, 'diagnostics': arr(DIAGNOSTIC)})
    row = obj({'representation_id': TEXT, 'kind': choice('jats_percent', 'visual_ratio', 'visual_percent', 'visual_signal_pair'),
        'selection': {'oneOf': [jats_selection, visual_selection]},
        'comparison_relation': extracted_meaning(RELATION),
        'physical_measurement': extracted_meaning(meaning()), 'reference_measurement': extracted_meaning(meaning()),
        'reading_state': choice(*READING), 'readings': arr(reading),
        'fragments': arr(obj({'selection': FRAGMENT, 'locator': nullable(IMAGE_LOCATOR), 'diagnostics': arr(DIAGNOSTIC)})),
        'origin': choice('reported', 'visual_transcription'), 'diagnostics': arr(DIAGNOSTIC)})
    EXTRACTION = obj({'version': {'const': 'relative_signal_source_extraction_v2'}, 'selection': REQUEST,
        'sources': arr(obj({'source_ref': REF, 'representation': choice('original', 'text'),
            'artifact_ref': {'type': ['string', 'null'], 'format': 'reference'},
            'byte_sha256': {'type': ['string', 'null']}, 'state': choice('available', 'unavailable'),
            'diagnostics': arr(DIAGNOSTIC)})), 'views': arr(view),
        'comparison': obj({name: extracted_meaning(value) for name, value in comparison.items()}),
        'representations': arr(row), 'interpretation_attribution': {'const': 'investigating_episode_interpretation'}})
    CELL = obj({'value': NUMBER, 'value_candidates': arr({'type': 'number'}, uniqueItems=True),
        'reported_domains': arr(DOMAIN), 'unit': {'type': ['string', 'null'], 'enum': ['fraction', 'dimensionless', None]},
        'status': choice('populated', 'conflicting', 'unavailable'), 'origin': choice('reported', 'visual_transcription', 'derived', 'proposed'),
        'formula': TEXT, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [*REASONS, None]},
        'conditional_on': arr(choice('source_comparison_interpretation', 'nominated_printed_signal_pair'), uniqueItems=True)})
    SHEET = obj({'version': {'const': 'relative_signal_sheet_v2'}, 'scope': {'const': 'reported_relative_signal'},
        'cells': obj({name: CELL for name in COMPONENTS}), 'selected_roster_resolved': BOOL,
        'point_candidate_set_complete': BOOL, 'known_source_conflict': BOOL,
        'independent_preparation_count': {'type': 'null'}, 'annotation_credit': {'type': 'null'}})

    IMAGE_LOCATOR['properties']['quote'] = {'type': ['string', 'null']}
    RELATION['properties']['value'] = choice('supported', 'different', 'unknown', 'conflicting')
    visual_selection['properties']['signal_scale'] = obj({
        'value': choice('supported', 'different', 'unknown', 'conflicting', 'not_applicable'),
        'witnesses': arr(WITNESS)})
    row['properties']['comparison_relation'] = extracted_meaning(RELATION)
    row['properties']['reading_state'] = choice(*READING, 'not_applicable')
    row['properties']['parse_status'] = choice('parsed', 'partial', 'unavailable')
    row['required'].append('parse_status')
    reasons = (*REASONS, 'different_reported_quantities', 'signal_scales_differ')
    DIAGNOSTIC['properties']['code'] = choice(*reasons)
    CELL['properties']['unavailable_reason']['enum'] = [*reasons, None]
    row['properties']['origin']['enum'].append('synthetic')
    CELL['properties']['origin']['enum'].append('synthetic')
    EXTRACTION['properties']['evidence_origin'] = choice('reported_source', 'synthetic_fixture')
    EXTRACTION['required'].append('evidence_origin')
    #008 adds truthful generic UTF8 spans ONLY to authenticated witness locators.
    text_span = obj({'kind': {'const': 'text_span'}, 'source_ref': deepcopy(REF),
        'artifact_ref': deepcopy(REF), 'representation': choice('original', 'text'),
        'start': INDEX, 'end': {'type': 'integer', 'minimum': 1}, 'quote': TEXT})
    visited = set()
    def add_text_spans(node):
        if isinstance(node, dict):
            if id(node) in visited:
                return
            visited.add(id(node))
            if set(node.get('properties', {})) == {'selection', 'locator', 'authentication', 'attribution', 'diagnostics'}:
                # Break the constructor's shared LOCATOR alias:008 extends
                # witness locators only, never numeric operand locators.
                node['properties']['locator'] = deepcopy(node['properties']['locator'])
                union = node['properties']['locator']['anyOf'][0]['oneOf']
                union.append(deepcopy(text_span))
            for child in node.values():
                add_text_spans(child)
        elif isinstance(node, list):
            for child in node:
                add_text_spans(child)
    add_text_spans(EXTRACTION)
    EXTRACTION['properties']['version']['const'] = 'relative_signal_source_extraction_v3'
    return REQUEST, EXTRACTION, SHEET


_REQUEST_SCHEMA, _EXTRACTION_SCHEMA, _SHEET_SCHEMA = _build_schemas()

def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _hash(content):
    return hashlib.sha256(content).hexdigest()


def _json(value, field):
    import math
    if isinstance(value, dict):
        if any(type(k) is not str for k in value):
            _fail('json_string_keys_required', field)
        for k, v in value.items():
            _json(v, field + '.' + k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _json(v, f'{field}[{i}]')
    elif value is not None and type(value) not in (str, bool, int, float):
        _fail('json_value_required', field)
    elif type(value) in (int, float):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            _fail('finite_number_required', field)


def _shape(value, schema, field):
    _json(value, field)
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        _fail('schema_mismatch', field + '.' + '.'.join(map(str, error.absolute_path)))
    def numeric(v, node, path):
        if isinstance(v, dict):
            for k, item in v.items():
                numeric(item, node.get('properties', {}).get(k, {}), path + '.' + k)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                numeric(item, node.get('items', {}), f'{path}[{i}]')
        if node.get('type') == 'integer' and type(v) is not int:
            _fail('integer_required', path)
        for kind in ('oneOf', 'anyOf'):
            for child in node.get(kind, []):
                if Draft202012Validator(child).is_valid(v):
                    numeric(v, child, path)
                    break
    numeric(value, schema, field)


def _diagnostic(code, field, refs=()):
    return {'code': code, 'field': field, 'source_refs': list(dict.fromkeys(refs))}


def relative_signal_source_arguments_schema():
    return deepcopy(_REQUEST_SCHEMA)


def validate_relative_signal_source_selection(selection):
    from .literature_ratio_source_validation import _validate_selection
    _validate_selection(selection)
    return deepcopy(selection)


def validate_relative_signal_source_extraction(extraction):
    from .literature_ratio_source_validation import _validate_extraction
    _validate_extraction(extraction)
    return deepcopy(extraction)


def _dependencies(selection):
    sources, views = [], []
    def visit(value):
        if isinstance(value, dict):
            if value.get('kind') == 'text':
                key = (value['source_ref'], value['representation'])
                if key not in sources:
                    sources.append(key)
            if 'view_ref' in value and value['view_ref'] not in views:
                views.append(value['view_ref'])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(selection)
    for row in selection['representations']:
        if row['kind'] == 'jats_percent':
            key = (row['selection']['source_ref'], 'original')
            if key not in sources:
                sources.append(key)
    return sources, views


def _available_call(callback, *args):
    try:
        return callback(*args)
    except OSError as error:
        if error.errno not in (errno.ENOENT, errno.EIO, errno.ETIMEDOUT):
            raise
        return _UNAVAILABLE


def _register(artifacts, ref, content):
    if type(ref) is not str or not ref.strip() or type(content) is not bytes:
        _fail('immutable_artifact_bytes_required', 'callback')
    digest = _hash(content)
    if ref in artifacts and artifacts[ref] != digest:
        _fail('artifact_bytes_mismatch', ref)
    artifacts[ref] = digest
    return digest


def _view_bytes(ref, raw, artifacts):
    if type(raw) is not dict or set(raw) != {'metadata', 'original_bytes', 'display_bytes', 'own_action_receipt'}:
        _fail('closed_fields_required', 'read_view')
    schema = _EXTRACTION_SCHEMA['properties']['views']['items']['properties']
    _shape(raw['metadata'], schema['metadata']['anyOf'][0], 'view.metadata')
    _shape(raw['own_action_receipt'], schema['own_action_receipt']['anyOf'][0], 'view.receipt')
    m, receipt = raw['metadata'], raw['own_action_receipt']
    from .literature_ratio_source_validation import _view_binding
    _view_binding(ref, m, receipt)
    original_hash = _register(artifacts, m['original_artifact_ref'], raw['original_bytes'])
    display_hash = _register(artifacts, m['image_artifact_ref'], raw['display_bytes'])
    try:
        with Image.open(BytesIO(raw['original_bytes'])) as original:
            fmt, initial = original.format, original.mode
            count = getattr(original, 'n_frames', 1)
            if not 0 <= m['frame'] < count:
                _fail('image_frame_outside_source', ref)
            original.seek(m['frame'])
            original.load()
            if (fmt != m['native_format'] or initial != m['native_initial_mode'] or count != m['frame_count']
                    or original.mode != m['selected_mode'] or original.size != (m['width'], m['height'])):
                _fail('native_image_metadata_mismatch', ref)
            selected = original.convert('RGB') if m['colour_conversion'] == 'rgb' else original
            with Image.open(BytesIO(raw['display_bytes'])) as display:
                display.load()
                if (display.format != 'PNG' or display.mode != m['display_mode']
                        or display.size != selected.size or getattr(display, 'n_frames', 1) != 1):
                    _fail('display_image_metadata_mismatch', ref)
                restored = display if display.mode == selected.mode else display.convert(selected.mode)
                if restored.tobytes() != selected.tobytes() or (selected.mode == 'P'
                        and selected.convert('RGBA').tobytes() != display.convert('RGBA').tobytes()):
                    _fail('display_pixels_mismatch', ref)
    except ExperimentalContractError:
        raise
    except (OSError, ValueError, SyntaxError) as error:
        raise ExperimentalContractError('image_decode_failed', ref) from error
    return {'view_ref': ref, 'metadata': deepcopy(m), 'original_sha256': original_hash,
        'display_sha256': display_hash, 'own_action_receipt': deepcopy(receipt),
        'state': 'available', 'diagnostics': []}


def _image_locator(witness, view):
    if view['state'] == 'unavailable':
        return None
    m, box = view['metadata'], witness['region']
    if not (0 <= box[0] < box[2] <= m['width'] and 0 <= box[1] < box[3] <= m['height']):
        _fail('image_region_out_of_bounds', 'region')
    return {'kind': 'image', 'view_ref': witness['view_ref'], 'source_ref': m['source_ref'],
        'artifact_ref': m['image_artifact_ref'], 'original_source_ref': m['input_source_ref'],
        'original_artifact_ref': m['original_artifact_ref'], 'frame': m['frame'],
        'region': deepcopy(box), 'quote': witness.get('quote', witness.get('raw_fragment'))}


def _reading_key(numerator, denominator):
    def identity(operand):
        if operand is None or operand['locator'] is None:
            return None
        loc = operand['locator']
        if loc['kind'] == 'image':
            return {k: loc[k] for k in ('original_artifact_ref', 'frame', 'region', 'quote')}
        return {k: loc[k] for k in ('artifact_ref', 'section_id', 'paragraph_index', 'expression_start', 'expression_end', 'expression')}
    if numerator['locator'] is None or denominator is not None and denominator['locator'] is None:
        return None
    return _hash(_canonical({'numerator': identity(numerator), 'denominator': identity(denominator)}).encode('utf-8'))


def read_relative_signal_source_inputs(selection, *, read_source, read_view, evidence_origin):
    selection = validate_relative_signal_source_selection(selection)
    if type(evidence_origin) is not str or evidence_origin not in ('reported_source', 'synthetic_fixture'):
        _fail('evidence_origin_required', 'evidence_origin')
    if not callable(read_source) or not callable(read_view):
        _fail('source_callbacks_required', 'callbacks')
    source_deps, view_deps = _dependencies(selection)
    # Complete callback authorization/acquisition for ALL dependencies before
    # helpers/decoding/parsing. None is not a callback availability signal.
    source_raw, view_raw = [], []
    for key in source_deps:
        raw = _available_call(read_source, *key)
        source_raw.append((key, raw))
    for ref in view_deps:
        view_raw.append((ref, _available_call(read_view, ref)))
    artifacts, sources, views, contents = {}, [], [], {}
    for (ref, representation), raw in source_raw:
        row = {'source_ref': ref, 'representation': representation, 'artifact_ref': None,
            'byte_sha256': None, 'state': 'unavailable', 'diagnostics': [_diagnostic('source_dependency_unavailable', 'source', [ref])]}
        if raw is not _UNAVAILABLE:
            if type(raw) is not dict or set(raw) != {'artifact_ref', 'content'}:
                _fail('closed_fields_required', 'read_source')
            digest = _register(artifacts, raw['artifact_ref'], raw['content'])
            row.update(artifact_ref=raw['artifact_ref'], byte_sha256=digest, state='available', diagnostics=[])
            contents[(ref, representation)] = raw['content']
        sources.append(row)
    for ref, raw in view_raw:
        views.append(_view_bytes(ref, raw, artifacts) if raw is not _UNAVAILABLE else {
            'view_ref': ref, 'metadata': None, 'original_sha256': None, 'display_sha256': None,
            'own_action_receipt': None, 'state': 'unavailable',
            'diagnostics': [_diagnostic('source_dependency_unavailable', 'view', [ref])]})
    source_map = {(r['source_ref'], r['representation']): r for r in sources}
    view_map = {r['view_ref']: r for r in views}
    def witness(w):
        refs = [w.get('source_ref', w.get('view_ref'))]
        if w['kind'] == 'image':
            locator = _image_locator(w, view_map[w['view_ref']])
            authentication, attribution = 'native_view_bytes_and_geometry', 'investigating_episode_interpretation'
        else:
            row = source_map[(w['source_ref'], w['representation'])]
            locator = None
            if row['state'] == 'available':
                content = contents[(w['source_ref'], w['representation'])]
                try:
                    actual = content[w['start']:w['end']].decode('utf-8')
                except UnicodeDecodeError as error:
                    raise ExperimentalContractError('source_span_utf8_boundary_required', 'witness') from error
                if w['end'] > len(content) or actual != w['quote']:
                    _fail('source_quote_mismatch', 'witness')
                locator = {'kind': 'text_span', 'source_ref': w['source_ref'], 'artifact_ref': row['artifact_ref'],
                    'representation': w['representation'], 'start': w['start'], 'end': w['end'], 'quote': w['quote']}
            authentication, attribution = 'exact_utf8_span', 'literal_source_record'
        return {'selection': deepcopy(w), 'locator': locator,
            'authentication': authentication if locator is not None else 'unavailable', 'attribution': attribution,
            'diagnostics': [] if locator is not None else [_diagnostic('source_dependency_unavailable', 'witness', refs)]}
    def meaning(m):
        return {**deepcopy(m), 'witnesses': [witness(w) for w in m['witnesses']], 'interpretation_kind': 'episode_source_interpretation'}
    from .literature_ratio_source_validation import _operand, _ratio_reading
    rows = []
    for spec in selection['representations']:
        selected, kind = spec['selection'], spec['kind']
        row = {**{k: deepcopy(spec[k]) for k in ('representation_id', 'kind', 'selection')},
            **{k: meaning(spec[k]) for k in ('comparison_relation', 'physical_measurement', 'reference_measurement')},
            'reading_state': 'not_applicable' if kind == 'jats_percent' else selected['reading_state'],
            'readings': [], 'fragments': [], 'origin': 'synthetic' if evidence_origin == 'synthetic_fixture' else
            'reported' if kind == 'jats_percent' else 'visual_transcription', 'diagnostics': [], 'parse_status': 'partial'}
        if kind == 'jats_percent':
            source = source_map[(selected['source_ref'], 'original')]
            if source['state'] == 'unavailable':
                row['diagnostics'] = [_diagnostic('source_dependency_unavailable', 'jats', [selected['source_ref']])]
            else:
                # Finite capability failures remain distinct from image readability.
                try:
                    text, match = _jats_expression(contents[(selected['source_ref'], 'original')], selected)
                    locator = {'kind': 'jats', 'source_ref': selected['source_ref'], 'artifact_ref': source['artifact_ref'],
                        'section_id': selected['section_id'], 'paragraph_index': selected['paragraph_index'],
                        'paragraph_text': text, 'expression': match.group(), 'expression_start': match.start(), 'expression_end': match.end()}
                    operand = _operand(match['number'] + '%', locator, percent=True)
                    row['readings'] = [_ratio_reading(0, operand, None, kind, None)]
                except (UnicodeDecodeError, ET.ParseError, ValueError, IndexError):
                    row['diagnostics'] = [_diagnostic('jats_expression_capability_partial', 'jats', [selected['source_ref']])]
        else:
            scale_auth = meaning(selected['signal_scale'])
            for i, candidate in enumerate(selected['candidates']):
                nw, dw = candidate['numerator'], candidate['denominator']
                n = _operand(nw['quote'], _image_locator(nw, view_map[nw['view_ref']]), percent=kind == 'visual_percent')
                d = _operand(dw['quote'], _image_locator(dw, view_map[dw['view_ref']])) if dw else None
                row['readings'].append(_ratio_reading(i, n, d, kind, scale_auth))
            for fragment in selected['fragments']:
                loc = _image_locator(fragment, view_map[fragment['view_ref']])
                row['fragments'].append({'selection': deepcopy(fragment), 'locator': loc,
                    'diagnostics': [] if loc else [_diagnostic('source_dependency_unavailable', 'fragment', [fragment['view_ref']])]})
            if row['reading_state'] == 'unreadable':
                row['diagnostics'].append(_diagnostic('unreadable_transcription', 'reading_state'))
            elif row['reading_state'] in ('ambiguous', 'conflicting'):
                row['diagnostics'].append(_diagnostic('ambiguous_transcription' if row['reading_state'] == 'ambiguous' else 'source_representation_conflict', 'reading_state'))
        row['parse_status'] = _parse_status(row)
        rows.append(row)
    output = {'version': 'relative_signal_source_extraction_v3', 'selection': selection,
        'sources': sources, 'views': views, 'comparison': {k: meaning(v) for k, v in selection['comparison'].items()},
        'representations': rows, 'interpretation_attribution': 'investigating_episode_interpretation', 'evidence_origin': evidence_origin}
    return validate_relative_signal_source_extraction(output)


def _jats_expression(content, selected):
    xml = content.decode('utf-8')
    _check_declarations(xml)
    root = ET.fromstring(xml)
    if _tag(root) != 'article':
        raise ValueError('article')
    sections = [e for e in root.iter() if e.get('id') == selected['section_id']]
    if len(sections) != 1 or _tag(sections[0]) != 'sec':
        raise ValueError('section')
    paragraphs = [e for e in sections[0] if _tag(e) == 'p']
    return _jats_matches(_direct_paragraph_text(paragraphs[selected['paragraph_index']]), selected)


def _jats_matches(text, selected):
    if not _contains_literal(text, selected['expected_subject']):
        raise ValueError('subject')
    matches = []
    for match in _PERCENT.finditer(text):
        if not _contains_literal(match['label'], selected['variant']):
            continue
        following = text[match.end():_sentence_end(text, match.end())]
        refs = list(re.finditer(r'(?<!\w)of\s+' + re.escape(selected['reference_literal']) + r'(?!\w)', following))
        first = re.search(r'(?<!\w)of\b', following)
        if len(refs) != 1 or first is None or first.start() != refs[0].start():
            continue
        if (_LIMIT_PREFIX.search(text[:match.start()]) or _RANGE_PREFIX.search(text[:match.start()])
                or re.search(r'±|\+\s*/\s*[−-]|\b(?:SD|SEM|CI)\b', following[:refs[0].start()])
                or re.match(r'\s*(?:or\s+(?:less|more|greater|lower|higher)|at\s+(?:most|least))\b', following)):
            raise ValueError('qualified expression')
        matches.append(match)
    if len(matches) != 1:
        raise ValueError('one expression')
    return text, matches[0]


def _parse_status(row):
    if any(r['numerator']['locator'] is None or r['denominator'] is not None and r['denominator']['locator'] is None for r in row['readings']):
        return 'unavailable'
    if not row['readings'] and row['diagnostics'] and row['diagnostics'][0]['code'] == 'source_dependency_unavailable':
        return 'unavailable'
    return 'parsed' if row['readings'] and all(r['reported_domains'] for r in row['readings']) else 'partial'


_UNAVAILABLE = object()
__all__ = ['relative_signal_source_arguments_schema', 'validate_relative_signal_source_selection',
           'read_relative_signal_source_inputs', 'validate_relative_signal_source_extraction']
