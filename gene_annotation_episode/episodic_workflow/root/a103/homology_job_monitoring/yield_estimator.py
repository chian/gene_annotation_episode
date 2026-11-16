"""Own this Homology job's original supplied continuation and observation wrapper."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _runtime


def yield_controller(workflow, path, identity, row):
    role = path[-1][0]
    if getattr(workflow.controller_factory, 'requires_original_task', False):
        request = _runtime.json.loads(row['request'])
        bound = _runtime.BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(workflow.receipts.known(identity.episode_id)) if workflow.receipts is not None else ())
        controller = workflow.controller_factory(path, row['initial_credit'], context=bound, task_key=None, credit_definition=None)
    else:
        controller = workflow.controller_factory(path, row['initial_credit'])
    native = workflow.has_native_estimation()
    episode_id = identity.episode_id
    capture = lambda unit_ref, index, value: workflow.capture_completion_evidence(episode_id, original_decision_index=index, unit_ref=unit_ref, controller_input=value)
    return _runtime.ExecutionContextController(controller, workflow.journal, episode_id, include_native=native, capture_current_completion=capture)
