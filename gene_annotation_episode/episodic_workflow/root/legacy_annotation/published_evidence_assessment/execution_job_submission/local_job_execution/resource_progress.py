"""Original fixed local execution progress responsibilities; source candidate."""
from __future__ import annotations


class LocalProgress:
    def completion_for_action(self,context,operation_key):
        proof=self.state(context).completion_proof()
        return proof if proof is not None and proof['operation_key']==operation_key else None

    def practical_estimator(self,context):
        from gene_annotation_episode.episodic_workflow.root.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(self.state(context).verify_completion)

    def credit_view(self,context,receiver_selection):return self.state(context).credit_view()

