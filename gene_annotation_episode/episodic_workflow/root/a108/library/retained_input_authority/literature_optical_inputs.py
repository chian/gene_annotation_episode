"""Source-bound optical operands, separate from science interpretation and credit.

Selections supply experimental meanings; verified quotes establish custody only.
No source acquisition, calculator execution, model, state mutation or episode
decision occurs here. Reuse refs are local calculator aliases, not global
physical identities or evidence of independence between sheets.
"""
from __future__ import annotations
PRIMITIVE_ORDER = ('sample_slope', 'blank_slope', 'epsilon', 'path_length')
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'synthetic_fixture')
LITERAL_FIELDS = ('molecule', 'construct', 'preparation', 'condition', 'measured_entity')
QUALIFICATIONS = ('reported_point', 'source_qualified_approximate', 'unknown', 'conflicting')
INTERPRETATIONS = {'signal_kind': ('absorbance_slope', 'absorbance_difference', 'static_absorbance', 'unknown'), 'relation': ('applicable_extinction_relation', 'not_applicable', 'unknown', 'conflicting'), 'blank_role': ('matched_no_reaction_background', 'condition_reference', 'component_omission', 'unknown', 'conflicting'), 'same_endpoint': ('same', 'different', 'unknown'), 'matched_window': ('same', 'different', 'unknown'), 'rate_window': ('source_supported_rate_interval', 'interval_mean_only', 'static_only', 'unknown')}
