"""Prepare this parent's original child question, typed result, custody and request."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.runtime import ContractInformationError, Episode, EpisodeGoal, EpisodeRequest, Record, _plain, validate_saved_fact_form

def assemble_request(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    goal = _live_original_runtime.EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else _live_original_runtime.EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
    message = {'scope': scope, 'initial_report': initial or {}}
    if workflow.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': workflow.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise _live_original_runtime.ContractInformationError('report_contract_required_for_declaration')
        _live_original_runtime.validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _live_original_runtime._plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        workflow.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _live_original_runtime._plain(episode_assignment)
    if scientific_process is not None:
        message['scientific_process'] = _live_original_runtime._plain(scientific_process)
    identity = _live_original_runtime.Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    if workflow.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a102.scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(workflow.run_id, path)
    if workflow.receipts is not None:
        parent_id = _live_original_runtime.Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = _live_original_runtime.EpisodeRequest(goal, _live_original_runtime.Record(message), contract)
    return (path, goal, message, identity, request)

from . import runtime as _runtime

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
            from .episode_return_records import EpisodeReturnRecords
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
from gene_annotation_episode.episodic_workflow.root.a102 import runtime as _live_original_runtime
