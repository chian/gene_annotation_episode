"""Private to child execution job submission for A104 hpc_execution."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.hpc_ledger import HPCLedger
from pathlib import Path
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104 import hpc_queue
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain



def authenticate_launch(parent, selection, operation_key, directory):
    """Only the exact planned launch may consume the original allocation slot."""
    owner = parent.assignment['owner_episode_id'] if parent.role == 'hpc_execution' else parent.episode_id
    ledger = HPCLedger.open_existing(Path(directory)/'hpc'/hpc_queue.digest([parent.run_id, owner]))
    matching = [row for row in ledger.records('plan') if row['body']['launch_assignment'] == plain(selection)]
    if len(matching) != 1 or ledger.read('owner')['scope'] != plain(parent.scope):
        raise ValueError('hpc_launch_must_match_original_planned_portfolio')
    plan = matching[0]['body']
    identity = 'launch:'+plan['plan_id']
    reservation = {'operation_key': operation_key, 'plan_id': plan['plan_id']}
    if any(row['id'] == identity for row in ledger.records('launch_commission')):
        # Completed parent actions still reconstruct their original child after
        # result collection closes the allocation. Authenticate that exact
        # reservation; a different action cannot use it to launch again.
        ledger.put('launch_commission', reservation, identity=identity)
        return
    if any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('hpc_allocation_already_closed')
    ledger.put('launch_commission', reservation, identity=identity)

class LaunchPreparation:
    def initial_decision_context(self, context):
        """Supply actual job inputs and acceptance, without a setup recipe."""
        if context.role not in ('launch', 'launch_hpc'):
            return {}
        from gene_annotation_episode.episodic_workflow.root.a104.method_loop.identities import EpisodeRef
        prefixes = [context.path[:i+1] for i, part in enumerate(context.path) if part[0] == 'hpc']
        if not prefixes:
            return {}
        # Runtime paths contain scope keys; compute the actual episode ID.
        owner = EpisodeRef(context.run_id, prefixes[-1]).episode_id
        ledger = HPCLedger.open_existing(self.directory/'hpc'/hpc_queue.digest([context.run_id, owner]))
        selected = plain(context.assignment)
        key = 'launch_assignment' if context.role == 'launch' else 'practical_assignment'
        plans = [row['body'] for row in ledger.records('plan') if row['body'][key] == selected]
        if len(plans) != 1 or ledger.read('owner')['scope'] != plain(context.scope):
            raise ValueError('hpc_launch_preparation_identity_conflict')
        plan = plans[0]
        from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable
        input_directory=ledger.path.parent/'launch-inputs'
        input_directory.mkdir(exist_ok=True)
        input_path=input_directory/(plan['plan_id']+'.json')
        _immutable(input_path,plan)
        return {'hpc_execution_job': {'plan_id':plan['plan_id'],
            'objective':ledger.commission['objective'],
            'scientific_manifest':deepcopy(plan['manifest']),
            'scientific_acceptance':deepcopy(ledger.commission['obligations']),
            'supplied_input_file':str(input_path.resolve()),
            'coordinator_workspace':str(self.directory.resolve()),
            'instructions':'The supplied local input file contains the frozen scientific manifest '
                'and reference source files. Use general terminal commands on the coordinator or '
                'assigned resource as needed; choose your scripts, environment and transfer method. '
                'Do not transcribe supplied source code into a child goal. Reference implementation '
                'files are available inputs, not a required execution procedure. Preserve original '
                'unit identities, scientific inputs, output/progress formats and acceptance predicates. '
                'Run computation in the actual allocation and retain its original identity. '
                'An uncertain submission must be investigated rather than duplicated.'}}


from gene_annotation_episode.episodic_workflow.root.a104.runtime import EpisodeGoal, Episode, EpisodeRequest, Record, _plain
from gene_annotation_episode.episodic_workflow.root.a104.episode_contract_information import ContractInformationError, validate_saved_fact_form

def assemble_request(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
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
    if scientific_process is not None:
        message['scientific_process'] = _plain(scientific_process)
    identity = Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    workflow.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}
    if workflow.receipts is not None:
        parent_id = Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (path, goal, message, identity, request)
