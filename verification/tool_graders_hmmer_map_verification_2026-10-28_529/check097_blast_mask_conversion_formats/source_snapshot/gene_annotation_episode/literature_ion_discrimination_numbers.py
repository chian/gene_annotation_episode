"""Exact original-token reading for ion-discrimination estimates and limits.

This local lexical extension does not alter shared readers or source bytes.
Scientific ownership, quantity meanings and applicability are separate inputs.
"""
from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from .domain import identity
from .literature_experimental_contracts import ExperimentalContractError
from .literature_rate_native_inputs import _field_contexts
from .literature_partner_source_fields import (_ALL_TAGS, _unit_continuation, _BETWEEN_AND,
    _BETWEEN_FIRST_PREFIX, _BETWEEN_FIRST_SUFFIX, _between_numeric_scope, _table_contexts)

_DECIMAL = r'[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?'
_GROUPED = r'[+−-]?[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?(?:[eE][+−-]?[0-9]+)?'
_POWER = re.compile(r'10<sup>([+−-]?[0-9]+)</sup>\Z')
_APPROX = re.compile(r'(?:[~≈≃≅∼]|\b(?:approximately|roughly|around|about|circa|approx\.?))\s*$', re.I)
_MARKERS = [(re.compile(pattern + r'\s*$', re.I), code) for pattern, code in (
    (r'(?:>=|≥|\bat\s+least|\bno\s+less\s+than|\bgreater\s+than\s+or\s+equal\s+to)', 'ge'),
    (r'(?:<=|≤|\bat\s+most|\bno\s+more\s+than|\bless\s+than\s+or\s+equal\s+to)', 'le'),
    (r'(?:>|\bgreater\s+than|\bmore\s+than|\babove|\bexceed(?:s|ed)?)', 'gt'),
    (r'(?:<|\bless\s+than|\bbelow)', 'lt'),
    (r'\blower\s+limit\s+(?:of|on|at)', 'lower_limit'),
    (r'\bupper\s+limit\s+(?:of|on|at)', 'upper_limit'))]
_UNIT = re.compile(r'(?:ions?\s*/\s*(?:s|sec(?:onds?)?)|(?:s|min)\s*(?:\^?\s*[-−⁻]\s*[1¹])|per[_ ]?(?:s|min)|1\s*/\s*(?:s|min)|[pnumµμ]?[AVS]|[nmuµμ]?M)\b')


def _fail(code, field='number'):
    raise ExperimentalContractError(code, field)


def rational(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def fraction(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def _finite(exact):
    try:
        value = float(exact)
    except (OverflowError, ValueError):
        _fail('numerical_model_range')
    if not math.isfinite(value) or value == 0 and exact != 0:
        _fail('numerical_model_range')
    return value


def _parse(token):
    power = _POWER.fullmatch(token)
    if power:
        exponent = int(power[1].replace('−', '-'))
        if not -323 <= exponent <= 308:
            _fail('numerical_model_range')
        return Fraction(10) ** exponent
    if re.fullmatch(_DECIMAL, token) or re.fullmatch(_GROUPED, token):
        try:
            return Fraction(token.replace(',', '').replace('−', '-'))
        except (ValueError, OverflowError):
            _fail('numerical_model_range')
    _fail('unimplemented_number_representation')


def read_ion_number(selection, *, sources, _spread=False):
    """Authenticate a complete decimal/grouped/JATS-power token and qualifiers."""
    if set(selection) != {'witness', 'number_start', 'number_end'}:
        _fail('closed_fields_required')
    w = sources.witness(selection['witness'], 'ion_number.witness')
    start, end = selection['number_start'], selection['number_end']
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(w['quote']):
        _fail('source_number_span_order_invalid')
    token = w['quote'][start:end]
    exact = _parse(token)
    prefix, suffix = _field_contexts(sources, w, start, end)
    before, after = prefix[-1:], suffix[:1]
    stop = after == '.' and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ')]};:')
    pm_spread=_spread and bool(re.search(r'(?:±|\+\s*/\s*[-−])\s*$',prefix))
    if (before and (before.isalnum() or before in '.eE+−-_,^') and not pm_spread
            or after and (after.isdigit() or after in '.eE+,^') and not stop
            or re.match(r'^[−-](?:[0-9]|$)', suffix)
            or re.search(r'[0-9],\s*$', prefix) or re.match(r',\s*[0-9]', suffix)):
        _fail('partial_source_numeric_token')
    if not _spread and re.search(r'(?:±|\+\s*/\s*[-−]|\bSD|\bSEM|\bstandard\s+(?:error|deviation))\s*[:=]?\s*$', prefix, re.I):
        _fail('uncertainty_is_not_rate_point')
    if (re.search(r'\b(?:between|from|range|interval|CI|confidence\s+interval)\s*[:=]?\s*$', prefix, re.I)
            or ((_BETWEEN_AND.search(prefix) or (_BETWEEN_FIRST_PREFIX.search(prefix) and _BETWEEN_FIRST_SUFFIX.match(suffix))) and _between_numeric_scope(prefix,suffix)!='non_numeric_coordination')
            or re.search(r'[0-9]\s*(?:[–—−-]|\bto)\s*$', prefix)
            or re.match(r'\s*(?:[–—−-]|\bto\b)\s*[+−-]?(?:[0-9]|\.[0-9])', suffix)):
        _fail('interval_source_number_unsupported')
    operator = r'(?:[/×⋅·*+^]|\btimes\b|\bx\b)'
    if (re.search(r'[0-9]\s*' + operator + r'\s*$', prefix, re.I)
            or re.match(r'\s*' + operator + r'\s*[+−-]?(?:[0-9]|\.[0-9])', suffix, re.I)):
        _fail('source_arithmetic_expression_unsupported')
    remaining, relations, approximate = prefix, [], False
    while True:
        approx = _APPROX.search(remaining)
        if approx:
            approximate = True; remaining = remaining[:approx.start()]; continue
        found = next(((m, code) for rx, code in _MARKERS if (m := rx.search(remaining))), None)
        if found is None:
            break
        match, code = found; relations.append(code); remaining = remaining[:match.start()]
    if len(set(relations)) > 1 or re.search(r'\bnot\s*(?:(?:significantly|substantially|clearly)\s*)?$', remaining, re.I):
        _fail('source_qualification_conflicting')
    if re.match(r'\s*(?:or\s+(?:more|less)|and\s+(?:above|below)|approximately|about|roughly)\b', suffix, re.I):
        _fail('unimplemented_number_representation')
    if not relations and re.search(r'\b(?:LOD|LOQ|detection\s+limit|limit\s+of\s+(?:detection|quantification))\s*[:=]?\s*$', remaining, re.I):
        _fail('untyped_limit_source_number')
    if _spread and (relations or approximate or exact<0 or re.match(r'\s*\(?\s*(?:%|percent\b|CV\b|RSD\b)',suffix,re.I)):
        _fail('plain_nonnegative_absolute_spread_required')
    a = w['start'] + len(w['quote'][:start].encode('utf8')); b = w['start'] + len(w['quote'][:end].encode('utf8'))
    return {'selector': {**deepcopy(selection), 'witness': w}, 'raw_token': token,
        'exact': rational(exact), 'value': _finite(exact), 'relation': relations[0] if relations else 'point',
        'adjacent_approximate': approximate, 'adjacent_uncertainty_uninterpreted':bool(re.match(r'\s*\(?\s*(?:±|\+\s*/\s*[-−])',suffix)), 'byte_span': {'artifact_ref': w['artifact_ref'], 'start': a, 'end': b},
        'measurement_key': identity('ion_numeric_span', {'artifact_ref': w['artifact_ref'], 'start': a, 'end': b})}


def _unit(raw):
    text = re.sub(r'\s+', '', html.unescape(_ALL_TAGS.sub('', raw))).replace('−', '-').replace('⁻', '-').replace('¹', '1').replace('^', '')
    if text in ('s-1', '1/s', 'per_s', 'pers'):
        return 'per_s', Fraction(1)
    if text in ('min-1', '1/min', 'per_min', 'permin'):
        return 'per_min', Fraction(1, 60)
    if text in ('ion/s', 'ions/s', 'ion/sec', 'ions/sec', 'ions/second'):
        return 'ions_per_s', Fraction(1)
    if text in ('fold', '-fold', 'dimensionless'):
        return 'dimensionless', Fraction(1)
    _fail('unsupported_source_unit', 'unit')


def _continues(suffix):
    return _unit_continuation(suffix) or bool(re.match(
        r"\s*\)*\s*(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]|[-−⁻]\s*[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]|per\b|[/^*]|[×⋅·])",suffix))


def _following_spread(number,sources):
    selected=number['selector'];w=selected['witness']
    _,suffix=_table_contexts(sources,w,selected['number_start'],selected['number_end'])
    gap=r"(?:\s|</?[A-Za-z_][^<>]*>)*"
    pm=r"(?:±|&(?:plusmn|PlusMinus);|&#0*177;|&#[xX]0*[bB]1;|\+"+gap+r"/"+gap+r"[-−])"
    numeric=r"(?:10<sup>[+−-]?[0-9]+</sup>|"+_GROUPED+r"|"+_DECIMAL+r")"
    rx=re.compile(r"^"+gap+r"(?:\("+gap+r")?"+pm+gap+r"(?P<number>"+numeric+r")")
    match=rx.match(suffix)
    if match is None:_fail('ion_spread_syntax_unsupported')
    token=match['number'];mean_end=w['start']+len(w['quote'][:selected['number_end']].encode())
    start=mean_end+len(suffix[:match.start('number')].encode())
    span={'source_ref':w['source_ref'],'representation':w['representation'],'start':start,'end':start+len(token.encode()),'quote':token}
    return read_ion_number({'witness':span,'number_start':0,'number_end':len(token)},sources=sources,_spread=True)


def read_ion_unit(selection, *, sources):
    if selection is None:
        return None
    w = sources.witness(selection, 'ion_unit')
    prefix, suffix = _field_contexts(sources, w, 0, len(w['quote']))
    if (prefix[-1:] and (prefix[-1:].isalpha() or prefix[-1:] in '/_^⁻') or _continues(suffix)):
        _fail('partial_source_rate_unit', 'unit')
    unit, scale = _unit(w['quote'])
    return {'witness': w, 'unit': unit, 'canonical_rate_scale': rational(scale)}


def check_explicit_unit(number, unit, *, sources, dimensionless, _following=False):
    selected = number['selector'];w = selected['witness']
    _, suffix = _field_contexts(sources, w, selected['number_start'], selected['number_end'])
    visible = suffix.lstrip()
    if re.match(r'^\(?\s*(?:±|\+)',visible):
        if _following:_fail('ion_spread_syntax_unsupported')
        spread=_following_spread(number,sources)
        return check_explicit_unit(spread,unit,sources=sources,dimensionless=dimensionless,_following=True)
    wrapped=re.match(r'^\(\s*(?=(?:ions?|per|s|min|1/|[pnumµμ]?[AVS]|[nmuµμ]?M))',visible)
    if wrapped:visible=visible[wrapped.end():]
    fold=re.match(r'^-?fold\b',visible)
    if fold:
        if not dimensionless:_fail('source_number_unit_role_mismatch')
        if _continues(visible[fold.end():]):_fail('partial_source_rate_unit')
        return None
    match = _UNIT.match(visible)
    explicit_other=re.match(r'^(?:%|percent\b|per\s+cent\b|°\s*[CFK]|[nmuµμk]?g\b|[nmuµμ]?mol\b|[nmuµμ]?L\b|[nmuµμ]?m\b|[nmuµμ]?M\b|(?:seconds?|sec|s|minutes?|min|hours?|h|K|counts?|molecules?|ions?)\b)',visible)
    if explicit_other and (dimensionless or match is None):_fail('source_number_unit_role_mismatch')
    if match:
        try:
            native = _unit(match[0])
        except ExperimentalContractError:
            _fail('source_number_unit_role_mismatch')
        if dimensionless or unit is not None and native != (unit['unit'], fraction(unit['canonical_rate_scale'])):
            _fail('source_number_unit_role_mismatch')
        if _continues(visible[match.end():]):
            _fail('partial_source_rate_unit')
    elif _following and visible and not re.match(r'^[)\].,;:]+(?:\s|$)',visible):
        _fail('ion_spread_syntax_unsupported')
    elif not dimensionless and unit is not None and unit['unit'] == 'dimensionless':
        _fail('source_number_unit_role_mismatch')


__all__ = ['read_ion_number', 'read_ion_unit', 'check_explicit_unit', 'rational', 'fraction']
