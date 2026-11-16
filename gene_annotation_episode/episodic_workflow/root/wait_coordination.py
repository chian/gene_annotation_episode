"""Root-owned wait_coordination.py"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import EventTargetError
from collections.abc import Mapping
from .task_values import _digest
from .workflow_values import _now
from .task_values import _plain
from .wait_events import estimate_wait
import json
from .wait_events import validate_condition

class WaitCoordination:

    def pending_work(self, source):
        from .pending_assignment import original_assignment
        if self.execution_binding is not None:
            return self.commissions.pending(source.episode_id)
        if source._execution_context is not None:
            invocations = source._execution_context._pending_children(source.path)
            if invocations:
                from .inprocess_waiting import public_child_handle
                return {'version': 'pending_work_v2', 'captured_at': _now(), 'items': [{'handle': public_child_handle(source.episode_id, item.handle), 'role': item.role, 'original_assignment': original_assignment(getattr(item, '_request', None), getattr(item, 'decision_index', None)), 'lifecycle_state': 'returned' if item._task.done() else 'executing', 'suspension': {key: value for key, value in item._suspension.condition.items() if key != 'schedule_ref'} if isinstance(item._suspension.condition, Mapping) else item._suspension.condition, 'event_target': False, 'return_available': item._task.done(), 'selected_at': item.selected_at, 'observed_at': _now(), 'resource_selection': None, 'expectation_snapshot_refs': [], 'latest_progress_ref': None} for item in invocations]}
        rows = self.store.db.execute("SELECT decision_index,json_extract(result,'$.pending_handle') AS handle, json_extract(result,'$.selected_at') AS selected_at FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(result,'$.status')='pending' AND json_extract(result,'$.pending_handle') IS NOT NULL ORDER BY decision_index", (self.run_id, source.episode_id))
        items = []
        for row in rows:
            status = self.execution_backend.status(row['handle'])
            spec = self.execution_backend.load_commission(row['handle'])
            items.append({'handle': row['handle'], 'role': spec['child']['role'], 'original_assignment': original_assignment(spec['child']['request'], row['decision_index']), 'lifecycle_state': status['lifecycle_state'], 'selected_at': row['selected_at'], 'observed_at': status['observed_at'], 'resource_selection': spec['resource_selection'], 'expectation_snapshot_refs': spec['expectation_snapshot_refs'], 'latest_progress_ref': None, 'return_available': status['return_available'], 'suspension': status.get('suspension'), 'event_target': True})
        return {'version': 'pending_work_v2', 'captured_at': _now(), 'items': items}

    def pending_handles(self, source):
        return [item['handle'] for item in self.pending_work(source)['items']]

    def last_observed_credit(self, source):
        row = self.store.db.execute("SELECT json_extract(observation,'$.credit.credit') FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index DESC LIMIT 1", (self.run_id, source.episode_id)).fetchone()
        return row[0] if row is not None else self.journal.row('runtime_episodes', source.episode_id)['initial_credit']

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
        from gene_annotation_episode.episodic_workflow.root.method_loop.suspension import external_wait
        outcome = await external_wait(self.wait_store.perform_wait(request, self.execution_backend), {'kind': 'selected_external_event', 'wait_id': wait_id, 'condition': request['condition']})
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': outcome, 'wait_outcome': outcome, 'wait_estimate': request['estimate_snapshot'], 'pending_work_after_action': self.pending_work(source)}
