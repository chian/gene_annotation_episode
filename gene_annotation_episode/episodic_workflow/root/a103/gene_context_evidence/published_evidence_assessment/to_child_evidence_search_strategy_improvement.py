"""Assemble the original evidence search strategy improvement child request."""
from gene_annotation_episode.episodic_workflow.root.a103.runtime import EpisodeGoal, Episode, EpisodeRequest, Record, _plain
from gene_annotation_episode.episodic_workflow.root.a103.episode_contract_information import ContractInformationError, validate_saved_fact_form

class EvidenceSearchStrategyImprovementRequest:


    def _assemble_evidence_search_strategy_improvement_request(self, workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, gene_context_evidence=None, report_contract_declaration=None):
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
        if gene_context_evidence is not None:
            message['gene_context_evidence'] = _live_original_runtime._plain(gene_context_evidence)
        identity = _live_original_runtime.Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
        if workflow.receipts is not None:
            parent_id = _live_original_runtime.Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
            message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
        request = _live_original_runtime.EpisodeRequest(goal, _live_original_runtime.Record(message), contract)
        return (path, goal, message, identity, request)
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
