"""Private A104 API internal summary."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class APIInternalSummary:

    def decision_context(self, context, current_view):
        value = {'execution_assignment': plain(context.assignment), 'execution_progress': self.facts(context, {})}
        callback = getattr(self.api_execution, 'decision_context', None)
        if callback is not None:
            value.update(callback(context, current_view))
        return self._with_selected_execution_task(context, value)
