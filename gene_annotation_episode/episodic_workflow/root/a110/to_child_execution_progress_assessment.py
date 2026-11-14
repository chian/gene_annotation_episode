"""Original A110 annotation request envelope for execution_progress_assessment."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _original_runtime

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
        from .scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(workflow.run_id, path)
    if workflow.receipts is not None:
        parent_id = _original_runtime.Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = _original_runtime.EpisodeRequest(goal, _original_runtime.Record(message), contract)
    return (path, goal, message, identity, request)
