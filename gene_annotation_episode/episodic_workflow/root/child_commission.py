"""Root-owned child_commission.py"""
from __future__ import annotations
from .workflow_values import EPISODE_BRANCH_LIFECYCLE
from .workflow_values import OwnedChildActionUnit
from gene_annotation_episode.episodic_workflow.root.method_loop import PendingAction
from .episode_journal import WorkflowError
from .task_values import _digest
from .task_values import _json
from .workflow_values import _now
from .task_values import _plain
from .reference_selection import _references_in
from .communication import interpretation_schema
import json

class ChildCommission:

    def commission_child(self, source, child, selection, index):
        self.validate_child_choice(source, child.source.path[-1][0], selection=selection, original=True)
        if self.episode_bindings.private_owners:
            self._binding_owner_for_path(child.source.path)
            self._owner_records().authenticate(self.binding_context(child.source))
        message = child.request.message.as_record()
        assignment = message.get('episode_assignment', message.get('job_assignment', {}))
        references = _references_in({'scope': child.source.scope, 'assignment': assignment}, self.store.get, forms=[(message['initial_report'], interpretation_schema(child.request.report_contract.schema))], reference_subset=lambda refs: self.store.reference_subset(refs, child.source.scope))
        from .episode_input_versions import pin_commission_inputs
        resource_versions = assignment.get('immutable_input_versions', assignment.get('handoff', {}).get('submitted_input_versions', ()))
        pinned = pin_commission_inputs(self.store, references, resource_input_versions=resource_versions)
        original = json.loads(self.journal.row('runtime_model_calls', source.episode_id, index)['request'])['context']
        expectation_refs = list(dict.fromkeys((snapshot['ref'] for name in ('execution_expectations', 'native_execution_expectations') for snapshot in (original.get(name) or {}).get('snapshots', []))))
        resources = self.tools.resource_binding() if callable(getattr(self.tools, 'resource_binding', None)) else {}
        constraints = _plain(assignment.get('constraints', {'local_jobs': resources.get('local_jobs')}))
        spec = self.commissions.select(parent={'episode_id': source.episode_id, 'goal_id': source.request.goal.goal_id, 'path': _plain(source.path)}, child={'episode_id': child.source.episode_id, 'role': child.source.path[-1][0], 'key': child.key, 'path': _plain(child.source.path), 'request': _plain(child.request.as_record()), 'scope': _plain(child.source.scope)}, original_decision_index=index, selection=selection, runtime_binding=self.execution_binding, input_versions=pinned, constraints=constraints, resource_selection=assignment.get('resource_selection'), expectation_snapshot_refs=expectation_refs, selected_at=_now())
        return self.deferred_unit(source, index, spec)

    def deferred_unit(self, source, index, spec):

        def dispatch(context):
            self.dispatch_commission(source, index, spec)
            return spec['handle']

        async def collect(context, handle):
            status = await self.execution_backend.await_return_or_suspension(handle)
            if not status['return_available']:
                self.settle_unclaimed_child_failures(source)
                return PendingAction(handle)
            slot = self.next_return(source, only_handle=handle)
            if slot is None:
                delivery_ref = 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
                await self.resolve_pending_deliveries(source, source._selection_view, only_delivery_ref=delivery_ref)
                row = self.store.db.execute('SELECT slot FROM runtime_completion_slots WHERE run_id=? AND episode_id=? AND original_decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
                slot = None if row is None else json.loads(row[0])
            if slot is None:
                raise WorkflowError('owned_return_requires_accounted_original_action')
            return await self.completed_unit(source, slot).acquire_async(context)
        return OwnedChildActionUnit(spec['child']['key'], dispatch, decision_index=index, collect=collect)

    def dispatch_commission(self, source, index, spec):
        if self.episode_bindings.private_owners:
            self._binding_owner_for_path(spec['child']['path'])
            original_child = self._owner_records().context(spec['child']['episode_id'])
            if _plain(original_child.request) != spec['child']['request']:
                raise ValueError('root_binding_commission_request_conflict')
        self.validate_child_choice(source, spec['child']['role'], original=True)
        if self.annotation_child_roles is not None and (spec['run_id'] != self.run_id or spec['parent']['episode_id'] != source.episode_id or _plain(spec['parent']['path']) != _plain(source.path)):
            raise ValueError('commission_parent_identity_mismatch')
        if self.annotation_child_roles is not None:
            original = self.store.db.execute('SELECT spec FROM runtime_commission_intents WHERE run_id=? AND parent_episode_id=? AND handle=?', (self.run_id, source.episode_id, spec['handle'])).fetchone()
            if original is None or json.loads(original[0]) != _plain(spec):
                raise ValueError('commission_intent_identity_mismatch')
        with self.journal.measure('runtime_actions', source.episode_id, index):
            status = self.commissions.dispatch(spec['handle'])
        if self.execution_handle is not None and self.progress_provider is not None:
            action = self.journal.row('runtime_actions', source.episode_id, index)
            selected_at = json.loads(action['result'])['selected_at']
            self.progress_provider.expose(self.execution_handle, operation_key=spec['operation_key'], dependencies=[{'handle': spec['handle'], 'kind': 'episode', 'relation_ref': _digest(spec), 'observed_at': selected_at, 'state': 'pending'}])
            self.progress_provider.flush_notifications()
        if status.get('failure') is not None:
            source.feedback = status['failure']
        return status

    def recover_commissions(self, source):
        by_handle = {item['handle'] for item in self.commissions.pending(source.episode_id)['items']}
        for spec in self.commissions.recover_selected(source.episode_id):
            if spec['handle'] in by_handle:
                if self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE:
                    try:
                        status = self.execution_backend.status(spec['handle'])
                    except KeyError:
                        pass
                    else:
                        if status['failure'] is not None and status['execution_identity'] is None and (not status['return_available']):
                            continue
                action = self.store.db.execute("SELECT decision_index FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(result,'$.pending_handle')=?", (self.run_id, source.episode_id, spec['handle'])).fetchone()
                self.dispatch_commission(source, action[0], spec)

    def settle_unclaimed_child_failures(self, source):
        """Account for an attempted bootstrap without inventing child science."""
        if self.episode_branch_lifecycle != EPISODE_BRANCH_LIFECYCLE or self.journal.row('runtime_episodes', source.episode_id)['state'] != 'active':
            return
        rows = self.store.db.execute("SELECT decision_index,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(result,'$.status')='pending' AND json_extract(result,'$.pending_handle') IS NOT NULL ORDER BY decision_index", (self.run_id, source.episode_id)).fetchall()
        for row in rows:
            handle = json.loads(row['result'])['pending_handle']
            try:
                status = self.execution_backend.status(handle)
            except KeyError:
                continue
            if status['failure'] is None or status['execution_identity'] is not None or status['return_available']:
                continue
            index = row['decision_index']
            with self.store.transaction():
                original = self.journal.row('runtime_actions', source.episode_id, index)
                if original['result'] != row['result'] or original['credit'] is not None:
                    raise WorkflowError('unclaimed_child_failure_action_changed')
                outcome = {'status': 'failed', 'execution_handle': handle, 'record_refs': [], 'changed_record_refs': [], 'feedback': status['failure']}
                self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': original['action'], 'result': _json(outcome), 'credit': None})
                credit = self.source_credit_view(source)['credit']
                self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': original['action'], 'result': _json(outcome), 'credit': credit})
                self.completions.stage(source.episode_id, index, label=f'child_{index}', kind='own_action', controller_input=self.controller_value(source, index, credit), child_return=None)
                source.last_outcome, source.last_outcome_index = (outcome, index)
                source.feedback = status['failure']
                source.checkpoint()
