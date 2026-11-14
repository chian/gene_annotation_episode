"""A110's private source-evidence parent prompt."""
from __future__ import annotations
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.a110.composition_information import CONTRACT_INFORMATION_PROFILE, is_contract_information
from gene_annotation_episode.episodic_workflow.root.a110.schema_information_text import render_schema_information
from gene_annotation_episode.episodic_workflow.root.a110.library.scientific_decision_presentation import text_instructions
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_instructions import A110_SOURCE_LEAD
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_source_presentation import CONTRACT_INFORMATION_TASK, FACT_CONTRACT_TASK, _pick, _section, _steering, _values
VERSION = 'reference_evidence_parent_v1'

def _descriptor(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    descriptor = state.get('reference_evidence_parent') if isinstance(state, Mapping) else None
    if not isinstance(marker, Mapping) or marker.get('version') != 'literature_experimental_task_v1' or marker.get('aspect') != 'reference_evidence_parent' or (not isinstance(descriptor, Mapping)) or (descriptor.get('version') != VERSION):
        raise ValueError('a110_reference_evidence_parent_context_required')
    references = descriptor.get('source_refs')
    if not isinstance(references, (tuple, list)) or any((not isinstance(ref, str) or not ref for ref in references)) or len(set(references)) != len(references):
        raise ValueError('a110_reference_evidence_parent_source_assignment_required')
    return descriptor

def render_reference_evidence_parent_prompt(state, instructions, *, lookup_results=()):
    descriptor = _descriptor(state)
    normalized = text_instructions(instructions)
    parts = ['TASK', '', A110_SOURCE_LEAD]
    if normalized and normalized != A110_SOURCE_LEAD:
        parts.extend(['', normalized])
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(['', CONTRACT_INFORMATION_TASK, '', FACT_CONTRACT_TASK])
    goal = state.get('goal', {})
    _section(parts, 'Assigned A110 source-evidence question', _pick(goal, ('objective', 'task_context') if profile else ('objective', 'task_context', 'result_contract')) if isinstance(goal, Mapping) else goal)
    if profile and isinstance(goal, Mapping) and (goal.get('result_contract') is not None):
        _section(parts, 'Assigned result contract', render_schema_information(goal['result_contract'], title='Assigned result contract'))
    _section(parts, 'Scientific scope', state.get('scope'))
    if descriptor['source_refs']:
        _section(parts, 'Caller-selected source assignment', {'source_refs': descriptor['source_refs']})
    else:
        _section(parts, 'A110 source discovery', 'Find source-bound chemical equations, measured ratios, model predictions, resource observations and their context. Preserve the actual source subject and missing inputs.')
    references = set(descriptor['source_refs'])
    _section(parts, 'Available representations of assigned sources', [_pick(row, ('source_ref', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'version')) for row in descriptor.get('source_custody', ()) if isinstance(row, Mapping) and row.get('source_ref') in references])
    _section(parts, 'Supplied material and scoped access', _pick(state.get('working_state', {}), ('subjects', 'materials', 'material_links', 'target_binding', 'read_library_access')))
    _section(parts, 'Original caller question and context', descriptor.get('supplied_context'))
    _section(parts, 'Selected constraints', _pick(state, ('constraints', 'selected_constraints')))
    _section(parts, 'Available operations', state.get('tools'))
    _section(parts, 'Permitted narrower investigations', state.get('child_options'))
    _section(parts, 'Requested typed return', state.get('requested_form'))
    steering_fields = ('component_axis_source_access', 'component_axis_scoring_sheets', 'action_yields', 'controller', 'working_state', 'last_local_outcome', 'literature_completed_work', 'literature_current_scoring_sheets', 'completed_action_reports', 'feedback', 'current_report_update', 'requested_form', 'child_reports', 'pending_work', 'waiting_support', 'current_report_basis_refs', 'shared_information_context')
    task = '\n'.join(parts)
    contracts = [row for row in lookup_results if is_contract_information(row)]
    if contracts:
        task += '\n\nRequested operation contracts\n' + _values(contracts)
    return task + '\n\n' + _steering(_pick(state, steering_fields), [row for row in lookup_results if row not in contracts])
