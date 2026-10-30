"""Authenticated source operands for a finite A105 comparison section.

Scientific meanings remain supplied witnessed interpretations. This module has
no acquisition, Store, model call, runtime decision or credit behavior. Schema
resources are the exact reviewed plan004 values, retained locally with no IO.
"""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
import hashlib
import html
import json
import math
import re
from .domain import identity, validate_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_assay_inputs import _Sources, _interpretation
from .literature_partner_source_fields import _NUMBER, number_selector_schema
from .literature_rate_native_inputs import _number, _unit, _scale, _check_explicit_unit, _plain_unit
from .literature_kinetic_inputs import _count_reading, _interval, _confidence, _interpret as _native_interpret
from .literature_measurement_validation_inputs import _visible_span, _table_cells, _associate, _read_number, _RANGE, _field_witness
from .literature_product_coupling_inputs import _number as _nondetection_number
from .literature_optical_inputs import _unit as _optical_unit, _explicit_unit as _optical_explicit_unit, _UNIT_TABLES, _normalize

_SCHEMA_BUNDLE = json.loads('{"definitions":{"coefficient":{"type":"object","properties":{"origin":{"enum":["explicit_source_token","implicit_unit_coefficient"]},"number":{"anyOf":[{"$ref":"#/$defs/number_selector"},{"type":"null"}]},"implicit_value":{"anyOf":[{"type":"object","properties":{"numerator":{"const":"1"},"denominator":{"const":"1"}},"required":["numerator","denominator"],"additionalProperties":false},{"type":"null"}]},"support":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["origin","number","implicit_value","support"],"additionalProperties":false},"common_model":{"type":"object","properties":{"kind":{"const":"common_unbiased_quantity"},"applicability":{"$ref":"#/$defs/model_meaning"},"variance_interpretation":{"enum":["known_joint_estimator_covariance","estimated_joint_estimator_covariance","unknown"]},"combination":{"enum":["generalized_least_squares","not_requested"]}},"required":["kind","applicability","variance_interpretation","combination"],"additionalProperties":false},"conversion":{"type":"object","properties":{"kind":{"enum":["identity","fixed_reaction_scale","unresolved"]},"direction":{"type":"object","properties":{"value":{"enum":["same_direction_supported","opposite_direction","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"support_status":{"type":"object","properties":{"value":{"enum":["supported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"reaction":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"endpoint_species":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"common_species":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"endpoint_coefficient":{"anyOf":[{"$ref":"#/$defs/coefficient"},{"type":"null"}]},"common_coefficient":{"anyOf":[{"$ref":"#/$defs/coefficient"},{"type":"null"}]}},"required":["kind","direction","support_status","reaction","endpoint_species","common_species","endpoint_coefficient","common_coefficient"],"additionalProperties":false},"model_meaning":{"type":"object","properties":{"value":{"enum":["supported","stipulated_sensitivity","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"number_selector":{"type":"object","properties":{"witness":{"$ref":"#/$defs/witness"},"number_start":{"type":"integer","minimum":0},"number_end":{"type":"integer","minimum":1}},"required":["witness","number_start","number_end"],"additionalProperties":false},"optical":{"type":"object","properties":{"signal_role":{"enum":["left","right"]},"observation_equation":{"const":"y=h+s*alpha*f"},"nuisance_sign":{"enum":[-1,1]},"sign_support":{"type":"array","items":{"$ref":"#/$defs/witness"}},"raw_optical_relation":{"$ref":"#/$defs/model_meaning"},"coefficient_applicability":{"$ref":"#/$defs/model_meaning"},"estimate_scale_applicability":{"$ref":"#/$defs/model_meaning"},"nuisance_quantity_linkage":{"$ref":"#/$defs/model_meaning"},"scenario":{"anyOf":[{"type":"object","properties":{"kind":{"const":"required_interference_on_selected_report_scale"},"anchor_role":{"enum":["left","right"]},"common_rate_equality":{"$ref":"#/$defs/model_meaning"},"linear_mixture_on_estimate_scale":{"$ref":"#/$defs/model_meaning"}},"required":["kind","anchor_role","common_rate_equality","linear_mixture_on_estimate_scale"],"additionalProperties":false},{"type":"null"}]}},"required":["signal_role","observation_equation","nuisance_sign","sign_support","raw_optical_relation","coefficient_applicability","estimate_scale_applicability","nuisance_quantity_linkage","scenario"],"additionalProperties":false},"quantity_selection":{"type":"object","properties":{"layout":{"enum":["table","labelled_record"]},"record":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"number":{"anyOf":[{"$ref":"#/$defs/number_selector"},{"type":"null"}]},"row_label":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"quantity_label":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"unit":{"$ref":"#/$defs/unit_selection"},"quantity_kind":{"type":"object","properties":{"value":{"enum":["apparent_specific_activity","specific_activity","fixed_condition_rate","turnover_rate","terminal_conversion","affinity","extinction_coefficient","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"estimator_scale":{"type":"object","properties":{"value":{"enum":["direct_rate","fitted_asymptote","reported_mean","terminal_amount","parameter_estimate","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"semantics":{"type":"object","properties":{"value":{"enum":["reported_point_estimate","reported_nondetection","reported_negligible","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"qualification":{"type":"object","properties":{"value":{"enum":["reported_point","rounded_after_fit","source_qualified_approximate","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"normalization":{"type":"object","properties":{"value":{"enum":["protein_mass","assayed_molecule_amount","active_molecule_amount","reaction_volume","unnormalized_amount","extinction_unit","other","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"subject":{"type":"object","properties":{"organism":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"genotype":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"molecule":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"construct":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"expression_host":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"arrangement":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]}},"required":["organism","genotype","molecule","construct","expression_host","arrangement"],"additionalProperties":false},"assay":{"type":"object","properties":{"assay":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"preparation":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"purification_reconstitution":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"partners":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"substrates":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"conditions":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"direct_endpoint":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"inferred_quantity":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"denominator":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"time_window":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"fit_basis":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"sampling_unit":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"intended_change":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"additional_differences":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"calibration":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"blank":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"active_fraction":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"purity":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]}},"required":["assay","preparation","purification_reconstitution","partners","substrates","conditions","direct_endpoint","inferred_quantity","denominator","time_window","fit_basis","sampling_unit","intended_change","additional_differences","calibration","blank","active_fraction","purity"],"additionalProperties":false},"physical_identity":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"dependency_witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}},"uncertainty":{"$ref":"#/$defs/uncertainty_selection"}},"required":["layout","record","number","row_label","quantity_label","unit","quantity_kind","estimator_scale","semantics","qualification","normalization","subject","assay","physical_identity","dependency_witnesses","uncertainty"],"additionalProperties":false},"relationships":{"type":"object","properties":{"construct":{"type":"object","properties":{"value":{"enum":["same_construct_supported","intended_variant","different","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"preparation":{"type":"object","properties":{"value":{"enum":["same_preparation_supported","different_preparations_supported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"preparation_target":{"type":"object","properties":{"value":{"enum":["same_preparation_quantity","same_population_estimand_supported","incompatible","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"protocol":{"type":"object","properties":{"value":{"enum":["matched_except_intended_change","additional_differences","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"endpoint":{"type":"object","properties":{"value":{"enum":["same_quantity","fixed_reaction_conversion","complementary","incompatible","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"denominator":{"type":"object","properties":{"value":{"enum":["same_basis_supported","different","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"functional_bearing":{"type":"object","properties":{"value":{"enum":["same_quantitative_assertion","existence_only","partner_dependence_only","complementary","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"attribution":{"type":"object","properties":{"value":{"enum":["isolated_supported","mixed_contributors_identified","unresolved","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"sampling":{"type":"object","properties":{"value":{"enum":["repeated_representation","shared_physical_estimate","paired_observations_supported","independent_preparations_supported","independence_not_established","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"systematic_coverage":{"type":"object","properties":{"value":{"enum":["included_in_selected_covariance","identified_unresolved","not_established","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"left_validity":{"type":"object","properties":{"value":{"enum":["endpoint_quantification_supported","identified_unresolved_interference","corrected_endpoint_supported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"right_validity":{"type":"object","properties":{"value":{"enum":["endpoint_quantification_supported","identified_unresolved_interference","corrected_endpoint_supported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"left_readout_isolation":{"type":"object","properties":{"value":{"enum":["isolated_signal_supported","mixed_optical_contributions","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"right_readout_isolation":{"type":"object","properties":{"value":{"enum":["isolated_signal_supported","mixed_optical_contributions","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false}},"required":["construct","preparation","preparation_target","protocol","endpoint","denominator","functional_bearing","attribution","sampling","systematic_coverage","left_validity","right_validity","left_readout_isolation","right_readout_isolation"],"additionalProperties":false},"uncertainty_selection":{"type":"object","properties":{"statistic":{"type":"object","properties":{"value":{"enum":["sd","sem","ci","unspecified","unreported"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"magnitude":{"anyOf":[{"$ref":"#/$defs/number_selector"},{"type":"null"}]},"interval":{"anyOf":[{"type":"object","properties":{"witness":{"$ref":"#/$defs/witness"},"lower_start":{"type":"integer","minimum":0},"lower_end":{"type":"integer","minimum":1},"upper_start":{"type":"integer","minimum":0},"upper_end":{"type":"integer","minimum":1}},"required":["witness","lower_start","lower_end","upper_start","upper_end"],"additionalProperties":false},{"type":"null"}]},"confidence_level":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"unit":{"anyOf":[{"$ref":"#/$defs/witness"},{"$ref":"#/$defs/unit_definition"},{"type":"null"}]},"unit_relationship":{"type":"object","properties":{"value":{"enum":["same_as_estimate","explicit_unit","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"count":{"anyOf":[{"$ref":"#/$defs/number_selector"},{"type":"null"}]},"repetition_basis":{"type":"object","properties":{"value":{"enum":["independent_preparations","paired_units","technical_repeats","timepoints","unspecified","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false},"estimate_basis":{"type":"object","properties":{"value":{"enum":["fit_to_averaged_curve","between_fitted_estimates","within_curve_points","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/witness"}}},"required":["value","witnesses"],"additionalProperties":false}},"required":["statistic","magnitude","interval","confidence_level","unit","unit_relationship","count","repetition_basis","estimate_basis"],"additionalProperties":false},"unit_definition":{"type":"object","properties":{"kind":{"const":"source_defined_rate_unit"},"witness":{"$ref":"#/$defs/witness"},"definition":{"type":"object","properties":{"bridge":{"$ref":"#/$defs/witness"},"clause":{"$ref":"#/$defs/witness"},"amount_unit":{"$ref":"#/$defs/witness"},"time_unit":{"$ref":"#/$defs/witness"},"endpoint":{"$ref":"#/$defs/witness"},"endpoint_entity":{"$ref":"#/$defs/witness"},"definition_entity":{"$ref":"#/$defs/witness"},"amount":{"$ref":"#/$defs/number_selector"}},"required":["bridge","clause","amount_unit","time_unit","endpoint","endpoint_entity","definition_entity","amount"],"additionalProperties":false}},"required":["kind","witness","definition"],"additionalProperties":false},"unit_selection":{"anyOf":[{"$ref":"#/$defs/witness"},{"$ref":"#/$defs/unit_definition"},{"type":"null"}]},"witness":{"type":"object","properties":{"source_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1}},"required":["source_ref","representation","start","end","quote"],"additionalProperties":false},"coefficient_reading":{"type":"object","properties":{"reading":{"$ref":"#/$defs/retained_number"},"source_context":{"$ref":"#/$defs/retained_witness"}},"required":["reading","source_context"],"additionalProperties":false},"conversion_value":{"type":"object","properties":{"kind":{"enum":["identity","fixed_reaction_scale","unresolved"]},"multiplier_exact":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"status":{"enum":["supported","unknown","conflicting"]},"model_key":{"type":"string","minLength":1},"source_witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}},"coefficient_readings":{"type":"object","properties":{"endpoint":{"anyOf":[{"$ref":"#/$defs/coefficient_reading"},{"type":"null"}]},"common":{"anyOf":[{"$ref":"#/$defs/coefficient_reading"},{"type":"null"}]}},"required":["endpoint","common"],"additionalProperties":false}},"required":["kind","multiplier_exact","status","model_key","source_witnesses","coefficient_readings"],"additionalProperties":false},"covariance_block":{"type":"object","properties":{"source_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"artifact_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"roles":{"type":"array","items":{"enum":["left","right","epsilon_signal","epsilon_nuisance","nuisance"]},"uniqueItems":true},"owner_keys":{"type":"array","items":{"type":"string","minLength":1}},"units":{"type":"array","items":{"type":"string","minLength":1}},"dependency_keys":{"type":"array","items":{"type":"array","items":{"type":"string","minLength":1},"uniqueItems":true}},"matrix_exact":{"anyOf":[{"type":"array","items":{"type":"array","items":{"$ref":"#/$defs/exact"}}},{"type":"null"}]},"basis":{"const":"joint_covariance_of_selected_estimates"},"variance_status":{"enum":["known","estimated","unknown"]},"origin":{"enum":["reported","derived","synthetic"]},"systematic_coverage":{"enum":["included_as_declared","not_established","identified_unresolved"]},"derivation":{"enum":["reported_estimator_covariance","exact_linear_transform","estimated_from_observations","synthetic_model"]},"status":{"enum":["available","unavailable"]},"reasons":{"$ref":"#/$defs/reasons"},"raw_document_utf8":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]}},"required":["source_ref","artifact_ref","roles","owner_keys","units","dependency_keys","matrix_exact","basis","variance_status","origin","systematic_coverage","derivation","status","reasons","raw_document_utf8"],"additionalProperties":false},"domain_reasons":{"type":"array","items":{"enum":["zero_denominator","positive_values_required_for_log","nonzero_spectral_signal_required","positive_discrepancy_variance_required","nonunique_gls_weights","inconsistent_deterministic_constraint","covariance_invalid_shape","covariance_not_symmetric","covariance_not_positive_semidefinite","covariance_owner_unit_dependency_mismatch","covariance_overlap_conflict","physical_owner_value_conflict","covariance_json_invalid","covariance_basis_status_invalid","covariance_nonfinite_numeric","covariance_estimate_owner_unavailable","zero_plugin_difference_variance","combined_estimate_not_identified_by_plugin_covariance"]},"uniqueItems":true},"exact":{"type":"object","properties":{"numerator":{"type":"string","pattern":"^-?[0-9]+$"},"denominator":{"type":"string","pattern":"^[1-9][0-9]*$"}},"required":["numerator","denominator"],"additionalProperties":false},"implementation_reasons":{"type":"array","items":{"enum":["unsupported_unit","bounded_arithmetic_unimplemented","range_arithmetic_unimplemented","unresolved_native_qualification","opposite_direction_conversion_unimplemented","uncertain_conversion_unimplemented","numerical_model_range"]},"uniqueItems":true},"quantity_value":{"type":"object","properties":{"role":{"enum":["left","right","epsilon_signal","epsilon_nuisance","nuisance"]},"native_token":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"native_value":{"type":["number","null"]},"native_exact":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"canonical_value":{"type":["number","null"]},"canonical_exact":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"canonical_unit":{"enum":["umol/min/mg","umol/min","uM/min","per_min","mM^-1cm^-1",null]},"relation":{"enum":["point","lt","le","gt","ge","range","unresolved"]},"approximate":{"type":"boolean"},"estimator_scale":{"enum":["direct_rate","fitted_asymptote","reported_mean","terminal_amount","parameter_estimate","unknown","conflicting"]},"quantity_kind":{"enum":["apparent_specific_activity","specific_activity","fixed_condition_rate","turnover_rate","terminal_conversion","affinity","extinction_coefficient","unknown","conflicting"]},"semantics":{"enum":["reported_point_estimate","reported_nondetection","reported_negligible","unknown","conflicting"]},"normalization":{"enum":["protein_mass","assayed_molecule_amount","active_molecule_amount","reaction_volume","unnormalized_amount","extinction_unit","other","unknown","conflicting"]},"origin":{"enum":["reported","derived","synthetic"]},"owner_key":{"type":"string","minLength":1},"physical_owner_key":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"dependency_keys":{"type":"array","items":{"type":"string","minLength":1},"uniqueItems":true},"source_locations":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}},"reasons":{"$ref":"#/$defs/reasons"}},"required":["role","native_token","native_value","native_exact","canonical_value","canonical_exact","canonical_unit","relation","approximate","estimator_scale","quantity_kind","semantics","normalization","origin","owner_key","physical_owner_key","dependency_keys","source_locations","reasons"],"additionalProperties":false},"reasons":{"type":"object","properties":{"source":{"$ref":"#/$defs/source_reasons"},"relationship":{"$ref":"#/$defs/relationship_reasons"},"implementation":{"$ref":"#/$defs/implementation_reasons"},"domain":{"$ref":"#/$defs/domain_reasons"}},"required":["source","relationship","implementation","domain"],"additionalProperties":false},"relationship_reasons":{"type":"array","items":{"enum":["construct_not_common","preparation_target_unknown","preparation_target_conflicting","protocols_not_matched","endpoint_conversion_unknown","endpoint_conversion_conflicting","endpoint_incompatible","denominator_not_common","functional_resolution_not_quantitative","attribution_unresolved","validity_unresolved","duplicate_representation_not_replication","shared_estimate_not_replication","common_model_not_selected","common_model_unknown","common_model_conflicting","optical_model_unknown","optical_model_conflicting","estimate_scale_model_unknown","estimate_scale_model_conflicting","coefficient_applicability_unknown","coefficient_applicability_conflicting","nuisance_linkage_unknown","nuisance_linkage_conflicting","scenario_not_selected","scenario_stipulations_unresolved","variance_meaning_mismatch","common_systematic_error_not_assessed"]},"uniqueItems":true},"retained_number":{"type":"object","properties":{"selector":{"type":"object","properties":{"witness":{"$ref":"#/$defs/retained_witness"},"number_start":{"type":"integer","minimum":0},"number_end":{"type":"integer","minimum":1}},"required":["witness","number_start","number_end"],"additionalProperties":false},"raw_token":{"type":"string","minLength":1},"native_exact":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"relation":{"enum":["point","lt","le","gt","ge","range","unresolved"]},"approximate":{"type":"boolean"},"measurement_key":{"type":"string","minLength":1}},"required":["selector","raw_token","native_exact","relation","approximate","measurement_key"],"additionalProperties":false},"retained_quantity":{"type":"object","properties":{"selection":{"$ref":"#/$defs/quantity_selection"},"number":{"anyOf":[{"$ref":"#/$defs/retained_number"},{"type":"null"}]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}},"count_reading":{"anyOf":[{"type":"object","properties":{"raw_token":{"type":"string","minLength":1},"exact_count":{"type":["integer","null"],"minimum":1},"status":{"enum":["exact","qualified","range_or_alternatives","unsupported","not_positive"]},"repetition_basis":{"enum":["independent_preparations","paired_units","technical_repeats","timepoints","unspecified","unknown","conflicting"]}},"required":["raw_token","exact_count","status","repetition_basis"],"additionalProperties":false},{"type":"null"}]},"reported_uncertainty":{"type":"object","properties":{"statistic":{"enum":["sd","sem","ci","unspecified","unreported"]},"magnitude_exact":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"interval_exact":{"anyOf":[{"type":"array","items":{"$ref":"#/$defs/exact"}},{"type":"null"}]},"confidence_level_exact":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"unit":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"meaning":{"const":"reported_spread_not_joint_estimator_covariance"}},"required":["statistic","magnitude_exact","interval_exact","confidence_level_exact","unit","meaning"],"additionalProperties":false},"value":{"$ref":"#/$defs/quantity_value"}},"required":["selection","number","witnesses","count_reading","reported_uncertainty","value"],"additionalProperties":false},"retained_relationships":{"type":"object","properties":{"construct":{"type":"object","properties":{"value":{"enum":["same_construct_supported","intended_variant","different","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"preparation":{"type":"object","properties":{"value":{"enum":["same_preparation_supported","different_preparations_supported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"preparation_target":{"type":"object","properties":{"value":{"enum":["same_preparation_quantity","same_population_estimand_supported","incompatible","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"protocol":{"type":"object","properties":{"value":{"enum":["matched_except_intended_change","additional_differences","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"endpoint":{"type":"object","properties":{"value":{"enum":["same_quantity","fixed_reaction_conversion","complementary","incompatible","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"denominator":{"type":"object","properties":{"value":{"enum":["same_basis_supported","different","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"functional_bearing":{"type":"object","properties":{"value":{"enum":["same_quantitative_assertion","existence_only","partner_dependence_only","complementary","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"attribution":{"type":"object","properties":{"value":{"enum":["isolated_supported","mixed_contributors_identified","unresolved","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"sampling":{"type":"object","properties":{"value":{"enum":["repeated_representation","shared_physical_estimate","paired_observations_supported","independent_preparations_supported","independence_not_established","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"systematic_coverage":{"type":"object","properties":{"value":{"enum":["included_in_selected_covariance","identified_unresolved","not_established","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"left_validity":{"type":"object","properties":{"value":{"enum":["endpoint_quantification_supported","identified_unresolved_interference","corrected_endpoint_supported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"right_validity":{"type":"object","properties":{"value":{"enum":["endpoint_quantification_supported","identified_unresolved_interference","corrected_endpoint_supported","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"left_readout_isolation":{"type":"object","properties":{"value":{"enum":["isolated_signal_supported","mixed_optical_contributions","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false},"right_readout_isolation":{"type":"object","properties":{"value":{"enum":["isolated_signal_supported","mixed_optical_contributions","unknown","conflicting"]},"witnesses":{"type":"array","items":{"$ref":"#/$defs/retained_witness"}}},"required":["value","witnesses"],"additionalProperties":false}},"required":["construct","preparation","preparation_target","protocol","endpoint","denominator","functional_bearing","attribution","sampling","systematic_coverage","left_validity","right_validity","left_readout_isolation","right_readout_isolation"],"additionalProperties":false},"retained_witness":{"type":"object","properties":{"source_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"representation":{"enum":["original","text"]},"start":{"type":"integer","minimum":0},"end":{"type":"integer","minimum":1},"quote":{"type":"string","minLength":1},"artifact_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"}},"required":["source_ref","representation","start","end","quote","artifact_ref"],"additionalProperties":false},"selection":{"type":"object","properties":{"version":{"const":"a105_measurement_comparison_selection_v1"},"source_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"source_kind":{"enum":["primary_source","synthetic_fixture"]},"assertion":{"type":"object","properties":{"question":{"enum":["activity_existence","partner_dependence","quantitative_activity","coupling_compatibility"]},"molecule":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"functional_assertion":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]}},"required":["question","molecule","functional_assertion"],"additionalProperties":false},"quantities":{"type":"object","properties":{"left":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"right":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"epsilon_signal":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"epsilon_nuisance":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"nuisance":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]}},"required":["left","right","epsilon_signal","epsilon_nuisance","nuisance"],"additionalProperties":false},"relationships":{"$ref":"#/$defs/relationships"},"common_quantity":{"type":"object","properties":{"label":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"unit":{"enum":["umol/min/mg","umol/min","uM/min","per_min","unknown"]},"left_conversion":{"$ref":"#/$defs/conversion"},"right_conversion":{"$ref":"#/$defs/conversion"}},"required":["label","unit","left_conversion","right_conversion"],"additionalProperties":false},"common_model":{"anyOf":[{"$ref":"#/$defs/common_model"},{"type":"null"}]},"optical":{"anyOf":[{"$ref":"#/$defs/optical"},{"type":"null"}]},"covariance_source_refs":{"type":"array","items":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"uniqueItems":true},"requested_cells":{"type":"array","items":{"enum":["native_left","native_right","converted_left","converted_right","protocol_difference","protocol_ratio","protocol_log_ratio","common_difference","common_ratio","common_log_ratio","difference_variance","difference_standard_uncertainty","standardized_difference","squared_standardized_difference","weight_left","weight_right","combined_estimate","combined_variance","combined_standard_uncertainty","spectral_multiplier","spectral_multiplier_variance","observed_interference","corrected_estimate","corrected_estimate_variance","required_interference_scenario","required_nuisance_equivalent_scenario"]},"uniqueItems":true}},"required":["version","source_ref","source_kind","assertion","quantities","relationships","common_quantity","common_model","optical","covariance_source_refs","requested_cells"],"additionalProperties":false},"source_reasons":{"type":"array","items":{"enum":["quantity_not_selected","source_number_unreported","source_unit_unreported","native_nondetection_not_point","native_negligible_not_point","source_semantics_unknown","source_semantics_conflicting","reported_uncertainty_not_joint_covariance","nuisance_quantity_unmeasured","covariance_not_supplied","joint_covariance_incomplete","covariance_status_unknown"]},"uniqueItems":true},"cell":{"type":"object","properties":{"component":{"enum":["native_left","native_right","converted_left","converted_right","protocol_difference","protocol_ratio","protocol_log_ratio","common_difference","common_ratio","common_log_ratio","difference_variance","difference_standard_uncertainty","standardized_difference","squared_standardized_difference","weight_left","weight_right","combined_estimate","combined_variance","combined_standard_uncertainty","spectral_multiplier","spectral_multiplier_variance","observed_interference","corrected_estimate","corrected_estimate_variance","required_interference_scenario","required_nuisance_equivalent_scenario"]},"value":{"type":["number","null"]},"exact_value":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"conditional_value":{"type":["number","null"]},"conditional_exact_value":{"anyOf":[{"$ref":"#/$defs/exact"},{"type":"null"}]},"status":{"enum":["populated","conditional_scenario","unavailable"]},"unit":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"relation":{"enum":["point","lt","le","gt","ge","range","unresolved"]},"approximate":{"type":"boolean"},"interpretation":{"enum":["native_report","supported_reexpression","descriptive_protocol_comparison","common_estimand_comparison","known_covariance_standardization","estimated_covariance_plugin_standardization","known_covariance_common_estimate","estimated_covariance_plugin_common_estimate","spectral_sensitivity","supported_estimate_scale_correction","first_order_known_input_covariance","first_order_estimated_input_covariance","stipulated_report_scale_scenario","unavailable","protocol_difference_uncertainty_known_covariance","protocol_difference_uncertainty_estimated_covariance"]},"formula":{"enum":["native_estimate","c_left*x_left","c_right*x_right","L-R","L/R","ln(L)-ln(R)","c_left^2*Cll+c_right^2*Crr-2*c_left*c_right*Clr","sqrt(V_D)","D/sqrt(V_D)","D^2/V_D","(V_R-C_LR)/(V_L+V_R-2*C_LR)","(V_L-C_LR)/(V_L+V_R-2*C_LR)","if(V_D>0,w_L*L+w_R*R,if(V_D==0&&D==0,L,unavailable))","if(V_D>0,(V_L*V_R-C_LR^2)/V_D,if(V_D==0&&D==0,V_L,unavailable))","sqrt(V_combined)","epsilon_nuisance/epsilon_signal","J_alpha*C_epsilon*J_alpha_transpose","s*alpha*f","y-s*alpha*f","J_h*C_y_epsilon_f*J_h_transpose","y-H","(y-H)/(s*alpha)"]},"meaning_code":{"enum":["native_left","native_right","converted_left","converted_right","protocol_difference","protocol_ratio","protocol_log_ratio","common_difference","common_ratio","common_log_ratio","difference_variance","difference_standard_uncertainty","standardized_difference","squared_standardized_difference","weight_left","weight_right","combined_estimate","combined_variance","combined_standard_uncertainty","spectral_multiplier","spectral_multiplier_variance","observed_interference","corrected_estimate","corrected_estimate_variance","required_interference_scenario","required_nuisance_equivalent_scenario"]},"origin":{"enum":["reported","derived","synthetic","proposed"]},"input_origins":{"type":"array","items":{"enum":["reported","derived","synthetic","proposed"]},"uniqueItems":true},"operand_roles":{"type":"array","items":{"enum":["left","right","epsilon_signal","epsilon_nuisance","nuisance"]},"uniqueItems":true},"operand_keys":{"type":"array","items":{"type":"string","minLength":1},"uniqueItems":true},"model_keys":{"type":"array","items":{"type":"string","minLength":1},"uniqueItems":true},"contribution_key":{"type":"string","minLength":1},"uncertainty":{"type":"object","properties":{"covariance_source_refs":{"type":"array","items":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"uniqueItems":true},"variance_status":{"enum":["not_selected","known","estimated","unknown"]},"scope":{"enum":["not_applicable","selected_estimator_covariance","first_order_operand_propagation"]},"sampling_distribution":{"const":"not_assumed"}},"required":["covariance_source_refs","variance_status","scope","sampling_distribution"],"additionalProperties":false},"reasons":{"$ref":"#/$defs/reasons"}},"required":["component","value","exact_value","conditional_value","conditional_exact_value","status","unit","relation","approximate","interpretation","formula","meaning_code","origin","input_origins","operand_roles","operand_keys","model_keys","contribution_key","uncertainty","reasons"],"additionalProperties":false,"allOf":[{"if":{"properties":{"component":{"const":"native_left"}}},"then":{"properties":{"formula":{"const":"native_estimate"},"meaning_code":{"const":"native_left"}}}},{"if":{"properties":{"component":{"const":"native_right"}}},"then":{"properties":{"formula":{"const":"native_estimate"},"meaning_code":{"const":"native_right"}}}},{"if":{"properties":{"component":{"const":"converted_left"}}},"then":{"properties":{"formula":{"const":"c_left*x_left"},"meaning_code":{"const":"converted_left"}}}},{"if":{"properties":{"component":{"const":"converted_right"}}},"then":{"properties":{"formula":{"const":"c_right*x_right"},"meaning_code":{"const":"converted_right"}}}},{"if":{"properties":{"component":{"const":"protocol_difference"}}},"then":{"properties":{"formula":{"const":"L-R"},"meaning_code":{"const":"protocol_difference"}}}},{"if":{"properties":{"component":{"const":"protocol_ratio"}}},"then":{"properties":{"formula":{"const":"L/R"},"meaning_code":{"const":"protocol_ratio"}}}},{"if":{"properties":{"component":{"const":"protocol_log_ratio"}}},"then":{"properties":{"formula":{"const":"ln(L)-ln(R)"},"meaning_code":{"const":"protocol_log_ratio"}}}},{"if":{"properties":{"component":{"const":"common_difference"}}},"then":{"properties":{"formula":{"const":"L-R"},"meaning_code":{"const":"common_difference"}}}},{"if":{"properties":{"component":{"const":"common_ratio"}}},"then":{"properties":{"formula":{"const":"L/R"},"meaning_code":{"const":"common_ratio"}}}},{"if":{"properties":{"component":{"const":"common_log_ratio"}}},"then":{"properties":{"formula":{"const":"ln(L)-ln(R)"},"meaning_code":{"const":"common_log_ratio"}}}},{"if":{"properties":{"component":{"const":"difference_variance"}}},"then":{"properties":{"formula":{"const":"c_left^2*Cll+c_right^2*Crr-2*c_left*c_right*Clr"},"meaning_code":{"const":"difference_variance"}}}},{"if":{"properties":{"component":{"const":"difference_standard_uncertainty"}}},"then":{"properties":{"formula":{"const":"sqrt(V_D)"},"meaning_code":{"const":"difference_standard_uncertainty"}}}},{"if":{"properties":{"component":{"const":"standardized_difference"}}},"then":{"properties":{"formula":{"const":"D/sqrt(V_D)"},"meaning_code":{"const":"standardized_difference"}}}},{"if":{"properties":{"component":{"const":"squared_standardized_difference"}}},"then":{"properties":{"formula":{"const":"D^2/V_D"},"meaning_code":{"const":"squared_standardized_difference"}}}},{"if":{"properties":{"component":{"const":"weight_left"}}},"then":{"properties":{"formula":{"const":"(V_R-C_LR)/(V_L+V_R-2*C_LR)"},"meaning_code":{"const":"weight_left"}}}},{"if":{"properties":{"component":{"const":"weight_right"}}},"then":{"properties":{"formula":{"const":"(V_L-C_LR)/(V_L+V_R-2*C_LR)"},"meaning_code":{"const":"weight_right"}}}},{"if":{"properties":{"component":{"const":"combined_estimate"}}},"then":{"properties":{"formula":{"const":"if(V_D>0,w_L*L+w_R*R,if(V_D==0&&D==0,L,unavailable))"},"meaning_code":{"const":"combined_estimate"}}}},{"if":{"properties":{"component":{"const":"combined_variance"}}},"then":{"properties":{"formula":{"const":"if(V_D>0,(V_L*V_R-C_LR^2)/V_D,if(V_D==0&&D==0,V_L,unavailable))"},"meaning_code":{"const":"combined_variance"}}}},{"if":{"properties":{"component":{"const":"combined_standard_uncertainty"}}},"then":{"properties":{"formula":{"const":"sqrt(V_combined)"},"meaning_code":{"const":"combined_standard_uncertainty"}}}},{"if":{"properties":{"component":{"const":"spectral_multiplier"}}},"then":{"properties":{"formula":{"const":"epsilon_nuisance/epsilon_signal"},"meaning_code":{"const":"spectral_multiplier"}}}},{"if":{"properties":{"component":{"const":"spectral_multiplier_variance"}}},"then":{"properties":{"formula":{"const":"J_alpha*C_epsilon*J_alpha_transpose"},"meaning_code":{"const":"spectral_multiplier_variance"}}}},{"if":{"properties":{"component":{"const":"observed_interference"}}},"then":{"properties":{"formula":{"const":"s*alpha*f"},"meaning_code":{"const":"observed_interference"}}}},{"if":{"properties":{"component":{"const":"corrected_estimate"}}},"then":{"properties":{"formula":{"const":"y-s*alpha*f"},"meaning_code":{"const":"corrected_estimate"}}}},{"if":{"properties":{"component":{"const":"corrected_estimate_variance"}}},"then":{"properties":{"formula":{"const":"J_h*C_y_epsilon_f*J_h_transpose"},"meaning_code":{"const":"corrected_estimate_variance"}}}},{"if":{"properties":{"component":{"const":"required_interference_scenario"}}},"then":{"properties":{"formula":{"const":"y-H"},"meaning_code":{"const":"required_interference_scenario"}}}},{"if":{"properties":{"component":{"const":"required_nuisance_equivalent_scenario"}}},"then":{"properties":{"formula":{"const":"(y-H)/(s*alpha)"},"meaning_code":{"const":"required_nuisance_equivalent_scenario"}}}},{"if":{"properties":{"status":{"const":"populated"}}},"then":{"properties":{"value":{"type":"number"},"conditional_value":{"type":"null"},"conditional_exact_value":{"type":"null"}}}},{"if":{"properties":{"status":{"const":"conditional_scenario"}}},"then":{"properties":{"value":{"type":"null"},"exact_value":{"type":"null"},"conditional_value":{"type":"number"}}}},{"if":{"properties":{"status":{"const":"unavailable"}}},"then":{"properties":{"value":{"type":"null"},"exact_value":{"type":"null"},"conditional_value":{"type":"null"},"conditional_exact_value":{"type":"null"}}}}]}},"resources":{"SELECTION":{"body":{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:a105:measurement-comparison:258:plan004:selection","type":"object","properties":{"version":{"const":"a105_measurement_comparison_selection_v1"},"source_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"source_kind":{"enum":["primary_source","synthetic_fixture"]},"assertion":{"type":"object","properties":{"question":{"enum":["activity_existence","partner_dependence","quantitative_activity","coupling_compatibility"]},"molecule":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"functional_assertion":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]}},"required":["question","molecule","functional_assertion"],"additionalProperties":false},"quantities":{"type":"object","properties":{"left":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"right":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"epsilon_signal":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"epsilon_nuisance":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]},"nuisance":{"anyOf":[{"$ref":"#/$defs/quantity_selection"},{"type":"null"}]}},"required":["left","right","epsilon_signal","epsilon_nuisance","nuisance"],"additionalProperties":false},"relationships":{"$ref":"#/$defs/relationships"},"common_quantity":{"type":"object","properties":{"label":{"anyOf":[{"$ref":"#/$defs/witness"},{"type":"null"}]},"unit":{"enum":["umol/min/mg","umol/min","uM/min","per_min","unknown"]},"left_conversion":{"$ref":"#/$defs/conversion"},"right_conversion":{"$ref":"#/$defs/conversion"}},"required":["label","unit","left_conversion","right_conversion"],"additionalProperties":false},"common_model":{"anyOf":[{"$ref":"#/$defs/common_model"},{"type":"null"}]},"optical":{"anyOf":[{"$ref":"#/$defs/optical"},{"type":"null"}]},"covariance_source_refs":{"type":"array","items":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"uniqueItems":true},"requested_cells":{"type":"array","items":{"enum":["native_left","native_right","converted_left","converted_right","protocol_difference","protocol_ratio","protocol_log_ratio","common_difference","common_ratio","common_log_ratio","difference_variance","difference_standard_uncertainty","standardized_difference","squared_standardized_difference","weight_left","weight_right","combined_estimate","combined_variance","combined_standard_uncertainty","spectral_multiplier","spectral_multiplier_variance","observed_interference","corrected_estimate","corrected_estimate_variance","required_interference_scenario","required_nuisance_equivalent_scenario"]},"uniqueItems":true}},"required":["version","source_ref","source_kind","assertion","quantities","relationships","common_quantity","common_model","optical","covariance_source_refs","requested_cells"],"additionalProperties":false},"definition_names":["coefficient","common_model","conversion","model_meaning","number_selector","optical","quantity_selection","relationships","uncertainty_selection","unit_definition","unit_selection","witness"]},"EXTRACTION":{"body":{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:a105:measurement-comparison:258:plan004:extraction","type":"object","properties":{"version":{"const":"a105_measurement_comparison_extraction_v2"},"selection":{"$ref":"#/$defs/selection"},"quantities":{"type":"object","properties":{"left":{"anyOf":[{"$ref":"#/$defs/retained_quantity"},{"type":"null"}]},"right":{"anyOf":[{"$ref":"#/$defs/retained_quantity"},{"type":"null"}]},"epsilon_signal":{"anyOf":[{"$ref":"#/$defs/retained_quantity"},{"type":"null"}]},"epsilon_nuisance":{"anyOf":[{"$ref":"#/$defs/retained_quantity"},{"type":"null"}]},"nuisance":{"anyOf":[{"$ref":"#/$defs/retained_quantity"},{"type":"null"}]}},"required":["left","right","epsilon_signal","epsilon_nuisance","nuisance"],"additionalProperties":false},"relationships":{"$ref":"#/$defs/retained_relationships"},"conversions":{"type":"object","properties":{"left":{"$ref":"#/$defs/conversion_value"},"right":{"$ref":"#/$defs/conversion_value"}},"required":["left","right"],"additionalProperties":false},"covariance_blocks":{"type":"array","items":{"$ref":"#/$defs/covariance_block"}},"source_refs":{"type":"array","items":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"uniqueItems":true},"source_artifacts":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"artifact_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"representation":{"enum":["original","text"]}},"required":["source_ref","artifact_ref","representation"],"additionalProperties":false}},"dependency_fingerprints":{"type":"array","items":{"type":"object","properties":{"module":{"type":"string","minLength":1},"sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"}},"required":["module","sha256"],"additionalProperties":false}}},"required":["version","selection","quantities","relationships","conversions","covariance_blocks","source_refs","source_artifacts","dependency_fingerprints"],"additionalProperties":false},"definition_names":["coefficient","coefficient_reading","common_model","conversion","conversion_value","covariance_block","domain_reasons","exact","implementation_reasons","model_meaning","number_selector","optical","quantity_selection","quantity_value","reasons","relationship_reasons","relationships","retained_number","retained_quantity","retained_relationships","retained_witness","selection","source_reasons","uncertainty_selection","unit_definition","unit_selection","witness"]},"CALCULATION_INPUTS":{"body":{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:a105:measurement-comparison:258:plan004:calculation_inputs","type":"object","properties":{"version":{"const":"a105_measurement_comparison_calculation_inputs_v2"},"selection":{"$ref":"#/$defs/selection"},"quantities":{"type":"object","properties":{"left":{"anyOf":[{"$ref":"#/$defs/quantity_value"},{"type":"null"}]},"right":{"anyOf":[{"$ref":"#/$defs/quantity_value"},{"type":"null"}]},"epsilon_signal":{"anyOf":[{"$ref":"#/$defs/quantity_value"},{"type":"null"}]},"epsilon_nuisance":{"anyOf":[{"$ref":"#/$defs/quantity_value"},{"type":"null"}]},"nuisance":{"anyOf":[{"$ref":"#/$defs/quantity_value"},{"type":"null"}]}},"required":["left","right","epsilon_signal","epsilon_nuisance","nuisance"],"additionalProperties":false},"conversions":{"type":"object","properties":{"left":{"$ref":"#/$defs/conversion_value"},"right":{"$ref":"#/$defs/conversion_value"}},"required":["left","right"],"additionalProperties":false},"relationships":{"$ref":"#/$defs/retained_relationships"},"covariance_blocks":{"type":"array","items":{"$ref":"#/$defs/covariance_block"}},"assertion_key":{"type":"string","minLength":1},"contribution_key":{"type":"string","minLength":1},"source_artifacts":{"type":"array","items":{"type":"object","properties":{"source_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"artifact_ref":{"type":"string","pattern":"^[a-z][a-z_]*_[a-f0-9]{24,64}$"},"representation":{"enum":["original","text"]}},"required":["source_ref","artifact_ref","representation"],"additionalProperties":false}}},"required":["version","selection","quantities","conversions","relationships","covariance_blocks","assertion_key","contribution_key","source_artifacts"],"additionalProperties":false},"definition_names":["coefficient","coefficient_reading","common_model","conversion","conversion_value","covariance_block","domain_reasons","exact","implementation_reasons","model_meaning","number_selector","optical","quantity_selection","quantity_value","reasons","relationship_reasons","relationships","retained_number","retained_relationships","retained_witness","selection","source_reasons","uncertainty_selection","unit_definition","unit_selection","witness"]},"SHEET":{"body":{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:a105:measurement-comparison:258:plan004:sheet","type":"object","properties":{"version":{"const":"a105_measurement_comparison_sheet_v1"},"axis":{"const":"A105"},"section":{"const":"measurement_comparison_validity"},"assertion_key":{"type":"string","minLength":1},"contribution_key":{"type":"string","minLength":1},"cells":{"type":"array","items":{"$ref":"#/$defs/cell"}},"relationship_meanings":{"type":"object","properties":{"construct":{"enum":["same_construct_supported","intended_variant","different","unknown","conflicting"]},"preparation":{"enum":["same_preparation_supported","different_preparations_supported","unknown","conflicting"]},"preparation_target":{"enum":["same_preparation_quantity","same_population_estimand_supported","incompatible","unknown","conflicting"]},"protocol":{"enum":["matched_except_intended_change","additional_differences","unknown","conflicting"]},"endpoint":{"enum":["same_quantity","fixed_reaction_conversion","complementary","incompatible","unknown","conflicting"]},"denominator":{"enum":["same_basis_supported","different","unknown","conflicting"]},"functional_bearing":{"enum":["same_quantitative_assertion","existence_only","partner_dependence_only","complementary","unknown","conflicting"]},"attribution":{"enum":["isolated_supported","mixed_contributors_identified","unresolved","unknown","conflicting"]},"sampling":{"enum":["repeated_representation","shared_physical_estimate","paired_observations_supported","independent_preparations_supported","independence_not_established","unknown","conflicting"]},"systematic_coverage":{"enum":["included_in_selected_covariance","identified_unresolved","not_established","unknown","conflicting"]},"left_validity":{"enum":["endpoint_quantification_supported","identified_unresolved_interference","corrected_endpoint_supported","unknown","conflicting"]},"right_validity":{"enum":["endpoint_quantification_supported","identified_unresolved_interference","corrected_endpoint_supported","unknown","conflicting"]},"left_readout_isolation":{"enum":["isolated_signal_supported","mixed_optical_contributions","unknown","conflicting"]},"right_readout_isolation":{"enum":["isolated_signal_supported","mixed_optical_contributions","unknown","conflicting"]}},"required":["construct","preparation","preparation_target","protocol","endpoint","denominator","functional_bearing","attribution","sampling","systematic_coverage","left_validity","right_validity","left_readout_isolation","right_readout_isolation"],"additionalProperties":false},"estimate_bindings":{"type":"array","items":{"type":"object","properties":{"role":{"enum":["left","right","epsilon_signal","epsilon_nuisance","nuisance"]},"owner_key":{"type":"string","minLength":1},"physical_owner_key":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"dependency_keys":{"type":"array","items":{"type":"string","minLength":1},"uniqueItems":true},"unit":{"anyOf":[{"type":"string","minLength":1},{"type":"null"}]},"estimator_scale":{"enum":["direct_rate","fitted_asymptote","reported_mean","terminal_amount","parameter_estimate","unknown","conflicting"]}},"required":["role","owner_key","physical_owner_key","dependency_keys","unit","estimator_scale"],"additionalProperties":false}},"dependence":{"type":"array","items":{"type":"object","properties":{"roles":{"type":"array","items":{"enum":["left","right","epsilon_signal","epsilon_nuisance","nuisance"]},"uniqueItems":true},"relation":{"enum":["shared_primitive","repeated_representation","shared_physical_estimate","sampling_unknown","paired_observations_supported","independent_preparations_supported","complementary_endpoint"]}},"required":["roles","relation"],"additionalProperties":false}},"assumptions":{"type":"array","items":{"enum":["common_unbiased_quantity_model","fixed_reaction_conversion","linear_mixture_on_selected_estimate_scale","common_rate_equality_stipulated","linear_estimate_scale_mapping_stipulated","first_order_covariance_propagation","estimated_weights_treated_as_plugin","no_reference_distribution_assumed"]},"uniqueItems":true},"annotation_credit":{"type":"null"},"remaining_limits":{"type":"array","items":{"enum":["standalone_components_not_selected_integration","same_estimate_ratio_log_difference_are_dependent","agreement_does_not_detect_shared_bias","source_positive_matched_covariance_case_still_open","general_A105_adequacy_unfinished","no_target_transfer_or_W05","corrected_quantity_not_automatically_substituted_into_common_pair","unknown_systematics_not_set_to_zero"]},"uniqueItems":true}},"required":["version","axis","section","assertion_key","contribution_key","cells","relationship_meanings","estimate_bindings","dependence","assumptions","annotation_credit","remaining_limits"],"additionalProperties":false},"definition_names":["cell","domain_reasons","exact","implementation_reasons","reasons","relationship_reasons","source_reasons"]},"COVARIANCE_DOCUMENT":{"body":{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:a105:measurement-comparison:258:plan004:covariance_document","type":"object","properties":{"version":{"const":"a105_measurement_comparison_covariance_v1"},"roles":{"type":"array","items":{"enum":["left","right","epsilon_signal","epsilon_nuisance","nuisance"]},"uniqueItems":true},"owner_keys":{"type":"array","items":{"type":"string","minLength":1}},"units":{"type":"array","items":{"type":"string","minLength":1}},"dependency_keys":{"type":"array","items":{"type":"array","items":{"type":"string","minLength":1},"uniqueItems":true}},"covariance":{"anyOf":[{"type":"array","items":{"type":"array","items":{"type":"number"}}},{"type":"null"}]},"basis":{"const":"joint_covariance_of_selected_estimates"},"variance_status":{"enum":["known","estimated","unknown"]},"origin":{"enum":["reported","derived","synthetic"]},"systematic_coverage":{"enum":["included_as_declared","not_established","identified_unresolved"]},"derivation":{"enum":["reported_estimator_covariance","exact_linear_transform","estimated_from_observations","synthetic_model"]}},"required":["version","roles","owner_keys","units","dependency_keys","covariance","basis","variance_status","origin","systematic_coverage","derivation"],"additionalProperties":false},"definition_names":[]}}}')

_ROLES = ('left', 'right', 'epsilon_signal', 'epsilon_nuisance', 'nuisance')
_DEPENDENCIES = (
    'literature_assay_inputs', 'literature_partner_source_fields',
    'literature_rate_native_inputs', 'literature_partner_defined_units',
    'literature_kinetic_inputs', 'literature_measurement_validation_inputs',
    'literature_product_coupling_inputs', 'literature_optical_inputs',
)


def _resource(name):
    resource = _SCHEMA_BUNDLE['resources'][name]
    return {**deepcopy(resource['body']), '$defs': {
        key: deepcopy(_SCHEMA_BUNDLE['definitions'][key]) for key in resource['definition_names']}}


def measurement_comparison_selection_schema(): return _resource('SELECTION')
def measurement_comparison_extraction_schema(): return _resource('EXTRACTION')
def measurement_comparison_calculation_inputs_schema(): return _resource('CALCULATION_INPUTS')
def measurement_comparison_covariance_schema(): return _resource('COVARIANCE_DOCUMENT')


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _q(value):
    result = Fraction(int(value['numerator']), int(value['denominator']))
    if _exact(result) != value:
        _fail('canonical_exact_fraction_required', 'exact')
    return result


def _exact(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _float(value):
    try:
        result = float(value)
    except (ArithmeticError, ValueError):
        return None
    return result if math.isfinite(result) and (result != 0 or value == 0) else None


def _reasons():
    return dict(source=[], relationship=[], implementation=[], domain=[])


def _merge(*groups):
    result = _reasons()
    for group in groups:
        for name in result:
            result[name] = list(dict.fromkeys([*result[name], *group[name]]))
    return result


def _location(w):
    return {k: w[k] for k in ('source_ref', 'artifact_ref', 'representation', 'start', 'end')}


def _measurement_key(w, start, end):
    return identity('literature_measurement', dict(artifact_ref=w['artifact_ref'], number_start=start, number_end=end))


def _physical_key(w):
    return identity('physical_source_span', dict(artifact_ref=w['artifact_ref'], start=w['start'], end=w['end']))


def _interpret(value, sources, field):
    return _native_interpret(value, sources, field)


def _read_scalar(selector, sources):
    w = sources.witness(selector['witness'], 'number.witness')
    a, z = selector['number_start'], selector['number_end']
    if not 0 <= a < z <= len(w['quote']): _fail('source_number_span_order_invalid', 'number')
    start, end = w['start'] + len(w['quote'][:a].encode()), w['start'] + len(w['quote'][:z].encode())
    _visible_span(sources, w, start, end, 'number')
    raw = w['quote'][a:z]
    reason = None
    exact = None
    if re.fullmatch(r'(?:ND|N\.?D\.?|not\s+detected|nondetected)', raw, re.I):
        item = _nondetection_number(selector, sources, 'reported')
        relation, approximate = 'unresolved', False
        reason = 'native_nondetection_not_point'
    elif _RANGE.fullmatch(raw):
        item = _read_number(selector, sources, 'reported')
        relation, approximate = 'range', False
        reason = 'range_arithmetic_unimplemented'
    else:
        try:
            item = _number(selector, sources, 'rate')
            relation, approximate = item['relation'], item['approximate']
            exact = Fraction(raw.replace('−', '-'))
        except ExperimentalContractError as error:
            if error.code != 'numerical_model_range': raise
            # The shared reader has already checked complete tokens/context.
            relation, approximate = 'unresolved', False
            reason = 'numerical_model_range'
    return {'selector': {**deepcopy(selector), 'witness': w}, 'raw_token': raw,
        'native_exact': None if exact is None else _exact(exact), 'relation': relation,
        'approximate': approximate, 'measurement_key': _measurement_key(w, start, end)}, reason


def _numeric_location(number):
    s = number['selector']; w = s['witness']; a, z = s['number_start'], s['number_end']
    return {**w, 'start': w['start'] + len(w['quote'][:a].encode()),
        'end': w['start'] + len(w['quote'][:z].encode()), 'quote': number['raw_token'],
        'number_start_bytes': w['start'] + len(w['quote'][:a].encode()),
        'number_end_bytes': w['start'] + len(w['quote'][:z].encode())}


def _association(selected, number, witnesses, sources):
    if number is None: return
    numeric = _numeric_location(number)
    labels = {name: None if selected[name] is None else sources.witness(selected[name], name)
              for name in ('record', 'row_label', 'quantity_label')}
    rawunit = selected['unit']
    unit = None if rawunit is None else sources.witness(rawunit.get('witness', rawunit), 'unit')
    if labels['quantity_label'] is None: _fail('selected_quantity_label_required', 'quantity_label')
    for name, w in (*labels.items(), ('unit', unit)):
        if w is None: continue
        if w['artifact_ref'] != numeric['artifact_ref'] or w['representation'] != numeric['representation']:
            _fail('borrowed_source_quantity_witness', name)
        _visible_span(sources, w, w['start'], w['end'], name)
    table, cells = _table_cells(sources, numeric)
    if selected['layout'] == 'table':
        cell = next((c for c in cells if c['start'] <= numeric['start'] < numeric['end'] <= c['end']), None)
        row = labels['row_label']
        rowcell = next((c for c in cells if row is not None and c['start'] <= row['start'] < row['end'] <= c['end']), None)
        if table is None or cell is None or rowcell is None or rowcell['row'] != cell['row'] or max(rowcell['columns']) >= min(cell['columns']):
            _fail('comparison_source_row_mismatch', 'row_label')
        bound = {**number, 'number_start_bytes': numeric['start'], 'number_end_bytes': numeric['end']}
        _associate(bound, labels['quantity_label'], sources, 'quantity_label')
        if unit is not None: _associate(bound, unit, sources, 'unit')
    else:
        record = labels['record']
        if table is not None or record is None or any(w is not None and not record['start'] <= w['start'] < w['end'] <= record['end']
            for w in (numeric, labels['row_label'], labels['quantity_label'], unit)):
            _fail('comparison_labelled_record_association_required', 'record')
        # A narrow labelled record cannot borrow another unassigned magnitude.
        rest = bytearray(record['quote'].encode())
        for w in (numeric, labels['row_label'], labels['quantity_label'], unit):
            if w:
                a, z = w['start'] - record['start'], w['end'] - record['start']
                rest[a:z] = b' ' * (z-a)
        if re.search(rb'(?<![A-Za-z0-9_])[0-9]+(?:\.[0-9]+)?', rest):
            _fail('ambiguous_comparison_record_numbers', 'record')


def _quantity(role, selected, sources, origin):
    if selected is None: return None
    before = set(sources.cache)
    meanings = {name: _interpret(selected[name], sources, role+'.'+name) for name in
                ('quantity_kind', 'estimator_scale', 'semantics', 'qualification', 'normalization')}
    retained_witnesses = []
    def authenticate(value):
        if isinstance(value, dict):
            if set(value) == {'source_ref','representation','start','end','quote'}:
                w = sources.witness(value, role)
                if w not in retained_witnesses: retained_witnesses.append(w)
            else:
                for child in value.values(): authenticate(child)
        elif isinstance(value, list):
            for child in value: authenticate(child)
    authenticate(selected)
    number, numeric_reason = (None, 'source_number_unreported') if selected['number'] is None else _read_scalar(selected['number'], sources)
    _association(selected, number, retained_witnesses, sources)
    reasons = _reasons()
    if numeric_reason:
        family = 'implementation' if numeric_reason in ('numerical_model_range','range_arithmetic_unimplemented') else 'source'
        reasons[family].append(numeric_reason)
    unit = None
    scale = None
    if selected['unit'] is None: reasons['source'].append('source_unit_unreported')
    else:
        raw = selected['unit']; raw_w = raw.get('witness', raw)
        if role.startswith('epsilon'):
            if 'kind' in raw: _fail('extinction_unit_not_activity_definition', role)
            unit = _optical_unit(raw, 'epsilon', sources)
            if unit['canonical_unit']:
                scale = _UNIT_TABLES['epsilon'][_normalize(unit['raw_unit'])][1]
                if number is not None and number['native_exact'] is not None:
                    ns = number['selector']; n = {'selector':ns,'raw_number':number['raw_token']}
                    _optical_explicit_unit(n, unit, 'epsilon', sources)
        else:
            endpoint = selected['assay']['direct_endpoint']
            unit = _comparison_unit(raw, sources, endpoint)
            if unit['canonical_unit']:
                scale = _comparison_scale(unit)
                if number is not None and number['native_exact'] is not None:
                    _check_explicit_unit({'selector': number['selector'], 'raw_number':number['raw_token']}, unit, sources)
        if unit['canonical_unit'] is None: reasons['implementation'].append('unsupported_unit')
    semantics = meanings['semantics']['value']
    if semantics in ('reported_nondetection','reported_negligible'):
        reasons['source'].append('native_nondetection_not_point' if semantics == 'reported_nondetection' else 'native_negligible_not_point')
    elif semantics in ('unknown','conflicting'): reasons['source'].append('source_semantics_'+semantics)
    if meanings['qualification']['value'] in ('unknown','conflicting'): reasons['implementation'].append('unresolved_native_qualification')
    if role.startswith('epsilon') and meanings['quantity_kind']['value']!='extinction_coefficient':reasons['source'].append('source_semantics_unknown')
    exact = None if number is None or number['native_exact'] is None else _q(number['native_exact'])
    canonical = None if exact is None or scale is None else exact*scale
    canonical_float = None if canonical is None else _float(canonical)
    if canonical is not None and canonical_float is None: reasons['implementation'].append('numerical_model_range')
    if number is not None and number['relation'] in ('lt','le','gt','ge'): reasons['implementation'].append('bounded_arithmetic_unimplemented')
    expected_normalization={'umol/min/mg':('protein_mass',),'umol/min':('unnormalized_amount',),'uM/min':('reaction_volume',),'per_min':('assayed_molecule_amount','active_molecule_amount'),'mM^-1cm^-1':('extinction_unit',)}
    if unit is not None and unit['canonical_unit'] in expected_normalization and meanings['normalization']['value'] not in expected_normalization[unit['canonical_unit']]: reasons['relationship'].append('denominator_not_common')
    physical = selected['physical_identity']
    physical = None if physical is None else sources.witness(physical, 'physical_identity')
    dependencies = [sources.witness(w, 'dependency') for w in selected['dependency_witnesses']]
    owner = identity('unreported_comparison_estimate', selected) if number is None else number['measurement_key']
    deps = list(dict.fromkeys([owner]+[_physical_key(w) for w in dependencies]))
    locations = [] if number is None else [{k:v for k,v in _numeric_location(number).items() if k not in ('number_start_bytes','number_end_bytes')}]
    value = dict(role=role, native_token=None if number is None else number['raw_token'],
        native_value=None if exact is None else _float(exact), native_exact=None if exact is None else _exact(exact),
        canonical_value=canonical_float, canonical_exact=None if canonical is None else _exact(canonical),
        canonical_unit=None if unit is None else unit['canonical_unit'], relation='unresolved' if number is None else number['relation'],
        approximate=bool(number and number['approximate'] or meanings['qualification']['value'] in ('rounded_after_fit','source_qualified_approximate')),
        estimator_scale=meanings['estimator_scale']['value'], quantity_kind=meanings['quantity_kind']['value'], semantics=semantics,
        normalization=meanings['normalization']['value'], origin=origin, owner_key=owner,
        physical_owner_key=None if physical is None else _physical_key(physical), dependency_keys=deps,
        source_locations=locations, reasons=reasons)
    unc = selected['uncertainty']
    for field in ('statistic','unit_relationship','repetition_basis','estimate_basis'): _interpret(unc[field], sources, 'uncertainty.'+field)
    statistic = unc['statistic']['value']
    magnitude = None if unc['magnitude'] is None else _number(unc['magnitude'], sources, 'spread')
    interval = _interval(unc['interval'], sources)
    confidence = _confidence(unc['confidence_level'], sources)
    if ((statistic == 'unreported' and (magnitude or interval or confidence)) or statistic == 'ci' and magnitude
            or statistic != 'ci' and (interval or confidence)):
        _fail('source_uncertainty_representation_mismatch', 'uncertainty')
    if statistic in ('sd','sem') and not unc['statistic']['witnesses']: _fail('interpretation_witness_required','uncertainty.statistic')
    effective = unit if unc['unit_relationship']['value']=='same_as_estimate' else None
    if unc['unit'] is not None:
        explicit = _optical_unit(unc['unit'], 'epsilon', sources) if role.startswith('epsilon') else _comparison_unit(unc['unit'], sources, selected['assay']['direct_endpoint'])
        if unc['unit_relationship']['value'] == 'same_as_estimate' and unit is not None and (explicit['canonical_unit'], explicit['multiplier']) != (unit['canonical_unit'], unit['multiplier']):
            _fail('source_uncertainty_unit_mismatch', 'uncertainty.unit')
        if unc['unit_relationship']['value'] in ('same_as_estimate','explicit_unit'): effective = explicit
    if magnitude is not None and effective is not None and not role.startswith('epsilon'):
        _check_explicit_unit(magnitude, effective, sources)
    count = _count_reading(unc['count'], sources)
    count = None if count is None else {'raw_token':count['raw_number'],'exact_count': count['value'] if count['status']=='exact' else None,
        'status':count['status'],'repetition_basis':unc['repetition_basis']['value']}
    uncertainty = {'statistic':statistic,'magnitude_exact':None if magnitude is None else _exact(Fraction(magnitude['raw_number'].replace('−','-'))),
        'interval_exact':None if interval is None else [_exact(Fraction(v.replace('−','-'))) for v in interval['raw_values']],
        'confidence_level_exact':None if confidence is None else _exact(Fraction(str(confidence['value']))),
        'unit': None if effective is None else effective['raw_unit'], 'meaning':'reported_spread_not_joint_estimator_covariance'}
    value['reasons']=_merge(value['reasons'])
    return {'selection':deepcopy(selected),'number':number,'witnesses':retained_witnesses,
        'count_reading':count,'reported_uncertainty':uncertainty,'value':value}


def _conversion(selected, sources):
    for name in ('direction','support_status'): _interpret(selected[name], sources, 'conversion.'+name)
    witnesses=[]
    for name in ('reaction','endpoint_species','common_species'):
        if selected[name] is not None:witnesses.append(sources.witness(selected[name],'conversion.'+name))
    status=selected['support_status']['value'];multiplier=None
    readings={'endpoint':None,'common':None};coefficients=[]
    if selected['kind']=='identity':
        if selected['endpoint_coefficient'] is not None or selected['common_coefficient'] is not None:
            _fail('identity_conversion_has_no_selected_coefficients','conversion')
        if status=='supported' and selected['direction']['value']=='same_direction_supported':multiplier=Fraction(1)
    else:
        for side in ('endpoint','common'):
            c=selected[side+'_coefficient']
            if c is None:coefficients.append(None);continue
            support=[sources.witness(w,'conversion.coefficient') for w in c['support']]
            if not support:_fail('interpretation_witness_required',side+'_coefficient')
            witnesses.extend(support)
            if c['origin']=='implicit_unit_coefficient':
                if c['number'] is not None or c['implicit_value']!=_exact(Fraction(1)):
                    _fail('implicit_unit_coefficient_required',side+'_coefficient')
                coefficients.append(Fraction(1))
            else:
                if c['number'] is None or c['implicit_value'] is not None:_fail('source_coefficient_selector_required',side+'_coefficient')
                number,reason=_read_scalar(c['number'],sources)
                numeric=_numeric_location(number)
                context=_field_witness(sources,number['selector']['witness'],numeric['start'],numeric['end'])
                readings[side]={'reading':number,'source_context':context}
                witnesses.extend((number['selector']['witness'],context))
                coefficients.append(_eligible_coefficient(readings[side]))
        if selected['kind']=='fixed_reaction_scale' and status=='supported' and selected['direction']['value']=='same_direction_supported' and None not in coefficients:
            if selected['reaction'] is None:_fail('reaction_conversion_witness_required','conversion')
            if any(c<=0 for c in coefficients):_fail('positive_stoichiometric_coefficient_required','conversion')
            multiplier=coefficients[1]/coefficients[0]
    return {'kind':selected['kind'],'multiplier_exact':None if multiplier is None else _exact(multiplier),
        'status':status,'model_key':identity('measurement_comparison_conversion',selected),
        'source_witnesses':list({json.dumps(w,sort_keys=True):w for w in witnesses}.values()),
        'coefficient_readings':readings}


def _psd(matrix):
    n=len(matrix)
    if any(len(row)!=n for row in matrix): return False
    if any(matrix[i][j]!=matrix[j][i] for i in range(n) for j in range(i)): return False
    work=deepcopy(matrix)
    for k in range(n):
        if any(work[i][i]<0 for i in range(k,n)): return False
        pivot=next((i for i in range(k,n) if work[i][i]>0),None)
        if pivot is None: return not any(work[i][j] for i in range(k,n) for j in range(k,n))
        work[k],work[pivot]=work[pivot],work[k]
        for row in work: row[k],row[pivot]=row[pivot],row[k]
        p=work[k][k]
        for i in range(k+1,n):
            for j in range(k+1,n): work[i][j]-=work[i][k]*work[k][j]/p
    return True


def _covariance(reference, quantities, sources):
    source=sources.source(reference,'original')
    try: text=source['content'].decode('utf8')
    except UnicodeError: text=None
    reasons=_reasons()
    result=dict(source_ref=reference,artifact_ref=source['artifact_ref'],roles=[],owner_keys=[],units=[],dependency_keys=[],
        matrix_exact=None,basis='joint_covariance_of_selected_estimates',variance_status='unknown',origin='derived',
        systematic_coverage='not_established',derivation='reported_estimator_covariance',status='unavailable',reasons=reasons,raw_document_utf8=text)
    def bad(code):
        reasons['domain'].append(code);return result
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('duplicate_json_key')
            out[k]=v
        return out
    def constant(value): raise ValueError('nonfinite_numeric')
    try:
        data=json.loads(text,parse_int=Fraction,parse_float=Fraction,parse_constant=constant,object_pairs_hook=pairs)
    except (ValueError,TypeError): return bad('covariance_json_invalid')
    expected=set(measurement_comparison_covariance_schema()['properties'])
    if not isinstance(data,dict) or set(data)!=expected: return bad('covariance_basis_status_invalid')
    roles=data['roles']
    if not isinstance(roles,list) or not roles or any(r not in _ROLES for r in roles) or len(set(roles))!=len(roles):
        return bad('covariance_invalid_shape')
    if data['version']!='a105_measurement_comparison_covariance_v1' or data['basis']!=result['basis'] or data['variance_status'] not in ('known','estimated','unknown') or data['origin'] not in ('reported','derived','synthetic') or data['derivation'] not in ('reported_estimator_covariance','exact_linear_transform','estimated_from_observations','synthetic_model') or data['systematic_coverage'] not in ('included_as_declared','not_established','identified_unresolved'):
        return bad('covariance_basis_status_invalid')
    if any(quantities[r] is None or quantities[r]['canonical_exact'] is None for r in roles): return bad('covariance_estimate_owner_unavailable')
    values=[quantities[r] for r in roles]
    if (data['owner_keys'] != [v['owner_key'] for v in values] or data['units'] != [v['canonical_unit'] for v in values]
            or data['dependency_keys'] != [v['dependency_keys'] for v in values]):
        return bad('covariance_owner_unit_dependency_mismatch')
    result.update({k:deepcopy(data[k]) for k in ('roles','owner_keys','units','dependency_keys','variance_status','origin','systematic_coverage','derivation')})
    matrix=data['covariance']; n=len(roles)
    if matrix is None:
        if data['variance_status']=='unknown': reasons['source'].append('covariance_status_unknown');return result
        return bad('covariance_invalid_shape')
    if not isinstance(matrix,list) or len(matrix)!=n or any(not isinstance(row,list) or len(row)!=n for row in matrix): return bad('covariance_invalid_shape')
    if any(type(x) is not Fraction for row in matrix for x in row): return bad('covariance_nonfinite_numeric')
    if any(matrix[i][j]!=matrix[j][i] for i in range(n) for j in range(i)): return bad('covariance_not_symmetric')
    if not _psd(matrix): return bad('covariance_not_positive_semidefinite')
    for i in range(n):
        for j in range(i):
            if values[i]['owner_key']==values[j]['owner_key'] and (matrix[i]!=matrix[j] or any(row[i]!=row[j] for row in matrix)):
                return bad('covariance_owner_unit_dependency_mismatch')
    result['matrix_exact']=[[_exact(x) for x in row] for row in matrix]
    if data['variance_status']=='unknown': reasons['source'].append('covariance_status_unknown');return result
    result['status']='available'
    return result


def _check_owners(quantities):
    facts={}
    for role,value in quantities.items():
        if value is None: continue
        fact=tuple(json.dumps(value[k],sort_keys=True) for k in ('canonical_exact','canonical_unit','estimator_scale','quantity_kind','normalization','semantics'))
        for key in (value['owner_key'],value['physical_owner_key']):
            if key is None: continue
            if key in facts and facts[key]!=fact: _fail('physical_owner_value_conflict',role)
            facts[key]=fact


def read_measurement_comparison_inputs(selection: dict, *, read_source) -> dict:
    args=deepcopy(selection);validate_schema(args,measurement_comparison_selection_schema())
    def authenticated_read(reference,representation):
        result=read_source(reference,representation)
        if isinstance(result,dict) and isinstance(result.get('content'),bytes):
            _validate_content_identity(result.get('artifact_ref'),result['content'],'comparison_source_artifact_mismatch','source_result.artifact_ref')
        return result
    sources=_Sources(authenticated_read);sources.source(args['source_ref'],'original')
    # Authenticate every nominated context/model witness once, including scientific
    # assumptions that are not numerical operands. Quotes establish custody only.
    def authenticate(node):
        if isinstance(node,dict):
            if set(node)=={'source_ref','representation','start','end','quote'}:sources.witness(node,'selection.witness')
            else:
                for child in node.values():authenticate(child)
        elif isinstance(node,list):
            for child in node:authenticate(child)
    authenticate(args)
    for model in (args['common_model'],args['optical']):
        if model is None:continue
        def meanings(node):
            if isinstance(node,dict):
                if set(node)=={'value','witnesses'}:_interpret(node,sources,'model')
                else:
                    for child in node.values():meanings(child)
        meanings(model)
    if args['optical'] is not None and not args['optical']['sign_support']:_fail('interpretation_witness_required','optical.sign_support')
    origin='synthetic' if args['source_kind']=='synthetic_fixture' else 'reported'
    quantities={r:_quantity(r,s,sources,origin) for r,s in args['quantities'].items()}
    _check_owners({r:None if x is None else x['value'] for r,x in quantities.items()})
    relationships={k:_interpret(v,sources,'relationships.'+k) for k,v in args['relationships'].items()}
    conversions={r:_conversion(args['common_quantity'][r+'_conversion'],sources) for r in ('left','right')}
    values={r:None if x is None else x['value'] for r,x in quantities.items()}
    covariance=[_covariance(ref,values,sources) for ref in args['covariance_source_refs']]
    _mark_covariance_overlaps(covariance)
    data={'version':'a105_measurement_comparison_extraction_v2','selection':args,'quantities':quantities,
        'relationships':relationships,'conversions':conversions,'covariance_blocks':covariance,
        'source_refs':list(sources.references),'source_artifacts':[{'source_ref':ref,'representation':rep,'artifact_ref':item['artifact_ref']}
            for (ref,rep),item in sources.cache.items()], 'dependency_fingerprints':[]}
    return validate_measurement_comparison_extraction(data)


def _saved_witness(w, artifacts):
    if (w['end']-w['start']!=len(w['quote'].encode()) or
        (w['source_ref'],w['representation'],w['artifact_ref']) not in artifacts):
        _fail('comparison_witness_record_mismatch','witness')


def _validate_value(v):
    for number,key in (('native_value','native_exact'),('canonical_value','canonical_exact')):
        exact=v[key]
        if exact is not None and v[number] != _float(_q(exact)): _fail('comparison_exact_value_mismatch',key)
        if exact is None and v[number] is not None: _fail('comparison_exact_value_required',number)
    if v['native_token'] is not None and v['native_exact'] is not None and Fraction(v['native_token'].replace('−','-'))!=_q(v['native_exact']):
        _fail('comparison_source_token_mismatch','native_exact')
    if v['owner_key'] not in v['dependency_keys']: _fail('comparison_owner_dependency_mismatch','dependency_keys')


def _validate_covariance_blocks(blocks,quantities,source_artifacts):
    artifacts={(a['source_ref'],a['representation']):a['artifact_ref'] for a in source_artifacts}
    rebuilt=[]
    for block in blocks:
        if artifacts.get((block['source_ref'],'original'))!=block['artifact_ref']:
            _fail('comparison_covariance_artifact_binding_mismatch','covariance')
        if block['raw_document_utf8'] is None:
            # The reader emits this only for undecodable source bytes. Such a
            # record may preserve an unavailable partial, never measured C.
            if block['status']=='available':_fail('comparison_covariance_snapshot_missing','covariance')
            absent=dict(roles=[],owner_keys=[],units=[],dependency_keys=[],matrix_exact=None,
                basis='joint_covariance_of_selected_estimates',variance_status='unknown',origin='derived',
                systematic_coverage='not_established',derivation='reported_estimator_covariance',status='unavailable',
                reasons=_reason_for_undecodable_covariance())
            if any(block[k]!=v for k,v in absent.items()):
                _fail('comparison_covariance_missing_snapshot_has_numeric_claim','covariance')
            rebuilt.append(deepcopy(block));continue
        try: raw=block['raw_document_utf8'].encode('utf8')
        except UnicodeError:_fail('comparison_covariance_snapshot_utf8_invalid','covariance')
        _validate_content_identity(block['artifact_ref'],raw,'comparison_covariance_snapshot_digest_mismatch','covariance')
        source=_Sources(lambda reference,representation,b=block,raw=raw: {'artifact_ref':b['artifact_ref'],'content':raw})
        rebuilt.append(_covariance(block['source_ref'],quantities,source))
    _mark_covariance_overlaps(rebuilt)
    if rebuilt!=blocks:_fail('comparison_covariance_snapshot_mismatch','covariance')
    facts={};statuses={}
    for b in blocks:
        if b['status']!='available':
            if not any(b['reasons'].values()):_fail('unavailable_covariance_reason_required','covariance')
            continue
        roles=b['roles'];rows=[quantities[r] for r in roles]
        if any(r is None for r in rows) or not roles or len(set(roles))!=len(roles):_fail('covariance_owner_unit_dependency_mismatch','covariance')
        if b['owner_keys']!=[r['owner_key'] for r in rows] or b['units']!=[r['canonical_unit'] for r in rows] or b['dependency_keys']!=[r['dependency_keys'] for r in rows]:
            _fail('covariance_owner_unit_dependency_mismatch','covariance')
        matrix=b['matrix_exact'];n=len(roles)
        if matrix is None or len(matrix)!=n or any(len(row)!=n for row in matrix):_fail('covariance_invalid_shape','covariance')
        C=[[_q(v) for v in row] for row in matrix]
        if not _psd(C):_fail('covariance_not_positive_semidefinite','covariance')
        if b['variance_status']=='unknown' or any(b['reasons'].values()):_fail('available_covariance_status_mismatch','covariance')
        for i,owner in enumerate(b['owner_keys']):
            if owner in statuses and statuses[owner]!=b['variance_status']:_fail('covariance_overlap_conflict','covariance')
            statuses[owner]=b['variance_status']
            for j,other in enumerate(b['owner_keys']):
                key=(owner,other)
                if key in facts and facts[key]!=C[i][j]:_fail('covariance_overlap_conflict','covariance')
                facts[key]=C[i][j]
            for j in range(i):
                if owner==b['owner_keys'][j] and (C[i]!=C[j] or any(row[i]!=row[j] for row in C)):
                    _fail('covariance_owner_unit_dependency_mismatch','covariance')


def validate_measurement_comparison_extraction(extraction: dict) -> dict:
    data=deepcopy(extraction);validate_schema(data,measurement_comparison_extraction_schema())
    args=data['selection'];artifacts={(x['source_ref'],x['representation'],x['artifact_ref']) for x in data['source_artifacts']}
    if set(data['source_refs'])!={x[0] for x in artifacts} or args['source_ref'] not in data['source_refs']:_fail('comparison_source_roster_mismatch','source_refs')
    for role,item in data['quantities'].items():
        selected=args['quantities'][role]
        if (item is None)!=(selected is None):_fail('comparison_saved_selection_mismatch',role)
        if item is None:continue
        if item['selection']!=selected:_fail('comparison_saved_selection_mismatch',role)
        v=item['value'];_validate_value(v)
        if v['role']!=role or v['origin']!=('synthetic' if args['source_kind']=='synthetic_fixture' else 'reported'):_fail('comparison_value_origin_role_mismatch',role)
        for w in item['witnesses']:_saved_witness(w,artifacts)
        n=item['number']
        if n is not None:
            s=n['selector'];w=s['witness'];_saved_witness(w,artifacts)
            a,z=s['number_start'],s['number_end']
            if not 0<=a<z<=len(w['quote']) or w['quote'][a:z]!=n['raw_token']:_fail('comparison_number_record_mismatch',role)
            if {k:v for k,v in s.items() if k!='witness'}!={k:v for k,v in selected['number'].items() if k!='witness'} or {k:v for k,v in w.items() if k!='artifact_ref'}!=selected['number']['witness']:
                _fail('comparison_saved_selection_mismatch',role)
            location=_numeric_location(n);key=_measurement_key(w,location['start'],location['end'])
            if n['measurement_key']!=key or v['owner_key']!=key or v['native_token']!=n['raw_token'] or v['native_exact']!=n['native_exact']:
                _fail('comparison_number_owner_mismatch',role)
            expected=[{k:v for k,v in location.items() if k not in ('number_start_bytes','number_end_bytes')}]
            if v['source_locations']!=expected:_fail('comparison_location_binding_mismatch',role)
        for field in ('quantity_kind','estimator_scale','semantics','normalization'):
            if v[field]!=selected[field]['value']:_fail('comparison_meaning_record_mismatch',role)
    for name,meaning in data['relationships'].items():
        original=args['relationships'][name]
        if meaning['value']!=original['value'] or [{k:v for k,v in w.items() if k!='artifact_ref'} for w in meaning['witnesses']]!=original['witnesses']:
            _fail('comparison_relationship_record_mismatch',name)
        for w in meaning['witnesses']:_saved_witness(w,artifacts)
    _validate_bound_values(args,{r:None if x is None else x['value'] for r,x in data['quantities'].items()},data['source_artifacts'])
    _validate_bound_conversions(args,data['conversions'],data['source_artifacts'])
    _check_owners({r:None if x is None else x['value'] for r,x in data['quantities'].items()})
    _validate_covariance_blocks(data['covariance_blocks'],{r:None if x is None else x['value'] for r,x in data['quantities'].items()},data['source_artifacts'])
    return data


def compile_measurement_comparison_inputs(extraction: dict) -> dict:
    data=validate_measurement_comparison_extraction(extraction)
    args=data['selection'];quantities={r:None if x is None else deepcopy(x['value']) for r,x in data['quantities'].items()}
    assertion_key=identity('measurement_comparison_assertion',args['assertion'])
    owners=sorted({v['owner_key'] for r,v in quantities.items() if v is not None and r in ('left','right')})
    result=dict(version='a105_measurement_comparison_calculation_inputs_v2',selection=args,quantities=quantities,
        conversions=data['conversions'],relationships=data['relationships'],covariance_blocks=data['covariance_blocks'],
        assertion_key=assertion_key,contribution_key=identity('measurement_comparison_contribution',{'assertion':assertion_key,'owners':owners}),source_artifacts=data['source_artifacts'])
    return validate_measurement_comparison_calculation_inputs(result)


def validate_measurement_comparison_calculation_inputs(inputs: dict) -> dict:
    data=deepcopy(inputs);validate_schema(data,measurement_comparison_calculation_inputs_schema())
    for role,v in data['quantities'].items():
        if v is not None:
            _validate_value(v)
            if v['role']!=role:_fail('comparison_value_role_mismatch',role)
    _validate_bound_values(data['selection'],data['quantities'],data['source_artifacts'])
    _validate_bound_conversions(data['selection'],data['conversions'],data['source_artifacts'])
    _validate_bound_relationships(data['selection'],data['relationships'])
    _check_owners(data['quantities']);_validate_covariance_blocks(data['covariance_blocks'],data['quantities'],data['source_artifacts'])
    for role,c in data['conversions'].items():
        if c['multiplier_exact'] is not None and (_q(c['multiplier_exact'])<=0 or c['status']!='supported'):_fail('conversion_status_value_mismatch',role)
    expected=identity('measurement_comparison_assertion',data['selection']['assertion'])
    if data['assertion_key']!=expected:_fail('comparison_assertion_binding_mismatch','assertion_key')
    owners=sorted({v['owner_key'] for r,v in data['quantities'].items() if v is not None and r in ('left','right')})
    if data['contribution_key']!=identity('measurement_comparison_contribution',{'assertion':expected,'owners':owners}):_fail('comparison_contribution_binding_mismatch','contribution_key')
    return data


def _reversed_definition_scale(definition):
    """Only the parent-converted reversed grammatical variant is added here.

    The frozen helper first checks amount/time/entity, token containment and
    exact gaps. Its unsupported-bridge error occurs after those checks. No quote
    is rewritten to impersonate a supported source sentence.
    """
    from .literature_partner_defined_units import (
        _definition_scale, _quantity_token, _number_fraction,
        _AMOUNT_SCALES, _TIME_SCALES, _normal,
    )
    try:return _definition_scale(definition)
    except ExperimentalContractError as error:
        if error.code!='defined_unit_bridge_unsupported':raise
    bridge=_quantity_token(definition['bridge']['quote'])
    clause=_quantity_token(definition['clause']['quote'])
    pattern=r'(?:Formation|Reduction)\s+of\s+'+re.escape(clause)+r'\s+was\s+defined\s+as\s+(?:representing\s+)?1\s+unit\.?'
    if re.fullmatch(pattern,bridge,re.I) is None:_fail('defined_unit_bridge_unsupported','unit.definition.bridge')
    amount=_number_fraction(definition['amount'],'unit.definition.amount',point=True)
    return amount*_AMOUNT_SCALES[_quantity_token(definition['amount_unit']['quote'])]*_TIME_SCALES[_normal(definition['time_unit']['quote'])]


def _comparison_unit(selection,sources,endpoint):
    try:return _unit(selection,sources,endpoint)
    except ExperimentalContractError as error:
        if error.code!='defined_unit_bridge_unsupported':raise
    # All original lexical/endpoint/whole-definition checks were reached above.
    definition={k:sources.witness(v,'unit.definition.'+k) for k,v in selection['definition'].items() if k!='amount'}
    amount=_number(selection['definition']['amount'],sources,'condition',count_unit_guard=False)
    definition['amount']={k:v for k,v in amount.items() if k!='approximate'}
    scale=_reversed_definition_scale(definition)
    witness=sources.witness(selection['witness'],'unit.witness')
    parsed={'witness':witness,'raw_unit':witness['quote'],'canonical_unit':'pmol/min/mg','multiplier':_float(scale),'definition':definition}
    return {'witness':witness,'raw_unit':witness['quote'],'canonical_unit':'umol/min/mg','multiplier':_float(scale/Fraction(1000000)),
        'source_defined_unit':parsed,'unavailable_reason':None}


def _comparison_scale(unit):
    try:return _scale(unit)
    except ExperimentalContractError as error:
        if error.code!='defined_unit_bridge_unsupported':raise
    return _reversed_definition_scale(unit['source_defined_unit']['definition'])/1000000


def _selected_unit_scale(selected,role,artifact_map):
    raw=selected['unit']
    if raw is None:return None,None
    if role.startswith('epsilon'):
        if 'kind' in raw:return None,None
        parsed=_UNIT_TABLES['epsilon'].get(_normalize(raw['quote']))
        return (None,None) if parsed is None else parsed
    if 'kind' not in raw:
        parsed=_plain_unit(raw['quote'])
        return (None,None) if parsed is None else parsed
    def enriched(w):
        artifact=artifact_map.get((w['source_ref'],w['representation']))
        if artifact is None:_fail('comparison_source_roster_mismatch','unit')
        return {**w,'artifact_ref':artifact}
    definition={k:enriched(v) for k,v in raw['definition'].items() if k!='amount'}
    selector=raw['definition']['amount'];w=selector['witness'];a,z=selector['number_start'],selector['number_end']
    token=w['quote'][a:z]
    if _NUMBER.fullmatch(token) is None:_fail('comparison_unit_amount_token_mismatch','unit.definition.amount')
    definition['amount']={'selector':{**selector,'witness':enriched(w)},'raw_number':token,'value':float(token.replace('−','-')),'relation':'point'}
    scale=_reversed_definition_scale(definition)/1000000
    return 'umol/min/mg',scale


def _validate_bound_values(args,quantities,artifacts):
    amap={(a['source_ref'],a['representation']):a['artifact_ref'] for a in artifacts}
    for role,value in quantities.items():
        selected=args['quantities'][role]
        if (selected is None)!=(value is None):_fail('comparison_saved_selection_mismatch',role)
        if value is None:continue
        for field in ('quantity_kind','estimator_scale','semantics','normalization'):
            if value[field]!=selected[field]['value']:_fail('comparison_meaning_record_mismatch',role)
        if value['origin']!=('synthetic' if args['source_kind']=='synthetic_fixture' else 'reported'):_fail('comparison_value_origin_role_mismatch',role)
        semantic_reason={'reported_nondetection':'native_nondetection_not_point','reported_negligible':'native_negligible_not_point','unknown':'source_semantics_unknown','conflicting':'source_semantics_conflicting'}.get(value['semantics'])
        if semantic_reason is not None and semantic_reason not in value['reasons']['source']:_fail('comparison_semantic_reason_mismatch',role)
        if value['relation'] in ('lt','le','gt','ge') and 'bounded_arithmetic_unimplemented' not in value['reasons']['implementation']:_fail('comparison_bound_reason_mismatch',role)
        if value['relation']=='range' and 'range_arithmetic_unimplemented' not in value['reasons']['implementation']:_fail('comparison_bound_reason_mismatch',role)
        if selected['qualification']['value'] in ('rounded_after_fit','source_qualified_approximate') and not value['approximate']:_fail('comparison_approximation_record_mismatch',role)
        selector=selected['number']
        if selector is not None:
            w=selector['witness'];a,z=selector['number_start'],selector['number_end'];token=w['quote'][a:z]
            artifact=amap.get((w['source_ref'],w['representation']))
            if artifact is None or not 0<=a<z<=len(w['quote']):_fail('comparison_number_record_mismatch',role)
            key=_measurement_key({**w,'artifact_ref':artifact},w['start']+len(w['quote'][:a].encode()),w['start']+len(w['quote'][:z].encode()))
            if value['native_token']!=token or value['owner_key']!=key:_fail('comparison_number_owner_mismatch',role)
        if value['canonical_exact'] is not None:
            unit,scale=_selected_unit_scale(selected,role,amap)
            if unit!=value['canonical_unit'] or scale is None or value['native_exact'] is None or _q(value['canonical_exact'])!=_q(value['native_exact'])*scale:
                _fail('comparison_native_unit_conversion_mismatch',role)
        physical=selected['physical_identity']
        expected_physical=None if physical is None else _physical_key({**physical,'artifact_ref':amap[(physical['source_ref'],physical['representation'])]})
        dependencies=[value['owner_key']]+[_physical_key({**w,'artifact_ref':amap[(w['source_ref'],w['representation'])]}) for w in selected['dependency_witnesses']]
        if value['physical_owner_key']!=expected_physical or value['dependency_keys']!=list(dict.fromkeys(dependencies)):_fail('comparison_owner_dependency_mismatch',role)


def _validate_bound_relationships(args,relationships):
    for name,value in relationships.items():
        selected=args['relationships'][name]
        if value['value']!=selected['value'] or [{k:v for k,v in w.items() if k!='artifact_ref'} for w in value['witnesses']]!=selected['witnesses']:
            _fail('comparison_relationship_record_mismatch',name)


def _validate_bound_conversions(args,conversions,source_artifacts):
    artifacts={(w['source_ref'],w['representation'],w['artifact_ref']) for w in source_artifacts}
    for role,value in conversions.items():
        selected=args['common_quantity'][role+'_conversion'];multiplier=None
        if value['kind']!=selected['kind'] or value['status']!=selected['support_status']['value'] or value['model_key']!=identity('measurement_comparison_conversion',selected):
            _fail('comparison_conversion_binding_mismatch',role)
        for w in value['source_witnesses']:_saved_witness(w,artifacts)
        coefficients=[]
        for side in ('endpoint','common'):
            c=selected[side+'_coefficient'];retained=value['coefficient_readings'][side]
            if c is None:
                if retained is not None:_fail('comparison_coefficient_selection_mismatch',role+'.'+side)
                coefficients.append(None)
            elif c['origin']=='implicit_unit_coefficient':
                if retained is not None or c['number'] is not None or c['implicit_value']!=_exact(Fraction(1)):
                    _fail('comparison_coefficient_selection_mismatch',role+'.'+side)
                coefficients.append(Fraction(1))
            else:
                if retained is None or c['number'] is None or c['implicit_value'] is not None:
                    _fail('comparison_coefficient_selection_mismatch',role+'.'+side)
                _validate_coefficient_reading(c['number'],retained,artifacts,role+'.'+side)
                coefficients.append(_eligible_coefficient(retained))
        if value['status']=='supported' and selected['direction']['value']=='same_direction_supported':
            if selected['kind']=='identity':
                if selected['endpoint_coefficient'] is not None or selected['common_coefficient'] is not None:
                    _fail('identity_conversion_has_no_selected_coefficients','conversion')
                multiplier=Fraction(1)
            elif selected['kind']=='fixed_reaction_scale' and None not in coefficients and all(c>0 for c in coefficients):
                multiplier=coefficients[1]/coefficients[0]
        if value['multiplier_exact']!=(None if multiplier is None else _exact(multiplier)):_fail('comparison_conversion_binding_mismatch',role)


def _mark_covariance_overlaps(blocks):
    facts={};status={};conflicts=set()
    for k,b in enumerate(blocks):
        if b['status']!='available':continue
        for i,owner in enumerate(b['owner_keys']):
            if owner in status and status[owner][0]!=b['variance_status']:conflicts.update((k,status[owner][1]))
            status.setdefault(owner,(b['variance_status'],k))
            for j,other in enumerate(b['owner_keys']):
                key=(owner,other);value=b['matrix_exact'][i][j]
                if key in facts and facts[key][0]!=value:conflicts.update((k,facts[key][1]))
                facts.setdefault(key,(value,k))
    for k in conflicts:
        blocks[k]['status']='unavailable';blocks[k]['reasons']['domain'].append('covariance_overlap_conflict')


def _validate_content_identity(artifact,content,code,field):
    """Authenticate whole retained bytes when the identity is a SHA256 digest."""
    if re.fullmatch(r'artifact_[a-f0-9]{64}',str(artifact)) and artifact!='artifact_'+hashlib.sha256(content).hexdigest():
        _fail(code,field)


def _reason_for_undecodable_covariance():
    result=_reasons();result['domain'].append('covariance_json_invalid');return result


def _eligible_coefficient(retained):
    reading=retained['reading']
    if reading['native_exact'] is None or reading['relation']!='point' or reading['approximate']:return None
    return _q(reading['native_exact'])


def _validate_coefficient_reading(selection,retained,artifacts,field):
    reading=retained['reading'];selector=reading['selector'];w=selector['witness'];context=retained['source_context']
    _saved_witness(w,artifacts);_saved_witness(context,artifacts)
    unbound={**selector,'witness':{k:v for k,v in w.items() if k!='artifact_ref'}}
    if unbound!=selection:_fail('comparison_coefficient_selection_mismatch',field)
    a,z=selector['number_start'],selector['number_end']
    if not 0<=a<z<=len(w['quote']) or w['quote'][a:z]!=reading['raw_token']:
        _fail('comparison_coefficient_token_mismatch',field)
    start=w['start']+len(w['quote'][:a].encode());end=w['start']+len(w['quote'][:z].encode())
    if (reading['measurement_key']!=_measurement_key(w,start,end) or
        any(context[k]!=w[k] for k in ('source_ref','artifact_ref','representation')) or
        not context['start']<=start<end<=context['end']):
        _fail('comparison_coefficient_context_binding_mismatch',field)
    raw=context['quote'].encode();left,right=start-context['start'],end-context['start']
    if raw[left:right]!=reading['raw_token'].encode():_fail('comparison_coefficient_context_binding_mismatch',field)
    # This is only deterministic consistency validation of the saved field. It
    # does not read the original source or assign a new scientific meaning. A
    # local field identity avoids passing a source fragment off as whole bytes
    # of the original content-derived artifact.
    local_digest=hashlib.sha256(raw).hexdigest();local_ref='source_'+local_digest
    before=raw[:left].decode();token=raw[left:right].decode()
    local_selector={'witness':{'source_ref':local_ref,'representation':'original','start':0,'end':len(raw),'quote':context['quote']},
        'number_start':len(before),'number_end':len(before)+len(token)}
    local_sources=_Sources(lambda reference,representation:{'artifact_ref':'artifact_'+local_digest,'content':raw})
    checked,_=_read_scalar(local_selector,local_sources)
    if any(reading[k]!=checked[k] for k in ('raw_token','native_exact','relation','approximate')):
        _fail('comparison_coefficient_qualification_mismatch',field)
