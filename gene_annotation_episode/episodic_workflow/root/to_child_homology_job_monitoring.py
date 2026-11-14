from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.communication import interpretation_schema
from gene_annotation_episode.episodic_workflow.root.boundary_validation import parse_json_object
from gene_annotation_episode.episodic_workflow.root.communication import validate_form

def prepare_request(workflow, source, selection, index, scope, role, selected_owner):
    episode_assignment = None
    scientific_process = None
    schema, report_declaration = workflow.expanded_contract_form(source, selection, index, role, owner=selected_owner)
    if selection['kind'] == 'episode_child':
        binding = workflow.episode_bindings.for_child(source.path, role, owner=selected_owner)
        required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(workflow.binding_context(source), role)
        sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
        for fact_source in required:
            if sources.count(fact_source) != 1:
                raise _request_runtime.ContractError('child_return_requires_' + fact_source)
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise _request_runtime.ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')
    initial = _request_runtime.parse_json_object(workflow.child_initial_report_input(source, selection, role))
    if selection['kind'] == 'episode_child':
        _request_runtime.validate_form(initial, _request_runtime.interpretation_schema(schema), lambda *_: True)
    else:
        _request_runtime.validate_form(initial, _request_runtime.interpretation_schema(schema), workflow.resolver(scope, grain=role))
        workflow.validate_report(initial, scope, grain=role, schema=_request_runtime.interpretation_schema(schema))
    if selection['kind'] == 'episode_child':
        specialist = workflow.specialist(source)
        allowed = workflow.available_child_roles(source) if workflow.annotation_child_roles is not None else specialist.allowed_children(workflow.binding_context(source), workflow.services.capabilities()) if specialist is not None else workflow.episode_bindings.entry_roles
        if role not in allowed:
            raise ValueError('child_role_not_available_to_parent')
        binding = workflow.episode_bindings.for_child(source.path, role, owner=selected_owner)
        workflow.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
        if binding is (workflow.episode_bindings.for_role('scientific_process', owner=selected_owner) if 'scientific_process' in workflow.episode_bindings.roles else None):
            closed = {}
            recorded = workflow.journal.row('runtime_actions', source.episode_id, index)
            if recorded is not None and recorded['result'] is not None and (_request_runtime._json(_request_runtime.json.loads(recorded['action'])) == _request_runtime._json(selection)) and (_request_runtime.json.loads(recorded['result']).get('status') == 'completed'):
                from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
                child_id = _request_runtime.Episode.identity(workflow.context, workflow.grains[role], f'child_{index}', parent_path=source.path).episode_id
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
            episode_assignment = binding.prepare_assignment(workflow.binding_context(source), role, selection['assignment'], scope, f'{workflow.run_id}:{source.episode_id}:{index}')
    if selection['kind'] == 'job_child':
        _assignment_jobs = workflow.job_episodes
        from gene_annotation_episode.episodic_workflow.root.library.homology_episode_family import HomologyEpisodes as _CurrentHomology
        if type(_assignment_jobs) is _CurrentHomology:
            assignment = _assignment_jobs.implementation_for_path(source.path, child_role=role).assign(workflow.store, role, selection, scope, operation_key=f'{workflow.run_id}:{source.episode_id}:{index}')
        else:
            assignment = _assignment_jobs.assign(workflow.store, role, selection, scope, operation_key=f'{workflow.run_id}:{source.episode_id}:{index}')
    else:
        assignment = None
    return (schema, report_declaration, initial, episode_assignment, scientific_process, assignment)

from gene_annotation_episode.episodic_workflow.root import action_execution as _request_runtime
