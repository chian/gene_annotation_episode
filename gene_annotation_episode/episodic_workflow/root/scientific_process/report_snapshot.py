"""Scientific completion credit, yield and parent-invocation qualification."""
from __future__ import annotations

def complete_scientific_snapshot(self, source, context, snapshot, facts):
    snapshot.update(initial_credit=self.journal.row('runtime_episodes', source.episode_id)['initial_credit'], credit=facts['credit'], controller_credit=self.source_controller_credit(source), episode_yield=facts['episode_yield'], parent_invocation_ref=self.services.scientific_parent_invocation(context))

from gene_annotation_episode.episodic_workflow.root import report_validation as _original_report_validation
