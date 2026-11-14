"""Ion discrimination from source activities or separately reported limits.

Estimator arithmetic, reported domains, nominal threshold arithmetic and
conditional physical bounds are different outputs. No reliability probability,
GHK inversion, target transfer, final credit or source acquisition is performed.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from .domain import validate_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_ion_discrimination_inputs import (VERSION as INPUT_VERSION, ROLES, ion_discrimination_sheet_schema,
    validate_ion_discrimination_extraction,canonical_activity_owner)
from .literature_ion_discrimination_numbers import fraction, rational

VERSION='a105_ion_discrimination_sheet_v1'
FORMULAS={'preferred_activity':'selected_preferred_activity_or_limit','alternative_activity':'selected_alternative_activity_or_limit',
 'activity_ratio':'preferred_activity/alternative_activity','log_activity_ratio':'ln(activity_ratio)',
 'activity_ratio_variance':'J_R*C*J_R_transpose','activity_ratio_standard_uncertainty':'sqrt(activity_ratio_variance)',
 'log_activity_ratio_variance':'J_log*C*J_log_transpose','log_activity_ratio_standard_uncertainty':'sqrt(log_activity_ratio_variance)',
 'reported_selectivity':'selected_original_reported_selectivity','nominal_threshold_ratio':'preferred_threshold/alternative_threshold'}
COMPONENTS=tuple(FORMULAS)
MEANINGS={'preferred_activity':'native_selected_activity_or_limit','alternative_activity':'native_selected_activity_or_limit',
 'activity_ratio':'ion_specific_rate_ratio','log_activity_ratio':'log_ion_specific_rate_ratio',
 'activity_ratio_variance':'first_order_ratio_variance','activity_ratio_standard_uncertainty':'first_order_ratio_standard_uncertainty',
 'log_activity_ratio_variance':'first_order_log_ratio_variance','log_activity_ratio_standard_uncertainty':'first_order_log_ratio_standard_uncertainty',
 'reported_selectivity':'source_reported_selectivity_limit','nominal_threshold_ratio':'nominal_reported_threshold_division'}


def _float(q):
    if q is None:return None
    try:
        v=float(q)
        return v if math.isfinite(v) and (v!=0 or q==0) else None
    except (OverflowError,ValueError):return None


def _domain(lo,hi,lc,uc,meaning):
    return {'meaning':meaning,'lower':_float(lo),'upper':_float(hi),'lower_inclusive':lc if lo is not None else None,
        'upper_inclusive':uc if hi is not None else None,'lower_unbounded':lo is None,'upper_unbounded':hi is None,
        'lower_exact':None if lo is None else rational(lo),'upper_exact':None if hi is None else rational(hi)}


def _point(x,meaning='derived_estimator_domain'):
    return _domain(x,x,True,True,meaning)


def _cell(name,*,value=None,threshold=None,unit=None,status='unavailable',origin='derived',reason='route_not_applicable',
          deps=(),approx='not_explicitly_qualified',kind='unknown',applicability='unresolved',limits=()):
    return {'component':name,'value':_float(value),'threshold':_float(threshold),
        'unit':unit if name in ('preferred_activity','alternative_activity') else 'dimensionless_squared' if name.endswith('_variance') else 'dimensionless',
        'status':status,'origin':origin,'meaning':MEANINGS[name],'formula_code':FORMULAS[name],
        'reported_domain':None,'estimator_domain':None,'nominal_domain':None,'physical_domain':None,
        'relation':'point' if value is not None else 'none','approximation':approx,'quantity_kind':kind,
        'scientific_applicability':applicability,'unavailable_reasons':[] if reason is None else [reason],
        'limitations':list(limits),'dependencies':deepcopy(list(deps)),'variance_status':'unknown','zero_denominator_case':'not_applicable','derivation':'not_applicable','source_qualifications':[],'annotation_credit':None}


def _dependency(operand,role,source_ref):
    if operand['kind']=='compiled_activity':
        row=operand['row'];physical=[];opaque=[]
        for dep in row['dependencies']:
            physical.extend(dep['canonical_physical_keys']);opaque.extend(dep['recorded_dependency_keys'])
        return {'role':role,'source_ref':row['evidence_source_ref'],'component_ref':row['sheet_ref'],
            'namespace':'literature_compiled_assay_cells','component':'corrected_activity',
            'physical_keys':list(dict.fromkeys(physical)),'opaque_dependency_keys':list(dict.fromkeys(opaque)),
            'physical_identity_status':'partly_canonical' if physical else 'cross_component_identity_unknown','origin':row['origin']}
    n=operand['number']
    return {'role':role,'source_ref':source_ref,'component_ref':None,'namespace':None,'component':None,
        'physical_keys':[] if n is None else [n['measurement_key']],'opaque_dependency_keys':[],
        'physical_identity_status':'source_numeric_span' if n else 'cross_component_identity_unknown','origin':operand['origin']}


def _comparison_reasons(e):
    r={k:v['value'] for k,v in e['relationships'].items()};reasons=[]
    if r['intended_ions']!='different_ions':reasons.append('intended_ions_not_distinct')
    if r['subject_construct']!='same_construct':reasons.append('different_subject_construct' if r['subject_construct']=='different_construct' else 'subject_construct_unresolved')
    if r['quantity']!='same_ion_specific_rate_kind':reasons.append('different_physical_quantities' if r['quantity']=='different_physical_quantity' else 'quantity_relation_unresolved')
    if r['normalization'] not in ('same_molecular_basis','common_unresolved_molecular_unit'):
        reasons.append('different_molecular_basis' if r['normalization']=='different_molecular_basis' else 'normalization_unresolved')
    if r['nonintended_conditions']=='source_supported_adjustment':
        reasons.extend(e['adjustment_reasons'])
        if e['route']!='compiled_activity_pair':reasons.append('adjustment_binding_required')
    elif r['nonintended_conditions']!='matched' or e['nonintended_differences']:
        reasons.append('nonintended_conditions_different' if r['nonintended_conditions']=='different' else 'nonintended_conditions_unresolved')
    if any(r[x]!='intended_protein_and_ion_supported' for x in ('preferred_ion_attribution','alternative_ion_attribution')):
        reasons.append('ion_attribution_unresolved')
    return list(dict.fromkeys(reasons))


def _reported_domain(n,meaning='reported_estimate_domain',*,scale=Fraction(1),nonnegative=False):
    x=fraction(n['exact'])*scale;relation=n['relation']
    if relation=='point':return _point(x,meaning)
    if relation in ('gt','ge','lower_limit'):
        return _domain(x,None,None if relation=='lower_limit' else relation=='ge',None,meaning)
    lo=Fraction(0) if nonnegative else None
    return _domain(lo,x,True if nonnegative else None,None if relation=='upper_limit' else relation=='le',meaning)


def _physical_reasons(q):
    m={k:v['value'] for k,v in q['interpretations'].items()};reasons=[]
    if m['quantity_scope']!='specific_construct':reasons.append('subject_construct_unresolved')
    if m['domain_bearer']!='physical_parameter' or m['physical_domain_support']!='explicit_nonnegative_parameter_limit_supported':
        reasons.append('physical_domain_support_missing')
    if m['derivation']!='source_parameter_bound_derivation_supported':reasons.append('physical_parameter_model_unimplemented')
    if q['approximation']!='not_explicitly_qualified':reasons.append('approximation_model_missing')
    if q['number'] is not None and q['number'].get('adjacent_uncertainty_uninterpreted'):reasons.append('reported_uncertainty_reading_unimplemented')
    if m['meaning'] not in ('per_unit_ion_efflux_rate','reported_transport_selectivity_ratio'):
        reasons.append('reported_estimate_not_physical_bound')
    if q['number'] is None or fraction(q['number']['exact'])<0:reasons.append('signed_estimator_not_physical_rate')
    if q['number'] is not None and q['number']['relation']=='lt' and fraction(q['number']['exact'])==0:reasons.append('physical_domain_inconsistent')
    return list(dict.fromkeys(reasons))


def _native_reported(name,q,e,role):
    deps=[_dependency(q,role,e['source_ref'])];n=q['number'];m=q['interpretations'];ratio=m['meaning']['value'].startswith('reported_')
    unit=q['unit']['unit'] if q['unit'] else 'dimensionless' if ratio else None
    origin=q['origin']
    why=q['reasons'][0] if q['reasons'] else None
    if name=='reported_selectivity' and not ratio:
        wrong=_cell(name,reason='source_quantity_meaning_unknown' if m['meaning']['value'] in ('unknown','conflicting') else 'different_physical_quantities',deps=deps,origin=origin,approx=q['approximation'],kind=m['meaning']['value'])
        wrong['derivation']=m['derivation']['value'];wrong['source_qualifications']=deepcopy(q['source_qualifications'])
        return wrong
    c=_cell(name,unit=unit,reason=why or ('source_number_not_selected' if n is None else None),deps=deps,
        approx=q['approximation'],kind=m['meaning']['value'],origin=origin,
        applicability='conditional_source_report',limits=('no_annotation_credit','reported_and_calculated_not_separate_experiments'))
    c['derivation']=m['derivation']['value'];c['source_qualifications']=deepcopy(q['source_qualifications'])
    if n is not None:
        c['value']=n['value'] if n['relation']=='point' else None;c['threshold']=None if n['relation']=='point' else n['value']
        c['relation']=n['relation'];c['reported_domain']=_reported_domain(n)
        c['status']='populated' if n['relation']=='point' else 'bounded'
        if why:c['unavailable_reasons']=list(q['reasons'])
        pwhy=_physical_reasons(q)+_comparison_reasons(e)
        if not pwhy and not why:c['physical_domain']=_reported_domain(n,'conditional_physical_parameter_domain',nonnegative=True)
        else:c['unavailable_reasons']=list(dict.fromkeys([*c['unavailable_reasons'],*pwhy]))
    return c


def _sqrt(x):
    with localcontext() as c:
        c.prec=80
        return (Decimal(x.numerator)/Decimal(x.denominator)).sqrt()


def _compiled(e,cells):
    reasons=_comparison_reasons(e);ops=e['operands'];deps=[_dependency(ops[r],r,e['source_ref']) for r in ROLES]
    values=[]
    for role,name in zip(ROLES,('preferred_activity','alternative_activity')):
        row=ops[role]['row'];v=row['value'];why=None
        if (row['status']!='populated' or v is None or row['formula_code']!='corrected_activity_compiled_v1'
                or row['formula'] not in ('(q-g)*v/(k*E*u)','source_already_corrected_amount_normalized_value')):why='selected_activity_unavailable'
        elif row['unit']!='per_min':why='different_physical_quantities'
        if row['endpoint_kind']!='transport_flux':reasons.append('endpoint_not_transport_flux')
        if why:reasons.append(why)
        c=_cell(name,value=v if why is None else None,unit=row['unit'],status='populated' if why is None else 'unavailable',
            reason=why,origin=row['origin'],deps=[deps[ROLES.index(role)]],kind='ion_specific_rate',applicability='estimator_comparison_only')
        if v is not None:c['estimator_domain']=_point(Fraction(str(v)))
        c['derivation']='selected_compiled_activity'
        cells[name]=c;values.append(None if why else Fraction(str(v)))
    aliases=[canonical_activity_owner(ops[r]['row']) for r in ROLES]
    if ops['preferred']['activity_key']==ops['alternative']['activity_key'] or aliases[0] is not None and aliases[0]==aliases[1]:
        reasons.append('shared_activity_estimator_inconsistent' if values[0]!=values[1] else 'reused_activity_not_ion_discrimination')
    if e['selection']['source_kind']!='synthetic_fixture' and any(ops[r]['row']['origin']=='synthetic' for r in ROLES):
        reasons.append('synthetic_activity_for_nonsynthetic_selection')
    bases=[ops[r]['row']['operand_meanings']['E'] for r in ROLES]
    if set(bases)=={'same_assay_active_molecules','same_assay_total_molecules'}:reasons.append('different_molecular_basis')
    origins={ops[r]['row']['origin'] for r in ROLES}
    derived_origin='synthetic' if 'synthetic' in origins or e['selection']['source_kind']=='synthetic_fixture' else 'graph_derived' if 'graph_derived' in origins else 'derived'
    A,B=values;reason=next(iter(dict.fromkeys(reasons)),None)
    if reason is None and B==0:reason='zero_denominator_estimator';reasons.append(reason)
    R=None if reason else A/B
    signed=R is not None and (A<0 or B<0)
    app='estimator_comparison_only' if signed else 'supported_for_selected_comparison'
    rc=_cell('activity_ratio',value=R,reason=reason,status='populated' if R is not None else 'unavailable',deps=deps,
        kind='source_activity_estimator_ratio',applicability=app if R is not None else 'unresolved',limits=('no_annotation_credit','no_independence_from_distinct_refs'))
    if R is not None:
        rc['estimator_domain']=_point(R)
        if signed:rc['meaning']='signed_activity_estimator_ratio'
    zero_case='unknown' if B is None else 'selected_estimator_is_zero' if B==0 else 'selected_estimator_nonzero'
    if R is None and reasons:rc['unavailable_reasons']=list(dict.fromkeys(reasons))
    rc['origin']=derived_origin;rc['derivation']='derived_activity_ratio'
    rc['zero_denominator_case']=zero_case
    cells['activity_ratio']=rc
    L=math.log(float(R)) if R is not None and R>0 and _float(R) is not None else None
    lr=reason or ('ratio_not_positive' if R is not None and R<=0 else 'numerical_model_range' if R is not None and L is None else None)
    cells['log_activity_ratio']=_cell('log_activity_ratio',value=L,reason=lr,status='populated' if L is not None else 'unavailable',deps=deps,
        kind=rc['quantity_kind'],applicability=app if L is not None else 'unresolved',limits=rc['limitations'])
    if R is None and reasons:cells['log_activity_ratio']['unavailable_reasons']=list(dict.fromkeys(reasons))
    cells['log_activity_ratio']['origin']=derived_origin;cells['log_activity_ratio']['derivation']='derived_activity_ratio'
    cells['log_activity_ratio']['zero_denominator_case']=zero_case
    if L is not None:cells['log_activity_ratio']['estimator_domain']=_point(Fraction(str(L)))
    cov=e['covariance'];var_reason=reason
    if var_reason is None and cov['status']!='valid':var_reason='covariance_not_selected' if cov['status']=='not_selected' else cov['status']
    if var_reason is None and cov['data']['variance_status']=='unknown':var_reason='covariance_status_unknown'
    for prefix,gradient,base_reason in (
        ('activity_ratio',(Fraction(1)/B,-A/(B*B)) if R is not None else None,var_reason),
        ('log_activity_ratio',(Fraction(1)/A,-Fraction(1)/B) if R is not None and R>0 else None,lr or var_reason)):
        variance=None
        if base_reason is None and gradient is not None:
            C=[[Fraction(str(v)) for v in row] for row in cov['data']['matrix']]
            variance=sum(gradient[i]*C[i][j]*gradient[j] for i in range(2) for j in range(2))
        for suffix,value in (('variance',variance),('standard_uncertainty',None if variance is None else _sqrt(variance))):
            name=prefix+'_'+suffix
            cell=_cell(name,value=value,reason=base_reason,status='populated' if value is not None else 'unavailable',deps=deps,
                kind=rc['quantity_kind'],applicability=app if value is not None else 'unresolved',limits=('first_order_joint_covariance','no_reliability_probability'))
            if value is not None:cell['variance_status']=cov['data']['variance_status'];cell['estimator_domain']=_point(Fraction(str(value)))
            if R is None and reasons:cell['unavailable_reasons']=list(dict.fromkeys(reasons))
            cell['origin']=derived_origin;cell['derivation']='first_order_activity_covariance'
            cell['zero_denominator_case']=zero_case
            cells[name]=cell


def _positive_ratio_domain(a,b,meaning):
    # This is set arithmetic on a stated B>0 branch, never a confidence interval.
    loA=None if a['lower_exact'] is None else fraction(a['lower_exact']);hiA=None if a['upper_exact'] is None else fraction(a['upper_exact'])
    loB=None if b['lower_exact'] is None else fraction(b['lower_exact']);hiB=None if b['upper_exact'] is None else fraction(b['upper_exact'])
    if loA is None or loA<0 or hiB is not None and hiB<=0 or loB is not None and loB<0:return None
    if loA==hiA==0:return _point(Fraction(0),meaning)
    lower=Fraction(0) if hiB is None else loA/hiB
    upper=None if hiA is None or loB is None or loB==0 else hiA/loB
    conjunction=lambda x,y: False if x is False or y is False else True if x is True and y is True else None
    lc=False if hiB is None else conjunction(a['lower_inclusive'],b['upper_inclusive'])
    if lower==0 and loA==0:lc=a['lower_inclusive']
    uc=None if upper is None else conjunction(a['upper_inclusive'],b['lower_inclusive'])
    return _domain(lower,upper,lc,uc,meaning)


def _thresholds(e,cells):
    qs=e['operands'];deps=[_dependency(qs[r],r,e['source_ref']) for r in ROLES]
    for r,name in zip(ROLES,('preferred_activity','alternative_activity')):cells[name]=_native_reported(name,qs[r],e,r)
    reason=next((x for r in ROLES for x in qs[r]['reasons']),None)
    if reason is None and any(qs[r]['interpretations']['meaning']['value'] not in ('per_unit_ion_efflux_rate','author_inferred_per_unit_ion_efflux_rate') for r in ROLES):
        reason='different_physical_quantities'
    ns=[qs[r]['number'] for r in ROLES]
    if reason is None and any(n is None for n in ns):reason='source_number_not_selected'
    values=[None if n is None else fraction(n['exact']) for n in ns]
    scales=[fraction(qs[r]['unit']['canonical_rate_scale']) if qs[r]['unit'] else Fraction(1) for r in ROLES]
    if reason is None and values[1]==0:reason='zero_denominator_estimator'
    ratio=None if reason else values[0]*scales[0]/(values[1]*scales[1])
    c=_cell('nominal_threshold_ratio',threshold=ratio,reason=reason,status='conditional_arithmetic' if ratio is not None else 'unavailable',deps=deps,
        approx='source_qualified' if any(qs[r]['approximation']=='source_qualified' for r in ROLES) else 'unknown',
        kind='nominal_threshold_comparison',applicability='conditional_source_report',limits=('nominal_threshold_arithmetic_not_physical_bound','denominator_positive_condition','paper_summary_not_construct_specific'))
    if ratio is not None:
        domains=[_reported_domain(n,'nominal_threshold_arithmetic_domain',scale=s) for n,s in zip(ns,scales)]
        c['nominal_domain']=_positive_ratio_domain(*domains,'nominal_threshold_arithmetic_domain')
        if c['nominal_domain'] is not None and c['nominal_domain']['lower_exact']==c['nominal_domain']['upper_exact']==rational(ratio):
            c['value']=_float(ratio);c['threshold']=None;c['relation']='point'
        elif c['nominal_domain'] is not None and c['nominal_domain']['lower_exact']==rational(ratio):
            c['relation']='ge' if c['nominal_domain']['lower_inclusive'] else 'gt' if c['nominal_domain']['lower_inclusive'] is False else 'lower_limit'
        why=_comparison_reasons(e)+[x for r in ROLES for x in _physical_reasons(qs[r])]
        if ns[0]['measurement_key']==ns[1]['measurement_key']:why.append('reused_activity_not_ion_discrimination')
        if not why:
            physical=[_reported_domain(qs[r]['number'],'conditional_physical_parameter_domain',scale=scales[i],nonnegative=True) for i,r in enumerate(ROLES)]
            c['physical_domain']=_positive_ratio_domain(*physical,'conditional_physical_parameter_domain')
        c['unavailable_reasons']=list(dict.fromkeys(why))
    if e['selection']['source_kind']=='synthetic_fixture':c['origin']='synthetic'
    if ns[1] is None:c['zero_denominator_case']='unknown'
    elif ns[1]['relation']=='point':c['zero_denominator_case']='selected_estimator_is_zero' if values[1]==0 else 'selected_estimator_nonzero'
    else:
        d=_reported_domain(ns[1]);lo=d['lower'];hi=d['upper']
        excludes=(lo is not None and (lo>0 or lo==0 and d['lower_inclusive'] is False) or hi is not None and (hi<0 or hi==0 and d['upper_inclusive'] is False))
        c['zero_denominator_case']='excluded_by_selected_source_domain' if excludes else 'possible_in_source_domain'
    cells['nominal_threshold_ratio']=c


def populate_ion_discrimination(extraction):
    """Populate deterministic contributions from authenticated interpreted inputs."""
    e=validate_ion_discrimination_extraction(extraction)
    cells={name:_cell(name) for name in COMPONENTS}
    if e['route']=='compiled_activity_pair':_compiled(e,cells)
    elif e['route']=='reported_ratio':cells['reported_selectivity']=_native_reported('reported_selectivity',e['operands']['reported'],e,'reported')
    elif e['route']=='reported_threshold_pair':_thresholds(e,cells)
    else:raise ExperimentalContractError('ion_route_required','route')
    for cell in cells.values():
        if cell['status']=='populated' and cell['value'] is None:
            cell['status']='unavailable';cell['unavailable_reasons'].append('numerical_model_range')
    sheet={'version':VERSION,'axis':'A105','route':e['route'],'cells':cells,'overall_quality_grade':None,'annotation_credit':None}
    validate_schema(sheet,ion_discrimination_sheet_schema())
    return sheet


__all__=['VERSION','COMPONENTS','FORMULAS','MEANINGS','populate_ion_discrimination']
