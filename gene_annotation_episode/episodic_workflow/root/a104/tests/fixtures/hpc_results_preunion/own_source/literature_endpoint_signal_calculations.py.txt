"""Numerical A105 endpoint-contribution sheet; no source IO or final credit.

One shared native ordinate owns both numerator and denominator. Manual reading
bounds and optional joint uncertainty retain their separate meanings. Physical
covariance is never inferred from an enclosure or a supplied reading model.
"""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from itertools import product
import math

from .domain import identity, obj
from .literature_endpoint_signal_inputs import (
    ALL_COMPONENTS, POINT_ORDER, endpoint_signal_population_schema,
    endpoint_signal_extraction_schema, covariance_source_schema,
    validate_endpoint_signal_extraction, _exact_schema, _nullable, _array,
    _enum, _const, _TEXT, _exact, _fraction, _schema_check,
)

VERSION='a105_endpoint_signal_components_v1'
COMPONENTS=ALL_COMPONENTS
_BASE=COMPONENTS[:5]
FORMULAS=dict(zip(COMPONENTS,('s*(a-t)','s*(a-b)','s*(b-t)','(a-b)/(a-t)',
    '1-(a-b)/(a-t)','J_D*Sigma*J_D_transpose','J_C*Sigma*J_C_transpose',
    'J_G*Sigma*J_G_transpose','J_F*Sigma*J_F_transpose','J_H*Sigma*J_H_transpose')))
MEANINGS=dict(zip(COMPONENTS,(
    'Selected total reporter amplitude in direction-oriented native pixels.',
    'Reporter amplitude retained under the selected baseline correction model.',
    'Additional reporter amplitude under the selected baseline correction model.',
    'Corrected-to-total reporter amplitude ratio under the selected model.',
    'Additional-to-total reporter amplitude ratio under the selected model.',
    'First-order variance of the total amplitude in the supplied joint estimate model.',
    'First-order variance of the corrected amplitude in the supplied joint estimate model.',
    'First-order variance of the additional amplitude in the supplied joint estimate model.',
    'First-order variance of the retained fraction in the supplied joint estimate model.',
    'First-order variance of the additional fraction in the supplied joint estimate model.')))
REASONS=('source_unavailable','missing_initial','missing_baseline_at_addition','missing_late',
    'axis_scale_unestablished','ordinate_direction_unresolved','measurement_stage_not_endpoint',
    'correction_already_applied','correction_stage_unresolved','baseline_basis_unsupported',
    'baseline_applicability_unresolved','fast_component_completion_unresolved','zero_total_amplitude',
    'reading_enclosure_unreported','reading_denominator_contains_zero','covariance_unreported',
    'covariance_unavailable','covariance_status_unknown','covariance_basis_not_applicable','numerical_projection_range')
QUALIFICATIONS=('manual_reading_not_physical_measurement','reading_bounds_not_statistical_CI',
    'nonnegative_additive_model_incompatible','physical_covariance_unreported','synthetic_covariance_model',
    'not_molecular_attribution','first_order_covariance_propagation')
CONDITIONS=('common_affine_native_ordinate','selected_ordinate_direction','selected_finite_time_coordinate',
    'source_displayed_baseline','baseline_extrapolation_supported','baseline_extrapolation_stipulated',
    'fast_component_completion_supported','fast_component_completion_stipulated','uncorrected_source_trace',
    'same_trace_shared_initial_ordinate','joint_manual_reading_error_model','joint_physical_ordinate_estimate_model',
    'covariance_already_in_native_coordinate_units','known_covariance','estimated_covariance',
    'first_order_covariance_propagation','synthetic_uncertainty_scenario')

def endpoint_signal_cell_schema(component=None):
    if component is not None and component not in COMPONENTS: raise ValueError('unknown_endpoint_component')
    return obj({'component':_enum(COMPONENTS) if component is None else _const(component),
        'value':_nullable({'type':'number'}),'conditional_value':_nullable({'type':'number'}),
        'exact_value':_nullable(_exact_schema()),'conditional_exact_value':_nullable(_exact_schema()),
        'lower':_nullable({'type':'number'}),'upper':_nullable({'type':'number'}),
        'exact_lower':_nullable(_exact_schema()),'exact_upper':_nullable(_exact_schema()),
        'unit':_enum(('direction_oriented_pixel','dimensionless','pixel^2','dimensionless^2')),
        'status':_enum(('populated','conditional_scenario','unavailable')),
        'origin':_const('derived'),
        'input_origins':endpoint_signal_extraction_schema()['properties']['input_origins'],
        'formula':_enum(FORMULAS.values()) if component is None else _const(FORMULAS[component]),
        'meaning':_enum(MEANINGS.values()) if component is None else _const(MEANINGS[component]),
        'conditional_on':_array(_enum(CONDITIONS),uniqueItems=True),
        'unavailable_reasons':_array(_enum(REASONS),uniqueItems=True),
        'qualifications':_array(_enum(QUALIFICATIONS),uniqueItems=True),
        'bound_kind':_enum(('manual_reading_enclosure_not_confidence_interval','none')),
        'primitive_owners':_array(_nullable(_TEXT),minItems=3,maxItems=3),
        'contribution_key':deepcopy(_TEXT),
        'uncertainty_basis':_nullable(_enum(('joint_manual_reading_error','joint_physical_ordinate_estimates')))})

def endpoint_signal_sheet_schema():
    wire=covariance_source_schema()
    return obj({'version':_const(VERSION),'axis':_const('A105'),'section':_const('endpoint_signal_contribution'),
        'requested_cells':endpoint_signal_population_schema()['properties']['requested_cells'],
        'cells':_array(endpoint_signal_cell_schema(),uniqueItems=True),
        'input_snapshot':endpoint_signal_extraction_schema(),
        'joint_propagation':_nullable(obj({'basis':wire['properties']['basis'],'origin':wire['properties']['origin'],
            'primitive_order':_const(list(POINT_ORDER)),'primitive_owners':wire['properties']['primitive_owners'],
            'component_order':_const(list(_BASE)),
            'exact_covariance':_array(_array(_exact_schema(),minItems=5,maxItems=5),minItems=5,maxItems=5)}))})

def _project(q,direction=0):
    try: value=float(q)
    except (OverflowError,ValueError): return None
    if not math.isfinite(value) or value==0 and q!=0: return None
    if direction<0 and Fraction(value)>q: value=math.nextafter(value,-math.inf)
    if direction>0 and Fraction(value)<q: value=math.nextafter(value,math.inf)
    return value if math.isfinite(value) else None

def _relationship(data,name):
    record=data['relationships'][name]
    return record['interpretation']['value'] if record['interpretation'] is not None else 'unknown'

def populate_endpoint_signal(extraction):
    """Populate only the ordered requested cells, retaining conditional meanings.

    Endpoint amplitudes are direction-oriented pixels. Their ratio is justified
    only under a common affine ordinate and the supplied baseline applicability.
    Propagation uses the actual ordered three-primitive covariance. A source
    supplied physical block is ALREADY in native-coordinate units; this function
    has no numeric affine calibration operands and performs no unit conversion.
    """
    data=validate_endpoint_signal_extraction(extraction)
    points=[data['points'][r]['observation'] for r in POINT_ORDER]
    coords=[Fraction(p['y']) if p is not None else None for p in points]
    owners=[p['coordinate_owner'] if p is not None else None for p in points]
    a,b,t=coords
    direction=_relationship(data,'ordinate_direction')
    s=Fraction(-1 if direction=='increases_upward' else 1)
    rel=lambda name:_relationship(data,name)
    conditions=['same_trace_shared_initial_ordinate','selected_finite_time_coordinate']
    common=[]
    if rel('axis_scale')!='common_affine': common.append('axis_scale_unestablished')
    else: conditions.append('common_affine_native_ordinate')
    if direction not in ('increases_upward','increases_downward'): common.append('ordinate_direction_unresolved')
    else: conditions.append('selected_ordinate_direction')
    if rel('measurement_stage')!='endpoint_amplitude': common.append('measurement_stage_not_endpoint')
    correction=[]
    if rel('correction_stage')!='not_applied':
        correction.append('correction_already_applied' if rel('correction_stage')=='already_applied' else 'correction_stage_unresolved')
    else: conditions.append('uncorrected_source_trace')
    if rel('baseline_basis')!='source_displayed_extrapolation': correction.append('baseline_basis_unsupported')
    else: conditions.append('source_displayed_baseline')
    conditional=False
    for name,reason,prefix in (('baseline_applicability','baseline_applicability_unresolved','baseline_extrapolation'),
            ('fast_component_completion','fast_component_completion_unresolved','fast_component_completion')):
        if rel(name)=='supported': conditions.append(prefix+'_supported')
        elif rel(name)=='explicit_conditional_scenario':
            conditional=True;conditions.append(prefix+'_stipulated')
        else: correction.append(reason)
    values=[None]*5;bounds=[None]*5;reasons=[]
    required=((0,2),(0,1),(1,2),(0,1,2),(0,1,2))
    for i,indices in enumerate(required):
        reason=list(common)+(list(correction) if i else [])
        reason.extend('missing_'+POINT_ORDER[j] for j in indices if coords[j] is None)
        reasons.append(list(dict.fromkeys(reason)))
    if not reasons[0]: values[0]=s*(a-t)
    if not reasons[1]: values[1]=s*(a-b)
    if not reasons[2]: values[2]=s*(b-t)
    for i in (3,4):
        if not reasons[i] and a==t: reasons[i].append('zero_total_amplitude')
    if not reasons[3]: values[3]=(a-b)/(a-t)
    if not reasons[4]: values[4]=1-(a-b)/(a-t)
    enclosure_reasons=[None]*5
    for i,indices in enumerate(required):
        if values[i] is None: continue
        if any(points[j]['y_enclosure'] is None for j in indices):
            enclosure_reasons[i]='reading_enclosure_unreported';continue
        ranges=[points[j]['y_enclosure'] if j in indices else (0,0) for j in range(3)]
        if i>=3:
            dlo=Fraction(ranges[0][0])-Fraction(ranges[2][1])
            dhi=Fraction(ranges[0][1])-Fraction(ranges[2][0])
            if dlo<=0<=dhi:
                enclosure_reasons[i]='reading_denominator_contains_zero';continue
        # All corners reuse the SAME a in numerator and denominator.
        candidates=[]
        for aa,bb,tt in product(*ranges):
            aa,bb,tt=map(Fraction,(aa,bb,tt))
            candidates.append((s*(aa-tt),s*(aa-bb),s*(bb-tt),None,None)[i] if i<3
                else (aa-bb)/(aa-tt) if i==3 else 1-(aa-bb)/(aa-tt))
        bounds[i]=(min(candidates),max(candidates))
    incompatible=(rel('additive_interpretation')=='nonnegative_additive' and any(q is not None and q<0 for q in values[:3]))
    cov=data['covariance'];model=cov['model'] if cov and cov['error'] is None else None
    physical=model is not None and model['basis']=='joint_physical_ordinate_estimates'
    qualifications=['manual_reading_not_physical_measurement','not_molecular_attribution']
    if not physical: qualifications.append('physical_covariance_unreported')
    if incompatible: qualifications.append('nonnegative_additive_model_incompatible')
    matrix=[[_fraction(q) for q in row] for row in cov['exact_covariance']] if model else None
    variance_reason=('covariance_unreported' if cov is None else 'covariance_unavailable' if model is None
        else 'covariance_status_unknown' if model['variance_status']=='unknown' else None)
    gradients=[None]*5
    if a is not None and t is not None: gradients[0]=(s,0,-s)
    if a is not None and b is not None: gradients[1]=(s,-s,0)
    if b is not None and t is not None: gradients[2]=(0,s,-s)
    if all(v is not None for v in coords) and a!=t:
        gradients[3]=((b-t)/(a-t)**2,-1/(a-t),(a-b)/(a-t)**2)
        gradients[4]=tuple(-v for v in gradients[3])
    propagated=None
    if variance_reason is None and all(g is not None for g in gradients) and not any(reasons):
        propagated=[[sum(gradients[i][k]*matrix[k][l]*gradients[j][l] for k in range(3) for l in range(3))
            for j in range(5)] for i in range(5)]
    def cell(i,variance=False):
        name=COMPONENTS[i+5 if variance else i]
        reason=list(reasons[i]);q=values[i];interval=bounds[i]
        quals=list(qualifications);conds=list(conditions);cell_owners=owners
        if not variance and enclosure_reasons[i]: reason.append(enclosure_reasons[i])
        if variance:
            interval=None;q=None
            if variance_reason: reason.append(variance_reason)
            elif not reason and gradients[i] is not None:
                q=sum(gradients[i][k]*matrix[k][l]*gradients[i][l] for k in range(3) for l in range(3))
            quals.append('first_order_covariance_propagation');conds.append('first_order_covariance_propagation')
            if model:
                cell_owners=model['primitive_owners']
                conds.extend(['joint_physical_ordinate_estimate_model' if physical else 'joint_manual_reading_error_model',
                    'covariance_already_in_native_coordinate_units'])
                if model['variance_status'] in ('known','estimated'): conds.append(model['variance_status']+'_covariance')
                if model['origin']=='synthetic':
                    quals.append('synthetic_covariance_model');conds.append('synthetic_uncertainty_scenario')
        if interval is not None: quals.append('reading_bounds_not_statistical_CI')
        is_conditional=conditional and i!=0
        value=_project(q) if q is not None else None
        if q is not None and value is None: reason.append('numerical_projection_range')
        lo,hi=interval if interval is not None else (None,None)
        lower,upper=(_project(lo,-1) if lo is not None else None),(_project(hi,1) if hi is not None else None)
        if interval is not None and (lower is None or upper is None) and 'numerical_projection_range' not in reason:
            reason.append('numerical_projection_range')
        unit=('pixel^2' if i<3 else 'dimensionless^2') if variance else ('direction_oriented_pixel' if i<3 else 'dimensionless')
        return {'component':name,'value':None if is_conditional else value,'conditional_value':value if is_conditional else None,
            'exact_value':_exact(q) if q is not None and not is_conditional else None,
            'conditional_exact_value':_exact(q) if q is not None and is_conditional else None,
            'lower':lower,'upper':upper,'exact_lower':_exact(lo) if lo is not None else None,
            'exact_upper':_exact(hi) if hi is not None else None,'unit':unit,
            'status':'unavailable' if q is None else 'conditional_scenario' if is_conditional else 'populated',
            'origin':'derived','input_origins':deepcopy(data['input_origins']),
            'formula':FORMULAS[name],'meaning':MEANINGS[name],
            'conditional_on':list(dict.fromkeys(conds)),'unavailable_reasons':list(dict.fromkeys(reason)),
            'qualifications':list(dict.fromkeys(quals)),
            'bound_kind':'manual_reading_enclosure_not_confidence_interval' if interval is not None else 'none',
            'primitive_owners':deepcopy(cell_owners),
            'contribution_key':identity('endpoint_contribution',{'owners':owners}),
            'uncertainty_basis':model['basis'] if variance and model else None}
    cells={name:cell(i%5,i>=5) for i,name in enumerate(COMPONENTS)}
    sheet={'version':VERSION,'axis':'A105','section':'endpoint_signal_contribution',
        'requested_cells':list(data['arguments']['requested_cells']),
        'cells':[cells[name] for name in data['arguments']['requested_cells']],
        'input_snapshot':data,'joint_propagation':None}
    if propagated is not None:
        sheet['joint_propagation']={'basis':model['basis'],'origin':model['origin'],
            'primitive_order':list(POINT_ORDER),'primitive_owners':deepcopy(model['primitive_owners']),
            'component_order':list(_BASE),'exact_covariance':[[_exact(q) for q in row] for row in propagated]}
    _schema_check(sheet,endpoint_signal_sheet_schema(),'sheet')
    return sheet

__all__=['VERSION','COMPONENTS','FORMULAS','MEANINGS','REASONS','QUALIFICATIONS',
    'endpoint_signal_cell_schema','endpoint_signal_sheet_schema','populate_endpoint_signal']
