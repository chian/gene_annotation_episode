"""Source-bound precision/Z-prime and possessed recovery operands.

Scientific relationships are explicit caller interpretations. Callbacks authorize
received facts; this module performs no acquisition, private-sheet lookup or IO.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import re

from .domain import REF, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _interpretation, _witness_schema
from .literature_calibration_recovery_calculations import _float, _q
from .literature_experimental_contracts import ExperimentalContractError
from .literature_partner_source_fields import (
    _ALL_TAGS, _NUMBER, _LOWER, _contexts, _interval_contexts,
    _relation, _soft_break_numeric_token, _unit_contexts, _TABLE_BOUNDARY, _edge_contexts,
    number_selector_schema,
)

VERSION = 'a105_measurement_validation_inputs_v1'
NAMESPACE = 'literature_calibration_recovery_cells'
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'synthetic_fixture')
ORIGINS = {'primary_source': 'reported', 'retained_extraction': 'derived', 'synthetic_fixture': 'synthetic'}
CONTEXT_FIELDS = ('experiment', 'analyte', 'matrix', 'method', 'endpoint', 'repetition',
                  'mean_definition', 'nominal_uncertainty')
RELATIONSHIPS = {
    'basis': ('within_run', 'between_run', 'between_preparation', 'unspecified', 'unknown', 'conflicting'),
    'mean_precision_population': ('same', 'different', 'unknown', 'conflicting'),
    'cv_denominator': ('displayed_measured_mean', 'other_reported_mean', 'unknown', 'conflicting'),
    'recovery_context': ('same', 'different', 'unknown', 'conflicting'),
    'validation_relation': ('held_out_observations_and_stock_supported', 'shared_fit_or_stock', 'unknown', 'conflicting'),
}
FORMULA_RELATIONS = ('conventional_zprime', 'different', 'unknown', 'conflicting')
PAIR_REASONS = ('recovery_pair_not_supplied', 'recovery_pair_incomplete', 'recovery_pair_identity_mismatch',
    'recovery_pair_dependencies_mismatch', 'recovery_pair_exact_identity_mismatch',
    'recovery_pair_unavailable', 'recovery_pair_units_mismatch', 'recovery_pair_scope_mismatch',
    'recovery_pair_control_unknown', 'recovery_pair_control_conflicting',
    'enzyme_activity_spike_is_not_reporter_standard', 'recovery_pair_source_meanings_mismatch')
NUMBER_REASONS = ('source_approximation_unimplemented', 'source_range_unimplemented',
                  'nonfinite_source_statistic_unavailable', 'source_negated_comparison_unimplemented')
RELATIONS = ('point', 'lt', 'le', 'gt', 'ge', 'approximate', 'range', 'unresolved')
_SCALAR = r'[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?'
_RANGE = re.compile(r'\s*(?:(?:between\s+|from\s+)?' + _SCALAR
    + r'\s*(?:[–—]|\s*-\s*|\bto\b|\band\b)\s*' + _SCALAR
    + r'|\[\s*' + _SCALAR + r'\s*,\s*' + _SCALAR + r'\s*\])\s*\Z', re.I)
_APPROX_MARKER = r'(?:[~≈≃≅∼]|\b(?:approximately|about|circa|approx\.?))'
_APPROX = re.compile(_APPROX_MARKER + r'\s*(?:[<>]=?|[≤≥])?\s*$', re.I)
_APPROX_POINT = re.compile(r'\s*' + _APPROX_MARKER + r'\s*(?P<point>' + _SCALAR + r')\s*\Z', re.I)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}


def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}


def _exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
                'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})


def _exact(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _interpreted_schema(values, enriched=False):
    witness = _retained_witness_schema() if enriched else _witness_schema()
    return obj({**({'kind': {'const': 'source_interpretation'}} if enriched else {}),
        'value': {'enum': list(values)}, 'witnesses': _array(witness)})


def _retained_witness_schema():
    return obj({**deepcopy(_witness_schema()['properties']), 'artifact_ref': deepcopy(REF)})


def recovery_selector_schema(component):
    if component not in ('recovery', 'relative_bias'):
        _fail('unsupported_recovery_operand', 'component')
    return obj({'namespace': {'const': NAMESPACE}, 'sheet_ref': deepcopy(REF),
                'component': {'const': component}})


def measurement_validation_population_schema():
    precision = obj({'number': number_selector_schema(), 'quantity_label': _witness_schema(),
        'unit': obj({'value': {'enum': ['percent', 'fraction']}, 'witness': _witness_schema()}),
        **{name: _interpreted_schema(values) for name, values in RELATIONSHIPS.items()}})
    zprime = obj({'number': number_selector_schema(), 'quantity_label': _witness_schema(),
                  'formula_relation': _interpreted_schema(FORMULA_RELATIONS)})
    return obj({'source_ref': deepcopy(REF), 'source_kind': {'enum': list(SOURCE_KINDS)},
        'context': obj({name: _nullable(_witness_schema()) for name in CONTEXT_FIELDS}),
        **{role: _nullable(recovery_selector_schema(role)) for role in ('recovery', 'relative_bias')},
        'precision': _array(precision), 'zprime': _array(zprime)})


def _number_schema():
    selector = obj({**number_selector_schema()['properties'], 'witness': _retained_witness_schema()})
    return obj({'selector': selector, 'raw_number': {'type': 'string', 'minLength': 1},
        'native_value': {'type': ['number', 'null']}, 'native_exact_value': _nullable(_exact_schema()),
        'relation': {'enum': list(RELATIONS)}, 'capability_reason': {'enum': [*NUMBER_REASONS, None]},
        'representation_witness': _retained_witness_schema(),
        'measurement_key': deepcopy(REF), 'number_start_bytes': {'type': 'integer', 'minimum': 0},
        'number_end_bytes': {'type': 'integer', 'minimum': 1}, 'origin': {'enum': list(ORIGINS.values())}})


def _row_schema():
    # Reuse the actual projected-fact contract, without looking up a sheet.
    from .literature_calibration_recovery_storage import calibration_recovery_cells_schema
    return deepcopy(calibration_recovery_cells_schema()['items'])


def measurement_validation_extraction_schema():
    witness = _retained_witness_schema()
    precision = obj({'number': _number_schema(), 'quantity_label': witness,
        'unit': obj({'value': {'enum': ['percent', 'fraction']}, 'witness': witness}),
        **{name: _interpreted_schema(values, True) for name, values in RELATIONSHIPS.items()},
        'aliases': _array(obj({**number_selector_schema()['properties'], 'witness': witness}))})
    zprime = obj({'number': _number_schema(), 'quantity_label': witness,
        'formula_relation': _interpreted_schema(FORMULA_RELATIONS, True),
        'aliases': _array(obj({**number_selector_schema()['properties'], 'witness': witness}))})
    operand = lambda role: _nullable(obj({'selection': recovery_selector_schema(role), 'row': _row_schema()}))
    return obj({'version': {'const': VERSION}, 'source_ref': deepcopy(REF), 'artifact_ref': deepcopy(REF),
        'source_kind': {'enum': list(SOURCE_KINDS)}, 'context': obj({name: _nullable(obj({
            'value': {'type': 'string', 'minLength': 1}, 'witness': witness})) for name in CONTEXT_FIELDS}),
        'recovery': operand('recovery'), 'relative_bias': operand('relative_bias'),
        'pair_unavailable_reasons': _array({'enum': list(PAIR_REASONS)}, True),
        'precision': _array(precision), 'zprime': _array(zprime),
        'input_origins': _array({'enum': list(ORIGINS.values())}, True),
        'source_refs': _array(REF, True)})


def _visible(raw):
    return html.unescape(_ALL_TAGS.sub('', raw))


def _visible_span(sources, witness, start, end, field):
    """Markup attributes and entity codepoints are not printed statistics."""
    raw = sources.source(witness['source_ref'], witness['representation'])['content']
    for position in (start, end - 1):
        prefix = raw[:position]
        tag_start = prefix.rfind(b'<')
        complete_selected_tag = position == end - 1 and raw[position:position+1] == b'>' and tag_start >= start
        if (tag_start > prefix.rfind(b'>') and not complete_selected_tag
                and re.match(rb'</?[A-Za-z_]|<!--|<\?', prefix[tag_start:])):
            _fail('source_markup_is_not_statistic', field)
        ampersand = prefix.rfind(b'&')
        complete_selected_entity = position == end - 1 and raw[position:position+1] == b';' and ampersand >= start
        if (ampersand > prefix.rfind(b';') and not complete_selected_entity
                and re.fullmatch(rb'&(?:#(?:x[0-9a-fA-F]*|[0-9]*)?|[A-Za-z]*)', prefix[ampersand:])):
            _fail('partial_source_entity', field)


def _field_witness(sources, witness, start, end):
    """Retain the complete containing visible field, including source qualifiers."""
    source = sources.source(witness['source_ref'], witness['representation'])['content']
    opening = list(re.finditer(rb'<(?:td|th|p|title|caption)\b[^>]*>', source[:start], re.I))
    left = opening[-1].end() if opening else 0
    closing = re.search(rb'</(?:td|th|p|title|caption)\s*>', source[end:], re.I)
    right = end + closing.start() if closing else len(source)
    raw = source[left:right].decode('utf-8')
    return sources.witness({'source_ref': witness['source_ref'], 'representation': witness['representation'],
        'start': left, 'end': right, 'quote': raw}, 'number.representation')


def _read_number(selector, sources, origin):
    witness = sources.witness(selector['witness'], 'number.witness')
    ns, ne = selector['number_start'], selector['number_end']
    if not 0 <= ns < ne <= len(witness['quote']):
        _fail('source_number_span_order_invalid', 'number')
    token = witness['quote'][ns:ne]
    prefix, suffix = _contexts(sources, witness, ns, ne)
    interval = _interval_contexts(sources, witness, ns, ne)
    capability = None
    if _NUMBER.fullmatch(token):
        # The shared classifier intentionally rejects lower limits and source
        # approximations. Strip only those detected markers for its remaining
        # interval/uncertainty checks, then retain their distinct native meaning.
        lower = _LOWER.search(prefix)
        postfix_lower = re.match(r'\s*(?:or\s+(?:more|greater)|and\s+above)\b', suffix, re.I)
        approx = _APPROX.search(prefix)
        postfix_approx = re.match(r'\s*(?:approximately|approx\.?|circa)\b', suffix, re.I)
        negated = re.search(r'\bnot\s+(?:(?:significantly|substantially|clearly)\s+)?(?:[<>]=?|[≤≥]|less\s+than|more\s+than|greater\s+than|below|above|at\s+(?:most|least))\s*$', prefix, re.I)
        marker = negated or approx or lower
        adjusted_prefix = prefix[:marker.start()] if marker else prefix
        adjusted_suffix = suffix[(postfix_lower or postfix_approx).end():] if postfix_lower or postfix_approx else suffix
        adjusted_prefix, adjusted_suffix = _edge_contexts(adjusted_prefix, adjusted_suffix)
        relation = _relation(adjusted_prefix, adjusted_suffix, role='rate', interval_contexts=interval)
        if lower or postfix_lower:
            marker = '' if lower is None else lower.group().lower()
            relation = 'ge' if re.search(r'>=|≥|at\s+least|no\s+less|equal', marker) else 'gt'
        if approx or postfix_approx:
            relation, capability = 'approximate', 'source_approximation_unimplemented'
        if negated:
            relation, capability = 'unresolved', 'source_negated_comparison_unimplemented'
        before, after = prefix[-1:], suffix[:1]
        stop = after == '.' and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ')]};:')
        if (_soft_break_numeric_token(sources, witness, ns, ne, token, pm_spread=False)
                or before and (before in '.eE+−-' or before.isdigit() or before.isalpha() or before == '_')
                or after and (after in '.eE+−-' or after.isdigit()) and not stop):
            _fail('partial_source_numeric_token', 'number')
        if re.search(r'\d,\s*$', prefix) or re.match(r',\s*\d', suffix):
            _fail('comma_source_number_unsupported', 'number')
        native = Fraction(token.replace('−', '-'))
    elif _RANGE.fullmatch(token) or _APPROX_POINT.fullmatch(token):
        if (prefix[-1:] and (prefix[-1:].isalnum() or prefix[-1:] in '.eE+−-_')
                or suffix[:1] and (suffix[:1].isdigit() or suffix[:1] in '.eE+−-')):
            _fail('partial_source_numeric_token', 'number')
        approximate_point = _APPROX_POINT.fullmatch(token)
        if approximate_point:
            relation, capability = 'approximate', 'source_approximation_unimplemented'
            native = Fraction(approximate_point.group('point').replace('−', '-'))
        else:
            relation, capability, native = 'range', 'source_range_unimplemented', None
    elif re.fullmatch(r'[+−-]?(?:NaN|Inf|Infinity)', token, re.I):
        if prefix[-1:].isalnum() or suffix[:1].isalnum():
            _fail('partial_source_numeric_token', 'number')
        relation, capability, native = 'point', 'nonfinite_source_statistic_unavailable', None
    else:
        _fail('literal_source_number_or_complete_range_required', 'number')
    start = witness['start'] + len(witness['quote'][:ns].encode())
    end = witness['start'] + len(witness['quote'][:ne].encode())
    _visible_span(sources, witness, start, end, 'number')
    return {'selector': {**deepcopy(selector), 'witness': witness}, 'raw_number': token,
        'native_value': None if native is None else _float(native),
        'native_exact_value': None if native is None else _exact(native), 'relation': relation,
        'capability_reason': capability, 'representation_witness': _field_witness(sources, witness, start, end),
        'measurement_key': identity('literature_measurement', {'artifact_ref': witness['artifact_ref'],
            'number_start': start, 'number_end': end}), 'number_start_bytes': start, 'number_end_bytes': end,
        'origin': origin}


def _table_cells(sources, witness):
    """A bounded XML table geometry guard, not a scientific-meaning classifier."""
    raw = sources.source(witness['source_ref'], witness['representation'])['content']
    start, end = witness['start'], witness['end']
    for table in re.finditer(rb'<table\b[^>]*>.*?</table\s*>', raw, re.I | re.S):
        if not table.start() <= start < end <= table.end():
            continue
        cells, occupied = [], {}
        for row_index, row in enumerate(re.finditer(rb'<tr\b[^>]*>.*?</tr\s*>', table.group(), re.I | re.S)):
            column = 0
            for cell in re.finditer(rb'<(td|th)\b([^>]*?)(?:/\s*>|>.*?</(?:td|th)\s*>)', row.group(), re.I | re.S):
                while occupied.get(column, -1) >= row_index:
                    column += 1
                attrs = cell.group(2)
                def span(name):
                    found = re.search(name + rb'\s*=\s*[\'\"]([0-9]+)[\'\"]', attrs, re.I)
                    result = int(found.group(1)) if found else 1
                    if result < 1:
                        _fail('ambiguous_source_table_geometry', 'quantity_label')
                    return result
                width, height = span(b'colspan'), span(b'rowspan')
                columns = tuple(range(column, column + width))
                if any(occupied.get(c, -1) >= row_index for c in columns):
                    _fail('ambiguous_source_table_geometry', 'quantity_label')
                for c in columns:
                    occupied[c] = row_index + height - 1
                left = table.start() + row.start() + cell.start()
                cells.append({'start': left, 'end': left + len(cell.group()), 'row': row_index,
                              'columns': columns, 'header': cell.group(1).lower() == b'th'})
                column += width
        return (table.start(), table.end()), cells
    return None, []


def _associate(number, witness, sources, field):
    anchor = number['selector']['witness']
    if witness['artifact_ref'] != anchor['artifact_ref'] or witness['representation'] != anchor['representation']:
        _fail('borrowed_source_quantity_witness', field)
    numeric = {**anchor, 'start': number['number_start_bytes'], 'end': number['number_end_bytes']}
    table, cells = _table_cells(sources, numeric)
    if table is None:
        return
    selected = next((c for c in cells if c['start'] <= numeric['start'] < numeric['end'] <= c['end']), None)
    label = next((c for c in cells if c['start'] <= witness['start'] < witness['end'] <= c['end']), None)
    if (selected is None or label is None or not set(selected['columns']) & set(label['columns'])
            or label != selected and (not label['header'] or label['row'] > selected['row'])):
        _fail('source_quantity_column_mismatch', field)


def _label(witness, kind, number, sources):
    value = sources.witness(witness, 'quantity_label')
    _visible_span(sources, value, value['start'], value['end'], 'quantity_label')
    text = _visible(value['quote'])
    pattern = r'\bCV\b|coefficient\s+of\s+variation' if kind == 'cv' else r'\bZ\s*[\'’′]\s*(?:[-–]?\s*factor)?|\bZ\s*prime\b'
    if not re.search(pattern, text, re.I):
        _fail('source_statistic_label_mismatch', 'quantity_label')
    before, after = _unit_contexts(sources, value, 0, len(value['quote']))
    if before[-1:].isalpha() or after[:1].isalpha():
        _fail('partial_source_statistic_label', 'quantity_label')
    opposing = r'\bRE\b|relative\s+error|\bZ\s*[\'’′]|\bZ\s*prime\b' if kind == 'cv' else r'\bCV\b|coefficient\s+of\s+variation|\bRE\b|relative\s+error'
    if re.search(opposing, text, re.I):
        _fail('ambiguous_source_statistic_label', 'quantity_label')
    _associate(number, value, sources, 'quantity_label')
    return value


def _unit_value(raw):
    parts = [_visible(p).strip() for p in _TABLE_BOUNDARY.split(raw)]
    if sum(bool(p) for p in parts) > 1:
        _fail('multiple_source_unit_fields', 'unit')
    text = re.sub(r'\s+', ' ', _visible(raw)).strip().lower()
    if text in ('%', '%cv', 'percent', 'per cent', 'percent coefficient of variation'):
        return 'percent'
    if text in ('fraction', 'dimensionless', '1'):
        return 'fraction'
    _fail('unsupported_precision_unit', 'unit')


def _unit(value, number, sources):
    witness = sources.witness(value['witness'], 'unit')
    _visible_span(sources, witness, witness['start'], witness['end'], 'unit')
    before, after = _unit_contexts(sources, witness, 0, len(witness['quote']))
    if (before[-1:] and (before[-1:].isalpha() or before[-1:] in '_µμ/^%−⁻¹')
            or re.match(r'(?:[A-Za-z0-9µμ/_^%−⁻¹-]|\s*(?:/|\^)|\s+[A-Za-zµμ]+\s*(?:[/^]|[-−⁻]\s*[1¹]))', after)):
        _fail('partial_source_unit', 'unit')
    actual = _unit_value(witness['quote'])
    if actual != value['value']:
        _fail('precision_unit_mismatch', 'unit')
    if _visible(witness['quote']).strip() == '1':
        if before[-1:] and (before[-1:].isdigit() or before[-1:] in '.eE+−-') or after[:1] and (after[:1].isdigit() or after[:1] in '.eE+−-'):
            _fail('partial_source_unit', 'unit')
    _associate(number, witness, sources, 'unit')
    _explicit_unit(number, actual, sources)
    return {'value': actual, 'witness': witness}


def _explicit_unit(number, expected, sources):
    selected = number['selector']
    _, tail = _unit_contexts(sources, selected['witness'], selected['number_start'], selected['number_end'])
    visible = _visible(tail).lstrip()
    # A printed unit after a spread still applies to the selected magnitude.
    pm = re.match(r'(?:±|\+\s*/\s*-|\+\s*−)\s*[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?\s*', visible)
    if pm:
        visible = visible[pm.end():]
    match = re.match(r'(?:%CV\b|%|percent\b|per\s+cent\b|fraction\b|dimensionless\b)', visible, re.I)
    if match:
        if re.match(r'(?:[A-Za-z0-9/_^%−⁻¹-]|\s*[/^]|\s+[A-Za-zµμ]+\s*(?:/|[-−⁻]\s*[1¹]))', visible[match.end():]):
            _fail('partial_source_unit', 'number.unit')
        if _unit_value(match.group()) != expected:
            _fail('explicit_precision_unit_mismatch', 'number.unit')
    elif re.match(r'(?:[pnumµμ]?mol(?:e)?|[pnumµμ]?M|mg|ug|µg|μg|g|s|min|Hz)(?=\b|/)', visible):
        _fail('explicit_precision_unit_mismatch', 'number.unit')


def recovery_pair_reasons(recovery, bias):
    if recovery is None and bias is None:
        return ['recovery_pair_not_supplied']
    if recovery is None or bias is None:
        return ['recovery_pair_incomplete']
    r, b = recovery['row'], bias['row']
    reasons = []
    if any(r[k] != b[k] for k in ('sheet_ref', 'evidence_source_ref', 'source_kind', 'input_origins', 'control_kind', 'section', 'applicability', 'spread_kind', 'interpretation_scope_unavailable_reason')):
        reasons.append('recovery_pair_identity_mismatch')
    from .literature_calibration_recovery_calculations import FORMULAS
    if any(row['formula'] != FORMULAS[role] or row['origin'] != 'derived'
           or row['input_origins'] != [ORIGINS[row['source_kind']]]
           or (row['status'] == 'populated') != (row['unavailable_reason'] is None)
           for row, role in ((r, 'recovery'), (b, 'relative_bias'))):
        reasons.append('recovery_pair_identity_mismatch')
    if r['source_meanings'] != b['source_meanings']:
        reasons.append('recovery_pair_source_meanings_mismatch')
    if not r['input_measurement_keys'] or r['input_measurement_keys'] != b['input_measurement_keys']:
        reasons.append('recovery_pair_dependencies_mismatch')
    if r['unit'] != 'fraction' or b['unit'] != 'fraction':
        reasons.append('recovery_pair_units_mismatch')
    if any(row['status'] != 'populated' or row['exact_value'] is None or row['value'] is None for row in (r, b)):
        reasons.append('recovery_pair_unavailable')
    else:
        rq, bq = _q(r['exact_value']), _q(b['exact_value'])
        if rq - 1 != bq or r['value'] != _float(rq) or b['value'] != _float(bq):
            reasons.append('recovery_pair_exact_identity_mismatch')
    control = r['control_kind']
    if control != 'reporter_standard':
        reasons.append('enzyme_activity_spike_is_not_reporter_standard' if control == 'enzyme_activity_spike' else 'recovery_pair_control_' + control)
    if r['section'] != 'calibration_validity' or r['interpretation_scope_unavailable_reason'] is not None:
        reasons.append('recovery_pair_scope_mismatch')
    return list(dict.fromkeys(reasons))


def _operand(selector, role, read_component):
    if selector is None:
        return None
    if not callable(read_component):
        _fail('component_reader_required', role)
    rows = read_component(deepcopy(selector))
    validate_schema(rows, {'type': 'array', 'items': _row_schema()})
    if len(rows) != 1 or rows[0]['sheet_ref'] != selector['sheet_ref'] or rows[0]['component'] != role:
        _fail('selected_component_not_received', role)
    return {'selection': deepcopy(selector), 'row': deepcopy(rows[0])}


def _deduplicate(items, fields):
    result, seen = [], {}
    for item in items:
        key = item['number']['measurement_key']
        signature = {name: item[name]['value'] for name in fields}
        signature['origin'] = item['number']['origin']
        if key in seen:
            prior, meanings = seen[key]
            if meanings != signature:
                _fail('duplicate_measurement_meaning_conflict', 'number')
            prior['aliases'].append(deepcopy(item['number']['selector']))
        else:
            item['aliases'] = []
            result.append(item)
            seen[key] = item, signature
    return result


def read_measurement_validation_inputs(arguments, *, read_source, read_component=None):
    """Read exact nominated spans and actual possessed fact rows, preserving partials."""
    args = deepcopy(arguments)
    validate_schema(args, measurement_validation_population_schema())
    sources = _Sources(read_source)
    original = sources.source(args['source_ref'], 'original')
    origin = ORIGINS[args['source_kind']]
    context = {}
    for name, selected in args['context'].items():
        witness = None if selected is None else sources.witness(selected, 'context.' + name)
        context[name] = None if witness is None else {'value': witness['quote'], 'witness': witness}
    operands = {role: _operand(args[role], role, read_component) for role in ('recovery', 'relative_bias')}
    precision, zprime = [], []
    for selected in args['precision']:
        number = _read_number(selected['number'], sources, origin)
        item = {'number': number, 'quantity_label': _label(selected['quantity_label'], 'cv', number, sources),
                'unit': _unit(selected['unit'], number, sources)}
        for name, values in RELATIONSHIPS.items():
            item[name] = _interpretation(selected[name], values, sources, name)
        if item['basis']['value'] not in ('unknown', 'conflicting', 'unspecified'):
            for witness in item['basis']['witnesses']:
                # A directly selected table basis must cover this numeric column.
                if _table_cells(sources, witness)[0] is not None:
                    _associate(number, witness, sources, 'basis')
        precision.append(item)
    for selected in args['zprime']:
        number = _read_number(selected['number'], sources, origin)
        item = {'number': number, 'quantity_label': _label(selected['quantity_label'], 'zprime', number, sources),
            'formula_relation': _interpretation(selected['formula_relation'], FORMULA_RELATIONS, sources, 'formula_relation')}
        _explicit_unit(number, 'fraction', sources)
        zprime.append(item)
    result = {'version': VERSION, 'source_ref': args['source_ref'], 'artifact_ref': original['artifact_ref'],
        'source_kind': args['source_kind'], 'context': context, **operands,
        'pair_unavailable_reasons': recovery_pair_reasons(operands['recovery'], operands['relative_bias']),
        'precision': _deduplicate(precision, ('unit', *RELATIONSHIPS)),
        'zprime': _deduplicate(zprime, ('formula_relation',)), 'input_origins': [origin],
        'source_refs': list(sources.references)}
    validate_measurement_validation_extraction(result)
    return result


def validate_measurement_validation_extraction(data):
    """Check retained relationships/identities without reacquiring source bytes."""
    validate_schema(data, measurement_validation_extraction_schema())
    if data['source_ref'] not in data['source_refs'] or data['input_origins'] != [ORIGINS[data['source_kind']]]:
        _fail('measurement_validation_source_record_mismatch', 'source_refs')
    def witnesses(value):
        if isinstance(value, dict):
            if set(value) == {'source_ref', 'representation', 'start', 'end', 'quote', 'artifact_ref'}:
                if value['source_ref'] not in data['source_refs'] or value['end'] - value['start'] != len(value['quote'].encode()):
                    _fail('measurement_validation_witness_record_mismatch', 'witness')
            else:
                for child in value.values():
                    witnesses(child)
        elif isinstance(value, list):
            for child in value:
                witnesses(child)
    # Possessed rows use their own provenance contract, not source witnesses.
    witnesses({k: v for k, v in data.items() if k not in ('recovery', 'relative_bias')})
    for value in data['context'].values():
        if value is not None and value['value'] != value['witness']['quote']:
            _fail('measurement_validation_literal_record_mismatch', 'context')
    for role in ('recovery', 'relative_bias'):
        operand = data[role]
        if operand is not None and (operand['selection']['sheet_ref'] != operand['row']['sheet_ref'] or operand['row']['component'] != role):
            _fail('selected_component_not_received', role)
    if data['pair_unavailable_reasons'] != recovery_pair_reasons(data['recovery'], data['relative_bias']):
        _fail('measurement_validation_pair_reason_mismatch', 'pair_unavailable_reasons')
    used = set()
    for family in ('precision', 'zprime'):
        for item in data[family]:
            number = item['number']; selector = number['selector']; witness = selector['witness']
            ns, ne = selector['number_start'], selector['number_end']
            if not 0 <= ns < ne <= len(witness['quote']) or witness['quote'][ns:ne] != number['raw_number']:
                _fail('measurement_validation_number_record_mismatch', family)
            start = witness['start'] + len(witness['quote'][:ns].encode())
            end = witness['start'] + len(witness['quote'][:ne].encode())
            key = identity('literature_measurement', {'artifact_ref': witness['artifact_ref'], 'number_start': start, 'number_end': end})
            if (key != number['measurement_key'] or start != number['number_start_bytes'] or end != number['number_end_bytes']
                    or number['origin'] != ORIGINS[data['source_kind']] or key in used):
                _fail('measurement_validation_measurement_binding_mismatch', family)
            used.add(key)
            raw = number['raw_number']
            nonfinite = re.fullmatch(r'[+−-]?(?:NaN|Inf|Infinity)', raw, re.I) is not None
            approximate_point = _APPROX_POINT.fullmatch(raw)
            if (number['relation'] == 'range' and not _RANGE.fullmatch(raw)
                    or number['relation'] != 'range' and not nonfinite and not _NUMBER.fullmatch(raw) and not approximate_point
                    or approximate_point and number['relation'] != 'approximate'
                    or nonfinite and number['relation'] != 'point'):
                _fail('measurement_validation_number_record_mismatch', family)
            exact = (None if number['relation'] == 'range' or nonfinite else
                     Fraction((approximate_point.group('point') if approximate_point else raw).replace('−', '-')))
            if (number['native_exact_value'] != (None if exact is None else _exact(exact))
                    or number['native_value'] != (None if exact is None else _float(exact))):
                _fail('measurement_validation_number_record_mismatch', family)
            expected_reason = {'range': 'source_range_unimplemented', 'approximate': 'source_approximation_unimplemented',
                               'unresolved': 'source_negated_comparison_unimplemented'}.get(number['relation'])
            if nonfinite:
                expected_reason = 'nonfinite_source_statistic_unavailable'
            if expected_reason != number['capability_reason']:
                _fail('measurement_validation_capability_record_mismatch', family)
            rep = number['representation_witness']
            if (rep['artifact_ref'] != witness['artifact_ref'] or not rep['start'] <= start < end <= rep['end']
                    or rep['quote'].encode()[start-rep['start']:end-rep['start']] != raw.encode()):
                _fail('measurement_validation_representation_binding_mismatch', family)
            for alias in item['aliases']:
                aw = alias['witness']; an, ae = alias['number_start'], alias['number_end']
                if (aw['artifact_ref'] != witness['artifact_ref'] or aw['start'] + len(aw['quote'][:an].encode()) != start
                        or aw['start'] + len(aw['quote'][:ae].encode()) != end or aw['quote'][an:ae] != raw):
                    _fail('measurement_validation_alias_binding_mismatch', family)
            interpreted = RELATIONSHIPS if family == 'precision' else {'formula_relation': FORMULA_RELATIONS}
            for name in interpreted:
                value = item[name]
                unique = {(w['artifact_ref'], w['representation'], w['start'], w['end']) for w in value['witnesses']}
                required = 0 if value['value'] == 'unknown' else 2 if value['value'] == 'conflicting' else 1
                if len(unique) < required:
                    _fail('interpretation_witness_required', name)
            if family == 'precision' and _unit_value(item['unit']['witness']['quote']) != item['unit']['value']:
                _fail('precision_unit_mismatch', 'unit')


__all__ = ['VERSION', 'NAMESPACE', 'SOURCE_KINDS', 'CONTEXT_FIELDS', 'RELATIONSHIPS', 'FORMULA_RELATIONS',
    'PAIR_REASONS', 'NUMBER_REASONS', 'RELATIONS', 'recovery_selector_schema',
    'measurement_validation_population_schema', 'measurement_validation_extraction_schema',
    'read_measurement_validation_inputs', 'validate_measurement_validation_extraction']
