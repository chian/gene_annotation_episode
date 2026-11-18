"""A102's private structural-source prompt presentation."""
from __future__ import annotations

from collections.abc import Mapping
import json

from .composition_information import CONTRACT_INFORMATION_PROFILE
from .schema_information_text import render_schema_information
from .structural_homology_evidence_prompt import text_instructions
from .literature_structure_prompt import STRUCTURE_TASK


VERSION = 'literature_experimental_task_v1'
EXPERIMENTAL_TASK = STRUCTURE_TASK
SAVED_NUMERICAL_RETURN_TASK = (
    'Request the declared saved structural or geometric result components. '
    'Keep the selected model, feature, conditions and unavailable endpoints with '
    'each result. Write interpretations in separate fields.')
FACT_CONTRACT_TASK = ('For a declared A102 child return, request episode.return_contract '
    'with the child role and recorded-fact source. Select its exact saved type with '
    'a top-level {"$ref":"episode-fact:<source>"} field. The host supplies the saved '
    'value; write interpretations in separate closed fields.')
_PRIVATE = frozenset(('private_history', 'private_reasoning', 'provider_result',
    'calculation_implementation', 'report_contract_declaration'))


def is_literature_experimental_context(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    return isinstance(marker, Mapping) and marker.get('version') == VERSION


def _safe(value):
    if isinstance(value, Mapping):
        return {name: _safe(child) for name, child in value.items()
            if name not in _PRIVATE and not name.startswith('private_')
            and not name.endswith('_sha256')}
    if isinstance(value, (list, tuple)):
        return [_safe(child) for child in value]
    return value


def _value(value):
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(_safe(value), ensure_ascii=False, sort_keys=True, indent=2,
            allow_nan=False, default=str)
    return 'unknown' if value is None else str(value)


def _section(parts, title, value):
    if value is not None and value != '' and value != [] and value != {}:
        parts.extend(('', title, '', _value(value)))


def _task(state, instructions):
    normalized = text_instructions(instructions)
    parts = ['TASK', '', STRUCTURE_TASK]
    additional = normalized.replace(STRUCTURE_TASK, '').strip()
    if additional:
        parts.extend(('', additional))
    if SAVED_NUMERICAL_RETURN_TASK not in normalized:
        parts.extend(('', SAVED_NUMERICAL_RETURN_TASK))
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(('', FACT_CONTRACT_TASK))
    goal = state.get('goal', {})
    _section(parts, 'Assigned structural question', goal)
    _section(parts, 'Assigned scientific scope', state.get('scope'))
    _section(parts, 'Source and target assignment', state.get('literature_assignment'))
    descriptor = state.get('reference_evidence_parent', {})
    if isinstance(descriptor, Mapping):
        _section(parts, 'Caller-selected source references', descriptor.get('source_refs'))
        _section(parts, 'Representations of selected sources', descriptor.get('source_custody'))
    working = state.get('working_state', {})
    if isinstance(working, Mapping):
        _section(parts, 'Supplied structural material', {key: working[key] for key in (
            'subjects', 'materials', 'material_links', 'target_binding',
            'read_library_access', 'supplied_context_source_refs') if key in working})
    for tool in state.get('tools', ()):
        if not isinstance(tool, Mapping):
            continue
        _section(parts, 'Operation ' + str(tool.get('name', '')), tool.get('description'))
        if not profile:
            _section(parts, 'Operands for ' + str(tool.get('name', '')), tool.get('input_schema'))
    _section(parts, 'Permitted narrower investigations', state.get('child_options'))
    _section(parts, 'Requested report purpose', state.get('requested_report_purpose'))
    form = state.get('requested_form')
    if isinstance(form, Mapping):
        _section(parts, 'Typed return meanings',
            render_schema_information(form, title='Parent requested return') if profile else form)
    _section(parts, 'Return interpretation timing', state.get('report_lifecycle'))
    return '\n'.join(parts)


def _steering(state, lookup_results):
    parts = ['STEERING', '', 'Use the original A102 structural question and the actual received source results.']
    _section(parts, 'Current structural state', state.get('current_results'))
    _section(parts, 'Saved structural assessments', state.get('current_scoring'))
    _section(parts, 'Received results', list(lookup_results))
    _section(parts, 'Previous decisions', state.get('completed_actions'))
    return '\n'.join(parts)


def render_literature_experimental_prompt(state, instructions, *, lookup_results=()):
    if not is_literature_experimental_context(state):
        raise ValueError('literature_experimental_context_required')
    if state['literature_experimental_work'].get('aspect') == 'reference_evidence_parent':
        from .literature_reference_parent_prompt import render_reference_evidence_parent_prompt
        return render_reference_evidence_parent_prompt(state, instructions,
            lookup_results=lookup_results)
    return _task(state, instructions) + '\n\n' + _steering(state, lookup_results)


__all__ = ['VERSION', 'EXPERIMENTAL_TASK', 'SAVED_NUMERICAL_RETURN_TASK',
    'is_literature_experimental_context', 'render_literature_experimental_prompt']
