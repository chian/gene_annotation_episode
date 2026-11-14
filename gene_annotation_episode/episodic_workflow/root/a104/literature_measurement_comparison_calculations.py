"""Finite A105 measurement comparisons, signed mixtures and covariance.

All scientific interpretations and observations are already bound by the reader.
No acquisition, state mutation, model call, stopping decision or credit occurs.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import re
from .domain import identity, validate_schema
from .literature_measurement_comparison_inputs import (
    _resource, _q, _exact, _float, _reasons, _merge, _psd, _fail,
    validate_measurement_comparison_calculation_inputs,
)

_COMPONENTS = {'native_left': {'formula': 'native_estimate', 'meaning': 'Native selected left report'}, 'native_right': {'formula': 'native_estimate', 'meaning': 'Native selected right report'}, 'converted_left': {'formula': 'c_left*x_left', 'meaning': 'Left report expressed on supported common endpoint scale'}, 'converted_right': {'formula': 'c_right*x_right', 'meaning': 'Right report expressed on supported common endpoint scale'}, 'protocol_difference': {'formula': 'L-R', 'meaning': 'Signed difference of linked source protocol estimates'}, 'protocol_ratio': {'formula': 'L/R', 'meaning': 'Descriptive ratio of linked source protocol estimates'}, 'protocol_log_ratio': {'formula': 'ln(L)-ln(R)', 'meaning': 'Dependent log representation of protocol comparison'}, 'common_difference': {'formula': 'L-R', 'meaning': 'Difference under declared common estimand model'}, 'common_ratio': {'formula': 'L/R', 'meaning': 'Ratio under declared common estimand model'}, 'common_log_ratio': {'formula': 'ln(L)-ln(R)', 'meaning': 'Dependent log representation of common comparison'}, 'difference_variance': {'formula': 'c_left^2*Cll+c_right^2*Crr-2*c_left*c_right*Clr', 'meaning': 'Variance of the linked reported-protocol difference under the actual joint selected-estimator covariance; no common-condition or common-mean equivalence is required.'}, 'difference_standard_uncertainty': {'formula': 'sqrt(V_D)', 'meaning': 'Square root of that reported-protocol difference variance; no common-mean model or sampling distribution is inferred.'}, 'standardized_difference': {'formula': 'D/sqrt(V_D)', 'meaning': 'Signed standardized discrepancy with stated variance meaning'}, 'squared_standardized_difference': {'formula': 'D^2/V_D', 'meaning': 'Squared standardized discrepancy from the same measurements'}, 'weight_left': {'formula': '(V_R-C_LR)/(V_L+V_R-2*C_LR)', 'meaning': 'Generalized least squares left weight'}, 'weight_right': {'formula': '(V_L-C_LR)/(V_L+V_R-2*C_LR)', 'meaning': 'Generalized least squares right weight'}, 'combined_estimate': {'formula': 'if(V_D>0,w_L*L+w_R*R,if(V_D==0&&D==0,L,unavailable))', 'meaning': 'Common unbiased quantity estimate under the declared covariance model; for V_D=0 and L=R the shared value is unique even when the unbiased weight allocation is nonunique.'}, 'combined_variance': {'formula': 'if(V_D>0,(V_L*V_R-C_LR^2)/V_D,if(V_D==0&&D==0,V_L,unavailable))', 'meaning': 'Variance of the common estimate under the declared covariance model; for V_D=0 and L=R, PSD implies V_L=V_R=C_LR=v and every unbiased weight allocation has variance v.'}, 'combined_standard_uncertainty': {'formula': 'sqrt(V_combined)', 'meaning': 'Square root of that common-estimate variance, including zero under a declared known zero-variance model; nonunique weights do not erase this quantity.'}, 'spectral_multiplier': {'formula': 'epsilon_nuisance/epsilon_signal', 'meaning': 'Relative signed mixture sensitivity magnitude'}, 'spectral_multiplier_variance': {'formula': 'J_alpha*C_epsilon*J_alpha_transpose', 'meaning': 'First order multiplier variance'}, 'observed_interference': {'formula': 's*alpha*f', 'meaning': 'Observed nuisance contribution on applicable selected estimate scale'}, 'corrected_estimate': {'formula': 'y-s*alpha*f', 'meaning': 'Measured corrected quantity under applicable estimate scale model'}, 'corrected_estimate_variance': {'formula': 'J_h*C_y_epsilon_f*J_h_transpose', 'meaning': 'First order corrected quantity variance'}, 'required_interference_scenario': {'formula': 'y-H', 'meaning': 'Required signed observed mixture contribution if true quantity equals H'}, 'required_nuisance_equivalent_scenario': {'formula': '(y-H)/(s*alpha)', 'meaning': 'Required nuisance equivalent on selected report scale under two explicit stipulations'}}
_LIMITS = ['standalone_components_not_selected_integration', 'same_estimate_ratio_log_difference_are_dependent', 'agreement_does_not_detect_shared_bias', 'source_positive_matched_covariance_case_still_open', 'general_A105_adequacy_unfinished', 'no_target_transfer_or_W05', 'corrected_quantity_not_automatically_substituted_into_common_pair', 'unknown_systematics_not_set_to_zero']


def measurement_comparison_sheet_schema(): return _resource('SHEET')


def measurement_comparison_cell_schema(component: str | None = None) -> dict:
    schema=measurement_comparison_sheet_schema()
    result={'$schema':schema['$schema'],'$defs':schema['$defs'],**deepcopy(schema['$defs']['cell'])}
    if component is not None:
        if component not in _COMPONENTS:_fail('unknown_comparison_component','component')
        result['properties']['component']={'const':component}
    return result


def _sqrt(value):
    n,d=math.isqrt(value.numerator),math.isqrt(value.denominator)
    if n*n==value.numerator and d*d==value.denominator:
        exact=Fraction(n,d);return _float(exact),_exact(exact)
    with localcontext() as context:
        context.prec=80
        return _float((Decimal(value.numerator)/Decimal(value.denominator)).sqrt()),None


def _reason(family,code):
    result=_reasons();result[family].append(code);return result


def _has_reason(reasons): return any(reasons.values())


def _log_ratio(left,right):
    ratio=left/right
    if ratio==1:return 0.0
    if abs(ratio-1)<=Fraction(1,2):
        delta=_float(ratio-1)
        if delta is None:return None
        return math.log1p(delta)
    result=math.log(ratio.numerator)-math.log(ratio.denominator)
    return result if math.isfinite(result) and result!=0 else None


def _covariance_for(data,roles):
    quantities=data['quantities'];needed=[]
    for role in roles:
        if quantities[role] is None:return None,'unknown',[],_reason('source','quantity_not_selected'),[]
        if quantities[role]['owner_key'] not in needed:needed.append(quantities[role]['owner_key'])
    available=[b for b in data['covariance_blocks'] if b['status']=='available' and set(b['owner_keys'])&set(needed)]
    if not available:
        reasons=_reasons()
        for b in data['covariance_blocks']:reasons=_merge(reasons,b['reasons'])
        if not _has_reason(reasons):reasons['source'].append('covariance_not_supplied')
        return None,'unknown',[],reasons,[]
    entries={};status=[];sources=[];origins=[]
    for block in available:
        status.append(block['variance_status']);sources.append(block['source_ref']);origins.append(block['origin'])
        for i,a in enumerate(block['owner_keys']):
            for j,b in enumerate(block['owner_keys']):entries[(a,b)]=_q(block['matrix_exact'][i][j])
    if any((a,b) not in entries for a in needed for b in needed):
        return None,'unknown',sources,_reason('source','joint_covariance_incomplete'),origins
    unique=[[entries[(a,b)] for b in needed] for a in needed]
    if not _psd(unique):return None,'unknown',sources,_reason('domain','covariance_not_positive_semidefinite'),origins
    ordered=[quantities[r]['owner_key'] for r in roles]
    C=[[entries[(a,b)] for b in ordered] for a in ordered]
    return C,'estimated' if 'estimated' in status else 'known',list(dict.fromkeys(sources)),_reasons(),list(dict.fromkeys(origins))


def populate_measurement_comparison(inputs: dict) -> dict:
    data=validate_measurement_comparison_calculation_inputs(inputs)
    args=data['selection'];quantities=data['quantities'];conversions=data['conversions']
    relation={k:v['value'] for k,v in data['relationships'].items()}
    optical=args['optical'];model=args['common_model'];cells={}
    def own_reasons(roles):
        return _merge(*[_reason('source','quantity_not_selected') if quantities[r] is None else quantities[r]['reasons'] for r in roles])
    def quantity(role):
        value=quantities[role]
        return None if value is None or value['canonical_exact'] is None or _has_reason(value['reasons']) else _q(value['canonical_exact'])
    def cell(name,value=None,*,roles=('left','right'),reasons=None,unit='dimensionless',interpretation='supported_reexpression',
             conditional=False,models=(),variance_status='not_selected',covrefs=(),covorigins=(),scope='not_applicable',root=False,native=None):
        reasons=_reasons() if reasons is None else _merge(reasons)
        if _has_reason(reasons):value=None
        exact=None;floating=None
        if value is not None:
            if root:floating,exact=_sqrt(value)
            elif isinstance(value,Fraction):floating,exact=_float(value),_exact(value)
            else:floating=_float(value)
            if floating is None:
                reasons['implementation'].append('numerical_model_range');exact=None
        origins=list(dict.fromkeys([quantities[r]['origin'] for r in roles if quantities[r] is not None]+list(covorigins)))
        owners=list(dict.fromkeys(quantities[r]['owner_key'] for r in roles if quantities[r] is not None))
        contribution=data['contribution_key']
        if name.startswith(('spectral','observed_interference','corrected_','required_')):
            contribution=identity('measurement_comparison_optical_contribution',{'assertion':data['assertion_key'],'owners':owners,'model':optical})
        return {'component':name,'value':None if conditional else floating,'exact_value':None if conditional else exact,
            'conditional_value':floating if conditional else None,'conditional_exact_value':exact if conditional else None,
            'status':'unavailable' if floating is None else 'conditional_scenario' if conditional else 'populated','unit':unit,
            'relation':native['relation'] if native else 'point','approximate':any(quantities[r] is not None and quantities[r]['approximate'] for r in roles),
            'interpretation':'unavailable' if floating is None else interpretation,'formula':_COMPONENTS[name]['formula'],'meaning_code':name,
            'origin':native['origin'] if native else 'derived','input_origins':origins,'operand_roles':list(roles),'operand_keys':owners,
            'model_keys':list(dict.fromkeys(models)),'contribution_key':contribution,
            'uncertainty':{'covariance_source_refs':list(covrefs),'variance_status':variance_status,'scope':scope,'sampling_distribution':'not_assumed'},'reasons':reasons}
    # Native fields display reported qualifiers without using a threshold/ND as a point operand.
    for role in ('left','right'):
        value=quantities[role];selection=args['quantities'][role]
        native=None if value is None or value['native_exact'] is None else _q(value['native_exact'])
        native_unit=None
        if selection is not None and selection['unit'] is not None:
            u=selection['unit'];native_unit=u.get('witness',u)['quote']
        why=_reasons() if native is not None else own_reasons((role,))
        cells['native_'+role]=cell('native_'+role,native,roles=(role,),unit=native_unit,interpretation='native_report',reasons=why,native=value)
    baseunit=args['common_quantity']['unit'];converted={};conv_reasons={};scales={}
    for role in ('left','right'):
        why=own_reasons((role,));v=quantities[role];conversion=conversions[role]
        if conversion['multiplier_exact'] is None:
            selected=args['common_quantity'][role+'_conversion']
            qualified=[r['reading'] for r in conversion['coefficient_readings'].values() if r is not None and
                       (r['reading']['relation']!='point' or r['reading']['approximate'] or r['reading']['native_exact'] is None)]
            if qualified:
                why['implementation'].append('numerical_model_range' if any(r['native_exact'] is None and r['relation']=='unresolved' and re.fullmatch(r'[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?',r['raw_token']) for r in qualified) else 'uncertain_conversion_unimplemented')
                if 'conflicting' in (conversion['status'],selected['direction']['value']):
                    why['relationship'].append('endpoint_conversion_conflicting')
                elif 'unknown' in (conversion['status'],selected['direction']['value']):
                    why['relationship'].append('endpoint_conversion_unknown')
            else:
                why['relationship'].append('endpoint_conversion_conflicting' if conversion['status']=='conflicting' else 'endpoint_conversion_unknown')
            if selected['direction']['value']=='opposite_direction':why['implementation'].append('opposite_direction_conversion_unimplemented')
        if v is not None and (v['canonical_unit']!=baseunit or v['quantity_kind'] not in ('apparent_specific_activity','specific_activity','fixed_condition_rate','turnover_rate')):
            why['implementation'].append('unsupported_unit')
        scale=None if conversion['multiplier_exact'] is None else _q(conversion['multiplier_exact'])
        scales[role]=scale
        value=None if scale is None or quantity(role) is None or _has_reason(why) else scale*quantity(role)
        converted[role]=value;conv_reasons[role]=why
        cells['converted_'+role]=cell('converted_'+role,value,roles=(role,),reasons=why,unit=baseunit,models=(conversion['model_key'],))
    pair_reasons=_merge(*conv_reasons.values())
    if relation['endpoint'] not in ('same_quantity','fixed_reaction_conversion'):pair_reasons['relationship'].append('endpoint_incompatible' if relation['endpoint']=='incompatible' else 'endpoint_conversion_unknown')
    if relation['denominator']!='same_basis_supported':pair_reasons['relationship'].append('denominator_not_common')
    L,R=converted['left'],converted['right'];difference=ratio=log=None
    if not _has_reason(pair_reasons) and L is not None and R is not None:
        difference=L-R
        if R!=0:ratio=L/R
        if L>0 and R>0:log=_log_ratio(L,R)
    ratio_why=_merge(pair_reasons,_reason('domain','zero_denominator') if R==0 else _reasons())
    log_why=deepcopy(pair_reasons)
    if L is not None and R is not None and (L<=0 or R<=0):log_why['domain'].append('positive_values_required_for_log')
    elif not _has_reason(log_why) and log is None:log_why['implementation'].append('numerical_model_range')
    conversion_keys=[conversions[r]['model_key'] for r in ('left','right')]
    for name,val,why,unit in (('protocol_difference',difference,pair_reasons,baseunit),('protocol_ratio',ratio,ratio_why,'dimensionless'),('protocol_log_ratio',log,log_why,'dimensionless')):
        cells[name]=cell(name,val,reasons=why,unit=unit,interpretation='descriptive_protocol_comparison',models=conversion_keys)
    common_why=deepcopy(pair_reasons);conditional=False;common_keys=conversion_keys[:]
    if model is None:common_why['relationship'].append('common_model_not_selected')
    else:
        status=model['applicability']['value']
        if status in ('unknown','conflicting'):common_why['relationship'].append('common_model_'+status)
        conditional=status=='stipulated_sensitivity'
        common_keys.append(identity('measurement_comparison_common_model',model))
    if relation['construct']!='same_construct_supported':common_why['relationship'].append('construct_not_common')
    if relation['preparation_target'] not in ('same_preparation_quantity','same_population_estimand_supported'):
        common_why['relationship'].append('preparation_target_conflicting' if relation['preparation_target']=='conflicting' else 'preparation_target_unknown')
    if relation['protocol']!='matched_except_intended_change':common_why['relationship'].append('protocols_not_matched')
    if relation['functional_bearing']!='same_quantitative_assertion':common_why['relationship'].append('functional_resolution_not_quantitative')
    if any(relation[r+'_validity'] not in ('endpoint_quantification_supported','corrected_endpoint_supported') for r in ('left','right')):
        common_why['relationship'].append('validity_unresolved')
    for name,val,extra,unit in (('common_difference',difference,_reasons(),baseunit),('common_ratio',ratio,ratio_why,'dimensionless'),('common_log_ratio',log,log_why,'dimensionless')):
        cells[name]=cell(name,val,reasons=_merge(common_why,extra),unit=unit,interpretation='common_estimand_comparison',conditional=conditional,models=common_keys)
    # A descriptive difference variance needs no common-mean model.
    C,status,refs,cov_why,cov_origins=_covariance_for(data,('left','right'))
    vwhy=_merge(pair_reasons,cov_why);VD=a=b=c=None
    if C is not None and not _has_reason(vwhy):
        sl,sr=scales['left'],scales['right'];a=sl*sl*C[0][0];b=sl*sr*C[0][1];c=sr*sr*C[1][1];VD=a+c-2*b
    variance_unit=None if baseunit=='unknown' else '('+baseunit+')^2'
    vinterp='protocol_difference_uncertainty_estimated_covariance' if status=='estimated' else 'protocol_difference_uncertainty_known_covariance'
    for name,root,unit in (('difference_variance',False,variance_unit),('difference_standard_uncertainty',True,baseunit)):
        cells[name]=cell(name,VD,reasons=vwhy,unit=unit,interpretation=vinterp,root=root,models=conversion_keys,
            variance_status=status,covrefs=refs,covorigins=cov_origins,scope='selected_estimator_covariance')
    score_why=_merge(common_why,vwhy)
    if model is not None and status in ('known','estimated') and model['variance_interpretation']!=status+'_joint_estimator_covariance':
        score_why['relationship'].append('variance_meaning_mismatch')
    z=z2=wl=wr=mean=variance=None
    weight_why=deepcopy(score_why);comb_why=deepcopy(score_why);zwhy=deepcopy(score_why)
    if VD is not None and not _has_reason(score_why):
        if VD>0:
            z2=difference*difference/VD;wl=(c-b)/VD;wr=(a-b)/VD;mean=wl*L+wr*R;variance=(a*c-b*b)/VD
            # Scale before projection so variance/sqrt intermediates do not overflow.
            z_abs,_=_sqrt(z2)
            z=None if z_abs is None else -z_abs if difference<0 else z_abs
        elif difference==0:
            zwhy['domain'].append('zero_plugin_difference_variance' if status=='estimated' else 'positive_discrepancy_variance_required')
            weight_why['domain'].append('nonunique_gls_weights');mean=L;variance=a
        elif status=='known':
            for why in (zwhy,weight_why,comb_why):why['domain'].append('inconsistent_deterministic_constraint')
        else:
            zwhy['domain'].append('zero_plugin_difference_variance');weight_why['domain'].append('nonunique_gls_weights')
            comb_why['domain'].append('combined_estimate_not_identified_by_plugin_covariance')
    if model is not None and model['combination']=='not_requested':
        comb_why['relationship'].append('common_model_not_selected');weight_why['relationship'].append('common_model_not_selected')
    interp='estimated_covariance_plugin_standardization' if status=='estimated' else 'known_covariance_standardization'
    for name,val in (('standardized_difference',z),('squared_standardized_difference',z2)):
        cells[name]=cell(name,val,reasons=zwhy,interpretation=interp,conditional=conditional,models=common_keys,
            variance_status=status,covrefs=refs,covorigins=cov_origins,scope='selected_estimator_covariance')
    interp='estimated_covariance_plugin_common_estimate' if status=='estimated' else 'known_covariance_common_estimate'
    for name,val,why,unit,root in (('weight_left',wl,weight_why,'dimensionless',False),('weight_right',wr,weight_why,'dimensionless',False),
            ('combined_estimate',mean,comb_why,baseunit,False),('combined_variance',variance,comb_why,variance_unit,False),('combined_standard_uncertainty',variance,comb_why,baseunit,True)):
        cells[name]=cell(name,val,reasons=why,unit=unit,interpretation=interp,root=root,conditional=conditional,models=common_keys,
            variance_status=status,covrefs=refs,covorigins=cov_origins,scope='selected_estimator_covariance')
    # Optical physics and fitted-estimate applicability are separate declarations.
    alpha=None;alpha_why=own_reasons(('epsilon_nuisance','epsilon_signal'))
    optical_keys=[] if optical is None else [identity('measurement_comparison_optical_model',optical)]
    def model_reason(item,unknown,conflicting):
        if item['value']=='unknown':return _reason('relationship',unknown)
        if item['value']=='conflicting':return _reason('relationship',conflicting)
        return _reasons()
    if optical is None:alpha_why['relationship'].append('optical_model_unknown')
    else:alpha_why=_merge(alpha_why,model_reason(optical['coefficient_applicability'],'coefficient_applicability_unknown','coefficient_applicability_conflicting'))
    en,es=quantity('epsilon_nuisance'),quantity('epsilon_signal')
    if es==0:alpha_why['domain'].append('nonzero_spectral_signal_required')
    if en is not None and es is not None and not _has_reason(alpha_why):alpha=en/es
    spectral_cond=bool(optical and optical['coefficient_applicability']['value']=='stipulated_sensitivity')
    cells['spectral_multiplier']=cell('spectral_multiplier',alpha,roles=('epsilon_nuisance','epsilon_signal'),reasons=alpha_why,
        unit='umol_signal_equivalent_per_umol_nuisance',interpretation='spectral_sensitivity',conditional=spectral_cond,models=optical_keys)
    eC,estatus,erefs,ecwhy,eorigins=_covariance_for(data,('epsilon_nuisance','epsilon_signal'))
    alphavar=None;awhy=_merge(alpha_why,ecwhy)
    if alpha is not None and eC is not None and not _has_reason(awhy):
        J=(1/es,-en/es**2);alphavar=sum(J[i]*eC[i][j]*J[j] for i in range(2) for j in range(2))
    cells['spectral_multiplier_variance']=cell('spectral_multiplier_variance',alphavar,roles=('epsilon_nuisance','epsilon_signal'),
        reasons=awhy,unit='(umol_signal_equivalent_per_umol_nuisance)^2',interpretation='first_order_estimated_input_covariance' if estatus=='estimated' else 'first_order_known_input_covariance',
        conditional=spectral_cond,models=optical_keys,variance_status=estatus,covrefs=erefs,covorigins=eorigins,scope='first_order_operand_propagation')
    signal_role='left' if optical is None else optical['signal_role']
    y=quantity(signal_role);f=quantity('nuisance');yv=quantities[signal_role];fv=quantities['nuisance']
    signalunit=None if yv is None else yv['canonical_unit']
    correction_why=_merge(alpha_why,own_reasons(('nuisance',)))
    correction_cond=spectral_cond
    if f is None and 'quantity_not_selected' in correction_why['source']:
        correction_why['source'].remove('quantity_not_selected');correction_why['source'].append('nuisance_quantity_unmeasured')
    if optical:
        for field,unknown,conflict in (('raw_optical_relation','optical_model_unknown','optical_model_conflicting'),
                ('estimate_scale_applicability','estimate_scale_model_unknown','estimate_scale_model_conflicting'),
                ('nuisance_quantity_linkage','nuisance_linkage_unknown','nuisance_linkage_conflicting')):
            correction_why=_merge(correction_why,model_reason(optical[field],unknown,conflict))
            correction_cond |= optical[field]['value']=='stipulated_sensitivity'
    if yv is not None and fv is not None and (yv['canonical_unit']!=fv['canonical_unit'] or yv['normalization']!=fv['normalization']):
        correction_why['relationship'].append('denominator_not_common')
    s=-1 if optical is None else optical['nuisance_sign']
    interference=None if alpha is None or f is None or _has_reason(correction_why) else s*alpha*f
    corrected_why=_merge(correction_why,own_reasons((signal_role,)))
    corrected=None if y is None or interference is None or _has_reason(corrected_why) else y-interference
    opt_roles=(signal_role,'epsilon_nuisance','epsilon_signal','nuisance')
    cells['observed_interference']=cell('observed_interference',interference,roles=('epsilon_nuisance','epsilon_signal','nuisance'),
        reasons=correction_why,unit=signalunit,interpretation='supported_estimate_scale_correction',conditional=correction_cond,models=optical_keys)
    cells['corrected_estimate']=cell('corrected_estimate',corrected,roles=opt_roles,reasons=corrected_why,
        unit=signalunit,interpretation='supported_estimate_scale_correction',conditional=correction_cond,models=optical_keys)
    hC,hstatus,hrefs,hcwhy,horigins=_covariance_for(data,opt_roles)
    hwhy=_merge(corrected_why,hcwhy);hvar=None
    if corrected is not None and hC is not None and not _has_reason(hwhy):
        J=(Fraction(1),-s*f/es,s*f*en/es**2,-s*alpha)
        hvar=sum(J[i]*hC[i][j]*J[j] for i in range(4) for j in range(4))
    cells['corrected_estimate_variance']=cell('corrected_estimate_variance',hvar,roles=opt_roles,reasons=hwhy,
        unit=None if signalunit is None else '('+signalunit+')^2',interpretation='first_order_estimated_input_covariance' if hstatus=='estimated' else 'first_order_known_input_covariance',
        conditional=correction_cond,models=optical_keys,variance_status=hstatus,covrefs=hrefs,covorigins=horigins,scope='first_order_operand_propagation')
    scenario=None if optical is None else optical['scenario'];scenario_why=_reasons() if optical else _reason('relationship','optical_model_unknown');Ireq=freq=None
    scenario_roles=(signal_role,'right' if signal_role=='left' else 'left','epsilon_nuisance','epsilon_signal')
    if scenario is None:scenario_why['relationship'].append('scenario_not_selected')
    else:
        anchor=scenario['anchor_role'];scenario_roles=(signal_role,anchor,'epsilon_nuisance','epsilon_signal')
        scenario_why=_merge(scenario_why,own_reasons((signal_role,anchor)),conv_reasons[signal_role],conv_reasons[anchor])
        if anchor==signal_role or any(scenario[name]['value'] not in ('supported','stipulated_sensitivity') for name in ('common_rate_equality','linear_mixture_on_estimate_scale')):
            scenario_why['relationship'].append('scenario_stipulations_unresolved')
        if optical['raw_optical_relation']['value'] in ('unknown','conflicting'):
            scenario_why['relationship'].append('optical_model_'+optical['raw_optical_relation']['value'])
        if not _has_reason(scenario_why) and y is not None and converted[anchor] is not None:
            H=converted[anchor]/scales[signal_role];Ireq=y-H
            if alpha is not None and alpha!=0:freq=Ireq/(s*alpha)
    for name,val,unit in (('required_interference_scenario',Ireq,'umol_signal_equivalent/min/mg_on_apparent_report_scale' if signalunit=='umol/min/mg' else (signalunit or 'unknown')+'_on_selected_report_scale'),
            ('required_nuisance_equivalent_scenario',freq,'umol_nuisance_equivalent/min/mg_on_apparent_report_scale' if signalunit=='umol/min/mg' else (signalunit or 'unknown')+'_nuisance_equivalent_on_selected_report_scale')):
        why=deepcopy(scenario_why)
        roles=tuple(dict.fromkeys(scenario_roles[:2]))
        if name=='required_nuisance_equivalent_scenario':
            why=_merge(why,alpha_why);roles=tuple(dict.fromkeys(scenario_roles))
            if alpha==0:why['domain'].append('zero_denominator')
        cells[name]=cell(name,val,roles=roles,reasons=why,unit=unit,
            interpretation='stipulated_report_scale_scenario',conditional=True,models=(*optical_keys,*conversion_keys))
    groups={}
    for r,v in quantities.items():
        if v is not None:groups.setdefault(v['physical_owner_key'] or v['owner_key'],[]).append(r)
    dependence=[{'roles':roles,'relation':'shared_primitive'} for roles in groups.values() if len(roles)>1]
    sampling=relation['sampling']
    dependence.append({'roles':[r for r in ('left','right') if quantities[r] is not None],
        'relation':sampling if sampling in ('repeated_representation','shared_physical_estimate','paired_observations_supported','independent_preparations_supported') else 'sampling_unknown'})
    assumptions=[]
    if model is not None:assumptions.append('common_unbiased_quantity_model')
    if any(c['kind']=='fixed_reaction_scale' for c in conversions.values()):assumptions.append('fixed_reaction_conversion')
    if optical is not None and optical['estimate_scale_applicability']['value']=='supported':assumptions.append('linear_mixture_on_selected_estimate_scale')
    if scenario:
        if scenario['common_rate_equality']['value']=='stipulated_sensitivity':assumptions.append('common_rate_equality_stipulated')
        if scenario['linear_mixture_on_estimate_scale']['value']=='stipulated_sensitivity':assumptions.append('linear_estimate_scale_mapping_stipulated')
    if status=='estimated':assumptions.append('estimated_weights_treated_as_plugin')
    if any(c['uncertainty']['scope']=='first_order_operand_propagation' and c['status']!='unavailable' for c in cells.values()):assumptions.append('first_order_covariance_propagation')
    assumptions.append('no_reference_distribution_assumed')
    result=dict(version='a105_measurement_comparison_sheet_v1',axis='A105',section='measurement_comparison_validity',
        assertion_key=data['assertion_key'],contribution_key=data['contribution_key'],cells=[cells[n] for n in args['requested_cells']],
        relationship_meanings=relation,estimate_bindings=[{'role':r,**{k:v[k] for k in ('owner_key','physical_owner_key','dependency_keys','estimator_scale')},'unit':v['canonical_unit']}
            for r,v in quantities.items() if v is not None],dependence=dependence,assumptions=list(dict.fromkeys(assumptions)),annotation_credit=None,remaining_limits=list(_LIMITS))
    validate_schema(result,measurement_comparison_sheet_schema())
    return result


def validate_measurement_comparison_sheet(sheet: dict, *, inputs: dict | None = None) -> dict:
    result=deepcopy(sheet);validate_schema(result,measurement_comparison_sheet_schema())
    names=[c['component'] for c in result['cells']]
    if len(set(names))!=len(names):_fail('duplicate_comparison_sheet_component','cells')
    for c in result['cells']:
        for f,e in (('value','exact_value'),('conditional_value','conditional_exact_value')):
            if c[e] is not None and c[f]!=_float(_q(c[e])):_fail('comparison_sheet_exact_value_mismatch',c['component'])
        if c['status']=='unavailable' and not _has_reason(c['reasons']):_fail('comparison_unavailable_reason_required',c['component'])
        if c['uncertainty']['variance_status']=='estimated' and c['interpretation']=='known_covariance_standardization':_fail('comparison_variance_interpretation_mismatch',c['component'])
    if inputs is not None and result!=populate_measurement_comparison(inputs):_fail('comparison_sheet_derivation_mismatch','sheet')
    return result
