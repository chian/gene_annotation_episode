"""Source-bound v3 readers and closed parsed contracts for internal A105 sheets.

These host functions read experimental quantities and preserve source meanings.
"""
from __future__ import annotations
from copy import deepcopy as cp
import json
from fractions import Fraction
import errno
import hashlib
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_figure_inputs as graph_reader

from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_v3_contracts import (
    _schemas, controlled_response_v3_arguments_schema, _extraction_schema, _graph_schema
)

def _graph_request(selected, measurement):
    return {'version': 'controlled_response_rate_figure_selection_v1', 'images': cp(selected['images']), 'measurement': cp(measurement)}

def _read_graph(context, selected):

    def cached(reference, representation):
        key = (reference, representation)
        context._active()
        if key not in context.cache:
            shared._fail('unselected_source_read', 'source_ref')
        error = context.unavailable_errors.get(key)
        if error is not None:
            if isinstance(error, EOFError):
                raise OSError(errno.EIO, str(error)) from error
            raise error
        return context.read_source(reference, representation)
    result = graph_reader.read_controlled_response_rate_figure(_graph_request(context.arguments, selected), read_source=cached)
    return _graph_reading(context, selected, result)

def _graph_reading(context, selected, result):
    measurement = result['measurement']
    return shared._StageValue(context, {'selection': selected, 'extraction': measurement, 'operand_projection': result['operand_projection'], 'unit_semantics': {'kind': 'graph', 'record': measurement['unit']}, 'exact_response': shared._exact_response(measurement, graph=True), 'source_observation_id': measurement['source_observation_id'], 'graph_details': result})

def _saved_roster(selected, extraction):
    sources = {}
    artifacts = {}
    for source in extraction['sources']:
        key = (source['source_ref'], source['representation'])
        if key in sources:
            shared._fail('saved_duplicate_source', 'sources')
        sources[key] = source
        if source['state'] == 'available':
            if not source['artifact_ref'].strip() or not source['byte_sha256']:
                shared._fail('saved_source_identity_mismatch', 'sources')
            if source['artifact_ref'] in artifacts and artifacts[source['artifact_ref']] != source['byte_sha256']:
                shared._fail('artifact_content_conflict', 'sources')
            artifacts[source['artifact_ref']] = source['byte_sha256']
        elif source['artifact_ref'] is not None or source['byte_sha256'] is not None:
            shared._fail('saved_source_state_mismatch', 'sources')
    if list(sources) != shared._reference_closure(selected):
        shared._fail('saved_source_roster_mismatch', 'sources')
    _saved_images(selected['images'], extraction['images'], sources)
    return sources

def _saved_images(nominated, images, sources):
    if len(images) != len(nominated):
        shared._fail('saved_image_roster_mismatch', 'images')
    for spec, record in zip(nominated, images):
        if any((spec[k] != record[k] for k in ('image_id', 'source_ref', 'original_source_ref', 'mapping'))):
            shared._fail('saved_image_selection_mismatch', 'images')
        for prefix, ref_key in (('', 'source_ref'), ('original_', 'original_source_ref')):
            source = sources[spec[ref_key], 'original']
            if record[prefix + 'artifact_ref'] is not None and (record[prefix + 'artifact_ref'] != source['artifact_ref'] or record[prefix + 'byte_sha256'] != source['byte_sha256']):
                shared._fail('saved_image_source_mismatch', 'images')
        if not record['error'] and (not record['width'] or not record['height'] or record['frame_count'] != 1):
            shared._fail('saved_image_geometry_mismatch', 'images')

def _check_witness(record, nominated, sources, images, field):
    shared._saved_witness(record, nominated, sources, field)
    if record is None or record['canonical_locator'] is None or record['selection']['kind'] != 'image':
        return
    selected = record['selection']
    image = next((i for i in images if i['image_id'] == selected['image_id']))
    region = selected['region']
    if image['error'] or not (0 <= region[0] < region[2] <= image['width'] and 0 <= region[1] < region[3] <= image['height']):
        shared._fail('saved_image_geometry_mismatch', field)
    if image['mapping']:
        original = image['mapping']['original_region']
        region = [region[0] + original[0], region[1] + original[1], region[2] + original[0], region[3] + original[1]]
    wanted = {'kind': 'image', 'original_source_ref': image['original_source_ref'], 'original_artifact_ref': image['original_artifact_ref'], 'original_byte_sha256': image['original_byte_sha256'], 'region': region}
    if record['canonical_locator'] != wanted or record['artifact_ref'] != image['artifact_ref'] or record['byte_sha256'] != image['byte_sha256']:
        shared._fail('saved_image_identity_mismatch', field)

def _validate_text(selected, measurement, sources, images):
    if measurement['selection'] != selected:
        shared._fail('saved_selection_mismatch', 'measurement')
    if selected is None:
        expected = {'selection': None, 'candidates': [], 'fragments': [], 'unit': None, 'graph_witnesses': [], 'reading_status': 'not_selected', 'source_observation_id': None, 'canonical_display': shared._display(None, None), 'pixel_result': None}
        if any((measurement[k] != v for k, v in expected.items())):
            shared._fail('saved_measurement_projection_mismatch', 'measurement')
        return
    literal = selected['literal']
    if len(measurement['candidates']) != len(literal['candidates']) or len(measurement['fragments']) != len(literal['fragments']):
        shared._fail('saved_selection_mismatch', 'measurement')
    for record, nominated in zip(measurement['candidates'], literal['candidates']):
        shared._saved_number(record, nominated, sources, 'measurement.candidates')
    for record, nominated in zip(measurement['fragments'], literal['fragments']):
        _check_witness(record, nominated, sources, images, 'measurement.fragments')
    shared._saved_unit(measurement['unit'], selected['unit'], sources, 'measurement.unit')
    state = literal['status']
    if any((n['status'] == 'dependency_unavailable' for n in measurement['candidates'])) or any((w['canonical_locator'] is None for w in measurement['fragments'])):
        state = 'dependency_unavailable'
    elif state == 'exact' and measurement['candidates'][0]['status'] != 'parsed':
        state = 'unsupported'
    locators = [n['source_locator'] for n in measurement['candidates'] if n['source_locator'] is not None]
    locators += [w['canonical_locator'] for w in measurement['fragments'] if w['canonical_locator'] is not None]
    reading_id = shared.identity('controlled_source_token', locators[0] if len(locators) == 1 else locators) if state != 'dependency_unavailable' and locators else None
    if measurement['reading_status'] != state or measurement['source_observation_id'] != reading_id:
        shared._fail('saved_measurement_identity_mismatch', 'measurement')
    number = measurement['candidates'][0] if state == 'exact' else None
    expected_display = shared._display(number, measurement['unit']) if state == 'exact' else shared._display(None, None)
    if measurement['canonical_display'] != expected_display:
        shared._fail('saved_canonical_display_mismatch', 'measurement')

def _validate_measurement(selected, saved_measurement, *, source_records, image_records):
    """Closed text check; graph checks additionally retain the complete063 result."""
    sources = {(s['source_ref'], s['representation']): s for s in source_records}
    _validate_text(selected, saved_measurement, sources, image_records)
    return shared._reading_from_text(None, selected, saved_measurement)

def _validate_graph(selected, result, *, sources, images, request):
    Draft202012Validator(_graph_schema()).validate(result)
    if result['selection'] != _graph_request(request, selected) or result['version'] != 'controlled_response_rate_figure_extraction_v1':
        shared._fail('saved_graph_selection_mismatch', 'graph_details')
    closure = []
    for image in request['images']:
        closure.extend([(image['source_ref'], 'original'), (image['original_source_ref'], 'original')])
    closure += [(w['source_ref'], w['representation']) for w in graph_reader._witnesses(selected) if w['kind'] == 'text']
    closure = list(dict.fromkeys(closure))
    actual_closure = [(s['source_ref'], s['representation']) for s in result['sources']]
    if len(actual_closure) != len(set(actual_closure)) or set(actual_closure) != set(closure):
        shared._fail('saved_graph_source_roster_mismatch', 'graph_details.sources')
    for source in result['sources']:
        original = sources[source['source_ref'], source['representation']]
        if any((source[k] != original[k] for k in ('artifact_ref', 'byte_sha256', 'state'))):
            shared._fail('saved_graph_source_identity_mismatch', 'graph_details.sources')
    _saved_images(request['images'], result['images'], sources)
    actual_images = result['images']
    for name, literal in result['axis_literals'].items():
        nominated = selected['axis'][name] if name == 'unit' else selected['axis'][name]['tick']
        if literal['selection'] != nominated:
            shared._fail('saved_graph_literal_selection_mismatch', 'axis.' + name)
        for part in ('candidates', 'fragments'):
            if len(literal[part]) != len(nominated[part]):
                shared._fail('saved_graph_literal_selection_mismatch', 'axis.' + name)
            for saved, witness in zip(literal[part], nominated[part]):
                _check_witness(saved, witness, sources, actual_images, 'axis.' + name)
        available = all((w['canonical_locator'] is not None for part in ('candidates', 'fragments') for w in literal[part]))
        if literal['status'] == 'parsed':
            if nominated['status'] != 'exact' or not available or literal['raw_literal'] != nominated['candidates'][0]['quote']:
                shared._fail('saved_graph_literal_mismatch', 'axis.' + name)
            witness = nominated['candidates'][0]
            qualification = 'source_text_literal' if witness['kind'] == 'text' else 'episode_image_transcription'
            if literal['qualification'] != qualification:
                shared._fail('saved_graph_literal_mismatch', 'axis.' + name)
            if name != 'unit':
                token = literal['raw_literal'].strip().replace('−', '-')
                if not graph_reader._LITERAL.fullmatch(literal['raw_literal'].strip()) or literal['exact_value'] != shared._rational(Fraction(token)):
                    shared._fail('saved_graph_tick_mismatch', 'axis.' + name)
        elif not available and literal['status'] != 'dependency_unavailable' and (nominated['status'] == 'exact'):
            shared._fail('saved_graph_literal_availability_mismatch', 'axis.' + name)
    scale = result['axis_scale']
    if scale['selection'] != selected['axis']['scale'] or len(scale['witnesses']) != len(scale['selection']['witnesses']):
        shared._fail('saved_graph_scale_mismatch', 'axis.scale')
    for saved, witness in zip(scale['witnesses'], scale['selection']['witnesses']):
        _check_witness(saved, witness, sources, actual_images, 'axis.scale')
    if scale['support'] in ('literal_source_text', 'episode_image_interpretation'):
        expected_support = 'literal_source_text' if scale['selection']['basis'] == 'source_text_literal' else 'episode_image_interpretation'
        if scale['support'] != expected_support:
            shared._fail('saved_graph_scale_mismatch', 'axis.scale')
        if scale['selection']['status'] != 'known' or scale['effective_kind'] != scale['selection']['kind'] or any((w['canonical_locator'] is None for w in scale['witnesses'])):
            shared._fail('saved_graph_scale_mismatch', 'axis.scale')
        if scale['support'] == 'literal_source_text' and any((graph_reader._SCALE_PHRASES.get(w['selection']['quote'].strip().lower()) != scale['effective_kind'] for w in scale['witnesses'])):
            shared._fail('saved_graph_scale_literal_mismatch', 'axis.scale')
    unit = result['measurement']['unit']
    literal = result['axis_literals']['unit']
    if unit['selection'] != selected['axis']['unit'] or unit['raw_unit'] != literal['raw_literal']:
        shared._fail('saved_graph_unit_mismatch', 'axis.unit')
    if unit['status'] == 'supported':
        parsed = shared._plain_unit(unit['raw_unit'])
        if parsed is None or parsed != (unit['canonical_unit'], shared._fraction(unit['exact_scale'])):
            shared._fail('saved_graph_unit_mismatch', 'axis.unit')
        native = next((k for k in shared.RATE_UNITS if shared._plain_unit(k) == parsed), None)
        if native != unit['native_registry_unit'] or unit['witness'] != literal['candidates'][0]:
            shared._fail('saved_graph_unit_mismatch', 'axis.unit')
    pixels = result['measurement']['pixel_result']
    spec = next((i for i in actual_images if i['image_id'] == selected['image_id']))
    if pixels['recipe'] != selected['bar_selection'] or pixels['terminal_edge'] != selected['terminal_edge'] or pixels['image_id'] != selected['image_id']:
        shared._fail('saved_graph_recipe_mismatch', 'pixels')
    if pixels['image_sha256'] != spec['byte_sha256'] or pixels['original_image_sha256'] != spec['original_byte_sha256']:
        shared._fail('saved_graph_image_identity_mismatch', 'pixels')
    recipe, edge = (selected['bar_selection'], selected['terminal_edge'])
    roi = recipe['roi']
    runs = pixels['qualifying_runs']
    for i, run in enumerate(runs):
        if not roi['top'] <= run['top'] < run['bottom'] <= roi['bottom'] or run['bottom'] - run['top'] < recipe['minimum_run_rows'] or (i and runs[i - 1]['bottom'] >= run['top']):
            shared._fail('saved_graph_runs_mismatch', 'pixels.qualifying_runs')
    if pixels['mapped_roi']:
        region = [roi[k] for k in ('left', 'top', 'right', 'bottom')]
        if spec['mapping']:
            ox, oy = spec['mapping']['original_region'][:2]
            region = [region[0] + ox, region[1] + oy, region[2] + ox, region[3] + oy]
        wanted = {'kind': 'image', 'original_source_ref': spec['original_source_ref'], 'original_artifact_ref': spec['original_artifact_ref'], 'original_byte_sha256': spec['original_byte_sha256'], 'region': region}
        if pixels['mapped_roi'] != wanted or pixels['image_size'] != {'width': spec['width'], 'height': spec['height']}:
            shared._fail('saved_graph_mapping_mismatch', 'pixels')
    if pixels['pixel_edge'] is not None:
        if len(runs) != 1:
            shared._fail('saved_graph_edge_mismatch', 'pixels')
        run = runs[0]
        clipped = run['top'] == roi['top'] if edge == 'upper' else run['bottom'] == roi['bottom']
        if clipped:
            shared._fail('saved_graph_terminal_clipping_mismatch', 'pixels')
        tolerance = Fraction(recipe['edge_tolerance_pixels'])
        if edge == 'upper':
            point, lo, hi = (Fraction(run['top']) + Fraction(1, 2), Fraction(run['top']) - tolerance, Fraction(run['top'] + 1) + tolerance)
        else:
            point, lo, hi = (Fraction(run['bottom']) - Fraction(1, 2), Fraction(run['bottom'] - 1) - tolerance, Fraction(run['bottom']) + tolerance)
        wanted = {'terminal_edge': edge, 'nominal': shared._rational(point), 'bounds': {'lower': shared._rational(lo), 'upper': shared._rational(hi)}}
        if pixels['pixel_edge'] != wanted:
            shared._fail('saved_graph_edge_mismatch', 'pixels')
    if pixels['status'] == 'measured':
        if pixels['pixel_edge'] is None or scale['effective_kind'] != 'linear' or scale['support'] not in ('literal_source_text', 'episode_image_interpretation') or (unit['status'] != 'supported'):
            shared._fail('saved_graph_calibration_mismatch', 'pixels')
        p1, p2 = (Fraction(selected['axis'][k]['pixel']) for k in ('first', 'second'))
        v1, v2 = (shared._fraction(result['axis_literals'][k]['exact_value']) for k in ('first', 'second'))
        if p1 == p2 or v1 == v2 or (not 0 <= lo <= hi < spec['height']):
            shared._fail('saved_graph_calibration_mismatch', 'pixels')
        slope = (v2 - v1) / (p2 - p1)
        axis = {'first_pixel': shared._rational(p1), 'second_pixel': shared._rational(p2), 'first_value': shared._rational(v1), 'second_value': shared._rational(v2), 'unit': unit['native_registry_unit'], 'slope': shared._rational(slope)}
        ordinate = lambda p: v1 + (p - p1) * slope
        lower, upper = sorted((ordinate(lo), ordinate(hi)))
        if pixels['axis'] != axis or pixels['native_ordinate'] != shared._rational(ordinate(point)) or pixels['native_bounds'] != {'lower': shared._rational(lower), 'upper': shared._rational(upper)}:
            shared._fail('saved_graph_ordinate_mismatch', 'pixels')
    measurement, projection = (result['measurement'], result['operand_projection'])
    states = []
    if any((s['state'] == 'unavailable' for s in result['sources'])) or any((w['authentication'] == 'unavailable' for w in scale['witnesses'])):
        states.append('dependency_unavailable')
    states += [literal['status'] for literal in result['axis_literals'].values() if literal['status'] != 'parsed']
    if selected['axis']['scale']['status'] == 'conflicting':
        states.append('conflicting')
    states.append('graph_digitized' if pixels['status'] == 'measured' else pixels['status'])
    expected_status = next((status for status in ('dependency_unavailable', 'conflicting', 'ambiguous', 'unreadable', 'unsupported', 'graph_digitized') if status in states))
    if expected_status == 'graph_digitized':
        try:
            graph_reader._finite_float(shared._fraction(pixels['native_ordinate']))
            for side, direction in (('lower', -1), ('upper', 1)):
                graph_reader._outward(shared._fraction(pixels['native_bounds'][side]), direction)
        except OverflowError:
            expected_status = 'unsupported'
    if measurement['reading_status'] != expected_status:
        shared._fail('saved_graph_status_mismatch', 'measurement')
    expected_projection_status = 'point' if expected_status == 'graph_digitized' else 'missing' if expected_status in ('dependency_unavailable', 'unreadable') else expected_status
    if projection['status'] != expected_projection_status or projection['approximate'] is not True or projection['unit'] != unit['native_registry_unit']:
        shared._fail('saved_graph_projection_mismatch', 'operand_projection')
    ordered_literals = [result['axis_literals'][name] for name in ('first', 'second', 'unit')]
    fragments = [w for literal in ordered_literals for w in literal['fragments']]
    witnesses = [w for literal in ordered_literals for part in ('candidates', 'fragments') for w in literal[part]] + scale['witnesses']
    if measurement['selection'] != selected or measurement['fragments'] != fragments or measurement['graph_witnesses'] != witnesses or measurement['candidates']:
        shared._fail('saved_graph_measurement_mismatch', 'measurement')
    if projection['status'] == 'point':
        if pixels['status'] != 'measured' or measurement['reading_status'] != 'graph_digitized':
            shared._fail('saved_graph_projection_mismatch', 'measurement')
        native = shared._fraction(pixels['native_ordinate'])
        lower, upper = (shared._fraction(pixels['native_bounds'][s]) for s in ('lower', 'upper'))
        value = graph_reader._finite_float(native)
        interval = {'lower': min(graph_reader._outward(lower, -1), value), 'upper': max(graph_reader._outward(upper, 1), value)}
        expected = {'value': value, 'threshold': None, 'relation': 'interval', 'approximate': True, 'unit': unit['native_registry_unit'], 'status': 'point', 'origin': 'graph_derived', 'digitization_interval': interval}
        if projection != expected:
            shared._fail('saved_graph_projection_mismatch', 'operand_projection')
        identity_record = {'version': result['version'], 'selection': result['selection'], 'images': result['images'], 'literals': result['axis_literals'], 'scale': scale, 'unit': unit, 'pixels': pixels}
        expected_id = 'controlled_response_graph_' + hashlib.sha256(json.dumps(identity_record, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()
        if measurement['source_observation_id'] != expected_id:
            shared._fail('saved_graph_identity_mismatch', 'measurement.source_observation_id')
        display = {'value': None, 'threshold': None, 'unit': unit['canonical_unit'], 'relation': 'none', 'approximate': True, 'diagnostics': []}
        try:
            display['value'] = graph_reader._finite_float(native * shared._fraction(unit['exact_scale']))
        except OverflowError:
            display['diagnostics'] = [graph_reader._diagnostic('graph_canonical_display_range', 'measurement.canonical_display')]
        else:
            display['relation'] = 'eq'
        if measurement['canonical_display'] != display:
            shared._fail('saved_graph_display_mismatch', 'measurement.canonical_display')
    elif any((projection[k] is not None for k in ('value', 'threshold', 'digitization_interval'))) or projection['relation'] != 'none' or measurement['source_observation_id'] is not None:
        shared._fail('saved_graph_projection_mismatch', 'operand_projection')
    return _graph_reading(None, selected, result)

def validate_controlled_response_v3_selection(arguments):
    selected = shared._validate_selection(arguments, controlled_response_v3_arguments_schema())
    roster = {(role, None): arm for role, arm in selected['arms'].items()}
    keys = set()
    for row in selected['companion_readings']:
        key = row['reading_key']
        if key in keys:
            shared._fail('duplicate_companion_reading_key', 'companion_readings')
        keys.add(key)
        roster[row['primary_role'], key] = row['reading']

    def selector(value, field):
        if (value['role'], value['reading_key']) not in roster:
            shared._fail('controlled_reading_selector_unresolved', field)
    for arm in roster.values():
        if arm and arm['measurement'] and (arm['measurement']['kind'] == 'linear_bar'):
            graph_reader._validate(_graph_request(selected, arm['measurement']))
    maps = set()
    for row in selected['joint_reading_assignments']:
        key = tuple((row['assignment'][r] for r in shared.PRIMITIVE_ORDER))
        if key in maps:
            shared._fail('duplicate_joint_reading_assignment', 'joint_reading_assignments')
        maps.add(key)
        for role, reading_key in row['assignment'].items():
            selector({'role': role, 'reading_key': reading_key}, 'joint_reading_assignments')
    indices = [r['assignment_index'] for r in selected['joint_scopes']]
    if indices != list(range(len(selected['joint_reading_assignments']))):
        shared._fail('joint_scope_roster_mismatch', 'joint_scopes')
    roles = set()
    for row in selected['reading_reconciliations']:
        role = row['role']
        if role in roles:
            shared._fail('duplicate_reconciliation_role', 'reading_reconciliations')
        roles.add(role)
        auth = row['authority']
        if auth['status'] == 'source_explicit':
            if auth['reading'] is None or auth['reading']['role'] != role:
                shared._fail('authority_reading_role_mismatch', 'reading_reconciliations')
            selector(auth['reading'], 'reading_reconciliations.authority.reading')
        elif auth['reading'] is not None:
            shared._fail('authority_reading_without_designation', 'reading_reconciliations')
        minimum = 2 if auth['status'] == 'conflicting' else 1 if auth['status'] == 'source_explicit' else 0
        if len({shared._nomination_key(w) for w in auth['witnesses']}) < minimum:
            shared._fail('interpretation_witness_required', 'reading_reconciliations.authority')
    needed = {r['primary_role'] for r in selected['companion_readings']}
    if not needed <= roles:
        shared._fail('reading_reconciliation_missing', 'reading_reconciliations')
    pairs = set()
    for row in selected['local_pair_assignments']:
        if row['pair_key'] in pairs:
            shared._fail('duplicate_local_pair_key', 'local_pair_assignments')
        pairs.add(row['pair_key'])
        for name, prefix in (('protein', 'protein_'), ('control', 'empty_')):
            value = row[name]
            selector(value, 'local_pair_assignments.' + name)
            if value['role'] != prefix + row['condition']:
                shared._fail('local_pair_role_mismatch', 'local_pair_assignments.' + name)
    return selected


def _selector(role, key=None):
    return {'role': role, 'reading_key': key}


def read_controlled_response_v3_inputs(arguments, *, read_source):
    """Read every actual nomination in one authenticated shared source context."""
    validate_controlled_response_v3_selection(arguments)
    with shared.open_controlled_response_sources(arguments, read_source=read_source) as context:
        readings, arms, companions = {}, {}, []
        nominations = [(_selector(r), context.arguments['arms'][r]) for r in shared.PRIMITIVE_ORDER]
        nominations += [(_selector(row['primary_role'], row['reading_key']), row['reading'])
            for row in context.arguments['companion_readings']]
        for selector, selected in nominations:
            arm = None
            if selected is not None:
                science = shared.read_controlled_response_arm_science(context, selected, reading_selector=selector)
                endpoint = science['meanings']['endpoint']
                measurement = (shared.read_controlled_response_graph_measurement(context, selector, endpoint=endpoint)
                    if selected['measurement'] and selected['measurement']['kind'] == 'linear_bar' else
                    shared.read_controlled_response_text_measurement(context, selected['measurement'],
                        endpoint=endpoint, reading_selector=selector))
                arm = shared.finish_controlled_response_arm(context, science, measurement=measurement, reading_selector=selector)
            readings[(selector['role'], selector['reading_key'])] = arm
            if selector['reading_key'] is None: arms[selector['role']] = arm
            else: companions.append((selector, arm))
        scopes = []
        scope_selectors = [({'kind': 'base', 'index': None}, [_selector(r) for r in shared.PRIMITIVE_ORDER])]
        scope_selectors += [({'kind': 'joint', 'index': i}, [_selector(r, row['assignment'][r]) for r in shared.PRIMITIVE_ORDER])
            for i, row in enumerate(context.arguments['joint_reading_assignments'])]
        scope_selectors += [({'kind': 'local', 'index': i}, [row['protein'], row['control']])
            for i, row in enumerate(context.arguments['local_pair_assignments'])]
        for scope, selectors in scope_selectors:
            document = shared.read_controlled_response_covariance_document(context, scope)
            scopes.append(shared.bind_controlled_response_covariance_scope(context, scope, document,
                readings=[(s, readings[(s['role'], s['reading_key'])]) for s in selectors]))
        return shared.finish_controlled_response_inputs(context, arms=arms, companion_arms=companions, covariance_scopes=scopes)


def _relation(context, nomination, field):
    witnesses = [context.witness(w, field) for w in nomination['witnesses']]
    value = nomination['value']
    if any(w['canonical_locator'] is None for w in witnesses): value = 'unknown'
    return {'selection': cp(nomination), 'witnesses': witnesses, 'effective_value': value}


def _same_science(members):
    if not members or any(a is None for _, a in members): return 'unknown'
    arms = [a for _, a in members]
    if any(v['resolved_state'] == 'conflicting' for a in arms for v in a['meanings'].values()): return 'conflicting'
    if any(v['resolved_state'] != 'known' for a in arms for v in a['meanings'].values()): return 'unknown'
    first = arms[0]
    for arm in arms[1:]:
        if any(arm['meanings'][m]['canonical_id'] != first['meanings'][m]['canonical_id'] for m in shared._MEANINGS): return 'conflicting'
        if arm['protein_arrangement']['effective_value'] != first['protein_arrangement']['effective_value']: return 'conflicting'
        if arm['context'] != first['context']: return 'unknown'
    return 'same'


def _domain(arm):
    return shared._exact_response(arm['measurement'], graph=bool(arm['graph_details'])) if arm else None


def _domain_relation(selected, other):
    if selected is None or other is None or selected['unit'] is None or other['unit'] != selected['unit']:
        return 'unknown'
    if selected == other: return 'equal'
    if shared._response_domains_disjoint(selected, other): return 'disjoint'
    # A reported point can be consistent with a display without equating them.
    if selected['relation'] == 'eq' and selected['point'] is not None and other['lower'] and other['upper']:
        point = shared._fraction(selected['point'])
        if shared._fraction(other['lower']) <= point <= shared._fraction(other['upper']): return 'contains'
    return 'unknown'


def _reconcile(context, nomination, members):
    field = 'reading_reconciliations.' + nomination['role']
    relationship = _relation(context, nomination['relationship'], field + '.relationship')
    relations = {k: _relation(context, nomination[k], field + '.' + k) for k in ('normalization', 'calibration', 'revision', 'model_scope')}
    auth = nomination['authority']
    auth_witnesses = [context.witness(w, field + '.authority') for w in auth['witnesses']]
    science = _same_science(members)
    authority = auth['status'] if all(w['canonical_locator'] is not None for w in auth_witnesses) else 'not_established'
    state, method, chosen = 'unknown_authority', 'unresolved', None
    if science != 'same': state = 'scientific_conflict' if science == 'conflicting' else 'unsupported_group_projection'
    elif authority == 'conflicting' or relationship['effective_value'] == 'conflicting': state = 'conflicting_authority'
    elif any(r['effective_value'] in ('unknown', 'conflicting') for k, r in relations.items() if k != 'model_scope'):
        state = 'unsupported_group_projection'
    else:
        domains = [_domain(a) for s, a in members]
        if len(members) == 1:
            state, method, chosen = 'ready', 'single', members[0][0]
        elif relationship['effective_value'] == 'exact_duplicate' and domains[0] is not None and all(d == domains[0] for d in domains):
            state, method, chosen = 'ready', 'exact_equivalence', members[0][0]
        elif authority == 'source_explicit' and relationship['effective_value'] == 'same_reported_mean_and_display':
            selected = next((a for s, a in members if s == auth['reading']), None)
            domain = _domain(selected)
            checks = [_domain_relation(domain, d) for d in domains]
            if domain and domain['relation'] == 'eq' and not domain['approximate'] and all(c in ('equal', 'contains') for c in checks):
                state, method, chosen = 'ready', 'explicit_reported_mean_display', cp(auth['reading'])
            elif 'disjoint' in checks: state = 'different_domains'
        elif any(shared._response_domains_disjoint(a, b) for i, a in enumerate(domains) if a for b in domains[:i] if b):
            state = 'different_domains'
    selected_domain = _domain(next((a for s, a in members if s == chosen), None))
    qualifications = ['same_representation_not_replication'] if len(members) > 1 else []
    if any(a and a['graph_details'] for s, a in members): qualifications.append('conditional_digitization_not_sampling')
    if method == 'explicit_reported_mean_display': qualifications.append('source_explicit_reported_mean')
    origins = {a['calculation_operand']['origin'] for s, a in members if a}
    if len(origins) > 1: qualifications.append('mixed_original_origins_retained')
    model_state = ('original_source_model' if state == 'ready' and relations['model_scope']['effective_value'] in ('same', 'explicit_compatible')
        else 'none' if relations['model_scope']['effective_value'] == 'not_applicable' else 'unresolved')
    return {'role': nomination['role'], 'selection': cp(nomination),
        'witnesses': [w for r in [relationship, *relations.values()] for w in r['witnesses']] + auth_witnesses,
        'reading_selectors': [cp(s) for s, a in members], 'scientific_correspondence': science,
        'method': method, 'state': state, 'selected_reading': cp(chosen),
        'normalized_domain_checks': [{'reading': cp(s), 'relation_to_selected': _domain_relation(selected_domain, _domain(a))} for s, a in members],
        'model_state': model_state, 'qualifications': sorted(set(qualifications))}


def _requested(context, variance, model, field):
    return {'variance_status': shared._interpretation(context, variance, field + '.variance_status'),
        'model_kind': shared._interpretation(context, model, field + '.model_kind')}


def _owner_projection(arms, relationships, covariance, requested, *, variance_scope=True, model_scope=True):
    effective = shared._effective_model(requested, covariance if variance_scope else None, arms)
    if not model_scope:
        effective['model_kind'] = 'none'
    parsed = shared._calculation_inputs(arms, relationships, covariance, effective)
    owner.validate_controlled_response_owner_inputs(parsed)
    return (parsed, effective)


def _group_mask(role, members):
    """A real retained unresolved group, never an invented union origin."""
    from gene_annotation_episode.domain import identity
    actual = [a for s, a in members if a]
    if not actual or _same_science(members) != 'same': return None, 'unavailable_group_identity'
    operands = [a['calculation_operand'] for a in actual]
    if len({a['origin'] for a in operands}) != 1: return None, 'unsupported_origin_projection'
    if any(a['source_observation_id'] is None for a in operands): return None, 'unavailable_group_identity'
    dimensions = {shared.RATE_UNITS[a['unit']][0] for a in operands if a['unit']}
    if len(dimensions) != 1 or any(a['unit'] is None for a in operands): return None, 'unavailable_group_identity'
    payload = {'primary_role': role, 'primary_reading_id': operands[0]['source_observation_id'],
        'companions': [{'reading_key': s['reading_key'], 'reading_id': a['calculation_operand']['source_observation_id']} for s, a in members[1:]],
        'scientific_owner_id': operands[0]['physical_observation_id'],
        'members': [{'source_kind': a['selection']['source_kind'], 'measurement_method':
            'graph' if a['graph_details'] else 'text' if a['selection']['measurement'] else 'not_selected'} for a in actual]}
    mask = cp(operands[0])
    mask.update(value=None, threshold=None, relation='none', status='ambiguous', digitization_interval=None,
        approximate=any(a['approximate'] for a in operands), source_observation_id=identity('controlled_active_reading_group_v3', payload))
    return mask, 'ready'


def _finish_v3(context, *, arms, companion_arms, covariance_scopes):
    selected = context.arguments
    relationships = cp(context.relationships)
    roster = {(r, None): arms[r] for r in shared.PRIMITIVE_ORDER}
    roster.update({(s['role'], s['reading_key']): a for s, a in companion_arms})
    scopes = {(s['scope']['kind'], s['scope']['index']): s for s in covariance_scopes}
    base_covariance = cp(scopes[('base', None)]['whole_projection'])
    requested = _requested(context, selected['variance_status'], selected['model_kind'], 'model')
    decisions = []
    assignment = {r: None for r in shared.PRIMITIVE_ORDER}
    unresolved = []
    groups = owner._groups([arms[r]['calculation_operand'] if arms[r] else None for r in shared.PRIMITIVE_ORDER])
    canceled = {r for g in groups if g['known_owner'] and g['coefficient'] == 0 for r in g['roles']}
    for nomination in selected['reading_reconciliations']:
        role = nomination['role']
        members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
        decision = _reconcile(context, nomination, members); decisions.append(decision)
        if decision['state'] == 'ready': assignment[role] = decision['selected_reading']['reading_key']
        elif role not in canceled or _same_science(members) != 'same': unresolved.append(role)
    joint_rows, alternatives = [], []
    for i, nomination in enumerate(selected['joint_reading_assignments']):
        spec = selected['joint_scopes'][i]
        admissibility = _relation(context, nomination['admissibility'], 'joint_reading_assignments')
        relations = {k: _relation(context, spec[k], 'joint_scopes.' + k) for k in
            ('normalization', 'calibration', 'revision', 'covariance_scope', 'model_scope')}
        compatible = admissibility['effective_value']
        for k in ('normalization', 'calibration', 'revision'):
            if relations[k]['effective_value'] == 'conflicting': compatible = 'conflicting'
            elif relations[k]['effective_value'] == 'unknown' and compatible != 'conflicting': compatible = 'unknown'
        covariance = cp(scopes[('joint', i)]['whole_projection'])
        request = _requested(context, spec['variance_status'], spec['model_kind'], 'joint_scopes')
        joint_arms = {r: roster[(r, nomination['assignment'][r])] for r in shared.PRIMITIVE_ORDER}
        parsed, effective = _owner_projection(joint_arms, relationships, covariance, request,
            variance_scope=relations['covariance_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'),
            model_scope=relations['model_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'))
        joint_rows.append({'assignment_index': i, 'witnesses': admissibility['witnesses'] +
            [w for rel in relations.values() for w in rel['witnesses']], 'effective_admissibility': compatible,
            'source_covariance': covariance, 'requested_model': request, 'effective_model': effective})
        if compatible == 'compatible':
            alternatives.append({'reading_assignment': cp(nomination['assignment']), 'scope_index': i,
                'source_covariance': covariance, 'requested_model': request, 'effective_model': effective, 'calculation_inputs': parsed})
    projection, basis = None, None
    effective = {'variance_status': 'unknown', 'model_kind': 'none', 'diagnostics': []}
    if not unresolved:
        matching = next((a for a in alternatives if a['reading_assignment'] == assignment), None)
        if all(v is None for v in assignment.values()):
            projection, effective = _owner_projection(arms, relationships, base_covariance, requested,
                model_scope=all(d['model_state'] == 'original_source_model' for d in decisions if d['state'] == 'ready'))
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'base', 'scope_index': None,
                'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        elif matching:
            projection, effective = cp(matching['calculation_inputs']), cp(matching['effective_model'])
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'joint', 'scope_index': matching['scope_index'],
                'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        else:
            unresolved = [r for r, key in assignment.items() if key is not None]
    partial, partial_state = None, 'not_required'
    if projection is None:
        masked_arms = {r: cp(dict(a)) if a is not None else None for r, a in arms.items()}
        partial_state = 'ready'
        for role in unresolved:
            members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
            mask, state = _group_mask(role, members)
            if state != 'ready': partial_state = state; break
            masked_arms[role]['calculation_operand'] = mask
        if partial_state == 'ready':
            partial, unused_effective = _owner_projection(masked_arms, relationships, base_covariance, requested, model_scope=False)
    unknown_uncertainty = {'statistic': 'unknown', 'magnitude': None, 'interval': None, 'confidence_level': None,
        'count': None, 'repetition_basis': 'unknown', 'estimate_basis': 'unknown'}
    local_readings = []
    for (role, key), arm in roster.items():
        local_readings.append({'reading': _selector(role, key), 'arm': cp(arm['calculation_operand']) if arm else None,
            'reported_uncertainty': cp(arm['reported_uncertainty']['canonical']) if arm else cp(unknown_uncertainty),
            'source_kind': arm['selection']['source_kind'] if arm else None,
            'measurement_method': 'graph' if arm and arm['graph_details'] else 'text' if arm and arm['selection']['measurement'] else 'not_selected'})
    documents, source_indices = [], {}
    for scope in covariance_scopes:
        document = scope['document']
        if document is not None and document['source_ref'] not in source_indices:
            source_indices[document['source_ref']] = len(documents); documents.append(cp(document))
    pairs, pair_extractions = [], []
    for i, pair in enumerate(selected['local_pair_assignments']):
        scope = scopes[('local', i)]
        document = scope['document']
        admissibility = _relation(context, pair['admissibility'], 'local_pair_assignments.admissibility')
        scope_relation = _relation(context, pair['scope'], 'local_pair_assignments.scope')
        bindings = [b['binding'] for b in scope['bindings']]
        variance = shared._interpretation(context, pair['variance_status'], 'local_pair_assignments.variance_status')
        pair_extractions.append({'pair_key': pair['pair_key'], 'admissibility': admissibility,
            'scope': scope_relation, 'variance_status': variance})
        pairs.append({'pair_key': pair['pair_key'], 'condition': pair['condition'], 'protein': cp(pair['protein']), 'control': cp(pair['control']),
            'target': shared._relationships_inputs(relationships)[pair['condition'] + '_target'],
            'control_application': relationships[pair['condition'] + '_control_application']['effective_value'],
            'joint_admissibility': admissibility['effective_value'], 'scope_state': scope_relation['effective_value'],
            'covariance_index': source_indices[document['source_ref']] if document else None,
            'protein_binding': cp(bindings[0]) if document else None, 'control_binding': cp(bindings[1]) if document else None,
            'variance_status': variance['effective_value']})
    result = {'version': 'controlled_response_source_extraction_v3', 'selection': cp(selected), 'sources': cp(context.roster),
        'images': cp(context.images), 'arms': {r: cp(dict(a)) if a else None for r, a in arms.items()},
        'relationships': relationships, 'covariance': base_covariance, 'requested_model': requested, 'effective_model': effective,
        'calculation_inputs': projection, 'representation_reconciliations': shared._representations(arms), 'diagnostics': [],
        'implementation_dependencies': {'reader_contract_version': 'controlled_response_source_extraction_v3',
            'calculator_contract_version': 'controlled_response_owner_inputs_v2'},
        'companion_extractions': [{'reading_key': s['reading_key'], 'primary_role': s['role'], 'reading': cp(dict(a))} for s, a in companion_arms],
        'projection_status': 'ready' if projection is not None else 'unresolved_active_reconciliation', 'final_projection_basis': basis,
        'reconciliation_decisions': decisions, 'joint_scope_extractions': joint_rows, 'alternative_inputs': alternatives,
        'partial_calculation_inputs': partial, 'partial_projection_state': partial_state,
        'local_pair_extractions': pair_extractions,
        'component_local_inputs': {'version': 'controlled_response_local_inputs_v1', 'readings': local_readings, 'pairs': pairs, 'source_covariances': documents},
        'covariance_document_scopes': [{'scope': cp(s['scope']), 'document': cp(s['document'])} for s in covariance_scopes]}
    for record in result['representation_reconciliations']:
        for reading in record['readings']: reading['reading_key'] = None
    result['diagnostics'] = shared._unique_diagnostics(result, stable=True)
    Draft202012Validator(_extraction_schema()).validate(result)
    json.dumps(result, allow_nan=False)
    return cp(result)


def validate_controlled_response_v3_extraction(arguments, extraction):

    def check(selector, selected, measurement, *, source_records, image_records):
        if selected and selected['kind'] == 'linear_bar':
            arm = extraction['arms'][selector['role']] if selector['reading_key'] is None else next((row['reading'] for row in extraction['companion_extractions'] if row['primary_role'] == selector['role'] and row['reading_key'] == selector['reading_key']))
            if arm['graph_details'] is None or arm['graph_details']['measurement'] != measurement:
                shared._fail('saved_graph_measurement_mismatch', 'measurement')
            return _validate_graph(selected, arm['graph_details'], sources={(s['source_ref'], s['representation']): s for s in source_records}, images=image_records, request=arguments)
        return _validate_measurement(selected, measurement, source_records=source_records, image_records=image_records)
    return shared.validate_controlled_response_saved_science(arguments, extraction, measurement_checks=check)


__all__ = ['controlled_response_v3_arguments_schema', 'validate_controlled_response_v3_selection',
    'read_controlled_response_v3_inputs', 'validate_controlled_response_v3_extraction']
