"""Original unbound annotation continuation; configured numerical factory preserved."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _original_runtime

def controller(workflow, path, identity, row, role, binding, bound, binding_controller):
    if binding_controller is not None:
        pass
    elif getattr(workflow.controller_factory, 'requires_original_task', False):
        request = _original_runtime.json.loads(row['request'])
        bound = _original_runtime.BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(workflow.receipts.known(identity.episode_id)) if workflow.receipts is not None else ())
        task_key = credit_definition = None
        scientific_child = len(path) > 1 and (role == 'improvement' or (binding is not None and binding.credit_kind(role) == 'scientific'))
        if scientific_child:
            pass
        controller = workflow.controller_factory(path, row['initial_credit'], context=bound, task_key=task_key, credit_definition=credit_definition)
    else:
        controller = workflow.controller_factory(path, row['initial_credit'])
    if binding is not None and binding_controller is None:
        pass
    native = workflow.has_native_estimation()
    episode_id = identity.episode_id
    capture = lambda unit_ref, index, value: workflow.capture_completion_evidence(episode_id, original_decision_index=index, unit_ref=unit_ref, controller_input=value)
    return _original_runtime.ExecutionContextController(controller, workflow.journal, episode_id, include_native=native, capture_current_completion=capture)
