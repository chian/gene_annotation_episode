"""Shared Root policy assembly."""
from __future__ import annotations

def reasoning_action_schema(self, source, commit_schema=None):
    commit_schema = self.store.reasoning_schema() if commit_schema is None else commit_schema
    specialist = self.specialist(source)
    schema = getattr(specialist, 'reasoning_action_schema', None)
    selected = schema(self.binding_context(source), commit_schema) if schema is not None else None
    result = selected if selected is not None else _original_action_catalog._object({'kind': {'type': 'string', 'const': 'reason'}, 'commit': commit_schema})
    return {**result, 'description': '\n\n'.join((value for value in (result.get('description'), _original_action_catalog.REASONING_COMMIT_REQUIREMENT) if value))}

def action_schema(self, source):
    from gene_annotation_episode.episodic_workflow.root.library.scientific_child_contracts import form_examples
    form_example, interpretive_example, scope_schema = form_examples()
    specialist = self.specialist(source)
    common_actions = specialist.permitted_common_actions(self.binding_context(source)) if specialist is not None else ('tool', 'reason', 'child', 'wait', 'redeliver_report')
    if not self.permits_common_action(source, 'wait'):
        common_actions = tuple((action for action in common_actions if action != 'wait'))
    from gene_annotation_episode.episodic_workflow.root.commissioning_policy import filter_annotation_tools
    common_actions = filter_annotation_tools(self, source, common_actions)
    options = [] if self.is_job_source(source) or 'reason' not in common_actions else [self.reasoning_action_schema(source)]
    if 'wait' in common_actions:
        options.append(_original_action_catalog._object({'kind': {'type': 'string', 'const': 'wait'}, 'condition': _original_action_catalog._wait_condition_schema()}))
    for item in self.catalog(source.scope, source=source) if 'tool' in common_actions else ():
        branch = _original_action_catalog._object({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': item['name']}, 'arguments': _original_action_catalog._embedded_tool_schema(item['input_schema'])})
        if item.get('argument_transport') is not None:
            if item['argument_transport'] != _original_action_catalog.CONTRACT_ARGUMENT_TRANSPORT:
                raise ValueError('unsupported_tool_argument_transport')
            branch['x-argument-transport'] = _original_action_catalog.CONTRACT_ARGUMENT_TRANSPORT
        options.append(branch)
    from gene_annotation_episode.episodic_workflow.root.library.scientific_child_contracts import scientific_child_contract
    scientific_child = scientific_child_contract(form_example, interpretive_example, scope_schema)
    if not self.is_job_source(source):
        explicit_roles = None if self.annotation_child_roles is None and (not (len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False))) else self.available_child_roles(source)
        if self.job_episodes is not None and specialist is None:
            options.extend((option for option in self.job_commission_schemas(source, scientific_child) if explicit_roles is None or option['properties']['role']['const'] in explicit_roles))
        if 'child' in common_actions:
            roles = tuple((role for role in explicit_roles if role in self.episode_bindings.roles)) if explicit_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
            declared = set(specialist.child_roles(source.path[-1][0])) if specialist else set(roles)
            if not set(roles) <= declared:
                raise _original_action_catalog.WorkflowError('available_child_outside_declared_type_edges')
            for role in roles:
                binding = self.episode_bindings.for_child(source.path, role)
                child_schema = getattr(binding, 'child_assignment_schema', None)
                properties = {**scientific_child['properties'], 'kind': {'type': 'string', 'const': 'episode_child'}, 'role': {'type': 'string', 'const': role}, 'assignment': child_schema(self.binding_context(source), role) if child_schema is not None else binding.assignment_schema(role)}
                if self.root_child_return_sources(source, role):
                    properties.pop('schema_json')
                    properties.pop('initial_report_json')
                options.append(_original_action_catalog._object(properties))
    if not self.is_job_source(source) and 'redeliver_report' in common_actions:
        options.append(_original_action_catalog._object({'kind': {'type': 'string', 'const': 'redeliver_report'}, 'delivery_ref': {'type': 'string', 'description': 'Copy the delivery_ref from report_deliveries or report_delivery_failure for the saved child report.'}, 'purpose': {'type': 'string'}, 'schema_json': {'type': 'string'}}))
    return _original_action_catalog._object({'selection': {'anyOf': options}, 'report_update': source.interpret_schema})

from gene_annotation_episode.episodic_workflow.root import action_catalog as _original_action_catalog
