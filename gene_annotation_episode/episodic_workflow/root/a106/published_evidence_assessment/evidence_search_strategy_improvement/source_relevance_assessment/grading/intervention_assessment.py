from __future__ import annotations
from ..source_contracts import ContractError, validate_schema

class InterventionAssessment:

    def _required_grading_repository(self, context=None):
        return None

    def _intervention_source_cells(self, context, namespace, sheet_ref, components):
        if namespace == 'bvbrc_application_outcomes':
            from ..received_evidence import received_application_rows
            return received_application_rows(self.services, context, sheet_ref, components)
        if namespace == 'literature_controlled_response_component_cells' and self.controlled_response_population:
            rows = self._controlled_response_repository().fact_cells(context, [sheet_ref], components=components)
            validate_schema(rows, self._rate_fact_sources()[namespace]['report_schema'])
            return rows
        if namespace == 'literature_gel_component_cells' and self.gel_population:
            rows = self._gel_repository().fact_cells(context, [sheet_ref], components=components)
            validate_schema(rows, self._rate_fact_sources()[namespace]['report_schema'])
            return rows
        for name, _, _, _, repository in self._population_routes(context):
            if name == namespace:
                rows = repository().fact_cells(context, [sheet_ref], components=components)
                schema = self._rate_fact_sources()[namespace]['report_schema']
                validate_schema(rows, schema)
                return rows
        raise ContractError('assay_grading_reader_namespace_unbound')

    def _intervention_grading_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_storage import LiteratureInterventionRepository
        if not hasattr(self, '_intervention_grading_repo'):
            self._intervention_grading_repo = LiteratureInterventionRepository(self.services.workflow.store, self.services.workflow.run_id, read_cells=self._intervention_source_cells)
        return self._intervention_grading_repo
