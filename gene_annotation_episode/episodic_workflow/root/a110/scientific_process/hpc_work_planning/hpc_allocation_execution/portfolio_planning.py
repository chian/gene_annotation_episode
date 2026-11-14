"""Private portfolio planning for A110 hpc_execution."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.hpc_campaign import build_plan
from gene_annotation_episode.episodic_workflow.root.a110 import hpc_queue
from gene_annotation_episode.episodic_workflow.root.a110.library import hpc_prediction as prediction




class PortfolioPlanning:
    async def _freeze_portfolio_plan(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        existing = ledger.records('plan')
        own = next((row for row in existing if row['body'].get('operation_key') == operation_key), None)
        if own is not None:
            plan = own['body']
            forecast_ref = self._freeze(ledger, plan, plan['original_prediction'], plan['original_reference'], {}, 'planned', operation_key)
            return ledger.save_action(operation_key, selection, {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': {'plan_ref': own['id'], 'forecast_ref': forecast_ref, **{key: value for key, value in plan.items() if key != 'prediction_episode_id'}}})
        observed = self._queue(ledger, arguments['queue_ref'], require_fresh=True)
        candidate = next((row for row in self._candidates(ledger) if row['id'] == arguments['candidate_id']))
        queue = hpc_queue.features(observed, candidate)
        rules = queue['queue_rules']
        if not rules or not rules['enabled'] or (not rules['started']) or (rules['type'] != 'Execution'):
            raise ValueError('choose_an_observed_enabled_execution_queue')
        for key, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
            if rules['min_' + key] is not None and value < rules['min_' + key] or (rules['max_' + key] is not None and value > rules['max_' + key]):
                raise ValueError('candidate_violates_observed_queue_limits')
        plan = build_plan(commission, candidate, configuration, ledger.read('owner'), len(existing))
        features = self._features(candidate, queue)
        predicted = prediction.predict(ledger.read(arguments['model_ref']), features)
        reference = prediction.predict(ledger.read('reference_model'), features)
        plan.update(model_ref=arguments['model_ref'], queue_ref=arguments['queue_ref'], original_prediction=predicted, original_reference=reference, operation_key=operation_key)
        choices = [row['body'] for row in ledger.records('model_choice') if row['body']['model_ref'] == arguments['model_ref']]
        plan['prediction_episode_id'] = choices[-1].get('episode_id') if choices else None
        plan_ref = ledger.put('plan', plan)
        forecast_ref = self._freeze(ledger, plan, predicted, reference, {}, 'planned', operation_key)
        result = {'plan_ref': plan_ref, 'forecast_ref': forecast_ref, **{key: value for key, value in plan.items() if key != 'prediction_episode_id'}}
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
