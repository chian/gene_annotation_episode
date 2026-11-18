from __future__ import annotations
from . import runtime as _original_runtime

def prepare_request(self, source, selection, index, scope, role):
    episode_assignment = None
    partner_presence_evidence = None
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
        if binding is self.partner_presence_evidence_binding:
            closed = {}
            recorded = self.journal.row('runtime_actions', source.episode_id, index)
            if recorded is not None and recorded['result'] is not None and (_original_runtime._json(_original_runtime.json.loads(recorded['action'])) == _original_runtime._json(selection)) and (_original_runtime.json.loads(recorded['result']).get('status') == 'completed'):
                from gene_annotation_episode.episodic_workflow.root.a107.episode_return_records import EpisodeReturnRecords
                child_id = _original_runtime.Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path).episode_id
                if self.journal.row('runtime_episodes', child_id) is not None:
                    records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='scientific_closed_')
                    candidate = records.context(child_id)
                    read_closed = getattr(self.services, 'scientific_closed_request', None)
                    if callable(read_closed) and read_closed(candidate) is not None:
                        closed['closed_context'] = candidate
            prepared = binding.prepare_invocation(self.binding_context(source), role, selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}', invocation={'objective': selection['goal'], 'purpose': selection['purpose'], 'report_schema': schema, 'initial_report': initial}, **closed)
            episode_assignment = prepared['assignment']
            partner_presence_evidence = prepared['partner_presence_evidence']
        else:
            child_assignment = selection['assignment']
            send_request = getattr(specialist, 'prepare_child_request', None)
            if send_request is not None:
                child_assignment = send_request(self.binding_context(source), role, child_assignment)
            elif specialist is None and len(source.path) == 1 and (source.path[0][0] == 'annotation'):
                if role == 'launch':
                    from gene_annotation_episode.episodic_workflow.root.a107.to_child_execution_job_submission import prepare_request
                    child_assignment = prepare_request(source, child_assignment)
                elif role == 'results':
                    from gene_annotation_episode.episodic_workflow.root.a107.to_child_execution_result_acquisition import prepare_request
                    child_assignment = prepare_request(source, child_assignment)
            episode_assignment = binding.prepare_assignment(self.binding_context(source), role, child_assignment, scope, f'{self.run_id}:{source.episode_id}:{index}')
    assignment = self.job_episodes.assign(self.store, role, selection, scope, operation_key=f'{self.run_id}:{source.episode_id}:{index}') if selection['kind'] == 'job_child' else None
    return (schema, report_declaration, initial, episode_assignment, partner_presence_evidence, assignment)
