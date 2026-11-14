"""Private A104 API received practical state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class APIReceivedPracticalState:

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        context.role
        return self._practical[assignment['resource_id']]

    def _practical_context(self, context):
        return context

