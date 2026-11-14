"""Root-owned contract_information.py"""
from __future__ import annotations
from .composition_information import CONTRACT_ARGUMENT_TRANSPORT
from .composition_information import CONTRACT_INFORMATION_OPERATIONS
from .composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.domain import ContractError
from .episode_contract_information import ContractInformationError
from .decision_context import INSTRUCTIONS as DECISION_EXCHANGE_INSTRUCTIONS
from .decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from .report_facts import FACT_MEANINGS
from .report_facts import FACT_SOURCES
from .episode_journal import WorkflowError
from .workflow_values import _compile_form
from .task_values import _digest
from .workflow_values import _embedded_tool_schema
from .task_values import _json
from .task_action_contracts import _object
from .task_values import _plain
from .episode_contract_information import expand_fact_form
import json
from . import literature_numerical_contracts
from .episode_contract_information import operation_contract_information
from .boundary_validation import parse_json_object
from .composition_information import restricted_root
from .episode_contract_information import return_contract_information
from .episode_contract_information import validate_saved_fact_form

class ContractInformation:

    def validate_contract_information_configuration(self, profile):
        if profile is not None and (profile != CONTRACT_INFORMATION_PROFILE or self.decision_protocol != DECISION_EXCHANGE_PROTOCOL):
            raise ContractInformationError('contract_information_requires_pending_decision_protocol', 'decision_protocol')
        return profile

    def contract_information_profile(self, source):
        if source is None:
            return None
        profile = self.episode_bindings.contract_information_profile(self.binding_context(source))
        return self.validate_contract_information_configuration(profile)

    def freeze_contract_information(self, source, context, schema):
        """Freeze declared instruction contracts, never source facts or work."""
        roles = list(self.available_child_roles(source))
        facts = {role: _plain(self.return_contract_sources(role, parent_path=source.path)) for role in roles}
        return {'version': CONTRACT_INFORMATION_PROFILE, 'permitted_child_roles': roles, 'fact_sources_by_role': facts, 'fact_sources_sha256': _digest(facts), 'catalog_sha256': _digest(context.get('tools', [])), 'action_schema_sha256': _digest(schema), 'exchange_schema': json.loads(_json(source.exchange_schema(schema))), 'instructions': source.instructions(context) + '\n' + DECISION_EXCHANGE_INSTRUCTIONS}

    def validate_contract_information(self, saved):
        """Check original host schema/catalog associations without a factory."""
        record, context, schema = (saved.get('contract_information'), saved['context'], saved['schema'])
        keys = {'version', 'permitted_child_roles', 'fact_sources_by_role', 'fact_sources_sha256', 'catalog_sha256', 'action_schema_sha256', 'exchange_schema', 'instructions'}
        if not isinstance(record, dict) or set(record) != keys or record['version'] != CONTRACT_INFORMATION_PROFILE or (context.get('contract_information_profile') != CONTRACT_INFORMATION_PROFILE) or (type(record['instructions']) is not str) or (record['fact_sources_sha256'] != _digest(record['fact_sources_by_role'])) or (record['catalog_sha256'] != _digest(context.get('tools', []))) or (record['action_schema_sha256'] != _digest(schema)):
            raise WorkflowError('original_contract_information_mismatch')
        roles = record['permitted_child_roles']
        if not isinstance(roles, list) or any((type(role) is not str or not role for role in roles)) or len(set(roles)) != len(roles) or (not isinstance(record['fact_sources_by_role'], dict)) or any((not isinstance(rows, dict) for rows in record['fact_sources_by_role'].values())) or (set(record['fact_sources_by_role']) != set(roles)):
            raise WorkflowError('original_return_contract_roles_mismatch')
        catalog = context.get('tools', [])
        if not isinstance(catalog, list) or any((not isinstance(row, dict) or not {'name', 'input_schema', 'description'} <= row.keys() or type(row['name']) is not str or (type(row['description']) is not str) for row in catalog)) or len({row['name'] for row in catalog}) != len(catalog):
            raise WorkflowError('original_operation_catalog_mismatch')
        branches = schema['properties']['selection']['anyOf']
        tools = [row for row in branches if row.get('properties', {}).get('kind', {}).get('const') == 'tool']
        by_name = {row['properties']['tool']['const']: row for row in tools}
        if len(by_name) != len(tools) or set(by_name) != {row['name'] for row in catalog}:
            raise WorkflowError('original_operation_catalog_mismatch')
        for entry in catalog:
            branch = by_name[entry['name']]
            expected = _object({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': entry['name']}, 'arguments': _embedded_tool_schema(entry['input_schema'])})
            if 'argument_transport' in entry:
                if entry['argument_transport'] != CONTRACT_ARGUMENT_TRANSPORT:
                    raise WorkflowError('original_operation_transport_mismatch')
                expected['x-argument-transport'] = CONTRACT_ARGUMENT_TRANSPORT
            if _json(branch) != _json(expected):
                raise WorkflowError('original_operation_contract_mismatch')
        exchange = record['exchange_schema']
        try:
            alternatives = exchange['properties']['response']['anyOf']
            selected = _object({'response_type': {'type': 'string', 'const': 'select_action'}, **schema['properties']})
            selected['required'] = ['response_type', *schema['required']]
            lookups = alternatives[0]['properties']['lookup']['anyOf']
            child = next((row for row in lookups if row['properties'].get('view', {}).get('const') == 'child_options'))
            names = {row['properties'].get('operation', {}).get('const') for row in lookups}
            if alternatives[1] != selected or child['properties']['role']['enum'] != [None, *roles] or (not set(CONTRACT_INFORMATION_OPERATIONS) <= names):
                raise WorkflowError('original_contract_lookup_schema_mismatch')
        except (KeyError, TypeError, IndexError, StopIteration) as error:
            raise WorkflowError('original_contract_lookup_schema_mismatch') from error
        return record

    def pending_contract_information(self, source, decision_index):
        row = self.journal.row('runtime_model_calls', source.episode_id, decision_index)
        if row is None or row['purpose'] != 'decision':
            raise WorkflowError('original_contract_decision_unavailable')
        saved = json.loads(row['request'])
        return (saved, self.validate_contract_information(saved))

    def contract_information_reply(self, saved, record, name, arguments):
        """Resolve only ORIGINAL declared information; this executes no tool."""
        if name == CONTRACT_INFORMATION_OPERATIONS[0]:
            return operation_contract_information(catalog=saved['context'].get('tools', []), operation=arguments['operation'])
        facts = {role: {source: row for source, row in rows.items() if 'report_schema' in row} for role, rows in record['fact_sources_by_role'].items()}
        return return_contract_information(facts_by_role=facts, permitted_child_roles=record['permitted_child_roles'], role=arguments['role'], source=arguments['source'])

    def freeze_literature_numerical_contracts(self, source, context, schema):
        """Freeze a bounded declaration surface only for fresh literature tasks."""
        from .literature_context_marker import is_literature_experimental_context
        if not is_literature_experimental_context(context):
            return None
        roles = list(self.available_child_roles(source))
        builtins = {name: {'type': 'number' if name == 'credit' else 'array', 'meaning': FACT_MEANINGS[name]} for name in FACT_SOURCES}
        facts = {role: builtins | _plain(self.report_sources(role, parent_path=source.path)) for role in roles}
        return literature_numerical_contracts.freeze_contracts(facts_by_role=facts, permitted_child_roles=roles, action_schema=schema)

    from .commissioning_policy import root_child_return_sources

    def child_form_input(self, source, selection, role):
        if 'schema_json' in selection:
            return selection['schema_json']
        sources = self.root_child_return_sources(source, role)
        if not sources:
            raise ContractError('child_return_form_required')
        return _json(self.project_credit.child_return_form(self.binding_context(source), role))

    def child_initial_report_input(self, source, selection, role):
        if 'initial_report_json' in selection:
            return selection['initial_report_json']
        if not self.root_child_return_sources(source, role):
            raise ContractError('child_initial_report_required')
        return '{}'

    def expanded_contract_form(self, source, selection, index, role, *, original_child=True, owner=None):
        """Resolve a chosen form from original pending or saved child records."""
        schema_json = self.child_form_input(source, selection, role)
        if self.contract_information_profile(source) is None:
            submitted = parse_json_object(schema_json)
            if not literature_numerical_contracts.uses_fact_references(submitted):
                return (_compile_form(schema_json, self.report_sources(role, parent_path=source.path, owner=owner)), None)
            if original_child:
                identity = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path)
                child = self.journal.row('runtime_episodes', identity.episode_id)
                if child is not None:
                    request = json.loads(child['request'])
                    declaration = request['message'].get('report_contract_declaration')
                    if declaration is None:
                        raise WorkflowError('original_report_contract_declaration_unavailable')
                    schema = validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json, expanded_schema=request['report_contract']['measurements']['schema'], declaration=declaration)
                    return (schema, declaration)
            row = self.journal.row('runtime_model_calls', source.episode_id, index)
            saved = json.loads(row['request']) if row is not None and row['purpose'] == 'decision' else {}
            if literature_numerical_contracts.SAVED_MEMBER not in saved:
                return (_compile_form(schema_json, self.report_sources(role, parent_path=source.path, owner=owner)), None)
            record = literature_numerical_contracts.validate_frozen_contracts(saved)
            result = literature_numerical_contracts.expand_numerical_form(schema_json, child_role=role, saved=saved)
            schema = _compile_form(_json(result['expanded_schema']), record['source_types_by_role'][role], include_runtime_sources=False)
            validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json, expanded_schema=schema, declaration=result['declaration'])
            return (schema, result['declaration'])
        if original_child:
            identity = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path)
            row = self.journal.row('runtime_episodes', identity.episode_id)
            if row is not None:
                request = json.loads(row['request'])
                declaration = request['message'].get('report_contract_declaration')
                if declaration is None:
                    raise WorkflowError('original_report_contract_declaration_unavailable')
                schema = validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json, expanded_schema=request['report_contract']['measurements']['schema'], declaration=declaration)
                return (schema, declaration)
        _, record = self.pending_contract_information(source, index)
        full = record['fact_sources_by_role']
        typed = {key: {name: row for name, row in rows.items() if 'report_schema' in row} for key, rows in full.items()}
        result = expand_fact_form(schema_json, child_role=role, facts_by_role=typed, permitted_child_roles=record['permitted_child_roles'])
        schema = _compile_form(_json(result['expanded_schema']), full[role])
        validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json, expanded_schema=schema, declaration=result['declaration'])
        return (schema, result['declaration'])
