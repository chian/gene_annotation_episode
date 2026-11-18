"""Prepare the original hpc resource work execution assignment and required typed return."""
from gene_annotation_episode.episodic_workflow.root.a101.runtime import ContractError, parse_json_object, validate_form, interpretation_schema

def prepare_commission(workflow, source, selection, index):
    scope = workflow.store.validate_scope(selection['scope'], parent_scope=source.scope)
    role = 'launch_hpc'
    schema, report_declaration = workflow.expanded_contract_form(source, selection, index, role)
    binding = workflow.episode_bindings.for_child(source.path, role)
    if binding.binding_path != 'resource_work_submission/hpc_resource_work_execution':
        raise ValueError('child_binding_path_conflict')
    required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(workflow.binding_context(source), role)
    sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
    for fact_source in required:
        if sources.count(fact_source) != 1:
            raise ContractError('child_return_requires_' + fact_source)
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')
    initial = parse_json_object(workflow.child_initial_report_input(source, selection, role))
    validate_form(initial, interpretation_schema(schema), lambda *_: True)
    specialist = workflow.specialist(source)
    allowed = workflow.available_child_roles(source) if workflow.annotation_child_roles is not None else specialist.allowed_children(workflow.binding_context(source), workflow.services.capabilities()) if specialist is not None else workflow.episode_bindings.entry_roles
    if role not in allowed:
        raise ValueError('child_role_not_available_to_parent')
    binding = workflow.episode_bindings.for_child(source.path, role)
    workflow.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
    child_assignment = selection['assignment']
    send_request = getattr(specialist, 'prepare_child_request', None)
    if send_request is not None:
        child_assignment = send_request(workflow.binding_context(source), role, child_assignment)
    episode_assignment = binding.prepare_assignment(workflow.binding_context(source), role, child_assignment, scope, f'{workflow.run_id}:{source.episode_id}:{index}')
    return {'scope': scope, 'role': role, 'schema': schema, 'report_declaration': report_declaration, 'initial': initial, 'episode_assignment': episode_assignment, 'sequence_homology_evidence': None, 'assignment': None}
