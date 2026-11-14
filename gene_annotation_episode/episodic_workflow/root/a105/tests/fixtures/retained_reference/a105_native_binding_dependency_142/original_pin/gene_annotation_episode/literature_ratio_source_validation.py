"""Authoritative detached v2 relationship checks and exact numerical primitives.

Saved validation uses retained operands and recorded associations only: no source
callbacks, XML reader, image decoder or population function is called. It checks
arithmetic identities rather than constructing a replacement historical sheet.
Native Store/provider/caller identity remains the repository's responsibility.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
import math
import re
import sys

from .literature_ratio_source_inputs import (
    _REQUEST_SCHEMA, _EXTRACTION_SCHEMA, _SHEET_SCHEMA, _shape, _fail,
    _canonical, _diagnostic, _dependencies, _reading_key, _image_locator, _parse_status,
)

COMPONENTS = tuple(_SHEET_SCHEMA['properties']['cells']['properties'])
_NUM = re.compile(r'(?P<rel><=|>=|<|>|≤|≥)?\s*(?P<num>[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?)')
_HEX = re.compile(r'[a-f0-9]{64}')


def _same(actual, expected, field):
    if _canonical(actual) != _canonical(expected):
        _fail('saved_relationship_mismatch', field)


def _nonempty(value, field):
    if type(value) is not str or not value.strip():
        _fail('nonempty_token_required', field)


def _walk_shape(value):
    if isinstance(value, dict):
        if 'region' in value:
            box = value['region']
            if any(type(x) is not int for x in box) or box[0] >= box[2] or box[1] >= box[3]:
                _fail('nonempty_integer_image_region_required', 'region')
        if value.get('kind') in ('text', 'text_span') and (value['start'] >= value['end'] or value['end'] - value['start'] != len(value['quote'].encode('utf-8'))):
            _fail('nonempty_utf8_span_required', 'witness')
        for k, v in value.items():
            if type(v) is str and (k.endswith('_ref') or k == 'representation_id'):
                _nonempty(v, k)
            _walk_shape(v)
    elif isinstance(value, list):
        for v in value:
            _walk_shape(v)


def _meaning(m, field):
    witnesses = m['witnesses']
    state = m.get('status', m.get('value'))
    count = len({_canonical(w) for w in witnesses})
    if state in ('known', 'supported', 'different') and not count:
        _fail('interpretation_witness_required', field)
    if state == 'known':
        _nonempty(m['value'], field)
    if state in ('unknown', 'conflicting') and 'status' in m and m['value'] is not None:
        _fail('unresolved_meaning_requires_null', field)
    if state == 'conflicting' and count < 2:
        _fail('distinct_conflict_witnesses_required', field)


def _validate_selection(selection):
    _shape(selection, _REQUEST_SCHEMA, 'selection')
    _walk_shape(selection)
    for key, m in selection['comparison'].items():
        _meaning(m, 'comparison.' + key)
    ids = set()
    for row in selection['representations']:
        if row['representation_id'] in ids:
            _fail('duplicate_representation_id', 'representations')
        ids.add(row['representation_id'])
        for key in ('comparison_relation', 'physical_measurement', 'reference_measurement'):
            _meaning(row[key], key)
        if row['kind'] == 'jats_percent':
            continue
        s = row['selection']
        _meaning(s['signal_scale'], 'signal_scale')
        if row['kind'] == 'visual_signal_pair' and s['signal_scale']['value'] == 'not_applicable':
            _fail('pair_scale_state_required', 'signal_scale')
        count = len(s['candidates'])
        if s['reading_state'] == 'exact' and (count != 1 or s['fragments']):
            _fail('one_exact_candidate_required', 'candidates')
        if s['reading_state'] == 'unreadable' and (count or not s['fragments']):
            _fail('unreadable_fragment_required', 'fragments')
        if s['reading_state'] in ('ambiguous', 'conflicting'):
            signatures = {_canonical(c) for c in s['candidates']}
            if len(signatures) < 2:
                _fail('distinct_transcription_candidates_required', 'candidates')
        for c in s['candidates']:
            if (c['denominator'] is not None) != (row['kind'] == 'visual_signal_pair'):
                _fail('denominator_kind_mismatch', 'candidate')


def _view_binding(ref, m, receipt):
    if m['id'] != ref or receipt['view_ref'] != ref:
        _fail('view_receipt_mismatch', ref)
    if not 0 <= m['frame'] < m['frame_count']:
        _fail('image_frame_outside_source', ref)
    for field in ('run_id', 'episode_id', 'operation_ref'):
        _nonempty(receipt[field], 'receipt.' + field)
    if not receipt['operation_ref'].startswith('operation_') or not _HEX.fullmatch(receipt['result_sha256']):
        _fail('native_receipt_binding_required', ref)
    for field in ('native_format', 'native_initial_mode', 'selected_mode', 'display_mode', 'software_version'):
        _nonempty(m[field], 'metadata.' + field)
    if m['colour_conversion'] == 'rgb' and m['display_mode'] != 'RGB':
        _fail('rgb_display_mode_required', ref)


def _fraction(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def _rational(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _project(value):
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) and (number != 0 or value == 0) else None


def _outward(value, upper):
    number = _project(value)
    if number is None:
        return None
    actual = Fraction.from_float(number)
    if upper and actual < value:
        number = math.nextafter(number, math.inf)
    elif not upper and actual > value:
        number = math.nextafter(number, -math.inf)
    return number if math.isfinite(number) else None


def _domain(bounds):
    lo, hi, lc, uc = bounds
    lower = _outward(lo, False) if lo is not None else None
    upper = _outward(hi, True) if hi is not None else None
    if lo is not None and lower is None or hi is not None and upper is None:
        return None
    return {'lower': lower, 'lower_infinite': lo is None, 'lower_closed': lc if lo is not None else False,
        'upper': upper, 'upper_infinite': hi is None, 'upper_closed': uc if hi is not None else False,
        'meaning': 'reported_estimate_domain'}


def _literal(literal, *, percent=False):
    raw = literal.strip()
    if percent:
        if not raw.endswith('%'):
            return 'unavailable', None, None, 'unsupported_expression'
        raw = raw[:-1].strip()
    match = _NUM.fullmatch(raw)
    if not match:
        return 'unavailable', None, None, 'unsupported_expression'
    relation = {None: 'point', '<': 'lt', '<=': 'le', '≤': 'le', '>': 'gt', '>=': 'ge', '≥': 'ge'}[match['rel']]
    try:
        decimal = Decimal(match['num'].replace('−', '-'))
        # Materializing an exponent with billions of digits is outside this
        # finite export implementation. Use the interpreter's actual integer
        # string limit (not an evidence/roster limit) before allocating powers.
        digits = sys.get_int_max_str_digits() or 4300
        projected_digits = len(decimal.as_tuple().digits) + abs(decimal.as_tuple().exponent)
        if projected_digits > digits:
            return relation, None, None, 'numerical_model_range'
        # Out-of-range literal remains retained even if Python cannot materialize
        # an enormous exact integer. Ordinary overflow/underflow keeps rational.
        numerator, denominator = decimal.as_integer_ratio()
        exact = Fraction(numerator, denominator)
        rational = _rational(exact)
    except (InvalidOperation, OverflowError, ValueError):
        return relation, None, None, 'numerical_model_range'
    if exact < 0:
        return relation, None, rational, 'negative_reported_signal_unsupported'
    value = _project(exact)
    if value is None:
        return relation, None, rational, 'numerical_model_range'
    if relation == 'lt' and exact == 0:
        return relation, value, rational, 'unsupported_expression'
    return relation, value, rational, None


def _operand(literal, locator, *, percent=False):
    relation, value, exact, reason = (_literal(literal, percent=percent) if locator is not None else
        ('unavailable', None, None, 'source_dependency_unavailable'))
    refs = [locator['source_ref']] if locator else []
    return {'literal': literal, 'relation': relation, 'value': value, 'exact': exact, 'locator': deepcopy(locator),
        'diagnostics': [] if reason is None else [_diagnostic(reason, 'operand', refs)]}


def _bounds(operand, *, percent=False):
    if operand['diagnostics'] or operand['exact'] is None:
        return None
    value = _fraction(operand['exact']) / (100 if percent else 1)
    relation = operand['relation']
    if relation == 'point':
        return value, value, True, True
    if relation in ('lt', 'le'):
        return Fraction(0), value, True, relation == 'le'
    if relation in ('gt', 'ge'):
        return value, None, relation == 'ge', False
    return None


def _ratio_semantics(n, d, kind, scale):
    """One declared candidate's arithmetic; also validates saved identities."""
    reasons = [x['code'] for operand in (n, d) if operand for x in operand['diagnostics']]
    if reasons:
        return None, None, [], reasons[0]
    a = _bounds(n, percent=kind in ('visual_percent', 'jats_percent'))
    if a is None:
        return None, None, [], 'unsupported_expression'
    if d is not None:
        if scale['value'] == 'different':
            return None, None, [], 'signal_scales_differ'
        if scale['value'] != 'supported' or any(w['authentication'] == 'unavailable' for w in scale['witnesses']):
            return None, None, [], 'signal_scale_unresolved'
        b = _bounds(d)
        if b is None or b[0] < 0 or b[0] == 0 and b[2]:
            return None, None, [], 'positive_denominator_not_established'
        lo = a[0] / b[1] if b[1] is not None else Fraction(0)
        hi = None if a[1] is None or b[0] == 0 and a[1] > 0 else a[1] / b[0] if b[0] else Fraction(0)
        lc = a[2] and b[3] if b[1] is not None else a[0] == 0 and a[2]
        uc = a[3] and b[2] if hi is not None else False
        if a[0] == 0 and a[2]:
            lc = True
        if hi == 0 and a[1] == 0 and a[3]:
            uc = True
        bounds = lo, hi, lc, uc
    else:
        bounds = a
    exact = None
    if n['relation'] == 'point' and (d is None or d['relation'] == 'point'):
        exact = _fraction(n['exact']) / (100 if kind in ('visual_percent', 'jats_percent') else 1)
        if d is not None:
            exact /= _fraction(d['exact'])
    domain = _domain(bounds)
    ratio = _project(exact) if exact is not None else None
    if domain is None or exact is not None and ratio is None:
        return None, _rational(exact) if exact is not None else None, [], 'numerical_model_range'
    return ratio, _rational(exact) if exact is not None else None, [domain], None


def _ratio_reading(index, n, d, kind, scale):
    ratio, exact, domains, reason = _ratio_semantics(n, d, kind, scale)
    return {'candidate_index': index, 'numerator': n, 'denominator': d, 'ratio': ratio,
        'ratio_exact': exact, 'reported_domains': domains, 'source_reading_key': _reading_key(n, d),
        'diagnostics': [] if reason is None else [_diagnostic(reason, 'reading')]}


def _saved_witness(selected, saved, sources, views):
    _same(saved['selection'], selected, 'witness.selection')
    if selected['kind'] == 'image':
        expected = _image_locator(selected, views[selected['view_ref']])
        authentication, attribution = 'native_view_bytes_and_geometry', 'investigating_episode_interpretation'
    else:
        source = sources[(selected['source_ref'], selected['representation'])]
        expected = None if source['state'] == 'unavailable' else {
            'kind': 'text_span', 'source_ref': selected['source_ref'], 'artifact_ref': source['artifact_ref'],
            'representation': selected['representation'], 'start': selected['start'],
            'end': selected['end'], 'quote': selected['quote']}
        authentication, attribution = 'exact_utf8_span', 'literal_source_record'
    _same(saved['locator'], expected, 'witness.locator')
    _same(saved['authentication'], authentication if expected is not None else 'unavailable', 'witness.authentication')
    _same(saved['attribution'], attribution, 'witness.attribution')
    refs = [selected.get('source_ref', selected.get('view_ref'))]
    _same(saved['diagnostics'], [] if expected is not None else [_diagnostic('source_dependency_unavailable', 'witness', refs)], 'witness.diagnostics')


def _saved_meaning(selected, saved, sources, views):
    for field in selected:
        if field != 'witnesses':
            _same(saved[field], selected[field], 'meaning.' + field)
    if len(selected['witnesses']) != len(saved['witnesses']):
        _fail('witness_roster_mismatch', 'meaning')
    for a, b in zip(selected['witnesses'], saved['witnesses']):
        _saved_witness(a, b, sources, views)


def _validate_extraction(e):
    _shape(e, _EXTRACTION_SCHEMA, 'extraction')
    _validate_selection(e['selection'])
    _walk_shape(e)
    deps, view_deps = _dependencies(e['selection'])
    _same([(s['source_ref'], s['representation']) for s in e['sources']], deps, 'sources.roster')
    _same([v['view_ref'] for v in e['views']], view_deps, 'views.roster')
    sources = {(s['source_ref'], s['representation']): s for s in e['sources']}
    views = {v['view_ref']: v for v in e['views']}
    artifacts = {}
    def digest(ref, value):
        if not _HEX.fullmatch(value or ''):
            _fail('sha256_required', 'dependency')
        if ref in artifacts and artifacts[ref] != value:
            _fail('artifact_hash_alias_mismatch', ref)
        artifacts[ref] = value
    for s in e['sources']:
        available = s['state'] == 'available'
        if available:
            _nonempty(s['artifact_ref'], 'source.artifact_ref')
            digest(s['artifact_ref'], s['byte_sha256'])
        elif s['artifact_ref'] is not None or s['byte_sha256'] is not None:
            _fail('unavailable_dependency_has_bytes', 'source')
        _same(s['diagnostics'], [] if available else [_diagnostic('source_dependency_unavailable', 'source', [s['source_ref']])], 'source.diagnostics')
    receipts = set()
    for v in e['views']:
        if v['state'] == 'available':
            if v['metadata'] is None or v['own_action_receipt'] is None:
                _fail('view_metadata_receipt_required', 'view')
            _view_binding(v['view_ref'], v['metadata'], v['own_action_receipt'])
            m = v['metadata']
            digest(m['original_artifact_ref'], v['original_sha256'])
            digest(m['image_artifact_ref'], v['display_sha256'])
            receipts.add((v['own_action_receipt']['run_id'], v['own_action_receipt']['episode_id']))
        elif any(v[k] is not None for k in ('metadata', 'own_action_receipt', 'original_sha256', 'display_sha256')):
            _fail('unavailable_view_has_bytes', 'view')
        _same(v['diagnostics'], [] if v['state'] == 'available' else [_diagnostic('source_dependency_unavailable', 'view', [v['view_ref']])], 'view.diagnostics')
    if len(receipts) > 1:
        _fail('view_receipt_owner_mismatch', 'views')
    for name, meaning in e['selection']['comparison'].items():
        _saved_meaning(meaning, e['comparison'][name], sources, views)
    selected_rows = e['selection']['representations']
    if len(e['representations']) != len(selected_rows):
        _fail('representation_roster_mismatch', 'representations')
    for spec, row in zip(selected_rows, e['representations']):
        for key in ('representation_id', 'kind', 'selection'):
            _same(row[key], spec[key], 'row.' + key)
        for key in ('comparison_relation', 'physical_measurement', 'reference_measurement'):
            _saved_meaning(spec[key], row[key], sources, views)
        origin = ('synthetic' if e['evidence_origin'] == 'synthetic_fixture' else
            'reported' if row['kind'] == 'jats_percent' else 'visual_transcription')
        _same(row['origin'], origin, 'row.origin')
        visual = row['kind'] != 'jats_percent'
        selected = spec['selection']
        _same(row['reading_state'], selected['reading_state'] if visual else 'not_applicable', 'row.reading_state')
        scale = None
        if visual:
            # Scale witnesses have no separate extracted field in008; validate
            # their authenticated saved dependencies/geometry without reacquisition.
            scale = deepcopy(selected['signal_scale'])
            scale['witnesses'] = []
            for w in selected['signal_scale']['witnesses']:
                available = views[w['view_ref']]['state'] == 'available' if w['kind'] == 'image' else sources[(w['source_ref'], w['representation'])]['state'] == 'available'
                if w['kind'] == 'image':
                    _image_locator(w, views[w['view_ref']])
                scale['witnesses'].append({'authentication': 'available' if available else 'unavailable'})
            if len(row['readings']) != len(selected['candidates']):
                _fail('candidate_roster_mismatch', 'readings')
            if len(row['fragments']) != len(selected['fragments']):
                _fail('fragment_roster_mismatch', 'fragments')
            for original, fragment in zip(selected['fragments'], row['fragments']):
                _same(fragment['selection'], original, 'fragment.selection')
                expected = _image_locator(original, views[original['view_ref']])
                _same(fragment['locator'], expected, 'fragment.locator')
                _same(fragment['diagnostics'], [] if expected else [_diagnostic('source_dependency_unavailable', 'fragment', [original['view_ref']])], 'fragment.diagnostics')
            diagnostics = []
            if row['reading_state'] in ('unreadable', 'ambiguous', 'conflicting'):
                code = {'unreadable': 'unreadable_transcription', 'ambiguous': 'ambiguous_transcription', 'conflicting': 'source_representation_conflict'}[row['reading_state']]
                diagnostics = [_diagnostic(code, 'reading_state')]
            _same(row['diagnostics'], diagnostics, 'row.diagnostics')
        else:
            _same(row['fragments'], [], 'jats.fragments')
            src = sources[(selected['source_ref'], 'original')]
            if not row['readings']:
                code = 'source_dependency_unavailable' if src['state'] == 'unavailable' else 'jats_expression_capability_partial'
                _same(row['diagnostics'], [_diagnostic(code, 'jats', [selected['source_ref']])], 'jats.diagnostics')
            elif len(row['readings']) != 1 or src['state'] != 'available' or row['diagnostics']:
                _fail('jats_reading_mismatch', 'readings')
        for i, reading in enumerate(row['readings']):
            _same(reading['candidate_index'], i, 'candidate_index')
            if visual:
                candidate = selected['candidates'][i]
                for name in ('numerator', 'denominator'):
                    w, operand = candidate[name], reading[name]
                    if w is None:
                        _same(operand, None, 'reading.denominator')
                    else:
                        _same(operand['literal'], w['quote'], 'operand.literal')
                        _same(operand['locator'], _image_locator(w, views[w['view_ref']]), 'operand.locator')
            else:
                _same(reading['denominator'], None, 'jats.denominator')
                locator = reading['numerator']['locator']
                if locator is None or locator['kind'] != 'jats':
                    _fail('jats_locator_required', 'locator')
                for key in ('source_ref', 'section_id', 'paragraph_index'):
                    _same(locator[key], selected[key], 'jats.' + key)
                _same(locator['artifact_ref'], src['artifact_ref'], 'jats.artifact_ref')
                start, end = locator['expression_start'], locator['expression_end']
                if not 0 <= start < end <= len(locator['paragraph_text']):
                    _fail('jats_expression_bounds', 'locator')
                _same(locator['paragraph_text'][start:end], locator['expression'], 'jats.expression')
                # Saved-only finite grammar validation; no XML/parser call. Exact
                # expression retains complete percentage and variant label.
                m = re.fullmatch(r'(?P<number>[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?)\s*%\s*\((?P<label>[^()]*)\)', locator['expression'])
                if m is None or not re.search(r'(?<!\w)' + re.escape(selected['variant']) + r'(?!\w)', m['label']):
                    _fail('jats_expression_literal_mismatch', 'locator')
                _same(reading['numerator']['literal'], m['number'] + '%', 'jats.literal')
                text = locator['paragraph_text']
                if not re.search(r'(?<!\w)' + re.escape(selected['expected_subject']) + r'(?!\w)', text):
                    _fail('jats_subject_mismatch', 'locator')
                # Preserve denominator association in the retained paragraph.
                after = text[end:]
                first_of = re.search(r'(?<!\w)of\s+', after)
                if first_of is None or not after[first_of.end():].startswith(selected['reference_literal']):
                    _fail('jats_reference_mismatch', 'locator')
            for name in ('numerator', 'denominator'):
                operand = reading[name]
                if operand is None:
                    continue
                percent = name == 'numerator' and row['kind'] in ('visual_percent', 'jats_percent')
                relation, value, exact, reason = _literal(operand['literal'], percent=percent) if operand['locator'] is not None else ('unavailable', None, None, 'source_dependency_unavailable')
                for key, expected in (('relation', relation), ('value', value), ('exact', exact)):
                    _same(operand[key], expected, 'operand.' + key)
                refs = [operand['locator']['source_ref']] if operand['locator'] else []
                _same(operand['diagnostics'], [] if reason is None else [_diagnostic(reason, 'operand', refs)], 'operand.diagnostics')
            ratio, exact, domains, reason = _ratio_semantics(reading['numerator'], reading['denominator'], row['kind'], scale)
            for key, expected in (('ratio', ratio), ('ratio_exact', exact), ('reported_domains', domains),
                    ('source_reading_key', _reading_key(reading['numerator'], reading['denominator'])),
                    ('diagnostics', [] if reason is None else [_diagnostic(reason, 'reading')])):
                _same(reading[key], expected, 'reading.' + key)
        _same(row['parse_status'], _parse_status(row), 'row.parse_status')


def _log_fraction(value):
    if value <= 0:
        return None
    if value == 1:
        return 0.0
    # Decimal division with enough significant digits to retain distance from1
    # avoids math.log(float(exact)) turning a nonunit rational into exact0.
    with localcontext() as context:
        context.prec = max(len(str(abs(value.numerator))), len(str(value.denominator))) + 50
        result = (Decimal(value.numerator) / Decimal(value.denominator)).ln()
        out = float(result)
    return out if math.isfinite(out) and out != 0 else None


def _domain_transform(reading, component):
    """Transform a retained domain with outward finite projection."""
    if not reading['reported_domains']:
        return []
    exact = _fraction(reading['ratio_exact']) if reading['ratio_exact'] else None
    domain = reading['reported_domains'][0]
    if exact is not None:
        if component == 'reported_ratio':
            return deepcopy(reading['reported_domains'])
        if component == 'difference_from_reference':
            projected = _domain((exact - 1, exact - 1, True, True))
            return [projected] if projected else []
        value = _log_fraction(exact)
        if value is None:
            return []
        # The numerical log bound is conservatively rounded outward.
        lo = value if exact == 1 else math.nextafter(value, -math.inf)
        hi = value if exact == 1 else math.nextafter(value, math.inf)
        if not math.isfinite(lo) or not math.isfinite(hi):
            return []
        return [{**domain, 'lower': lo, 'upper': hi, 'lower_infinite': False, 'upper_infinite': False,
            'lower_closed': True, 'upper_closed': True}]
    if component == 'reported_ratio':
        return deepcopy(reading['reported_domains'])
    out = deepcopy(domain)
    if component == 'difference_from_reference':
        for end, upper in (('lower', False), ('upper', True)):
            if not domain[end + '_infinite']:
                projected = _outward(Fraction.from_float(domain[end]) - 1, upper)
                if projected is None:
                    return []
                out[end] = projected
    else:
        # Positive branch only: zero can be the lower limit, never a log point.
        if not domain['upper_infinite'] and domain['upper'] <= 0:
            return []
        if domain['lower_infinite'] or domain['lower'] <= 0:
            out.update(lower=None, lower_infinite=True, lower_closed=False)
        else:
            value = _log_fraction(Fraction.from_float(domain['lower']))
            if value is None:
                return []
            out['lower'] = math.nextafter(value, -math.inf)
        if not domain['upper_infinite']:
            value = _log_fraction(Fraction.from_float(domain['upper']))
            if value is None:
                return []
            out['upper'] = math.nextafter(value, math.inf)
    return [out]


def _association(row):
    relation = row['comparison_relation']
    if relation['value'] == 'supported' and any(w['authentication'] == 'unavailable' for w in relation['witnesses']):
        return 'unknown'
    return relation['value']


def _facts(e):
    """Saved roster semantics, not a replacement sheet or interpretation.

    Shared by initial population and saved relationship checks so they cannot
    disagree about selected completeness, linked source conflict or dedup aliases.
    """
    rows, readings, seen, reasons = e['representations'], [], set(), []
    resolved, points, conflict = bool(rows), bool(rows), False
    if not rows:
        reasons.append('no_selected_representations')
    exacts, certain = set(), set()
    for row in rows:
        association = _association(row)
        if association != 'supported':
            resolved = points = False
            reasons.append('different_reported_quantities' if association == 'different' else 'comparison_association_unresolved')
        state = row['reading_state']
        if state not in ('exact', 'not_applicable'):
            resolved = points = False
            reasons.append({'unreadable': 'unreadable_transcription', 'ambiguous': 'ambiguous_transcription', 'conflicting': 'source_representation_conflict'}[state])
        if association == 'supported' and state == 'conflicting':
            conflict = True
        if row['parse_status'] != 'parsed':
            resolved = points = False
            reasons.extend(d['code'] for d in row['diagnostics'])
        if not row['readings']:
            resolved = points = False
        row_exacts = set()
        for reading in row['readings']:
            if not reading['reported_domains']:
                resolved = points = False
                reasons.extend(d['code'] for d in reading['diagnostics'])
            if reading['ratio'] is None:
                points = False
                if reading['reported_domains']:
                    reasons.append('reported_limit_not_point')
            if association != 'supported':
                continue
            signature = (reading['source_reading_key'], _canonical(reading['ratio_exact']), _canonical(reading['reported_domains']))
            if signature not in seen:
                readings.append(reading)
                seen.add(signature)
            if reading['ratio_exact'] is not None and reading['ratio'] is not None:
                exact = _fraction(reading['ratio_exact'])
                exacts.add(exact)
                row_exacts.add(exact)
        if association == 'supported' and state in ('exact', 'not_applicable') and len(row_exacts) == 1:
            certain.update(row_exacts)
    conflict = conflict or len(certain) > 1
    # Complete ambiguous alternatives remain incomplete as point interpretations.
    full = resolved and points and len(exacts) == 1 and not conflict
    reason = None if full else ('incomplete_conflicting_representations' if conflict and not resolved else
        'source_representation_conflict' if conflict else next(iter(reasons), 'unsupported_expression'))
    return {'resolved': resolved, 'complete': resolved and points, 'conflict': conflict,
        'readings': readings, 'exacts': sorted(exacts), 'point': next(iter(exacts)) if full else None,
        'reason': reason}


_FORMULAS = {
    'reported_ratio': 'printed_ratio; printed_percent/100; or printed_numerator/printed_reference',
    'difference_from_reference': 'reported_ratio-1', 'log_reported_ratio': 'ln(reported_ratio), positive branch',
    'calibrated_amount_ratio': 'applicable_calibrated_amount_response',
    'amount_adjusted_effect': 'applicable_functional_response_at_matched_amount',
    'source_profile_log_ratio': 'supported_joint_observation_model', 'source_signed_index': 'tanh(source_profile_log_ratio/2)',
}
_LIMITS = {'calibrated_amount_ratio': 'calibrated_amount_conversion_unimplemented',
    'amount_adjusted_effect': 'functional_response_conversion_unimplemented',
    'source_profile_log_ratio': 'observation_model_unimplemented', 'source_signed_index': 'observation_model_unimplemented'}


def _component_contract(e, name):
    unit = ('dimensionless' if name in ('log_reported_ratio', 'source_profile_log_ratio', 'source_signed_index')
        else None if name == 'amount_adjusted_effect' else 'fraction')
    origin = 'proposed' if name == 'source_signed_index' else 'derived'
    if name == 'reported_ratio':
        origins = {row['origin'] for row in e['representations']}
        origin = next(iter(origins)) if len(origins) == 1 else 'derived'
    conditional = [] if name in _LIMITS else ['source_comparison_interpretation']
    if conditional and any(row['kind'] == 'visual_signal_pair' for row in e['representations']):
        conditional.append('nominated_printed_signal_pair')
    return unit, origin, conditional


def _transform(exact, name):
    if name == 'reported_ratio':
        return _project(exact)
    if name == 'difference_from_reference':
        return _project(exact - 1)
    return _log_fraction(exact)


def _validate_cell(cell, e, facts, name):
    """Check equations on saved operands; never construct a replacement cell."""
    unit, origin, conditional = _component_contract(e, name)
    for field, expected in (('unit', unit), ('origin', origin), ('conditional_on', conditional), ('formula', _FORMULAS[name])):
        _same(cell[field], expected, 'cell.' + name + '.' + field)
    if name in _LIMITS:
        for field, expected in (('value', None), ('value_candidates', []), ('reported_domains', []),
                ('status', 'unavailable'), ('unavailable_reason', _LIMITS[name])):
            _same(cell[field], expected, 'cell.' + name + '.' + field)
        return
    # Each candidate is exactly a transform of at least one retained rational;
    # each transform with a finite projection occurs once. Rounded equality
    # cannot erase the exact source-conflict flag checked separately.
    projected = {_transform(x, name) for x in facts['exacts']}
    projected.discard(None)
    if cell['value_candidates'] != sorted(projected):
        _fail('candidate_transform_mismatch', 'cell.' + name)
    point = facts['point']
    expected_value = _transform(point, name) if point is not None else None
    _same(cell['value'], expected_value, 'cell.' + name + '.value')
    reason = facts['reason']
    if point is not None and expected_value is None:
        reason = 'zero_reported_ratio' if name == 'log_reported_ratio' and point == 0 else 'numerical_model_range'
    status = 'populated' if cell['value'] is not None else 'conflicting' if facts['conflict'] and facts['resolved'] else 'unavailable'
    if name == 'log_reported_ratio' and 0 in facts['exacts']:
        if not facts['conflict']:
            reason = 'zero_reported_ratio'
        if cell['value'] is None:
            status = 'unavailable'
    _same(cell['unavailable_reason'], reason, 'cell.' + name + '.reason')
    _same(cell['status'], status, 'cell.' + name + '.status')
    cursor = 0
    for reading in facts['readings']:
        domains = _domain_transform(reading, name)
        _same(cell['reported_domains'][cursor:cursor + len(domains)], domains, 'cell.' + name + '.domains')
        cursor += len(domains)
    if cursor != len(cell['reported_domains']):
        _fail('domain_roster_mismatch', 'cell.' + name)


def validate_relative_signal_saved(selection, extraction, sheet, saved_outcome):
    """Validate detached saved relationships, with no original source access.

    This does not authenticate actual provider/owner/request artifacts in Store.
    Those actual record checks are required in the native repository separately.
    """
    _validate_selection(selection)
    _validate_extraction(extraction)
    _same(extraction['selection'], selection, 'selection')
    _shape(sheet, _SHEET_SCHEMA, 'sheet')
    facts = _facts(extraction)
    for name, key in (('selected_roster_resolved', 'resolved'), ('point_candidate_set_complete', 'complete'), ('known_source_conflict', 'conflict')):
        _same(sheet[name], facts[key], 'sheet.' + name)
    for name in COMPONENTS:
        _validate_cell(sheet['cells'][name], extraction, facts, name)
    if type(saved_outcome) is not dict or set(saved_outcome) != {'status', 'operation_ref', 'record_refs', 'changed_record_refs', 'result', 'feedback'}:
        _fail('closed_fields_required', 'saved_outcome')
    _same(saved_outcome['status'], 'completed', 'outcome.status')
    _same(saved_outcome['feedback'], None, 'outcome.feedback')
    op = saved_outcome['operation_ref']
    if type(op) is not str or not op.startswith('operation_') or not op.removeprefix('operation_'):
        _fail('operation_reference_required', 'outcome.operation_ref')
    for field in ('record_refs', 'changed_record_refs'):
        refs = saved_outcome[field]
        if type(refs) is not list or any(type(ref) is not str or not ref.strip() for ref in refs) or len(set(refs)) != len(refs):
            _fail('unique_reference_array_required', 'outcome.' + field)
    if not set(saved_outcome['changed_record_refs']) <= set(saved_outcome['record_refs']):
        _fail('changed_record_subset_required', 'outcome')
    result = saved_outcome['result']
    if type(result) is not dict or set(result) != {'sheet_ref', 'cells', 'selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict'}:
        _fail('closed_fields_required', 'outcome.result')
    ref = result['sheet_ref']
    if type(ref) is not str or not ref.startswith('source_') or ref not in saved_outcome['record_refs']:
        _fail('sheet_output_membership_required', 'outcome.result.sheet_ref')
    _same(result['cells'], sheet['cells'], 'outcome.cells')
    for field in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict'):
        _same(result[field], sheet[field], 'outcome.' + field)


__all__ = ['validate_relative_signal_saved']
