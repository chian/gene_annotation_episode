"""A110's private source and reaction evidence prompt."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a110.composition_information import CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_PROFILE, is_contract_information
from gene_annotation_episode.episodic_workflow.root.a110.schema_information_text import render_schema_information
from gene_annotation_episode.episodic_workflow.root.a110.library.scientific_decision_presentation import _band, _schema, text_instructions
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_instructions import lead, selected_family
VERSION = 'literature_experimental_task_v1'
SOURCE_AVAILABILITY = 'Inspect returned native availability metadata when acquiring literature. Preserve retrieval failure separately from scientific absence. Select a usable representation or another relevant source when appropriate.'
SOURCE_SCOPE = "A source reader can inspect only its assigned Source and derived Sources. Preserve source and data access boundaries when delegating calculations. A rejected read does not widen a child's assignment."
COMPONENT_READING_TASK = 'Reuse applicable recorded components, source witnesses and prior inspections. Select additional reading or calculation for a specific unresolved operand or scientific question. Preserve the actual species, quantities, units, conditions, model assumptions, provenance and missing inputs. Chemical bookkeeping, measured activity and physiological feasibility are separate conclusions. Return the requested typed findings with their scope and limitations; the existing controller owns continuation.'
FACT_CONTRACT_TASK = 'For a declared recorded fact, request episode.return_contract with its permitted child role and source. Select the complete saved return type using a top-level field containing only {"$ref":"episode-fact:<source>"}; the host fills that field. Keep interpretation fields separate and explicit.'
CONTRACT_INFORMATION_TASK = "Request episode.operation_contract when the selected operation's complete argument type is needed. Select the actual operation and original typed operands. A contract lookup creates no observation."

def is_literature_experimental_context(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    return isinstance(marker, Mapping) and marker.get('version') == VERSION

def _safe(value):
    if isinstance(value, Mapping):
        hidden = {'private_history', 'private_reasoning', 'history', 'parent_history', 'own_completed_action_history', 'restored_episode_history', 'body', 'content', 'bytes', 'base64', 'stdout', 'stderr'}
        return {key: _safe(child) for key, child in value.items() if key not in hidden}
    if isinstance(value, (tuple, list)):
        return [_safe(child) for child in value]
    return value

def _values(value):
    return json.dumps(_safe(value), ensure_ascii=False, sort_keys=True, indent=2, default=str)

def _pick(value, fields):
    return {key: value[key] for key in fields if isinstance(value, Mapping) and key in value}

def _section(parts, title, content):
    if content not in (None, '', [], {}, ()):
        parts.extend(['', title, content if isinstance(content, str) else _values(content)])

def _family(state):
    assignment = state.get('literature_assignment', {})
    selected = {key for key, value in assignment.items() if key.startswith('requested_') and value} if isinstance(assignment, Mapping) else set()
    form = state.get('requested_form', {})
    properties = form.get('properties', {}) if isinstance(form, Mapping) else {}
    sources = {field['x-source'] for field in properties.values() if isinstance(field, Mapping) and isinstance(field.get('x-source'), str)} if isinstance(properties, Mapping) else set()
    return selected_family(selected, sources)

def _task(state, instructions, family):
    normalized = text_instructions(instructions)
    parts = ['TASK', '', lead(family) if family else COMPONENT_READING_TASK, '', SOURCE_AVAILABILITY, '', SOURCE_SCOPE]
    if normalized and normalized not in parts:
        parts.extend(['', normalized])
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(['', CONTRACT_INFORMATION_TASK, '', FACT_CONTRACT_TASK])
    goal = state.get('goal', {})
    _section(parts, 'Assigned A110 question', _pick(goal, ('objective', 'task_context') if profile else ('objective', 'task_context', 'result_contract')) if isinstance(goal, Mapping) else goal)
    if profile and isinstance(goal, Mapping) and (goal.get('result_contract') is not None):
        _section(parts, 'Assigned result contract', render_schema_information(goal['result_contract'], title='Assigned result contract'))
    _section(parts, 'Scientific scope', state.get('scope'))
    _section(parts, 'Selected source and reaction operands', state.get('literature_assignment'))
    _section(parts, 'Available source representations', state.get('literature_source_custody'))
    _section(parts, 'Supplied material and source access', _pick(state.get('working_state', {}), ('subjects', 'materials', 'material_links', 'target_binding', 'read_library_access')))
    tools = list(state.get('tools', ()))
    if profile:
        preferred = [row for row in tools if row.get('name', '').startswith('literature.reaction.')]
        tools = preferred + [row for row in tools if row not in preferred]
    _section(parts, 'Available operations', tools)
    for tool in tools:
        if 'input_schema' in tool and (not (profile and tool.get('argument_transport') == CONTRACT_ARGUMENT_TRANSPORT)):
            _section(parts, 'Operands for ' + tool['name'], _schema(tool['input_schema'], 'arguments'))
    _section(parts, 'Permitted narrower investigations', state.get('child_options'))
    _section(parts, 'Parent requested typed return', render_schema_information(state['requested_form'], title='Parent requested return') if profile and isinstance(state.get('requested_form'), Mapping) else state.get('requested_form'))
    _section(parts, 'Return interpretation timing', state.get('report_lifecycle'))
    return '\n'.join(parts)

def _steering(state, lookup_results):
    parts = ['STEERING', '', 'Use exact source references and source-bound meanings. Preserve unresolved identity, measurement, model and resource inputs.']
    _section(parts, 'Recorded source inspections and access', state.get('component_axis_source_access'))
    _section(parts, 'Complete the original child return', state.get('pending_child_delivery'))
    _section(parts, 'Own action yields', state.get('action_yields'))
    controller = state.get('controller', {})
    if isinstance(controller, Mapping) and controller.get('estimate'):
        estimate = controller['estimate']
        _section(parts, 'Current continuation expectation', {'completed_actions': estimate.get('turns'), 'expected_next_gain': _band(estimate.get('expected_next_gain')), 'continuation_cost': controller.get('decision', {}).get('continuation_cost')})
    for key, title in (('last_local_outcome', 'Last action outcome'), ('feedback', 'Returned feedback'), ('current_report_update', 'Requested interpretation'), ('child_reports', 'Received child returns'), ('shared_information_context', 'Investigation updates'), ('pending_work', 'Pending assigned work'), ('waiting_support', 'Waiting information')):
        _section(parts, title, state.get(key))
    for result in lookup_results:
        _section(parts, 'Requested information; continue this decision', result)
    return '\n'.join(parts)

def render_literature_experimental_prompt(state, instructions, *, lookup_results=()):
    if not is_literature_experimental_context(state):
        raise ValueError('a110_literature_experimental_context_required')
    if state['literature_experimental_work'].get('aspect') == 'reference_evidence_parent':
        from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reference_parent_presentation import render_reference_evidence_parent_prompt
        return render_reference_evidence_parent_prompt(state, instructions, lookup_results=lookup_results)
    family = _family(state)
    task = _task(state, instructions, family)
    contracts = [row for row in lookup_results if is_contract_information(row)]
    if contracts:
        _section_output = ['Requested operation contracts', _values(contracts)]
        task += '\n\n' + '\n'.join(_section_output)
    return task + '\n\n' + _steering(state, [row for row in lookup_results if row not in contracts])
