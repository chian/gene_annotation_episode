"""Recurring investigation instructions; pure requested-cell scientific display."""
from collections.abc import Mapping

def is_row(row):
    return isinstance(row, Mapping) and row.get('evaluation_scope') in ('source_reported_rate_observations', 'source_reported_curve_precision') and ('component' in row)

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
                    yield from (r for r in value if is_row(r))

def render_received(parts, rows, *, section, table):
    rows = list(rows)
    render_grid_received(parts, [r for r in rows if is_grid_row(r)], section=section, table=table)
    rows = [r for r in rows if not is_grid_row(r)]
    comparisons = {}
    entries = {}
    for row in rows:
        comparisons.setdefault(row['sheet_ref'], []).append(row)
        for group in row['groups'].values():
            for entry in group['observed']['observation_labels'] if group['observed'] else ():
                entries.setdefault(entry['record_identity'], len(entries) + 1)
    for number, comparison in enumerate(comparisons.values(), 1):
        first = comparison[0]
        section(parts, 'Reported activity comparison ' + str(number), table(('Subject', 'Source panel / reported endpoint', 'Native source convention', 'Input origin'), [(first['subject'], first['panel'], first['source_native_unit'], ', '.join(first['input_origins']))]))
        section(parts, 'Requested reported-entry numerical components', table(('Component', 'Value', 'Unit', 'Status', 'Unavailable reason'), [(row['component'], row['value'], row['unit'], row['status'], row['unavailable_reason']) for row in comparison]))
        section(parts, 'Requested groups and actual count basis', table(('Role', 'Requested group', 'Observed status', 'Distinct source entries', 'Selected rows', 'Known entries', 'Available points', 'Representations', 'Complete', 'Association unresolved'), [(role, g['requested_label'], g['status'], g['observed']['entry_count'] if g['observed'] else None, g['observed']['selected_row_count'] if g['observed'] else None, g['observed']['known_entry_count'] if g['observed'] else None, g['observed']['point_entry_count'] if g['observed'] else None, g['observed']['representation_count'] if g['observed'] else None, g['observed']['complete'] if g['observed'] else None, g['observed']['association_unresolved'] if g['observed'] else None) for role, g in first['groups'].items()]))
        section(parts, 'Source-labelled entry identity and reuse', table(('Role', 'Group', 'Source observation label', 'Local report-entry identity', 'Status', 'Conflict', 'Association unresolved', 'Limitation'), [(role, g['requested_label'], entry['label'], 'source entry ' + str(entries[entry['record_identity']]), entry['status'], entry['conflicting'], entry['association_unresolved'], entry['unavailable_reason']) for role, g in first['groups'].items() for entry in (g['observed']['observation_labels'] if g['observed'] else ())]))
        section(parts, 'Scientific qualifications', table(('Meaning', 'Status'), [('Arithmetic', 'same-source reported convention only'), ('Preparation grouping / independent n', 'unknown'), ('SD / CV basis', 'descriptive across distinct reported entries; denominator entry_count-1 for SD'), ('SE / pairing / between-preparation SD', 'unavailable; grouping and sampling design unknown'), ('Physical unit conversion / assay method / blank / calibration / product attribution', 'unknown'), ('Experimental comparability / effect isolation', 'not established by common source, subject or units')]))
        section(parts, 'Requested calculation meanings', table(('Component', 'Calculation'), [(row['component'], row['formula']) for row in comparison]))
RATE_OBSERVATION_UNION_OPERATION_DESCRIPTION = 'Populate requested numerical components from actually received source XLSX cells. The original row-labelled branch retains reported-entry descriptive contrasts under its original layout and native convention. The explicit reported-curve branch reads concentration rows and reporting columns, authenticates selected unit/endpoint/sampling context, and supplies requested descriptive spread, fitted-estimator and conditional covariance scalars. Keep the mean of fitted parameter vectors separate from fitting point means. Source labels do not establish physical IID preparations. Preserve fixed concentration-coordinate scope, endpoint conflicts, source versus implementation limitations and available-only partials. Native amount-rate Vmax is not kcat; no overall reliability grade or annotation credit.'

def is_grid_row(value):
    return is_row(value) and value.get('evaluation_scope') == 'source_reported_curve_precision'


def legacy_task_relevant(state):
    assignment = state.get('literature_assignment', {})
    if isinstance(assignment, Mapping) and assignment.get('requested_rate_observation_components'):
        return True
    if state.get('literature_rate_grid_operation_lookup'):
        return True
    result = (state.get('last_local_outcome') or {}).get('result', {})
    if isinstance(result, Mapping) and result.get('view') == 'reported_rate_observation_components':
        return True
    return any((not is_grid_row(r) for r in rows_from_values((state.get('child_reports', ()), state.get('current_report_update', {})))))


def render_grid_received(parts, rows, *, section, table):
    grouped = {}
    seen = set()
    for row in rows:
        import json
        key = json.dumps(row, sort_keys=True, allow_nan=False)
        if key in seen:
            continue
        seen.add(key)
        grouped.setdefault(row['sheet_ref'], []).append(row)
    sets = {}
    estimators = {}
    models = {}

    def local(mapping, key, name):
        if key is None:
            return 'not applicable'
        if key not in mapping:
            mapping[key] = name + ' ' + str(len(mapping) + 1)
        return mapping[key]

    def exact(value):
        if value is None:
            return 'unknown'
        return value['numerator'] if value['denominator'] == '1' else value['numerator'] + '/' + value['denominator']
    for number, selected in enumerate(grouped.values(), 1):
        first = selected[0]
        section(parts, 'Reported curve precision ' + str(number), table(('Aspect', 'Scientific meaning'), [(name, value['display_text']) for name, value in first['source_context'].items()] + [('Source kind', first['source_kind']), ('Input origins', ', '.join(first['input_origins']))]))
        section(parts, 'Requested curve precision results', table(('Question', 'Ordinary value', 'Conditional scenario', 'Unit', 'Status', 'Estimator'), [(row['selector']['scope'] + ': ' + row['selector']['component'], row['value'], row['conditional_value'], row['unit'], row['status'], row['model_meaning']['estimator']) for row in selected]))
        coordinates = [(row['selector']['component'], c['role'], exact(c['exact_value']), c['unit'], c['status'], c['bound'], exact(c['exact_limit'])) for row in selected for c in row['coordinate_context']]
        if coordinates:
            section(parts, 'Named source concentration coordinates', table(('Component', 'Coordinate role', 'Reported point', 'Unit', 'Status', 'Bound', 'Reported limit'), coordinates))
        section(parts, 'Numerical meanings and limitations', table(('Component', 'Calculation', 'Numeric basis', 'Source point/count limits', 'Model or relationship limits', 'Implementation limits'), [(r['selector']['component'], r['formula_id'], r['numeric_basis'], ', '.join(r['source_missing_reasons']), ', '.join(r['relationship_reasons']), ', '.join(r['implementation_reasons'])) for r in selected]))
        section(parts, 'Sampling and fixed-coordinate scope', table(('Aspect', 'Meaning'), list(first['sampling'].items()) + list(first['scientific_scope'].items()) + [('Count basis', first['count_basis'])]))
        section(parts, 'Selected statistic reporting denominators', table(('Component', 'Reporting meaning', 'Count'), [(row['selector']['component'], key, value) for row in selected for key, value in row['reporting_counts'].items() if value is not None]))
        section(parts, 'Shared source and estimator dependencies', table(('Component', 'Source quantities', 'Estimator identity', 'Sampling scenario', 'Variance status'), [(row['selector']['component'], local(sets, tuple(row['input_measurement_keys']), 'shared source set'), local(estimators, row['estimator_key'], 'selected estimator'), ', '.join((local(models, k, 'declared scenario') for k in row['model_keys'])) or 'not used', row['variance_status']) for row in selected]))
        section(parts, 'Interpretation limits', table(('Meaning',), [('Source sets and estimator labels identify reuse, not independent experiments.',), ('Reporting columns and entry counts do not establish physical preparations or biological n.',), ('Reporter precision does not establish product identity, recovery, molecular attribution or annotation credit.',), ('Only requested scalars and their named concentration context are returned; other source entries and fitted values stay scoped.',)]))
