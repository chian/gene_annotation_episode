"""Display supplied completed-work and scoring records; no receipt acquisition."""
from collections.abc import Mapping
from copy import deepcopy
import json


def _display_cell_results(cells):
    """Factor identical JSON result field values only within one sheet."""
    groups, positions = [], {}
    for cell in cells:
        if not isinstance(cell, Mapping) or not isinstance(cell.get('component'), str) or 'components' in cell:
            groups.append({'original': deepcopy(cell)})
            continue
        fields = {name: value for name, value in cell.items() if name != 'component'}
        key = json.dumps(fields, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if key not in positions:
            positions[key] = len(groups)
            groups.append({'original': deepcopy(cell), 'fields': deepcopy(fields),
                           'components': [cell['component']]})
        else:
            groups[positions[key]]['components'].append(cell['component'])
    return [({'components': group['components'], **group['fields']}
             if len(group.get('components', ())) > 1 else group['original'])
            for group in groups]


def _display_scoring_results(value):
    """Factor known work-result envelopes; keep the retained result untouched."""
    result = deepcopy(value)
    if not isinstance(result, Mapping):
        return result
    if isinstance(result.get('saved_components'), (list, tuple)):
        result['saved_components'] = _display_cell_results(result['saved_components'])
    sheets = result.get('admitted_scoring_sheets')
    for sheet in (sheets if isinstance(sheets, (list, tuple)) else ()):
        if isinstance(sheet, Mapping) and isinstance(sheet.get('results'), (list, tuple)):
            sheet['results'] = _display_cell_results(sheet['results'])
    if 'returned_result' in result:
        result['returned_result'] = _display_scoring_results(result['returned_result'])
    gradings = result.get('saved_gradings')
    for grading in (gradings if isinstance(gradings, (list, tuple)) else ()):
        if isinstance(grading, Mapping) and 'result' in grading:
            grading['result'] = _display_scoring_results(grading['result'])
    return result


def render_completed_work(rows, *, table, display):
    def inputs(row):
        return display.inline(row['inputs']) if row['inputs'] else 'No additional operands'

    result = []
    for row in rows:
        saved = len(row['saved_sheet_refs'])
        changed = len(row['changed_record_refs'])
        outcome = row['status'] or 'Status not recorded'
        if saved:
            outcome += f'; saved {saved} scoring sheet(s)'
        if changed:
            outcome += f'; changed {changed} record(s)'
        if row['failure_code']:
            outcome += '; ' + row['failure_code']
        actual = _display_scoring_results(row.get('returned_result'))
        if actual:
            if isinstance(actual, Mapping) and 'returned_provider_error' in actual:
                ordinary = {name: value for name, value in actual.items()
                    if name != 'returned_provider_error'}
                outcome += '; ' + display.inline(ordinary)
                outcome += '; complete returned provider error: ' + json.dumps(
                    actual['returned_provider_error'], ensure_ascii=False, indent=2, allow_nan=False)
            else:
                outcome += '; ' + display.inline(actual)
        diagnostics = row.get('returned_diagnostics')
        if diagnostics:
            # Returned errors retain their exact text/fields. In particular,
            # source-anchor errors must not disappear behind a later alias
            # failure or be rewritten as source-name display references.
            outcome += '; complete returned feedback and errors: ' + json.dumps(
                diagnostics, ensure_ascii=False, indent=2, allow_nan=False)
        marks = row.get('original_credit_marks')
        credit = (', '.join(str(value) for value in marks) if marks is not None
            else str(row['earned_credit']) if row['credit_receipts'] else 'No completion credit receipt')
        if marks is not None and len(marks) > 1:
            credit = 'Original completion gains: ' + credit
        if marks is not None and row.get('original_action_count', 1) > 1:
            credit += ' per original action (' + str(row['original_action_count']) + ' actions)'
        if row['unobserved_actions'] and row['credit_receipts']:
            credit += f'; {row["unobserved_actions"]} action(s) without a completion credit receipt'
        result.append((row['operation'], inputs(row), outcome, credit, row['decisions']))
    return table(('Work performed', 'Actual inputs', 'Recorded outcome',
                  'Recorded earned credit', 'Original decisions'), result)


def render_scoring_sheets(sheets, *, table, display):
    """Display exact saved current cells; never supply a new interpretation."""
    rows = []
    seen = set()
    for sheet in sheets:
        for scope, saved in [('Main evidence scoring sheet', sheet),
                *(('Subscoring sheet', item) for item in sheet.get('subscoring_sheets', []))]:
            reference = saved['sheet_ref']
            if reference in seen:
                continue
            seen.add(reference)
            for cell in saved.get('cells', []):
                subject = cell.get('experiment_ref', cell.get('target_context_ref', sheet.get('assertion_ref')))
                value = cell.get('value')
                reasons = cell.get('reasons', cell.get('unavailable_reason', []))
                rows.append((sheet['axis'] + ' ' + scope, display.ref(subject),
                    cell['component'].replace('_', ' '),
                    value if value is not None else 'Unavailable', cell.get('unit'),
                    cell.get('status'), display.inline(reasons), reference))
    return table(('Saved result', 'Experiment or contextual question', 'Component',
        'Saved value', 'Unit', 'Status', 'Recorded limitation', 'Sheet argument reference'), rows)
