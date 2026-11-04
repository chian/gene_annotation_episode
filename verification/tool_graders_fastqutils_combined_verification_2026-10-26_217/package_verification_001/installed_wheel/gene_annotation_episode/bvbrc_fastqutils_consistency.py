"""Signed report-versus-observed count difference on the selected population."""
from __future__ import annotations

from .bvbrc_fastqutils_contracts import FastqUtilsContractError
from .bvbrc_fastqutils_retention import _comparison_inputs, _component, _COUNT_UNITS


def calculate_report_consistency(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]:
    job, populations, cells, state, codes = _comparison_inputs(sheet, job, parameters_sha256, 'report_consistency_v1')
    if job['comparison_kind'] != 'report_count_consistency':
        raise FastqUtilsContractError('shape_invalid', '/comparison_kind')
    unit = next((c['unit'] for c in cells if c is not None and c['unit'] in _COUNT_UNITS), 'reads')
    report = cells[0]['value'] if len(cells) > 0 and cells[0] is not None else None
    observed = cells[1]['value'] if len(cells) > 1 and cells[1] is not None else None
    value = None
    if state == 'available':
        if report is None or observed is None:
            state = 'missing'; codes.append('missing_requested_value')
        elif cells[0]['id'] == cells[1]['id']:
            state = 'incompatible'; codes.append('incompatible_population')
        else:
            value = report - observed
            if value != 0: codes.append('count_inconsistent')
    return [_component(sheet, job, parameters_sha256, 'report_count_difference', state=state, value=value,
        unit=unit, cells=cells, populations=populations, numerator=None, denominator=None, codes=codes)]
