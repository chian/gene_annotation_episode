"""Closed source selections and numerical input contracts for A105 amounts.

Scientific numbers in selected-operation arguments are source selectors only.
The source reader verifies byte custody and numerical syntax. Numerical
validation owns neither the truth of supplied experimental interpretations nor
experimental attribution. No acquisition, model call or state mutation occurs.
"""
from __future__ import annotations
COMPARISON_KINDS = ('stock_target_mass_estimate_over_total_mass_estimate', 'between_arm_nominal_molar_amount', 'unknown', 'conflicting')
AMOUNT_ROLES = ('target_mass_estimate', 'total_protein_mass_estimate', 'nominal_molecule_amount', 'unknown', 'conflicting')
AMOUNT_KINDS = ('measured', 'estimated', 'nominal', 'unknown', 'conflicting')
QUALIFICATIONS = ('reported_point', 'source_qualified_approximate', 'unknown', 'conflicting')
RELATIONSHIPS = ('supported', 'unknown', 'conflicting')
STOCK_RELATIONSHIPS = ('same', 'different', 'not_applicable', 'unknown', 'conflicting')
UNCERTAINTY_KINDS = ('sd', 'sem', 'ci', 'untyped', 'unreported', 'unknown', 'conflicting')
