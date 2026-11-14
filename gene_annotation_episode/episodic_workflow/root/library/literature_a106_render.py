"""Present exact A106 results with their experiment and source meanings.

Equal experimental metadata may share an adjacent numerical table. Saved
values, witnesses, qualifications and selected versions stay unchanged. No
labels replace cells and no model-side joins are needed.
"""
from collections.abc import Mapping
import json


_CELL_FIELDS = frozenset((
    'component', 'dimension', 'value', 'unit', 'status', 'reasons', 'formula',
    'meaning', 'measurement_keys', 'source_refs', 'input_origins', 'conditions', 'bound',
))


def is_assessment(row):
    return (isinstance(row, Mapping)
        and row.get('evaluation_scope') == 'intervention_experimental_evidence'
        and row.get('assay_type') == 'intervention_response'
        and isinstance(row.get('sheet_ref'), str)
        and isinstance(row.get('component'), str)
        and isinstance(row.get('experiment_assessment'), Mapping)
        and isinstance(row.get('experimental_design'), Mapping))


def is_final(row):
    return (isinstance(row, Mapping) and row.get('axis') == 'A106'
        and row.get('evaluation_scope') == 'a106_intervention_experimental_evidence'
        and row.get('component') == 'experimental_subscore'
        and isinstance(row.get('sheet_ref'), str)
        and isinstance(row.get('selected_components'), (list, tuple))
        and all(is_assessment(cell) for cell in row['selected_components']))


def is_result(row):
    return is_assessment(row) or is_final(row)


def _key(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _copy(value):
    if isinstance(value, Mapping):
        return {name: _copy(child) for name, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy(child) for child in value]
    return value


def assessment_groups(rows):
    """Keep different experiment uses/versions distinct; group equal context."""
    groups = {}
    for row in rows:
        shared = {name: _copy(value) for name, value in row.items()
                  if name not in _CELL_FIELDS}
        key = _key(shared)
        if key not in groups:
            groups[key] = {'experiment': shared, 'components': []}
        component = {name: _copy(value) for name, value in row.items()
                     if name in _CELL_FIELDS}
        if component not in groups[key]['components']:
            groups[key]['components'].append(component)
    return list(groups.values())


def split_reports(reports):
    """Separate exact A106 rows for direct rendering; preserve ordinary fields."""
    ordinary, results = [], []
    for report in reports:
        if not isinstance(report, Mapping):
            ordinary.append(report)
            continue
        remainder = {}
        for name, value in report.items():
            if (isinstance(value, (list, tuple)) and value
                    and all(is_result(row) for row in value)):
                results.append({'return_field': name, 'rows': _copy(value)})
            else:
                remainder[name] = value
        if remainder:
            ordinary.append(remainder)
    return ordinary, results


def _name(reference, records, fallback):
    record = records.get(reference)
    label = (record.get('label') or record.get('name')) if isinstance(record, Mapping) else None
    return str(label) if label else fallback


def _inline(value):
    if isinstance(value, Mapping):
        return '; '.join(name.replace('_', ' ') + ': ' + _inline(child)
                        for name, child in value.items())
    if isinstance(value, (list, tuple)):
        return '; '.join(_inline(child) for child in value) or 'None recorded'
    return 'Not supplied' if value is None else str(value)


def render_received(parts, results, *, section, table, values, records=None):
    """Place actual context and exact saved values together without indirection."""
    records = records or {}
    supplied = [row for result in results for row in result['rows']]
    successors = {}
    for row in supplied:
        rows = [row] if is_assessment(row) else row['selected_components']
        for assessment in rows:
            prior = assessment['experiment_assessment'].get('revises_sheet_ref')
            if prior is not None:
                successors.setdefault(prior, set()).add(assessment['sheet_ref'])
        if is_final(row) and row.get('revises_subscore_ref') is not None:
            successors.setdefault(row['revises_subscore_ref'], set()).add(row['sheet_ref'])

    def version(reference):
        following = successors.get(reference)
        if following:
            section(parts, 'Saved version status',
                'Historical saved version: another received version explicitly supersedes it. '
                'Its original values below are retained unchanged.')
        else:
            section(parts, 'Saved version status',
                'This is the exact saved version delivered here. A global current-version '
                'designation was not supplied; delivery order is not a revision selection.')

    def assessments(rows, title):
        for group in assessment_groups(rows):
            experiment = group['experiment']
            label = _name(experiment['experiment_ref'], records, 'Source-reported intervention experiment')
            section(parts, title + ': ' + label, values(experiment))
            version(experiment['sheet_ref'])
            numerical = []
            for row in group['components']:
                value = row.get('value')
                limits = {name: row[name] for name in ('bound', 'reasons', 'conditions')
                          if name in row and row[name] not in (None, [], ())}
                numerical.append((row['component'].replace('_', ' '), row.get('meaning', ''),
                    value if value is not None else 'Unavailable', row.get('unit'), row.get('status'),
                    _inline(limits) if limits else 'No additional limitation recorded'))
            section(parts, 'Saved numerical components for this experiment', table(
                ('Component', 'Scientific meaning', 'Saved value', 'Unit', 'Status', 'Recorded limits'), numerical))
            definitions = [{name: row[name] for name in ('component', 'formula',
                'measurement_keys', 'source_refs', 'input_origins') if name in row}
                for row in group['components']]
            if any(len(row) > 1 for row in definitions):
                section(parts, 'Original numerical definitions and source ownership', values(definitions))

    for result in results:
        section(parts, 'A106 saved results requested in ' + result['return_field'],
            'The actual saved results below retain their experiment and conditions. '
            'These scientific values are separate from the original action earned credit.')
        assessments([row for row in result['rows'] if is_assessment(row)], 'Intervention experiment')
        for row in result['rows']:
            if not is_final(row):
                continue
            context = {name: _copy(value) for name, value in row.items()
                if name not in ('selected_components', 'value', 'available_value', 'status', 'unit',
                    'unavailable_reasons', 'conditions')}
            section(parts, 'A106 main evidence scoring sheet and biological question', values(context))
            value = row.get('value')
            section(parts, 'Saved A106 experimental subscore', table(
                ('Component', 'Saved value', 'Unit', 'Status', 'Recorded limits'),
                [(row['component'].replace('_', ' '), value if value is not None else 'Unavailable',
                    row.get('unit'), row.get('status'), _inline({
                        'unavailable_reasons': row.get('unavailable_reasons', []),
                        'conditions': row.get('conditions', [])}))]))
            if row.get('available_value') is not None and row.get('status') != 'complete':
                section(parts, 'Separately labelled supported subtotal', values({
                    'available_value': row['available_value'], 'unit': row['unit'],
                    'meaning': 'Saved partial subtotal; the complete experimental subscore remains unavailable'}))
            version(row['sheet_ref'])
            assessments(row['selected_components'], 'Experiment actually selected by this saved main sheet')


__all__ = ['is_assessment', 'is_final', 'is_result', 'assessment_groups',
           'split_reports', 'render_received']
