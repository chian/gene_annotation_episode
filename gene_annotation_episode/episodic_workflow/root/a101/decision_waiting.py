"""Actual selected waiting, original saved wait and duration/progress observations."""

def wait_estimate(self, source, condition, context):
    support = context.get('waiting_support')
    if support is None:
        support = self.waiting_support(source, context)
    return estimate_wait(condition, context['pending_work'], support['progress_records'], support['duration_expectations'], support['own_completed_action_history'])

def validate_wait_selection(self, source, condition):
    condition = validate_condition(_plain(condition))
    if not condition['events']:
        raise EventTargetError('wait_target_unavailable', affected_refs=[self.binding_context(source).episode_id], detail='selected_wait_requires_actual_outstanding_dependency')
    from .inprocess_waiting import selected_owned_children
    if selected_owned_children(self, source, condition) is not None:
        return condition
    if self.native_event_information is not None:
        condition = self.native_event_information.validate_wait(self.binding_context(source), condition)
    else:
        for event in condition['events']:
            if event['handle'].startswith('native_event_target_'):
                raise EventTargetError('wait_target_unavailable', affected_refs=[event['handle']], detail='native_event_target_unavailable')
    return self.execution_backend.validate_event_targets(condition)

def waiting_support(self, source, context):
    captures = [context[key] for key in ('execution_expectations', 'native_execution_expectations') if context.get(key) is not None]
    with self.store.read_snapshot():
        arguments = {}
        metadata = self.source_controller_credit(source)
        if metadata is not None:
            arguments['local_return_history'] = self.local_return_history.capture(source.episode_id, **metadata)
        support = self.wait_inputs.capture(source.episode_id, pending=context['pending_work'], known_progress_refs=self.progress_selection(source)['known_progress_refs'], current_duration_expectations=captures, **arguments)
        if metadata is None:
            support['local_return_history_unavailable_reason'] = 'controller_credit_binding_unavailable'
        if self.native_event_information is not None:
            support['native_event_targets'] = _plain(context.get('native_event_targets', []))
        return support

async def perform_selected_wait(self, source, condition, index):
    from .inprocess_waiting import selected_owned_children, await_owned_return
    if selected_owned_children(self, source, condition) is not None:
        condition = self.validate_wait_selection(source, condition)
        call = self.journal.row('runtime_model_calls', source.episode_id, index)
        context = json.loads(call['request'])['context']
        estimate = self.wait_estimate(source, condition, context)
        outcome = await await_owned_return(self, source, condition)
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': outcome, 'wait_estimate': estimate, 'pending_work_after_action': self.pending_work(source)}
    wait_id = 'wait_' + _digest({'run': self.run_id, 'episode': source.episode_id, 'decision': index})
    saved = self.wait_store.get(wait_id)
    if saved is not None:
        request = saved['request']
        if saved['outcome'] is None:
            self.validate_wait_selection(source, request['condition'])
    else:
        condition = self.validate_wait_selection(source, condition)
        call = self.journal.row('runtime_model_calls', source.episode_id, index)
        context = json.loads(call['request'])['context']
        request = {'version': 'wait_request_v1', 'wait_id': wait_id, 'parent_episode_id': source.episode_id, 'original_decision_index': index, 'condition': condition, 'estimate_snapshot': self.wait_estimate(source, condition, context)}
        with self.store.transaction():
            self.wait_store.select(request)
    from gene_annotation_episode.episodic_workflow.root.a101.method_loop.suspension import external_wait
    outcome = await external_wait(self.wait_store.perform_wait(request, self.execution_backend), {'kind': 'selected_external_event', 'wait_id': wait_id, 'condition': request['condition']})
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': outcome, 'wait_outcome': outcome, 'wait_estimate': request['estimate_snapshot'], 'pending_work_after_action': self.pending_work(source)}

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('wait_estimate', 'validate_wait_selection', 'waiting_support', 'perform_selected_wait')},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'wait_estimate': 'Workflow.wait_estimate', 'validate_wait_selection': 'Workflow.validate_wait_selection', 'waiting_support': 'Workflow.waiting_support', 'perform_selected_wait': 'Workflow.perform_selected_wait'},
        defining_module=None)
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
