"""Private portfolio comparison for A103 prediction."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103 import hpc_queue
from gene_annotation_episode.episodic_workflow.root.a103.library import hpc_prediction as prediction



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
