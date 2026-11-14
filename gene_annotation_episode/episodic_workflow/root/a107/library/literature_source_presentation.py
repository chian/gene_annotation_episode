"""A107 source and partner evidence prompt."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a107.library.partner_source_task import lead, operation_family, selected_family
from gene_annotation_episode.episodic_workflow.root.a107.library.scientific_decision_presentation import text_instructions
VERSION = 'literature_experimental_task_v1'
SOURCE_AVAILABILITY = 'For literature acquisition, inspect the returned native availability metadata. Europe PMC full-text XML serves its open-access subset; presence in PMC or free HTML/PDF access does not by itself establish XML availability. Preserve the actual retrieval failure separately from scientific absence, and select a usable representation or another relevant source when appropriate.'
SOURCE_SCOPE = 'Page and reader children can use only their assigned Source and its derived Sources. A known or received sibling dataset is outside that reading assignment, even when it describes the same experiment. Keep a calculation needing separate evidence and data Sources with a literature, strategy or search parent that actually holds both. A bounded reader can instead return source-local observations or select operands entirely within its own Source. Before delegating, preserve the inputs the child can actually read. component_axis_source_access reports real access rejections to the parent on its next decision; these are operational needs, not scientific absence or opposition. Repeating a rejected read does not widen its assignment.'
COMPONENT_READING_TASK = 'Reuse applicable recorded components, exact source witnesses and prior inspections before selecting more work. Choose an additional read or calculation to address a particular unresolved operand or scientific question; revisiting a passage remains available when needed. A completed read is not a completed biological assessment. An unavailable cell describes its selected inputs, not everything in a paper.\n\nEstablish the actual assayed molecule or construct, organism, experimental system, endpoint, units, controls, conditions, uncertainty and repetition basis. Keep source quantities, interpreted models and target application separate. Select source spans and scientific meanings; the original readers, validators and graders perform the calculations. Preserve missing calibration, identity, measurements and dependence. Repeated representations are not independent evidence. No overall reliability, transfer weight or annotation probability is defined here.\n\nReturn the requested saved typed information with its scope and limitations. Source reading, bookkeeping and repeated results add no scientific credit; the existing controller owns continuation.'
FACT_CONTRACT_TASK = 'Exact saved child return contracts\n\nFor this episode\'s declared contract-information interface, request_context with view=composition_information, operation=episode.return_contract and arguments containing the permitted child\'s role and the requested recorded-fact source returns its complete frozen type and meaning. This is information within the pending decision, not an action or a child launch.\n\nSelect a saved return in your child schema using a top-level field containing only {"$ref":"episode-fact:<source>"}, replacing <source> with the actual declared source name. The host expands this explicit reference to the complete closed type and supplies the saved values; leave that field out of initial_report_json. Choose interpretation fields separately and keep them explicit, required and closed. Select only facts needed for the assigned question.'
_TRACKING = frozenset({'run_id', 'episode_id', 'goal_id', 'parent_goal_id', 'sha256', 'digest', 'content_sha256', 'entry_sha256', 'section_sha256', 'implementation_sha256', 'private_history', 'private_reasoning', 'restored_episode_history', 'restored_public_exchanges', 'diagnostics', 'controller_binding', 'credit_binding'})

def _public(value):
    if isinstance(value, Mapping):
        return {key: _public(child) for key, child in value.items() if isinstance(key, str) and key not in _TRACKING and (not key.startswith('private_')) and (not key.endswith('_sha256'))}
    if isinstance(value, (tuple, list)):
        return [_public(child) for child in value]
    return value

def _display(value):
    return json.dumps(_public(value), ensure_ascii=False, sort_keys=True, indent=2, default=str)

def _section(parts, title, value):
    if value is not None and value != {} and (value != []) and (value != ()):
        parts.extend(('', title, '', value if isinstance(value, str) else _display(value)))

def _selected_family(state):
    assignment = state.get('literature_assignment', {})
    if not isinstance(assignment, Mapping):
        return None
    selected = {key for key, value in assignment.items() if isinstance(key, str) and key.startswith('requested_') and value}
    sources = set()
    if not selected:
        form = state.get('requested_form', {})
        properties = form.get('properties', {}) if isinstance(form, Mapping) else {}
        if isinstance(properties, Mapping):
            sources = {field['x-source'] for field in properties.values() if isinstance(field, Mapping) and isinstance(field.get('x-source'), str)}
    return selected_family(selected, sources)

def _selected_tools(state):
    tools = state.get('tools', ())
    if state.get('contract_information_profile') != 'operation_contract_information_v1':
        return tools
    tools = deepcopy(tools)
    preferred, other = ([], [])
    prefix = 'literature.' + operation_family() + '.'
    for tool in tools:
        name = tool.get('name', '')
        if name.startswith('literature.') and (not name.startswith(prefix)):
            tool['description'] = 'Available; request its full meaning and operands through episode.operation_contract.'
            tool.pop('input_schema', None)
            other.append(tool)
        else:
            preferred.append(tool)
    return preferred + other

def is_literature_experimental_context(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    return isinstance(marker, Mapping) and marker.get('version') == VERSION
