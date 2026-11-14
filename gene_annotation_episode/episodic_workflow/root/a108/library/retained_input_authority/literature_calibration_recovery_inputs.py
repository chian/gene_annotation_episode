"""Exact source pairs for A105 recovery components, without scientific scoring.

Callers interpret source roles. The callback owns received-source authorization;
this module checks selected bytes, complete tokens and supported dimensions.
It acquires no source and treats matching quotations as no semantic proof.
"""
from __future__ import annotations
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'synthetic_fixture')
LITERAL_FIELDS = ('experiment', 'analyte', 'matrix', 'endpoint', 'blank_treatment', 'expected_quantity_basis')
CONTROL_KINDS = ('reporter_standard', 'enzyme_activity_spike', 'unknown', 'conflicting')
APPLICABILITIES = ('same_matrix_same_endpoint_supported', 'different_matrix_or_endpoint', 'unknown', 'conflicting')
SPREAD_KINDS = ('SD', 'SEM', 'unspecified', 'unknown')
