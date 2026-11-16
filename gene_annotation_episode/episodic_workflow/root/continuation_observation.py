"""Root-owned continuation_observation.py"""
from __future__ import annotations
from .receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from .workflow_values import ExecutionContextController
from collections.abc import Mapping
from .task_values import Record
from .episode_journal import WorkflowError
from .task_values import _plain
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical
import hashlib
import json

class ContinuationObservation:

    def controller(self, path):
        if path[-1][0] == 'improvement' and 'improvement' not in self.episode_bindings.roles:
            from .legacy_annotation.episode import LegacyAnnotationEpisodeBinding
            return LegacyAnnotationEpisodeBinding.controller(self, path)
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

    def capture_completion_evidence(self, episode_id, *, original_decision_index, unit_ref, controller_input):
        from .completion_evidence import CompletionEvidence
        return CompletionEvidence(self.store, self.journal, self.execution_backend, self.progress_provider).capture(episode_id, original_decision_index=original_decision_index, unit_ref=unit_ref, controller_input=controller_input)

    def has_native_estimation(self):
        return getattr(self.tools, 'native_statistics', None) is not None and self.resource_estimator is not None

    def controller_value(self, source, index, credit):
        observed = self.store.db.execute("SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? AND json_extract(observation,'$.decision_index')=?", (self.run_id, source.episode_id, index)).fetchone()
        if observed is not None:
            original = json.loads(observed['observation'])['credit']
            if not isinstance(original, dict) or 'credit' not in original or original.get('estimation_action_index', index) != index:
                raise WorkflowError('recorded controller input does not match its action')
            return Record(original)
        value = {'credit': credit, 'estimation_action_index': index}
        if isinstance(credit, Mapping) and credit.get('mode') == 'annotation_axis_credit':
            value.update(self.episode_bindings.annotation_axis_yield_context(self.binding_context(source), credit))
            action = self.journal.row('runtime_actions', source.episode_id, index)
            selected = json.loads(action['action'])
            if selected.get('kind') == 'episode_child' and selected.get('role') == 'scientific_process':
                assignment = selected['assignment']
                from .scientific_process_records import selection_fields
                process = assignment['selection']
                axis = process[selection_fields(process)[0]]['option_id']
                ref = assignment.get('proposed_annotation_ref')
                arms = [arm for arm in credit['arms'] if arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == selected['scope'])]
                if len(arms) != 1:
                    raise WorkflowError('completed_axis_requires_one_original_annotation_subject_scope')
                value['completed_annotation_axis'] = {name: arms[0][name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}
        binding = self.specialist(source)
        continuation = getattr(binding, 'continuation_for_action', None)
        if continuation is not None:
            pending_value = continuation(self.binding_context(source), f'{self.run_id}:{source.episode_id}:{index}')
            if pending_value is not None:
                value['hpc_continuation'] = pending_value
                value['estimation_action_index'] = index
        completion = getattr(binding, 'completion_for_action', None)
        if completion is not None:
            proof = completion(self.binding_context(source), f'{self.run_id}:{source.episode_id}:{index}')
            if proof is not None:
                value['practical_completion'] = proof
                value['estimation_action_index'] = index
        return Record(value)
