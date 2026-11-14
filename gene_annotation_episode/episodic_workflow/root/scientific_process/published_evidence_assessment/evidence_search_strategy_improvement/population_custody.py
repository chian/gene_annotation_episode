from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.family import member_for_role

from .population_display import LiteraturePopulationDisplay

from .population_routes import LiteraturePopulationRoutes

from .numerical_report_fields import LiteratureNumericalReportFields

from .numerical_report_projection import LiteratureNumericalReportProjection

class LiteraturePopulationCustody(LiteratureNumericalReportProjection, LiteratureNumericalReportFields, LiteraturePopulationRoutes, LiteraturePopulationDisplay):
    def _endpoint_signal_repository(self):
        """Lazy selected adapter; discovery and reconstruction create no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_endpoint_signal_storage import LiteratureEndpointSignalRepository
        if not hasattr(self, '_endpoint_signal_repo'):
            self._endpoint_signal_repo = LiteratureEndpointSignalRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._endpoint_signal_repo

    def _concentration_window_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_concentration_window_storage import LiteratureConcentrationWindowRepository
        if not hasattr(self, '_concentration_window_repo'):
            self._concentration_window_repo = LiteratureConcentrationWindowRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._concentration_window_repo

    def _measurement_comparison_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_measurement_comparison_storage import LiteratureMeasurementComparisonRepository
        if not hasattr(self, '_measurement_comparison_repo'):
            self._measurement_comparison_repo = LiteratureMeasurementComparisonRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._measurement_comparison_repo

    def _summary_precision_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_kinetic_summary_precision_storage import LiteratureKineticSummaryPrecisionRepository
        if not hasattr(self, '_summary_precision_repo'):
            self._summary_precision_repo = LiteratureKineticSummaryPrecisionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._summary_precision_repo

    def _rate_grid_repository(self):
        return self.services.literature_rate_observation_repository().grid_projection()

    def _compiled_assay_repository(self):
        """Lazy common-sheet compilation; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage import LiteratureCompiledAssayRepository
        if not hasattr(self, "_compiled_assay_repo"):
            self._compiled_assay_repo = LiteratureCompiledAssayRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._compiled_assay_repo

    def _compiled_assay_v2_repository(self):
        return self._compiled_assay_repository().v2_projection()

    def _compiled_assay_v3_repository(self):
        return self._compiled_assay_repository().v3_projection()

    def _product_coupling_repository(self):
        """Lazy selected product/cofactor adapter; discovery creates no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_product_coupling_storage import LiteratureProductCouplingRepository
        if not hasattr(self, "_product_coupling_repo"):
            self._product_coupling_repo = LiteratureProductCouplingRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._product_coupling_repo

    def _measurement_validation_repository(self):
        """Lazy selected precision/control adapter; discovery creates no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_measurement_validation_storage import LiteratureMeasurementValidationRepository
        if not hasattr(self, "_measurement_validation_repo"):
            self._measurement_validation_repo = LiteratureMeasurementValidationRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._measurement_validation_repo

    def _ion_discrimination_repository(self):
        """Optional lazy adapter; discovery and saved reads create no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_ion_discrimination_storage import LiteratureIonDiscriminationRepository
        if not hasattr(self, "_ion_discrimination_repo"):
            self._ion_discrimination_repo = LiteratureIonDiscriminationRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._ion_discrimination_repo

    def _channel_repository(self):
        """Lazy adapter; only a selected population reads electrical sources."""
        from gene_annotation_episode.episodic_workflow.root.literature_channel_storage import LiteratureChannelRepository
        if not hasattr(self, "_channel_repo"):
            self._channel_repo = LiteratureChannelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._channel_repo

    def _completion_time_repository(self):
        """Lazy selected-operation adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_completion_time_storage import LiteratureCompletionTimeRepository
        if not hasattr(self, "_completion_time_repo"):
            self._completion_time_repo = LiteratureCompletionTimeRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._completion_time_repo

    def _active_site_repository(self):
        """Lazy selected-operation adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_active_site_storage import LiteratureActiveSiteRepository
        if not hasattr(self, "_active_site_repo"):
            self._active_site_repo = LiteratureActiveSiteRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._active_site_repo

    def _assay_grading_source_cells(self, context, namespace, sheet_ref, components):
        # A source identifier does not grant a receiver the private child sheet.
        # fact_cells returns this owner's cells or exactly admitted typed rows.
        if namespace == 'bvbrc_application_outcomes' and self._enabled('a106_intervention', context):
            from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.analysis_contract import received_application_rows
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
            if name == namespace and name != 'literature_assay_grading_cells':
                rows = repository().fact_cells(context, [sheet_ref], components=components)
                schema = self._rate_fact_sources()[namespace]['report_schema']
                validate_schema(rows, schema)
                return rows
        raise ContractError('assay_grading_reader_namespace_unbound')

    def _assay_grading_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_assay_grading_storage import LiteratureAssayGradingRepository
        if not hasattr(self, '_assay_grading_repo'):
            self._assay_grading_repo = LiteratureAssayGradingRepository(
                self.services.workflow.store, self.services.workflow.run_id,
                read_cells=self._assay_grading_source_cells)
        return self._assay_grading_repo

    def _intervention_grading_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_intervention_storage import LiteratureInterventionRepository
        if not hasattr(self, '_intervention_grading_repo'):
            self._intervention_grading_repo = LiteratureInterventionRepository(
                self.services.workflow.store, self.services.workflow.run_id,
                read_cells=self._assay_grading_source_cells)
        return self._intervention_grading_repo

    def _perturbation_operand_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_perturbation_operands import LiteraturePerturbationOperandProjection
        if not hasattr(self, '_perturbation_operand_repo'):
            self._perturbation_operand_repo = LiteraturePerturbationOperandProjection(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._perturbation_operand_repo

    def _a108_grading_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_a108_grading_storage import LiteratureA108GradingRepository
        if not hasattr(self, '_a108_grading_repo'):
            self._a108_grading_repo = LiteratureA108GradingRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._a108_grading_repo

    def _a108_aggregation_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_a108_aggregation_storage import LiteratureA108AggregationRepository
        if not hasattr(self, '_a108_aggregation_repo'):
            self._a108_aggregation_repo = LiteratureA108AggregationRepository(
                self.services.workflow.store, self.services.workflow.run_id,
                read_cells=lambda context, sheet_ref, components:
                    self._a108_grading_repository().fact_cells(context, [sheet_ref], components=components))
        return self._a108_aggregation_repo

    def _a105_aggregation_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_a105_aggregation_storage import LiteratureA105AggregationRepository
        if not hasattr(self, '_a105_aggregation_repo'):
            self._a105_aggregation_repo = LiteratureA105AggregationRepository(
                self.services.workflow.store, self.services.workflow.run_id,
                read_cells=lambda context, sheet_ref, components:
                    self._assay_grading_repository().fact_cells(context, [sheet_ref], components=components))
        return self._a105_aggregation_repo

    def _a106_subscore_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
        if not hasattr(self, '_a106_subscore_repo'):
            self._a106_subscore_repo = LiteratureA106SubscoreRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._a106_subscore_repo

    def _parent_depletion_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_parent_depletion_storage import LiteratureParentDepletionRepository
        if not hasattr(self,'_parent_depletion_repo'):
            self._parent_depletion_repo=LiteratureParentDepletionRepository(
                self.services.workflow.store,self.services.workflow.run_id)
        return self._parent_depletion_repo

    def _stoichiometric_balance_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_stoichiometric_balance_storage import LiteratureStoichiometricBalanceRepository
        if not hasattr(self, '_stoichiometric_balance_repo'):
            self._stoichiometric_balance_repo = LiteratureStoichiometricBalanceRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._stoichiometric_balance_repo

    def _product_partition_repository(self):
        """Lazy source-composition adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.literature_product_partition_storage import LiteratureProductPartitionRepository
        if not hasattr(self, "_product_partition_repo"):
            self._product_partition_repo = LiteratureProductPartitionRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._product_partition_repo

    def _binding_interaction_model_repository(self):
        """Optional adapter; construction and saved reads install no tables."""
        from gene_annotation_episode.episodic_workflow.root.literature_binding_interaction_model_storage import LiteratureBindingInteractionModelRepository
        if not hasattr(self, "_binding_interaction_model_repo"):
            self._binding_interaction_model_repo = LiteratureBindingInteractionModelRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._binding_interaction_model_repo

    def _kinetic_model_repository(self):
        """Optional local adapter; discovery and saved reads install no tables."""
        from gene_annotation_episode.episodic_workflow.root.literature_kinetic_model_storage import LiteratureKineticModelRepository
        if not hasattr(self, "_kinetic_model_repo"):
            self._kinetic_model_repo = LiteratureKineticModelRepository(
                self.services.workflow.store, self.services.workflow.run_id)
        return self._kinetic_model_repo

    def _ratio_source_repository(self):
        return self.services.literature_ratio_source_repository(
            evidence_origin=self.ratio_source_evidence_origin)

    def _controlled_response_repository(self):
        return self.services.literature_controlled_response_repository(
            expected_descriptor=self._controlled_response_descriptor,
            evidence_origin=self.controlled_response_evidence_origin)
    def _gel_repository(self):
        return self.services.literature_gel_repository(
            expected_descriptor=self._gel_descriptor,
            evidence_origin=self.gel_evidence_origin)

    def _native_rate_meaning_repository(self):
        from gene_annotation_episode.episodic_workflow.root.literature_rate_meaning_delivery import source_meaning_projection
        return source_meaning_projection(self.services.literature_rate_repository())

