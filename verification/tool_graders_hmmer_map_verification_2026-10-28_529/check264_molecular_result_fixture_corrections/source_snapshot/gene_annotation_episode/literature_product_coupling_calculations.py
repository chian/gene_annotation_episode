"""Exact endpoint-coupling components; no function probability or final credit."""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from math import isqrt

from .domain import identity, obj, validate_schema
from .literature_product_coupling_inputs import (
    _q, _float, _exact, _exact_schema, _nullable, _array,
    product_coupling_extraction_schema, validate_product_coupling_extraction,
    NUMBER_REASONS, EXTRA_NUMBER_REASONS, UNIT_REASONS, COVARIANCE_REASONS,
    QUANTITY_MEANINGS, RELATIONSHIPS, ROLES, RELATIONS,
)

VERSION='a105_product_coupling_components_v1'
COMPONENTS=('reported_product_activity','reported_cofactor_activity','product_per_cofactor',
    'productive_fraction','calculated_coupling_percent','reported_coupling_percent',
    'displayed_coupling_difference_pp','reconstructed_product_activity',
    'product_per_cofactor_variance','productive_fraction_variance','productive_fraction_standard_uncertainty')
FORMULAS=dict(zip(COMPONENTS,('source_product_rate_unit_conversion','source_cofactor_rate_unit_conversion',
    'P/H','nu_cofactor_per_product*P/H','100*nu_cofactor_per_product*P/H',
    'source_reported_coupling_percent_unit_conversion','100*nu_cofactor_per_product*P/H-reported_percent',
    '(P/H)*H_same_operands','J*Sigma*Jtranspose;J=(1/H,-P/H^2)',
    'fixed_nu_cofactor_per_product^2*product_per_cofactor_variance',
    'sqrt(fixed_nu_cofactor_per_product^2*product_per_cofactor_variance)')))
MEANINGS=dict(zip(COMPONENTS,('Source product report on its supported rate scale; a qualified native zero is not physical absence.',
    'Source cofactor-consumption report; reporter turnover alone does not establish productive chemistry.',
    'Descriptive identified-product per consumed-cofactor comparison of selected source rates.',
    'Stoichiometric productive fraction of the selected reaction system, distinct from molecular attribution.',
    'The same productive-fraction component displayed in percent.',
    'The author-reported coupling statistic on percent scale, preserving original source meaning.',
    'Displayed-rate arithmetic minus author-reported coupling in percentage points; no rounding/error penalty inferred.',
    'Same-source product-rate reconstruction; original product contribution, not independent validation.',
    'First-order variance of the descriptive ratio under the supplied joint selected-estimate covariance.',
    'Fixed-nu first-order productive-fraction variance; conditional fixed-substitution term when nu is uncertain.',
    'Square root of the same fixed-nu variance term, not a confidence interval or function probability.')))
REASONS=tuple(dict.fromkeys((*NUMBER_REASONS,*EXTRA_NUMBER_REASONS,*UNIT_REASONS,*COVARIANCE_REASONS,
    'quantity_not_supplied','source_number_not_supplied','unsupported_rate_dimension_for_coupling',
    'bounded_ratio_calculation_unimplemented','reused_source_observation','zero_cofactor_denominator',
    'nonpositive_cofactor_rate_for_physical_fraction','incompatible_normalization_bases',
    'nu_model_not_supplied','nu_model_conflicting','nonpositive_stoichiometric_model',
    'uncertain_nu_uncertainty_propagation_unimplemented','outside_physical_fraction_range',
    'numerical_model_range','reported_coupling_not_a_point',
    *(role+'_'+name+'_'+value for role in ROLES for name,values in QUANTITY_MEANINGS.items()
      for value in values),
    *('eta_relationship_'+name+'_'+value for name,values in RELATIONSHIPS.items() for value in values
      if value not in ('author_assigned','same','compatible','matched','chemically_identified','controlled')))))
ASSUMPTIONS=('selected_source_role_interpretations','first_order_delta_propagation_for_selected_rate_estimates',
    'fixed_stoichiometric_reaction_account_model','supplied_nu_estimate_held_fixed_for_conditional_arithmetic',
    'conditional_variance_term_excludes_nu_variance_and_covariance',
    'unknown_scientific_relationships_assumed_compatible_only_for_conditional_arithmetic',
    'unconstrained_displayed_estimate_is_not_a_physical_fraction_outside_zero_one',
    'same_operand_reconstruction_reuses_original_product_measurement')
QUALIFICATIONS=('product_identity_and_cofactor_turnover_answer_distinct_questions',
    'product_identity_does_not_quantify_molecule_specific_attribution',
    'source_pair_does_not_establish_identical_aliquot_preparation_or_sampling_window',
    'nu_is_an_explicit_interpreted_reaction_account_not_a_default_or_fitted_quality_weight',
    'reported_zero_with_nondetection_is_not_exact_physical_zero',
    'reported_and_displayed_coupling_are_preserved_separately',
    'ratio_fraction_percent_and_reconstruction_reuse_measurements',
    'shared_normalization_does_not_supply_missing_covariance',
    'supplied_covariance_is_for_selected_estimates_not_raw_variability_or_inferred_SE',
    'variance_and_standard_uncertainty_are_same_contribution_not_independent_support',
    'binding_does_not_establish_catalysis',
    'calculated_residual_water_is_not_independent_measured_mass_balance',
    'no_application_to_another_assay_or_independent_replication_inferred',
    'target_correspondence_function_probability_and_final_annotation_credit_are_outside_this_operation')


def product_coupling_cell_schema(component=None):
    return obj({'value':{'type':['number','null']},'exact_value':_nullable(_exact_schema()),
        'conditional_value':{'type':['number','null']},'conditional_exact_value':_nullable(_exact_schema()),
        'source_value':{'type':['number','null']},'source_exact_value':_nullable(_exact_schema()),
        'source_unit':{'type':['string','null']},
        'native_measurement_semantics':{'enum':[*QUANTITY_MEANINGS['measurement_semantics'],None]},
        'status':{'enum':['populated','conditional','unavailable']},
        'interpretation':{'enum':['native_report','descriptive_ratio','conditional_descriptive_ratio',
            'physical_fraction_estimate','conditional_physical_fraction_estimate','dependent_reconstruction',
            'first_order_uncertainty','conditional_first_order_uncertainty','deterministic_reexpression','unimplemented']},
        'origin':{'enum':['reported','derived','synthetic','proposed']},
        'input_origins':_array({'enum':['reported','derived','synthetic']},True),
        'relation':{'enum':list(RELATIONS)},'unit':{'type':['string','null']},
        'formula':{'const':FORMULAS[component]} if component else {'enum':list(FORMULAS.values())},
        'meaning':{'const':MEANINGS[component]} if component else {'enum':list(MEANINGS.values())},
        'input_measurement_keys':_array({'type':'string','minLength':1},True),
        'input_model_keys':_array({'type':'string','minLength':1},True),
        'contribution_key':{'type':'string','minLength':1},
        'physical_fraction_status':{'enum':['within_reported_model_domain','outside_reported_model_domain','unresolved','not_applicable']},
        'assumptions':_array({'enum':list(ASSUMPTIONS)},True),
        'unavailable_reasons':_array({'enum':list(REASONS)},True)})


def product_coupling_sheet_schema():
    return obj({'version':{'const':VERSION},'axis':{'const':'A105'},'section':{'const':'product_coupling'},
        'extraction':product_coupling_extraction_schema(),
        'cells':obj({name:product_coupling_cell_schema(name) for name in COMPONENTS}),
        'qualifications':{'const':list(QUALIFICATIONS)},'annotation_credit':{'type':'null'},
        'cross_arm_uncertainty':{'const':'not_implemented_by_single_arm_operation'}})


def _sqrt(value):
    n,d=isqrt(value.numerator),isqrt(value.denominator)
    if n*n==value.numerator and d*d==value.denominator:
        exact=Fraction(n,d);return _float(exact),_exact(exact)
    with localcontext() as context:
        context.prec=65
        root=(Decimal(value.numerator)/Decimal(value.denominator)).sqrt()
        return _float(root),None


def populate_product_coupling(extraction):
    """Populate source-specific endpoint and first-order uncertainty components."""
    validate_product_coupling_extraction(extraction)
    data=deepcopy(extraction);quantities=data['quantities'];origins=data['input_origins']
    p,h=(quantities[role] for role in ('product','cofactor'))
    def dependencies(item):return [] if item is None else item['dependency_keys']
    keys=list(dict.fromkeys([*dependencies(p),*dependencies(h)]))
    pair_key=identity('product_coupling_pair_contribution',{'dependencies':keys})
    nu=data['nu_cofactor_per_product'];nu_value=None if nu['exact_value'] is None else _q(nu['exact_value'])
    model_keys=[] if nu['model_key'] is None else [nu['model_key']]
    eta_key=identity('product_coupling_stoichiometric_contribution',{'pair':pair_key,'models':model_keys})

    def cell(name,value=None,*,conditional=None,reasons=(),unit=None,interpretation='deterministic_reexpression',
             origin='derived',input_origins=None,input_keys=(),models=(),contribution=None,
             assumptions=(),relation='point',physical='not_applicable',native=None,root=False):
        exact=None if value is None else _exact(value);floating=None if value is None else _float(value)
        ce=None if conditional is None else _exact(conditional);cf=None if conditional is None else _float(conditional)
        if root:
            if value is not None:floating,exact=_sqrt(value)
            if conditional is not None:cf,ce=_sqrt(conditional)
        why=list(dict.fromkeys(reasons))
        if value is not None and floating is None or conditional is not None and cf is None:why.append('numerical_model_range')
        number=None if native is None else native['number'];native_unit=None if native is None else native['unit']
        return {'value':floating,'exact_value':exact,'conditional_value':cf,'conditional_exact_value':ce,
            'source_value':None if number is None else number['native_value'],
            'source_exact_value':None if number is None else deepcopy(number['native_exact_value']),
            'source_unit':None if native_unit is None else native_unit['raw_unit'],
            'native_measurement_semantics':None if native is None else native['measurement_semantics']['value'],
            'status':'populated' if floating is not None else 'conditional' if cf is not None else 'unavailable',
            'interpretation':interpretation,'origin':origin,'input_origins':list(dict.fromkeys(origins if input_origins is None else input_origins)),
            'relation':relation,'unit':unit,'formula':FORMULAS[name],'meaning':MEANINGS[name],
            'input_measurement_keys':list(dict.fromkeys(input_keys)),'input_model_keys':list(dict.fromkeys(models)),
            'contribution_key':contribution or identity('product_coupling_unavailable_component',{'component':name,'keys':list(input_keys)}),
            'physical_fraction_status':physical,'assumptions':list(dict.fromkeys(assumptions)),
            'unavailable_reasons':list(dict.fromkeys(why))}

    cells={}
    values={}
    native_reasons={}
    for role,name in (('product','reported_product_activity'),('cofactor','reported_cofactor_activity'),('reported_coupling','reported_coupling_percent')):
        item=quantities[role];number=None if item is None else item['number'];unit=None if item is None else item['unit']
        reason=['quantity_not_supplied'] if item is None else ['source_number_not_supplied'] if number is None else []
        if number is not None and number['capability_reason']:reason.append(number['capability_reason'])
        if item is not None and unit is None:reason.append('source_unit_not_supplied')
        elif unit is not None and unit['unavailable_reason']:reason.append(unit['unavailable_reason'])
        value=None if reason or item['canonical_exact_value'] is None else _q(item['canonical_exact_value'])
        values[role]=value;native_reasons[role]=reason
        key=None if number is None else number['measurement_key']
        cells[name]=cell(name,value,reasons=reason,unit=None if item is None else item['canonical_unit'],
            interpretation='native_report',origin=number['origin'] if number else 'derived',
            input_keys=dependencies(item),contribution=key,relation=number['relation'] if number else 'unresolved',native=item)

    arithmetic=[];semantic=[]
    expected_roles={'product':'product_formation','cofactor':'cofactor_consumption'}
    for role in ('product','cofactor'):
        item=quantities[role];arithmetic.extend(native_reasons[role])
        if item is None:continue
        number=item['number']
        if item['canonical_unit'] not in (None,'per_min'):arithmetic.append('unsupported_rate_dimension_for_coupling')
        if number is not None and number['relation'] in ('lt','le','gt','ge'):arithmetic.append('bounded_ratio_calculation_unimplemented')
        meaning=item['measurement_semantics']['value']
        if meaning!='reported_point':
            (arithmetic if meaning in ('reported_nondetection','reported_negligible','conflicting') else semantic).append(role+'_measurement_semantics_'+meaning)
        endpoint=item['endpoint_role']['value']
        if endpoint!=expected_roles[role]:
            (arithmetic if endpoint not in ('unknown',) else semantic).append(role+'_endpoint_role_'+endpoint)
    if p is not None and h is not None:
        if (p['number'] is not None and h['number'] is not None and p['number']['measurement_key']==h['number']['measurement_key']
                or p['physical_identity_key'] is not None and p['physical_identity_key']==h['physical_identity_key']):
            arithmetic.append('reused_source_observation')
    P,H=values['product'],values['cofactor']
    if H==0:arithmetic.append('zero_cofactor_denominator')
    rho=None if arithmetic or P is None or H is None else P/H
    cells['product_per_cofactor']=cell('product_per_cofactor',rho if not semantic else None,
        conditional=rho if semantic else None,reasons=[*arithmetic,*semantic],unit='product_per_cofactor',
        interpretation='conditional_descriptive_ratio' if semantic else 'descriptive_ratio',
        input_keys=keys,contribution=pair_key,assumptions=['selected_source_role_interpretations'])
    reconstructed=None if rho is None else rho*H
    cells['reconstructed_product_activity']=cell('reconstructed_product_activity',reconstructed if not semantic else None,
        conditional=reconstructed if semantic else None,reasons=[*arithmetic,*semantic],unit='per_min',
        interpretation='dependent_reconstruction',input_keys=keys,
        contribution=None if p is None or p['number'] is None else p['number']['measurement_key'],
        assumptions=['same_operand_reconstruction_reuses_original_product_measurement'])

    eta_block=[];eta_cond=list(semantic)
    if nu_value is None:eta_block.append('nu_model_not_supplied')
    elif nu_value<=0:eta_block.append('nonpositive_stoichiometric_model')
    if nu['status']=='conflicting':eta_block.append('nu_model_conflicting')
    if nu['status']=='uncertain_model':eta_cond.append('uncertain_nu_uncertainty_propagation_unimplemented')
    wanted={'source_pairing':'author_assigned','same_molecule':'same','same_preparation':'same',
        'normalization':'compatible','conditions':'matched','product_identity':'chemically_identified'}
    for name,expected in wanted.items():
        value=data['relationships'][name]['value']
        if value!=expected:
            (eta_cond if value=='unknown' else eta_block).append('eta_relationship_'+name+'_'+value)
    if p is not None and h is not None:
        a,b=(item['normalization']['value'] for item in (p,h))
        if a in ('unknown','conflicting') or b in ('unknown','conflicting'):
            for role in ('product','cofactor'):
                status=quantities[role]['normalization']['value']
                if status in ('unknown','conflicting'):
                    (eta_block if status=='conflicting' else eta_cond).append(role+'_normalization_'+status)
        elif a!=b:eta_block.append('incompatible_normalization_bases')
    if H is not None and H<=0:eta_block.append('nonpositive_cofactor_rate_for_physical_fraction')
    eta=None if rho is None or eta_block else nu_value*rho
    physical='unresolved'
    if eta is not None:
        physical='within_reported_model_domain' if 0<=eta<=1 else 'outside_reported_model_domain'
        if physical=='outside_reported_model_domain':eta_cond.append('outside_physical_fraction_range')
    assumptions=['fixed_stoichiometric_reaction_account_model']
    if any(reason.endswith('_unknown') for reason in eta_cond):
        assumptions.append('unknown_scientific_relationships_assumed_compatible_only_for_conditional_arithmetic')
    if nu['status']=='uncertain_model':assumptions.append('supplied_nu_estimate_held_fixed_for_conditional_arithmetic')
    if physical=='outside_reported_model_domain':assumptions.append('unconstrained_displayed_estimate_is_not_a_physical_fraction_outside_zero_one')
    eta_reasons=[*arithmetic,*eta_block,*eta_cond]
    for name,multiplier in (('productive_fraction',1),('calculated_coupling_percent',100)):
        proposed=None if eta is None else multiplier*eta
        cells[name]=cell(name,proposed if not eta_cond else None,conditional=proposed if eta_cond else None,
            reasons=eta_reasons,unit='fraction' if multiplier==1 else 'percent',origin='proposed',
            interpretation='conditional_physical_fraction_estimate' if eta_cond else 'physical_fraction_estimate',
            input_keys=keys,models=model_keys,contribution=eta_key,assumptions=assumptions,physical=physical)
    report=quantities['reported_coupling'];reported=values['reported_coupling'];report_reasons=list(native_reasons['reported_coupling'])
    if report is not None and (report['number'] is None or report['number']['relation']!='point'
            or report['measurement_semantics']['value']!='reported_point' or report['endpoint_role']['value']!='coupling_fraction'):
        report_reasons.append('reported_coupling_not_a_point')
    difference=None if eta is None or reported is None or report_reasons else 100*eta-reported
    cells['displayed_coupling_difference_pp']=cell('displayed_coupling_difference_pp',difference if not eta_cond else None,
        conditional=difference if eta_cond else None,reasons=[*eta_reasons,*report_reasons],unit='percentage_point',
        input_keys=[*keys,*dependencies(report)],models=model_keys,contribution=eta_key,
        interpretation='deterministic_reexpression',assumptions=assumptions,physical=physical)

    covariance=data['covariance'];cov_reasons=[] if covariance['unavailable_reason'] is None else [covariance['unavailable_reason']]
    cov_origins=list(origins)+([] if covariance['origin'] is None else [covariance['origin']])
    variance=None
    if rho is not None and not cov_reasons:
        C=[[_q(x) for x in row] for row in covariance['matrix_exact']]
        J=(1/H,-P/H**2)
        variance=sum(J[i]*C[i][j]*J[j] for i in range(2) for j in range(2))
    uncertainty_key=identity('product_coupling_uncertainty_contribution',{'pair':pair_key,'source_ref':covariance['source_ref']})
    cells['product_per_cofactor_variance']=cell('product_per_cofactor_variance',variance if not semantic else None,
        conditional=variance if semantic else None,reasons=[*arithmetic,*semantic,*cov_reasons],unit='product_per_cofactor_squared',
        interpretation='conditional_first_order_uncertainty' if semantic else 'first_order_uncertainty',origin='proposed',
        input_origins=cov_origins,input_keys=keys,contribution=uncertainty_key,
        assumptions=['first_order_delta_propagation_for_selected_rate_estimates'])
    eta_variance=None if variance is None or eta is None else nu_value**2*variance
    variance_assumptions=[*assumptions,'first_order_delta_propagation_for_selected_rate_estimates']
    if nu['status']=='uncertain_model':variance_assumptions.append('conditional_variance_term_excludes_nu_variance_and_covariance')
    for name,root in (('productive_fraction_variance',False),('productive_fraction_standard_uncertainty',True)):
        cells[name]=cell(name,eta_variance if not eta_cond else None,conditional=eta_variance if eta_cond else None,
            reasons=[*eta_reasons,*cov_reasons],unit='fraction' if root else 'fraction_squared',
            interpretation='conditional_first_order_uncertainty' if eta_cond else 'first_order_uncertainty',origin='proposed',
            input_origins=cov_origins,input_keys=keys,models=model_keys,
            contribution=uncertainty_key,assumptions=variance_assumptions,physical=physical,root=root)
    result={'version':VERSION,'axis':'A105','section':'product_coupling','extraction':data,'cells':cells,
        'qualifications':list(QUALIFICATIONS),'annotation_credit':None,'cross_arm_uncertainty':'not_implemented_by_single_arm_operation'}
    validate_schema(result,product_coupling_sheet_schema())
    return result


__all__=['VERSION','COMPONENTS','FORMULAS','MEANINGS','REASONS','ASSUMPTIONS','QUALIFICATIONS',
    'product_coupling_cell_schema','product_coupling_sheet_schema','populate_product_coupling']
