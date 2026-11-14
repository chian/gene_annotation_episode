"""Private yield for A110 prediction."""
from __future__ import annotations
import time



class HPCEpisodeYield:
    def yield_controller(self, context, initial_credit, epoch):
        """Bind the original HPC episode's active and pending work forecast."""
        self.credit_kind(context.role)
        if not self.private_yield_binding:
            raise ValueError('hpc_episode_yield_binding_required:' + context.role)
        from gene_annotation_episode.episodic_workflow.root.a110.numerical import YieldController, YieldParameters
        commission = self._commission(context.assignment, context.scope)
        if 'yield_bindings' not in commission:
            raise ValueError('hpc_commission_yield_binding_required:' + context.role)
        chosen = commission['yield_bindings'][context.role]
        estimator = self.practical_estimator(context).with_continuation_cost(chosen['cutoff'])
        return YieldController(epoch, initial_credit, chosen['cutoff'],
            YieldParameters(**chosen['parameters']), estimate_with_context=estimator)

    def continuation_for_action(self, context, operation_key):
        ledger = self.state(context)
        model_ref = self._current_model(ledger)
        available = set(self._history(ledger))-set(ledger.commission['validation_ids'])
        trained = set(ledger.read(model_ref)['training_ids'])
        candidates = {row['id'] for row in self._candidates(ledger)}
        comparisons = [row['body'] for row in ledger.records('comparison')
            if row['body']['model_ref'] == model_ref and row['body']['episode_id'] == context.episode_id
            and {item['candidate_id'] for item in row['body']['comparisons']} == candidates]
        # With no held-out cases, rereading/refitting the same measured data
        # has no supported incremental model credit. Once a trained model
        # and current comparisons exist, actual execution supplies the next
        # evidence. This bounds available action value, not action count.
        if (not ledger.commission['validation_ids'] and available <= trained
                and candidates and comparisons):
            latest = comparisons[-1]
            queue = self._queue(ledger, latest['queue_ref'])
            if time.time()-queue['captured_at'] <= ledger.commission['limits']['queue_max_age_seconds']:
                evidence = {'run_id': context.run_id, 'episode_id': context.episode_id,
                    'operation_key': operation_key, 'earned_wait_credit': 0.,
                    'expected_continuation_credit': 0., 'active_credit_ceiling': 0.,
                    'reason': 'prediction_ready_without_new_measured_improvement_opportunities',
                    'model_ref': model_ref, 'training_ids': sorted(trained),
                    'candidate_ids': sorted(candidates), 'comparison_operation': latest['operation_key'],
                    'queue_ref': latest['queue_ref'],
                    'scope': 'current_model_family_and_available_evidence; new observations reopen prediction'}
                reference = 'prediction-continuation:'+operation_key
                ledger.put('continuation', evidence, identity=reference)
                return {'reference': reference, 'evidence': evidence}
        return None

    def practical_estimator(self, context):
        if context.role not in self.roles:
            return None
        from gene_annotation_episode.episodic_workflow.root.a110.library.hpc_continuation import HPCContinuationEstimator
        ledger = self.state(context)
        def verify(packet):
            return ledger.read(packet['reference']) == packet['evidence']
        return HPCContinuationEstimator(verify)
