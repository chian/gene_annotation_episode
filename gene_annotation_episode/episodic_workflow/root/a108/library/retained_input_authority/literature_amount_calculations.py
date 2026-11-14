"""Finite A105 amount comparisons, separate from activity and final credit.

Source interpretation, custody and unit conversion precede this boundary. Ratios
of target/total estimates are not automatically validated purity; nominal between-arm amounts
are not active concentrations or a response model. No saved rate is changed.
"""
from __future__ import annotations
COMPONENTS = ('numerator_amount', 'denominator_amount', 'amount_difference', 'amount_ratio', 'reciprocal_amount_ratio', 'conditional_mass_denominator_factor', 'amount_difference_variance', 'amount_difference_standard_uncertainty', 'amount_ratio_variance', 'amount_ratio_standard_uncertainty', 'reciprocal_amount_ratio_variance', 'reciprocal_amount_ratio_standard_uncertainty')
REASONS = ('source_measurement_unavailable', 'censored_measurement', 'conflicting_measurement', 'source_amount_unit_unreported', 'unsupported_source_amount_unit', 'amount_qualification_unknown', 'amount_qualification_conflicting', 'comparison_kind_unknown', 'comparison_kind_conflicting', 'pair_relationship_unknown', 'pair_relationship_conflicting', 'amount_basis_unknown', 'amount_basis_conflicting', 'amount_role_mismatch', 'amount_kind_unresolved', 'stock_relationship_unknown', 'stock_relationship_conflicting', 'different_stocks', 'incompatible_amount_dimensions', 'reused_source_observation', 'zero_denominator_amount', 'zero_numerator_amount', 'mass_factor_not_applicable', 'positive_mass_estimates_required', 'amount_covariance_unreported', 'numerical_model_range', 'invalid_propagated_variance')
