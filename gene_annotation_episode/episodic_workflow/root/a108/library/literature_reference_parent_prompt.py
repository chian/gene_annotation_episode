"""A108's own source-evidence parent task and factual steering renderer."""
from __future__ import annotations
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.a108.composition_information import CONTRACT_INFORMATION_PROFILE, is_contract_information
from gene_annotation_episode.episodic_workflow.root.a108.schema_information_text import render_schema_information
from gene_annotation_episode.episodic_workflow.root.a108.library.sample_context_evidence_prompt import text_instructions
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_prompt import A108_CONTEXT_TASK, A108_PARENT_TASK
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_parent_prompt import SOURCE_DISCOVERY
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_experimental_prompt import CONTRACT_INFORMATION_TASK, SAVED_NUMERICAL_RETURN_TASK, _pick, _requested_contract_task, _section, _selected_sections, _steering, _values
VERSION = 'reference_evidence_parent_v1'

def _descriptor(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    descriptor = state.get('reference_evidence_parent') if isinstance(state, Mapping) else None
    if not isinstance(marker, Mapping) or marker.get('version') != 'literature_experimental_task_v1' or marker.get('evidence_axis') != 'A108' or (marker.get('aspect') != 'reference_evidence_parent') or (not isinstance(descriptor, Mapping)) or (descriptor.get('version') != VERSION):
        raise ValueError('a108_reference_evidence_parent_context_required')
    references = descriptor.get('source_refs')
    if not isinstance(references, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in references)) or len(set(references)) != len(references):
        raise ValueError('a108_reference_evidence_parent_source_assignment_required')
    return descriptor

def _task(state, instructions, descriptor, *, selected_sections=None):
    normalized = text_instructions(instructions)
    parts = ['TASK', '', A108_PARENT_TASK, '', A108_CONTEXT_TASK, '', SAVED_NUMERICAL_RETURN_TASK]
    for source, task in _selected_sections(state) if selected_sections is None else selected_sections:
        if task not in normalized:
            _section(parts, 'Selected A108 instructions: ' + source, task)
    additional = normalized.replace(A108_PARENT_TASK, '').replace(A108_CONTEXT_TASK, '').replace(SAVED_NUMERICAL_RETURN_TASK, '').strip()
    if additional:
        parts.extend(['', additional])
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(['', CONTRACT_INFORMATION_TASK])
    goal = state.get('goal', {})
    _section(parts, 'Assigned source-evidence question', _pick(goal, ('objective', 'task_context') if profile else ('objective', 'task_context', 'result_contract')) if isinstance(goal, Mapping) else goal)
    if profile and isinstance(goal, Mapping) and (goal.get('result_contract') is not None) and (goal['result_contract'] != state.get('requested_form')):
        _section(parts, 'Assigned result contract', render_schema_information(goal['result_contract'], title='Assigned result contract'))
    _section(parts, 'Assigned scientific scope', state.get('scope'))
    if descriptor['source_refs']:
        _section(parts, 'Caller-selected source assignment', {'source_refs': descriptor['source_refs']})
    else:
        _section(parts, 'Organism-context source discovery', SOURCE_DISCOVERY)
    references = set(descriptor['source_refs'])
    custody = [_pick(row, ('source_ref', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'version')) for row in descriptor.get('source_custody', ()) if isinstance(row, Mapping) and row.get('source_ref') in references]
    _section(parts, 'Available representations of assigned sources', custody)
    working = state.get('working_state', {})
    _section(parts, 'Supplied material and scoped access', _pick(working, ('subjects', 'materials', 'material_links', 'target_binding', 'read_library_access', 'supplied_context_source_refs')))
    _section(parts, 'Original caller-provided biological question and context', descriptor.get('supplied_context'))
    _section(parts, 'Selected constraints', _pick(state, ('constraints', 'selected_constraints')))
    _section(parts, 'Available selected operations', state.get('tools'))
    _section(parts, 'Permitted narrower investigations', state.get('child_options'))
    _section(parts, 'Requested return', state.get('requested_form'))
    return '\n'.join(parts)

def render_reference_evidence_parent_prompt(state, instructions, *, lookup_results=()):
    descriptor = _descriptor(state)
    sections = tuple(_selected_sections(state, lookup_results))
    steering_fields = ('action_yields', 'controller', 'working_state', 'last_local_outcome', 'literature_completed_work', 'literature_current_scoring_sheets', 'completed_action_reports', 'feedback', 'current_report_update', 'requested_form', 'child_reports', 'pending_work', 'waiting_support', 'current_report_basis_refs', 'shared_information_context')
    steering_state = _pick(state, steering_fields)
    task = _task(state, instructions, descriptor, selected_sections=sections)
    if state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE:
        return _requested_contract_task(task, lookup_results) + '\n\n' + _steering(steering_state, [row for row in lookup_results if not is_contract_information(row)])
    return task + '\n\n' + _steering(steering_state, lookup_results)
__all__ = ['VERSION', 'render_reference_evidence_parent_prompt']
