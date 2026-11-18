"""Private measured history for A110 hpc."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.hpc_resource_prediction import physical_attempt_key
import time




class MeasuredHistory:
    @staticmethod
    def _history(ledger):
        rows = {row['id']: row for row in ledger.commission['history']}
        original_attempts = {physical_attempt_key(row) for row in rows.values()}-{None}
        for snapshot in ledger.records('shared_history')[-1:]:
            rows.update({row['id']: row for row in snapshot['body']['observations']
                         if physical_attempt_key(row) not in original_attempts})
        plans = {row['body']['plan_id']: row['body'] for row in ledger.records('plan')}
        closed = {row['body']['plan_id'] for row in ledger.records('closed')}
        # Keep one latest observation per actual allocation, not one training
        # example per poll. Failed unfinished work retains a censored duration.
        latest = {}
        for row in ledger.records('measured'):
            if row['body']['plan_id'] in closed:
                latest[row['body']['plan_id']] = row
        for plan_id, row in latest.items():
            body = row['body']
            rows['allocation:'+plan_id] = {'id': 'allocation:'+plan_id,
                'observed_at': body['observed_at'], 'features': plans[plan_id]['original_prediction']['features'],
                'metrics': body['metrics'], 'success': body['success'], 'provenance': [row['id']]}
        return rows

    def _shared_history(self, ledger):
        from gene_annotation_episode.episodic_workflow.root.a110.execution_guidance import resource_identity
        commission = ledger.commission
        profile = commission.get('execution_profile')
        resource = resource_identity(commission['resource_id'], self.resources[commission['resource_id']])
        # Queue timing is resource-wide. Work timing requires explicit matching
        # algorithm, parameters, software and hardware, never just 'Aurora'.
        query = profile or {'resource_id': resource, 'backend': 'hpc', 'tool': 'allocation',
            'implementation': 'unspecified', 'parameters': 'unspecified', 'hardware': resource}
        now = time.time()
        rows = {row['id']: row for row in self.memory.history(query, now=now, queue_only=True)}
        if profile:
            rows.update({row['id']: row for row in self.memory.history(profile, now=now)})
        queues = {candidate['queue'] for candidate in self._candidates(ledger)}
        model_features = {item['name'] for item in commission['model']['features']}
        filtered = []
        for row in rows.values():
            queue = row.get('queue')
            # Different PBS queues are not interchangeable. Pool only when
            # the portfolio has one matching queue, or the model explicitly
            # carries its categorical indicator.
            if 'queue' in row['metrics'] and not (queue and
                    (queues == {queue} or 'queue:'+queue in model_features)):
                row['metrics'].pop('queue')
            if queue:
                row['features']['queue:'+queue] = 1.
            if row['metrics'] or row['success'] is not None:
                filtered.append(row)
        original = {row['id'] for row in commission['history']}
        original_attempts = {physical_attempt_key(row) for row in commission['history']}-{None}
        return {'captured_at': now, 'policy': self.memory.as_record()['policy'],
                'observations': [row for row in filtered if row['id'] not in original
                                 and physical_attempt_key(row) not in original_attempts][:2000]}

    def export_closed(self, ledger, plan):
        """Reusable for retained completed runs; this performs no remote work."""
        if self.memory is None:
            return
        from gene_annotation_episode.episodic_workflow.root.a110.hpc_history import closed_measurement
        if not any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
            raise ValueError('only_closed_allocations_enter_shared_history')
        measured = ledger.once('export_measurement:'+plan['plan_id'], 'export_measurement', lambda:
            [row for row in ledger.records('measured') if row['body']['plan_id'] == plan['plan_id']][-1])
        handoff = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']][-1]
        self.memory.record(**closed_measurement(ledger.commission, plan, measured, handoff,
                                               resources=self.resources, ledger_path=ledger.path))

    async def _refresh_measured_history(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        result = ledger.once('shared_history:' + operation_key, 'shared_history', lambda: self._shared_history(ledger))
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
