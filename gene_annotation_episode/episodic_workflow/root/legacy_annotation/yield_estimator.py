"""Root-owned continuation_observation.py"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from gene_annotation_episode.episodic_workflow.root.workflow_values import ExecutionContextController
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
from gene_annotation_episode.episodic_workflow.root.task_values import _plain
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical
import hashlib
import json

def controller(self, path):
    identity = Episode.identity(self.context, self.grains[path[-1][0]], path[-1][1], parent_path=path[:-1])
    row = self.journal.row('runtime_episodes', identity.episode_id)
    role = path[-1][0]
    binding = self.episode_bindings.for_path(path) if role in self.episode_bindings.roles else None
    bound = None
    owner_controller = getattr(binding, 'yield_controller', None) if getattr(binding, 'private_yield_binding', False) else None
    if owner_controller is not None:
        request = json.loads(row['request'])
        bound = BindingContext(self.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(self.receipts.known(identity.episode_id)) if self.receipts is not None else ())
        epoch = hashlib.sha256(canonical(path).encode()).hexdigest()
        controller = owner_controller(bound, row['initial_credit'], epoch)
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
    if binding is not None and owner_controller is None:
        estimator = getattr(binding, 'practical_estimator', None)
        if estimator is not None:
            if bound is None:
                request = json.loads(row['request'])
                bound = BindingContext(self.run_id, identity.episode_id, role, path, request['message']['scope'], request['message']['episode_assignment'], request)
            callback = estimator(bound)
            if callback is not None:
                from gene_annotation_episode.episodic_workflow.root.numerical import YieldController
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

