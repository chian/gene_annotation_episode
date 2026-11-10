"""Deterministic, receiver-scoped accounts of completed work and earned credit.

The original action and completion receipts own these facts. Presentation does
not run a calculator, reprice historical work, infer biological support or read a
child's private journal. Axis adapters see only the original received outcome,
the already authorized receiver views and possessed meaning records.
"""
from collections.abc import Mapping
from copy import deepcopy
from functools import cache
from importlib import import_module
import json
import math

from .api_error_feedback import is_api_error_return
from .shared_information_results import outcome_view as shared_outcome_view

VERSION = 'completed_action_reports_v1'
_ADAPTERS = ('a101_work_report', 'a102_work_report', 'a103_work_report',
             'a104_work_report', 'a106_work_report', 'a107_work_report', 'a110_work_report')
_BODY_FIELDS = frozenset({'text', 'content', 'contents', 'body', 'provider_result',
    'stdout', 'stderr', 'raw_output', 'raw_response', 'raw_text', 'file_contents',
    'instructions', 'input_schema', 'output_schema', 'schema', 'contract',
    'initial_report_json', 'report_schema', 'outputSchema'})
_VIEW_FIELDS = ('received_structural_evidence', 'received_gene_context_execution',
    'received_partner_and_chemical_evidence', 'received_partner_and_chemical_native_components',
    'received_partner_and_chemical_qualifications', 'component_axis_scoring_sheets',
    'received_bvbrc_values', 'a101_sheet', 'a103_sheet', 'tool_attachments',
    'source_contributions', 'a104_sheet')


def _object_sql(expression, fields):
    # A returned failed action may contain malformed JSON in its argument
    # string. Present the recorded failure rather than failing the next view.
    valid = '(CASE WHEN json_valid(' + expression + ') THEN ' + expression + ' ELSE NULL END)'
    # Aggregate the complete field selection instead of passing one function
    # argument pair per field. SQLite builds have different function arities;
    # that interface must not restrict the scientific result fields retained.
    selected = json.dumps(tuple(fields), separators=(',', ':')).replace("'", "''")
    return ('json((SELECT json_group_object(selected_field.value,json_extract('
        + valid + ",'$.' || selected_field.value)) FROM json_each('" + selected
        + "') AS selected_field))")


_ARGUMENT_FIELDS = ('subject_ref', 'target_ref', 'source_ref', 'input_ref', 'query',
    'decision_indices', 'entry_id', 'section_id',
    'program', 'database', 'reference_ref', 'model_ref', 'profile_ref', 'query_ref',
    'request_ref', 'measurement_ref', 'resource_id', 'endpoint', 'view', 'start',
    'end', 'offset', 'limit', 'regions', 'selector', 'selection', 'target',
    'reference', 'target_model', 'reference_model', 'context_ref', 'scope',
    'parameter', 'component', 'components', 'requested_components', 'mode',
    'comparison_ref', 'assay_type', 'grader_type', 'quantity_kind',
    'experiment_ref', 'assertion_ref', 'numerator', 'denominator', 'native_ref',
    'analysis', 'split_index', 'family_analysis', 'organismal_analysis', 'tip_ids',
    'placement_ref', 'placement_refs', 'case_id', 'target_handle', 'handle',
    'job_ref', 'service', 'algorithm', 'publication_ref', 'need_ref',
    'evidence_refs', 'available_record_refs')
_RESULT_FIELDS = ('status', 'view', 'source_ref', 'sheet_ref', 'request_ref',
    'producer_operation', 'measurements', 'cells', 'components', 'comparisons',
    'native_comparisons', 'qualifications', 'unavailable', 'missing',
    'missing_inputs', 'failure', 'returncode', 'outcome', 'result_refs',
    'execution_result_refs', 'evidence_refs', 'snapshot_ref', 'subject_ref',
    'reference_ref', 'profile_ref', 'query_ref', 'target_ref', 'parameter',
    'count', 'total', 'returned_count', 'next_offset', 'next_query',
    'n_hits', 'n_records', 'matched_count', 'completed', 'execution_completed',
    'bit_score', 'bitscore', 'evalue', 'sequence_credit', 'structural_credit',
    'measurement_ref', 'native_ref', 'native_phylogeny_refs', 'execution_status',
    'scientific_status', 'new_execution_requested', 'analysis_need_ref',
    'commission_source_ref', 'execution_owner', 'next_owner', 'pbs_job_id',
    'partial_execution', 'missing_analysis_names', 'corresponding_relationships', 'analyses',
    'axis', 'scientific_profile', 'native_components', 'projection', 'version',
    'native_execution_state', 'requested_projection_status', 'diagnostics',
    'qualification_refs', 'native_execution_requested', 'publication_ref',
    'kind', 'evidence_refs', 'saved_grading_results', 'grading_delivery')


def _action_sql():
    fields = _object_sql('a.action', ('kind', 'tool', 'role', 'condition'))
    arguments = _object_sql("json_extract(a.action,'$.arguments')", _ARGUMENT_FIELDS)
    assignment = _object_sql("json_extract(a.action,'$.episode_assignment')",
        ('selection', 'evidence_refs', 'constraints'))
    grading = _object_sql("json_extract(g.value,'$.arguments')", (
        'source_ref', 'experiment_ref', 'assertion_ref', 'target_context_ref',
        'assay_type', 'grader_type', 'quantity_kind'))
    gradings = "(SELECT json_group_array(" + grading + ") FROM json_each(a.action,'$.evidence_processing.gradings') g)"
    counts = 'json_object(' + ','.join("'" + name + "',json_array_length(a.action,'$.commit."
        + name + "')" for name in ('source_subjects', 'observations', 'hypotheses', 'assessments', 'annotation_updates')) + ')'
    return ('json_set(' + fields + ",'$.arguments'," + arguments + ",'$.episode_assignment',"
        + assignment + ",'$.recorded_section_counts'," + counts + ",'$.selected_grading'," + gradings + ')')


def _outcome_sql():
    top = _object_sql('a.result', ('status', 'aliases', 'record_refs',
        'changed_record_refs', 'feedback', 'child_completion', 'error_code',
        'errors', 'conflicts', 'notices'))
    selected = _object_sql("json_extract(a.result,'$.result')", _RESULT_FIELDS)
    # Native axis envelopes contain already returned measured quantities,
    # unlike provider/file/text bodies. Axis adapters choose their actual
    # numerical fields before anything is rendered.
    native = ("COALESCE(json_extract(a.result,'$.result.body.schema'),"
        "json_extract(a.result,'$.result.schema'),'')")
    result = ("CASE WHEN (" + native + " LIKE 'a10%' OR " + native + " LIKE 'a110%') THEN json_extract(a.result,'$.result') "
        'ELSE ' + selected + ' END')
    projected = ('json_set(' + top + ",'$.result'," + result + ",'$.returned_record_count',"
        + "json_array_length(a.result,'$.result.records'))")
    api_error = ("(json_extract(a.action,'$.tool') LIKE 'api.%' OR "
        "json_extract(a.action,'$.tool') LIKE 'public.%') AND ("
        "json_extract(a.result,'$.status') IN ('invalid','failed','interrupted','unavailable','error') "
        "OR json_type(a.result,'$.feedback') NOT IN ('null') "
        "OR json_extract(a.result,'$.result.event.state')='failed' "
        "OR json_extract(a.result,'$.result.event.failure_code') IS NOT NULL "
        "OR json_extract(a.result,'$.result.native_response_state')='error')")
    return '(CASE WHEN ' + api_error + ' THEN a.result ELSE ' + projected + ' END)'


def _json(value, default=None):
    return default if value is None else json.loads(value) if isinstance(value, str) else value


def _references(value):
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(child, str) and (key == 'ref' or key.endswith('_ref')):
                yield child
            elif key.endswith('_refs') and isinstance(child, (tuple, list)):
                yield from (ref for ref in child if isinstance(ref, str))
            else:
                yield from _references(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _references(child)


def _compact(value):
    """Retain result facts, not another copy of source bytes or tool contracts."""
    if isinstance(value, Mapping):
        result = {}
        for key, child in value.items():
            if key in _BODY_FIELDS or key == 'diagnostic_ref' or key.startswith('private_'):
                continue
            if key in {'records', 'observations', 'assessments', 'annotations'} and isinstance(child, (list, tuple)) and all(
                    isinstance(row, Mapping) and 'record_type' in row for row in child):
                result[key + '_returned'] = len(child)
                # Explicit IDs remain reusable without copying generic verdict
                # objects over the numerical result that actually owns credit.
                references = [row if isinstance(row, str) else row['id'] for row in child
                    if isinstance(row, str) or isinstance(row, Mapping) and isinstance(row.get('id'), str)]
                if references:
                    result[key + '_refs'] = references
                continue
            result[key] = _compact(child)
        return result
    if isinstance(value, (tuple, list)):
        return [_compact(child) for child in value]
    return value


def _selection(selection, aliases):
    kind = selection.get('kind')
    if kind == 'tool':
        work = selection.get('tool', 'Selected tool')
        inputs = _compact(selection.get('arguments', {}))
    elif kind in {'child', 'episode_child', 'job_child'}:
        work = 'Receive child investigation: ' + str(selection.get('role', 'improvement'))
        inputs = _compact({key: value for key, value in selection.items()
            if key not in {'kind', 'report_schema', 'return_schema', 'initial_report_json'}})
    elif kind == 'reason':
        work = 'Record source findings and execute selected scientific calculations'
        inputs = {'recorded_sections': selection.get('recorded_section_counts', {})}
        if selection.get('selected_grading'):
            inputs['selected_grading'] = _compact(selection['selected_grading'])
    elif kind == 'wait':
        work, inputs = 'Observe selected pending work', _compact(selection.get('condition', {}))
    else:
        work, inputs = str(kind or 'Recorded action'), _compact(selection)

    def resolve(value):
        if isinstance(value, Mapping):
            return {key: resolve(child) for key, child in value.items()}
        if isinstance(value, (tuple, list)):
            return [resolve(child) for child in value]
        if isinstance(value, str) and value.startswith('@') and value[1:] in aliases:
            return aliases[value[1:]]
        return value
    return work, resolve(inputs)


def _meaning_records(workflow, source, state, references):
    """Only possessed/scoped records; never hydrate a numerical artifact."""
    working = state.get('working_state', {})
    result = {row['id']: deepcopy(row) for rows in working.values()
        if isinstance(rows, (tuple, list)) for row in rows
        if isinstance(row, Mapping) and isinstance(row.get('id'), str)}
    received = workflow.binding_context(source).received_record_refs
    requested = set(references).intersection(received)
    subset = workflow.store.reference_subset(requested, source.scope) if requested else []
    for reference in subset:
        if reference in result:
            continue
        record = workflow.store.get(reference)
        if record.get('record_type') == 'artifact':
            continue
        if record.get('record_type') == 'source':
            # The source's identity is possessed, not every private numerical
            # component in a referenced artifact. Exact admitted cells below
            # remain the sole source for returned numerical results.
            record = {key: record[key] for key in ('id', 'record_type', 'label',
                'title', 'name', 'uri', 'provider', 'origin') if key in record}
        result[reference] = deepcopy(record)
    return result


def _adapter_results(selection, outcome, records):
    result = []
    for name in _ADAPTERS:
        try:
            adapter = import_module('.' + name, __package__)
        except ModuleNotFoundError as error:
            # Separately implemented axis adapters may not yet exist in a
            # selected build. A missing transitive dependency is a real error.
            if error.name == __package__ + '.' + name:
                continue
            raise
        facts = adapter.completed_work_result(selection, outcome, records)
        if facts is not None:
            result.append(facts)
    return result


@cache
def _axis_report_fields(module_name, axis=None, include_sequence_credit=None):
    module = import_module('.' + module_name, __package__)
    arguments = (() if axis is None else (axis,))
    options = ({} if include_sequence_credit is None else
        {'include_sequence_credit': include_sequence_credit})
    return (frozenset(module.legacy_report_schema(*arguments, **options)['properties']),
            frozenset(module.report_schema(*arguments, **options)['properties']))


def _grading_report_values(form):
    """Project known old forms without repeating separate agent verdicts.

    Original typed forms remain immutable. Unknown/custom report schemas and
    purpose-specific grading contents are preserved rather than key-filtered.
    """
    if not isinstance(form, Mapping):
        return form
    fields = frozenset(form)
    specifications = [
        ('a101_investigation', None, 'sequence_credit' in form),
        ('a102_investigation', None, None),
        ('a103_investigation', None, None),
        ('a104_investigation', None, None),
        ('a102_structural_report', None, None),
    ]
    if form.get('axis') in ('A107', 'A110'):
        specifications.append(('component_axis_reports', form['axis'], None))
    for module, axis, include_credit in specifications:
        legacy, current = _axis_report_fields(module, axis, include_credit)
        if fields == legacy:
            return {name: value for name, value in form.items() if name in current}
    return form


def requested_action_history(workflow, source, *, before):
    """Retain outcomes this actor explicitly read through its own history tool.

    A later read does not revoke earlier received information. Only original
    own history returns are inspected; unrequested actions and other
    actors' journals are not read. This is presentation memory, not a new read,
    scientific interpretation, credit receipt or continuation observation.
    """
    db = workflow.store.db
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_actions'").fetchone() is None:
        return []
    retained = {}
    rows = db.execute("SELECT decision_index,result FROM runtime_actions WHERE run_id=? "
        "AND episode_id=? AND decision_index<? AND json_extract(action,'$.tool')='episode.history' "
        "AND result IS NOT NULL ORDER BY decision_index", (workflow.run_id, source.episode_id, before))
    fields = ('decision_index', 'kind', 'tool', 'selection', 'status', 'outcome',
        'admitted_report', 'report_delivery_failure', 'execution_timing')
    for row in rows:
        outcome = _json(row['result'], {})
        body = outcome.get('result', {}) if isinstance(outcome, Mapping) else {}
        if not isinstance(body, Mapping) or body.get('view') != 'records':
            continue
        pending = list(reversed(body.get('records', ())))
        while pending:
            record = pending.pop()
            if not isinstance(record, Mapping) or type(record.get('decision_index')) is not int:
                continue
            nested = record.get('outcome', {})
            nested = nested.get('result', {}) if isinstance(nested, Mapping) else {}
            if (record.get('tool') == 'episode.history' and isinstance(nested, Mapping)
                    and nested.get('view') == 'records'):
                # Keep requested leaves once, rather than copying a growing
                # history-of-history tree. Original receipts stay untouched.
                pending.extend(reversed(nested.get('records', ())))
                continue
            retained[record['decision_index']] = {
                'last_requested_at_decision': row['decision_index'],
                'record': {key: deepcopy(record[key]) for key in fields if key in record}}
    return [retained[index] for index in sorted(retained)]


def completed_action_reports(workflow, source, state, *, before, received_axis_results=None):
    """Join original owner/parent decisions to their own completion receipts."""
    db = workflow.store.db
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'runtime_actions', 'runtime_observations'} <= tables:
        return []
    slots = 'runtime_completion_slots' in tables
    join = ('LEFT JOIN runtime_completion_slots s ON s.run_id=o.run_id '
            'AND s.episode_id=o.episode_id AND s.sequence=o.unit_index' if slots else '')
    original = ('COALESCE(json_extract(o.observation,\'$.decision_index\'),s.original_decision_index)'
                if slots else "json_extract(o.observation,'$.decision_index')")
    credits = {}
    for row in db.execute('SELECT o.unit_index,' + original + ' AS decision_index,'
            "json_extract(o.observation,'$.step.marginal_credit') AS marginal_credit "
            'FROM runtime_observations o ' + join + ' WHERE o.run_id=? AND o.episode_id=? '
            'ORDER BY o.unit_index', (workflow.run_id, source.episode_id)):
        index, value = row['decision_index'], row['marginal_credit']
        if index is not None and index < before:
            credits.setdefault(index, []).append({'completion_index': row['unit_index'],
                'earned_credit': value if isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) else None})
    reports = 'runtime_report_attempts' in tables
    columns = (',p.form AS admitted_form,p.failure AS delivery_failure' if reports else
               ',NULL AS admitted_form,NULL AS delivery_failure')
    join = (' LEFT JOIN runtime_report_attempts p ON p.run_id=a.run_id '
            'AND p.parent_episode_id=a.episode_id AND p.decision_index=a.decision_index' if reports else '')
    actions = []
    references = set()
    for row in db.execute('SELECT a.decision_index,' + _action_sql() + ' AS action,'
            + _outcome_sql() + ' AS result' + columns
            + ' FROM runtime_actions a' + join
            + ' WHERE a.run_id=? AND a.episode_id=? AND a.decision_index<? '
            'AND a.result IS NOT NULL ORDER BY a.decision_index',
            (workflow.run_id, source.episode_id, before)):
        selection = {key: value for key, value in _json(row['action'], {}).items() if value is not None}
        for key in ('arguments', 'episode_assignment', 'recorded_section_counts'):
            selection[key] = {name: value for name, value in selection.get(key, {}).items() if value is not None}
        selection['selected_grading'] = [{key: value for key, value in item.items() if value is not None}
            for item in selection.get('selected_grading', [])]
        received = _json(row['result'], {})
        if (str(selection.get('tool', '')).startswith(('api.', 'public.')) and is_api_error_return(received)):
            outcome = deepcopy(received)
        elif isinstance(received, Mapping):
            outcome = {key: value for key, value in received.items() if value is not None}
            if isinstance(outcome.get('result'), Mapping):
                outcome['result'] = {key: value for key, value in outcome['result'].items() if value is not None}
        else:
            outcome = {'recorded_result': received}
        outcome = shared_outcome_view(outcome)
        delivery_failure = _json(row['delivery_failure'])
        if row['admitted_form'] is not None and delivery_failure is None:
            outcome['admitted_child_return'] = _json(row['admitted_form'])
            outcome.setdefault('status', 'Child return admitted')
        if delivery_failure is not None:
            outcome['report_delivery_failure'] = delivery_failure
        # Existing receiver-authorized native views may resolve exact returned
        # grant/sheet versions. Each axis adapter must match this action's refs;
        # an unrelated current sibling view is not its historical result.
        outcome['received_axis_results'] = {**state.get('received_axis_results', {}),
            **{key: state[key] for key in _VIEW_FIELDS if key in state},
            **(received_axis_results or {})}
        work, inputs = _selection(selection, outcome.get('aliases', {}))
        references.update(_references(inputs))
        references.update(_references(outcome))
        actions.append((row['decision_index'], selection, outcome, work, inputs))
    records = _meaning_records(workflow, source, state, references)
    display = WorkMeaningDisplay(records)
    result, grouped = [], {}
    binding = state.get('credit_binding', {})
    units = binding.get('kind') or binding.get('version') if isinstance(binding, Mapping) else None
    for index, selection, outcome, work, inputs in actions:
        api_error = (selection.get('kind') == 'tool'
            and str(selection.get('tool', '')).startswith(('api.', 'public.')) and is_api_error_return(outcome))
        complete_error = ({key: deepcopy(value) for key, value in outcome.items()
            if key != 'received_axis_results'} if api_error else None)
        body = outcome.get('result')
        shared_saved = (body.get('saved_grading_results') if isinstance(body, Mapping)
            and selection.get('tool') == 'shared.read_information' else None)
        native = ([] if shared_saved is not None or selection.get('tool') == 'shared.publish_information'
            else _adapter_results(selection, outcome, records))
        facts = {'status': outcome.get('status', 'Status not recorded')}
        if shared_saved is not None:
            facts['saved_results'] = deepcopy(shared_saved)
            facts['grading_delivery'] = body.get('grading_delivery')
            facts['received_material'] = deepcopy(body.get('evidence_refs', []))
        elif native:
            facts['saved_results'] = native
        elif body:
            facts['returned_result'] = _compact(body)
        if 'admitted_child_return' in outcome:
            # These are exact selected child fields. Any child-local credit in
            # them is labeled separately from this row's original parent gain.
            facts['admitted_child_values'] = {
                'value_owner': 'Returned child; separate from this original parent action’s earned credit',
                'values': deepcopy(_grading_report_values(outcome['admitted_child_return']))}
        for key in ('feedback', 'report_delivery_failure', 'child_completion',
                'error_code', 'errors', 'conflicts', 'notices'):
            if outcome.get(key) is not None:
                facts[key] = _compact(outcome[key])
        saved = outcome.get('changed_record_refs')
        if saved:
            facts['saved_changes'] = saved
        if complete_error is not None:
            facts = {'complete_returned_error': complete_error}
        observed = credits.get(index, [])
        mark = [receipt['earned_credit'] for receipt in observed]
        key = json.dumps([work, inputs, facts, mark], sort_keys=True, ensure_ascii=False)
        if key in grouped:
            entry = grouped[key]
            entry['original_decisions'].append(index)
            entry['credit_receipts'].extend({'original_decision': index, **item} for item in observed)
            continue
        entry = {'version': VERSION, 'work': work,
            'actual_inputs': display.project(inputs), 'recorded_outcome': display.project(facts),
            'credit_owner': source.path[-1][0], 'credit_units': units or 'This episode’s configured iterator units',
            'original_decisions': [index],
            'credit_receipts': [{'original_decision': index, **item} for item in observed],
            'credit_status': 'recorded' if observed else 'No original completion credit receipt'}
        if complete_error is not None:
            # Preserve diagnostics literally: source-name resolution and generic
            # body compaction must not rewrite or omit an API error message.
            entry['recorded_outcome'] = {'complete_returned_error': complete_error}
        grouped[key] = entry
        result.append(entry)
    return result


class WorkMeaningDisplay:
    """Resolve received names in place, never through an invented label index."""
    def __init__(self, records):
        self.records, self.active, self.cache = records, set(), {}

    def reference(self, reference):
        if reference is None:
            return 'Not supplied'
        if not isinstance(reference, str):
            return self.project(reference)
        if reference in self.cache:
            return self.cache[reference]
        record = self.records.get(reference)
        if reference in self.active:
            return 'Same received subject (argument reference: ' + reference + ')'
        if record is None:
            return 'Meaning not delivered (argument reference: ' + reference + ')'
        self.active.add(reference)
        try:
            name = record.get('label') or record.get('title') or record.get('name') or record.get('uri')
            kind = record.get('record_type')
            if not name and kind == 'hypothesis':
                name = '; '.join(self.reference(ref) for ref in record.get('subject_refs', []))
                name += ' — ' + str(record.get('predicate', 'proposed function')).replace('_', ' ')
                name += ': ' + self.text(self.project(record.get('value')))
            elif not name and kind == 'assessment':
                name = 'Source finding for ' + self.reference(record.get('hypothesis_ref'))
                name += '; reported result: ' + self.reference(record.get('observation_ref'))
            elif not name and kind == 'observation':
                name = 'Reported ' + str(record.get('kind', 'source result')).replace('_', ' ')
                subjects = record.get('source_subject_refs') or record.get('subject_refs', [])
                if subjects:
                    name += ' for ' + '; '.join(self.reference(ref) for ref in subjects)
                if record.get('measurements'):
                    name += ': ' + self.text(self.project(record['measurements']))
            elif not name and kind in {'input', 'feature', 'product', 'read_subject'}:
                name = 'Supplied ' + str(record.get('molecule') or kind).replace('_', ' ')
                if record.get('length') is not None:
                    name += ' (length ' + str(record['length']) + ')'
            elif not name:
                name = record.get('provider') or str(kind or 'Received record').replace('_', ' ')
            result = str(name) + ' (argument reference: ' + reference + ')'
            self.cache[reference] = result
            return result
        finally:
            self.active.remove(reference)

    def project(self, value):
        if isinstance(value, Mapping):
            if isinstance(value.get('type'), str) and value['type'] in {'reference', 'term_ref'} and isinstance(value.get('ref'), str):
                return self.reference(value['ref'])
            result = {}
            for key, child in value.items():
                if key == 'ref' or key.endswith('_ref') or key in {'target_model', 'reference_model'}:
                    result[key] = self.reference(child) if child is None or isinstance(child, str) else self.project(child)
                elif key.endswith('_refs') and isinstance(child, (tuple, list)):
                    result[key] = [self.reference(ref) for ref in child]
                else:
                    result[key] = self.project(child)
            return result
        if isinstance(value, (tuple, list)):
            return [self.project(child) for child in value]
        if isinstance(value, str) and value in self.records:
            return self.reference(value)
        return value

    @staticmethod
    def text(value):
        if isinstance(value, Mapping):
            return '; '.join(str(key).replace('_', ' ') + ': ' + WorkMeaningDisplay.text(child)
                for key, child in value.items())
        if isinstance(value, (tuple, list)):
            return '; '.join(WorkMeaningDisplay.text(child) for child in value) or 'None recorded'
        if value is None:
            return 'Not supplied'
        return str(value)


def render_completed_action_reports(reports):
    title = 'Completed work, actual results and recorded earned credit'
    if not reports:
        return title + '\n\nNo completed action receipt is available yet.'
    meaning = (
        "Original earned credit is this episode's recorded iterator progress, in its own units, for the listed action. "
        "Scientific quantities and any child-local credit retain their original meanings in the result column. "
        "Equal work and outcomes may share a row; every original decision and completion receipt remains listed.")
    def cell(value):
        text = (json.dumps(value['complete_returned_error'], ensure_ascii=False, indent=2)
            if isinstance(value, Mapping) and 'complete_returned_error' in value
            else WorkMeaningDisplay.text(value))
        return text.replace('|', '\\|').replace('\r', '').replace('\n', '<br>')
    rows = ['| Work performed | Actual inputs | Recorded result or failure | Original earned credit | Original decisions |',
            '| --- | --- | --- | --- | --- |']
    for entry in reports:
        gains = {}
        for receipt in entry['credit_receipts']:
            gains.setdefault(receipt['original_decision'], []).append(receipt['earned_credit'])
        patterns = [tuple(gains.get(index, ())) for index in entry['original_decisions']]
        def recorded(values):
            return ', '.join(str(value) if value is not None else 'Unknown original earned credit'
                for value in values) or entry['credit_status']
        if patterns and all(pattern == patterns[0] for pattern in patterns):
            credit = recorded(patterns[0])
            if len(patterns[0]) > 1:
                credit = 'Original completion gains: ' + credit
            if len(patterns) > 1 and patterns[0]:
                credit += ' per action (' + str(len(patterns)) + ' actions)'
        else:
            credit = '; '.join('decision ' + str(index) + ': ' + recorded(gains.get(index, ()))
                for index in entry['original_decisions'])
        rows.append('| ' + ' | '.join(cell(value) for value in (entry['work'],
            entry['actual_inputs'], entry['recorded_outcome'], credit,
            ', '.join(str(index) for index in entry['original_decisions']))) + ' |')
    return title + '\n\n' + meaning + '\n\n' + '\n'.join(rows)


__all__ = ['VERSION', 'completed_action_reports', 'render_completed_action_reports',
    'requested_action_history']
