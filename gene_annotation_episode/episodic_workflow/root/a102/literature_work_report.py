"""Read-only accounts of completed own work and its recorded iterator credit.

This projection uses original action and completion receipts. It performs no
scientific assessment, grading, action, or credit calculation. Equal selections
with equal outcomes are grouped for display; their original decisions remain
addressable in the ordinary history.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json

from .literature_work_results import (DATABASE_PREFIXES, DISCOVERY_TOOLS,
    original_json_sql, returned_result, result_projection_sql)


_CHILD_PROVENANCE_SOURCES = frozenset({
    'subject_refs', 'committed_record_refs', 'record_refs', 'changed_record_refs',
    'available_record_refs', 'interpretation_basis_refs', 'last_outcome_refs',
})
_SCORING_POPULATION_TOOLS = frozenset({
    'literature.assay_grading.populate', 'literature.a105.aggregate',
    'literature.a108_grading.populate', 'literature.a108.aggregate',
})
_SCORING_RESULT_FIELDS = (
    'component', 'value', 'unit', 'status', 'reasons', 'missing_inputs', 'unavailable_reason',
)


def _scoring_cell_result(cell):
    """Keep an original action's literal result, without repeating its full sheet."""
    if not isinstance(cell, Mapping):
        return deepcopy(cell)
    return {name: deepcopy(cell[name]) for name in _SCORING_RESULT_FIELDS if name in cell}


def _scoring_population_result(value):
    result = returned_result('', value)
    if isinstance(result, Mapping) and isinstance(result.get('saved_components'), (list, tuple)):
        result['saved_components'] = [_scoring_cell_result(cell) for cell in result['saved_components']]
    return result


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


def _child_return_receipts(store, context):
    """Read only this parent's retained typed delivery attempts, never child work."""
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_report_attempts'").fetchone() is None:
        return {}
    return {row['decision_index']: row for row in store.db.execute(
        'SELECT decision_index,contract,form,failure FROM runtime_report_attempts '
        'WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
        (context.run_id, context.episode_id))}


def _child_return_result(receipt, completion):
    """Describe an admitted result without retransmitting historical cell bodies.

    Sheet references identify the exact returned versions. Literal numerical
    results stay beside the original action's credit; full current criteria
    and source qualifications are presented separately, once. Visibility
    inventories remain retained in their original receipt. Other requested
    typed values are preserved as returned, without judging or reinterpreting
    the child's own interpretation.
    """
    result = {'child_completion': {name: value for name, value in completion.items()
                                  if name != 'failure'}}
    if receipt is None or receipt['failure'] is not None or completion.get('report_delivery') != 'admitted':
        return result
    form = _decoded(receipt['form'], {})
    contract = _decoded(receipt['contract'], {})
    if not isinstance(form, Mapping) or not isinstance(contract, Mapping):
        return result
    properties = contract.get('measurements', {}).get('schema', {}).get('properties', {})
    sheets = {}
    requested = {}
    for name, declaration in properties.items():
        if name not in form or not isinstance(declaration, Mapping):
            continue
        value = form[name]
        source = declaration.get('x-source')
        item_fields = declaration.get('items', {}).get('properties', {})
        numerical = (isinstance(source, str) and source.startswith('literature_')
            and source.endswith('_cells') and {'sheet_ref', 'component'} <= set(item_fields))
        if numerical and isinstance(value, (list, tuple)):
            for cell in value:
                reference = cell.get('sheet_ref') if isinstance(cell, Mapping) else None
                if isinstance(reference, str):
                    sheet = sheets.setdefault((source, reference), {
                        'source': source, 'sheet_ref': reference, 'results': []})
                    selected_result = _scoring_cell_result(cell)
                    if selected_result not in sheet['results']:
                        sheet['results'].append(selected_result)
        elif source not in _CHILD_PROVENANCE_SOURCES:
            requested[name] = value
    if sheets:
        result['admitted_scoring_sheets'] = list(sheets.values())
    if requested:
        result['requested_return_values'] = requested
    return result


def _decoded(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            # An executed invalid request still belongs in its original work
            # report. Malformed arguments cannot invalidate the next display.
            return default
    return value


def _indices(values):
    groups = []
    for value in values:
        if groups and value == groups[-1][-1] + 1:
            groups[-1].append(value)
        else:
            groups.append([value])
    return ', '.join(str(group[0]) if len(group) == 1
        else f'{group[0]}–{group[-1]}' for group in groups)


def source_metadata(store, possessed_references):
    """Resolve already possessed source names without reading source contents."""
    sources = [ref for ref in possessed_references
               if isinstance(ref, str) and ref.startswith('source_')]
    rows = store.db.execute("SELECT id,json_extract(data,'$.label') AS label,"
        "json_extract(data,'$.title') AS title,json_extract(data,'$.uri') AS uri,"
        "json_extract(data,'$.provider') AS provider FROM records "
        "WHERE record_type='source' AND id IN (SELECT value FROM json_each(?))",
        (json.dumps(sources),))
    return {row['id']: {'id': row['id'], 'record_type': 'source',
        'label': row['label'] or row['title'] or row['uri'] or row['provider'] or 'Received source'}
        for row in rows}


def completed_work(store, context):
    """Use only this episode's actual action/iterator receipts; never child logs."""
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone()
    if exists is None:
        return []
    credits = {}
    for receipt in store.db.execute("""SELECT
            json_extract(observation,'$.decision_index') AS decision_index,
            json_extract(observation,'$.step.marginal_credit') AS earned_credit
            FROM runtime_observations WHERE run_id=? AND episode_id=?
            ORDER BY unit_index""", (context.run_id, context.episode_id)):
        if receipt['earned_credit'] is not None:
            credits.setdefault(receipt['decision_index'], []).append(receipt['earned_credit'])
    child_returns = _child_return_receipts(store, context)
    rows = store.db.execute("""SELECT a.decision_index,a.action AS original_selection,
        json_extract(a.action,'$.kind') AS kind,
        json_extract(a.action,'$.tool') AS tool,
        json_extract(a.action,'$.role') AS role,
        json_extract(a.action,'$.goal') AS child_goal,
        json_extract(a.action,'$.purpose') AS child_purpose,
        json_extract(a.action,'$.assignment') AS child_assignment,
        json_extract(a.action,'$.arguments') AS arguments,
        json_extract(a.action,'$.evidence_processing.gradings') AS gradings,
        json_extract(a.result,'$.status') AS status,
        json_extract(a.result,'$.feedback.code') AS failure,
        json_extract(a.result,'$.aliases') AS aliases,
        json_extract(a.result,'$.result.sheet_ref') AS sheet_ref,
        json_extract(a.result,'$.changed_record_refs') AS changed,
        json_extract(a.result,'$.evidence_processing.gradings') AS saved_gradings,
        json_extract(a.result,'$.delivery_resolution_index') AS delivery_resolution_index,
        """ + original_json_sql('$.child_completion') + """ AS child_completion,
        """ + original_json_sql('$.feedback') + """ AS feedback,
        json_extract(a.result,'$.error_code') AS error_code,
        """ + original_json_sql('$.errors') + """ AS errors,
        """ + original_json_sql('$.conflicts') + """ AS conflicts,
        """ + result_projection_sql() + """ AS returned
        FROM runtime_actions a
        WHERE a.run_id=? AND a.episode_id=? AND a.result IS NOT NULL
        ORDER BY a.decision_index""", (context.run_id, context.episode_id))
    groups = {}
    fields = ('source_ref', 'input_ref', 'subject_ref', 'query', 'term', 'text_query', 'provider', 'database',
              'view', 'parameter', 'assay_type', 'grader_type', 'quantity_kind',
              'experiment_ref', 'assertion_ref', 'original_observation_ref',
              'decision_indices', 'record_index', 'record_indices', 'contains', 'contains_all',
              'page', 'size', 'cursor', 'reviewed', 'start', 'end', 'offset', 'limit',
              'representation')
    for row in rows:
        aliases = _decoded(row['aliases'], {})
        def actual_reference(value):
            return (aliases.get(value[1:], value)
                if isinstance(value, str) and value.startswith('@') else value)
        arguments = _decoded(row['arguments'], {})
        if not isinstance(arguments, Mapping):
            arguments = {}
        tool = row['tool'] or ''
        discovery = (tool in DISCOVERY_TOOLS or tool.startswith(DATABASE_PREFIXES)
            or tool in {'source.read', 'source.locate', 'episode.history'})
        inputs = ({name: actual_reference(value) for name, value in arguments.items()}
            if discovery or tool.startswith('source.') else
            {name: actual_reference(arguments[name]) for name in fields if name in arguments})
        selected = []
        for grading in _decoded(row['gradings'], []):
            actual = _decoded(grading.get('arguments'), {})
            if isinstance(actual, Mapping):
                selected.append({name: actual_reference(actual[name]) for name in fields if name in actual})
        operation = row['tool'] or ('Interpret source evidence with selected purpose-specific grading'
            if selected else 'Record scientific reasoning' if row['kind'] == 'reason'
            else 'Receive child investigation: ' + row['role'] if row['role']
            else row['kind'])
        if selected:
            inputs['selected_graders'] = selected
        completion = _decoded(row['child_completion'], {})
        if not isinstance(completion, Mapping):
            completion = {}
        if row['role'] or completion:
            assignment = _decoded(row['child_assignment'], {})
            if not isinstance(assignment, Mapping):
                assignment = {}
            inputs.update({name: row[field] for name, field in
                (('question', 'child_goal'), ('requested_result', 'child_purpose'))
                if row[field] is not None})
            inputs.update({name: assignment[name] for name in
                ('source_refs', 'prior_search_refs', 'search_result_refs',
                 'question_context_refs', 'source_ref', 'representation', 'artifact_ref', 'selection')
                if name in assignment})
            if isinstance(assignment.get('page'), Mapping):
                inputs['page'] = {name: assignment['page'][name] for name in
                    ('source_ref', 'representation', 'artifact_ref', 'question_context_refs')
                    if name in assignment['page']}
        # Actual read ranges are retained together, not silently described as
        # a complete source inspection or independent scientific evidence.
        source_range = {name: arguments[name] for name in
            ('start', 'end', 'offset', 'limit', 'representation') if name in arguments}
        actual_result = returned_result(row['tool'], _decoded(row['returned'], {}))
        if tool in _SCORING_POPULATION_TOOLS:
            actual_result = _scoring_population_result(_decoded(row['returned'], {}))
        resolution = row['delivery_resolution_index']
        child_receipt = child_returns.get(row['decision_index'] if resolution is None else resolution)
        if completion:
            actual_result = _child_return_result(child_receipt, completion)
        feedback = _decoded(row['feedback'], row['feedback'])
        diagnostics = {name: (row[name] if name == 'error_code' else _decoded(row[name], row[name]))
            for name in ('feedback', 'error_code', 'errors', 'conflicts') if row[name] is not None}
        if not any(diagnostics.values()):
            diagnostics = {}
        if completion.get('failure') is not None:
            diagnostics['child_completion_failure'] = completion['failure']
        if child_receipt is not None and child_receipt['failure'] is not None:
            diagnostics['report_delivery_failure'] = _decoded(child_receipt['failure'], child_receipt['failure'])
        saved_gradings = _decoded(row['saved_gradings'], [])
        if saved_gradings:
            actual_result = {'returned_result': actual_result,
                'saved_gradings': [{'status': grading.get('status'),
                    'result': _scoring_population_result(grading.get('result', {}))}
                    for grading in saved_gradings]}
        earned = credits.get(row['decision_index'])
        selection_identity = hashlib.sha256(row['original_selection'].encode('utf-8')).hexdigest()
        changed = _decoded(row['changed'], [])
        # Page bodies and full history returns are deliberately not copied.
        # Their projected metadata alone cannot prove equal returned content.
        known_result = (tool in DISCOVERY_TOOLS or tool.startswith(DATABASE_PREFIXES)
            or bool(saved_gradings))
        # Only equal original selections, returned facts, failures and credit
        # marks may share a display row. Different history windows or byte
        # ranges remain different completed work, even when both earned zero.
        key = json.dumps([selection_identity, operation, inputs, row['status'],
            actual_result, diagnostics, changed, aliases, earned,
            None if known_result else row['decision_index']],
            sort_keys=True, ensure_ascii=False)
        if key not in groups:
            groups[key] = {'operation': operation, 'inputs': inputs,
                'status': row['status'], 'failure_code': row['failure'] or row['error_code'],
                'returned_result': actual_result, 'feedback': feedback,
                'returned_diagnostics': diagnostics,
                'decisions': [], 'earned_credit': 0, 'credit_receipts': 0,
                'original_credit_marks': earned,
                'unobserved_actions': 0, 'saved_sheet_refs': [],
                'changed_record_refs': [], 'source_ranges': []}
        group = groups[key]
        group['decisions'].append(row['decision_index'])
        if earned is None:
            group['unobserved_actions'] += 1
        else:
            group['earned_credit'] += sum(earned)
            group['credit_receipts'] += len(earned)
        saved = [row['sheet_ref']] if row['sheet_ref'] else []
        saved.extend(grading.get('result', {}).get('sheet_ref')
            for grading in saved_gradings)
        for reference in saved:
            if reference and reference not in group['saved_sheet_refs']:
                group['saved_sheet_refs'].append(reference)
        for reference in changed:
            if reference not in group['changed_record_refs']:
                group['changed_record_refs'].append(reference)
        if source_range:
            group['source_ranges'].append({'decision': row['decision_index'], **source_range})
    return [{**group, 'original_action_count': len(group['decisions']),
             'decisions': _indices(group['decisions'])}
            for group in groups.values()]


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
