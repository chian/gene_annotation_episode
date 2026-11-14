"""Numerical A105 recovery components from a source-bound pair.

Recovery, bias and inverse correction share their original operands. They are
not independent experiments, calibration probabilities or annotation credit.
"""
from __future__ import annotations
COMPONENTS = ('nominal', 'measured', 'signed_difference', 'recovery', 'relative_bias', 'percent_bias', 'inverse_recovery', 'reported_measured_spread', 'measured_sd', 'measured_cv', 'reported_recovery', 'displayed_minus_reported_recovery', 'correction_for_other_measurement', 'recovery_variance')
FORMULAS = {'nominal': 'source_expected_quantity', 'measured': 'source_measured_quantity', 'signed_difference': 'measured-nominal', 'recovery': 'measured/nominal', 'relative_bias': 'measured/nominal-1', 'percent_bias': '100*(measured/nominal-1)', 'inverse_recovery': 'nominal/measured', 'reported_measured_spread': 'source_measured_spread', 'measured_sd': 'source_measured_spread_when_explicitly_SD', 'measured_cv': 'measured_SD/measured', 'reported_recovery': 'source_reported_recovery_as_fraction', 'displayed_minus_reported_recovery': 'measured/nominal-reported_recovery', 'correction_for_other_measurement': 'requires_linked_target_measurement_and_applicable_recovery', 'recovery_variance': 'requires_measured_and_nominal_uncertainty_and_covariance'}
REASONS = ('nominal_not_supplied', 'measured_not_supplied', 'shared_unit_not_supplied', 'nonpositive_nominal', 'nonpositive_measured', 'measured_spread_not_supplied', 'spread_kind_not_SD', 'reported_recovery_not_supplied', 'reported_recovery_unit_not_supplied', 'control_dimension_mismatch', 'no_target_measurement_supplied', 'denominator_uncertainty_and_covariance_not_supplied', 'numerical_model_range')
