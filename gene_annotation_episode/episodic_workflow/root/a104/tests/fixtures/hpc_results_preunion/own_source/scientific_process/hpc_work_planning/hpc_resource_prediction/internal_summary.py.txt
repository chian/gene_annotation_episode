"""Private internal summary for A104 prediction."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library import hpc_prediction as prediction



class PredictionSummary:
    def decision_context(self, context, current_view):
        ledger = self.state(context)
        if not ledger.records('model'):
            self.initialize(context)
        return {'hpc_commission': ledger.commission, 'hpc_owner_episode_id': ledger.read('owner')['episode_id'],
            'hpc_candidates': self._candidates(ledger),
            'hpc_resource': self.resources[ledger.commission['resource_id']],
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
            'hpc_queue_refs': [row['id'] for row in ledger.records('queue')],
            **({'hpc_shared_memory': self.memory.as_record(),
                'hpc_shared_history_refs': [row['id'] for row in ledger.records('shared_history')]}
               if self.memory else {}),
            'hpc_available_training_ids': sorted(set(self._history(ledger))-set(ledger.commission['validation_ids']))}
