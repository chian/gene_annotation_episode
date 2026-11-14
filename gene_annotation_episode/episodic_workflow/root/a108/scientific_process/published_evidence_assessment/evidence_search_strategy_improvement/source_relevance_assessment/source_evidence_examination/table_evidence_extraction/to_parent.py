from __future__ import annotations
'to parent for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.source_contracts import replace, validate_form

class LiteratureReport:

    def fact_sources(self, role):
        self._role(role)
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.goal import SCREENING
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.credit import screening_schema
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.goal import LEADS
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.credit import lead_return_schema
        return {**self._a108_fact_sources(), SCREENING: screening_schema(), LEADS: lead_return_schema()}

    def facts(self, context, completion_snapshot):
        self._role(context.role)
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.goal import SCREENING
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.credit import screening_answers
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.goal import LEADS
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.credit import lead_dispositions
        screening = {SCREENING: screening_answers(self.services.workflow.store, context)} if context.assignment.get('literature_task', {}).get('answer_kind') == 'screening' else {}
        if context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads':
            screening[LEADS] = lead_dispositions(self.services.workflow.store, context)
        return {**self._a108_facts(context, completion_snapshot['committed_record_refs']), **self.current_report_facts(context), **screening}

    def current_report_facts(self, context):
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            return {}
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_sheet_updates import current_scoring_sheets
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_work_report import completed_work
        sheets = current_scoring_sheets(workflow.store, context)
        return {'literature_completed_work': completed_work(workflow.store, context), **({'literature_current_scoring_sheets': sheets} if sheets else {})}

    def _a108_fact_sources(self):
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_storage import grading_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import aggregation_cells_schema
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_numerical_contracts import RETURN_MEANINGS
        return {name: {'type': 'array', 'meaning': RETURN_MEANINGS[name], 'report_schema': schema()} for name, schema in (('literature_a108_grading_cells', grading_cells_schema), ('literature_a108_aggregation_cells', aggregation_cells_schema))}

    def _a108_facts(self, context, references):
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_sheet_updates import current_sheet_refs
        current = current_sheet_refs(self.services.workflow.store, context)
        references = list(dict.fromkeys([*references, *current]))
        context = replace(context, received_record_refs=tuple(dict.fromkeys([*context.received_record_refs, *current])))
        result = {}
        for namespace, requested_field, provider, repository in self._population_routes():
            adapter = repository()
            selected = []
            for reference in references:
                if reference not in context.received_record_refs:
                    continue
                row = self.services.read_record(reference)
                if row.get('record_type') == 'source' and row.get('provider') == provider:
                    if row.get('version') != adapter.record_version:
                        continue
                    selected.append(reference)
            result[namespace] = adapter.fact_cells(context, selected, components=tuple(context.assignment.get(requested_field, [])))
        return result

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)
