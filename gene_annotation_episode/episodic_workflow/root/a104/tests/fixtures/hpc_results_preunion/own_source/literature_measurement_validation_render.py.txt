"""Scientific text for exactly possessed precision/control numerical rows."""
from collections.abc import Mapping
from .domain import canonical
from .literature_measurement_validation_prompt import MEASUREMENT_VALIDATION_TASK
from .literature_measurement_validation_storage import SCOPE


def is_row(value):
    return isinstance(value, Mapping) and value.get('evaluation_scope') == SCOPE and 'component' in value


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
    return (isinstance(assignment, Mapping) and bool(assignment.get('requested_measurement_validation_components'))
        or state.get('literature_measurement_validation_work', {}).get('version') == 'literature_measurement_validation_task_v1'
        or any(rows_from_values((state.get('last_local_outcome', {}), state.get('current_report_update', {}))))
        or any(rows_from_reports(state.get('child_reports', ()))))


def hidden_records(rows, records):
    locations = [location for row in rows for location in row['withheld_locations']]
    hidden = set()
    for ref, record in records.items():
        anchor = record.get('anchor')
        if not isinstance(anchor, Mapping):
            continue
        if any(anchor.get('artifact_ref') == loc['artifact_ref']
                and type(anchor.get('start')) is int and type(anchor.get('end')) is int
                and anchor['start'] < loc['end'] and loc['start'] < anchor['end'] for loc in locations):
            hidden.add(ref)
    return hidden


def _number(row, name):
    if row[name] is not None:
        return str(row[name])
    exact = row['conditional_exact_value' if name == 'conditional_value' else 'exact_value']
    if exact is not None:
        return exact['numerator'] if exact['denominator'] == '1' else exact['numerator'] + '/' + exact['denominator']
    return 'unknown'


def render_received(parts, rows, *, section, table):
    groups, seen = {}, set()
    for row in rows:
        key = canonical(row)
        if key in seen:
            continue
        seen.add(key)
        groups.setdefault(row['sheet_ref'], []).append(row)
    dependencies, contributions = {}, {}
    for number, selected in enumerate(groups.values(), 1):
        first = selected[0]
        section(parts, 'Measurement validation ' + str(number), table(
            ('Scientific meaning', 'Source definition'),
            [(name, value['display_text'] if value is not None else 'unknown')
                for name, value in first['source_meanings'].items()]))
        section(parts, 'Requested precision and control components', table(
            ('Component', 'Basis', 'Interpreted value', 'Conditional value', 'Unit', 'Relation', 'Status', 'Origin'),
            [(row['component'], row['basis'], _number(row, 'value'), _number(row, 'conditional_value'),
                row['unit'], row['relation'], row['status'], row['origin']) for row in selected]))
        interpretations = []
        for row in selected:
            if row['relationships'] is not None:
                interpretations.extend((row['basis'], name, value['value']) for name, value in row['relationships'].items())
            if row['formula_relation'] is not None:
                interpretations.append(('control separation', 'source formula', row['formula_relation']['value']))
        section(parts, 'Population and source-meaning relationships', table(
            ('Basis', 'Question', 'Source interpretation'), dict.fromkeys(interpretations)))
        section(parts, 'Measurement component interpretation and limits', table(
            ('Component', 'Basis', 'Meaning', 'Interpretation', 'Calculation', 'Assumptions', 'Unavailable reasons'),
            [(row['component'], row['basis'], row['meaning'], row['interpretation'], row['formula'],
                ', '.join(row['assumptions']), ', '.join(row['unavailable_reasons'])) for row in selected]))
        reuse = []
        for row in selected:
            for key in row['input_measurement_keys']:
                dependencies.setdefault(key, 'source measurement ' + str(len(dependencies)+1))
            key = row['contribution_key']
            contributions.setdefault(key, 'shared contribution ' + str(len(contributions)+1))
            reuse.append((row['component'], row['basis'], contributions[key],
                ', '.join(dependencies[key] for key in row['input_measurement_keys']) or 'unavailable'))
        section(parts, 'Precision and control measurement reuse', table(
            ('Component', 'Basis', 'Contribution identity', 'Original dependencies'), reuse))
        section(parts, 'Measurement-validation scope', table(('Question', 'Limit'), [
            ('Within/between precision', 'Alternative bases; do not add them as independent variance components.'),
            ('Variance', 'Specified measurement population; not SE of its mean or uncertainty of CV/loss.'),
            ('Conditional estimate', 'Hypothetical displayed-summary arithmetic remains separate from an interpreted estimate.'),
            ('Product identity and attribution', 'Reporter precision does not establish identified product or productive coupling.'),
            ('Independent support', 'Repeated transforms share measurements and do not establish independent validation.'),
            ('Later credit', 'These components retain declared scientific meanings; target correspondence and annotation aggregation remain later work.'),
        ]))


__all__ = ['MEASUREMENT_VALIDATION_TASK', 'is_row', 'rows_from_values', 'rows_from_reports',
    'task_relevant', 'hidden_records', 'render_received']
