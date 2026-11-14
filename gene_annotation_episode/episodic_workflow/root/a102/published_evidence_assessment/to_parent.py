"""Private A102 literature to parent."""
from __future__ import annotations
from .source_contracts import validate_form

class SourceToParent:

    def fact_sources(self, role):
        self._role(role)
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import SCREENING, screening_schema, LEADS, lead_return_schema
        return {**(self._rate_fact_sources() if self.structure_population else {}), SCREENING: screening_schema(), LEADS: lead_return_schema()}

    def facts(self, context, completion_snapshot):
        self._role(context.role)
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import SCREENING, screening_answers, LEADS, lead_dispositions
        screening = {SCREENING: screening_answers(self.services.workflow.store, context)} if context.assignment.get('literature_task', {}).get('answer_kind') == 'screening' else {}
        if context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads':
            screening[LEADS] = lead_dispositions(self.services.workflow.store, context)
        if not self.structure_population:
            return screening
        return {**self._rate_facts(context, completion_snapshot['committed_record_refs']), **self.current_report_facts(context), **screening}

    def current_report_facts(self, context):
        return {}

    def _rate_fact_sources(self):
        if not self.structure_population:
            return {}
        from gene_annotation_episode.episodic_workflow.root.a102.a102_literature_bindings import SOURCE_NAME, fact_source_definition
        return {SOURCE_NAME: fact_source_definition()}

    def _rate_facts(self, context, references):
        result = {}
        for namespace, requested_field, provider, defaults, repository in self._population_routes():
            selected = [reference for reference in dict.fromkeys(references) if reference in context.received_record_refs and (record := self.services.read_record(reference)).get('record_type') == 'source' and (record.get('provider') == provider)]
            result[namespace] = repository().fact_cells(context, selected, components=context.assignment.get(requested_field, defaults))
        return result

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)
