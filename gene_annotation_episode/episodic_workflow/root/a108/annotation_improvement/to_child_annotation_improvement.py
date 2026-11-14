from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime

def assemble_request(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    goal = _original_runtime.EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else _original_runtime.EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
    message = {'scope': scope, 'initial_report': initial or {}}
    if workflow.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': workflow.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise _original_runtime.ContractInformationError('report_contract_required_for_declaration')
        _original_runtime.validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _original_runtime._plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        workflow.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _original_runtime._plain(episode_assignment)
    if scientific_process is not None:
        message['scientific_process'] = _original_runtime._plain(scientific_process)
    identity = _original_runtime.Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    if workflow.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(workflow.run_id, path)
    if workflow.receipts is not None:
        parent_id = _original_runtime.Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = _original_runtime.EpisodeRequest(goal, _original_runtime.Record(message), contract)
    return (path, goal, message, identity, request)

def prepare_request(self, source, selection, index, scope, role):
    episode_assignment = None
    scientific_process = None
    schema, report_declaration = self.expanded_contract_form(source, selection, index, role)
    if selection['kind'] == 'episode_child':
        binding = self.episode_bindings.for_child(source.path, role)
        required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(self.binding_context(source), role)
        sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
        for fact_source in required:
            if sources.count(fact_source) != 1:
                raise _original_runtime.ContractError('child_return_requires_' + fact_source)
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise _original_runtime.ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')
    initial = _original_runtime.parse_json_object(self.child_initial_report_input(source, selection, role))
    if selection['kind'] == 'episode_child':
        _original_runtime.validate_form(initial, _original_runtime.interpretation_schema(schema), lambda *_: True)
    else:
        _original_runtime.validate_form(initial, _original_runtime.interpretation_schema(schema), self.resolver(scope, grain=role))
        self.validate_report(initial, scope, grain=role, schema=_original_runtime.interpretation_schema(schema))
    if selection['kind'] == 'episode_child':
        specialist = self.specialist(source)
        allowed = self.available_child_roles(source) if self.annotation_child_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
        if role not in allowed:
            raise ValueError('child_role_not_available_to_parent')
        binding = self.episode_bindings.for_child(source.path, role)
        self.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
        if binding is self.scientific_process_binding:
            closed = {}
            recorded = self.journal.row('runtime_actions', source.episode_id, index)
            if recorded is not None and recorded['result'] is not None and (_original_runtime._json(_original_runtime.json.loads(recorded['action'])) == _original_runtime._json(selection)) and (_original_runtime.json.loads(recorded['result']).get('status') == 'completed'):
                from gene_annotation_episode.episodic_workflow.root.a108.episode_return_records import EpisodeReturnRecords
                child_id = _original_runtime.Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path).episode_id
                if self.journal.row('runtime_episodes', child_id) is not None:
                    records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='scientific_closed_')
                    candidate = records.context(child_id)
                    read_closed = getattr(self.services, 'scientific_closed_request', None)
                    if callable(read_closed) and read_closed(candidate) is not None:
                        closed['closed_context'] = candidate
            prepared = binding.prepare_invocation(self.binding_context(source), role, selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}', invocation={'objective': selection['goal'], 'purpose': selection['purpose'], 'report_schema': schema, 'initial_report': initial}, **closed)
            episode_assignment = prepared['assignment']
            scientific_process = prepared['scientific_process']
        else:
            episode_assignment = binding.prepare_assignment(self.binding_context(source), role, selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}')
    assignment = self.job_episodes.assign(self.store, role, selection, scope, operation_key=f'{self.run_id}:{source.episode_id}:{index}') if selection['kind'] == 'job_child' else None
    return (schema, report_declaration, initial, episode_assignment, scientific_process, assignment)
