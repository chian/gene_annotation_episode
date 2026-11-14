"""Finite source kinetic-parameter contrasts, separate from annotation credit.

Readers authenticate source selections and normalize parameter-specific units.
The investigation supplies scientific relationships and model interpretations.
This pure boundary validates their shape and performs arithmetic; it does not
prove molecular identity, protocol comparability or scientific model validity.
Cell ``conditional_on`` lists formula prerequisites, including unmet ones named
by ``unavailable_reason``; it never certifies that a model was established.
"""
from __future__ import annotations
COMPONENTS = ('numerator_parameter', 'denominator_parameter', 'parameter_difference', 'parameter_ratio', 'log_parameter_contrast', 'log_contrast_variance', 'log_contrast_standard_uncertainty', 'source_profile_log_ratio', 'source_signed_index')
INPUT_UNAVAILABLE_REASONS = ('source_measurement_unreported', 'source_kinetic_unit_unreported', 'unsupported_source_kinetic_unit', 'source_operand_qualification_unknown', 'source_operand_qualification_conflicting', 'source_numeric_range')
REASONS = (*INPUT_UNAVAILABLE_REASONS, 'numerator_measurement_missing', 'denominator_measurement_missing', 'source_measurement_missing', 'censored_measurement', 'conflicting_measurement', 'parameter_kind_mismatch', 'subject_relationship_different', 'subject_relationship_unknown', 'subject_relationship_conflicting', 'parameter_definition_relationship_different', 'parameter_definition_relationship_unknown', 'parameter_definition_relationship_conflicting', 'mixed_substrates_unsupported', 'substrate_arrangement_unknown', 'substrate_arrangement_conflicting', 'comparison_scope_unknown', 'comparison_scope_conflicting', 'common_conditions_not_matched', 'reused_source_observation', 'conflicting_source_observation', 'zero_denominator_parameter', 'positive_parameters_required_for_log', 'kinetic_log_model_unreported', 'covariance_status_unknown', 'known_log_covariance_required', 'kinetic_observation_model_unspecified', 'approximate_parameter_model_unsupported', 'positive_log_contrast_variance_required', 'numerical_model_range')
CONDITIONAL_CODES = ('supplied_subject_and_parameter_relationships', 'reported_protocol_comparison', 'declared_common_conditions', 'supplied_log_covariance', 'known_normal_log_parameters')
