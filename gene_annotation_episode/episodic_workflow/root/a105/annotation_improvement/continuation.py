"""Original private A105 annotation continuation responsibility."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a105 import runtime as _original_runtime

def controller(workflow, path, *, identity, row, role, binding):
    bound = None
    owner_controller = getattr(binding, 'yield_controller', None) if getattr(binding, 'private_yield_binding', False) else None
    if owner_controller is not None:
        request = _original_runtime.json.loads(row['request'])
        bound = _original_runtime.BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(workflow.receipts.known(identity.episode_id)) if workflow.receipts is not None else ())
        epoch = _original_runtime.hashlib.sha256(_original_runtime.canonical(path).encode()).hexdigest()
        controller = owner_controller(bound, row['initial_credit'], epoch)
    elif getattr(workflow.controller_factory, 'requires_original_task', False):
        request = _original_runtime.json.loads(row['request'])
        bound = _original_runtime.BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(workflow.receipts.known(identity.episode_id)) if workflow.receipts is not None else ())
        task_key = credit_definition = None
        scientific_child = len(path) > 1 and (role == 'improvement' or (binding is not None and binding.credit_kind(role) == 'scientific'))
        if scientific_child:
            choose_task = getattr(binding, 'continuation_task', None)
            if choose_task is None:
                raise ValueError('scientific_continuation_task_not_declared:' + role)
            task_key = choose_task(bound)
            if not isinstance(task_key, str) or not task_key:
                raise ValueError('scientific_continuation_task_not_declared:' + role)
            credit_definition = _original_runtime._plain(workflow.scientific_projector_for_context(bound).as_record())
        controller = workflow.controller_factory(path, row['initial_credit'], context=bound, task_key=task_key, credit_definition=credit_definition)
    else:
        controller = workflow.controller_factory(path, row['initial_credit'])
    if binding is not None and owner_controller is None:
        estimator = getattr(binding, 'practical_estimator', None)
        if estimator is not None:
            if bound is None:
                request = _original_runtime.json.loads(row['request'])
                bound = _original_runtime.BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message']['episode_assignment'], request)
            callback = estimator(bound)
            if callback is not None:
                from gene_annotation_episode.episodic_workflow.root.a105.numerical import YieldController
                if type(controller) is not YieldController:
                    raise ValueError('practical_binding_requires_explicit_yield_controller')
                bind_cost = getattr(callback, 'with_continuation_cost', None)
                if bind_cost is not None:
                    callback = bind_cost(controller.cost)
                controller = YieldController(controller.epoch, row['initial_credit'], controller.cost, controller.settings, estimate_with_context=callback)
    native = workflow.has_native_estimation()
    episode_id = identity.episode_id
    capture = lambda unit_ref, index, value: workflow.capture_completion_evidence(episode_id, original_decision_index=index, unit_ref=unit_ref, controller_input=value)
    return _original_runtime.ExecutionContextController(controller, workflow.journal, episode_id, include_native=native, capture_current_completion=capture)

def controller_value(workflow, source, index, credit):
    value = {'credit': credit, 'estimation_action_index': index}
    if isinstance(credit, _original_runtime.Mapping) and credit.get('mode') == 'annotation_axis_credit':
        value.update(workflow.episode_bindings.annotation_axis_yield_context(workflow.binding_context(source), credit))
        action = workflow.journal.row('runtime_actions', source.episode_id, index)
        selected = _original_runtime.json.loads(action['action'])
        if selected.get('kind') == 'episode_child' and selected.get('role') == 'scientific_process':
            assignment = selected['assignment']
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_records import selection_fields
            process = assignment['selection']
            axis = process[selection_fields(process)[0]]['option_id']
            ref = assignment.get('proposed_annotation_ref')
            arms = [arm for arm in credit['arms'] if arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == selected['scope'])]
            if len(arms) != 1:
                raise _original_runtime.WorkflowError('completed_axis_requires_one_original_annotation_subject_scope')
            value['completed_annotation_axis'] = {name: arms[0][name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}
    binding = workflow.specialist(source)
    continuation = getattr(binding, 'continuation_for_action', None)
    if continuation is not None:
        pending_value = continuation(workflow.binding_context(source), f'{workflow.run_id}:{source.episode_id}:{index}')
        if pending_value is not None:
            value['hpc_continuation'] = pending_value
            value['estimation_action_index'] = index
    completion = getattr(binding, 'completion_for_action', None)
    if completion is not None:
        proof = completion(workflow.binding_context(source), f'{workflow.run_id}:{source.episode_id}:{index}')
        if proof is not None:
            value['practical_completion'] = proof
            value['estimation_action_index'] = index
    return _original_runtime.Record(value)
