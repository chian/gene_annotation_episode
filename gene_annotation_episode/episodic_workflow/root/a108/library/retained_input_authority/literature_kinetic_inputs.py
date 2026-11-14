"""Read selected kinetic parameter estimates; source meanings remain interpreted.

This finite source reader has no acquisition, Store, scoring, model or episode
behavior. Its caller authorizes each read. Exact quotes establish custody,
not scientific attribution or the applicability of a kinetic observation model.
"""
from __future__ import annotations
PARAMETER_UNITS = {'Km': 'uM', 'kcat': 'per_min', 'catalytic_efficiency': 'uM^-1min^-1'}
SUBJECT_FIELDS = ('organism', 'genotype', 'molecule', 'construct')
CONTEXT_FIELDS = ('substrate', 'preparation', 'experiment', 'experimental_system', 'conditions', 'endpoint', 'normalization')
QUALIFICATIONS = ('reported_point', 'source_qualified_approximate', 'unknown', 'conflicting')
COUNT_STATUSES = ('not_selected', 'exact', 'qualified', 'range_or_alternatives', 'unsupported', 'not_positive')
COUNT_REASONS = ('exact_count_qualified', 'count_range_or_alternatives', 'unsupported_count_literal', 'positive_count_required')
COUNT_NOTATIONS = ('decimal_digits', 'english_cardinal', 'unsupported')
COUNT_RELATIONS = ('point', 'lt', 'le', 'gt', 'ge', 'unresolved')
COMPARISON_VALUES = {'subject_relationship': ('same_molecule_and_construct', 'different', 'unknown', 'conflicting'), 'parameter_definition_relationship': ('same', 'different', 'unknown', 'conflicting'), 'substrate_arrangement': ('separate_assays', 'mixed_substrates', 'unknown', 'conflicting'), 'comparison_scope': ('reported_protocols', 'common_conditions', 'unknown', 'conflicting'), 'nonintended_conditions_relationship': ('matched', 'different', 'unknown', 'conflicting')}
