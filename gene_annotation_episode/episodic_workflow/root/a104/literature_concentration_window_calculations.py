"""Finite numerical concentration-window section, independent of credit/state."""
from copy import deepcopy
from fractions import Fraction
import math

from .literature_concentration_window_inputs import (
    ROLES, ANALYTES, _schema, _check, _digest, _exact, _q, _float, _reasons, _merge,
    _fail, _same, _validate_covariance,
)

_DEFINITIONS = {
    'substrate_start': {'formula': 'selected_native_token*unit_multiplier', 'unit': 'uM', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['substrate_start'], 'population': 'source', 'covariance_required': False},
    'substrate_end': {'formula': 'selected_native_token*unit_multiplier', 'unit': 'uM', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['substrate_end'], 'population': 'source', 'covariance_required': False},
    'total_product_start': {'formula': 'selected_native_token*unit_multiplier', 'unit': 'uM', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['total_product_start'], 'population': 'source', 'covariance_required': False},
    'total_product_end': {'formula': 'selected_native_token*unit_multiplier', 'unit': 'uM', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['total_product_end'], 'population': 'source', 'covariance_required': False},
    'fate_product_start': {'formula': 'selected_native_token*unit_multiplier', 'unit': 'uM', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['fate_product_start'], 'population': 'source', 'covariance_required': False},
    'fate_product_end': {'formula': 'selected_native_token*unit_multiplier', 'unit': 'uM', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['fate_product_end'], 'population': 'source', 'covariance_required': False},
    'coordinate_start': {'formula': 'selected_native_token*unit_multiplier', 'unit': 's', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['coordinate_start'], 'population': 'source', 'covariance_required': False},
    'coordinate_end': {'formula': 'selected_native_token*unit_multiplier', 'unit': 's', 'meaning': 'Native source operand; not an experimental reliability score.', 'operands': ['coordinate_end'], 'population': 'source', 'covariance_required': False},
    'substrate_loss': {'formula': 'S0-S1', 'unit': 'uM', 'meaning': 'Signed observed change over the selected common window.', 'operands': ['substrate_start', 'substrate_end'], 'population': 'source', 'covariance_required': False},
    'total_product_gain': {'formula': 'T1-T0', 'unit': 'uM', 'meaning': 'Signed observed change over the selected common window.', 'operands': ['total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': False},
    'fate_product_gain': {'formula': 'F1-F0', 'unit': 'uM', 'meaning': 'Signed observed change over the selected common window.', 'operands': ['fate_product_start', 'fate_product_end'], 'population': 'source', 'covariance_required': False},
    'coordinate_span': {'formula': 't1-t0', 'unit': 's', 'meaning': 'Released coordinate separation, not automatically elapsed time.', 'operands': ['coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': False},
    'chemical_discrepancy': {'formula': '(S0-S1)/nuS-(T1-T0)/nuT', 'unit': 'uM_reaction_equivalents', 'meaning': 'Signed disagreement between matched chemical readouts under declared stoichiometry.', 'operands': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': False},
    'chemical_ratio': {'formula': '((S0-S1)/nuS)/((T1-T0)/nuT)', 'unit': 'dimensionless', 'meaning': 'Relative agreement of matched substrate loss and total-product gain.', 'operands': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': False},
    'chemical_relative_discrepancy': {'formula': 'chemical_ratio-1', 'unit': 'dimensionless', 'meaning': 'Signed relative mismatch of the same chemical readouts.', 'operands': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': False},
    'fate_fraction': {'formula': '((F1-F0)/nuF)/((T1-T0)/nuT)', 'unit': 'dimensionless', 'meaning': 'Specific measured product fate relative to total measured cleavage; not enzyme attribution.', 'operands': ['total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end'], 'population': 'source', 'covariance_required': False},
    'substrate_depletion_fraction': {'formula': '(S0-S1)/S0', 'unit': 'fraction', 'meaning': 'Fractional depletion, which can limit an initial-regime interpretation.', 'operands': ['substrate_start', 'substrate_end'], 'population': 'source', 'covariance_required': False},
    'source_interval_average_substrate': {'formula': '60*substrate_loss/coordinate_span', 'unit': 'uM/min', 'meaning': 'Interval-average concentration change; never initial rate, Vmax or kcat.', 'operands': ['substrate_start', 'substrate_end', 'coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': False},
    'scenario_interval_average_substrate': {'formula': '60*substrate_loss/coordinate_span', 'unit': 'uM/min', 'meaning': 'Interval-average concentration change; never initial rate, Vmax or kcat.', 'operands': ['substrate_start', 'substrate_end', 'coordinate_start', 'coordinate_end'], 'population': 'scenario', 'covariance_required': False},
    'source_interval_average_total_product': {'formula': '60*total_product_gain/coordinate_span', 'unit': 'uM/min', 'meaning': 'Interval-average concentration change; never initial rate, Vmax or kcat.', 'operands': ['total_product_start', 'total_product_end', 'coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': False},
    'scenario_interval_average_total_product': {'formula': '60*total_product_gain/coordinate_span', 'unit': 'uM/min', 'meaning': 'Interval-average concentration change; never initial rate, Vmax or kcat.', 'operands': ['total_product_start', 'total_product_end', 'coordinate_start', 'coordinate_end'], 'population': 'scenario', 'covariance_required': False},
    'source_interval_average_fate_product': {'formula': '60*fate_product_gain/coordinate_span', 'unit': 'uM/min', 'meaning': 'Interval-average concentration change; never initial rate, Vmax or kcat.', 'operands': ['fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': False},
    'scenario_interval_average_fate_product': {'formula': '60*fate_product_gain/coordinate_span', 'unit': 'uM/min', 'meaning': 'Interval-average concentration change; never initial rate, Vmax or kcat.', 'operands': ['fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'population': 'scenario', 'covariance_required': False},
    'substrate_loss_variance': {'formula': 'gradient(substrate_loss)^T*C*gradient(substrate_loss)', 'unit': '(uM)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['substrate_start', 'substrate_end'], 'population': 'source', 'covariance_required': True},
    'total_product_gain_variance': {'formula': 'gradient(total_product_gain)^T*C*gradient(total_product_gain)', 'unit': '(uM)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': True},
    'fate_product_gain_variance': {'formula': 'gradient(fate_product_gain)^T*C*gradient(fate_product_gain)', 'unit': '(uM)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['fate_product_start', 'fate_product_end'], 'population': 'source', 'covariance_required': True},
    'coordinate_span_variance': {'formula': 'gradient(coordinate_span)^T*C*gradient(coordinate_span)', 'unit': '(s)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': True},
    'chemical_discrepancy_variance': {'formula': 'gradient(chemical_discrepancy)^T*C*gradient(chemical_discrepancy)', 'unit': '(uM_reaction_equivalents)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': True},
    'chemical_ratio_variance': {'formula': 'gradient(chemical_ratio)^T*C*gradient(chemical_ratio)', 'unit': '(dimensionless)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': True},
    'fate_fraction_variance': {'formula': 'gradient(fate_fraction)^T*C*gradient(fate_fraction)', 'unit': '(dimensionless)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end'], 'population': 'source', 'covariance_required': True},
    'source_interval_average_substrate_variance': {'formula': 'gradient(source_interval_average_substrate)^T*C*gradient(source_interval_average_substrate)', 'unit': '(uM/min)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['substrate_start', 'substrate_end', 'coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': True},
    'source_interval_average_total_product_variance': {'formula': 'gradient(source_interval_average_total_product)^T*C*gradient(source_interval_average_total_product)', 'unit': '(uM/min)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['total_product_start', 'total_product_end', 'coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': True},
    'source_interval_average_fate_product_variance': {'formula': 'gradient(source_interval_average_fate_product)^T*C*gradient(source_interval_average_fate_product)', 'unit': '(uM/min)^2', 'meaning': 'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.', 'operands': ['fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end'], 'population': 'source', 'covariance_required': True},
    'chemical_standardized_discrepancy': {'formula': 'chemical_discrepancy/sqrt(chemical_discrepancy_variance)', 'unit': 'dimensionless', 'meaning': 'Discrepancy relative to justified joint-estimate uncertainty; no p-value or probability.', 'operands': ['substrate_start', 'substrate_end', 'total_product_start', 'total_product_end'], 'population': 'source', 'covariance_required': True},
}
COMPONENTS = ('substrate_start', 'substrate_end', 'total_product_start', 'total_product_end', 'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end', 'substrate_loss', 'total_product_gain', 'fate_product_gain', 'coordinate_span', 'chemical_discrepancy', 'chemical_ratio', 'chemical_relative_discrepancy', 'fate_fraction', 'substrate_depletion_fraction', 'source_interval_average_substrate', 'scenario_interval_average_substrate', 'source_interval_average_total_product', 'scenario_interval_average_total_product', 'source_interval_average_fate_product', 'scenario_interval_average_fate_product', 'substrate_loss_variance', 'total_product_gain_variance', 'fate_product_gain_variance', 'coordinate_span_variance', 'chemical_discrepancy_variance', 'chemical_ratio_variance', 'fate_fraction_variance', 'source_interval_average_substrate_variance', 'source_interval_average_total_product_variance', 'source_interval_average_fate_product_variance', 'chemical_standardized_discrepancy')
VAR_BASES = ('substrate_loss','total_product_gain','fate_product_gain','coordinate_span',
    'chemical_discrepancy','chemical_ratio','fate_fraction','source_interval_average_substrate',
    'source_interval_average_total_product','source_interval_average_fate_product')


def concentration_window_sheet_schema(): return _schema('SHEET')


def _self_validate(inputs):
    _check(inputs,'CALCULATION_INPUTS')
    context=inputs['scientific_context']
    roster={(a['source_ref'],a['representation']):a for a in inputs['source_artifacts']}
    if len(roster)!=len(inputs['source_artifacts']):_fail('source_artifact_mismatch','source_artifacts')
    def fields(v):
        if isinstance(v,dict):
            if set(v)=={'status','scientific_text','display_status','binding','artifact_ref','source_sha256'}:
                if v['status']=='not_selected':
                    if any(v[k] is not None for k in ('scientific_text','binding','artifact_ref','source_sha256')) or v['display_status']!='not_selected':
                        _fail('concentration_window_saved_arithmetic_mismatch','scientific_context')
                else:
                    b=v['binding'];a=None if b is None else roster.get((b['source_ref'],b['representation']))
                    if a is None or a['artifact_ref']!=v['artifact_ref'] or a['sha256']!=v['source_sha256']:
                        _fail('source_artifact_mismatch','scientific_context')
                    if v['display_status']=='support_location_only' and v['scientific_text'] is not None:
                        _fail('concentration_window_saved_arithmetic_mismatch','scientific_context')
            else:
                for child in v.values():fields(child)
        elif isinstance(v,list):
            for child in v:fields(child)
    fields(context)
    for role,row in inputs['quantities'].items():
        if (row is None)!=(context['quantities'][role]['selection_status']=='not_selected'):
            _fail('concentration_window_saved_arithmetic_mismatch',role)
        if row is None:continue
        if row['role']!=role:_fail('concentration_window_saved_arithmetic_mismatch',role)
        if row['exact_value'] is not None and _float(_q(row['exact_value']))!=row['value']:
            _fail('concentration_window_saved_arithmetic_mismatch',role)
        if row['status']=='point' and (row['value'] is None or row['exact_value'] is None or row['relation']!='eq'):
            _fail('concentration_window_saved_arithmetic_mismatch',role)
        if row['value'] is not None and not math.isfinite(row['value']):_fail('numerical_model_range',role)
    for a,c in inputs['coefficients'].items():
        model=context['stoichiometry'][a]
        if any(model[k]!=c[k] for k in ('value','exact_value','origin','dependency_keys','reasons')):
            _fail('concentration_window_saved_arithmetic_mismatch','stoichiometry.'+a)
        if c['exact_value'] is not None and _float(_q(c['exact_value']))!=c['value']:
            _fail('concentration_window_saved_arithmetic_mismatch','stoichiometry.'+a)
        if model['operand_roles']!=[a+'_start',a+'_end']:
            _fail('concentration_window_saved_arithmetic_mismatch','stoichiometry.'+a)
    _validate_covariance(inputs['covariance'],inputs['quantities'])
    cov_context=inputs['covariance_context'];block=inputs['covariance']
    if cov_context['material']!=inputs['covariance_material']:
        _fail('concentration_window_saved_arithmetic_mismatch','covariance_context')
    if cov_context['selection_status']=='not_selected':
        if cov_context['material']!='not_selected' or any(cov_context[k] is not None for k in (
                'source_ref','artifact_ref','sha256','basis','variance_status','origin','derivation','systematic_coverage')) or any(
                cov_context[k] for k in ('roles','owner_keys','units','dependency_keys')):
            _fail('concentration_window_saved_arithmetic_mismatch','covariance_context')
    else:
        artifact=roster.get((cov_context['source_ref'],'original'))
        if artifact is None or artifact['artifact_ref']!=cov_context['artifact_ref'] or artifact['sha256']!=cov_context['sha256']:
            _fail('source_artifact_mismatch','covariance_context')
    if block is not None:
        for k in ('roles','owner_keys','units','dependency_keys','basis','variance_status','origin','derivation','systematic_coverage'):
            if cov_context[k]!=block['document'][k]:_fail('concentration_window_saved_arithmetic_mismatch','covariance_context.'+k)
        if any(cov_context[k]!=block[k] for k in ('source_ref','artifact_ref','sha256')):
            _fail('source_artifact_mismatch','covariance_context')
    elif any(cov_context[k] is not None for k in ('basis','variance_status','origin','derivation','systematic_coverage')) or any(
            cov_context[k] for k in ('roles','owner_keys','units','dependency_keys')):
        _fail('concentration_window_saved_arithmetic_mismatch','covariance_context')


def _operand_reason(role,inputs):
    row=inputs['quantities'][role];why=_reasons()
    if row is None:why['selection'].append('operand_not_selected');return why
    why=_merge(row['reasons'])
    if row['status']=='bounded':why['implementation'].append('bounded_arithmetic_unimplemented')
    if row['approximate']:why['implementation'].append('approximate_arithmetic_unimplemented')
    meaning=inputs['scientific_context']['quantities'][role]
    if meaning['reading_meaning']['value'] in ('unknown','conflicting'):
        why['relationship'].append('endpoint_assignment_'+meaning['reading_meaning']['value'])
    if meaning['unit_association']['value'] in ('unknown','conflicting'):
        why['relationship'].append('normalization_mapping_unresolved')
    if not role.startswith('coordinate') and meaning['concentration_basis']['value']!='native_reaction_concentration':
        why['relationship'].append('normalization_mapping_unresolved')
    return _merge(why)


def _pair_reason(name,inputs):
    p=inputs['scientific_context']['pair_relationships'][name];why=_reasons()
    value=p['endpoint_comparability']['value']
    if value not in ('same_series_supported','separately_measured_compatible'):
        why['relationship'].append('pair_endpoint_comparability_'+value)
    for field in ('selected_window','concentration_basis'):
        value=p[field]['value']
        if value!='supported':why['relationship'].append('pair_'+field+'_'+value)
    rows=[inputs['quantities'][name+'_'+s] for s in ('start','end')]
    if all(rows) and (rows[0]['owner_key']==rows[1]['owner_key'] or
        rows[0]['physical_owner_key'] is not None and rows[0]['physical_owner_key']==rows[1]['physical_owner_key']):
        why['relationship'].append('reused_physical_operand')
    return why


def _cross_reason(name,inputs):
    p=inputs['scientific_context']['cross_relationships'][name];why=_reasons()
    for f in ('window_compatibility','concentration_basis','calibration_compatibility'):
        value=p[f]['value']
        if value!='supported':why['relationship'].append('cross_'+f+'_'+value)
    value=p['endpoint_account']['value']
    if value not in ('same_reaction_account_supported','compatible_separate_accounts_supported'):
        why['relationship'].append('cross_endpoint_account_'+value)
    return why


def _blocked(why): return any(why.values())
def _add(a,b):return a[0]+b[0],tuple(x+y for x,y in zip(a[1],b[1]))
def _scale(a,k):return a[0]*k,tuple(x*k for x in a[1])
def _divide(a,b):return a[0]/b[0],tuple(x/b[0]-a[0]*y/(b[0]**2) for x,y in zip(a[1],b[1]))
def _constant(x):return Fraction(x),(Fraction(0),)*8


def _covariance_for(inputs,gradient):
    why=_reasons();block=inputs['covariance']
    if inputs['covariance_material']=='unsupported_observation_table':
        why['implementation'].append('covariance_estimation_from_table_unimplemented');return None,why
    if block is None:why['selection'].append('covariance_not_selected');return None,why
    if block['document']['variance_status']=='unknown':why['source'].append('joint_covariance_unknown');return None,why
    required={r for r,g in zip(ROLES,gradient) if g}
    if not required<=set(block['document']['roles']):why['source'].append('joint_covariance_incomplete');return None,why
    matrix=[[_q(x) for x in row] for row in block['matrix_exact']]
    roles=block['document']['roles'];g=[gradient[ROLES.index(r)] for r in roles]
    return sum(g[i]*matrix[i][j]*g[j] for i in range(len(roles)) for j in range(len(roles))),why


def populate_concentration_window(inputs):
    """Populate only selected cells, retaining meanings and independent partials.

    An external authoritative predecessor is checked by the separate validator.
    Internal operations never acquire sources, choose actions or earn observations.
    """
    _self_validate(inputs)
    rows=inputs['quantities'];context=inputs['scientific_context'];estimates={};reasons={};scope={}
    for i,r in enumerate(ROLES):
        row=rows[r]
        estimates[r]=(_q(row['exact_value']),tuple(Fraction(int(j==i)) for j in range(8))) if row and row['exact_value'] is not None else None
        reasons[r]=_operand_reason(r,inputs)
        scope[r]='native_observation'
    bases=dict(substrate='substrate_loss',total_product='total_product_gain',fate_product='fate_product_gain')
    for a,name in bases.items():
        start,end=a+'_start',a+'_end'
        why=_merge(reasons[start],reasons[end],_pair_reason(a,inputs));reasons[name]=why
        estimates[name]=None if _blocked(why) else _add(estimates[start],_scale(estimates[end],-1)) if a=='substrate' else _add(estimates[end],_scale(estimates[start],-1))
        scope[name]='physical_window_change' if context['pair_relationships'][a]['physical_pairing']['value'] in ('same_reaction_supported','paired_reactions_supported') else 'descriptive_change'
    reasons['coordinate_span']=_merge(reasons['coordinate_start'],reasons['coordinate_end'])
    estimates['coordinate_span']=None if _blocked(reasons['coordinate_span']) else _add(estimates['coordinate_end'],_scale(estimates['coordinate_start'],-1))
    scope['coordinate_span']='descriptive_change'
    coefficient={a:_q(c['exact_value']) if c['exact_value'] else None for a,c in inputs['coefficients'].items()}
    model_reason={a:_merge(inputs['coefficients'][a]['reasons']) for a in ANALYTES}
    for a in ANALYTES:
        if coefficient[a] is not None and coefficient[a]<=0:model_reason[a]['domain'].append('positive_coefficient_required')
    for name,cross,pairs in (('chemical_discrepancy','chemical',('substrate','total_product')),
            ('chemical_ratio','chemical',('substrate','total_product')),('fate_fraction','fate',('fate_product','total_product'))):
        a,b=pairs;why=_merge(reasons[bases[a]],reasons[bases[b]],model_reason[a],model_reason[b],_cross_reason(cross,inputs))
        value=None
        if not _blocked(why):
            first=_scale(estimates[bases[a]],1/coefficient[a]);second=_scale(estimates[bases[b]],1/coefficient[b])
            if name=='chemical_discrepancy':value=_add(first,_scale(second,-1))
            elif second[0]==0:why['domain'].append('zero_denominator')
            else:value=_divide(first,second)
        estimates[name]=value;reasons[name]=why
        links=context['cross_relationships'][cross]
        physical=links['endpoint_account']['value']=='same_reaction_account_supported' and links['physical_pairing']['value']=='same_reaction_supported' and all(scope[bases[p]]=='physical_window_change' for p in pairs)
        scope[name]='physical_reaction_account' if physical else 'descriptive_cross_readout_comparison'
    estimates['chemical_relative_discrepancy']=None if estimates['chemical_ratio'] is None else _add(estimates['chemical_ratio'],_constant(-1))
    reasons['chemical_relative_discrepancy']=_merge(reasons['chemical_ratio']);scope['chemical_relative_discrepancy']=scope['chemical_ratio']
    why=_merge(reasons['substrate_loss'],reasons['substrate_start']);value=None
    if not _blocked(why):
        if estimates['substrate_start'][0]==0:why['domain'].append('zero_denominator')
        else:value=_divide(estimates['substrate_loss'],estimates['substrate_start'])
    estimates['substrate_depletion_fraction']=value;reasons['substrate_depletion_fraction']=why;scope['substrate_depletion_fraction']=scope['substrate_loss']
    conditional={};timing=context['timing']['source_meaning']['value']
    for a,base in bases.items():
        for prefix in ('source','scenario'):
            name=prefix+'_interval_average_'+a;why=_merge(reasons[base],reasons['coordinate_span']);value=None
            span=estimates['coordinate_span']
            if span is not None and span[0]<=0:why['domain'].append('positive_time_span_required')
            if prefix=='source':
                if timing=='unknown':why['source'].append('timing_meaning_unknown')
                elif timing!='actual_sampling_time':why['relationship'].append('timing_meaning_conflicting' if timing=='conflicting' else 'timing_meaning_not_elapsed')
            else:
                if context['timing']['scenario'] is None:why['selection'].append('timing_scenario_not_selected')
                if timing!='unknown':why['relationship'].append('timing_meaning_conflicting' if timing=='conflicting' else 'timing_meaning_not_elapsed')
            if not _blocked(why):value=_scale(_divide(estimates[base],span),60)
            estimates[name]=value;reasons[name]=why;scope[name]='conditional_timing_sensitivity' if prefix=='scenario' else scope[base]
            conditional[name]=prefix=='scenario'
    variance={};variance_reason={};variance_method={}
    for base in VAR_BASES:
        why=_merge(reasons[base]);value=None
        if not _blocked(why):
            value,more=_covariance_for(inputs,estimates[base][1]);why=_merge(why,more)
        else:
            _,more=_covariance_for(inputs,(Fraction(0),)*8);why=_merge(why,more)
        variance[base]=value;variance_reason[base]=why
        variance_method[base]='exact_linear_covariance' if base in ('substrate_loss','total_product_gain','fate_product_gain','coordinate_span','chemical_discrepancy') else 'first_order_covariance'
    name='chemical_standardized_discrepancy';why=_merge(variance_reason['chemical_discrepancy']);standard=None;standard_exact=None
    v=variance['chemical_discrepancy']
    if not _blocked(why):
        if v is None or v<=0:why['domain'].append('positive_variance_required')
        else:
            numerator=math.isqrt(v.numerator);denominator=math.isqrt(v.denominator)
            if numerator*numerator==v.numerator and denominator*denominator==v.denominator:
                standard_exact=estimates['chemical_discrepancy'][0]/Fraction(numerator,denominator);standard=_float(standard_exact)
            else:
                vf=_float(v);df=_float(estimates['chemical_discrepancy'][0])
                if vf is not None and df is not None:standard=df/math.sqrt(vf)
            if standard is None or not math.isfinite(standard):why['domain'].append('numerical_model_range');standard=None;standard_exact=None
    reasons[name]=why
    contribution='contribution:'+_digest(dict(selection_digest=inputs['selection_digest'],source_artifacts=inputs['source_artifacts']))
    cells=[]
    for name in inputs['requested_cells']:
        definition=_DEFINITIONS[name];roles=definition['operands'];deps=list(dict.fromkeys(k for r in roles if rows[r] for k in rows[r]['dependency_keys']))
        model_names=() if not (name.startswith('chemical_') or name.startswith('fate_fraction')) else ('substrate','total_product') if name.startswith('chemical_') else ('fate_product','total_product')
        deps=list(dict.fromkeys([*deps,*(k for a in model_names for k in inputs['coefficients'][a]['dependency_keys'])]))
        native=name in ROLES;is_variance=name.endswith('_variance');base=name.removesuffix('_variance')
        value=None;exact_value=None;conditional_value=None;conditional_exact=None;method='not_applicable';interpretation=scope.get(name,'uncertainty_of_declared_estimates')
        if native:
            row=rows[name];why=_reasons() if row is not None and row['status']=='point' else _operand_reason(name,inputs)
            if row and row['status']=='point':value=row['value'];exact_value=deepcopy(row['exact_value'])
        elif is_variance:
            why=_merge(variance_reason[base]);q=variance[base];method=variance_method[base] if q is not None else 'not_available'
            if q is not None:
                value=_float(q);exact_value=_exact(q)
                if value is None:why['domain'].append('numerical_model_range')
        elif name=='chemical_standardized_discrepancy':
            why=_merge(reasons[name]);value=standard;exact_value=_exact(standard_exact) if standard_exact is not None else None;method='exact_linear_covariance' if standard is not None else 'not_available'
        else:
            why=_merge(reasons[name]);estimate=estimates[name]
            if estimate is not None:
                converted=_float(estimate[0])
                if converted is None:why['domain'].append('numerical_model_range')
                elif conditional.get(name):conditional_value=converted;conditional_exact=_exact(estimate[0])
                else:value=converted;exact_value=_exact(estimate[0])
        if value is None and conditional_value is None:status='unavailable';interpretation='unavailable'
        else:status='conditional_scenario' if conditional_value is not None else 'populated'
        if value is None:exact_value=None
        approximate=any(rows[r] and rows[r]['approximate'] for r in roles)
        row=rows[name] if native else None
        origin=row['origin'] if row else 'synthetic' if inputs['source_kind']=='synthetic_fixture' else 'calculated'
        if is_variance or name=='chemical_standardized_discrepancy':
            if inputs['covariance'] and inputs['covariance']['document']['origin']=='synthetic':origin='synthetic'
        cells.append(dict(component=name,value=value,exact_value=exact_value,conditional_value=conditional_value,
            conditional_exact_value=conditional_exact,status=status,unit=definition['unit'],formula=definition['formula'],meaning=definition['meaning'],
            origin=origin,operand_roles=list(roles),dependency_keys=deps,contribution_key=contribution,approximate=approximate,
            bound=row['relation'] if row and row['relation'] in ('lt','le','gt','ge') else 'none',
            threshold=row['value'] if row and row['status'] in ('bounded','nondetection') else None,
            outside_physical_fraction_range=bool(name in ('fate_fraction','substrate_depletion_fraction') and value is not None and not 0<=value<=1),
            negative_observed_change=bool(name in bases.values() and value is not None and value<0),
            timing_stipulation='coordinates_are_elapsed_sampling_times' if conditional_value is not None else None,
            uncertainty_method=method,reasons=_merge(why),interpretation_scope=interpretation))
    selected=[b for b in VAR_BASES if b+'_variance' in inputs['requested_cells'] and variance[b] is not None]
    derived=None
    if selected:
        block=inputs['covariance'];doc=block['document'];order=doc['roles'];C=[[_q(x) for x in row] for row in block['matrix_exact']]
        G=[[estimates[b][1][ROLES.index(r)] for r in order] for b in selected]
        matrix=[[sum(G[i][a]*C[a][b]*G[j][b] for a in range(len(order)) for b in range(len(order))) for j in range(len(selected))] for i in range(len(selected))]
        display=[[_float(x) for x in row] for row in matrix]
        if all(x is not None for row in display for x in row):derived=dict(components=selected,matrix=display,method='G*C*G_transpose',covariance_source_ref=block['source_ref'])
    result=dict(version='a105_concentration_window_sheet_v3',axis='A105',section='observed_concentration_window',
        cells=cells,assertion_resolution='total_chemical_extent_and_selected_product_fate',scientific_context=deepcopy(context),
        association=dict(selection_digest=inputs['selection_digest'],extraction_digest=inputs['extraction_digest'],calculation_inputs_digest=_digest(inputs)),
        source_artifacts=deepcopy(inputs['source_artifacts']),estimate_bindings=[{k:deepcopy(rows[r][k]) for k in ('role','owner_key','physical_owner_key','dependency_keys')} for r in ROLES if rows[r]],
        covariance_context=deepcopy(inputs['covariance_context']),
        derived_covariance=derived,limits=['observed_source_scale_not_blank_corrected','no_unique_molecular_attribution',
            'unknown_calibration_systematics','no_independent_replication_inferred','shared_derived_contribution',
            'interval_average_not_initial_or_turnover_rate','no_cumulative_amount_from_initial_volume',
            'selected_integration_unimplemented','general_reliability_compilation_unfinished','no_target_transfer_or_W05'],annotation_credit=None)
    _check(result,'SHEET');return result


def validate_concentration_window_sheet(sheet,*,inputs):
    _check(sheet,'SHEET');_same(sheet,populate_concentration_window(inputs),'sheet');return sheet
