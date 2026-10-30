"""Present registered numerical returns without reproducing a scoring sheet.

Only exact registered A105 numerical declarations receive this treatment.
The original closed contracts remain with the host; this pure detached view is
neither a schema accepted by validation nor a replacement return contract.
"""
from collections.abc import Mapping
from .literature_numerical_contracts import RETURN_MEANINGS, is_registered_schema


MEANINGS = {source: meaning + ' The host supplies the saved values under the original complete closed type; do not author or alter this recorded field.'
    for source, meaning in RETURN_MEANINGS.items()}


def _declaration_text(source):
    return ('To request this recorded return from a child, choose a top-level field whose declaration '
        'contains only $ref with the exact value episode-fact:' + source
        + '. The host expands that explicit reference to the original complete closed type before commissioning. '
        'Select the needed numerical components through the child assignment. '
        'Keep model-authored interpretations in separate fields with their original constrained meanings.')



def _copy(value):
    if isinstance(value, Mapping):
        return {name: _copy(child) for name, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy(child) for child in value]
    return value


def _compact(node):
    if not isinstance(node, Mapping) or node.get('x-source') not in MEANINGS:
        return node
    source = node['x-source']
    if not is_registered_schema(node):
        return node
    shown = {name: _copy(node[name]) for name in ('type', 'x-source', 'minItems', 'maxItems', 'uniqueItems')
        if name in node}
    shown['description'] = MEANINGS[source] + ' ' + _declaration_text(source)
    return shown


def return_schema_view(schema):
    """Keep actual interpretation constraints and compact exact fact nodes."""
    shown = _copy(schema)
    if not isinstance(shown, dict):
        return shown
    if shown.get('x-source') in MEANINGS:
        return _compact(shown)
    if isinstance(shown.get('properties'), dict):
        shown['properties'] = {name: _compact(node) for name, node in shown['properties'].items()}
    return shown


def state_view(state):
    """Copy only declared schema locations; scientific values stay unchanged."""
    shown = dict(state)
    if isinstance(state.get('requested_form'), Mapping):
        shown['requested_form'] = return_schema_view(state['requested_form'])
    goal = state.get('goal')
    if isinstance(goal, Mapping) and isinstance(goal.get('result_contract'), Mapping):
        shown['goal'] = {**goal, 'result_contract': return_schema_view(goal['result_contract'])}
    facts = state.get('available_report_facts')
    if isinstance(facts, Mapping):
        shown['available_report_facts'] = {name: ({**entry,
            'report_schema': return_schema_view(entry['report_schema'])}
            if name in MEANINGS and isinstance(entry, Mapping) and 'report_schema' in entry else entry)
            for name, entry in facts.items()}
    return shown


def lookup_task_kind(outcome):
    """Only an actual requested contract makes the corresponding task relevant."""
    result = outcome.get('result') if isinstance(outcome, Mapping) else None
    if not isinstance(result, Mapping) or outcome.get('status') != 'completed':
        return None
    if result.get('information_kind') == 'return_contract_information_v1':
        source = result.get('source')
        if source in MEANINGS:
            return source
    if result.get('information_kind') == 'operation_contract_information_v1':
        return {'literature.measurement_validation.populate': 'literature_measurement_validation_cells',
            'literature.channel.populate': 'literature_channel_cells',
            'literature.ion_discrimination.populate': 'literature_ion_discrimination_cells',
            'literature.assay.components.populate': 'literature_compiled_assay_cells'}.get(result.get('operation'))
    return None


def requested_return_text(result):
    """Present an exact requested return without exposing its numerical sheet.

    The original lookup retains its complete schema/text for host custody.
    The same explicit fact reference preserves the original requested type.
    """
    source = result.get('source')
    if (result.get('information_kind') != 'return_contract_information_v1' or source not in MEANINGS
            or not is_registered_schema(result.get('report_schema'), source=source)):
        return None
    return MEANINGS[source] + '\n\n' + _declaration_text(source)



__all__ = ['return_schema_view', 'state_view', 'lookup_task_kind', 'requested_return_text']
