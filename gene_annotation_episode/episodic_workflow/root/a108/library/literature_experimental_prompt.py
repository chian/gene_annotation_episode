"""A108's own source-context episode task and factual steering renderer."""
from __future__ import annotations
from collections.abc import Mapping
import json
from gene_annotation_episode.episodic_workflow.root.a108.composition_information import CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_PROFILE, is_contract_information
from gene_annotation_episode.episodic_workflow.root.a108.schema_information_text import render_schema_information
from gene_annotation_episode.episodic_workflow.root.a108.library.sample_context_evidence_prompt import _band, _schema, text_instructions
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_prompt import A108_CONTEXT_TASK, A108_READING_TASK
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_task_families import _ROWS
VERSION = 'literature_experimental_task_v1'
SAVED_NUMERICAL_RETURN_TASK = "For a saved numerical component, select its declared episode-fact source in a top-level return field. The host fills that field from saved cells. Give your interpretation in a separate field and preserve the parent's requested meanings."
CONTRACT_INFORMATION_TASK = "Use request_context, composition_information, or episode.operation_contract when you need an operation's full argument contract. Select the actual operation name and its complete typed inputs. A contract lookup creates no scientific observation."
FACT_CONTRACT_TASK = 'For a declared A108 child return, request episode.return_contract with the child role and recorded-fact source. Select its exact saved type with a top-level {"$ref":"episode-fact:<source>"} field. The host supplies the saved value; write interpretations in separate closed fields.'

def is_literature_experimental_context(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    return isinstance(marker, Mapping) and marker.get('version') == VERSION and (marker.get('evidence_axis') == 'A108')

_TRACKING = frozenset({'run_id', 'episode_id', 'goal_id', 'parent_goal_id', 'problem_ref', 'record_type', 'sha256', 'digest', 'content_sha256', 'entry_sha256', 'section_sha256', 'initial_selection_sha256', 'implementation_sha256', 'operation_ref', 'operation_key', 'base_revision', 'revision', 'removed_fields', 'created_at', 'updated_at', 'recorded_at', 'parser_version', 'parse_key', 'controller_binding', 'credit_binding', 'parent_history', 'parent_yields', 'private_history', 'history', 'private_reasoning', 'own_completed_action_history', 'local_return_history', 'restored_episode_history', 'restored_public_exchanges', 'restored_pending_decision_index', 'diagnostics', 'scientific_child_credit_binding', 'sample_context_evidence', 'scoring_rubric', 'axis_judgment_contract', 'calculation_implementation', 'curve_keys', 'measurement_keys', 'primitive_measurement_keys', 'report_contract_declaration', 'contract_information_profile', 'requested_controlled_response_component_keys', 'literature_controlled_response_return_bindings', 'requested_gel_component_keys', 'literature_gel_return_bindings', 'literature_gel_return_records', 'literature_rate_source_display', 'literature_rate_source_domain_display', 'literature_rate_source_meaning_display', 'literature_endpoint_receipt_bindings', 'literature_summary_precision_receipt_bindings', 'literature_measurement_comparison_receipt_bindings', 'literature_concentration_window_receipt_bindings'})
_PRIVATE = {'private_history', 'private_reasoning', 'history', 'parent_history', 'own_completed_action_history', 'restored_episode_history', 'body', 'content', 'bytes', 'base64', 'stdout', 'stderr'}

def _safe(value):
    if isinstance(value, Mapping):
        return {key: _safe(child) for key, child in value.items() if key not in _TRACKING and (not key.startswith('private_')) and (not key.endswith('_sha256')) and (not (key == 'accession' and isinstance(child, str) and child.startswith(('transport_curve_', 'transport_quantity_', 'native_rate_', 'amount_')))) and (key not in _PRIVATE)}
    if isinstance(value, (list, tuple)):
        return [_safe(child) for child in value]
    return value

def _values(value):
    return json.dumps(_safe(value), ensure_ascii=False, sort_keys=True, indent=2, default=str)

def _pick(value, fields):
    return {key: value[key] for key in fields if isinstance(value, Mapping) and key in value}

def _section(parts, title, content):
    if content not in (None, '', [], {}, ()):
        parts.extend(['', title, _values(content) if not isinstance(content, str) else content])

def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return ''
    return '\n'.join([' | '.join(map(str, headers)), ' | '.join(('---' for _ in headers)), *(' | '.join(map(str, row)) for row in rows)])

def _form_sources(value):
    if isinstance(value, Mapping):
        source = value.get('x-source')
        if isinstance(source, str):
            yield source
        for child in value.values():
            yield from _form_sources(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _form_sources(child)

def _selected_sections(state, lookup_results=()):
    sources = []
    assignment = state.get('literature_assignment', {})
    if isinstance(assignment, Mapping):
        sources.extend((source for source, row in _ROWS.items() if row[4] in assignment))
    sources.extend(_form_sources(state.get('requested_form')))
    goal = state.get('goal', {})
    if isinstance(goal, Mapping):
        sources.extend(_form_sources(goal.get('result_contract')))
    owned = state.get('literature_owned_population_sources')
    if isinstance(owned, (tuple, list)):
        sources.extend((source for source in owned if isinstance(source, str)))
    sources.extend(_form_sources(state.get('last_local_outcome')))
    sources.extend(_form_sources(lookup_results))
    seen = set()
    for source in sources:
        if isinstance(source, str) and source in _ROWS and (source not in seen):
            seen.add(source)
            yield (source, _ROWS[source][1])

def _requested_contract_task(task, lookup_results):
    rows = [row for row in lookup_results if is_contract_information(row)]
    return task + ('\n\nRequested operation contracts\n' + _values(rows) if rows else '')

def _task(state, instructions, *, selected_sections=None):
    normalized = text_instructions(instructions)
    parts = ['TASK', '', A108_CONTEXT_TASK, '', A108_READING_TASK]
    additional = normalized.replace(A108_CONTEXT_TASK, '').replace(A108_READING_TASK, '').strip()
    if additional:
        parts.extend(['', additional])
    if SAVED_NUMERICAL_RETURN_TASK not in normalized:
        parts.extend(['', SAVED_NUMERICAL_RETURN_TASK])
    for source, task in _selected_sections(state) if selected_sections is None else selected_sections:
        if task not in normalized:
            _section(parts, 'Selected A108 instructions: ' + source, task)
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(['', CONTRACT_INFORMATION_TASK, '', FACT_CONTRACT_TASK])
    goal = state.get('goal', {})
    _section(parts, 'Assigned organism-context question', _pick(goal, ('objective', 'task_context') if profile else ('objective', 'task_context', 'result_contract')) if isinstance(goal, Mapping) else goal)
    if profile and isinstance(goal, Mapping) and (goal.get('result_contract') is not None) and (goal['result_contract'] != state.get('requested_form')):
        _section(parts, 'Assigned result contract', render_schema_information(goal['result_contract'], title='Assigned result contract'))
    _section(parts, 'Assigned scope', state.get('scope'))
    _section(parts, 'Parent assignment and selected source operands', state.get('literature_assignment'))
    _section(parts, 'Representations available for selected sources', state.get('literature_source_custody'))
    working = state.get('working_state', {})
    _section(parts, 'Supplied material and scoped access', _pick(working, ('subjects', 'materials', 'material_links', 'target_binding', 'read_library_access', 'supplied_context_source_refs')))
    tools = state.get('tools', ())
    _section(parts, 'Available selected operations', _table(('Operation', 'Meaning'), ((row['name'], row.get('description', '')) for row in tools)))
    for tool in tools:
        if 'input_schema' in tool and (not (profile and tool.get('argument_transport') == CONTRACT_ARGUMENT_TRANSPORT)):
            _section(parts, 'Operands for ' + tool['name'], _schema(tool['input_schema'], 'arguments'))
    _section(parts, 'Permitted narrower investigations', state.get('child_options'))
    _section(parts, 'Information requested by the parent', state.get('requested_report_purpose'))
    form = state.get('requested_form')
    if isinstance(form, Mapping):
        _section(parts, "Parent's typed return meanings", render_schema_information(form, title='Parent requested return') if profile else _schema(form, 'return'))
    _section(parts, 'Return interpretation timing', state.get('report_lifecycle'))
    return '\n'.join(parts)

def _steering(state, lookup_results):
    parts = ['STEERING', '', 'For text anchors, select the received source_ref, artifact_ref and zero-based half-open UTF-8 byte range. The host retrieves the exact quotation in the original action. Preserve the source subject and original contextual observation identity.']
    _section(parts, 'Complete the original child return', state.get('pending_child_delivery'))
    yields = state.get('action_yields', {})
    _section(parts, 'Own action yields', yields)
    controller = state.get('controller', {})
    if controller.get('estimate'):
        estimate = controller['estimate']
        _section(parts, 'Current continuation expectation', {'completed_actions': estimate.get('turns'), 'expected_next_gain': _band(estimate.get('expected_next_gain')), 'continuation_cost': controller.get('decision', {}).get('continuation_cost')})
    _section(parts, 'Completed work and recorded earned credit', state.get('literature_completed_work'))
    _section(parts, 'Current saved A108 scoring sheets', state.get('literature_current_scoring_sheets'))
    _section(parts, 'Received source findings and corrections', _pick(state.get('working_state', {}), ('received_records', 'received_revision_status')))
    _section(parts, 'Previously examined source inputs', state.get('literature_examined_source_inputs'))
    _section(parts, 'Last selected action outcome', state.get('last_local_outcome'))
    _section(parts, 'Complete returned feedback', state.get('feedback'))
    _section(parts, 'Current requested interpretation', state.get('current_report_update'))
    _section(parts, 'Received child returns', state.get('child_reports'))
    _section(parts, 'Investigation updates', state.get('shared_information_context'))
    _section(parts, 'Pending assigned work', state.get('pending_work'))
    _section(parts, 'Received waiting information', state.get('waiting_support'))
    for result in lookup_results:
        _section(parts, 'Requested information; continue this decision', result)
    return '\n'.join(parts)

def render_literature_experimental_prompt(state, instructions, *, lookup_results=()):
    if not is_literature_experimental_context(state):
        raise ValueError('a108_literature_experimental_context_required')
    if state['literature_experimental_work'].get('aspect') == 'reference_evidence_parent':
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_reference_parent_prompt import render_reference_evidence_parent_prompt
        return render_reference_evidence_parent_prompt(state, instructions, lookup_results=lookup_results)
    sections = tuple(_selected_sections(state, lookup_results))
    task = _task(state, instructions, selected_sections=sections)
    if state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE:
        return _requested_contract_task(task, lookup_results) + '\n\n' + _steering(state, [row for row in lookup_results if not is_contract_information(row)])
    return task + '\n\n' + _steering(state, lookup_results)
