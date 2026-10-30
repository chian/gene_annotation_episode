"""Selected endpoint sections with scoped immutable scientific returns.

Only population reads original science and computes. Saved reads authenticate
original schemas, rows and selected ownership without reacquisition or fitting.
Constructors and discovery never install tables. No continuation policy lives here.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .communication import plain
from .domain import ContractError, canonical, identity, validate_schema
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = 'literature.experimental.figure'
VERSION = 'literature_figure_endpoint_signal_record_v1'
POPULATION = 'literature_figure_endpoint_signal_population_v1'
NAMESPACE = 'literature_endpoint_signal_cells'
REQUESTED = 'requested_endpoint_signal_components'
VIEW = 'endpoint_signal_components'
SCOPE = 'source_endpoint_signal_contribution'
COMPONENTS = ('total_amplitude', 'corrected_amplitude', 'additional_amplitude',
    'retained_fraction', 'additional_fraction', 'total_amplitude_variance',
    'corrected_amplitude_variance', 'additional_amplitude_variance',
    'retained_fraction_variance', 'additional_fraction_variance')

# Exact detached v1 metadata literals are inserted below. No scientific/current
# schema factory is called when the registered form compiler checks this type.
ENDPOINT_SIGNAL_CELLS_SCHEMA_V1 = json.loads('{"type":"array","items":{"type":"object","properties":{"component":{"enum":["total_amplitude","corrected_amplitude","additional_amplitude","retained_fraction","additional_fraction","total_amplitude_variance","corrected_amplitude_variance","additional_amplitude_variance","retained_fraction_variance","additional_fraction_variance"]},"value":{"anyOf":[{"type":"number"},{"type":"null"}]},"conditional_value":{"anyOf":[{"type":"number"},{"type":"null"}]},"exact_value":{"anyOf":[{"type":"object","properties":{"numerator":{"type":"string","pattern":"^-?[0-9]+$"},"denominator":{"type":"string","pattern":"^[1-9][0-9]*$"}},"required":["numerator","denominator"],"additionalProperties":false},{"type":"null"}]},"conditional_exact_value":{"anyOf":[{"type":"object","properties":{"numerator":{"type":"string","pattern":"^-?[0-9]+$"},"denominator":{"type":"string","pattern":"^[1-9][0-9]*$"}},"required":["numerator","denominator"],"additionalProperties":false},{"type":"null"}]},"lower":{"anyOf":[{"type":"number"},{"type":"null"}]},"upper":{"anyOf":[{"type":"number"},{"type":"null"}]},"exact_lower":{"anyOf":[{"type":"object","properties":{"numerator":{"type":"string","pattern":"^-?[0-9]+$"},"denominator":{"type":"string","pattern":"^[1-9][0-9]*$"}},"required":["numerator","denominator"],"additionalProperties":false},{"type":"null"}]},"exact_upper":{"anyOf":[{"type":"object","properties":{"numerator":{"type":"string","pattern":"^-?[0-9]+$"},"denominator":{"type":"string","pattern":"^[1-9][0-9]*$"}},"required":["numerator","denominator"],"additionalProperties":false},{"type":"null"}]},"unit":{"enum":["direction_oriented_pixel","dimensionless","pixel^2","dimensionless^2"]},"status":{"enum":["populated","conditional_scenario","unavailable"]},"origin":{"const":"derived"},"input_origins":{"type":"array","items":{"enum":["graph_derived_manual","reported","derived","synthetic"]},"uniqueItems":true},"formula":{"enum":["s*(a-t)","s*(a-b)","s*(b-t)","(a-b)/(a-t)","1-(a-b)/(a-t)","J_D*Sigma*J_D_transpose","J_C*Sigma*J_C_transpose","J_G*Sigma*J_G_transpose","J_F*Sigma*J_F_transpose","J_H*Sigma*J_H_transpose"]},"meaning":{"enum":["Selected total reporter amplitude in direction-oriented native pixels.","Reporter amplitude retained under the selected baseline correction model.","Additional reporter amplitude under the selected baseline correction model.","Corrected-to-total reporter amplitude ratio under the selected model.","Additional-to-total reporter amplitude ratio under the selected model.","First-order variance of the total amplitude in the supplied joint estimate model.","First-order variance of the corrected amplitude in the supplied joint estimate model.","First-order variance of the additional amplitude in the supplied joint estimate model.","First-order variance of the retained fraction in the supplied joint estimate model.","First-order variance of the additional fraction in the supplied joint estimate model."]},"conditional_on":{"type":"array","items":{"enum":["common_affine_native_ordinate","selected_ordinate_direction","selected_finite_time_coordinate","source_displayed_baseline","baseline_extrapolation_supported","baseline_extrapolation_stipulated","fast_component_completion_supported","fast_component_completion_stipulated","uncorrected_source_trace","same_trace_shared_initial_ordinate","joint_manual_reading_error_model","joint_physical_ordinate_estimate_model","covariance_already_in_native_coordinate_units","known_covariance","estimated_covariance","first_order_covariance_propagation","synthetic_uncertainty_scenario"]},"uniqueItems":true},"unavailable_reasons":{"type":"array","items":{"enum":["source_unavailable","missing_initial","missing_baseline_at_addition","missing_late","axis_scale_unestablished","ordinate_direction_unresolved","measurement_stage_not_endpoint","correction_already_applied","correction_stage_unresolved","baseline_basis_unsupported","baseline_applicability_unresolved","fast_component_completion_unresolved","zero_total_amplitude","reading_enclosure_unreported","reading_denominator_contains_zero","covariance_unreported","covariance_unavailable","covariance_status_unknown","covariance_basis_not_applicable","numerical_projection_range"]},"uniqueItems":true},"qualifications":{"type":"array","items":{"enum":["manual_reading_not_physical_measurement","reading_bounds_not_statistical_CI","nonnegative_additive_model_incompatible","physical_covariance_unreported","synthetic_covariance_model","not_molecular_attribution","first_order_covariance_propagation"]},"uniqueItems":true},"bound_kind":{"enum":["manual_reading_enclosure_not_confidence_interval","none"]},"primitive_owners":{"type":"array","items":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"minItems":3,"maxItems":3},"contribution_key":{"type":"string","minLength":1},"uncertainty_basis":{"anyOf":[{"enum":["joint_manual_reading_error","joint_physical_ordinate_estimates"]},{"type":"null"}]},"row_version":{"const":"endpoint_signal_return_v1"},"sheet_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"evidence_source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"image_source_ref":{"type":["string","null"],"format":"reference","x-reference-namespace":"source"},"evaluation_scope":{"const":"source_endpoint_signal_contribution"},"source_kind":{"enum":["primary_source","retained_extraction","synthetic_fixture"]},"source_context":{"type":"object","properties":{"subject":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"organism":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"genotype":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"construct":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"preparation":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"partners":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"experiment":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"condition":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"endpoint":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"normalization":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"intended_variable":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"functional_assertion":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"limitations":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"experimental_system":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false},"expression_host":{"type":"object","properties":{"status":{"type":"string","enum":["selected","not_selected","source_unavailable"]},"fragments":{"type":"array","items":{"type":"object","properties":{"text":{"type":"string","minLength":1},"location":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false}},"required":["text","location"],"additionalProperties":false}}},"required":["status","fragments"],"additionalProperties":false}},"required":["subject","organism","genotype","construct","preparation","partners","experiment","condition","endpoint","normalization","intended_variable","functional_assertion","limitations","experimental_system","expression_host"],"additionalProperties":false},"relationships":{"type":"object","properties":{"axis_scale":{"type":"object","properties":{"value":{"enum":["common_affine","nonlinear","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"ordinate_direction":{"type":"object","properties":{"value":{"enum":["increases_upward","increases_downward","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"measurement_stage":{"type":"object","properties":{"value":{"enum":["endpoint_amplitude","initial_rate","other","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"correction_stage":{"type":"object","properties":{"value":{"enum":["not_applied","already_applied","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"baseline_basis":{"type":"object","properties":{"value":{"enum":["source_displayed_extrapolation","matched_control","new_fit","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"baseline_applicability":{"type":"object","properties":{"value":{"enum":["supported","explicit_conditional_scenario","unsupported","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"fast_component_completion":{"type":"object","properties":{"value":{"enum":["supported","explicit_conditional_scenario","unsupported","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"additive_interpretation":{"type":"object","properties":{"value":{"enum":["nonnegative_additive","signed_decomposition","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false},"arrangement":{"type":"object","properties":{"value":{"enum":["single_preparation","replacement","coexistence","not_applicable","unknown","conflicting"],"type":"string"},"status":{"type":"string","enum":["authenticated_interpretation","source_unavailable"]}},"required":["value","status"],"additionalProperties":false}},"required":["axis_scale","ordinate_direction","measurement_stage","correction_stage","baseline_basis","baseline_applicability","fast_component_completion","additive_interpretation","arrangement"],"additionalProperties":false},"sampling_window":{"anyOf":[{"const":"finite_selected_late_point_no_physical_time_extracted"},{"type":"null"}]},"uncertainty":{"type":"object","properties":{"availability":{"type":"string","enum":["unreported","available","unavailable","unknown"]},"source_ref":{"type":["string","null"],"format":"reference","x-reference-namespace":"source"},"basis":{"anyOf":[{"type":"string","enum":["joint_manual_reading_error","joint_physical_ordinate_estimates"]},{"type":"null"}]},"variance_status":{"anyOf":[{"type":"string","enum":["known","estimated","unknown"]},{"type":"null"}]},"origin":{"anyOf":[{"type":"string","enum":["source_reported","source_derived","synthetic"]},{"type":"null"}]},"coordinate_units_status":{"anyOf":[{"const":"already_in_declared_native_coordinate_units"},{"type":"null"}]},"physical_uncertainty":{"type":"string","enum":["unreported","supplied_physical_estimate_model","unknown"]},"published_ratio_uncertainty":{"const":"not_extracted"}},"required":["availability","source_ref","basis","variance_status","origin","coordinate_units_status","physical_uncertainty","published_ratio_uncertainty"],"additionalProperties":false},"physical_preparation_count":{"type":"null"},"physical_preparation_count_status":{"const":"not_extracted"},"molecular_attribution":{"const":"not_established_by_signal_decomposition"},"functional_relevance":{"const":"not_scored_by_endpoint_section"},"dependency_meanings":{"const":["same_selected_trace_shared_initial","D_equals_C_plus_G","C_equals_F_times_D","H_equals_one_minus_F","dependent_views_not_independent_assays","amplitude_not_initial_rate_g","fraction_not_function_probability"]},"source_scope":{"type":"array","items":{"type":"string","format":"reference","x-reference-namespace":"source"},"uniqueItems":true},"withheld_locations":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","format":"reference","x-reference-namespace":"source"},"artifact_ref":{"type":"string","format":"reference","x-reference-namespace":"artifact"},"representation":{"type":"string","enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["source_ref","artifact_ref","representation","start","end"],"additionalProperties":false},"uniqueItems":true},"withheld_image_source_refs":{"type":"array","items":{"type":"string","format":"reference","x-reference-namespace":"source"},"uniqueItems":true}},"required":["component","value","conditional_value","exact_value","conditional_exact_value","lower","upper","exact_lower","exact_upper","unit","status","origin","input_origins","formula","meaning","conditional_on","unavailable_reasons","qualifications","bound_kind","primitive_owners","contribution_key","uncertainty_basis","row_version","sheet_ref","evidence_source_ref","image_source_ref","evaluation_scope","source_kind","source_context","relationships","sampling_window","uncertainty","physical_preparation_count","physical_preparation_count_status","molecular_attribution","functional_relevance","dependency_meanings","source_scope","withheld_locations","withheld_image_source_refs"],"additionalProperties":false,"allOf":[{"if":{"properties":{"component":{"const":"total_amplitude"}},"required":["component"]},"then":{"properties":{"unit":{"const":"direction_oriented_pixel"},"formula":{"const":"s*(a-t)"},"meaning":{"const":"Selected total reporter amplitude in direction-oriented native pixels."}}}},{"if":{"properties":{"component":{"const":"corrected_amplitude"}},"required":["component"]},"then":{"properties":{"unit":{"const":"direction_oriented_pixel"},"formula":{"const":"s*(a-b)"},"meaning":{"const":"Reporter amplitude retained under the selected baseline correction model."}}}},{"if":{"properties":{"component":{"const":"additional_amplitude"}},"required":["component"]},"then":{"properties":{"unit":{"const":"direction_oriented_pixel"},"formula":{"const":"s*(b-t)"},"meaning":{"const":"Additional reporter amplitude under the selected baseline correction model."}}}},{"if":{"properties":{"component":{"const":"retained_fraction"}},"required":["component"]},"then":{"properties":{"unit":{"const":"dimensionless"},"formula":{"const":"(a-b)/(a-t)"},"meaning":{"const":"Corrected-to-total reporter amplitude ratio under the selected model."}}}},{"if":{"properties":{"component":{"const":"additional_fraction"}},"required":["component"]},"then":{"properties":{"unit":{"const":"dimensionless"},"formula":{"const":"1-(a-b)/(a-t)"},"meaning":{"const":"Additional-to-total reporter amplitude ratio under the selected model."}}}},{"if":{"properties":{"component":{"const":"total_amplitude_variance"}},"required":["component"]},"then":{"properties":{"unit":{"const":"pixel^2"},"formula":{"const":"J_D*Sigma*J_D_transpose"},"meaning":{"const":"First-order variance of the total amplitude in the supplied joint estimate model."}}}},{"if":{"properties":{"component":{"const":"corrected_amplitude_variance"}},"required":["component"]},"then":{"properties":{"unit":{"const":"pixel^2"},"formula":{"const":"J_C*Sigma*J_C_transpose"},"meaning":{"const":"First-order variance of the corrected amplitude in the supplied joint estimate model."}}}},{"if":{"properties":{"component":{"const":"additional_amplitude_variance"}},"required":["component"]},"then":{"properties":{"unit":{"const":"pixel^2"},"formula":{"const":"J_G*Sigma*J_G_transpose"},"meaning":{"const":"First-order variance of the additional amplitude in the supplied joint estimate model."}}}},{"if":{"properties":{"component":{"const":"retained_fraction_variance"}},"required":["component"]},"then":{"properties":{"unit":{"const":"dimensionless^2"},"formula":{"const":"J_F*Sigma*J_F_transpose"},"meaning":{"const":"First-order variance of the retained fraction in the supplied joint estimate model."}}}},{"if":{"properties":{"component":{"const":"additional_fraction_variance"}},"required":["component"]},"then":{"properties":{"unit":{"const":"dimensionless^2"},"formula":{"const":"J_H*Sigma*J_H_transpose"},"meaning":{"const":"First-order variance of the additional fraction in the supplied joint estimate model."}}}}]},"x-source":"literature_endpoint_signal_cells"}')
ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1 = json.loads('{"type":"object","properties":{"version":{"const":"literature_figure_endpoint_signal_population_v1"},"selection":{"type":"object","properties":{"version":{"const":"a105_endpoint_signal_selection_v1"},"source_ref":{"type":"string","minLength":1},"source_kind":{"enum":["primary_source","retained_extraction","synthetic_fixture"]},"context":{"type":"object","properties":{"subject":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"organism":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"genotype":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"construct":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"preparation":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"partners":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"experiment":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"condition":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"endpoint":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"normalization":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"intended_variable":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"functional_assertion":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"correction_discussion":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"limitations":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"repetition":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"experimental_system":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"expression_host":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]},"sampling_window":{"anyOf":[{"type":"object","properties":{"image_region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"meaning":{"const":"finite_selected_late_point_no_physical_time_extracted"}},"required":["image_region","meaning"],"additionalProperties":false},{"type":"null"}]}},"required":["subject","organism","genotype","construct","preparation","partners","experiment","condition","endpoint","normalization","intended_variable","functional_assertion","correction_discussion","limitations","repetition","experimental_system","expression_host","sampling_window"],"additionalProperties":false},"relationships":{"type":"object","properties":{"axis_scale":{"type":"object","properties":{"value":{"enum":["common_affine","nonlinear","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"ordinate_direction":{"type":"object","properties":{"value":{"enum":["increases_upward","increases_downward","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"measurement_stage":{"type":"object","properties":{"value":{"enum":["endpoint_amplitude","initial_rate","other","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"correction_stage":{"type":"object","properties":{"value":{"enum":["not_applied","already_applied","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"baseline_basis":{"type":"object","properties":{"value":{"enum":["source_displayed_extrapolation","matched_control","new_fit","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"baseline_applicability":{"type":"object","properties":{"value":{"enum":["supported","explicit_conditional_scenario","unsupported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"fast_component_completion":{"type":"object","properties":{"value":{"enum":["supported","explicit_conditional_scenario","unsupported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"additive_interpretation":{"type":"object","properties":{"value":{"enum":["nonnegative_additive","signed_decomposition","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false},"arrangement":{"type":"object","properties":{"value":{"enum":["single_preparation","replacement","coexistence","not_applicable","unknown","conflicting"]},"witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"image_regions":{"type":"array","items":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4}}},"required":["value","witnesses","image_regions"],"additionalProperties":false}},"required":["axis_scale","ordinate_direction","measurement_stage","correction_stage","baseline_basis","baseline_applicability","fast_component_completion","additive_interpretation","arrangement"],"additionalProperties":false},"image":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"expected_sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"},"width":{"type":"integer","minimum":1},"height":{"type":"integer","minimum":1},"panel_region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"image_origin":{"enum":["published","synthetic"]},"points":{"type":"object","properties":{"initial":{"anyOf":[{"type":"object","properties":{"x":{"type":"integer","minimum":0},"y":{"type":"integer","minimum":0},"y_enclosure":{"anyOf":[{"type":"array","items":{"type":"integer","minimum":0},"minItems":2,"maxItems":2},{"type":"null"}]},"support_region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"maximum_rgb":{"type":"integer","minimum":0,"maximum":255},"image_witness":{"type":"object","properties":{"region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"meaning":{"enum":["initial_trace","displayed_baseline_at_addition","selected_late_trace"]}},"required":["region","meaning"],"additionalProperties":false},"semantic_witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"physical_estimate_owner":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]}},"required":["x","y","y_enclosure","support_region","maximum_rgb","image_witness","semantic_witnesses","physical_estimate_owner"],"additionalProperties":false},{"type":"null"}]},"baseline_at_addition":{"anyOf":[{"type":"object","properties":{"x":{"type":"integer","minimum":0},"y":{"type":"integer","minimum":0},"y_enclosure":{"anyOf":[{"type":"array","items":{"type":"integer","minimum":0},"minItems":2,"maxItems":2},{"type":"null"}]},"support_region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"maximum_rgb":{"type":"integer","minimum":0,"maximum":255},"image_witness":{"type":"object","properties":{"region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"meaning":{"enum":["initial_trace","displayed_baseline_at_addition","selected_late_trace"]}},"required":["region","meaning"],"additionalProperties":false},"semantic_witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"physical_estimate_owner":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]}},"required":["x","y","y_enclosure","support_region","maximum_rgb","image_witness","semantic_witnesses","physical_estimate_owner"],"additionalProperties":false},{"type":"null"}]},"late":{"anyOf":[{"type":"object","properties":{"x":{"type":"integer","minimum":0},"y":{"type":"integer","minimum":0},"y_enclosure":{"anyOf":[{"type":"array","items":{"type":"integer","minimum":0},"minItems":2,"maxItems":2},{"type":"null"}]},"support_region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"maximum_rgb":{"type":"integer","minimum":0,"maximum":255},"image_witness":{"type":"object","properties":{"region":{"type":"array","items":{"type":"integer","minimum":0},"minItems":4,"maxItems":4},"meaning":{"enum":["initial_trace","displayed_baseline_at_addition","selected_late_trace"]}},"required":["region","meaning"],"additionalProperties":false},"semantic_witnesses":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false}},"physical_estimate_owner":{"anyOf":[{"type":"object","properties":{"source_ref":{"type":"string","minLength":1},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},{"type":"null"}]}},"required":["x","y","y_enclosure","support_region","maximum_rgb","image_witness","semantic_witnesses","physical_estimate_owner"],"additionalProperties":false},{"type":"null"}]}},"required":["initial","baseline_at_addition","late"],"additionalProperties":false}},"required":["source_ref","expected_sha256","width","height","panel_region","image_origin","points"],"additionalProperties":false},{"type":"null"}]},"covariance_source_ref":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"requested_cells":{"type":"array","items":{"enum":["total_amplitude","corrected_amplitude","additional_amplitude","retained_fraction","additional_fraction","total_amplitude_variance","corrected_amplitude_variance","additional_amplitude_variance","retained_fraction_variance","additional_fraction_variance"]},"uniqueItems":true}},"required":["version","source_ref","source_kind","context","relationships","image","covariance_source_ref","requested_cells"],"additionalProperties":false},"return_context":{"type":"object","properties":{"subject":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"organism":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"genotype":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"construct":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"preparation":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"partners":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"experiment":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"condition":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"endpoint":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"normalization":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"intended_variable":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"functional_assertion":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"limitations":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"experimental_system":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true},"expression_host":{"type":"array","items":{"type":"object","properties":{"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1}},"required":["start","end"],"additionalProperties":false},"uniqueItems":true}},"required":["subject","organism","genotype","construct","preparation","partners","experiment","condition","endpoint","normalization","intended_variable","functional_assertion","limitations","experimental_system","expression_host"],"additionalProperties":false}},"required":["version","selection","return_context"],"additionalProperties":false}')
_PURE_HASHES = json.loads('{"literature_endpoint_signal_calculations.py":"48dfcd0473ad087e714067c868388bf54210a5069112d04e2d678ed9cda08340","literature_endpoint_signal_inputs.py":"5fcbb6d3393a278500038df3ef934895ef5d5443f2d9878c179dbe89ae9e015d","literature_endpoint_signal_prompt.py":"f4ebb4281b23b3ce334ad3eafdfe47ddfe15a43d00f331ab4d46e4c201b56477"}')


def endpoint_signal_cells_schema():
    return deepcopy(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)


def endpoint_signal_operation_schema():
    return deepcopy(ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1)


def _witnesses(value):
    if isinstance(value, dict):
        if {'source_ref', 'representation', 'start', 'end', 'quote'} <= value.keys():
            yield value
        else:
            for child in value.values():
                yield from _witnesses(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _witnesses(child)


def _direct(args):
    selected = args['selection']
    refs = [selected['source_ref']]
    if selected['image'] is not None:
        refs.append(selected['image']['source_ref'])
    refs.extend(w['source_ref'] for w in _witnesses(selected))
    if selected['covariance_source_ref'] is not None:
        refs.append(selected['covariance_source_ref'])
    return list(dict.fromkeys(refs))


def _location(witness):
    return {name: witness[name] for name in
        ('source_ref', 'artifact_ref', 'representation', 'start', 'end')}


def _context_projection(args, extraction):
    result = {}
    for name, windows in args['return_context'].items():
        selected, actual = args['selection']['context'][name], extraction['context'][name]
        fragments = []
        if windows and selected is None:
            raise ContractError('endpoint_context_without_source_witness')
        for window in windows:
            a, b = window['start'], window['end']
            if not selected['start'] <= a < b <= selected['end']:
                raise ContractError('endpoint_context_outside_role_witness')
            correction_entry = extraction['context']['correction_discussion']
            correction = correction_entry['witness'] if correction_entry is not None else None
            if (actual is not None and correction is not None
                    and actual['witness']['artifact_ref'] == correction['artifact_ref']
                    and a < correction['end'] and correction['start'] < b):
                raise ContractError('endpoint_context_overlaps_private_correction_result')
            covariance = extraction['covariance']
            if (actual is not None and covariance is not None and covariance['artifact_ref'] is not None
                    and actual['witness']['artifact_ref'] == covariance['artifact_ref']):
                raise ContractError('endpoint_context_from_covariance_packet')
            raw = selected['quote'].encode('utf-8')
            try:
                text = raw[a-selected['start']:b-selected['start']].decode('utf-8')
            except UnicodeError as error:
                raise ContractError('endpoint_context_utf8_boundary_required') from error
            if not text:
                raise ContractError('endpoint_context_empty_fragment')
            if actual is not None:
                fragments.append({'text': text, 'location': {
                    **_location(actual['witness']), 'start': a, 'end': b}})
        result[name] = {'status': 'not_selected' if not windows else
            'source_unavailable' if actual is None else 'selected', 'fragments': fragments}
    return result


def _project_once(args, extraction, sheet, source_refs, read_sizes):
    context = _context_projection(args, extraction)
    locations = []
    for w in _witnesses(extraction):
        if 'artifact_ref' in w and _location(w) not in locations:
            locations.append(_location(w))
    covariance = extraction['covariance']
    model = covariance['model'] if covariance and covariance['error'] is None else None
    if model is not None:
        # The covariance wire retains its authenticated selectors without the
        # reader's enriched artifact_ref. Bind those exact support spans using
        # its actual successful source receipts, including off-page aliases.
        artifacts = {(item['source_ref'], item['representation']): item['artifact_ref']
            for item in extraction['source_artifacts'] if item['error'] is None}
        for witness in _witnesses(model):
            artifact = artifacts.get((witness['source_ref'], witness['representation']))
            if artifact is not None:
                location = {**{key: witness[key] for key in ('source_ref', 'representation', 'start', 'end')},
                    'artifact_ref': artifact}
                if location not in locations:
                    locations.append(location)
    if covariance and covariance['artifact_ref'] is not None:
        size = read_sizes.get((covariance['source_ref'], 'original'), 0)
        if size:
            locations.append({'source_ref': covariance['source_ref'],
                'artifact_ref': covariance['artifact_ref'], 'representation': 'original', 'start': 0, 'end': size})
    uncertainty = {'availability': 'unreported' if covariance is None else 'unavailable' if model is None
        else 'unknown' if model['variance_status'] == 'unknown' else 'available',
        'source_ref': covariance['source_ref'] if covariance else None,
        'basis': model['basis'] if model else None,
        'variance_status': model['variance_status'] if model else None,
        'origin': model['origin'] if model else None,
        'coordinate_units_status': model['coordinate_units_status'] if model else None,
        'physical_uncertainty': 'supplied_physical_estimate_model' if model and
            model['basis'] == 'joint_physical_ordinate_estimates' else 'unreported',
        'published_ratio_uncertainty': 'not_extracted'}
    image = extraction['image']
    common = {'row_version': 'endpoint_signal_return_v1', 'evidence_source_ref': extraction['source_ref'],
        'image_source_ref': image['source_ref'] if image else None, 'evaluation_scope': SCOPE,
        'source_kind': extraction['source_kind'], 'source_context': context,
        'relationships': {name: {'value': item['interpretation']['value'] if item['interpretation'] else 'unknown',
            'status': 'authenticated_interpretation' if item['interpretation'] else 'source_unavailable'}
            for name, item in extraction['relationships'].items()},
        'sampling_window': extraction['context']['sampling_window']['value']
            if extraction['context']['sampling_window'] else None,
        'uncertainty': uncertainty, 'physical_preparation_count': None,
        'physical_preparation_count_status': 'not_extracted',
        'molecular_attribution': 'not_established_by_signal_decomposition',
        'functional_relevance': 'not_scored_by_endpoint_section',
        'dependency_meanings': deepcopy(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1['items']['properties']['dependency_meanings']['const']),
        'source_scope': list(source_refs), 'withheld_locations': locations,
        'withheld_image_source_refs': [image['source_ref']] if image else []}
    return [{**deepcopy(common), **deepcopy(cell)} for cell in sheet['cells']]


class LiteratureEndpointSignalRepository(LiteratureRateRepository):
    provider, record_version, components = PROVIDER, VERSION, COMPONENTS
    operations_table = 'literature_endpoint_signal_operations'
    received_table = 'literature_endpoint_signal_received'
    binding_fields = ()

    def __init__(self, store, run_id):
        if type(run_id) is not str or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    @staticmethod
    def _components(values):
        if (not isinstance(values, (list, tuple)) or any(type(x) is not str or x not in COMPONENTS for x in values)
                or len(set(values)) != len(values)):
            raise ContractError('endpoint_component_selection_invalid')
        return list(values)

    def _ancestors(self, scope, references):
        result = list(dict.fromkeys(references))
        for ref in result:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in result:
                    result.append(parent)
        return result

    def _original_implementation(self):
        files = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in _PURE_HASHES}
        if files != _PURE_HASHES:
            raise ContractError('endpoint_prospective_dependency_mismatch')
        for name in ('literature_endpoint_signal_storage.py', 'literature_endpoint_signal_render.py',
                'literature_figure_storage.py', 'literature_episodes.py', 'communication.py',
                'literature_numerical_contracts.py', 'literature_numerical_return_presentation.py',
                'literature_experimental_prompt.py', 'literature_reference_parent_prompt.py'):
            files[name] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        return {'version': 'endpoint_signal_original_implementation_v1', 'files': files}

    def populate(self, context, arguments, operation_key):
        from .literature_endpoint_signal_inputs import (read_endpoint_signal_inputs,
            endpoint_signal_population_schema, endpoint_signal_extraction_schema)
        from .literature_endpoint_signal_calculations import populate_endpoint_signal, endpoint_signal_sheet_schema
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if type(operation_key) is not str or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1)
        components = self._components(context.assignment.get(REQUESTED, []))
        if components != args['selection']['requested_cells']:
            raise ContractError('endpoint_assignment_request_roster_mismatch')
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'role': context.role,
            'operation_key': operation_key, 'scope': plain(context.scope), 'assignment': plain(context.assignment),
            'received_record_refs': list(context.received_record_refs), 'arguments': args, 'components': components}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome']); saved = self.read(outcome['result']['sheet_ref'])
            for reference in saved['direct_input_source_refs']:
                self._native_source(context, reference)
            return outcome
        for reference in _direct(args):
            self._native_source(context, reference)
        receipt = self._original_implementation()
        read_sizes, authorization_errors = {}, []
        def read_source(reference, representation):
            try:
                row = self._native_source(context, reference)
            except ContractError as error:
                authorization_errors.append(error); raise
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            raw = self.store.get_artifact(artifact)
            if artifact != 'artifact_' + hashlib.sha256(raw).hexdigest():
                raise ContractError('endpoint_source_artifact_hash_mismatch')
            read_sizes[(reference, representation)] = len(raw)
            return {'artifact_ref': artifact, 'content': raw}
        extraction = read_endpoint_signal_inputs(args['selection'], read_source=read_source)
        if authorization_errors:
            raise authorization_errors[0]
        sheet = populate_endpoint_signal(extraction)
        direct = list(dict.fromkeys([*_direct(args), *(s['source_ref'] for s in extraction['source_artifacts'])]))
        for reference in direct:
            self._native_source(context, reference)
        parents = self._ancestors(context.scope, direct)
        templates = _project_once(args, extraction, sheet, parents, read_sizes)
        source = self._native_source(context, args['selection']['source_ref'])
        snapshots = {'request': deepcopy(ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1),
            'selection': endpoint_signal_population_schema(), 'extraction': endpoint_signal_extraction_schema(),
            'sheet': endpoint_signal_sheet_schema(), 'rows': deepcopy(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)}
        payload = {'version': VERSION, 'input_source_ref': source['id'], 'input_artifact_ref': source['artifact_ref'],
            'direct_input_source_refs': direct, 'input_source_refs': parents,
            'source_metadata': {ref: self.store.get(ref) for ref in parents}, 'original_implementation': receipt,
            'original_schemas': snapshots, 'extraction': extraction, 'sheet': sheet, 'row_templates': templates}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            record = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': req_ref, 'version': VERSION, 'retrieved_at': None,
                'parent_source_refs': parents}
            ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (ref,)).fetchone()
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = [{'sheet_ref': ref, **deepcopy(row)} for row in templates]
            validate_schema(rows, snapshots['rows'])
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [ref],
                'changed_record_refs': [] if exists else [ref], 'result': {'sheet_ref': ref,
                    'view': VIEW, 'record_version': VERSION, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != 'artifact_' + hashlib.sha256(raw).hexdigest():
            raise ContractError('endpoint_saved_artifact_hash_mismatch')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ContractError('endpoint_saved_object_required')
        return value

    def read(self, reference):
        try:
            return self._read(reference)
        except ContractError:
            raise
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as error:
            raise ContractError('endpoint_saved_binding_mismatch') from error

    def _read(self, reference):
        def require(condition):
            if not condition:
                raise ContractError('endpoint_saved_binding_mismatch')
        source = self.store.get(reference)
        record = {k: v for k, v in source.items() if k not in ('id', 'origin', 'record_type')}
        require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
            and source.get('provider') == PROVIDER and source.get('version') == VERSION
            and identity('source', {'origin': 'tool', 'record': record}) == reference)
        request, saved = self._json(source['request_ref']), self._json(source['artifact_ref'])
        require(set(request) == {'run_id', 'episode_id', 'role', 'operation_key', 'scope', 'assignment',
            'received_record_refs', 'arguments', 'components'} and request['run_id'] == self.run_id)
        require(set(saved) == {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs',
            'input_source_refs', 'source_metadata', 'original_implementation', 'original_schemas',
            'extraction', 'sheet', 'row_templates'})
        require(saved['version'] == VERSION and source['text_ref'] == source['artifact_ref'])
        require(self._installed(self.operations_table))
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        require(operation is not None and operation['signature'] == canonical(request))
        schemas = saved['original_schemas']
        require(set(schemas) == {'request', 'selection', 'extraction', 'sheet', 'rows'})
        require(schemas['request'] == ENDPOINT_SIGNAL_REQUEST_SCHEMA_V1
            and schemas['rows'] == ENDPOINT_SIGNAL_CELLS_SCHEMA_V1
            and schemas['selection'] == schemas['request']['properties']['selection']
            and schemas['extraction']['properties']['arguments'] == schemas['selection']
            and schemas['sheet']['properties']['input_snapshot'] == schemas['extraction'])
        args, extraction, sheet = request['arguments'], saved['extraction'], saved['sheet']
        validate_schema(args, schemas['request']); validate_schema(args['selection'], schemas['selection'])
        validate_schema(extraction, schemas['extraction']); validate_schema(sheet, schemas['sheet'])
        require(args['version'] == POPULATION and extraction['arguments'] == args['selection'])
        require(request['components'] == request['assignment'].get(REQUESTED, []) == args['selection']['requested_cells'])
        require(sheet['input_snapshot'] == extraction and sheet['requested_cells'] == request['components'])
        require([c['component'] for c in sheet['cells']] == request['components'])
        require(saved['input_source_ref'] == args['selection']['source_ref'] == extraction['source_ref'])
        direct = saved['direct_input_source_refs']
        require(direct == list(dict.fromkeys([*_direct(args), *(s['source_ref'] for s in extraction['source_artifacts'])])))
        require(all(ref in request['received_record_refs'] for ref in direct))
        require(saved['input_source_refs'] == source['parent_source_refs'] == self._ancestors(request['scope'], direct))
        require(set(saved['source_metadata']) == set(saved['input_source_refs']))
        for ref, metadata in saved['source_metadata'].items():
            require(canonical(self._native_provenance(request['scope'], ref)) == canonical(metadata))
        require(saved['input_artifact_ref'] == saved['source_metadata'][saved['input_source_ref']]['artifact_ref'])
        receipt = saved['original_implementation']
        require(set(receipt) == {'version', 'files'} and receipt['version'] == 'endpoint_signal_original_implementation_v1'
            and all(receipt['files'].get(name) == digest for name, digest in _PURE_HASHES.items())
            and all(type(name) is str and type(digest) is str and len(digest) == 64
                and all(c in '0123456789abcdef' for c in digest) for name, digest in receipt['files'].items()))
        templates = saved['row_templates']
        require(len(templates) == len(sheet['cells']))
        cell_fields = schemas['sheet']['properties']['cells']['items']['properties']
        for template, cell in zip(templates, sheet['cells']):
            require({k: template[k] for k in cell_fields} == cell)
            require(template['source_scope'] == saved['input_source_refs'] and template['evidence_source_ref'] == saved['input_source_ref'])
            for name, projected in template['source_context'].items():
                selected = args['return_context'][name]; actual = extraction['context'][name]
                require(projected['status'] == ('not_selected' if not selected else 'source_unavailable' if actual is None else 'selected'))
                require(len(projected['fragments']) == (len(selected) if actual else 0))
                for fragment, window in zip(projected['fragments'], selected):
                    witness = actual['witness']; loc = fragment['location']
                    require(loc == {**_location(witness), **window})
                    a, b = window['start']-witness['start'], window['end']-witness['start']
                    require(0 <= a < b <= len(witness['quote'].encode()) and fragment['text'].encode() == witness['quote'].encode()[a:b])
        rows = [{'sheet_ref': reference, **deepcopy(row)} for row in templates]
        validate_schema(rows, schemas['rows'])
        outcome = json.loads(operation['outcome'])
        require(outcome['status'] == 'completed' and outcome['feedback'] is None and outcome['record_refs'] == [reference])
        require(outcome['operation_ref'] == identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']}))
        require(canonical(outcome['result']) == canonical({'sheet_ref': reference, 'view': VIEW, 'record_version': VERSION, 'cells': rows}))
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = None if components is None else self._components(components)
        result = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(ref)
            by_name = {row['component']: row for row in saved['row_templates']}
            result.extend({'sheet_ref': ref, **deepcopy(by_name[name])} for name in
                (list(by_name) if selected is None else selected) if name in by_name)
        return result

    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, ENDPOINT_SIGNAL_CELLS_SCHEMA_V1)
        seen = set()
        for row in cells:
            key = row['sheet_ref'], row['component']
            if key in seen:
                raise ContractError('duplicate_endpoint_return_cell')
            seen.add(key)
            expected = self.project_cells([row['sheet_ref']], permitted_record_refs=permitted_record_refs, components=[row['component']])
            if canonical(expected) != canonical([row]):
                raise ContractError('endpoint_return_differs_from_saved_cells')

    def fact_cells(self, context, sheet_refs, *, components):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        selected = self._components(components); result = []; received = None
        for ref in dict.fromkeys(sheet_refs):
            if ref not in context.received_record_refs:
                raise ContractError('literature_sheet_not_received')
            self._native_provenance(context.scope, ref)
            if self._sheet_owner(ref) == context.episode_id:
                result.extend(self.project_cells([ref], permitted_record_refs=context.received_record_refs, components=selected))
            else:
                if received is None:
                    received = {(row['sheet_ref'], row['component']): row for row in self.received_cells(context)}
                result.extend(deepcopy(received[ref, name]) for name in selected if (ref, name) in received)
        return result

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        if cells:
            with self.store.transaction():
                self._install(); return super().receive_cells(context, cells, operation_key)

    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        refs = list(dict.fromkeys(json.loads(row['outcome'])['result']['sheet_ref'] for row in self.store.db.execute(
            f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))))
        for ref in refs:
            self.read(ref)
        return refs

    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*(r for r in self.selected_sheet_refs(context) if r in context.received_record_refs),
            *(row['sheet_ref'] for row in self.received_cells(context) if row['sheet_ref'] in context.received_record_refs)]))

    def has_work(self, context):
        return bool(self.available_sheet_refs(context))

    def validate_empty_return_family(self, context):
        return None

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        def visit(value):
            if isinstance(value, dict):
                for name, child in value.items():
                    if name.endswith('_ref') and isinstance(child, str) and child.startswith(('source_', 'artifact_')):
                        refs.append(child)
                    elif name in ('source_scope', 'withheld_image_source_refs'):
                        refs.extend(child)
                    else:
                        visit(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    visit(child)
        visit(cells)
        return list(dict.fromkeys(refs))

    def receipt_bindings(self):
        """Host-only selected identity/artifact ownership; never installs state."""
        result = {}
        if not self._installed(self.operations_table):
            return result
        for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=?', (self.run_id,)):
            ref = json.loads(row['outcome'])['result']['sheet_ref']
            source = self.store.get(ref); owner = self._sheet_owner(ref)
            result[ref] = {'run_id': self.run_id, 'episode_id': owner,
                'artifacts': [source['artifact_ref'], source['request_ref']]}
        return result

    def _private_binding(self, source_ref, artifact=None):
        bindings = self.receipt_bindings()
        if source_ref in bindings:
            return bindings[source_ref]
        for binding in bindings.values():
            if artifact in binding['artifacts']:
                return binding
        source = self.store.get(source_ref) if source_ref is not None else {}
        if source.get('provider') == PROVIDER and source.get('version') == VERSION:
            raise ContractError('literature_endpoint_receipt_binding_invalid')
        return None

    def authorize_source_access(self, context, source_ref, representation, tool_name):
        source = self.store.get(source_ref)
        if source.get('record_type') != 'source':
            # Leave ordinary wrong-kind diagnostics to the selected source tool.
            return
        artifact = (source.get('text_ref') or source['artifact_ref']) if representation == 'text' and tool_name == 'source.read' else (
            source['artifact_ref'] if representation == 'original' else source.get(representation+'_ref'))
        binding = self._private_binding(source_ref, artifact)
        if binding and (binding['run_id'], binding['episode_id']) != (context.run_id, context.episode_id):
            raise ContractError('literature_endpoint_receipt_private')

    def authorize_record_access(self, context, record):
        if record.get('record_type') in {'source', 'artifact'}:
            return
        for anchor in (record, record.get('anchor'), record.get('visual_anchor')):
            if not isinstance(anchor, dict):
                continue
            binding = self._private_binding(anchor.get('source_ref'), anchor.get('artifact_ref'))
            if binding and (binding['run_id'], binding['episode_id']) != (context.run_id, context.episode_id):
                raise ContractError('literature_endpoint_receipt_private')


__all__ = ['LiteratureEndpointSignalRepository', 'ENDPOINT_SIGNAL_CELLS_SCHEMA_V1',
    'endpoint_signal_cells_schema', 'endpoint_signal_operation_schema', 'PROVIDER', 'VERSION',
    'POPULATION', 'NAMESPACE', 'REQUESTED', 'VIEW', 'SCOPE', 'COMPONENTS']
