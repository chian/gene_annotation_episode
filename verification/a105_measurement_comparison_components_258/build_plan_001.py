"""Generate review-only schemas/examples. No production implementation or scientific execution."""
from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import json, hashlib
import jsonschema

OUT=Path(__file__).parent
T={'type':'string','minLength':1}; NULL={'type':'null'}
def O(p): return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def E(*v): return {'enum':list(v)}
def A(s,unique=False): return {'type':'array','items':deepcopy(s),**({'uniqueItems':True} if unique else {})}
def N(s): return {'anyOf':[deepcopy(s),NULL]}
def R(name): return {'$ref':'#/$defs/'+name}
def q(v):
 f=Fraction(v); return {'numerator':str(f.numerator),'denominator':str(f.denominator)}
REF={'type':'string','pattern':'^[a-z][a-z_]*_[a-f0-9]{24,64}$'}
D={}
D['exact']=O({'numerator':{'type':'string','pattern':'^-?[0-9]+$'},'denominator':{'type':'string','pattern':'^[1-9][0-9]*$'}})
D['witness']=O({'source_ref':REF,'representation':E('original','text'),'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1},'quote':T})
D['retained_witness']=O({**D['witness']['properties'],'artifact_ref':REF})
D['number_selector']=O({'witness':R('witness'),'number_start':{'type':'integer','minimum':0},'number_end':{'type':'integer','minimum':1}})
STATUSES=('supported','stipulated_sensitivity','unknown','conflicting')
def M(values,enriched=False): return O({'value':E(*values),'witnesses':A(R('retained_witness' if enriched else 'witness'))})
D['model_meaning']=M(STATUSES)
D['retained_model_meaning']=M(STATUSES,True)
D['unit_definition']=O({'kind':{'const':'source_defined_rate_unit'},'witness':R('witness'),'definition':O({**{x:R('witness') for x in ('bridge','clause','amount_unit','time_unit','endpoint','endpoint_entity','definition_entity')},'amount':R('number_selector')})})
D['unit_selection']={'anyOf':[R('witness'),R('unit_definition'),NULL]}
SUBJECT=('organism','genotype','molecule','construct','expression_host','arrangement')
ASSAY=('assay','preparation','purification_reconstitution','partners','substrates','conditions','direct_endpoint','inferred_quantity','denominator','time_window','fit_basis','sampling_unit','intended_change','additional_differences','calibration','blank','active_fraction','purity')
KINDS=('apparent_specific_activity','specific_activity','fixed_condition_rate','turnover_rate','terminal_conversion','affinity','extinction_coefficient','unknown','conflicting')
SCALES=('direct_rate','fitted_asymptote','reported_mean','terminal_amount','parameter_estimate','unknown','conflicting')
SEM=('reported_point_estimate','reported_nondetection','reported_negligible','unknown','conflicting')
QUAL=('reported_point','rounded_after_fit','source_qualified_approximate','unknown','conflicting')
NORMS=('protein_mass','assayed_molecule_amount','active_molecule_amount','reaction_volume','unnormalized_amount','extinction_unit','other','unknown','conflicting')
REPETITION=('independent_preparations','paired_units','technical_repeats','timepoints','unspecified','unknown','conflicting')
D['uncertainty_selection']=O({'statistic':M(('sd','sem','ci','unspecified','unreported')),'magnitude':N(R('number_selector')),'interval':N(O({'witness':R('witness'),'lower_start':{'type':'integer','minimum':0},'lower_end':{'type':'integer','minimum':1},'upper_start':{'type':'integer','minimum':0},'upper_end':{'type':'integer','minimum':1}})),'confidence_level':N(R('witness')),'unit':D['unit_selection'],'unit_relationship':M(('same_as_estimate','explicit_unit','unknown','conflicting')),'count':N(R('number_selector')),'repetition_basis':M(REPETITION),'estimate_basis':M(('fit_to_averaged_curve','between_fitted_estimates','within_curve_points','unknown','conflicting'))})
D['quantity_selection']=O({'layout':E('table','labelled_record'),'record':N(R('witness')),'number':N(R('number_selector')),'row_label':N(R('witness')),'quantity_label':N(R('witness')),'unit':R('unit_selection'),'quantity_kind':M(KINDS),'estimator_scale':M(SCALES),'semantics':M(SEM),'qualification':M(QUAL),'normalization':M(NORMS),'subject':O({x:N(R('witness')) for x in SUBJECT}),'assay':O({x:N(R('witness')) for x in ASSAY}),'physical_identity':N(R('witness')),'dependency_witnesses':A(R('witness')),'uncertainty':R('uncertainty_selection')})
REL={
 'construct':('same_construct_supported','intended_variant','different','unknown','conflicting'),
 'preparation':('same_preparation_supported','different_preparations_supported','unknown','conflicting'),
 'preparation_target':('same_preparation_quantity','same_population_estimand_supported','incompatible','unknown','conflicting'),
 'protocol':('matched_except_intended_change','additional_differences','unknown','conflicting'),
 'endpoint':('same_quantity','fixed_reaction_conversion','complementary','incompatible','unknown','conflicting'),
 'denominator':('same_basis_supported','different','unknown','conflicting'),
 'functional_bearing':('same_quantitative_assertion','existence_only','partner_dependence_only','complementary','unknown','conflicting'),
 'attribution':('isolated_supported','mixed_contributors_identified','unresolved','unknown','conflicting'),
 'sampling':('repeated_representation','shared_physical_estimate','paired_observations_supported','independent_preparations_supported','independence_not_established','unknown','conflicting'),
 'systematic_coverage':('included_in_selected_covariance','identified_unresolved','not_established','unknown','conflicting'),
 'left_validity':('endpoint_quantification_supported','identified_unresolved_interference','corrected_endpoint_supported','unknown','conflicting'),
 'right_validity':('endpoint_quantification_supported','identified_unresolved_interference','corrected_endpoint_supported','unknown','conflicting')}
D['relationships']=O({name:M(values) for name,values in REL.items()})
D['retained_relationships']=O({name:M(values,True) for name,values in REL.items()})
D['coefficient']=O({'origin':E('explicit_source_token','implicit_unit_coefficient'),'number':N(R('number_selector')),'implicit_value':N(O({'numerator':{'const':'1'},'denominator':{'const':'1'}})),'support':A(R('witness'))})
D['conversion']=O({'kind':E('identity','fixed_reaction_scale','unresolved'),'direction':M(('same_direction_supported','opposite_direction','unknown','conflicting')),'support_status':M(('supported','unknown','conflicting')),'reaction':N(R('witness')),'endpoint_species':N(R('witness')),'common_species':N(R('witness')),'endpoint_coefficient':N(R('coefficient')),'common_coefficient':N(R('coefficient'))})
ROLES=('left','right','epsilon_signal','epsilon_nuisance','nuisance')
COMPONENTS={
 'native_left':('native_estimate','Native selected left report'),
 'native_right':('native_estimate','Native selected right report'),
 'converted_left':('c_left*x_left','Left report expressed on supported common endpoint scale'),
 'converted_right':('c_right*x_right','Right report expressed on supported common endpoint scale'),
 'protocol_difference':('L-R','Signed difference of linked source protocol estimates'),
 'protocol_ratio':('L/R','Descriptive ratio of linked source protocol estimates'),
 'protocol_log_ratio':('ln(L)-ln(R)','Dependent log representation of protocol comparison'),
 'common_difference':('L-R','Difference under declared common estimand model'),
 'common_ratio':('L/R','Ratio under declared common estimand model'),
 'common_log_ratio':('ln(L)-ln(R)','Dependent log representation of common comparison'),
 'difference_variance':('c_left^2*Cll+c_right^2*Crr-2*c_left*c_right*Clr','Covariance aware discrepancy variance'),
 'difference_standard_uncertainty':('sqrt(V_D)','Uncertainty of the same discrepancy'),
 'standardized_difference':('D/sqrt(V_D)','Signed standardized discrepancy with stated variance meaning'),
 'squared_standardized_difference':('D^2/V_D','Squared standardized discrepancy from the same measurements'),
 'weight_left':('(V_R-C_LR)/(V_L+V_R-2*C_LR)','Generalized least squares left weight'),
 'weight_right':('(V_L-C_LR)/(V_L+V_R-2*C_LR)','Generalized least squares right weight'),
 'combined_estimate':('w_L*L+w_R*R','Common unbiased quantity estimate under declared covariance model'),
 'combined_variance':('(V_L*V_R-C_LR^2)/(V_L+V_R-2*C_LR)','Variance of the same weighted common estimate'),
 'combined_standard_uncertainty':('sqrt(V_combined)','Uncertainty of the same combined estimate'),
 'spectral_multiplier':('epsilon_nuisance/epsilon_signal','Relative signed mixture sensitivity magnitude'),
 'spectral_multiplier_variance':('J_alpha*C_epsilon*J_alpha_transpose','First order multiplier variance'),
 'observed_interference':('s*alpha*f','Observed nuisance contribution on applicable selected estimate scale'),
 'corrected_estimate':('y-s*alpha*f','Measured corrected quantity under applicable estimate scale model'),
 'corrected_estimate_variance':('J_h*C_y_epsilon_f*J_h_transpose','First order corrected quantity variance'),
 'required_interference_scenario':('y-H','Required signed observed mixture contribution if true quantity equals H'),
 'required_nuisance_equivalent_scenario':('(y-H)/(s*alpha)','Required nuisance equivalent on selected report scale under two explicit stipulations')}
CELL_NAMES=tuple(COMPONENTS)
D['optical']=O({'signal_role':E('left','right'),'observation_equation':{'const':'y=h+s*alpha*f'},'nuisance_sign':E(-1,1),'sign_support':A(R('witness')),'raw_optical_relation':R('model_meaning'),'coefficient_applicability':R('model_meaning'),'estimate_scale_applicability':R('model_meaning'),'nuisance_quantity_linkage':R('model_meaning'),'scenario':N(O({'kind':{'const':'required_interference_on_selected_report_scale'},'anchor_role':E('left','right'),'common_rate_equality':R('model_meaning'),'linear_mixture_on_estimate_scale':R('model_meaning')}))})
D['common_model']=O({'kind':{'const':'common_unbiased_quantity'},'applicability':R('model_meaning'),'variance_interpretation':E('known_joint_estimator_covariance','estimated_joint_estimator_covariance','unknown'),'combination':E('generalized_least_squares','not_requested')})
D['selection']=O({'version':{'const':'a105_measurement_comparison_selection_v1'},'source_ref':REF,'source_kind':E('primary_source','synthetic_fixture'),'assertion':O({'question':E('activity_existence','partner_dependence','quantitative_activity','coupling_compatibility'),'molecule':N(R('witness')),'functional_assertion':N(R('witness'))}),'quantities':O({role:N(R('quantity_selection')) for role in ROLES}),'relationships':R('relationships'),'common_quantity':O({'label':N(R('witness')),'unit':E('umol/min/mg','umol/min','uM/min','per_min','unknown'),'left_conversion':R('conversion'),'right_conversion':R('conversion')}),'common_model':N(R('common_model')),'optical':N(R('optical')),'covariance_source_refs':A(REF,True),'requested_cells':A(E(*CELL_NAMES),True)})
REASONS={
 'source':('quantity_not_selected','source_number_unreported','source_unit_unreported','native_nondetection_not_point','native_negligible_not_point','source_semantics_unknown','source_semantics_conflicting','reported_uncertainty_not_joint_covariance','nuisance_quantity_unmeasured','covariance_not_supplied','joint_covariance_incomplete','covariance_status_unknown'),
 'relationship':('construct_not_common','preparation_target_unknown','preparation_target_conflicting','protocols_not_matched','endpoint_conversion_unknown','endpoint_conversion_conflicting','endpoint_incompatible','denominator_not_common','functional_resolution_not_quantitative','attribution_unresolved','validity_unresolved','duplicate_representation_not_replication','shared_estimate_not_replication','common_model_not_selected','common_model_unknown','common_model_conflicting','optical_model_unknown','optical_model_conflicting','estimate_scale_model_unknown','estimate_scale_model_conflicting','coefficient_applicability_unknown','coefficient_applicability_conflicting','nuisance_linkage_unknown','nuisance_linkage_conflicting','scenario_not_selected','scenario_stipulations_unresolved','variance_meaning_mismatch','common_systematic_error_not_assessed'),
 'implementation':('unsupported_unit','bounded_arithmetic_unimplemented','range_arithmetic_unimplemented','unresolved_native_qualification','opposite_direction_conversion_unimplemented','uncertain_conversion_unimplemented','numerical_model_range'),
 'domain':('zero_denominator','positive_values_required_for_log','nonzero_spectral_signal_required','positive_discrepancy_variance_required','degenerate_equal_estimate_covariance','inconsistent_deterministic_constraint','covariance_invalid_shape','covariance_not_symmetric','covariance_not_positive_semidefinite','covariance_owner_unit_dependency_mismatch','covariance_overlap_conflict','physical_owner_value_conflict')}
for family,values in REASONS.items(): D[family+'_reasons']=A(E(*values),True)
D['reasons']=O({family:R(family+'_reasons') for family in REASONS})
D['quantity_value']=O({'role':E(*ROLES),'native_token':N(T),'native_value':{'type':['number','null']},'native_exact':N(R('exact')),'canonical_value':{'type':['number','null']},'canonical_exact':N(R('exact')),'canonical_unit':E('umol/min/mg','umol/min','uM/min','per_min','mM^-1cm^-1',None),'relation':E('point','lt','le','gt','ge','range','unresolved'),'approximate':{'type':'boolean'},'estimator_scale':E(*SCALES),'quantity_kind':E(*KINDS),'semantics':E(*SEM),'normalization':E(*NORMS),'origin':E('reported','derived','synthetic'),'owner_key':T,'physical_owner_key':N(T),'dependency_keys':A(T,True),'source_locations':A(R('retained_witness')),'reasons':R('reasons')})
D['covariance_block']=O({'source_ref':REF,'artifact_ref':REF,'roles':A(E(*ROLES),True),'owner_keys':A(T),'units':A(T),'dependency_keys':A(A(T,True)),'matrix_exact':N(A(A(R('exact')))),'basis':{'const':'joint_covariance_of_selected_estimates'},'variance_status':E('known','estimated','unknown'),'origin':E('reported','derived','synthetic'),'systematic_coverage':E('included_as_declared','not_established','identified_unresolved'),'derivation':E('reported_estimator_covariance','exact_linear_transform','estimated_from_observations','synthetic_model')})
D['retained_number']=O({'selector':O({**D['number_selector']['properties'],'witness':R('retained_witness')}),'raw_token':T,'native_exact':N(R('exact')),'relation':E('point','lt','le','gt','ge','range','unresolved'),'approximate':{'type':'boolean'},'measurement_key':T})
D['retained_quantity']=O({'selection':R('quantity_selection'),'number':N(R('retained_number')),'witnesses':A(R('retained_witness')),'count_reading':N(O({'raw_token':T,'exact_count':{'type':['integer','null'],'minimum':1},'status':E('exact','qualified','range_or_alternatives','unsupported','not_positive'),'repetition_basis':E(*REPETITION)})),'reported_uncertainty':O({'statistic':E('sd','sem','ci','unspecified','unreported'),'magnitude_exact':N(R('exact')),'interval_exact':N(A(R('exact'))),'confidence_level_exact':N(R('exact')),'unit':N(T),'meaning':{'const':'reported_spread_not_joint_estimator_covariance'}}),'value':R('quantity_value')})
D['conversion_value']=O({'kind':E('identity','fixed_reaction_scale','unresolved'),'multiplier_exact':N(R('exact')),'status':E('supported','unknown','conflicting'),'model_key':T,'source_witnesses':A(R('retained_witness'))})
D['calculation_inputs']=O({'version':{'const':'a105_measurement_comparison_calculation_inputs_v1'},'selection':R('selection'),'quantities':O({role:N(R('quantity_value')) for role in ROLES}),'conversions':O({role:R('conversion_value') for role in ('left','right')}),'relationships':R('retained_relationships'),'covariance_blocks':A(R('covariance_block')),'assertion_key':T,'contribution_key':T,'source_artifacts':A(O({'source_ref':REF,'artifact_ref':REF,'representation':E('original','text')}))})
D['extraction']=O({'version':{'const':'a105_measurement_comparison_extraction_v1'},'selection':R('selection'),'quantities':O({role:N(R('retained_quantity')) for role in ROLES}),'relationships':R('retained_relationships'),'conversions':O({role:R('conversion_value') for role in ('left','right')}),'covariance_blocks':A(R('covariance_block')),'source_refs':A(REF,True),'source_artifacts':A(O({'source_ref':REF,'artifact_ref':REF,'representation':E('original','text')})),'dependency_fingerprints':A(O({'module':T,'sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'}}))})
INTERPRETATIONS=('native_report','supported_reexpression','descriptive_protocol_comparison','common_estimand_comparison','known_covariance_standardization','estimated_covariance_plugin_standardization','known_covariance_common_estimate','estimated_covariance_plugin_common_estimate','spectral_sensitivity','supported_estimate_scale_correction','first_order_known_input_covariance','first_order_estimated_input_covariance','stipulated_report_scale_scenario','unavailable')
D['cell']=O({'component':E(*CELL_NAMES),'value':{'type':['number','null']},'exact_value':N(R('exact')),'conditional_value':{'type':['number','null']},'conditional_exact_value':N(R('exact')),'status':E('populated','conditional_scenario','unavailable'),'unit':N(T),'relation':E('point','lt','le','gt','ge','range','unresolved'),'approximate':{'type':'boolean'},'interpretation':E(*INTERPRETATIONS),'formula':E(*(v[0] for v in COMPONENTS.values())),'meaning_code':E(*CELL_NAMES),'origin':E('reported','derived','synthetic','proposed'),'input_origins':A(E('reported','derived','synthetic','proposed'),True),'operand_roles':A(E(*ROLES),True),'operand_keys':A(T,True),'model_keys':A(T,True),'contribution_key':T,'uncertainty':O({'covariance_source_refs':A(REF,True),'variance_status':E('not_selected','known','estimated','unknown'),'scope':E('not_applicable','selected_estimator_covariance','first_order_operand_propagation'),'sampling_distribution':{'const':'not_assumed'}}),'reasons':R('reasons')})
LIMITS=('standalone_components_not_selected_integration','same_estimate_ratio_log_difference_are_dependent','agreement_does_not_detect_shared_bias','source_positive_matched_covariance_case_still_open','general_A105_adequacy_unfinished','no_target_transfer_or_W05','corrected_quantity_not_automatically_substituted_into_common_pair','unknown_systematics_not_set_to_zero')
D['sheet']=O({'version':{'const':'a105_measurement_comparison_sheet_v1'},'axis':{'const':'A105'},'section':{'const':'measurement_comparison_validity'},'assertion_key':T,'contribution_key':T,'cells':A(R('cell')),'relationship_meanings':O({k:E(*v) for k,v in REL.items()}),'estimate_bindings':A(O({'role':E(*ROLES),'owner_key':T,'physical_owner_key':N(T),'dependency_keys':A(T,True),'unit':N(T),'estimator_scale':E(*SCALES)})),'dependence':A(O({'roles':A(E(*ROLES),True),'relation':E('shared_primitive','repeated_representation','shared_physical_estimate','sampling_unknown','paired_observations_supported','independent_preparations_supported','complementary_endpoint')})),'assumptions':A(E('common_unbiased_quantity_model','fixed_reaction_conversion','linear_mixture_on_selected_estimate_scale','common_rate_equality_stipulated','linear_estimate_scale_mapping_stipulated','first_order_covariance_propagation','estimated_weights_treated_as_plugin','no_reference_distribution_assumed'),True),'annotation_credit':NULL,'remaining_limits':A(E(*LIMITS),True)})
# A covariance source uses actual numeric JSON tokens; extraction converts them exactly.
D['covariance_document']=O({'version':{'const':'a105_measurement_comparison_covariance_v1'},'roles':A(E(*ROLES),True),'owner_keys':A(T),'units':A(T),'dependency_keys':A(A(T,True)),'covariance':N(A(A({'type':'number'}))),'basis':{'const':'joint_covariance_of_selected_estimates'},'variance_status':E('known','estimated','unknown'),'origin':E('reported','derived','synthetic'),'systematic_coverage':E('included_as_declared','not_established','identified_unresolved'),'derivation':E('reported_estimator_covariance','exact_linear_transform','estimated_from_observations','synthetic_model')})

def schema(name):
 # Every resource is independently resolvable. No embedded foreign $id or external reference.
 reachable=set()
 def collect(x):
  if isinstance(x,dict):
   if '$ref' in x:
    ref=x['$ref'].removeprefix('#/$defs/')
    if ref not in reachable: reachable.add(ref); collect(D[ref])
   for k,v in x.items():
    if k!='$ref':collect(v)
  elif isinstance(x,list):
   for v in x:collect(v)
 collect(D[name]); body=deepcopy(D[name])
 return {'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:a105:measurement-comparison:258:plan001:'+name,**body,'$defs':{k:deepcopy(D[k]) for k in sorted(reachable)}}
for name in ('selection','extraction','calculation_inputs','sheet','covariance_document'):
 result=schema(name); jsonschema.Draft202012Validator.check_schema(result)
 (OUT/(name.upper()+'_SCHEMA_001.json')).write_text(json.dumps(result,indent=2)+'\n')
(OUT/'COMPONENT_FORMULAS_AND_MEANINGS_001.json').write_text(json.dumps({k:{'formula':v[0],'meaning':v[1]} for k,v in COMPONENTS.items()},indent=2)+'\n')
(OUT/'PLAN_DOMAINS_001.json').write_text(json.dumps({'roles':ROLES,'relationships':REL,'reasons':REASONS,'interpretations':INTERPRETATIONS,'limits':LIMITS},indent=2)+'\n')
print('Five standalone draft schemas generated and metaschema checked; no component implementation executed.')
# Additive refinement before release: readout decomposition is not molecular attribution.
for name in ('left_readout_isolation','right_readout_isolation'):
 REL[name]=('isolated_signal_supported','mixed_optical_contributions','unknown','conflicting')
D['relationships']=O({name:M(values) for name,values in REL.items()})
D['retained_relationships']=O({name:M(values,True) for name,values in REL.items()})
D['sheet']['properties']['relationship_meanings']=O({k:E(*v) for k,v in REL.items()})
# Component/formula bindings and populated-versus-scenario states are also structural.
D['cell']['allOf']=[{'if':{'properties':{'component':{'const':k}}},'then':{'properties':{'formula':{'const':v[0]},'meaning_code':{'const':k}}}} for k,v in COMPONENTS.items()]
D['cell']['allOf'] += [
 {'if':{'properties':{'status':{'const':'populated'}}},'then':{'properties':{'value':{'type':'number'},'conditional_value':NULL,'conditional_exact_value':NULL}}},
 {'if':{'properties':{'status':{'const':'conditional_scenario'}}},'then':{'properties':{'value':NULL,'exact_value':NULL,'conditional_value':{'type':'number'}}}},
 {'if':{'properties':{'status':{'const':'unavailable'}}},'then':{'properties':{x:NULL for x in ('value','exact_value','conditional_value','conditional_exact_value')}}}]
for name in ('selection','extraction','calculation_inputs','sheet','covariance_document'):
 result=schema(name); jsonschema.Draft202012Validator.check_schema(result)
 (OUT/(name.upper()+'_SCHEMA_001.json')).write_text(json.dumps(result,indent=2)+'\n')
(OUT/'PLAN_DOMAINS_001.json').write_text(json.dumps({'roles':ROLES,'relationships':REL,'reasons':REASONS,'interpretations':INTERPRETATIONS,'limits':LIMITS},indent=2)+'\n')
# Invalid covariance affects dependent cells, preserving native and descriptive results.
REASONS['domain'] += ('covariance_json_invalid','covariance_basis_status_invalid','covariance_nonfinite_numeric','covariance_estimate_owner_unavailable')
D['domain_reasons']=A(E(*REASONS['domain']),True)
D['covariance_block']['properties'].update(status=E('available','unavailable'),reasons=R('reasons'),raw_document_utf8=N(T))
D['covariance_block']['required']=list(D['covariance_block']['properties'])
for name in ('selection','extraction','calculation_inputs','sheet','covariance_document'):
 result=schema(name); jsonschema.Draft202012Validator.check_schema(result)
 (OUT/(name.upper()+'_SCHEMA_001.json')).write_text(json.dumps(result,indent=2)+'\n')
(OUT/'PLAN_DOMAINS_001.json').write_text(json.dumps({'roles':ROLES,'relationships':REL,'reasons':REASONS,'interpretations':INTERPRETATIONS,'limits':LIMITS},indent=2)+'\n')
