"""A106's recurring source investigation and parent prompt renderer.

The renderer presents only supplied state. It does not acquire a source,
interpret an experiment, execute a calculation, or award credit.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from gene_annotation_episode.episodic_workflow.root.a106.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episodic_workflow.root.a106.schema_information_text import render_schema_information
from gene_annotation_episode.episodic_workflow.root.a106.scientific_process_prompt import text_instructions
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_prompt import parent_tasks
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_prompt import PERTURBATION_TASK
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_task_families import selected_literature_task_sections
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_prompt_binding import render_child_results, render_covariance, render_source_result, separate_child_results, separate_covariance_rows, support_refs


VERSION = 'literature_experimental_task_v1'
SAVED_NUMERICAL_RETURN_TASK = (
    'When requesting saved numerical components, select the declared recorded '
    'return source and its needed components. Saved cells come from the host; '
    'keep interpretations in separate fields and preserve their source meanings.')
FACT_CONTRACT_TASK = ('For a declared A106 child return, request episode.return_contract '
    'with the child role and recorded-fact source. Select its exact saved type with '
    'a top-level {"$ref":"episode-fact:<source>"} field. The host supplies the saved '
    'value; write interpretations in separate closed fields.')
_PRIVATE = frozenset(('private_history', 'private_reasoning', 'provider_result',
    'implementation_sha256', 'calculation_implementation', 'report_contract_declaration'))

_ORIGINAL_TRACKING = frozenset({
    "run_id", "episode_id", "goal_id", "parent_goal_id", "problem_ref", "record_type",
    "sha256", "digest", "content_sha256", "entry_sha256", "section_sha256",
    "initial_selection_sha256", "implementation_sha256", "operation_ref", "operation_key",
    "base_revision", "revision", "removed_fields", "created_at", "updated_at",
    "recorded_at", "parser_version", "parse_key", "controller_binding", "credit_binding",
    "parent_history", "parent_yields", "private_history", "history", "private_reasoning",
    "own_completed_action_history", "local_return_history", "restored_episode_history",
    "restored_public_exchanges", "restored_pending_decision_index", "diagnostics",
    "scientific_child_credit_binding", "scientific_process", "scoring_rubric",
    "axis_judgment_contract", "calculation_implementation",
    "curve_keys", "measurement_keys", "primitive_measurement_keys",
    "report_contract_declaration", "contract_information_profile",
    "requested_controlled_response_component_keys", "literature_controlled_response_return_bindings",
    "requested_gel_component_keys", "literature_gel_return_bindings", "literature_gel_return_records",
    "literature_rate_source_display", "literature_rate_source_domain_display",
    "literature_rate_source_meaning_display", "literature_endpoint_receipt_bindings",
    "literature_summary_precision_receipt_bindings", "literature_measurement_comparison_receipt_bindings", "literature_concentration_window_receipt_bindings",
})
# Retain the current explicit private/provider exclusions as well.
_TRACKING = _ORIGINAL_TRACKING | _PRIVATE


def is_literature_experimental_context(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    return isinstance(marker, Mapping) and marker.get('version') == VERSION


def _safe(value):
    if isinstance(value, Mapping):
        return {key: _safe(child) for key, child in value.items()
                if key not in _TRACKING and not key.startswith("private_")
                and not key.endswith("_sha256")
                and not (key == "accession" and isinstance(child, str)
                    and child.startswith(("transport_curve_", "transport_quantity_", "native_rate_", "amount_")))}
    if isinstance(value, (list, tuple)):
        return [_safe(child) for child in value]
    return value


def _value(value):
    if value is None:
        return 'unknown'
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(_safe(value), ensure_ascii=False, sort_keys=True, indent=2,
            allow_nan=False, default=str)
    return str(value)


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return 'None supplied.'
    def cell(value):
        return _value(value).replace('|', '\\|').replace('\r', '').replace('\n', '<br>')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
        '| ' + ' | '.join('---' for _ in headers) + ' |',
        *('| ' + ' | '.join(cell(value) for value in row) + ' |' for row in rows)])


def _section(parts, title, content):
    if content is not None and content != '' and content != [] and content != {}:
        parts.extend(('', title, '', content if isinstance(content, str) else _value(content)))


def _pick(value, names):
    return {name: value[name] for name in names if name in value} if isinstance(value, Mapping) else {}


def _references(value):
    if isinstance(value, Mapping):
        for name, child in value.items():
            if (name in ('id', 'ref') or name.endswith('_ref')) and isinstance(child, str):
                yield child
            elif name.endswith('_refs') and isinstance(child, (list, tuple)):
                yield from (ref for ref in child if isinstance(ref, str))
            yield from _references(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _references(child)


def _task(state, instructions):
    marker = state['literature_experimental_work']
    parent = marker.get('aspect') == 'reference_evidence_parent'
    tasks = parent_tasks() if parent else (PERTURBATION_TASK,)
    normalized = text_instructions(instructions)
    parts = ['TASK', '', *[part for task in tasks for part in (task, '')]]
    additional = normalized
    for task in tasks:
        additional = additional.replace(task, '')
    if additional.strip():
        parts.append(additional.strip())
    if SAVED_NUMERICAL_RETURN_TASK not in normalized:
        parts.extend(('', SAVED_NUMERICAL_RETURN_TASK))
    for source, task in selected_literature_task_sections(state):
        if task not in normalized and task not in tasks:
            _section(parts, 'Selected A106 scientific instructions: ' + source, task)
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(('', FACT_CONTRACT_TASK))
    goal = state.get('goal', {})
    _section(parts, 'Assigned source-evidence question' if parent else 'Assigned experimental question',
        _pick(goal, ('objective', 'task_context', 'result_contract')) if isinstance(goal, Mapping) else goal)
    _section(parts, 'Assigned scope', state.get('scope', {}))
    _section(parts, 'Parent assignment and selected source operands', state.get('literature_assignment', {}))
    descriptor = state.get('reference_evidence_parent', {}) if parent else {}
    _section(parts, 'Caller-selected source assignment', descriptor.get('source_refs'))
    _section(parts, 'Representations available for selected sources',
        state.get('literature_source_custody') or descriptor.get('source_custody'))
    working = state.get('working_state', {})
    _section(parts, 'Supplied material and scoped access', _pick(working,
        ('subjects', 'materials', 'material_links', 'target_binding',
         'read_library_access', 'supplied_context_source_refs')))
    tools = state.get('tools', ())
    if tools:
        _section(parts, 'Available selected operations', _table(('Operation', 'Meaning'),
            ((row['name'], row.get('description', '')) for row in tools)))
        for tool in tools:
            if 'input_schema' in tool and not profile:
                _section(parts, 'Operands for ' + tool['name'], tool['input_schema'])
    _section(parts, 'Permitted narrower investigations', state.get('child_options'))
    _section(parts, 'Information requested by the parent', state.get('requested_report_purpose'))
    form = state.get('requested_form')
    if isinstance(form, Mapping):
        _section(parts, "Parent's typed return meanings",
            render_schema_information(form, title='Parent requested return') if profile else form)
    _section(parts, 'Return interpretation timing', state.get('report_lifecycle'))
    return '\n'.join(parts)


def _show_result(parts, value, title, records):
    content = value.get('result') if isinstance(value, Mapping) else None
    if render_source_result(parts, value, content, title, values=_value,
            records=records, section=_section, table=_table, pick=_pick):
        return
    if isinstance(content, Mapping) and isinstance(content.get('cells'), Mapping):
        render_covariance(parts, ({'component': name, **cell}
            for name, cell in content['cells'].items() if isinstance(cell, Mapping)), records,
            section=_section, table=_table)
    _section(parts, title, value)


def _steering(state, lookup_results):
    parts = ['STEERING', '',
        'For text anchors, use the received source_ref, artifact_ref, and '
        'zero-based half-open UTF-8 byte range. The host retains the exact '
        'quotation within the selected action.']
    _section(parts, 'Complete the original child return', state.get('pending_child_delivery'))
    _section(parts, 'Own action yields', state.get('action_yields'))
    _section(parts, 'Current continuation expectation', state.get('controller'))
    records = state.get('literature_received_fact_display', {}).get('records')
    if not isinstance(records, Mapping):
        records = {row['id']: row for rows in state.get('working_state', {}).values()
            if isinstance(rows, (list, tuple)) for row in rows
            if isinstance(row, Mapping) and isinstance(row.get('id'), str)}
    selected = {}
    pending = list(dict.fromkeys(_references((state.get('literature_assignment'),
        state.get('last_local_outcome'), state.get('child_reports'),
        state.get('current_report_update'), lookup_results))))
    covariance_support = set(support_refs((state.get('last_local_outcome'),
        state.get('child_reports'), state.get('current_report_update'), lookup_results), records))
    for reference in pending:
        if reference in selected or reference not in records:
            continue
        row = records[reference]
        if reference in covariance_support:
            row = {**row, 'anchor': None, 'visual_anchor': None}
        selected[reference] = row
        pending.extend(ref for ref in _references(row) if ref not in selected)
    records = selected
    _section(parts, 'Received scientific records', list(records.values()))
    _section(parts, 'Completed work and recorded earned credit', state.get('literature_completed_work'))
    _section(parts, 'Current saved subscoring and evidence scoring results',
        state.get('literature_current_scoring_sheets'))
    _section(parts, 'Previously examined inputs for your selected source',
        state.get('literature_examined_source_inputs'))
    if state.get('last_local_outcome') is not None:
        _show_result(parts, state['last_local_outcome'], 'Last selected action outcome', records)
    _section(parts, 'Complete returned feedback', state.get('feedback'))
    reports = [*state.get('child_reports', ())]
    if state.get('current_report_update'):
        reports.append(state['current_report_update'])
    ordinary, results = separate_child_results(reports)
    covariance = []
    compact = []
    for report in ordinary:
        if not isinstance(report, Mapping):
            compact.append(report)
            continue
        remainder = {}
        for name, value in report.items():
            remainder[name], rows = separate_covariance_rows(name, value)
            covariance.extend(rows)
        compact.append(remainder)
    _section(parts, 'Admitted requested child returns', compact)
    render_child_results(parts, results, section=_section, table=_table,
        values=_value, records=records)
    render_covariance(parts, covariance, records, section=_section, table=_table)
    _section(parts, 'Shared investigation updates', state.get('shared_information_context'))
    _section(parts, 'Pending assigned work', state.get('pending_work'))
    _section(parts, 'Choosing work or waiting for a child', state.get('waiting_support'))
    for result in lookup_results:
        _show_result(parts, result, 'Requested information; continue this decision', records)
    return '\n'.join(parts)


def render_literature_experimental_prompt(state, instructions, *, lookup_results=()):
    """Render A106 task and received steering through private A106 bindings."""
    if not is_literature_experimental_context(state):
        raise ValueError('literature_experimental_context_required')
    if state['literature_experimental_work'].get('aspect') == 'reference_evidence_parent':
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_reference_parent_prompt import render_reference_evidence_parent_prompt
        return render_reference_evidence_parent_prompt(state, instructions,
            lookup_results=lookup_results)
    return _task(state, instructions) + '\n\n' + _steering(state, lookup_results)


__all__ = ['VERSION', 'SAVED_NUMERICAL_RETURN_TASK',
    'is_literature_experimental_context', 'render_literature_experimental_prompt']
