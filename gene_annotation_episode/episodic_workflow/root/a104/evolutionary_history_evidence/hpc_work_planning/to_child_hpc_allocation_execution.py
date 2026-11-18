"""Prepare this parent's allocation work with its original commission and owner."""
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj

TEXT = {'type': 'string', 'minLength': 1}


def assignment_schema(commissions):
    fields = {'commission_source_ref': {'type': 'string', 'format': 'reference'}}
    if commissions:
        fields['commission_id'] = {'type': 'string', 'enum': list(commissions)}
    required = []
    fields['owner_episode_id'] = TEXT
    required.append('owner_episode_id')
    schema = obj(fields, required=required)
    if commissions:
        schema['oneOf'] = [{'required': ['commission_id']}, {'required': ['commission_source_ref']}]
    else:
        schema['required'].append('commission_source_ref')
    return schema


def commission_identity(assignment):
    return {key: assignment[key] for key in ('commission_id', 'commission_source_ref') if key in assignment}


def prepare_request(parent, selection, commissions):
    selection = plain(selection)
    validate_schema(selection, assignment_schema(commissions))
    if parent.role != 'hpc' or selection['owner_episode_id'] != parent.episode_id or commission_identity(selection) != commission_identity(parent.assignment):
        raise ValueError('prediction_or_execution_must_belong_to_its_original_hpc_parent')
    return selection


from gene_annotation_episode.episodic_workflow.root.a104.runtime import EpisodeGoal, Episode, EpisodeRequest, Record, _plain
from gene_annotation_episode.episodic_workflow.root.a104.episode_contract_information import ContractInformationError, validate_saved_fact_form

def assemble_request(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, evolutionary_history_evidence=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    goal = EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
    message = {'scope': scope, 'initial_report': initial or {}}
    if workflow.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': workflow.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise ContractInformationError('report_contract_required_for_declaration')
        validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        workflow.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _plain(episode_assignment)
    if evolutionary_history_evidence is not None:
        message['evolutionary_history_evidence'] = _plain(evolutionary_history_evidence)
    identity = Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    workflow.evolutionary_history_evidence_binding is not None and name in {'annotation', 'evolutionary_history_evidence'}
    if workflow.receipts is not None:
        parent_id = Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (path, goal, message, identity, request)
