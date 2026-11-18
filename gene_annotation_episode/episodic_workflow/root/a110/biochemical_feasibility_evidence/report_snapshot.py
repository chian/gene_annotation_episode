"""Actual Scientific completion qualification and parent invocation identity at its original late callback boundary."""
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _original_runtime

def complete_scientific_snapshot(self, source, context, snapshot, facts):
    snapshot.update(initial_credit=self.journal.row('runtime_episodes', source.episode_id)['initial_credit'], credit=facts['credit'], controller_credit=self.source_controller_credit(source), episode_yield=facts['episode_yield'], parent_invocation_ref=self.services.scientific_parent_invocation(context))
