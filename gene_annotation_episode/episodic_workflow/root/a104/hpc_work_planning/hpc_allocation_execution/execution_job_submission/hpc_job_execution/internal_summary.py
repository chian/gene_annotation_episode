"""Private A104 HPCExecution internal summary."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class HPCExecutionInternalSummary:

    def _with_selected_execution_task(self, context, value):
        assignment = plain(context.assignment)
        return value

    def decision_context(self, context, current_view):
        value = self._delegate(context).decision_context(context, current_view)
        return self._with_selected_execution_task(context, value)
