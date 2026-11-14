"""Original supplied continuation controller and observation wrapper."""
import json
from gene_annotation_episode.episodic_workflow.root.a103.method_loop.episode import Episode
from gene_annotation_episode.episodic_workflow.root.a103.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a103.runtime import ExecutionContextController
from gene_annotation_episode.episodic_workflow.root.a103.from_parent import validate_path


def yield_controller(workflow, path):
    validate_path(path)
    identity = _live_original_runtime.Episode.identity(workflow.context, workflow.grains[path[-1][0]], path[-1][1], parent_path=path[:-1])
    row = workflow.journal.row('runtime_episodes', identity.episode_id)
    role = path[-1][0]
    if getattr(workflow.controller_factory, 'requires_original_task', False):
        request = _live_original_runtime.json.loads(row['request'])
        bound = _live_original_runtime.BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(workflow.receipts.known(identity.episode_id)) if workflow.receipts is not None else ())
        task_key = credit_definition = None
        if len(path) > 1:
            raise ValueError('scientific_continuation_task_not_declared:' + role)
        controller = workflow.controller_factory(path, row['initial_credit'], context=bound, task_key=task_key, credit_definition=credit_definition)
    else:
        controller = workflow.controller_factory(path, row['initial_credit'])
    native = workflow.has_native_estimation()
    episode_id = identity.episode_id
    capture = None if workflow.completed_action_inputs_version is None else lambda unit_ref, index, value: workflow.capture_completion_evidence(episode_id, original_decision_index=index, unit_ref=unit_ref, controller_input=value)
    return _live_original_runtime.ExecutionContextController(controller, workflow.journal, episode_id, include_native=native, capture_current_completion=capture)
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
