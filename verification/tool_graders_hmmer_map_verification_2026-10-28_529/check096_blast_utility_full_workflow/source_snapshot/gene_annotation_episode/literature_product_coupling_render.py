"""Scientific text for the exact possessed product/cofactor component rows."""
from collections.abc import Mapping

from .domain import canonical
from .literature_product_coupling_prompt import PRODUCT_COUPLING_TASK
from .literature_product_coupling_storage import SCOPE, REQUESTED


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
    return (isinstance(assignment, Mapping) and bool(assignment.get(REQUESTED))
        or state.get('literature_product_coupling_work', {}).get('version') == 'literature_product_coupling_task_v1'
        or any(rows_from_values((state.get('last_local_outcome', {}), state.get('current_report_update', {}))))
        or any(rows_from_reports(state.get('child_reports', ()))))


def hidden_records(rows, records):
    locations = [location for row in rows for name in ('withheld_locations', 'model_support_locations')
        for location in row[name]]
    hidden = set()
    for ref, record in records.items():
        for name in ('anchor', 'visual_anchor'):
            anchor = record.get(name)
            if not isinstance(anchor, Mapping):
                continue
            if any(anchor.get('artifact_ref') == loc['artifact_ref']
                    and type(anchor.get('start')) is int and type(anchor.get('end')) is int
                    and anchor['start'] < loc['end'] and loc['start'] < anchor['end'] for loc in locations):
                hidden.add(ref)
    return hidden


def _exact(value):
    if value is None:
        return 'unknown'
    return value['numerator'] if value['denominator'] == '1' else value['numerator']+'/'+value['denominator']


def _number(row, name):
    if row[name] is not None:
        return str(row[name])
    return _exact(row[{'value': 'exact_value', 'conditional_value': 'conditional_exact_value',
        'source_value': 'source_exact_value'}[name]])


def render_received(parts, rows, *, section, table):
    groups, seen = {}, set()
    for row in rows:
        key = canonical(row)
        if key in seen:
            continue
        seen.add(key); groups.setdefault(row['sheet_ref'], []).append(row)
    measurements, models, contributions = {}, {}, {}
    def label(mapping, key, prefix):
        if key is None:
            return 'unknown'
        mapping.setdefault(key, prefix+' '+str(len(mapping)+1))
        return mapping[key]
    def display(value):
        return 'unknown' if value is None else value['display_text']
    for index, selected in enumerate(groups.values(), 1):
        first = selected[0]
        section(parts, 'Product and cofactor evidence '+str(index), table(
            ('Scientific meaning', 'Source definition'),
            [(name, display(value)) for name, value in first['source_meanings'].items()]))
        section(parts, 'Requested product and cofactor components', table(
            ('Component', 'Interpreted value', 'Conditional value', 'Unit', 'Relation', 'Status', 'Origin', 'Physical fraction status'),
            [(row['component'], _number(row, 'value'), _number(row, 'conditional_value'), row['unit'],
                row['relation'], row['status'], row['origin'], row['physical_fraction_status']) for row in selected]))
        native = [row for row in selected if row['native_measurement_semantics'] is not None]
        if native:
            section(parts, 'Requested native reports and their meaning', table(
                ('Component', 'Source-native value', 'Source-native unit', 'Measurement meaning'),
                [(row['component'], _number(row, 'source_value'), row['source_unit'], row['native_measurement_semantics']) for row in native]))
        meanings = []
        for role, quantity in first['quantity_meanings'].items():
            if quantity is not None:
                meanings.extend([(role, 'quantity', display(quantity['label'])),
                    (role, 'source unit', display(quantity['unit']))])
                meanings.extend((role, name, quantity[name]['value']) for name in ('endpoint_role', 'measurement_semantics', 'normalization'))
        section(parts, 'Selected endpoint meanings', table(('Endpoint', 'Question', 'Source interpretation'), meanings))
        section(parts, 'Experimental relationships and attribution', table(
            ('Question', 'Source interpretation'), [(name, value['value']) for name, value in first['relationships'].items()]))
        section(parts, 'Product coupling interpretation and limits', table(
            ('Component', 'Meaning', 'Interpretation', 'Calculation', 'Assumptions', 'Unavailable reasons'),
            [(row['component'], row['meaning'], row['interpretation'], row['formula'],
                ', '.join(row['assumptions']), ', '.join(row['unavailable_reasons'])) for row in selected]))
        reuse = []
        for row in selected:
            reuse.append((row['component'], label(contributions, row['contribution_key'], 'shared contribution'),
                ', '.join(label(measurements, key, 'source measurement') for key in row['input_measurement_keys']) or 'unknown',
                ', '.join(label(models, key, 'reaction model') for key in row['input_model_keys']) or 'not used'))
        section(parts, 'Product coupling measurement and model reuse', table(
            ('Component', 'Contribution identity', 'Original dependencies', 'Reaction model'), reuse))
        model_rows = list({canonical(row['reaction_account']): row['reaction_account'] for row in selected
            if row['reaction_account'] is not None}.values())
        if model_rows:
            section(parts, 'Selected interpreted reaction account', table(
                ('Direction', 'Status', 'Model coefficient', 'Model identity'),
                [(model['direction'], model['status'], _exact(model['exact_value']),
                    label(models, model['model_key'], 'reaction model')) for model in model_rows]))
        covariance_rows = list({canonical(row['covariance']): row['covariance'] for row in selected
            if row['covariance'] is not None}.values())
        if covariance_rows:
            section(parts, 'Selected uncertainty provenance', table(
                ('Status', 'Origin', 'Ordered measurement owners', 'Units', 'Estimate basis', 'Variance status', 'Unavailable reason'),
                [(cov['status'], cov['origin'], ', '.join(label(measurements, key, 'source measurement') for key in cov['measurement_keys']),
                    ', '.join(cov['units']), cov['basis'], cov['variance_status'], cov['unavailable_reason']) for cov in covariance_rows]))
        section(parts, 'Product coupling scope', table(('Question', 'Limit'), [
            ('Attribution', 'A productive fraction describes the selected reaction system; chemical product identity does not quantify attribution to the studied molecule.'),
            ('Dependence', 'Ratio, fraction, percent and same-operand product reconstruction share measurements; reconstruction retains the original product contribution.'),
            ('Uncertainty', 'Supplied covariance concerns the selected rate estimates. Fixed substitution for uncertain stoichiometry excludes its variance and covariance.'),
            ('Nondetection', 'A source-reported zero with nondetection does not establish exact absence or a numerical detection limit.'),
            ('Later compilation', 'Common A105 reliability, validity and relevance compilation remains unfinished; target correspondence and annotation credit are separate work.'),
        ]))


__all__ = ['PRODUCT_COUPLING_TASK', 'is_row', 'rows_from_values', 'rows_from_reports',
    'task_relevant', 'hidden_records', 'render_received']
