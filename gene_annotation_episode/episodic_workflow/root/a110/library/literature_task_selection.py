"""Select A110 reaction instructions from actual requested or returned work."""
from collections.abc import Mapping
import json
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_component_binding import population_family_specs, request_aliases, scope_sources, source_aliases
_SOURCE, _TASK, _MODULE, _REPOSITORY, _REQUEST, _OPERATION = population_family_specs()[0]
_SOURCES = {_SOURCE, *source_aliases()}
_REQUESTS = {_REQUEST: _SOURCE, **request_aliases()}
_SCOPES = scope_sources()

def population_task_metadata_specs():
    from gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage import LiteratureReactionRepository
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population_contracts import PROVIDER
    yield (_SOURCE, 'rate_population', LiteratureReactionRepository.operations_table, PROVIDER, (LiteratureReactionRepository.record_version, 'literature_reaction_record_v3'))

def _form_sources(form):
    if not isinstance(form, Mapping):
        return
    nodes = form.get('properties', {}).values() if isinstance(form.get('properties'), Mapping) else (form,)
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        if set(node) == {'$ref'} and isinstance(node['$ref'], str) and node['$ref'].startswith('episode-fact:'):
            source = node['$ref'][len('episode-fact:'):]
            if source in _SOURCES:
                yield source
        elif node.get('x-source') in _SOURCES:
            item = node.get('items')
            properties = item.get('properties') if isinstance(item, Mapping) else None
            if node.get('type') == 'array' and isinstance(properties, Mapping) and ({'sheet_ref', 'component'} <= properties.keys()) and (item.get('additionalProperties') is False):
                yield node['x-source']

def _row_source(value):
    if not isinstance(value.get('sheet_ref'), str) or not any((name in value for name in ('component', 'cells'))):
        return None
    if value.get('evaluation_scope', value.get('evaluated_scope')) in _SCOPES:
        return _SOURCE
    return None

def _information_sources(value, *, selected_history=False):
    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _information_sources(child, selected_history=selected_history)
        return
    if not isinstance(value, Mapping):
        return
    source = _row_source(value)
    if source:
        yield source
        return
    result = value.get('result')
    if isinstance(result, Mapping) and result.get('view') == 'records':
        selected_history = True
    if value.get('status') in ('invalid', 'failed', 'error') and value.get('selected_tool') in (_OPERATION, 'literature.reaction.source.populate'):
        yield _SOURCE
    if isinstance(result, Mapping) and value.get('status') == 'completed':
        kind = result.get('information_kind')
        if kind == 'return_contract_information_v1' and result.get('source') in _SOURCES:
            yield _SOURCE
            return
        if kind == 'operation_contract_information_v1' and result.get('operation') in (_OPERATION, 'literature.reaction.source.populate'):
            yield _SOURCE
            return
    if selected_history and isinstance(value.get('selection'), Mapping):
        if value.get('admitted_report') is not None:
            return
        selection = value['selection']
        if selection.get('tool') in (_OPERATION, 'literature.reaction.source.populate'):
            yield _SOURCE
    for name, child in value.items():
        if name not in {'selection', 'arguments', 'assignment', 'context', 'private_history', 'admitted_report', 'child_reports', 'current_report_update', 'requested_form', 'report_schema', 'input_schema', 'tools', 'child_options'}:
            yield from _information_sources(child, selected_history=selected_history)

def selected_literature_task_sections(state, lookup_results=()):
    """Return the private reaction task only when A110 work selects it."""
    if not isinstance(state, Mapping):
        return ()
    selected = []
    assignment = state.get('literature_assignment')
    if isinstance(assignment, Mapping):
        selected.extend((_REQUESTS[key] for key in assignment if key in _REQUESTS))
    selected.extend(_form_sources(state.get('requested_form')))
    goal = state.get('goal')
    if isinstance(goal, Mapping):
        selected.extend(_form_sources(goal.get('result_contract')))
    owned = state.get('literature_owned_population_sources')
    if isinstance(owned, (tuple, list)):
        selected.extend((source for source in owned if source in _SOURCES))
    selected.extend(_information_sources(state.get('last_local_outcome')))
    attempt = state.get('literature_selected_population_attempt')
    if isinstance(attempt, Mapping) and attempt.get('status') in ('invalid', 'failed', 'error'):
        if attempt.get('tool') in (_OPERATION, 'literature.reaction.source.populate'):
            selected.append(_SOURCE)
    selected.extend(_information_sources(lookup_results, selected_history=True))
    return ((_SOURCE, _TASK),) if selected else ()
