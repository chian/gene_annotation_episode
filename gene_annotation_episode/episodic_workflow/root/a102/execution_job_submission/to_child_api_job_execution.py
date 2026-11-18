"""Private A102 gene_annotation_episode/episodic_workflow/root/a102/execution_job_submission outgoing launch_api request envelope.

The selected child owns admission; this parent owns its immutable request.
Transport identity, inherited references and report-declaration callbacks retain
the original runtime lookup and order.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102 import runtime as _runtime


def assemble_request(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, structural_homology_evidence=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    goal = _runtime.EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else _runtime.EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
    message = {'scope': scope, 'initial_report': initial or {}}
    if workflow.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': workflow.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise _runtime.ContractInformationError('report_contract_required_for_declaration')
        _runtime.validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _runtime._plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        workflow.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _runtime._plain(episode_assignment)
    if structural_homology_evidence is not None:
        message['structural_homology_evidence'] = _runtime._plain(structural_homology_evidence)
    identity = _runtime.Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    if workflow.receipts is not None:
        parent_id = _runtime.Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = _runtime.EpisodeRequest(goal, _runtime.Record(message), contract)
    return path, goal, message, identity, request
