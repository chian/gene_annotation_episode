"""Private A104 internal summary."""
from __future__ import annotations
from .contracts import ContractError, _ACQUISITION_TOOLS, _READ_TOOLS, identity, json, plain

class LiteratureReportFacts:

    def facts(self, context, completion_snapshot):
        self._role(context.role)
        from gene_annotation_episode.episodic_workflow.root.a104.literature_task_credit import SCREENING, screening_answers, LEADS, lead_dispositions
        screening = {SCREENING: screening_answers(self.services.workflow.store, context)} if context.assignment.get('literature_task', {}).get('answer_kind') == 'screening' else {}
        if context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads':
            screening[LEADS] = lead_dispositions(self.services.workflow.store, context)
        if not self.rate_population:
            return screening
        return {**self._rate_facts(context, completion_snapshot['committed_record_refs']), **self.current_report_facts(context), **screening}

    def current_report_facts(self, context):
        if not self.assay_grading_population:
            return {}
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            return {}
        from gene_annotation_episode.episodic_workflow.root.a104.literature_sheet_updates import current_scoring_sheets
        from gene_annotation_episode.episodic_workflow.root.a104.literature_work_report import completed_work
        sheets = current_scoring_sheets(workflow.store, context)
        return {'literature_completed_work': completed_work(workflow.store, context), **({'literature_current_scoring_sheets': sheets} if sheets else {})}

