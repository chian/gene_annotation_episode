"""A104 original implicit improvement responsibility."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def prepare_parent_request(self, source, selection, index, scope, role):
    _parent_specialist_assigned = False
    episode_assignment = None
    evolutionary_history_evidence = None
    schema, report_declaration = self.expanded_contract_form(source, selection, index, role)
    if selection['kind'] == 'episode_child':
        binding = self.episode_bindings.for_child(source.path, role)
        required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(self.binding_context(source), role)
        sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
        for fact_source in required:
            if sources.count(fact_source) != 1:
                raise ContractError('child_return_requires_' + fact_source)
    hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
    if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
        raise ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')
    initial = parse_json_object(self.child_initial_report_input(source, selection, role))
    if selection['kind'] == 'episode_child':
        validate_form(initial, interpretation_schema(schema), lambda *_: True)
    else:
        validate_form(initial, interpretation_schema(schema), self.resolver(scope, grain=role))
        self.validate_report(initial, scope, grain=role, schema=interpretation_schema(schema))
    if selection['kind'] == 'episode_child':
        specialist = self.specialist(source)
        _parent_specialist_assigned = True
        allowed = self.available_child_roles(source) if self.annotation_child_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
        if role not in allowed:
            raise ValueError('child_role_not_available_to_parent')
        binding = self.episode_bindings.for_child(source.path, role)
        self.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
        if binding is self.evolutionary_history_evidence_binding:
            closed = {}
            recorded = self.journal.row('runtime_actions', source.episode_id, index)
            if recorded is not None and recorded['result'] is not None and (_json(json.loads(recorded['action'])) == _json(selection)) and (json.loads(recorded['result']).get('status') == 'completed'):
                from .episode_return_records import EpisodeReturnRecords
                child_id = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path).episode_id
                if self.journal.row('runtime_episodes', child_id) is not None:
                    records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='scientific_closed_')
                    candidate = records.context(child_id)
                    read_closed = getattr(self.services, 'scientific_closed_request', None)
                    if callable(read_closed) and read_closed(candidate) is not None:
                        closed['closed_context'] = candidate
            prepared = binding.prepare_invocation(self.binding_context(source), role, selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}', invocation={'objective': selection['goal'], 'purpose': selection['purpose'], 'report_schema': schema, 'initial_report': initial}, **closed)
            episode_assignment = prepared['assignment']
            evolutionary_history_evidence = prepared['evolutionary_history_evidence']
        else:
            child_assignment = selection['assignment']
            send_request = getattr(specialist, 'prepare_child_request', None)
            if send_request is not None:
                child_assignment = send_request(self.binding_context(source), role, child_assignment)
            episode_assignment = binding.prepare_assignment(self.binding_context(source), role, child_assignment, scope, f'{self.run_id}:{source.episode_id}:{index}')
    assignment = self.job_episodes.assign(self.store, role, selection, scope, operation_key=f'{self.run_id}:{source.episode_id}:{index}') if selection['kind'] == 'job_child' else None
    return {'schema': schema, 'report_declaration': report_declaration, 'initial': initial, 'episode_assignment': episode_assignment, 'evolutionary_history_evidence': evolutionary_history_evidence, 'assignment': assignment, **({'specialist': specialist} if _parent_specialist_assigned else {})}

def assemble_parent_request(self, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, evolutionary_history_evidence=None, report_contract_declaration=None, request_assembler=None):
    path = (*parent_path, (name, key))
    from .annotation_improvement.goal import prepare_goal
    goal = prepare_goal(name, goal_text, parent, contract)
    message = {'scope': scope, 'initial_report': initial or {}}
    if self.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': self.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise ContractInformationError('report_contract_required_for_declaration')
        validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        self.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _plain(episode_assignment)
    if evolutionary_history_evidence is not None:
        message['evolutionary_history_evidence'] = _plain(evolutionary_history_evidence)
    identity = Episode.identity(self.context, self.grains[name], key, parent_path=parent_path)
    if self.evolutionary_history_evidence_binding is not None and name in {'annotation', 'evolutionary_history_evidence'}:
        from .evolutionary_history_evidence_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(self.run_id, path)
    if self.receipts is not None:
        parent_id = Episode.identity(self.context, self.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = self.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (path, goal, message, identity, request)

def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['prepare_parent_request', 'assemble_parent_request']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'prepare_parent_request': 'prepare_parent_request', 'assemble_parent_request': 'assemble_parent_request'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
