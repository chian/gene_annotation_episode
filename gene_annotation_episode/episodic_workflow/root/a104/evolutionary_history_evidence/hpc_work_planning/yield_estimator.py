"""Private yield for A104 hpc."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.a104.library import hpc_prediction as prediction
import time




class HPCEpisodeYield:
    def yield_controller(self, context, initial_credit, epoch):
        """Bind the original HPC episode's active and pending work forecast."""
        self.credit_kind(context.role)
        if not self.private_yield_binding:
            raise ValueError('hpc_episode_yield_binding_required:' + context.role)
        from gene_annotation_episode.episodic_workflow.root.a104.numerical import YieldController, YieldParameters
        commission = self._commission(context.assignment, context.scope)
        if 'yield_bindings' not in commission:
            raise ValueError('hpc_commission_yield_binding_required:' + context.role)
        chosen = commission['yield_bindings'][context.role]
        estimator = self.practical_estimator(context).with_continuation_cost(chosen['cutoff'])
        return YieldController(epoch, initial_credit, chosen['cutoff'],
            YieldParameters(**chosen['parameters']), estimate_with_context=estimator)

    def continuation_for_action(self, context, operation_key):
        from gene_annotation_episode.episodic_workflow.root.a104.hpc_monitoring import choose_schedule
        ledger = self.state(context)
        reference = 'continuation:' + operation_key
        old = [row for row in ledger.records('continuation') if row['id'] == reference]
        if old:
            return {'reference': reference, 'evidence': old[0]['body']}
        credited = [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions'] if row['kind'] == 'actual']
        remaining = set(ledger.commission['obligations']) - set(credited)
        evidence = {'run_id': context.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key, 'earned_wait_credit': 0.0}
        if not remaining:
            evidence.update(expected_continuation_credit=0.0, active_credit_ceiling=0.0, reason='original_obligations_accepted')
        else:
            closed = {row['body']['plan_id'] for row in ledger.records('closed')}
            controllers = [row for row in ledger.records('monitor_controller') if row['body']['plan_id'] not in closed]
            if not controllers:
                return None
            pending_values, allocations, candidates = ({}, [], [])
            for controller in controllers:
                plan = next((row['body'] for row in ledger.records('plan') if row['body']['plan_id'] == controller['body']['plan_id']))
                candidate = self._candidate(ledger, plan)
                candidates.append(candidate)
                monitor = self._last_forecast(ledger, plan)
                current = monitor['conditional_prediction']
                state = current.get('telemetry', {}).get('state')
                collected = self._collected_unit_ids(ledger, plan)
                if state in ('complete', 'failed'):
                    unresolved = remaining.intersection((unit['obligation_id'] for unit in candidate['units'] if unit['unit_id'] not in collected))
                    values = {key: ledger.commission['obligations'][key]['credit'] for key in unresolved}
                    valuation = {'expected_continuation_credit': sum(values.values()), 'value_kind': 'unresolved_acceptance_upper_bound', 'reason': 'observed_outputs_await_acceptance'}
                    evidence['pending_action'] = 'collect'
                else:
                    valuation = choose_schedule(current, candidate, ledger.commission, controller['body']['policy'], credited=credited, now=time.time())
                    compared = prediction.compare(candidate, current, ledger.commission['obligations'], ledger.commission['preferences'], already_credited=credited)
                    total = compared['expected_actual_credit']
                    scale = min(1.0, valuation['expected_continuation_credit'] / total) if total else 0.0
                    values = {row['obligation_id']: row['expected_credit'] * scale for row in compared['attainable_units']}
                ready = self._uncollected_completed_unit_ids(ledger, plan, current)
                unresolved_outputs = {unit['obligation_id'] for unit in candidate['units'] if unit['unit_id'] in ready and unit['obligation_id'] in remaining}
                if unresolved_outputs:
                    for key in unresolved_outputs:
                        values[key] = max(values.get(key, 0.0), ledger.commission['obligations'][key]['credit'])
                    valuation = {'expected_continuation_credit': sum(values.values()), 'value_kind': 'unresolved_acceptance_upper_bound', 'reason': 'observed_unit_outputs_await_acceptance', 'ready_unit_ids': sorted(ready), 'remaining_computation_valuation': valuation}
                    evidence['pending_action'] = 'collect'
                for key, value in values.items():
                    pending_values[key] = max(pending_values.get(key, 0.0), value)
                allocations.append({'plan_id': plan['plan_id'], 'controller_ref': controller['id'], 'forecast_ref': monitor['forecast_ref'], 'valuation': valuation})
            total = sum(pending_values.values())
            combined = allocations[0]['valuation'] if len(allocations) == 1 else {'expected_continuation_credit': total, 'value_kind': 'unresolved_acceptance_upper_bound' if evidence.get('pending_action') == 'collect' else 'deduplicated_pending_expectation'}
            evidence.update(valuation=combined, expected_continuation_credit=total, pending_allocations=allocations, pending_by_obligation=pending_values)
            covered = {unit['obligation_id'] for row in ledger.records('plan') if row['body']['plan_id'] not in closed for unit in self._candidate(ledger, row['body'])['units']}
            untrained = set(self._history(ledger)) - set(ledger.commission['validation_ids']) - set(ledger.read(self._current_model(ledger))['training_ids'])
            fixed_single_unit = all((len(candidate['units']) == 1 for candidate in candidates))
            if not remaining - covered and (not untrained) and fixed_single_unit:
                evidence.update(active_credit_ceiling=0.0, active_exhaustion_reason='all_remaining_obligations_pending_and_no_new_training_cases')
        if self.store is not None:
            passive = {'hpc.monitor', 'hpc.monitor.wait', 'hpc.results'}
            rows = self.store.db.execute("SELECT o.unit_index,a.action FROM runtime_observations o JOIN runtime_actions a ON a.run_id=o.run_id AND a.episode_id=o.episode_id AND a.decision_index=json_extract(o.observation,'$.decision_index') WHERE o.run_id=? AND o.episode_id=? ORDER BY o.unit_index", (context.run_id, context.episode_id)).fetchall()
            indices = [row[0] for row in rows if (action := json.loads(row[1])).get('kind') != 'wait' and action.get('tool') not in passive]
            index = int(operation_key.rsplit(':', 1)[1])
            current = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, context.episode_id, index)).fetchone()
            if current is not None:
                action = json.loads(current[0])
                if action.get('kind') != 'wait' and action.get('tool') not in passive:
                    indices.append(len(rows))
            evidence['active_history_indices'] = indices
        ledger.put('continuation', evidence, identity=reference)
        return {'reference': reference, 'evidence': evidence}

    def practical_estimator(self, context):
        if context.role not in self.roles:
            return None
        from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_continuation import HPCContinuationEstimator
        ledger = self.state(context)
        def verify(packet):
            return ledger.read(packet['reference']) == packet['evidence']
        return HPCContinuationEstimator(verify)
