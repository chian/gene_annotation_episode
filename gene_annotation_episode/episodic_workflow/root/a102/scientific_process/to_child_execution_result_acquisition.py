"""Original A102 scientific_process/parent exchange with execution_result_acquisition."""
from __future__ import annotations
from .. import runtime as _runtime

def prepare_request(self, source, selection, index, scope, role):
    episode_assignment = None
    scientific_process = None
    schema, report_declaration = self.expanded_contract_form(source, selection, index, role)
    binding = self.episode_bindings.for_child(source.path, role)
    required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(self.binding_context(source), role)
    sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
    for fact_source in required:
        if sources.count(fact_source) != 1:
            raise _runtime.ContractError('child_return_requires_' + fact_source)
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise _runtime.ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')
    initial = _runtime.parse_json_object(self.child_initial_report_input(source, selection, role))
    _runtime.validate_form(initial, _runtime.interpretation_schema(schema), lambda *_: True)
    specialist = self.specialist(source)
    allowed = self.available_child_roles(source) if self.annotation_child_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
    if role not in allowed:
        raise ValueError('child_role_not_available_to_parent')
    binding = self.episode_bindings.for_child(source.path, role)
    self.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
    if binding is self.scientific_process_binding:
        closed = {}
        recorded = self.journal.row('runtime_actions', source.episode_id, index)
        if recorded is not None and recorded['result'] is not None and (_runtime._json(_runtime.json.loads(recorded['action'])) == _runtime._json(selection)) and (_runtime.json.loads(recorded['result']).get('status') == 'completed'):
            from ..episode_return_records import EpisodeReturnRecords
            child_id = _runtime.Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path).episode_id
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
        child_assignment = selection['assignment']
        send_request = getattr(specialist, 'prepare_child_request', None)
        if send_request is not None:
            child_assignment = send_request(self.binding_context(source), role, child_assignment)
        episode_assignment = binding.prepare_assignment(self.binding_context(source), role, child_assignment, scope, f'{self.run_id}:{source.episode_id}:{index}')
    assignment = None
    return schema, report_declaration, initial, episode_assignment, scientific_process, assignment, specialist, binding
