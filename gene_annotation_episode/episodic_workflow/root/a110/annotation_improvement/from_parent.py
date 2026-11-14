from __future__ import annotations
from .. import runtime as _original_runtime

def assemble_request(self, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
    from gene_annotation_episode.episodic_workflow.root.a110.annotation_improvement.goal import improvement_goal
    path = (*parent_path, (name, key))
    goal = improvement_goal(parent, goal_text, name, contract)
    message = {'scope': scope, 'initial_report': initial or {}}
    if self.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': self.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise _original_runtime.ContractInformationError('report_contract_required_for_declaration')
        _original_runtime.validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _original_runtime._plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        self.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _original_runtime._plain(episode_assignment)
    if scientific_process is not None:
        message['scientific_process'] = _original_runtime._plain(scientific_process)
    identity = _original_runtime.Episode.identity(self.context, self.grains[name], key, parent_path=parent_path)
    if self.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a110.scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(self.run_id, path)
    if self.receipts is not None:
        parent_id = _original_runtime.Episode.identity(self.context, self.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = self.receipts.bind(identity.episode_id, parent_id)
    request = _original_runtime.EpisodeRequest(goal, _original_runtime.Record(message), contract)
    return (path, goal, message, identity, request)
