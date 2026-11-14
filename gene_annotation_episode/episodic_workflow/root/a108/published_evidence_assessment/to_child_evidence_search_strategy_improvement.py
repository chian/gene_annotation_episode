from __future__ import annotations
"Prepare this parent's scoped evidence search strategy improvement commission and typed return."
from gene_annotation_episode.episodic_workflow.root.a108.runtime import ContractError, parse_json_object, validate_form, interpretation_schema

def prepare_request(workflow, source, selection, index):
    scope = workflow.store.validate_scope(selection['scope'], parent_scope=source.scope)
    role = 'literature_strategy'
    schema, report_declaration = workflow.expanded_contract_form(source, selection, index, role)
    binding = workflow.episode_bindings.for_child(source.path, role)
    required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(workflow.binding_context(source), role)
    sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
    for fact_source in required:
        if sources.count(fact_source) != 1:
            raise _original_runtime.ContractError('child_return_requires_' + fact_source)
    initial = _original_runtime.parse_json_object(workflow.child_initial_report_input(source, selection, role))
    _original_runtime.validate_form(initial, _original_runtime.interpretation_schema(schema), lambda *_: True)
    specialist = workflow.specialist(source)
    allowed = workflow.available_child_roles(source) if workflow.annotation_child_roles is not None else specialist.allowed_children(workflow.binding_context(source), workflow.services.capabilities()) if specialist is not None else workflow.episode_bindings.entry_roles
    if role not in allowed:
        raise ValueError('child_role_not_available_to_parent')
    binding = workflow.episode_bindings.for_child(source.path, role)
    workflow.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
    episode_assignment = binding.prepare_assignment(workflow.binding_context(source), role, selection['assignment'], scope, f'{workflow.run_id}:{source.episode_id}:{index}')
    return {'scope': scope, 'role': role, 'schema': schema, 'report_declaration': report_declaration, 'initial': initial, 'episode_assignment': episode_assignment, 'scientific_process': None, 'assignment': None}
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime
