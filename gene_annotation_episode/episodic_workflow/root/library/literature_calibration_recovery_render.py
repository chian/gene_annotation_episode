"""Render requested recovery-control facts as scientific text, without source IO."""
from collections.abc import Mapping


def is_row(row):
    return isinstance(row, Mapping) and row.get('evaluation_scope') == 'source_calibration_recovery' and 'component' in row


def rows_from_values(value):
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from rows_from_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from rows_from_values(child)


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for value in report.values():
                if isinstance(value, (list, tuple)):
                    yield from (row for row in value if is_row(row))


def task_relevant(state):
    """Actual assignment or own selected result only; no keyword/source routing."""
    assignment = state.get('literature_assignment', {})
    if isinstance(assignment, Mapping) and assignment.get('requested_calibration_recovery_components'):
        return True
    if state.get('literature_calibration_recovery_work', {}).get('version') == 'literature_calibration_recovery_task_v1':
        return True
    outcome = state.get('last_local_outcome') or {}
    return isinstance(outcome, Mapping) and isinstance(outcome.get('result'), Mapping) and outcome['result'].get('view') == 'calibration_recovery_components'


def render_received(parts, rows, *, section, table):
    groups = {}; labels = {}
    for row in rows:
        groups.setdefault(row['sheet_ref'], []).append(row)
        for key in row['input_measurement_keys']:
            labels.setdefault(key, 'source measurement ' + str(len(labels) + 1))
    for number, selected in enumerate(groups.values(), 1):
        first = selected[0]
        section(parts, 'Recovery control ' + str(number), table(
            ('Control type', 'Numerical section', 'Applicability', 'Spread meaning', 'Input origin'),
            [(first['control_kind'], first['section'], first['applicability'], first['spread_kind'], ', '.join(first['input_origins']))]))
        section(parts, 'Source meanings for the recovery control', table(('Meaning', 'Reported literal'), first['source_meanings'].items()))
        section(parts, 'Requested recovery numerical components', table(
            ('Component', 'Value', 'Unit', 'Status', 'Unavailable reason'),
            [(row['component'], row['value'], row['unit'], row['status'], row['unavailable_reason']) for row in selected]))
        section(parts, 'Requested calculation and shared measurements', table(
            ('Component', 'Calculation', 'Original measurement reuse'),
            [(row['component'], row['formula'], ', '.join(labels[key] for key in row['input_measurement_keys'])) for row in selected]))
        section(parts, 'Recovery interpretation limits', table(('Question', 'Status'), [
            ('Scientific control scope', first['interpretation_scope_unavailable_reason'] or 'conditional on source role assignments'),
            ('Analyte', 'the measured control subject; not automatically the reference enzyme'),
            ('Recovery, bias and inverse', 'dependent views of the same source operands'),
            ('Precision', 'only explicit SD supplies SD/CV; SEM and unspecified spread stay distinct'),
            ('Reported versus displayed recovery', 'retain both when selected; differences are not silently resolved'),
            ('Application to another measurement', 'unavailable; no linked target measurement supplied'),
            ('Recovery uncertainty', 'denominator uncertainty and covariance not supplied'),
            ('Independent preparations / product identity / functional attribution', 'not established by this control'),
        ]))
