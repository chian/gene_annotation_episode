"""Private portfolio comparison for A102 hpc_execution."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102 import hpc_queue
from gene_annotation_episode.episodic_workflow.root.a102.library import hpc_prediction as prediction




class PortfolioComparison:
    @staticmethod
    def _candidates(ledger):
        return ledger.commission['candidates']+[row['body'] for row in ledger.records('candidate')]

    @staticmethod
    def _features(candidate, queue):
        return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            'queue:'+candidate['queue']: 1.,
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}

    def _comparisons(self, ledger, model_ref, queue_ref):
        model = ledger.read(model_ref)
        observed = self._queue(ledger, queue_ref)
        actual = [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions'] if row['kind'] == 'actual']
        results = []
        for candidate in self._candidates(ledger):
            queue = hpc_queue.features(observed, candidate)
            forecast = prediction.predict(model, self._features(candidate, queue))
            row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                     ledger.commission['preferences'], already_credited=actual)
            row['queue_features'] = queue
            results.append(row)
        return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)

    def _candidate(self, ledger, plan):
        return next(row for row in self._candidates(ledger) if row['id'] == plan['candidate_id'])

    async def _compare_portfolios(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        try:
            result = {'comparisons': self._comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
        except (ValueError, KeyError) as error:
            return ledger.save_action(operation_key, selection, {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), 'recovery': 'Use a model_ref from hpc.model.fit or hpc_model_ref and a queue_ref from hpc.queue.observe or hpc_queue_refs; a resource identity is not a queue observation.'}})
        result['comparison_ref'] = ledger.put('comparison', {**result, **arguments, 'episode_id': context.episode_id, 'operation_key': operation_key})
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
