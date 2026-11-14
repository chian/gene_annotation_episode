"""Actual A103 parent request/admission responsibility; original late predicates retained."""
from __future__ import annotations

def prepare_request(self, source, selection, index, scope, role):
    episode_assignment = None
    scientific_process = None
    schema, report_declaration = self.expanded_contract_form(source, selection, index, role)
    if selection['kind'] == 'episode_child':
        binding = self.episode_bindings.for_child(source.path, role)
        required = _get_getattr()(binding, 'required_return_sources', lambda _parent, _role: ())(self.binding_context(source), role)
        sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
        for fact_source in required:
            if sources.count(fact_source) != 1:
                raise _get_ContractError()('child_return_requires_' + fact_source)
    from gene_annotation_episode.episodic_workflow.root.a103.library.hpc_handoff_report_contract import validate_hpc_launch_report_contract
    hpc_launch = validate_hpc_launch_report_contract(source, role, schema)
    initial = _get_parse_json_object()(self.child_initial_report_input(source, selection, role))
    if selection['kind'] == 'episode_child':
        _get_validate_form()(initial, _get_interpretation_schema()(schema), lambda *_: True)
    else:
        _get_validate_form()(initial, _get_interpretation_schema()(schema), self.resolver(scope, grain=role))
        self.validate_report(initial, scope, grain=role, schema=_get_interpretation_schema()(schema))
    if selection['kind'] == 'episode_child':
        specialist = self.specialist(source)
        allowed = self.available_child_roles(source) if self.annotation_child_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
        if role not in allowed:
            raise _get_ValueError()('child_role_not_available_to_parent')
        binding = self.episode_bindings.for_child(source.path, role)
        self.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
        if binding is self.scientific_process_binding:
            closed = {}
            recorded = self.journal.row('runtime_actions', source.episode_id, index)
            if recorded is not None and recorded['result'] is not None and (_get__json()(_get_json().loads(recorded['action'])) == _get__json()(selection)) and (_get_json().loads(recorded['result']).get('status') == 'completed'):
                from gene_annotation_episode.episodic_workflow.root.a103.episode_return_records import EpisodeReturnRecords
                child_id = _get_Episode().identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path).episode_id
                if self.journal.row('runtime_episodes', child_id) is not None:
                    records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='scientific_closed_')
                    candidate = records.context(child_id)
                    read_closed = _get_getattr()(self.services, 'scientific_closed_request', None)
                    if _get_callable()(read_closed) and read_closed(candidate) is not None:
                        closed['closed_context'] = candidate
            prepared = binding.prepare_invocation(self.binding_context(source), role, selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}', invocation={'objective': selection['goal'], 'purpose': selection['purpose'], 'report_schema': schema, 'initial_report': initial}, **closed)
            episode_assignment = prepared['assignment']
            scientific_process = prepared['scientific_process']
        else:
            child_assignment = selection['assignment']
            send_request = _get_getattr()(specialist, 'prepare_child_request', None)
            if send_request is not None:
                child_assignment = send_request(self.binding_context(source), role, child_assignment)
            episode_assignment = binding.prepare_assignment(self.binding_context(source), role, child_assignment, scope, f'{self.run_id}:{source.episode_id}:{index}')
    assignment = self.job_episode_for_child(source.path, role).assign(self.store, role, selection, scope, operation_key=f'{self.run_id}:{source.episode_id}:{index}') if selection['kind'] == 'job_child' else None
    request_locals = locals()
    bound = {name: request_locals[name] for name in ('specialist', 'binding') if name in request_locals}
    return (schema, report_declaration, initial, episode_assignment, scientific_process, assignment, bound)
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _parent_name_ContractError as _get_ContractError, _parent_name_Episode as _get_Episode, _parent_name_ValueError as _get_ValueError, _parent_name__json as _get__json, _parent_name_any as _get_any, _parent_name_callable as _get_callable, _parent_name_getattr as _get_getattr, _parent_name_interpretation_schema as _get_interpretation_schema, _parent_name_json as _get_json, _parent_name_parse_json_object as _get_parse_json_object, _parent_name_validate_form as _get_validate_form
