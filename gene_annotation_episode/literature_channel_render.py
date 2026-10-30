"""Detailed electrical TASK with concise exact requested numerical STEERING."""
from collections.abc import Mapping
from .domain import canonical
from .literature_channel_prompt import CHANNEL_TASK


def is_row(value):
    return isinstance(value, Mapping) and value.get('evaluation_scope') == 'source_electrical_activity' and 'component' in value


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
    assignment = state.get('literature_assignment', {})
    if isinstance(assignment, Mapping) and assignment.get('requested_channel_components'):
        return True
    if state.get('literature_channel_work', {}).get('version') == 'literature_channel_task_v1':
        return True
    outcome = state.get('last_local_outcome') or {}
    if isinstance(outcome, Mapping) and isinstance(outcome.get('result'), Mapping) and outcome['result'].get('view') == 'channel_components':
        return True
    return any(rows_from_reports(state.get('child_reports', ()))) or any(rows_from_values(state.get('current_report_update', {})))


def render_received(parts, rows, *, section, table):
    groups = {}
    seen = set()
    for row in rows:
        key = canonical(row)
        if key in seen:
            continue
        seen.add(key); groups.setdefault(row['sheet_ref'], []).append(row)
    dependencies = {}
    for index, selected in enumerate(groups.values(), 1):
        first = selected[0]
        meanings = []
        for name, item in first['source_meanings'].items():
            if item['status'] == 'selected':
                meanings.append((name, item['witness']['quote']))
            elif item['status'] == 'withheld_electrical_operand':
                meanings.append((name, 'Source meaning retained; its quotation contains an unrequested electrical operand.'))
        meanings.extend((('Molecular arrangement', first['arrangement_kind']['value']),
                         ('Current meaning', first['current_kind']['value']),
                         ('Reversal applicability', first['arrangement_relation']['value'])))
        section(parts, 'Source electrical experiment ' + str(index), table(('Scientific meaning', 'Source value'), meanings))
        section(parts, 'Requested electrical numerical sections', table(
            ('Section', 'Component', 'Value', 'Unit', 'Status', 'Unavailable reason', 'Origin'),
            [(r['section'], r['component'], r['value'], r['unit'], r['status'], r['unavailable_reason'], r['origin']) for r in selected]))
        section(parts, 'Electrical interpretation', table(('Component', 'Calculation', 'Meaning'),
            [(r['component'], r['formula'], r['meaning']) for r in selected]))
        readings = []
        for row in selected:
            for operand in row['operands']:
                reading = operand['reading']; spread = operand['spread_reading']
                if reading is not None:
                    readings.append((operand['role'], reading['number']['quote'], reading['native_unit'],
                        None if spread is None else spread['number']['quote'], operand['spread_kind']['value'],
                        reading['conversion_origin']))
        if readings:
            section(parts, 'Requested original electrical readings', table(
                ('Quantity', 'Printed point', 'Printed unit', 'Printed spread', 'Spread meaning', 'Conversion origin'), readings))
        reuse = []
        for row in selected:
            labels = []
            for key in row['measurement_keys']:
                dependencies.setdefault(key, 'measurement ' + str(len(dependencies) + 1))
                labels.append(dependencies[key])
            reuse.append((row['component'], ', '.join(labels) or 'physical measurement identity not supplied'))
        section(parts, 'Electrical measurement reuse', table(('Component', 'Original measurement dependencies'), reuse))
        section(parts, 'Electrical uncertainty and limits', table(('Question', 'Meaning'), [
            ('Joint covariance', first['variance_status'] + '; source origin ' + str(first['covariance_origin'])),
            ('Printed spread', 'Retains its selected meaning; it does not by itself supply joint covariance.'),
            ('Replication', 'Event, bilayer and histogram counts are not evaluated as independent preparation counts here.'),
            ('Charge equivalents', 'Do not establish the ion identity, fluoride flux, pore count or polypeptide turnover.'),
            ('Baseline', 'A closed-channel baseline is not a protein-free membrane control.'),
            ('Repeated numerical views', 'Share the original measurements and add no independent verification.'),
        ]))
