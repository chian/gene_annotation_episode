"""Closed observations and source-grounded numerical contracts for BLASTP reports.

Validation consumes saved data only. Schema assets load at import; no validation
or arithmetic operation opens files, invokes a parser, or acquires evidence.
The validator does not import the publication calculator.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, validators

from .bvbrc_proteome_directional_contracts import (
    ProteomeDirectionalError, directional_schema, validate_directional_report,
)
from .bvbrc_proteome_directional_geometry import DirectionalNumericalContractError

_DOCUMENT = json.loads(Path(__file__).with_name(
    'bvbrc_proteome_directional_numerical_schemas.json').read_text(encoding='utf-8'))
_DEFS = _DOCUMENT['$defs']


def _reader_namespace(node):
    if type(node) is dict:
        return {k: ('#/$defs/Reader' + v.removeprefix('#/$defs/') if k == '$ref'
                    else _reader_namespace(v)) for k,v in node.items()}
    if type(node) is list: return [_reader_namespace(v) for v in node]
    return node


for _native_name, _native_definition in directional_schema('DirectionalReportResult')['$defs'].items():
    if _DEFS.get('Reader' + _native_name) != _reader_namespace(_native_definition):
        raise RuntimeError('directional_numerical_native_schema_drift')
_NAMES = frozenset(('DirectionalSheet', 'DirectionalSheetResult',
    'DirectionalCalculationParameters', 'BlockComponents', 'HspComponents',
    'CorrespondenceGraph', 'DirectionalComponents', 'DirectionalComponentsResult',
    'DirectionalScoringSheet'))
_KEY_FIELDS = ('report_ordinal', 'query_ordinal', 'subject_ordinal',
               'hsp_ordinal', 'block_ordinal', 'column_ordinal')
_TRACE_UNITS = {
    'alignment_columns': 'alignment_column', 'paired_columns': 'paired_column',
    'displayed_symbol_identical_pairs': 'paired_column',
    'displayed_symbol_nonidentical_pairs': 'paired_column',
    'resolved_amino_acid_pairs': 'paired_column',
    'resolved_amino_acid_identical_pairs': 'paired_column',
    'resolved_amino_acid_substituted_pairs': 'paired_column',
    'unresolved_symbol_pairs': 'paired_column', 'stop_containing_pairs': 'paired_column',
    'query_gap_columns': 'alignment_column', 'subject_gap_columns': 'alignment_column',
    'query_gap_runs': 'gap_run', 'subject_gap_runs': 'gap_run',
    'query_non_gap_symbols': 'displayed_position',
    'subject_non_gap_symbols': 'displayed_position',
}
_FRACTION_COUNTS = {
    'trace_symbol_identity_over_columns': ('displayed_symbol_identical_pairs', 'alignment_columns'),
    'trace_symbol_identity_over_pairs': ('displayed_symbol_identical_pairs', 'paired_columns'),
    'trace_resolved_amino_acid_identity': ('resolved_amino_acid_identical_pairs', 'resolved_amino_acid_pairs'),
    'trace_resolved_pair_fraction': ('resolved_amino_acid_pairs', 'paired_columns'),
    'trace_unresolved_pair_fraction': ('unresolved_symbol_pairs', 'paired_columns'),
    'trace_gap_fraction': (('query_gap_columns', 'subject_gap_columns'), 'alignment_columns'),
}
_HSP_NATIVE_FIELDS = tuple(k for k in _DEFS['HspObservation']['properties'] if k != 'key')
_ARGUMENT_CODES = frozenset(('invalid_input_contract', 'invalid_parameters',
                            'semantic_context_missing', 'semantic_context_conflict'))


def _require(condition, pointer='', code='invalid_input_contract'):
    if not condition:
        raise DirectionalNumericalContractError(code, pointer)


def _ptr(path, token):
    return path + '/' + str(token).replace('~', '~0').replace('/', '~1')


def _plain_json(value, pointer='', ancestors=None):
    if value is None or type(value) in (str, int, bool):
        return
    _require(type(value) in (dict, list), pointer)
    ancestors = set() if ancestors is None else ancestors
    _require(id(value) not in ancestors, pointer)
    ancestors.add(id(value))
    for key, child in (value.items() if type(value) is dict else enumerate(value)):
        _require(type(value) is not dict or type(key) is str, pointer)
        _plain_json(child, _ptr(pointer, key), ancestors)
    ancestors.remove(id(value))


def canonical_sheet_sha256(sheet: dict) -> str:
    """SHA256 of sorted compact UTF-8 JSON, ensure_ascii=False, no NaN."""
    _require(type(sheet) is dict, '/sheet')
    _plain_json(sheet, '/sheet')
    return hashlib.sha256(json.dumps(sheet, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def directional_numerical_schema(name: str) -> dict:
    """Return a fresh closed schema containing only reachable local definitions."""
    _require(type(name) is str and name in _NAMES, '/name')
    reached = set()
    def visit(node):
        if type(node) is dict:
            if '$ref' in node:
                key = node['$ref'].removeprefix('#/$defs/')
                if key not in _DEFS:
                    raise RuntimeError('directional_numerical_packaged_reference_invalid')
                if key not in reached:
                    reached.add(key)
                    visit(_DEFS[key])
            for child in node.values(): visit(child)
        elif type(node) is list:
            for child in node: visit(child)
    root = {'$schema': _DOCUMENT['$schema'], '$ref': '#/$defs/' + name}
    visit(root)
    root['$defs'] = {k: deepcopy(v) for k, v in _DEFS.items() if k in reached}
    return root


_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    'integer': lambda checker, value: type(value) is int,
    'number': lambda checker, value: type(value) in (int, float),
})
_Validator = validators.extend(Draft202012Validator, type_checker=_TYPES)
_VALIDATORS = {n: _Validator(directional_numerical_schema(n)) for n in _NAMES}


def _shape(name, value, path=''):
    _plain_json(value, path)
    error = next(_VALIDATORS[name].iter_errors(value), None)
    if error:
        for token in error.absolute_path: path = _ptr(path, token)
        raise DirectionalNumericalContractError(
            'invalid_parameters' if name == 'DirectionalCalculationParameters' else 'invalid_input_contract', path)


def _same(actual, expected, path):
    """Locate the first semantic difference without exposing native content."""
    _require(type(actual) is type(expected), path)
    if type(expected) is dict:
        _require(set(actual) == set(expected), path)
        for key in expected: _same(actual[key], expected[key], _ptr(path, key))
    elif type(expected) is list:
        _require(len(actual) == len(expected), path)
        for index, (a, b) in enumerate(zip(actual, expected)): _same(a, b, _ptr(path, index))
    else:
        _require(actual == expected, path)


def _key(*ordinals):
    return dict(zip(_KEY_FIELDS, ordinals))


def _native_path(key, field=None):
    result = ''
    for name, array in zip(_KEY_FIELDS[1:5], ('queries', 'subjects', 'hsps', 'traceback_blocks')):
        if name in key: result += '/' + array + '/' + str(key[name])
    return result if field is None else result + '/' + field


def _ref(key, field=None):
    return {'report_ordinal': key['report_ordinal'], 'pointer': _native_path(key, field)}


def _resolve(sheet, reference, path):
    r = reference['report_ordinal']
    _require(r < len(sheet['reader_results']), path + '/report_ordinal')
    value = sheet['reader_results'][r]
    for token in reference['pointer'].split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            _require(re.fullmatch(r'0|[1-9][0-9]*', token) is not None, path + '/pointer')
            _require(int(token) < len(value), path + '/pointer')
            value = value[int(token)]
        else:
            _require(type(value) is dict and token in value, path + '/pointer')
            value = value[token]
    return value


def _native(sheet, key, path):
    return _resolve(sheet, _ref(key), path)


def _identity(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _unique(values, path):
    _require(len({_identity(v) for v in values}) == len(values), path)


def _refset(actual, expected, path):
    _unique(actual, path)
    _require({_identity(v) for v in actual} == {_identity(v) for v in expected}, path)


def _union_refs(cells):
    result = []
    for cell in cells:
        for ref in cell['inputs']:
            if ref not in result: result.append(ref)
    return result


def _issue(code, fields=(), *, columns=(), hsps=(), argument_pointer=None):
    return {'code': code, 'fields': list(fields), 'columns': list(columns),
            'hsps': list(hsps), 'argument_pointer': argument_pointer}


def _observations(results):
    reports = []
    for ri, result in enumerate(results):
        query_rows = []
        for qi, query in enumerate(result['queries']):
            subjects = []
            for si, subject in enumerate(query['subjects']):
                hsps = [{'key': _key(ri, qi, si, hi), **{field: deepcopy(hsp[field])
                         for field in _HSP_NATIVE_FIELDS}}
                        for hi, hsp in enumerate(subject['hsps'])]
                subjects.append({'key': _key(ri, qi, si),
                    'reported_length': deepcopy(subject['length']),
                    'defline_text': deepcopy(subject['defline_text']),
                    'identifier_token': deepcopy(subject['identifier_token']), 'hsps': hsps})
            query_rows.append({'key': _key(ri, qi), 'reported_length': deepcopy(query['length']),
                **{field: deepcopy(query[field]) for field in ('header_text', 'identifier_token',
                    'no_hits_marker', 'boundary', 'database_headers', 'descriptions', 'statistics')},
                'subjects': subjects})
        reports.append({'report_ordinal': ri, 'report_key': result['report_key'], 'query_rows': query_rows})
    return reports


def _sheet_diagnostics(results):
    result = []
    if not results:
        result.append(_issue('no_report_supplied'))
    for ri, native in enumerate(results):
        if native['parse_state'] != 'ok':
            result.append(_issue('native_reader_' + native['parse_state'],
                                 [{'report_ordinal': ri, 'pointer': '/parse_state'}]))
        for predicate, code, field in (
            (not native['source']['body_complete'], 'source_body_incomplete', 'body_complete'),
            (native['source']['object_complete'] == 'no', 'source_object_incomplete', 'object_complete'),
            (native['source']['object_complete'] == 'unknown', 'source_object_completeness_unknown', 'object_complete'),
        ):
            if predicate: result.append(_issue(code, [{'report_ordinal': ri, 'pointer': '/source/' + field}]))
    return result


def _validate_sheet(value, path=''):
    for index, result in enumerate(value['reader_results']):
        try: validate_directional_report(result)
        except ProteomeDirectionalError as error:
            raise DirectionalNumericalContractError('invalid_input_contract',
                f'{path}/reader_results/{index}' + error.path) from None
    _same(value['reports'], _observations(value['reader_results']), path + '/reports')
    _same(value['diagnostics'], _sheet_diagnostics(value['reader_results']), path + '/diagnostics')


def _walk_references(value, sheet, path='', native=False):
    """Every supplied scientific reference resolves before formula-specific checks."""
    if type(value) is list:
        for i, child in enumerate(value): _walk_references(child, sheet, _ptr(path, i), native)
    elif type(value) is dict:
        if set(value) == {'report_ordinal', 'pointer'}:
            _require(sheet is not None, path, 'semantic_context_missing')
            _resolve(sheet, value, path)
        elif set(value) == set(_KEY_FIELDS[:len(value)]) and 2 <= len(value) <= 6:
            _require(sheet is not None, path, 'semantic_context_missing')
            owner = _native(sheet, value, path)
            if 'column_ordinal' in value:
                q, s = owner['query_symbols'], owner['subject_symbols']
                _require(q['state'] == s['state'] == 'present' and
                         value['column_ordinal'] < len(q['value']) == len(s['value']), path)
        elif set(value) == {'code', 'fields', 'columns', 'hsps', 'argument_pointer'}:
            is_argument = value['code'] in _ARGUMENT_CODES
            _require((value['argument_pointer'] is not None) == is_argument, path + '/argument_pointer')
            if is_argument:
                _require(not value['fields'] and not value['columns'] and not value['hsps'], path)
            for name in ('fields', 'columns', 'hsps'):
                _unique(value[name], path + '/' + name)
                _walk_references(value[name], sheet, path + '/' + name)
        else:
            for name, child in value.items():
                if name not in ('reader_results', 'reports') or not native:
                    _walk_references(child, sheet, _ptr(path, name))


def _ratio_text(numerator, denominator, places):
    # Integer long division determines exact HALF_EVEN rounding, independent of
    # ambient Decimal context and with no binary-float intermediate.
    scale = 10 ** places
    quotient, remainder = divmod(numerator * scale, denominator)
    twice = remainder * 2
    if twice > denominator or twice == denominator and quotient % 2: quotient += 1
    return str(quotient) if not places else f'{quotient // scale}.{quotient % scale:0{places}d}'


def _cell(value, unit, number, refs, path, *, state='value', reasons=None, params=None):
    _same(value['unit'], unit, path + '/unit')
    _same(value['state'], state, path + '/state')
    if state == 'value' and unit == 'fraction':
        n, d = number
        _require(type(n) is type(d) is int and 0 <= n <= d and d > 0, path)
        _same(value['value'], {'numerator': n, 'denominator': d,
            'decimal': _ratio_text(n, d, params['ratio_decimal_places'])}, path + '/value')
    else:
        _same(value['value'], number if state == 'value' else None, path + '/value')
    _refset(value['inputs'], refs, path + '/inputs')
    _unique(value['reasons'], path + '/reasons')
    if reasons is not None:
        _require(set(value['reasons']) == set(reasons), path + '/reasons')
    elif state != 'value':
        _require(bool(value['reasons']), path + '/reasons')


def _validate_block(value, sheet, params, path):
    from .bvbrc_proteome_directional_geometry import calculate_protein_block
    key = value['key']
    block = _native(sheet, key, path + '/key')
    query = _native(sheet, {k: key[k] for k in _KEY_FIELDS[:2]}, path + '/key')
    subject = _native(sheet, {k: key[k] for k in _KEY_FIELDS[:3]}, path + '/key')
    expected = calculate_protein_block(block, key=key, query_length=query['length'],
        subject_length=subject['length'], amino_acid_alphabet=params['amino_acid_alphabet'],
        ratio_decimal_places=params['ratio_decimal_places'], rounding=params['rounding'])
    _same(value, expected, path)


def _present(cell):
    return cell['value'] if cell['state'] == 'present' else None


def _unavailable_state(cells, fallback='missing'):
    states = {c['state'] for c in cells}
    return next((s for s in ('conflict', 'invalid', 'missing', 'undefined') if s in states), fallback)


def _support(value, blocks, included, missing, path):
    expected = {'included_blocks': included,
        'excluded_blocks': [k for k in blocks if k not in included],
        'hsps_without_traceback': missing,
        'complete_for_displayed_blocks': len(included) == len(blocks) and not missing}
    _same(value, expected, path)


def _both_axes(block):
    return all(block['coverage'][axis + '_trace_occupied_union']['count']['state'] == 'value'
               for axis in ('query', 'subject'))


def _continuity(native, blocks):
    if not blocks: return 'unknown'
    if len(blocks) == 1:
        return 'yes' if blocks[0]['counts']['alignment_columns']['state'] == 'value' else 'unknown'
    # Discontinuity of two usable endpoint claims is already known even when
    # string geometry cannot be expanded. It never creates graph columns.
    for left, right in zip(blocks, blocks[1:]):
        for axis in ('query','subject'):
            a = left['coverage'][axis + '_reported_interval_union']
            b = right['coverage'][axis + '_reported_interval_union']
            if a['count']['state'] == b['count']['state'] == 'value' and a['intervals'][0][1] != b['intervals'][0][0]:
                return 'no'
    if any(b['counts']['alignment_columns']['state'] != 'value' for b in blocks): return 'unknown'
    unknown = False
    for left, right, lb, rb in zip(native['traceback_blocks'], native['traceback_blocks'][1:], blocks, blocks[1:]):
        for axis in ('query', 'subject'):
            if any(b['coverage'][axis + '_trace_occupied_union']['count']['state'] != 'value' for b in (lb, rb)):
                unknown = True
                continue
            a, b = _present(left[axis + '_end']), _present(right[axis + '_start'])
            if a is None or b is None: unknown = True
            elif b != a + 1:
                return 'no'
    return 'unknown' if unknown else 'yes'


def _all_block_refs(native, key, fields):
    return [_ref({**key, 'block_ordinal': bi}, field)
            for bi in range(len(native['traceback_blocks'])) for field in fields]


def _diagnostic_codes(issues):
    return {i['code'] for i in issues}


def _require_codes(issues, codes, path):
    _require(set(codes) <= _diagnostic_codes(issues), path)


def _unique_issues(issues):
    result = []
    for issue in issues:
        if issue not in result: result.append(issue)
    return result


def _check_issues(actual, expected, path):
    """Check truth and exact source operands, allowing equivalent unique order."""
    def normalize(issue):
        return {**issue, **{field: sorted(issue[field], key=_identity)
                           for field in ('fields','columns','hsps')}}
    actual = [normalize(i) for i in actual]
    expected = _unique_issues([normalize(i) for i in expected])
    _unique(actual, path)
    _require({_identity(i) for i in actual} == {_identity(i) for i in expected}, path)


def _hsp_issues(native, value):
    key, blocks = value['key'], value['blocks']
    def issue(code, refs): return _issue(code, refs, hsps=[key])
    expected = [i for block in blocks for i in block['diagnostics']]
    for cell in value['reported'].values():
        expected += [issue(code, cell['inputs']) for code in cell['reasons']]
    denoms = [_present(native[p + '_denominator']) for p in ('identity','positive','gap')]
    denoms = [d for d in denoms if d is not None and d > 0]
    drefs = [_ref(key, p + '_denominator') for p in ('identity','positive','gap')]
    if len(set(denoms)) > 1: expected.append(issue('incompatible_native_denominators', drefs))
    if value['native_denominator_extent'] == 'disagrees':
        expected.append(issue('native_denominator_extent_conflict', drefs))
    if value['contiguous_blocks'] == 'no':
        expected.append(issue('block_continuity_conflict', _all_block_refs(native,key,
            ('query_start','query_end','subject_start','subject_end'))))
    for field, code in (('strings_support','incomplete_displayed_strings'),('pair_geometry_support','incomplete_displayed_geometry')):
        if not value[field]['complete_for_displayed_blocks']:
            expected.append(issue(code, [_ref(key,'traceback_blocks')]))
    if value['strings_support']['complete_for_displayed_blocks'] and blocks:
        for prefix, counts in (('identity',('displayed_symbol_identical_pairs',)),('gap',('query_gap_columns','subject_gap_columns'))):
            number = _present(native[prefix + '_count'])
            if number is not None and number != sum(value['trace_counts'][f]['value'] for f in counts):
                expected.append(issue('reported_count_traceback_conflict',
                    [_ref(key,prefix + '_count'),_ref(key,'traceback_blocks')]))
    i, p = _present(native['identity_count']), _present(native['positive_count'])
    if i is not None and p is not None and p < i:
        expected.append(issue('positive_below_identity',[_ref(key,'identity_count'),_ref(key,'positive_count')]))
    paired = value['reported']['reported_paired_column_count']
    if paired['state'] == 'value' and p is not None and p > paired['value']:
        expected.append(issue('positive_exceeds_paired_count',[_ref(key,'positive_count')] + paired['inputs']))
    if value['native_scores']['expectation_display'] == 'printed_zero_precision_unknown':
        expected.append(issue('printed_zero_expectation',[_ref(key,'expect')]))
    return _unique_issues(expected)


def _validate_reported(value, native, key, params, path):
    """Native count ratios keep their own denominators and independent meaning."""
    information = {}
    for prefix in ('identity', 'positive', 'gap'):
        nc, dc = native[prefix + '_count'], native[prefix + '_denominator']
        n, d = _present(nc), _present(dc)
        reasons = []
        if 'missing' in (nc['state'], dc['state']): reasons.append('missing_native_count')
        if 'invalid' in (nc['state'], dc['state']): reasons.append('invalid_native_count')
        if d == 0: reasons.append('zero_native_denominator')
        if n is not None and d is not None and n > d: reasons.append('count_exceeds_denominator')
        state = ('invalid' if any(r != 'missing_native_count' for r in reasons) else 'missing') if reasons else 'value'
        refs = [_ref(key, prefix + '_count'), _ref(key, prefix + '_denominator')]
        _cell(value['reported_' + prefix + '_fraction'], 'fraction', (n, d), refs,
            path + '/reported_' + prefix + '_fraction', state=state, reasons=reasons, params=params)
        information[prefix] = (n, d, state, reasons, refs)
    i, di, istate, ireasons, irefs = information['identity']
    g, dg, gstate, greasons, grefs = information['gap']
    paired = dg - g if gstate == 'value' else None
    _cell(value['reported_paired_column_count'], 'paired_column', paired, grefs,
        path + '/reported_paired_column_count', state=gstate, reasons=greasons)
    reasons = list(dict.fromkeys(ireasons + greasons))
    state = _unavailable_state([{'state': istate}, {'state': gstate}], 'value')
    if di is not None and dg is not None and di != dg:
        state = 'conflict'
        reasons.append('incompatible_native_denominators')
    if paired is not None and i is not None and i > paired:
        state = 'conflict'
        reasons.append('identity_exceeds_paired_count')
    _cell(value['reported_nonidentical_paired_count'], 'paired_column',
          paired - i if state == 'value' else None, irefs + grefs,
          path + '/reported_nonidentical_paired_count', state=state, reasons=reasons)
    ratio_state = 'undefined' if state == 'value' and paired == 0 else state
    _cell(value['reported_identity_among_paired_fraction'], 'fraction', (i, paired),
        irefs + grefs, path + '/reported_identity_among_paired_fraction', state=ratio_state,
        reasons=['zero_paired_population'] if ratio_state == 'undefined' else reasons, params=params)


def _validate_fractions(fractions, counts, params, path):
    for name, (numerator, denominator) in _FRACTION_COUNTS.items():
        ns = [counts[f] for f in numerator] if type(numerator) is tuple else [counts[numerator]]
        dc = counts[denominator]
        cells = ns + [dc]
        refs = _union_refs(cells)
        state = _unavailable_state(cells, 'value')
        n, d = (sum(c['value'] for c in ns), dc['value']) if state == 'value' else (None, None)
        reasons = list(dict.fromkeys(r for c in cells for r in c['reasons']))
        if state == 'value' and d == 0:
            state = 'undefined'
            reasons = ['zero_resolved_population' if denominator == 'resolved_amino_acid_pairs' else 'zero_paired_population']
        _cell(fractions[name], 'fraction', (n, d), refs, path + '/' + name,
              state=state, reasons=reasons, params=params)


def _validate_position_union(value, unions, *, length, length_ref, missing,
                             params, path, zero_refs=None):
    from .bvbrc_proteome_directional_geometry import union_position_intervals
    blocks = [b for u in unions for b in u['support']['included_blocks'] + u['support']['excluded_blocks']]
    blocks.sort(key=lambda k: tuple(k[f] for f in _KEY_FIELDS if f in k))
    included = [b for u in unions for b in u['support']['included_blocks']]
    included.sort(key=lambda k: tuple(k[f] for f in _KEY_FIELDS if f in k))
    no_trace = [k for u in unions for k in u['support']['hsps_without_traceback']] + list(missing)
    no_trace = sorted({_identity(k): k for k in no_trace}.values(),
                      key=lambda k: tuple(k[f] for f in _KEY_FIELDS if f in k))
    _support(value['support'], blocks, included, no_trace, path + '/support')
    _same(value['reported_length'], length, path + '/reported_length')
    usable = [u for u in unions if u['count']['state'] == 'value']
    intervals = union_position_intervals([i for u in usable for i in u['intervals']])
    _same(value['intervals'], intervals, path + '/intervals')
    refs = _union_refs([u['count'] for u in unions])
    if zero_refs is not None: refs = zero_refs
    state = 'value' if usable or zero_refs is not None else _unavailable_state([u['count'] for u in unions])
    count = sum(b - a for a, b in intervals)
    reasons = [] if state == 'value' else list(dict.fromkeys(
        r for u in unions for r in u['count']['reasons'])) or ['missing_traceback']
    _cell(value['count'], 'displayed_position', count, refs, path + '/count', state=state, reasons=reasons)
    length_value = _present(length)
    coverage_state = state
    if state != 'conflict':
        if length['state'] == 'invalid' or length_value == 0: coverage_state = 'invalid'
        elif length['state'] == 'missing' and state not in ('invalid', 'conflict'): coverage_state = 'missing'
    cov_refs = refs + ([length_ref] if length_ref not in refs else [])
    coverage_reasons = list(reasons)
    if length['state'] == 'missing': coverage_reasons.append('missing_reported_length')
    elif length['state'] == 'invalid' or length_value == 0: coverage_reasons.append('invalid_reported_length')
    _cell(value['coverage'], 'fraction', (count, length_value), cov_refs,
          path + '/coverage', state=coverage_state, reasons=coverage_reasons, params=params)
    if length['state'] == 'missing':
        _require('missing_reported_length' in value['coverage']['reasons'], path + '/coverage/reasons')
    if length['state'] == 'invalid' or length_value == 0:
        _require('invalid_reported_length' in value['coverage']['reasons'], path + '/coverage/reasons')


def _validate_coverage(value, blocks, native_query, native_subject, key, missing, params, path):
    for name, actual in value.items():
        axis = name.split('_', 1)[0]
        operand_key = {k: key[k] for k in _KEY_FIELDS[:2 if axis == 'query' else 3]}
        length = (native_query if axis == 'query' else native_subject)['length']
        _validate_position_union(actual, [b['coverage'][name] for b in blocks],
            length=length, length_ref=_ref(operand_key, 'length'), missing=missing,
            params=params, path=path + '/' + name)


def _validate_hsp(value, sheet, params, path):
    key = value['key']
    native = _native(sheet, key, path + '/key')
    query = _native(sheet, {k: key[k] for k in _KEY_FIELDS[:2]}, path + '/key')
    subject = _native(sheet, {k: key[k] for k in _KEY_FIELDS[:3]}, path + '/key')
    blocks = value['blocks']
    _require(len(blocks) == len(native['traceback_blocks']), path + '/blocks')
    for bi, block in enumerate(blocks):
        _same(block['key'], {**key, 'block_ordinal': bi}, f'{path}/blocks/{bi}/key')
        _validate_block(block, sheet, params, f'{path}/blocks/{bi}')
    _validate_reported(value['reported'], native, key, params, path + '/reported')
    for field in ('bit_score', 'raw_score', 'expect', 'expect_group_count'):
        _same(value['native_scores'][field], native[field], path + '/native_scores/' + field)
    expect = native['expect']
    display = expect['state']
    if expect['state'] == 'present':
        number = Decimal(expect['value'])
        display = 'invalid' if number < 0 else 'printed_zero_precision_unknown' if number == 0 else 'positive_reported_decimal'
    _same(value['native_scores']['expectation_display'], display, path + '/native_scores/expectation_display')
    all_keys = [b['key'] for b in blocks]
    valid = [b for b in blocks if b['counts']['alignment_columns']['state'] == 'value']
    missing = [key] if not blocks else []
    _support(value['strings_support'], all_keys, [b['key'] for b in valid], missing, path + '/strings_support')
    _support(value['pair_geometry_support'], all_keys, [b['key'] for b in blocks if _both_axes(b)],
             missing, path + '/pair_geometry_support')
    continuity = _continuity(native, blocks)
    _same(value['contiguous_blocks'], continuity, path + '/contiguous_blocks')
    incomplete_refs = [r for b in blocks if b not in valid
                       for r in (_ref(b['key'], 'query_symbols'), _ref(b['key'], 'subject_symbols'))]
    for name, unit in _TRACE_UNITS.items():
        cells = [b['counts'][name] for b in valid]
        refs = _union_refs(cells)
        refs += [r for r in incomplete_refs if r not in refs]
        state = 'value' if valid else _unavailable_state([b['counts'][name] for b in blocks])
        number = sum(c['value'] for c in cells) if valid else None
        reasons = [] if valid else list(dict.fromkeys(
            reason for b in blocks for reason in b['counts'][name]['reasons'])) or ['missing_traceback']
        if name.endswith('_gap_runs') and len(blocks) > 1:
            boundary_refs = _all_block_refs(native, key, ('query_start','query_end','subject_start','subject_end'))
            refs += [r for r in boundary_refs if r not in refs]
            geometry = [b['coverage'][axis + '_trace_occupied_union']['count']
                        for b in blocks for axis in ('query','subject')]
            refs += [r for r in _union_refs(geometry) if r not in refs]
            if len(valid) != len(blocks) or continuity != 'yes':
                prerequisites = [b['counts'][name] for b in blocks] + geometry
                state = 'conflict' if continuity == 'no' else _unavailable_state(
                    prerequisites)
                reasons = list(dict.fromkeys(r for c in prerequisites for r in c['reasons']))
                reasons.append('block_continuity_conflict' if continuity == 'no' else 'incomplete_displayed_geometry')
                number = None
            else:
                axis = name.split('_',1)[0]
                number -= sum(left['columns'][-1][axis + '_symbol'] == right['columns'][0][axis + '_symbol'] == '-'
                              for left, right in zip(blocks, blocks[1:]))
        _cell(value['trace_counts'][name], unit, number, refs, path + '/trace_counts/' + name,
              state=state, reasons=reasons)
    _validate_fractions(value['trace_fractions'], value['trace_counts'], params, path + '/trace_fractions')
    _validate_coverage(value['coverage'], blocks, query, subject, key, missing, params, path + '/coverage')
    denoms = [_present(native[p + '_denominator']) for p in ('identity','positive','gap')]
    denoms = [d for d in denoms if d is not None and d > 0]
    extent = 'unknown'
    if blocks and len(valid) == len(blocks) and denoms:
        extent = 'agrees' if all(d == value['trace_counts']['alignment_columns']['value'] for d in denoms) else 'disagrees'
    _same(value['native_denominator_extent'], extent, path + '/native_denominator_extent')
    required = []
    if continuity == 'no': required.append('block_continuity_conflict')
    if extent == 'disagrees': required.append('native_denominator_extent_conflict')
    i, p = _present(native['identity_count']), _present(native['positive_count'])
    if i is not None and p is not None and p < i: required.append('positive_below_identity')
    gd, g = _present(native['gap_denominator']), _present(native['gap_count'])
    if gd is not None and g is not None and 0 <= g <= gd:
        if i is not None and i > gd - g: required.append('identity_exceeds_paired_count')
        if p is not None and p > gd - g: required.append('positive_exceeds_paired_count')
    if len(set(denoms)) > 1: required.append('incompatible_native_denominators')
    if len(valid) == len(blocks) and blocks:
        for prefix, fields in (('identity', ('displayed_symbol_identical_pairs',)),
                               ('gap', ('query_gap_columns','subject_gap_columns'))):
            count = _present(native[prefix + '_count'])
            if count is not None and count != sum(value['trace_counts'][f]['value'] for f in fields):
                required.append('reported_count_traceback_conflict')
    _require_codes(value['diagnostics'], required, path + '/diagnostics')
    _check_issues(value['diagnostics'], _hsp_issues(native,value), path + '/diagnostics')


def _source_geometry_hsps(sheet, key):
    """Temporary, alphabet-independent graph inputs, never saved scientific defaults.

    Graph construction reads only symbols, positions, support and continuity.
    Explicit standard20/zero-place options satisfy the block API; their class
    counts and ratio renderings are discarded. No graph fact uses those options.
    """
    from .bvbrc_proteome_directional_geometry import calculate_protein_block
    subject = _native(sheet, key, '/key')
    query = _native(sheet, {k: key[k] for k in _KEY_FIELDS[:2]}, '/key')
    hsps = []
    for hi, native in enumerate(subject['hsps']):
        hk = {**key, 'hsp_ordinal': hi}
        blocks = [calculate_protein_block(b, key={**hk, 'block_ordinal': bi},
                    query_length=query['length'], subject_length=subject['length'],
                    amino_acid_alphabet='standard20', ratio_decimal_places=0, rounding='half_even')
                  for bi, b in enumerate(native['traceback_blocks'])]
        included = [b['key'] for b in blocks if _both_axes(b)]
        excluded = [b['key'] for b in blocks if not _both_axes(b)]
        hsps.append({'key': hk, 'blocks': blocks, 'contiguous_blocks': _continuity(native, blocks),
            'pair_geometry_support': {'included_blocks': included, 'excluded_blocks': excluded,
                'hsps_without_traceback': [] if blocks else [hk],
                'complete_for_displayed_blocks': bool(blocks) and not excluded}})
    return hsps


def _validate_graph(value, sheet, path, hsps=None):
    from .bvbrc_proteome_directional_geometry import inspect_protein_correspondence
    if hsps is None: hsps = _source_geometry_hsps(sheet, value['key'])
    expected = inspect_protein_correspondence(hsps, key=value['key'])
    _same(value, expected, path)


def _validate_extremum(value, native, key, field, minimum, path):
    valid, excluded, reasons = [], [], []
    for hi, hsp in enumerate(native['hsps']):
        hk = {**key, 'hsp_ordinal': hi}
        cell = hsp[field]
        number = Decimal(cell['value']) if cell['state'] == 'present' else None
        if number is None or field == 'expect' and number < 0:
            excluded.append(hk)
            reason = 'missing_native_score' if cell['state'] == 'missing' else 'invalid_native_score'
            if reason not in reasons: reasons.append(reason)
        else: valid.append((number, hk))
    if valid:
        extreme = (min if minimum else max)(n for n, _ in valid)
        tied = [k for n, k in valid if n == extreme]
        state, selected = 'value', _ref(tied[0], field)
    else:
        state = 'invalid' if 'invalid_native_score' in reasons else 'missing'
        tied, selected = [], None
        if not reasons: reasons.append('missing_native_score')
    _same(value['state'], state, path + '/state')
    _same(value['selected_field'], selected, path + '/selected_field')
    _same(value['tied_hsps'], tied, path + '/tied_hsps')
    _same(value['excluded_hsps'], excluded, path + '/excluded_hsps')
    _unique(value['reason_codes'], path + '/reason_codes')
    _require(set(value['reason_codes']) == set(reasons), path + '/reason_codes')


def _validate_subject(value, sheet, params, path):
    key = value['key']
    native = _native(sheet, key, path + '/key')
    query = _native(sheet, {k: key[k] for k in _KEY_FIELDS[:2]}, path + '/key')
    hsps = value['hsps']
    _require(len(hsps) == len(native['hsps']), path + '/hsps')
    for hi, hsp in enumerate(hsps):
        _same(hsp['key'], {**key, 'hsp_ordinal': hi}, f'{path}/hsps/{hi}/key')
        _validate_hsp(hsp, sheet, params, f'{path}/hsps/{hi}')
    blocks = [b for h in hsps for b in h['blocks']]
    _cell(value['displayed_hsp_count'], 'hsp_occurrence', len(hsps), [_ref(key,'hsps')], path + '/displayed_hsp_count', reasons=[])
    _cell(value['displayed_block_count'], 'block_occurrence', len(blocks), [_ref(key,'hsps')], path + '/displayed_block_count', reasons=[])
    _validate_coverage(value['coverage'], blocks, query, native, key,
        [h['key'] for h in hsps if not h['blocks']], params, path + '/coverage')
    _same(value['correspondence']['key'], key, path + '/correspondence/key')
    _validate_graph(value['correspondence'], sheet, path + '/correspondence', hsps)
    graph = value['correspondence']
    refs = graph['distinct_pair_count']['inputs']
    mapping = graph['mapping_state']
    state = {'compatible_displayed_partial_map':'value', 'observed_conflict':'conflict',
             'incomplete_geometry':'missing'}[mapping]
    compatible_reasons = ([c['code'] for c in graph['conflicts']] if state == 'conflict' else
                          ['incomplete_displayed_geometry'] if state == 'missing' else [])
    lookup = {_identity(c['key']): c for b in blocks for c in b['columns']}
    columns = [lookup[_identity(edge['supports'][0])] for edge in graph['edges']]
    counts = {
        'identical_symbol_pairs': sum(c['displayed_symbol_equal'] for c in columns),
        'resolved_pairs': sum(c['kind'] in ('resolved_identical','resolved_substituted') for c in columns),
        'resolved_identical_pairs': sum(c['kind'] == 'resolved_identical' for c in columns),
        'resolved_substituted_pairs': sum(c['kind'] == 'resolved_substituted' for c in columns),
        'unresolved_pairs': sum(c['kind'] == 'unresolved_pair' for c in columns),
        'stop_containing_pairs': sum(c['kind'] == 'stop_containing_pair' for c in columns),
    }
    for name, count in counts.items():
        _cell(value['compatible_pair_counts'][name], 'coordinate_pair', count, refs,
              path + '/compatible_pair_counts/' + name, state=state, reasons=compatible_reasons)
    for name, numerator, denominator in (
        ('compatible_unique_pair_symbol_identity', counts['identical_symbol_pairs'], len(columns)),
        ('compatible_unique_pair_resolved_identity', counts['resolved_identical_pairs'], counts['resolved_pairs']),
        ('compatible_unique_pair_resolved_fraction', counts['resolved_pairs'], len(columns)),
    ):
        ratio_state = 'undefined' if state == 'value' and denominator == 0 else state
        ratio_reasons = list(compatible_reasons)
        if name != 'compatible_unique_pair_resolved_identity':
            ratio_reasons += graph['distinct_pair_count']['reasons']
        if ratio_state == 'undefined':
            ratio_reasons = ['zero_resolved_population' if name.endswith('resolved_identity') else 'zero_paired_population']
        _cell(value[name], 'fraction', (numerator, denominator), refs, path + '/' + name,
              state=ratio_state, reasons=ratio_reasons, params=params)
        if ratio_state == 'undefined':
            _require(('zero_resolved_population' if name.endswith('resolved_identity') else 'zero_paired_population')
                     in value[name]['reasons'], path + '/' + name + '/reasons')
    # The separately named native-count sum requires complete contiguous HSPs,
    # native identity/extent agreement and disjoint occupied sets on BOTH axes.
    aggregate_refs = []
    prerequisites = []
    reasons = []
    if not hsps: reasons.append('missing_traceback')
    for hsp, raw in zip(hsps, native['hsps']):
        prerequisite_refs = [_ref(hsp['key'], 'identity_count'), _ref(hsp['key'], 'identity_denominator')]
        prerequisite_refs += _union_refs([hsp['coverage'][a + '_trace_occupied_union']['count'] for a in ('query','subject')]
                                        + [hsp['trace_counts']['alignment_columns']])
        aggregate_refs += [r for r in prerequisite_refs if r not in aggregate_refs]
        prerequisites.extend([hsp['reported']['reported_identity_fraction'],
                              hsp['trace_counts']['alignment_columns'],
                              hsp['trace_counts']['displayed_symbol_identical_pairs']]
                              + [b['counts']['alignment_columns'] for b in hsp['blocks']]
                              + [b['coverage'][axis + '_trace_occupied_union']['count']
                                 for b in hsp['blocks'] for axis in ('query','subject')])
        block_prerequisites = [b['counts']['alignment_columns'] for b in hsp['blocks']] + [
            b['coverage'][axis + '_trace_occupied_union']['count']
            for b in hsp['blocks'] for axis in ('query','subject')]
        reasons.extend(r for c in block_prerequisites for r in c['reasons'])
        reasons.extend(hsp['reported']['reported_identity_fraction']['reasons'])
        if (not hsp['pair_geometry_support']['complete_for_displayed_blocks'] or
                not hsp['strings_support']['complete_for_displayed_blocks']):
            reasons.append('incomplete_displayed_geometry')
        if hsp['contiguous_blocks'] != 'yes':
            reasons.append('block_continuity_conflict' if hsp['contiguous_blocks'] == 'no' else 'incomplete_displayed_geometry')
        if (hsp['reported']['reported_identity_fraction']['state'] == 'value' and
                hsp['strings_support']['complete_for_displayed_blocks'] and hsp['blocks']):
            for raw_field, trace_field in (('identity_count','displayed_symbol_identical_pairs'),('identity_denominator','alignment_columns')):
                raw_value = _present(raw[raw_field])
                if raw_value is not None and raw_value != hsp['trace_counts'][trace_field]['value']:
                    reasons.append('reported_count_traceback_conflict')
    for axis in ('query','subject'):
        for i, first in enumerate(hsps):
            a = first['coverage'][axis + '_trace_occupied_union']['intervals']
            for second in hsps[i + 1:]:
                b = second['coverage'][axis + '_trace_occupied_union']['intervals']
                if any(max(x0,y0) < min(x1,y1) for x0,x1 in a for y0,y1 in b):
                    reasons.append('overlapping_hsp_occupied_positions')
    aggregate_state = _unavailable_state(prerequisites, 'value')
    if any(r in reasons for r in ('block_continuity_conflict','reported_count_traceback_conflict','overlapping_hsp_occupied_positions')):
        aggregate_state = 'conflict'
    elif reasons and aggregate_state == 'value': aggregate_state = 'missing'
    total_i = sum(_present(h['identity_count']) or 0 for h in native['hsps'])
    total_d = sum(_present(h['identity_denominator']) or 0 for h in native['hsps'])
    for name, unit, number in (
        ('nonoverlapping_hsp_reported_identity_count','paired_column', total_i),
        ('nonoverlapping_hsp_reported_alignment_columns','alignment_column',total_d),
        ('nonoverlapping_hsp_reported_identity_over_columns','fraction',(total_i,total_d)),
    ):
        _cell(value[name], unit, number, aggregate_refs, path + '/' + name,
              state=aggregate_state, reasons=reasons, params=params)
    for name, field, minimum in (
        ('maximum_reported_hsp_bit_score','bit_score',False),
        ('maximum_reported_hsp_raw_score','raw_score',False),
        ('minimum_reported_hsp_expectation','expect',True),
    ): _validate_extremum(value[name], native, key, field, minimum, path + '/' + name)
    expected_issues = [i for hsp in hsps for i in hsp['diagnostics']]
    for conflict in graph['conflicts']:
        hsp_keys = []
        for column in conflict['columns']:
            hk = {n:column[n] for n in _KEY_FIELDS[:4]}
            if hk not in hsp_keys: hsp_keys.append(hk)
        expected_issues.append(_issue(conflict['code'], graph['distinct_pair_count']['inputs'],
            columns=conflict['columns'], hsps=hsp_keys))
    if mapping == 'incomplete_geometry':
        expected_issues.append(_issue('incomplete_displayed_geometry',[_ref(key,'hsps')]))
    expected_issues.extend(_issue(code, aggregate_refs)
        for code in value['nonoverlapping_hsp_reported_identity_count']['reasons'])
    _check_issues(value['diagnostics'], expected_issues, path + '/diagnostics')


def _display_state(query):
    marker = query['no_hits_marker']['state'] == 'present'
    populated = bool(query['subjects'] or query['descriptions'])
    if marker: return 'contradictory_native_no_hit_claim' if populated else 'native_no_hit_claim'
    if query['subjects']: return 'alignments_displayed'
    if query['descriptions']: return 'descriptions_only'
    return 'empty_without_native_no_hit_claim'


def _statistic_issues(native, key):
    """Compare overlapping scientific cells only within the same statistic scope."""
    expected, groups = [], {}
    fields = ('integer_value','decimal_value','text_value','bits','lambda','k','h')
    threshold_kinds = {'sequences_better_than','hsps_better_than_without_gapping'}
    for index, row in enumerate(native['statistics']):
        threshold = _present(row['threshold'])
        if row['kind'] in threshold_kinds and threshold is None: continue
        scope = Decimal(threshold) if row['kind'] in threshold_kinds else None
        measured = {f: (row[f]['value'] if f in ('integer_value','text_value') else Decimal(row[f]['value']))
                    for f in fields if row[f]['state'] == 'present'}
        prior = groups.setdefault((row['kind'],scope),[])
        if any(any(values[f] != measured[f] for f in values.keys() & measured.keys()) for _,values in prior):
            expected.append(_issue('statistic_occurrences_disagree',
                [_ref(key,'statistics/' + str(i)) for i,_ in prior] + [_ref(key,'statistics/' + str(index))]))
        prior.append((index,measured))
    return expected


def _validate_query(value, sheet, params, path):
    key = value['key']
    native = _native(sheet, key, path + '/key')
    _same(value['display_state'], _display_state(native), path + '/display_state')
    subjects = value['subjects']
    _require(len(subjects) == len(native['subjects']), path + '/subjects')
    for si, subject in enumerate(subjects):
        _same(subject['key'], {**key, 'subject_ordinal':si}, f'{path}/subjects/{si}/key')
        _validate_subject(subject, sheet, params, f'{path}/subjects/{si}')
    hsps = [h for s in subjects for h in s['hsps']]
    counts = {'description':len(native['descriptions']), 'subject':len(subjects),
              'hsp':len(hsps), 'block':sum(len(h['blocks']) for h in hsps)}
    for kind, count in counts.items():
        field = 'displayed_' + kind + '_count'
        refs = [_ref(key, 'descriptions' if kind == 'description' else 'subjects')]
        _cell(value[field], kind + '_occurrence', count, refs, path + '/' + field, reasons=[])
    special = None
    if value['display_state'] == 'native_no_hit_claim':
        special = [_ref(key, f) for f in ('no_hits_marker','descriptions','subjects','length')]
    _validate_position_union(value['any_displayed_subject_query_paired_union'],
        [s['coverage']['query_trace_paired_union'] for s in subjects],
        length=native['length'], length_ref=_ref(key, 'length'), missing=[], params=params,
        zero_refs=special, path=path + '/any_displayed_subject_query_paired_union')
    required = {'contradictory_native_no_hit_claim':'native_no_hit_with_displayed_population',
                'descriptions_only':'descriptions_without_subject_blocks',
                'empty_without_native_no_hit_claim':'empty_without_native_no_hit'}
    if value['display_state'] in required:
        _require_codes(value['diagnostics'], [required[value['display_state']]], path + '/diagnostics')
    expected = [i for subject in subjects for i in subject['diagnostics']]
    if value['display_state'] in required:
        expected.append(_issue(required[value['display_state']],
            [_ref(key,f) for f in ('no_hits_marker','descriptions','subjects')]))
    expected += _statistic_issues(native,key)
    _check_issues(value['diagnostics'],expected,path + '/diagnostics')


def _validate_components(value, sheet, params, path=''):
    _same(value['sheet_sha256'], canonical_sheet_sha256(sheet), path + '/sheet_sha256')
    _same(value['formula_version'], params['formula_version'], path + '/formula_version')
    _require(len(value['reports']) == len(sheet['reader_results']), path + '/reports')
    for ri, (report, raw) in enumerate(zip(value['reports'], sheet['reader_results'])):
        rp = f'{path}/reports/{ri}'
        _same(report['report_ordinal'], ri, rp + '/report_ordinal')
        _require(len(report['queries']) == len(raw['queries']), rp + '/queries')
        for qi, query in enumerate(report['queries']):
            _same(query['key'], _key(ri,qi), f'{rp}/queries/{qi}/key')
            _validate_query(query, sheet, params, f'{rp}/queries/{qi}')
        queries = raw['queries']
        subjects = [s for q in queries for s in q['subjects']]
        hsps = [h for s in subjects for h in s['hsps']]
        counts = {'query':len(queries),'description':sum(len(q['descriptions']) for q in queries),
                  'subject':len(subjects),'hsp':len(hsps),'block':sum(len(h['traceback_blocks']) for h in hsps)}
        for kind, count in counts.items():
            name = 'displayed_' + kind + '_count'
            _cell(report[name], kind + '_occurrence', count,
                  [{'report_ordinal':ri,'pointer':'/queries'}], rp + '/' + name, reasons=[])
        _check_issues(report['diagnostics'],[i for q in report['queries'] for i in q['diagnostics']],rp + '/diagnostics')
    _check_issues(value['diagnostics'],sheet['diagnostics'] +
        [i for r in value['reports'] for i in r['diagnostics']],path + '/diagnostics')


def _result_degraded(components, sheet):
    if sheet['diagnostics']: return True
    def degraded(v):
        if type(v) is list: return any(degraded(x) for x in v)
        if type(v) is not dict: return False
        if v.get('mapping_state') in ('observed_conflict','incomplete_geometry'): return True
        if 'strings_support' in v and (not v['strings_support']['complete_for_displayed_blocks'] or
            not v['pair_geometry_support']['complete_for_displayed_blocks'] or v['contiguous_blocks'] != 'yes'): return True
        if 'unit' in v and v.get('state') in ('invalid','conflict'): return True
        return any(degraded(x) for x in v.values())
    return degraded(components)


def validate_directional_numerical(name: str, value: dict, *, sheet: dict | None = None,
                                   parameters: dict | None = None) -> dict:
    """Validate closed shapes and all scientific operands, returning a detached copy.

    Required semantic context is never replaced by shape-only success. Embedded
    and explicitly supplied context must agree exactly. Validation does not
    reacquire bytes or assert that supplied reports are authentic service jobs.
    """
    _require(type(name) is str and name in _NAMES, '/name')
    _shape(name, value)
    if name == 'DirectionalCalculationParameters':
        if parameters is not None:
            _plain_json(parameters,'/parameters')
            _require(_identity(parameters) == _identity(value), '/parameters', 'semantic_context_conflict')
        return deepcopy(value)
    observed = None
    embedded_params = None
    if name == 'DirectionalSheet': observed = value
    elif name == 'DirectionalSheetResult': observed = value['sheet']
    elif name == 'DirectionalScoringSheet':
        observed, embedded_params = value['observed'], value['calculated']['parameters']
    elif name == 'DirectionalComponents': embedded_params = value['parameters']
    elif name == 'DirectionalComponentsResult' and value['components'] is not None:
        embedded_params = value['components']['parameters']
    null_result = name.endswith('Result') and value['sheet' if name == 'DirectionalSheetResult' else 'components'] is None
    if null_result:
        if sheet is not None:
            _shape('DirectionalSheet', sheet, '/sheet')
            _validate_sheet(sheet, '/sheet')
        _walk_references(value['diagnostics'], sheet, '/diagnostics')
        _require(all(i['code'] in _ARGUMENT_CODES for i in value['diagnostics']), '/diagnostics')
        return deepcopy(value)
    if observed is not None:
        if sheet is not None:
            _plain_json(sheet,'/sheet')
            _require(_identity(sheet) == _identity(observed), '/sheet', 'semantic_context_conflict')
        sheet = observed
    _require(sheet is not None, '/sheet', 'semantic_context_missing')
    _shape('DirectionalSheet', sheet, '/sheet')
    _validate_sheet(sheet, '/sheet')
    if embedded_params is not None:
        if parameters is not None:
            _plain_json(parameters,'/parameters')
            _require(_identity(parameters) == _identity(embedded_params), '/parameters', 'semantic_context_conflict')
        parameters = embedded_params
    if name not in ('DirectionalSheet','DirectionalSheetResult','CorrespondenceGraph'):
        _require(parameters is not None, '/parameters', 'semantic_context_missing')
        _shape('DirectionalCalculationParameters', parameters, '/parameters')
    if name == 'DirectionalSheet':
        return deepcopy(value)
    if name == 'DirectionalSheetResult':
        expected = 'partial' if sheet['diagnostics'] else 'available'
        _same(value['state'], expected, '/state')
        _same(value['diagnostics'], sheet['diagnostics'], '/diagnostics')
        return deepcopy(value)
    _walk_references(value, sheet)
    if name == 'BlockComponents': _validate_block(value, sheet, parameters, '')
    elif name == 'HspComponents': _validate_hsp(value, sheet, parameters, '')
    elif name == 'CorrespondenceGraph': _validate_graph(value, sheet, '')
    elif name == 'DirectionalComponents': _validate_components(value, sheet, parameters)
    elif name == 'DirectionalComponentsResult':
        _validate_components(value['components'], sheet, parameters, '/components')
        _same(value['diagnostics'], value['components']['diagnostics'], '/diagnostics')
        partial = _result_degraded(value['components'], sheet) or bool(
            _diagnostic_codes(value['diagnostics']) - {'printed_zero_expectation','no_execution_or_occurrence_evidence'})
        _same(value['state'], 'partial' if partial else 'available', '/state')
    else:
        _validate_components(value['calculated'], sheet, parameters, '/calculated')
    return deepcopy(value)


__all__ = ['DirectionalNumericalContractError', 'canonical_sheet_sha256',
           'directional_numerical_schema', 'validate_directional_numerical']
