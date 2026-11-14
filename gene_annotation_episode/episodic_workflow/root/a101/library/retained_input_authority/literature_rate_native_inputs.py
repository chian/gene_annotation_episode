"""Witnessed native operands for the existing source-preparation rate sheet.

Selections assign scientific meanings; exact quotes establish custody only.
This reader performs no model call, acquisition, scoring or state mutation.
"""
from __future__ import annotations
ROLES = ('reference', 'test')
NATIVE_BINDINGS = tuple((role + '_' + field + '_ref' for role in ROLES for field in ('subject', 'construct', 'preparation')))
NATIVE_REASONS = ('source_rate_unit_unreported', 'unsupported_source_rate_unit', 'source_defined_unit_definition_required', 'source_spread_unit_unavailable', 'source_endpoint_relationship_unknown', 'source_endpoint_relationship_different', 'source_normalization_relationship_unknown', 'source_normalization_relationship_different', 'incompatible_rate_dimensions', 'reused_source_observation')
