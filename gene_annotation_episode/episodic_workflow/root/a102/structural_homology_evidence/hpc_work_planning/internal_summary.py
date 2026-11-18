"""Private internal summary for A102 hpc."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.a102.communication import plain
from gene_annotation_episode.episodic_workflow.root.a102.library import hpc_prediction as prediction




class HPCSummary:
    def decision_context(self, context, current_view):
        ledger = self.state(context)
        if not ledger.records('model'):
            self.initialize(context)
        deliveries = []
        if self.store is not None:
            for row in self.store.db.execute('SELECT a.delivery_ref,a.form,e.path FROM runtime_report_attempts a '
                    'JOIN runtime_episodes e ON e.run_id=a.run_id AND e.episode_id=a.child_episode_id '
                    'WHERE a.run_id=? AND a.parent_episode_id=? ORDER BY a.decision_index',
                    (context.run_id, context.episode_id)):
                if json.loads(row['path'])[-1][0] == 'launch':
                    deliveries.append({'delivery_ref': row['delivery_ref'],
                        'delivered_form': json.loads(row['form']) if row['form'] else None})
        return {'hpc_commission': ledger.commission, 'hpc_owner_episode_id': ledger.read('owner')['episode_id'],
            'hpc_candidates': self._candidates(ledger),
            'hpc_resource': self.resources[ledger.commission['resource_id']],
            'hpc_child_scope': plain(context.scope),
            'hpc_child_commission': self.commission_identity(context.assignment),
            'hpc_launch_deliveries': deliveries,
            'hpc_launch_report_form': {'type': 'object', 'additionalProperties': False,
                'properties': {'execution_handoff_refs': {'type': 'array', 'uniqueItems': True,
                    'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_handoff'},
                    'x-source': 'execution_handoff_refs'}}, 'required': ['execution_handoff_refs']},
            'hpc_tool_request': [row['body'] for row in ledger.records('tool_request')],
            'hpc_model_ref': self._current_model(ledger), 'hpc_credit': self.credit_view(context, None),
            'hpc_latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                if key not in ('episode_id', 'operation_key')}} for row in ledger.records('comparison')[-1:]],
            'hpc_model_support': prediction.predict(ledger.read(self._current_model(ledger)), {})['support'],
            'hpc_report_form': {'type': 'object', 'additionalProperties': False, 'properties': {
                'hpc_credit': {'type': 'number', 'x-source': 'hpc_credit'},
                'hpc_model_ref': {'type': 'string', 'format': 'reference',
                    'x-reference-namespace': 'hpc_model', 'x-source': 'hpc_model_ref'},
                'hpc_result_refs': {'type': 'array', 'uniqueItems': True, 'items': {
                    'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
                    'x-source': 'hpc_result_refs'}},
                'required': ['hpc_credit', 'hpc_model_ref', 'hpc_result_refs']},
            'hpc_plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                          for row in ledger.records('plan')],
            'hpc_latest_monitor': ledger.records('monitor')[-1:],
            'hpc_monitor_controllers': ledger.records('monitor_controller'),
            'hpc_activity_decision': self.activity_advice(context),
            'hpc_queue_refs': [row['id'] for row in ledger.records('queue')],
            **({'hpc_shared_memory': self.memory.as_record(),
                'hpc_shared_history_refs': [row['id'] for row in ledger.records('shared_history')]}
               if self.memory else {}),
            'hpc_available_training_ids': sorted(set(self._history(ledger))-set(ledger.commission['validation_ids']))}
