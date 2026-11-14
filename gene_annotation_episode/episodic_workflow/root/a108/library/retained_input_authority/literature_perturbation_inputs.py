"""Read retained A106 source measurements and literal experimental context.

The selected operation supplies source references and witnessed interpretations,
never numerical measurements. The finite JSON dataset is an explicit retained
data boundary, not a gel reader or a calibration procedure. Literal custody does
not establish the scientific truth of the selected experimental meanings.
"""
from __future__ import annotations
ENDPOINT_UNITS = ('events_per_100000_cells', 'fraction', 'CFU_per_mL', 'CFU_per_initial_OD_per_mL', 'minutes', 'per_min', 'per_h')
EXPOSURE_UNITS = ('molecules_per_cell', 'normalized_signal', 'fraction', 'mg_per_mL')
