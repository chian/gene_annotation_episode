"""Private queue observations for A107 prediction."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107 import hpc_queue
import time



class QueueObservations:
    def _observe_queue(self, ledger, configuration):
        from gene_annotation_episode.episodic_workflow.root.a107.execution_guidance import resource_identity
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
