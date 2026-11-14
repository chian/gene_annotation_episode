"""Source-level A105 rate extraction contracts, separate from annotation credit.

This first contract describes already acquired experimental summaries. It does
not acquire papers, infer subjects, choose a statistical model or transfer a
reference annotation to another molecule. Source tokens remain supporting
records; numerical calculators consume the validated measurements separately.
"""
from __future__ import annotations
from copy import deepcopy
REPRESENTATIONS = ('primary_table', 'retained_extraction', 'synthetic_fixture')
ORIGINS = ('reported', 'graph_derived', 'synthetic')
SAMPLING_BASES = ('biological_preparations', 'technical_measurements', 'unspecified')
RATE_UNITS = {'umol/min': ('amount_rate', 1.0), 'nmol/min': ('amount_rate', 0.001), 'mmol/min': ('amount_rate', 1000.0), 'uM/min': ('concentration_rate', 1.0), 'nM/min': ('concentration_rate', 0.001), 'per_min': ('turnover_rate', 1.0), 'per_s': ('turnover_rate', 60.0), 'umol/min/mg': ('specific_amount_rate', 1.0), 'nmol/min/mg': ('specific_amount_rate', 0.001)}

class ExperimentalContractError(ValueError):
    """A repairable field/relationship failure; never an overall evidence grade."""

    def __init__(self, code, field, *, detail=None):
        self.code, self.field = (code, field)
        self.detail = deepcopy(detail)
        super().__init__(f'{code}:{field}')
