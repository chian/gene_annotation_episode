"""A106 original library/episode_request_envelope defining responsibilities."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def assemble_request(self, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, perturbation_evidence=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    from .annotation_improvement.episode import goal_preparer
    _improvement_goal = goal_preparer(self, name, parent_path)
    if _improvement_goal is None:
        from .goal import prepare_goal
        goal = prepare_goal(name, goal_text, parent, contract)
    else:
        goal = _improvement_goal(name, goal_text, parent, contract)
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
    if perturbation_evidence is not None:
        message['perturbation_evidence'] = _plain(perturbation_evidence)
    identity = Episode.identity(self.context, self.grains[name], key, parent_path=parent_path)
    if self.perturbation_evidence_binding is not None and name in {'annotation', 'perturbation_evidence'}:
        from .perturbation_evidence_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(self.run_id, path)
    if self.receipts is not None:
        parent_id = Episode.identity(self.context, self.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = self.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (path, goal, message, identity, request)

def _bind_original_runtime(namespace):
    names = {'assemble_request': 'assemble_request'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names}, runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names, defining_module='gene_annotation_episode.episodic_workflow.root.a106.library.episode_request_envelope'))
from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
