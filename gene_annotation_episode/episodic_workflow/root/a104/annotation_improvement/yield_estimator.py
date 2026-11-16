"""A104 original implicit improvement responsibility."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def controller(self, path, identity, row, role, binding, bound, task_controller):
    if task_controller is not None:
        request = json.loads(row['request'])
        bound = BindingContext(self.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(self.receipts.known(identity.episode_id)) if self.receipts is not None else ())
        epoch = hashlib.sha256(canonical(path).encode()).hexdigest()
        controller = task_controller(bound, row['initial_credit'], epoch)
    elif getattr(self.controller_factory, 'requires_original_task', False):
        request = json.loads(row['request'])
        bound = BindingContext(self.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(self.receipts.known(identity.episode_id)) if self.receipts is not None else ())
        task_key = credit_definition = None
        scientific_child = len(path) > 1 and (role == 'improvement' or (binding is not None and binding.credit_kind(role) == 'scientific'))
        if scientific_child:
            choose_task = getattr(binding, 'continuation_task', None)
            if choose_task is None:
                raise ValueError('scientific_continuation_task_not_declared:' + role)
            task_key = choose_task(bound)
            if not isinstance(task_key, str) or not task_key:
                raise ValueError('scientific_continuation_task_not_declared:' + role)
            credit_definition = _plain(self.scientific_projector_for_context(bound).as_record())
        controller = self.controller_factory(path, row['initial_credit'], context=bound, task_key=task_key, credit_definition=credit_definition)
    else:
        controller = self.controller_factory(path, row['initial_credit'])
    if binding is not None and task_controller is None:
        estimator = getattr(binding, 'practical_estimator', None)
        if estimator is not None:
            if bound is None:
                request = json.loads(row['request'])
                bound = BindingContext(self.run_id, identity.episode_id, role, path, request['message']['scope'], request['message']['episode_assignment'], request)
            callback = estimator(bound)
            if callback is not None:
                from .numerical import YieldController
                if type(controller) is not YieldController:
                    raise ValueError('practical_binding_requires_explicit_yield_controller')
                bind_cost = getattr(callback, 'with_continuation_cost', None)
                if bind_cost is not None:
                    callback = bind_cost(controller.cost)
                controller = YieldController(controller.epoch, row['initial_credit'], controller.cost, controller.settings, estimate_with_context=callback)
    native = self.has_native_estimation()
    episode_id = identity.episode_id
    capture = lambda unit_ref, index, value: self.capture_completion_evidence(episode_id, original_decision_index=index, unit_ref=unit_ref, controller_input=value)
    return ExecutionContextController(controller, self.journal, episode_id, include_native=native, capture_current_completion=capture)

def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['controller']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'controller': 'controller'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
