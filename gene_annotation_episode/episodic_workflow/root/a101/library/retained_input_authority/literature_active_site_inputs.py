"""Source-bound operands for preparation-specific active-site titration amounts.

Scientific interpretations nominate roles; readers validate custody and literal
syntax. This module makes no model call or scientific attribution.
"""
ROLES = ('protein_mass_concentration', 'assumed_molecular_weight', 'active_site_concentration', 'reported_active_fraction')
LITERAL_FIELDS = ('subject', 'organism', 'construct', 'preparation', 'assay', 'condition', 'endpoint', 'measurement_identity')
QUALIFICATIONS = ('reported_point', 'source_qualified_approximate', 'unknown', 'conflicting')
SPREAD_KINDS = ('regression_sd', 'sd', 'sem', 'untyped', 'unreported', 'unknown', 'conflicting')
SAMPLING = ('same_preparation_aliquots', 'independent_preparations', 'unknown', 'conflicting')
INTERPRETATIONS = {'molecular_basis': ('per_monomer', 'per_dimer', 'unknown', 'conflicting'), 'amount_linkage': ('same_preparation_and_assay', 'different', 'unknown', 'conflicting'), 'active_estimate_meaning': ('titrated_active_sites', 'other', 'unknown', 'conflicting'), 'titrant_concentration_basis': ('nominal_reported', 'independently_standardized_active', 'unknown', 'conflicting'), 'titrant_to_site_stoichiometry': ('reported_one_to_one', 'other', 'unknown', 'conflicting'), 'site_stoichiometry': ('one_site_per_monomer', 'other', 'unknown', 'conflicting'), 'normalization_stage': ('none', 'total_monomer', 'active_sites', 'unknown', 'conflicting')}
