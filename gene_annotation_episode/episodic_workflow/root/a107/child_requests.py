"""Original private A107 annotation child_requests responsibility."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107 import runtime as _original_runtime

def prepare_child_request(workflow, source, selection, index, scope, role):
    episode_assignment = None
    scientific_process = None
    schema, report_declaration = workflow.expanded_contract_form(source, selection, index, role)
    if selection['kind'] == 'episode_child':
        binding = workflow.episode_bindings.for_child(source.path, role)
        required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(workflow.binding_context(source), role)
        sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
        for fact_source in required:
            if sources.count(fact_source) != 1:
                raise _original_runtime.ContractError('child_return_requires_' + fact_source)
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        pass
    initial = _original_runtime.parse_json_object(workflow.child_initial_report_input(source, selection, role))
    if selection['kind'] == 'episode_child':
        _original_runtime.validate_form(initial, _original_runtime.interpretation_schema(schema), lambda *_: True)
    if selection['kind'] == 'episode_child':
        specialist = workflow.specialist(source)
        allowed = workflow.available_child_roles(source) if workflow.annotation_child_roles is not None else specialist.allowed_children(workflow.binding_context(source), workflow.services.capabilities()) if specialist is not None else workflow.episode_bindings.entry_roles
        if role not in allowed:
            raise ValueError('child_role_not_available_to_parent')
        binding = workflow.episode_bindings.for_child(source.path, role)
        workflow.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
        if binding is workflow.scientific_process_binding:
            closed = {}
            recorded = workflow.journal.row('runtime_actions', source.episode_id, index)
            if recorded is not None and recorded['result'] is not None and (_original_runtime._json(_original_runtime.json.loads(recorded['action'])) == _original_runtime._json(selection)) and (_original_runtime.json.loads(recorded['result']).get('status') == 'completed'):
                from .episode_return_records import EpisodeReturnRecords
                child_id = _original_runtime.Episode.identity(workflow.context, workflow.grains[role], f'child_{index}', parent_path=source.path).episode_id
                if workflow.journal.row('runtime_episodes', child_id) is not None:
                    records = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='scientific_closed_')
                    candidate = records.context(child_id)
                    read_closed = getattr(workflow.services, 'scientific_closed_request', None)
                    if callable(read_closed) and read_closed(candidate) is not None:
                        closed['closed_context'] = candidate
            prepared = binding.prepare_invocation(workflow.binding_context(source), role, selection['assignment'], scope, f'{workflow.run_id}:{source.episode_id}:{index}', invocation={'objective': selection['goal'], 'purpose': selection['purpose'], 'report_schema': schema, 'initial_report': initial}, **closed)
            episode_assignment = prepared['assignment']
            scientific_process = prepared['scientific_process']
        else:
            child_assignment = selection['assignment']
            send_request = getattr(specialist, 'prepare_child_request', None)
            if send_request is not None:
                child_assignment = send_request(workflow.binding_context(source), role, child_assignment)
            elif specialist is None and len(source.path) == 1 and (source.path[0][0] == 'annotation'):
                if role == 'launch':
                    from .to_child_execution_job_submission import prepare_request
                    child_assignment = prepare_request(source, child_assignment)
                elif role == 'results':
                    from .to_child_execution_result_acquisition import prepare_request
                    child_assignment = prepare_request(source, child_assignment)
            episode_assignment = binding.prepare_assignment(workflow.binding_context(source), role, child_assignment, scope, f'{workflow.run_id}:{source.episode_id}:{index}')
    assignment = None if selection['kind'] == 'job_child' else None
    return (schema, report_declaration, initial, episode_assignment, scientific_process, assignment)
