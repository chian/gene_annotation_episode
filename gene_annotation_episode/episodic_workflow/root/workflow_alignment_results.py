"""Root host ports defined by WorkflowAlignmentResults."""
from __future__ import annotations

class WorkflowAlignmentResults:

    def _alignment_site_records(self):
        from .alignment_site_action_records import AlignmentSiteActionRecords
        return AlignmentSiteActionRecords(self.workflow.store, self.workflow.run_id, sequence_reader=self.workflow.tools._sequence)

    def alignment_site_own_action_results(self, context, *, source, selection, after_decision_index, limit):
        return self._alignment_site_records().own_action_results(context, source=source, selection=selection, after_decision_index=after_decision_index, limit=limit)

    def alignment_site_frozen_facts(self, context, *, sources):
        return self._alignment_site_records().frozen_facts(context, sources=sources)

