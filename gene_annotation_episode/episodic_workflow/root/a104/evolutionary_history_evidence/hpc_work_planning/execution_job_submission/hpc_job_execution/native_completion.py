"""Private original A104 HPCExecution service native_completion."""
from __future__ import annotations

class HPCExecutionNativeCompletion:

    def completion_for_action(self, context, operation_key):
        proof = self.state(context).completion_proof()
        return proof if proof is not None and proof['operation_key'] == operation_key else None

    def practical_estimator(self, context):
        from gene_annotation_episode.episodic_workflow.root.a104.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(self.state(context).verify_completion)
