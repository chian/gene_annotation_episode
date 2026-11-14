"""Pure source-only perturbation/restoration point components for A106.

The caller identifies the experimental design, endpoint calibration, actual
measurement identities and the bounds on nuisance effects. This calculator
does not infer those facts, acquire evidence, transfer annotations, or compute
annotation credit. The proposed source index is a convention, not a probability.
Joint uncertainty is unreported in this finite first interface.
"""
from __future__ import annotations
COMPONENTS = ('reference_endpoint', 'perturbed_endpoint', 'restored_endpoint', 'perturbation_difference', 'symmetric_effect', 'restoration_fraction_raw', 'restoration_agreement', 'amount_comparability', 'perturbation_isolation', 'restoration_isolation', 'effect_isolation', 'reference_restoration_index', 'reference_index_lower', 'reference_index_upper')
_ENDPOINT_CONDITIONS = ('validated_ratio_scale', 'same_endpoint_scope', 'distinct_role_measurements')
_RESTORATION_CONDITIONS = (*_ENDPOINT_CONDITIONS, 'explicit_restoration_design')
REASONS = ('endpoint_unreported', 'numerical_model_range', 'ratio_scale_not_validated', 'same_endpoint_not_established', 'restoration_design_not_established', 'endpoint_inputs_unreported', 'role_measurement_identity_unreported', 'role_measurement_not_distinct', 'zero_endpoint_sum', 'zero_perturbation_difference', 'amount_is_intended_change', 'nuisance_amount_role_unreported', 'amount_inputs_unreported', 'zero_amount_denominator', 'effect_bound_unreported', 'zero_effect_denominator', 'orientation_unreported', 'joint_uncertainty_unreported')
CONDITIONAL_CODES = (*_RESTORATION_CONDITIONS, 'nuisance_amount_comparison', 'supplied_effect_bound', 'supplied_effect_bounds', 'source_restoration_convention')
