"""Private queue observations for A104 hpc."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104 import hpc_queue
import time




class QueueObservations:
    def _observe_queue(self, ledger, configuration):
        from gene_annotation_episode.episodic_workflow.root.a104.execution_guidance import resource_identity
        resource = resource_identity(ledger.commission['resource_id'], configuration)
        if self.memory:
            cached = self.memory.latest(resource, 'queue')
            if (cached['state'] == 'fresh' and cached['age_seconds'] <=
                    ledger.commission['limits']['queue_max_age_seconds']):
                return cached['data']
        value = hpc_queue.observe(configuration)
        if self.memory:
            self.memory.observe(resource, 'queue', value,
                observed_at=value['snapshot']['captured_at'], provenance=value['acquisition'])
        return value

    def _queue(self, ledger, reference, *, require_fresh=False):
        observation = ledger.read(reference)['snapshot']
        if require_fresh and time.time()-observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
            raise ValueError('fresh_queue_observation_required_before_planning')
        return observation

    async def _observe_resource_queue(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        reference = 'queue:' + hpc_queue.digest(operation_key)
        result = ledger.once(reference, 'queue', lambda: self._observe_queue(ledger, configuration))
        result = {'queue_ref': reference, 'features': [hpc_queue.features(result['snapshot'], candidate) for candidate in self._candidates(ledger)], 'snapshot': result['snapshot']}
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
