from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.family import member_for_role

from .report_fields import LiteratureReportFields

class LiteratureScientificRecords(LiteratureReportFields):
    def facts(self, context, completion_snapshot):
        self._role(context.role)
        from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import SCREENING
        from .task_answers import screening_answers
        from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import LEADS
        from .task_answers import lead_dispositions
        screening = ({SCREENING: screening_answers(self.services.workflow.store, context)}
            if context.assignment.get('literature_task', {}).get('answer_kind') == 'screening' else {})
        if context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads':
            screening[LEADS] = lead_dispositions(self.services.workflow.store, context)
        if not (self.rate_population or self._enabled('a108_context_evidence', context)):
            return screening
        return {**self._rate_facts(context, completion_snapshot["committed_record_refs"]),
            **self.current_report_facts(context), **screening}

    def current_report_facts(self, context):
        if not (self._enabled('a108_context_evidence', context) or
                self._enabled('assay_grading_population', context) and not self._enabled('a106_intervention', context)):
            return {}
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            return {}
        from gene_annotation_episode.episodic_workflow.root.literature_sheet_updates import current_scoring_sheets
        from gene_annotation_episode.episodic_workflow.root.literature_completed_work_projection import completed_work
        sheets = current_scoring_sheets(workflow.store, context)
        return {'literature_completed_work': completed_work(workflow.store, context),
            **({'literature_current_scoring_sheets': sheets} if sheets else {})}

