"""Private A110 Launch scientific reference support"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class LaunchScientificReferenceSupport:

    def _matches_flux_balance_assignment(self, context, assignment):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, materialized_assignment
        original = materialized_assignment(self.store, context) if is_compact_assignment(plain(context.assignment)) else plain(context.assignment)
        return canonical(original) == canonical(assignment)
