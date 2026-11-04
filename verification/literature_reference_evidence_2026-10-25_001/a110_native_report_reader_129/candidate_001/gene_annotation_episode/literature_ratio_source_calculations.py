"""Deterministic v2 printed-relative-signal numerical sheet population.

Seven v1 component meanings are preserved. Only ratio, difference and positive
log transforms are populated; amount/response/observation models remain explicit
route limits. These dependent descriptions are not separate evidence credits.
"""
from .literature_ratio_source_inputs import validate_relative_signal_source_extraction, _shape, _SHEET_SCHEMA
from .literature_ratio_source_validation import (
    COMPONENTS, _facts, _FORMULAS, _LIMITS, _component_contract,
    _transform, _domain_transform,
)


def _component_facts(e, facts, name):
    point, exacts = facts['point'], facts['exacts']
    reason = facts['reason']
    unit, origin, conditional = _component_contract(e, name)
    if name in _LIMITS:
        return None, [], [], unit, 'unavailable', origin, _LIMITS[name], conditional
    candidates = sorted({v for x in exacts if (v := _transform(x, name)) is not None})
    value = _transform(point, name) if point is not None else None
    if point is not None and value is None:
        reason = 'zero_reported_ratio' if name == 'log_reported_ratio' and point == 0 else 'numerical_model_range'
    domains = [domain for reading in facts['readings'] for domain in _domain_transform(reading, name)]
    status = 'populated' if value is not None else 'conflicting' if facts['conflict'] and facts['resolved'] else 'unavailable'
    if name == 'log_reported_ratio' and 0 in exacts:
        if not facts['conflict']:
            reason = 'zero_reported_ratio'
        if value is None:
            status = 'unavailable'
    return value, candidates, domains, unit, status, origin, reason, conditional


def populate_relative_signal_v2(extraction):
    extraction = validate_relative_signal_source_extraction(extraction)
    facts = _facts(extraction)
    fields = ('value', 'value_candidates', 'reported_domains', 'unit', 'status', 'origin', 'unavailable_reason', 'conditional_on')
    cells = {}
    for name in COMPONENTS:
        cells[name] = dict(zip(fields, _component_facts(extraction, facts, name)))
        cells[name]['formula'] = _FORMULAS[name]
    sheet = {'version': 'relative_signal_sheet_v2', 'scope': 'reported_relative_signal', 'cells': cells,
        'selected_roster_resolved': facts['resolved'], 'point_candidate_set_complete': facts['complete'],
        'known_source_conflict': facts['conflict'], 'independent_preparation_count': None, 'annotation_credit': None}
    _shape(sheet, _SHEET_SCHEMA, 'sheet')
    return sheet


__all__ = ['populate_relative_signal_v2']
