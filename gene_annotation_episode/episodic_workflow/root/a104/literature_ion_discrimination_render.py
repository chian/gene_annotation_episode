"""Complete ion TASK and concise requested numerical/biological STEERING."""
from collections.abc import Mapping
from .domain import canonical
from .literature_ion_discrimination_prompt import ION_DISCRIMINATION_TASK
from .literature_ion_discrimination_storage import SCOPE


def is_row(value):
    return isinstance(value, Mapping) and value.get('evaluation_scope') == SCOPE and 'component' in value


def rows_from_values(value):
    if is_row(value): yield value
    elif isinstance(value, Mapping):
        for child in value.values(): yield from rows_from_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value: yield from rows_from_values(child)


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for value in report.values():
                if isinstance(value, (list, tuple)):
                    yield from (row for row in value if is_row(row))


def task_relevant(state):
    assignment = state.get('literature_assignment', {})
    return (isinstance(assignment, Mapping) and bool(assignment.get('requested_ion_discrimination_components'))
        or state.get('literature_ion_discrimination_work', {}).get('version') == 'literature_ion_discrimination_task_v1'
        or any(rows_from_values(state.get('last_local_outcome', {})))
        or any(rows_from_values(state.get('current_report_update', {})))
        or any(rows_from_reports(state.get('child_reports', ()))))


def hidden_records(rows, records):
    """A broad alias cannot expand private numbers through generic records."""
    rows = list(rows)
    locations = [loc for row in rows for loc in row['withheld_locations']]
    covariance_sources = {row['covariance']['source_ref'] for row in rows if row['covariance']['source_ref']}
    hidden = set()
    from .literature_ion_discrimination_storage import _DISPLAY_PATTERNS
    for ref, record in records.items():
        anchor = record.get('anchor')
        if not isinstance(anchor, Mapping): continue
        overlap = any(anchor.get('artifact_ref') == loc['artifact_ref']
            and type(anchor.get('start')) is int and type(anchor.get('end')) is int
            and anchor['start'] < loc['end'] and loc['start'] < anchor['end'] for loc in locations)
        scopes = {source for row in rows for source in row['source_scope']}
        source = anchor.get('source_ref')
        quote = anchor.get('quote', '')
        if (overlap or source in covariance_sources or source in scopes and isinstance(quote, str)
                and any(pattern.search(quote) for pattern in _DISPLAY_PATTERNS)): hidden.add(ref)
    return hidden


def _domain(domain):
    if domain is None: return 'unavailable'
    def endpoint(side, infinity):
        if domain[side + '_unbounded']: return infinity
        if domain[side] is not None: return str(domain[side])
        exact = domain[side + '_exact']
        if exact is None: return 'finite endpoint unavailable'
        numerator, denominator = exact['numerator'], exact['denominator']
        return numerator if denominator == '1' else numerator + '/' + denominator
    lower = endpoint('lower', '−∞')
    upper = endpoint('upper', '+∞')
    left = '(' if domain['lower_unbounded'] else '[' if domain['lower_inclusive'] is True else '(' if domain['lower_inclusive'] is False else '?'
    right = ')' if domain['upper_unbounded'] else ']' if domain['upper_inclusive'] is True else ')' if domain['upper_inclusive'] is False else '?'
    return left + lower + ', ' + upper + right


def render_received(parts, rows, *, section, table):
    groups = {}; seen = set()
    for row in rows:
        key = canonical(row)
        if key in seen: continue
        seen.add(key); groups.setdefault(row['sheet_ref'], []).append(row)
    dependencies = {}
    for index, selected in enumerate(groups.values(), 1):
        first = selected[0]
        meanings = []
        for name, value in first['source_meanings'].items():
            if name in ('preferred', 'alternative'):
                meanings.extend((name + ' ' + field, item['display_text']) for field, item in value.items() if item)
            elif value: meanings.append((name, value['display_text']))
        section(parts, 'Source ion comparison ' + str(index), table(('Scientific meaning', 'Source definition'), meanings))
        section(parts, 'Requested ion-discrimination numerical components', table(
            ('Component', 'Value', 'Threshold', 'Unit', 'Relation', 'Status', 'Origin', 'Quantity kind'),
            [(r['component'], r['value'], r['threshold'], r['unit'], r['relation'], r['status'], r['origin'], r['quantity_kind']) for r in selected]))
        section(parts, 'Ion comparison relationships', table(('Question', 'Source interpretation'),
            [(name, value['value']) for name, value in first['relationships'].items()]))
        if first['nonintended_differences']:
            section(parts, 'Nonintended experimental differences', table(('Aspect', 'Source meaning'),
                [(d['aspect'], '; '.join(w['display_text'] for w in d['support'] if w))
                    for d in first['nonintended_differences']]))
        if first['adjustment_bindings']:
            section(parts, 'Selected control applications', table(
                ('Difference', 'Arm', 'Compiled stage', 'Control application', 'Saved stage verified', 'Source meaning'),
                [(b['difference_index'], b['arm'], b['compiled_stage'], b['control_application'], b['compiled_stage_verified'],
                    '; '.join(w['display_text'] for w in b['support'] if w)) for b in first['adjustment_bindings']]))
        for operand in first['operands']:
            if operand['source_quantity_meanings'] is not None:
                section(parts, operand['role'].capitalize() + ' quantity meanings', table(('Meaning', 'Source interpretation'),
                    [(name, value['value']) for name, value in operand['source_quantity_meanings'].items()]))
            if operand['compiled_meanings'] is not None:
                compiled = operand['compiled_meanings']
                section(parts, operand['role'].capitalize() + ' compiled activity meanings', table(('Meaning', 'Source definition'),
                    [(name, text) for name, text in compiled['assay_meanings'].items() if text is not None]
                    + [(name, 'Source literal retained; requested numerical scope cannot be separated from this possessed literal.')
                        for name, status in compiled['literal_display_status'].items() if status == 'unrequested_numerical_scope_unresolved']
                    + [('endpoint', compiled['endpoint_kind']), ('arrangement', compiled['arrangement_kind'])]
                    + [('correction ' + name, value) for name, value in compiled['correction_stages'].items()]
                    + [('operand ' + name, value) for name, value in compiled['operand_meanings'].items()]))
        section(parts, 'Distinct numerical domains; none is a confidence interval', table(
            ('Component', 'Reported estimate', 'Estimator', 'Nominal threshold arithmetic', 'Conditional physical parameter', 'Zero denominator'),
            [(r['component'], *(_domain(r[name]) for name in ('reported_domain', 'estimator_domain', 'nominal_domain', 'physical_domain')),
                r['zero_denominator_case']) for r in selected]))
        section(parts, 'Ion component qualifications', table(('Component', 'Calculation', 'Meaning', 'Applicability', 'Derivation', 'Approximation', 'Source qualifications', 'Unavailable reasons', 'Limits'),
            [(r['component'], r['formula_code'], r['meaning'], r['scientific_applicability'], r['derivation'], r['approximation'],
                ', '.join(r['source_qualifications']), ', '.join(r['unavailable_reasons']), ', '.join(r['limitations'])) for r in selected]))
        reuse = []
        for row in selected:
            names = []
            for dependency in row['dependencies']:
                labels = []
                for key in [*dependency['physical_keys'], *dependency['opaque_dependency_keys']]:
                    dependencies.setdefault(key, 'retained measurement ' + str(len(dependencies) + 1)); labels.append(dependencies[key])
                names.append(dependency['role'] + ': ' + (', '.join(labels) or 'identity unknown')
                    + '; ' + dependency['physical_identity_status'] + '; ' + dependency['origin'])
            reuse.append((row['component'], '; '.join(names)))
        section(parts, 'Ion component measurement reuse', table(('Component', 'Original dependencies'), reuse))
        section(parts, 'Ion uncertainty and scope', table(('Question', 'Meaning'), [
            ('Joint activity covariance', first['covariance']['status'] + '; origin ' + str(first['covariance']['origin'])),
            ('Requested uncertainty', '; '.join(r['component'] + ': ' + r['variance_status'] for r in selected)),
            ('Replication', 'Complementary readouts and repeated transforms do not establish independent preparations.'),
            ('Nominal thresholds', 'Literal threshold division is distinct from a supported physical bound.'),
            ('Attribution and relevance', 'Isolation of the measured protein/ion effect differs from the endpoint bearing on a functional assertion.'),
            ('Scoring scope', 'Native discrimination components; no complete common reliability, validity or relevance score, target transfer or annotation credit.'),
        ]))


__all__ = ['ION_DISCRIMINATION_TASK', 'is_row', 'rows_from_values', 'rows_from_reports',
    'task_relevant', 'hidden_records', 'render_received']
