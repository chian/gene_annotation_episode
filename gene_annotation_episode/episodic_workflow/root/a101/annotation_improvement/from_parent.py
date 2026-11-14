"""Original A101 iterative annotation-improvement from_parent responsibility."""

def assemble_request(self, name, key, goal_text, scope, path, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
    from .annotation_improvement.goal import commissioned_goal
    goal = commissioned_goal(parent, goal_text, name, contract)
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
    if scientific_process is not None:
        message['scientific_process'] = _plain(scientific_process)
    identity = Episode.identity(self.context, self.grains[name], key, parent_path=parent_path)
    if self.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
        from .scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(self.run_id, path)
    if self.receipts is not None:
        parent_id = Episode.identity(self.context, self.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = self.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (goal, message, identity, request)

def __init__(self, workflow, path, request, scope):
    self.workflow, self.path, self.request, self.scope = (workflow, path, request, scope)
    self.episode_id = Episode.identity(workflow.context, workflow.grains[path[-1][0]], path[-1][1], parent_path=path[:-1]).episode_id
    self.calls = 0
    self.feedback = None
    self.last_outcome = None
    self.last_outcome_index = None
    self.report_values = _plain(request.message.as_record()['initial_report'])
    self.report_basis = []
    self._restored = False
    self._unfinished_own_actions = []
    self._source_revision = None
    self._latest_effect_index = None
    self._restored_source_state = None
    self._model_snapshot = None
    self._presented_conversation_key = None
    self._selection_view = None
    self._delivery_resolution_ref = None
    self._execution_context = None
    self._suspension_condition = None
    self._inprocess_replay_ready = False
    self.interpret_schema = interpretation_schema(request.report_contract.schema) if request.report_contract else _object({})

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('assemble_request',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'assemble_request': 'assemble_request'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.annotation_improvement.from_parent')
    globals().update(selected)
    incoming = bind_functions(namespace, {'__init__': globals()['__init__']},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'__init__': '__init__'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.annotation_improvement.from_parent')
    globals().update(incoming)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
