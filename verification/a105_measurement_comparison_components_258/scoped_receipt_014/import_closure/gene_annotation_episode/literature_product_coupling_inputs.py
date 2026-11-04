"""Source-bound product/cofactor operands and explicit scientific relationships.

Callbacks authorize actually received sources. Scientific role/model selections
are witnessed interpretations, not facts inferred from matching names or units.
This pure reader performs no acquisition, persistence, model call or credit work.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import json
import re

from .domain import REF, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _interpretation, _witness_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_measurement_validation_inputs import (
    _read_number, _number_schema, _associate, _visible_span, _field_witness,
    _retained_witness_schema, _nullable, _array, _exact_schema, _exact,
    _unit as _fraction_unit, _unit_value as _fraction_unit_value,
    _APPROX_POINT, _RANGE, NUMBER_REASONS, RELATIONS, _visible,
)
from .literature_partner_source_fields import (
    number_selector_schema, read_source_rate_unit, _rate_unit, _NUMBER,
    _unit_contexts, _PRINTED_RATE_UNIT, _RATE_UNIT_START, _unit_continuation,
)

VERSION = 'a105_product_coupling_inputs_v1'
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'synthetic_fixture')
ORIGINS = dict(primary_source='reported', retained_extraction='derived', synthetic_fixture='synthetic')
ROLES = ('product', 'cofactor', 'reported_coupling')
CONTEXT_FIELDS = ('experiment', 'organism', 'expression_host', 'molecule', 'construct',
    'preparation', 'partners', 'intended_change', 'substrate', 'product', 'product_identity_method',
    'product_conditions', 'cofactor_conditions', 'blank', 'calibration', 'normalization',
    'repetition', 'uncertainty', 'source_conflict')
QUANTITY_MEANINGS = {
    'endpoint_role': ('product_formation', 'cofactor_consumption', 'coupling_fraction', 'other_endpoint', 'unknown', 'conflicting'),
    'measurement_semantics': ('reported_point', 'reported_nondetection', 'reported_negligible', 'unknown', 'conflicting'),
    'normalization': ('per_assayed_molecule', 'per_active_molecule', 'other_basis', 'unknown', 'conflicting'),
}
RELATIONSHIPS = {
    'source_pairing': ('author_assigned', 'not_assigned', 'unknown', 'conflicting'),
    'same_molecule': ('same', 'different', 'unknown', 'conflicting'),
    'same_preparation': ('same', 'different', 'unknown', 'conflicting'),
    'normalization': ('compatible', 'incompatible', 'unknown', 'conflicting'),
    'conditions': ('matched', 'different', 'unknown', 'conflicting'),
    'product_identity': ('chemically_identified', 'other_product', 'reporter_only', 'unknown', 'conflicting'),
    'molecular_attribution': ('controlled', 'mixed_or_unresolved', 'unknown', 'conflicting'),
}
NU_STATUSES = ('fixed_model', 'uncertain_model', 'unknown', 'conflicting')
EXTRA_NUMBER_REASONS = ('nondetection_source_text',)
UNIT_REASONS = ('source_unit_not_supplied', 'unsupported_source_rate_unit', 'unsupported_coupling_unit')
COVARIANCE_REASONS = ('covariance_not_supplied', 'covariance_json_invalid', 'covariance_contract_mismatch',
    'covariance_owner_mismatch', 'covariance_units_mismatch', 'covariance_basis_mismatch',
    'covariance_status_unknown', 'covariance_nonfinite_or_non_numeric', 'covariance_shape_invalid',
    'covariance_not_symmetric', 'covariance_not_positive_semidefinite', 'covariance_rate_inputs_unavailable')
_ND = re.compile(r'(?:ND|N\.?D\.?|not\s+detected|nondetected)', re.I)
_COV_FIELDS = ('version', 'order', 'measurement_keys', 'units', 'basis', 'variance_status', 'origin', 'covariance')


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _q(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def _float(value):
    from math import isfinite
    try:
        result = float(value)
        return result if isfinite(result) and (result != 0 or value == 0) else None
    except (ValueError, OverflowError):
        return None


def _interpreted_schema(values, enriched=False):
    return obj({**({'kind': {'const': 'source_interpretation'}} if enriched else {}),
        'value': {'enum': list(values)},
        'witnesses': _array(_retained_witness_schema() if enriched else _witness_schema())})


def _nu_schema(enriched=False):
    return obj({'kind': {'const': 'interpreted_reaction_account'},
        'direction': {'const': 'cofactor_per_product'}, 'status': {'enum': list(NU_STATUSES)},
        'exact_value': _nullable(_exact_schema()),
        'witnesses': _array(_retained_witness_schema() if enriched else _witness_schema()),
        **({'model_key': _nullable(deepcopy(REF))} if enriched else {})})


def product_coupling_population_schema():
    quantity = obj({'number': _nullable(number_selector_schema()), 'quantity_label': _nullable(_witness_schema()),
        'unit': _nullable(_witness_schema()),
        **{name: _interpreted_schema(values) for name, values in QUANTITY_MEANINGS.items()},
        'physical_identity': _nullable(_witness_schema()), 'dependency_witnesses': _array(_witness_schema())})
    return obj({'source_ref': deepcopy(REF), 'source_kind': {'enum': list(SOURCE_KINDS)},
        'context': obj({name: _nullable(_witness_schema()) for name in CONTEXT_FIELDS}),
        'quantities': obj({role: _nullable(quantity) for role in ROLES}),
        'relationships': obj({name: _interpreted_schema(values) for name, values in RELATIONSHIPS.items()}),
        'nu_cofactor_per_product': _nu_schema(), 'covariance_source_ref': _nullable(deepcopy(REF))})


def _coupling_number_schema():
    result = _number_schema()
    result['properties']['capability_reason'] = {'enum': [*NUMBER_REASONS, *EXTRA_NUMBER_REASONS, None]}
    return result


def _unit_schema():
    return obj({'witness': _retained_witness_schema(), 'raw_unit': {'type': 'string', 'minLength': 1},
        'canonical_unit': {'type': ['string', 'null']}, 'multiplier_exact': _nullable(_exact_schema()),
        'unavailable_reason': {'enum': [*UNIT_REASONS, None]}})


def _covariance_schema():
    return obj({'source_ref': _nullable(deepcopy(REF)), 'artifact_ref': _nullable(deepcopy(REF)),
        'status': {'enum': ['not_supplied', 'valid_known', 'valid_estimated', 'unavailable']},
        'unavailable_reason': {'enum': [*COVARIANCE_REASONS, None]},
        'origin': {'enum': ['reported', 'derived', 'synthetic', None]},
        'measurement_keys': _array(REF), 'units': _array({'type': 'string'}),
        'basis': {'type': ['string', 'null']}, 'variance_status': {'enum': ['known', 'estimated', 'unknown', None]},
        'matrix_exact': _nullable(_array(_array(_exact_schema())))})


def product_coupling_extraction_schema():
    quantity = obj({'number': _nullable(_coupling_number_schema()), 'quantity_label': _nullable(_retained_witness_schema()),
        'unit': _nullable(_unit_schema()),
        **{name: _interpreted_schema(values, True) for name, values in QUANTITY_MEANINGS.items()},
        'physical_identity': _nullable(_retained_witness_schema()),
        'dependency_witnesses': _array(_retained_witness_schema()),
        'canonical_value': {'type': ['number', 'null']}, 'canonical_exact_value': _nullable(_exact_schema()),
        'canonical_unit': {'type': ['string', 'null']}, 'dependency_keys': _array(REF, True),
        'physical_identity_key': _nullable(deepcopy(REF))})
    return obj({'version': {'const': VERSION}, 'source_ref': deepcopy(REF), 'artifact_ref': deepcopy(REF),
        'source_kind': {'enum': list(SOURCE_KINDS)},
        'context': obj({name: _nullable(obj({'value': {'type': 'string', 'minLength': 1},
            'witness': _retained_witness_schema()})) for name in CONTEXT_FIELDS}),
        'quantities': obj({role: _nullable(quantity) for role in ROLES}),
        'relationships': obj({name: _interpreted_schema(values, True) for name, values in RELATIONSHIPS.items()}),
        'nu_cofactor_per_product': _nu_schema(True), 'covariance': _covariance_schema(),
        'source_refs': _array(REF, True), 'input_origins': _array({'enum': list(ORIGINS.values())}, True)})


def _interpret(selected, values, sources, field):
    value = _interpretation(selected, values, sources, field)
    unique = {(w['artifact_ref'], w['start'], w['end']) for w in value['witnesses']}
    required = 0 if value['value'] == 'unknown' else 2 if value['value'] == 'conflicting' else 1
    if len(unique) < required:
        _fail('interpretation_witness_required', field)
    return value


def _number(selected, sources, origin):
    witness = sources.witness(selected['witness'], 'number.witness')
    a, z = selected['number_start'], selected['number_end']
    if not 0 <= a < z <= len(witness['quote']):
        _fail('source_number_span_order_invalid', 'number')
    token = witness['quote'][a:z]
    if not _ND.fullmatch(token):
        return _read_number(selected, sources, origin)
    start = witness['start'] + len(witness['quote'][:a].encode())
    end = witness['start'] + len(witness['quote'][:z].encode())
    _visible_span(sources, witness, start, end, 'number')
    raw = sources.source(witness['source_ref'], witness['representation'])['content']
    before, after = raw[max(0,start-1):start].decode(errors='ignore'), raw[end:end+1].decode(errors='ignore')
    if before.isalnum() or after.isalnum():
        _fail('partial_source_nondetection_token', 'number')
    return {'selector': {**deepcopy(selected), 'witness': witness}, 'raw_number': token,
        'native_value': None, 'native_exact_value': None, 'relation': 'unresolved',
        'capability_reason': 'nondetection_source_text',
        'representation_witness': _field_witness(sources, witness, start, end),
        'measurement_key': identity('literature_measurement', {'artifact_ref': witness['artifact_ref'],
            'number_start': start, 'number_end': end}), 'number_start_bytes': start,
        'number_end_bytes': end, 'origin': origin}


def _unit(selected, number, sources, role):
    if selected is None:
        return None
    witness = sources.witness(selected, role+'.unit')
    _visible_span(sources, witness, witness['start'], witness['end'], role+'.unit')
    if number is not None:
        _associate(number, witness, sources, role+'.unit')
    result = {'witness': witness, 'raw_unit': witness['quote'], 'canonical_unit': None,
        'multiplier_exact': None, 'unavailable_reason': None}
    try:
        if role == 'reported_coupling':
            kind = _fraction_unit_value(witness['quote'])
            if number is not None:
                _fraction_unit({'value': kind, 'witness': selected}, number, sources)
            result.update(canonical_unit='percent', multiplier_exact=_exact(Fraction(1 if kind=='percent' else 100)))
        else:
            unit = read_source_rate_unit(selected, sources=sources)
            result.update(canonical_unit=unit['canonical_unit'], multiplier_exact=_exact(Fraction(str(unit['multiplier']))))
            if number is not None:
                selector=number['selector']
                _,tail=_unit_contexts(sources,selector['witness'],selector['number_start'],selector['number_end'])
                tail=_visible(tail).lstrip()
                spread=re.match(r'(?:±|\+\s*/\s*-|\+\s*−)\s*[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?\s*',tail)
                if spread:tail=tail[spread.end():]
                printed=_PRINTED_RATE_UNIT.match(tail)
                if printed:
                    if _unit_continuation(tail[printed.end():]):_fail('partial_source_rate_unit',role+'.number')
                    try:
                        canonical,multiplier=_rate_unit(printed.group())
                    except ExperimentalContractError:
                        _fail('explicit_source_rate_unit_mismatch',role+'.number')
                    if (canonical,Fraction(str(multiplier)))!=(unit['canonical_unit'],Fraction(str(unit['multiplier']))):
                        _fail('explicit_source_rate_unit_mismatch',role+'.number')
                elif _RATE_UNIT_START.match(tail) or re.match(r'(?:%|percent\b|fraction\b|dimensionless\b)',tail,re.I):
                    _fail('explicit_source_rate_unit_mismatch',role+'.number')
    except ExperimentalContractError as error:
        if error.code not in ('unsupported_source_rate_unit', 'unsupported_precision_unit'):
            raise
        result['unavailable_reason'] = 'unsupported_coupling_unit' if role=='reported_coupling' else 'unsupported_source_rate_unit'
    return result


def _witness_key(witness):
    return identity('physical_source_span', {name: witness[name] for name in ('artifact_ref', 'start', 'end')})


def _nu_model_key(nu):
    if nu['exact_value'] is None:
        return None
    spans=sorted({(w['artifact_ref'],w['start'],w['end']) for w in nu['witnesses']})
    return identity('product_coupling_stoichiometric_model',
        {'direction':nu['direction'],'status':nu['status'],'exact_value':nu['exact_value'],
         'witnesses':[{'artifact_ref':artifact,'start':start,'end':end} for artifact,start,end in spans]})


def _covariance(reference, quantities, sources):
    result = {'source_ref': reference, 'artifact_ref': None, 'status': 'not_supplied' if reference is None else 'unavailable',
        'unavailable_reason': 'covariance_not_supplied', 'origin': None, 'measurement_keys': [],
        'units': [], 'basis': None, 'variance_status': None, 'matrix_exact': None}
    if reference is None:
        return result
    source = sources.source(reference, 'original'); result['artifact_ref'] = source['artifact_ref']
    def bad_constant(_token):
        raise ValueError('nonfinite')
    def pairs(items):
        value = {}
        for key, val in items:
            if key in value: raise ValueError('duplicate')
            value[key] = val
        return value
    try:
        raw = json.loads(source['content'].decode(), parse_float=str, parse_int=str,
            parse_constant=bad_constant, object_pairs_hook=pairs)
    except (UnicodeDecodeError, ValueError):
        result['unavailable_reason'] = 'covariance_json_invalid'; return result
    if not isinstance(raw, dict) or set(raw) != set(_COV_FIELDS) or raw['version'] != 'a105_product_coupling_covariance_v1' or raw['order'] != ['product','cofactor']:
        result['unavailable_reason'] = 'covariance_contract_mismatch'; return result
    if raw['origin'] not in ('reported','derived','synthetic') or raw['variance_status'] not in ('known','estimated','unknown'):
        result['unavailable_reason'] = 'covariance_contract_mismatch'; return result
    if any(quantities[role] is None or quantities[role]['number'] is None for role in ('product','cofactor')):
        result['unavailable_reason'] = 'covariance_rate_inputs_unavailable'; return result
    owners = [quantities[role]['number']['measurement_key'] for role in ('product','cofactor')]
    if raw['measurement_keys'] != owners:
        result['unavailable_reason'] = 'covariance_owner_mismatch'; return result
    if raw['units'] != ['per_min','per_min'] or any(quantities[r]['canonical_unit']!='per_min' for r in ('product','cofactor')):
        result['unavailable_reason'] = 'covariance_units_mismatch'; return result
    if raw['basis'] != 'joint_covariance_of_selected_rate_estimates':
        result['unavailable_reason'] = 'covariance_basis_mismatch'; return result
    result.update(origin=raw['origin'], measurement_keys=owners, units=raw['units'], basis=raw['basis'], variance_status=raw['variance_status'])
    matrix = raw['covariance']
    if not isinstance(matrix,list) or len(matrix)!=2 or any(not isinstance(row,list) or len(row)!=2 for row in matrix):
        result['unavailable_reason'] = 'covariance_shape_invalid'; return result
    if any(type(v) is not str or _NUMBER.fullmatch(v) is None for row in matrix for v in row):
        result['unavailable_reason'] = 'covariance_nonfinite_or_non_numeric'; return result
    exact = [[Fraction(v.replace('−','-')) for v in row] for row in matrix]
    if exact[0][1] != exact[1][0]:
        result['unavailable_reason'] = 'covariance_not_symmetric'; return result
    if exact[0][0]<0 or exact[1][1]<0 or exact[0][0]*exact[1][1]-exact[0][1]**2<0:
        result['unavailable_reason'] = 'covariance_not_positive_semidefinite'; return result
    result['matrix_exact'] = [[_exact(v) for v in row] for row in exact]
    if raw['variance_status']=='unknown':
        result['unavailable_reason'] = 'covariance_status_unknown'; return result
    result.update(status='valid_'+raw['variance_status'], unavailable_reason=None)
    return result


def read_product_coupling_inputs(arguments, *, read_source):
    """Read the nominated arm and optional received joint covariance once."""
    args=deepcopy(arguments); validate_schema(args, product_coupling_population_schema())
    sources=_Sources(read_source); original=sources.source(args['source_ref'],'original')
    origin=ORIGINS[args['source_kind']]
    context={}
    for name, selected in args['context'].items():
        witness=None if selected is None else sources.witness(selected,'context.'+name)
        context[name]=None if witness is None else {'value':witness['quote'],'witness':witness}
    quantities={}
    for role, selected in args['quantities'].items():
        if selected is None:
            quantities[role]=None; continue
        number=None if selected['number'] is None else _number(selected['number'],sources,origin)
        label=None if selected['quantity_label'] is None else sources.witness(selected['quantity_label'],role+'.quantity_label')
        if number is not None:
            if label is None: _fail('selected_quantity_label_required',role)
            _visible_span(sources,label,label['start'],label['end'],role+'.quantity_label')
            _associate(number,label,sources,role+'.quantity_label')
        unit=_unit(selected['unit'],number,sources,role)
        physical=None if selected['physical_identity'] is None else sources.witness(selected['physical_identity'],role+'.physical_identity')
        dependencies=[sources.witness(w,role+'.dependency') for w in selected['dependency_witnesses']]
        canonical=None if number is None or number['native_exact_value'] is None or unit is None or unit['multiplier_exact'] is None else _q(number['native_exact_value'])*_q(unit['multiplier_exact'])
        quantities[role]={'number':number,'quantity_label':label,'unit':unit,
            **{name:_interpret(selected[name],values,sources,role+'.'+name) for name,values in QUANTITY_MEANINGS.items()},
            'physical_identity':physical,'dependency_witnesses':dependencies,
            'canonical_value':None if canonical is None else _float(canonical),
            'canonical_exact_value':None if canonical is None else _exact(canonical),
            'canonical_unit':None if unit is None else unit['canonical_unit'],
            'dependency_keys':list(dict.fromkeys(([number['measurement_key']] if number else [])+[_witness_key(w) for w in dependencies])),
            'physical_identity_key':None if physical is None else _witness_key(physical)}
    relationships={name:_interpret(args['relationships'][name],values,sources,'relationships.'+name) for name,values in RELATIONSHIPS.items()}
    selected=args['nu_cofactor_per_product']; witnesses=[sources.witness(w,'nu.witnesses') for w in selected['witnesses']]
    distinct={(w['artifact_ref'],w['start'],w['end']) for w in witnesses}
    required=0 if selected['status']=='unknown' else 2 if selected['status']=='conflicting' else 1
    if len(distinct)<required: _fail('interpretation_witness_required','nu_cofactor_per_product')
    if (selected['status']=='unknown') != (selected['exact_value'] is None):
        if selected['status']!='conflicting' or selected['exact_value'] is not None:
            _fail('nu_model_value_status_mismatch','nu_cofactor_per_product')
    nu={**selected,'witnesses':witnesses};nu['model_key']=_nu_model_key(nu)
    covariance=_covariance(args['covariance_source_ref'],quantities,sources)
    result={'version':VERSION,'source_ref':args['source_ref'],'artifact_ref':original['artifact_ref'],
        'source_kind':args['source_kind'],'context':context,'quantities':quantities,'relationships':relationships,
        'nu_cofactor_per_product':nu,'covariance':covariance,'source_refs':list(sources.references),'input_origins':[origin]}
    validate_product_coupling_extraction(result)
    return result


def validate_product_coupling_extraction(data):
    """Validate retained arithmetic/identities without original source IO."""
    validate_schema(data,product_coupling_extraction_schema())
    if data['source_ref'] not in data['source_refs'] or data['input_origins']!=[ORIGINS[data['source_kind']]]:
        _fail('product_coupling_source_record_mismatch','source_refs')
    def witnesses(node):
        if isinstance(node,dict):
            if set(node)=={'source_ref','representation','start','end','quote','artifact_ref'}:
                if node['source_ref'] not in data['source_refs'] or node['end']-node['start']!=len(node['quote'].encode()):
                    _fail('product_coupling_witness_record_mismatch','witness')
            else:
                for child in node.values():witnesses(child)
        elif isinstance(node,list):
            for child in node:witnesses(child)
    witnesses(data)
    for item in data['context'].values():
        if item is not None and item['value']!=item['witness']['quote']:
            _fail('product_coupling_literal_record_mismatch','context')
    for role,item in data['quantities'].items():
        if item is None:continue
        number=item['number']; canonical=None
        if number is not None:
            selected=number['selector']; w=selected['witness']; a,z=selected['number_start'],selected['number_end']
            raw=number['raw_number']
            if not 0<=a<z<=len(w['quote']) or w['quote'][a:z]!=raw:
                _fail('product_coupling_number_record_mismatch',role)
            start=w['start']+len(w['quote'][:a].encode()); end=w['start']+len(w['quote'][:z].encode())
            key=identity('literature_measurement',{'artifact_ref':w['artifact_ref'],'number_start':start,'number_end':end})
            if (number['number_start_bytes']!=start or number['number_end_bytes']!=end or number['measurement_key']!=key
                    or number['origin']!=ORIGINS[data['source_kind']]):
                _fail('product_coupling_measurement_binding_mismatch',role)
            approximate=_APPROX_POINT.fullmatch(raw)
            if _ND.fullmatch(raw):
                exact=None; reason='nondetection_source_text'
                if number['relation']!='unresolved':_fail('product_coupling_number_record_mismatch',role)
            elif re.fullmatch(r'[+−-]?(?:NaN|Inf|Infinity)',raw,re.I):
                exact=None;reason='nonfinite_source_statistic_unavailable'
            elif number['relation']=='range' and _RANGE.fullmatch(raw):
                exact=None;reason='source_range_unimplemented'
            elif _NUMBER.fullmatch(raw) or approximate:
                exact=Fraction((approximate.group('point') if approximate else raw).replace('−','-'))
                reason={'approximate':'source_approximation_unimplemented','unresolved':'source_negated_comparison_unimplemented'}.get(number['relation'])
            else:_fail('product_coupling_number_record_mismatch',role)
            if (number['native_exact_value']!=(None if exact is None else _exact(exact))
                    or number['native_value']!=(None if exact is None else _float(exact)) or number['capability_reason']!=reason):
                _fail('product_coupling_number_record_mismatch',role)
            rep=number['representation_witness']
            if rep['artifact_ref']!=w['artifact_ref'] or not rep['start']<=start<end<=rep['end'] or rep['quote'].encode()[start-rep['start']:end-rep['start']]!=raw.encode():
                _fail('product_coupling_representation_binding_mismatch',role)
            if item['unit'] is not None and item['unit']['multiplier_exact'] is not None and exact is not None:
                canonical=exact*_q(item['unit']['multiplier_exact'])
        unit=item['unit']
        if unit is not None:
            try:
                if role=='reported_coupling':
                    kind=_fraction_unit_value(unit['raw_unit'])
                    expected_unit,expected_multiplier='percent',Fraction(1 if kind=='percent' else 100)
                else:
                    expected_unit,multiplier=_rate_unit(unit['raw_unit'])
                    expected_multiplier=Fraction(str(multiplier))
            except ExperimentalContractError:
                expected_unit,expected_multiplier=None,None
            if (unit['canonical_unit']!=expected_unit
                    or unit['multiplier_exact']!=(None if expected_multiplier is None else _exact(expected_multiplier))
                    or (unit['unavailable_reason'] is None)!=(expected_multiplier is not None)):
                _fail('product_coupling_unit_record_mismatch',role)
        if (unit is not None and unit['raw_unit']!=unit['witness']['quote']
                or item['canonical_exact_value']!=(None if canonical is None else _exact(canonical))
                or item['canonical_value']!=(None if canonical is None else _float(canonical))
                or item['canonical_unit']!=(None if unit is None else unit['canonical_unit'])):
            _fail('product_coupling_unit_record_mismatch',role)
        expected_keys=list(dict.fromkeys(([number['measurement_key']] if number else [])+[_witness_key(w) for w in item['dependency_witnesses']]))
        if item['dependency_keys']!=expected_keys or item['physical_identity_key']!=(None if item['physical_identity'] is None else _witness_key(item['physical_identity'])):
            _fail('product_coupling_dependency_record_mismatch',role)
    def interpreted(value,field):
        unique={(w['artifact_ref'],w['start'],w['end']) for w in value['witnesses']}
        required=0 if value['value']=='unknown' else 2 if value['value']=='conflicting' else 1
        if len(unique)<required:_fail('interpretation_witness_required',field)
    for role,item in data['quantities'].items():
        if item:
            for name in QUANTITY_MEANINGS:interpreted(item[name],role+'.'+name)
    for name,value in data['relationships'].items():interpreted(value,'relationships.'+name)
    nu=data['nu_cofactor_per_product']
    if (nu['status']=='unknown' and nu['exact_value'] is not None
            or nu['status'] in ('fixed_model','uncertain_model') and nu['exact_value'] is None):
        _fail('nu_model_value_status_mismatch','nu')
    distinct={(w['artifact_ref'],w['start'],w['end']) for w in nu['witnesses']}
    required=0 if nu['status']=='unknown' else 2 if nu['status']=='conflicting' else 1
    if len(distinct)<required:_fail('interpretation_witness_required','nu')
    expected_model=_nu_model_key(nu)
    if nu['model_key']!=expected_model:_fail('product_coupling_nu_binding_mismatch','nu')
    covariance=data['covariance']
    if covariance['status'].startswith('valid_'):
        if any(data['quantities'][role] is None or data['quantities'][role]['number'] is None
               or data['quantities'][role]['canonical_unit']!='per_min' for role in ('product','cofactor')):
            _fail('product_coupling_covariance_binding_mismatch','covariance')
        owners=[data['quantities'][role]['number']['measurement_key'] for role in ('product','cofactor')]
        if (covariance['measurement_keys']!=owners or covariance['units']!=['per_min','per_min']
                or covariance['basis']!='joint_covariance_of_selected_rate_estimates'
                or covariance['status']!='valid_'+covariance['variance_status'] or covariance['unavailable_reason'] is not None
                or covariance['source_ref'] not in data['source_refs'] or covariance['artifact_ref'] is None
                or covariance['origin'] is None):
            _fail('product_coupling_covariance_binding_mismatch','covariance')
        matrix=covariance['matrix_exact']
        if matrix is None or len(matrix)!=2 or any(len(row)!=2 for row in matrix):
            _fail('product_coupling_covariance_binding_mismatch','covariance')
        c=[[_q(v) for v in row] for row in matrix]
        if c[0][1]!=c[1][0] or c[0][0]<0 or c[1][1]<0 or c[0][0]*c[1][1]-c[0][1]**2<0:
            _fail('product_coupling_covariance_binding_mismatch','covariance')


__all__=['VERSION','SOURCE_KINDS','ORIGINS','ROLES','CONTEXT_FIELDS','QUANTITY_MEANINGS','RELATIONSHIPS',
    'NU_STATUSES','EXTRA_NUMBER_REASONS','UNIT_REASONS','COVARIANCE_REASONS',
    'product_coupling_population_schema','product_coupling_extraction_schema',
    'read_product_coupling_inputs','validate_product_coupling_extraction']
