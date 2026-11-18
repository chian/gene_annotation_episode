from gene_annotation_episode.episodic_workflow.root.a103.goal import make_goal
from gene_annotation_episode.episodic_workflow.root.a103.method_loop.episode import Episode, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.a103.runtime import Record, _plain
from gene_annotation_episode.episodic_workflow.root.a103.episode_contract_information import ContractInformationError, validate_saved_fact_form

def assemble_request(self, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, gene_context_evidence=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    validate_path(path)
    goal = make_goal(name, goal_text, parent, contract)
    message = {'scope': scope, 'initial_report': initial or {}}
    if self.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': self.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise _live_original_runtime.ContractInformationError('report_contract_required_for_declaration')
        _live_original_runtime.validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _live_original_runtime._plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        self.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _live_original_runtime._plain(episode_assignment)
    if gene_context_evidence is not None:
        message['gene_context_evidence'] = _live_original_runtime._plain(gene_context_evidence)
    identity = _live_original_runtime.Episode.identity(self.context, self.grains[name], key, parent_path=parent_path)
    if self.gene_context_evidence_binding is not None:
        from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(self.run_id, path)
    if self.receipts is not None:
        parent_id = _live_original_runtime.Episode.identity(self.context, self.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = self.receipts.bind(identity.episode_id, parent_id)
    request = _live_original_runtime.EpisodeRequest(goal, _live_original_runtime.Record(message), contract)
    return (path, goal, message, identity, request)

def validate_path(path):
    if (not isinstance(path, (tuple, list)) or not path
            or any(not isinstance(part, (tuple, list)) or len(part) != 2
                   or any(not isinstance(value, str) or not value for value in part)
                   for part in path)
            or path[-1][0] != 'annotation' or len(path) != 1):
        raise ValueError('private_legacy_annotation_path_required')
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
