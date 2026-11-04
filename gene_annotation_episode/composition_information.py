"""Read-only child construction information inside a pending decision.

This module declares a closed metadata lookup surface. It exposes no scientific
record reader, external data acquisition, execution operation or action loop.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
import json

from .decision_history import lookup_schema as own_lookup_schema
from .tool_knowledge import catalog as knowledge_catalog
from .launch_instructions import catalog as launch_catalog


ROOT_BOUNDARY_VERSION = 'root_episode_commissioning_v1'
CONTRACT_INFORMATION_PROFILE = 'operation_contract_information_v1'
CONTRACT_ARGUMENT_TRANSPORT = 'json_object_contract_information_v1'
CONTRACT_INFORMATION_OPERATIONS = ('episode.operation_contract', 'episode.return_contract')


def contract_metadata_catalog():
    """Small information-only declarations, including for childless leaves."""
    def arguments(fields):
        return {'type': 'object', 'additionalProperties': False, 'required': list(fields),
            'properties': {name: {'type': 'string', 'minLength': 1} for name in fields}}
    return [{'name': CONTRACT_INFORMATION_OPERATIONS[0], 'description':
        'Inspect one actual operation\'s complete frozen argument contract within this pending decision. This does not invoke it.',
        'input_schema': arguments(('operation',))},
        {'name': CONTRACT_INFORMATION_OPERATIONS[1], 'description':
        'Inspect a permitted child\'s declared recorded-fact return contract within this pending decision. This creates no child or fact.',
        'input_schema': arguments(('role', 'source'))}]


def is_contract_information(outcome):
    return (isinstance(outcome, Mapping) and outcome.get('status') == 'completed'
        and isinstance(outcome.get('result'), Mapping) and outcome['result'].get('information_kind') in {
            'operation_contract_information_v1', 'return_contract_information_v1'})


def requested_contract_information(public_exchanges):
    """Select only answered public requests in this one pending decision."""
    selected = {}
    for exchange in public_exchanges:
        outcome = exchange.get('lookup_result')
        if not is_contract_information(outcome):
            continue
        result = outcome['result']
        key = tuple(result.get(name) for name in ('information_kind', 'operation', 'role', 'source'))
        if key in selected and selected[key] != outcome:
            raise ValueError('pending_contract_information_conflict')
        selected[key] = deepcopy(outcome)
    return list(selected.values())


def restricted_root(workflow, source):
    return (getattr(workflow, 'root_action_boundary', None) == ROOT_BOUNDARY_VERSION
        and source is not None and len(source.path) == 1
        and source.path[0][0] == 'annotation')


def metadata_catalog(workflow, source):
    """Only actual instruction/process libraries; never the ordinary registry."""
    entries = [*knowledge_catalog(), *launch_catalog()]
    if workflow.scientific_library_available(source):
        from .scientific_process_library import catalog
        entries.extend(catalog())
        entries.extend(workflow.scientific_retriever_catalog())
    if getattr(workflow, 'contract_information_profile', lambda _: None)(source) == CONTRACT_INFORMATION_PROFILE:
        entries.extend(contract_metadata_catalog())
    return deepcopy(entries)


def lookup_schema(workflow, source):
    roles = list(workflow.available_child_roles(source))
    branches = deepcopy(own_lookup_schema()['anyOf'])
    branches.append({'type': 'object', 'additionalProperties': False,
        'required': ['view', 'role'], 'properties': {
            'view': {'type': 'string', 'const': 'child_options'},
            'role': {'type': ['string', 'null'], 'enum': [None, *roles]}}})
    for entry in metadata_catalog(workflow, source):
        branches.append({'type': 'object', 'additionalProperties': False,
            'required': ['view', 'operation', 'arguments'], 'properties': {
                'view': {'type': 'string', 'const': 'composition_information'},
                'operation': {'type': 'string', 'const': entry['name']},
                'arguments': deepcopy(entry['input_schema'])}})
    return {'title': 'PendingDecisionLookup', 'anyOf': branches}


def _kind(schema):
    if schema.get('format') in {'reference', 'identifier'}:
        namespace = schema.get('x-reference-namespace')
        return schema['format'] + (' to ' + namespace if namespace else '')
    if 'const' in schema:
        return 'exactly ' + json.dumps(schema['const'], ensure_ascii=False)
    if 'enum' in schema:
        return 'one of ' + ', '.join(json.dumps(x, ensure_ascii=False) for x in schema['enum'])
    kind = schema.get('type')
    if isinstance(kind, list):
        return ' or '.join(kind)
    if kind == 'array':
        return 'array of ' + _kind(schema.get('items', {}))
    if kind:
        return kind
    if 'anyOf' in schema:
        return 'one of the declared alternatives'
    return 'declared value'


def _schema_rows(schema, prefix='assignment', required=True):
    """Render declared operands without serializing an entire schema object."""
    rows = [(prefix, 'required' if required else 'optional', _kind(schema),
             schema.get('description', ''))]
    for field, child in schema.get('properties', {}).items():
        rows.extend(_schema_rows(child, prefix + '.' + field,
            field in schema.get('required', ())))
    if isinstance(schema.get('items'), dict) and (
            'properties' in schema['items'] or 'anyOf' in schema['items']):
        rows.extend(_schema_rows(schema['items'], prefix + '[]', required))
    for index, branch in enumerate(schema.get('anyOf', ())):
        rows.extend(_schema_rows(branch, prefix + f' alternative {index + 1}', required))
    return rows


def _cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def _table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
        '| ' + ' | '.join('---' for _ in headers) + ' |',
        *('| ' + ' | '.join(_cell(x) for x in row) + ' |' for row in rows)])


def child_options(workflow, source, role=None):
    """Describe real allowed roles and their own return-source contracts."""
    allowed = workflow.available_child_roles(source)
    if role is not None and role not in allowed:
        raise ValueError('child_role_not_available_to_parent')
    rows, details = [], []
    for name in allowed if role is None else (role,):
        if name in workflow.episode_bindings.roles:
            binding = workflow.episode_bindings.for_role(name)
            assignment = binding.assignment_schema(name)
        elif workflow.job_episodes is not None and name in workflow.job_episodes.roles:
            assignment = {'type': 'object'}
        else:
            assignment = {'type': 'object'}
        facts = getattr(workflow, 'return_contract_sources', workflow.report_sources)(name)
        status = 'available'
        if name == 'scientific_process':
            library = workflow.scientific_process_binding.library
            if not any(row['option_ref']['slot'] in {'evidence_axis', 'annotation_distinction'}
                    for row in library.headers()):
                status = 'missing scientific-support option'
        fields = ', '.join(assignment.get('required', ())) or 'see declared child contract'
        rows.append((name, status, fields, ', '.join(facts)))
        if role is not None:
            details.extend(['', 'Assignment operands', '', _table(
                ('Field', 'Presence', 'Type/value', 'Meaning'), _schema_rows(assignment)),
                '', 'Return facts available for this child', '', _table(
                    ('Source', 'Type', 'Meaning'), [(key, _kind(value.get('report_schema', value)),
                        value.get('meaning', '')) for key, value in facts.items()])])
    text = _table(('Child', 'Construction', 'Required assignment fields', 'Return facts'), rows)
    return {'status': 'completed', 'text': text + '\n'.join(details)}


__all__ = ['ROOT_BOUNDARY_VERSION', 'restricted_root', 'metadata_catalog',
           'lookup_schema', 'child_options', 'CONTRACT_INFORMATION_PROFILE',
           'CONTRACT_ARGUMENT_TRANSPORT', 'CONTRACT_INFORMATION_OPERATIONS', 'contract_metadata_catalog',
           'is_contract_information', 'requested_contract_information']
