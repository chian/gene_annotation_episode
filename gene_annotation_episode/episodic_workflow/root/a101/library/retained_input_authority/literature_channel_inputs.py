"""Source-bound electrical operands, distinct from scientific interpretation.

The caller supplies experimental meanings and exact selections. The callback
owns authorization of received sources; this reader verifies bytes, whole scalar
tokens, dimensions and explicit covariance owners. It does not infer ion flux,
independence, applicability or a functional assertion from matching quotations.
"""
from __future__ import annotations
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture')
LITERAL_FIELDS = ('organism', 'genotype', 'molecule', 'construct', 'preparation', 'experimental_system', 'membrane', 'ionic_conditions', 'voltage_convention', 'current_baseline', 'conducting_unit', 'endpoint', 'intended_variable')
ARRANGEMENT_KINDS = ('single_preparation', 'replacement', 'coexistence', 'unknown', 'conflicting')
SPREAD_KINDS = ('SD', 'SEM', 'unspecified', 'unknown', 'conflicting')
