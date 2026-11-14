"""Private A104 to parent."""
from __future__ import annotations
from .contracts import reference_in_context, validate_form

class LiteratureReportFields:

    def fact_sources(self, role):
        self._role(role)
        from gene_annotation_episode.episodic_workflow.root.a104.literature_task_credit import SCREENING, screening_schema, LEADS, lead_return_schema
        return {**(self._rate_fact_sources() if self.rate_population else {}), SCREENING: screening_schema(), LEADS: lead_return_schema()}

