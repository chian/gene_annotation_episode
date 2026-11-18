"""This A107 source episode owns its complete original task reading presentation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.literature_source_presentation import COMPONENT_READING_TASK, FACT_CONTRACT_TASK, Mapping, SOURCE_AVAILABILITY, SOURCE_SCOPE, VERSION, _section, _selected_family, _selected_tools, lead, text_instructions

def render_literature_experimental_prompt(state, instructions, *, lookup_results=()):
    """Render A107's own assignment and selected evidence without axis dispatch."""
    marker = state.get('literature_experimental_work', {})
    if not isinstance(marker, Mapping) or marker.get('version') != VERSION:
        raise ValueError('literature_experimental_context_required')
    family = _selected_family(state)
    parts = ['TASK', '', lead(family or 'A107_source'), '', SOURCE_AVAILABILITY, '', SOURCE_SCOPE, '', COMPONENT_READING_TASK]
    instruction_text = text_instructions(instructions).strip()
    if instruction_text:
        parts.extend(('', instruction_text))
    if state.get('contract_information_profile') == 'operation_contract_information_v1':
        parts.extend(('', FACT_CONTRACT_TASK))
    _section(parts, 'Assigned question', state.get('goal'))
    _section(parts, 'Assigned scope', state.get('scope'))
    _section(parts, 'Parent assignment and selected source operands', state.get('literature_assignment'))
    _section(parts, 'Assigned source parent', state.get('reference_evidence_parent'))
    _section(parts, 'Representations available for selected sources', state.get('literature_source_custody'))
    _section(parts, 'Supplied material and scoped access', state.get('working_state'))
    _section(parts, 'Available selected operations', _selected_tools(state))
    _section(parts, 'Permitted narrower investigations', state.get('child_options'))
    _section(parts, 'Information requested by the parent', state.get('requested_report_purpose'))
    _section(parts, "Parent's typed return meanings", state.get('requested_form'))
    _section(parts, 'Return interpretation timing', state.get('report_lifecycle'))
    steering = ['STEERING', '', 'Select the received source_ref, artifact_ref and zero-based half-open UTF-8 byte range for text witnesses. Preserve the exact observed subject, source meaning and unresolved target correspondence.']
    _section(steering, 'Recorded source inspections and access', state.get('component_axis_source_access'))
    _section(steering, 'Own action yields', state.get('action_yields'))
    _section(steering, 'Current continuation expectation', state.get('controller'))
    _section(steering, 'Pending child delivery', state.get('pending_child_delivery'))
    _section(steering, 'Current findings', state.get('literature_current_results'))
    _section(steering, 'Received child reports', state.get('child_reports'))
    _section(steering, 'Received operation results', lookup_results)
    _section(steering, 'Own last outcome', state.get('last_local_outcome'))
    return '\n'.join(parts) + '\n\n' + '\n'.join(steering)
