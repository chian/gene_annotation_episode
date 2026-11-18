"""Private A104 source repositories."""
from __future__ import annotations
from .contracts import ContractError, json, validate_schema

from .repository_display import LiteratureRepositoryDisplay

from .population_routes import LiteraturePopulationRoutes

class LiteratureRepositories(LiteraturePopulationRoutes, LiteratureRepositoryDisplay):

    def literature_rate_repository(self):
        """Expose the selected source-sheet adapter; own no decisions or credit."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_rate_storage import LiteratureRateRepository
        if not hasattr(self, '_literature_rate_repository'):
            self._literature_rate_repository = LiteratureRateRepository(self.services.workflow.store, self.services.workflow.run_id)
        else:
            self._literature_rate_repository._ensure_storage()
        return self._literature_rate_repository

    def literature_calibration_recovery_repository(self):
        """Access selected recovery controls and exact saved numerical subsets."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
        if not hasattr(self, '_literature_calibration_recovery_repository'):
            self._literature_calibration_recovery_repository = LiteratureCalibrationRecoveryRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_calibration_recovery_repository

    def literature_rate_observation_repository(self):
        """Access selected original XLSX entries and saved requested subsets."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_rate_observation_storage import LiteratureRateObservationRepository
        if not hasattr(self, '_literature_rate_observation_repository'):
            self._literature_rate_observation_repository = LiteratureRateObservationRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_rate_observation_repository

    def literature_rate_replicate_repository(self):
        """Access explicitly selected raw-rate tables and saved typed subsets."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_rate_replicate_storage import LiteratureRateReplicateRepository
        if not hasattr(self, '_literature_rate_replicate_repository'):
            self._literature_rate_replicate_repository = LiteratureRateReplicateRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_rate_replicate_repository

    def literature_quantity_repository(self):
        """Access committed source-native quantities without owning episode work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_quantity_storage import LiteratureQuantityRepository
        if not hasattr(self, '_literature_quantity_repository'):
            self._literature_quantity_repository = LiteratureQuantityRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_quantity_repository

    def literature_assay_repository(self):
        """Access source-bound numerical assay calculations; own no decisions."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_assay_storage import LiteratureAssayRepository
        if not hasattr(self, '_literature_assay_repository'):
            self._literature_assay_repository = LiteratureAssayRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_assay_repository

    def literature_amount_repository(self):
        """Access selected source amount components without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_amount_storage import LiteratureAmountRepository
        if not hasattr(self, '_literature_amount_repository'):
            self._literature_amount_repository = LiteratureAmountRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_amount_repository

    def literature_optical_repository(self):
        """Access selected optical q/Vq inputs without choosing scientific work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_optical_storage import LiteratureOpticalRepository
        if not hasattr(self, '_literature_optical_repository'):
            self._literature_optical_repository = LiteratureOpticalRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_optical_repository

    def literature_kinetic_repository(self):
        """Access selected native kinetic parameter components, without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_kinetic_storage import LiteratureKineticRepository
        if not hasattr(self, '_literature_kinetic_repository'):
            self._literature_kinetic_repository = LiteratureKineticRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_kinetic_repository

    def literature_binding_interaction_repository(self):
        """Access selected four-cell source binding interaction components."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_interaction_storage import LiteratureBindingInteractionRepository
        if not hasattr(self, '_literature_binding_interaction_repository'):
            self._literature_binding_interaction_repository = LiteratureBindingInteractionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_binding_interaction_repository

    def literature_ratio_repository(self):
        """Access retained relative-signal components without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_ratio_storage import LiteratureRatioRepository
        if not hasattr(self, '_literature_ratio_repository'):
            self._literature_ratio_repository = LiteratureRatioRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_ratio_repository

    def literature_binding_repository(self):
        """Access saved source binding parameters without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_storage import LiteratureBindingRepository
        if not hasattr(self, '_literature_binding_repository'):
            self._literature_binding_repository = LiteratureBindingRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_binding_repository

    def literature_binding_model_repository(self):
        """Read and populate explicitly selected conditional binding models."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_model_storage import LiteratureBindingModelRepository
        if not hasattr(self, '_literature_binding_model_repository'):
            self._literature_binding_model_repository = LiteratureBindingModelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_binding_model_repository

    def literature_transport_repository(self):
        """Access explicitly selected source kinetic-response calculations."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_transport_storage import LiteratureTransportRepository
        if not hasattr(self, '_literature_transport_repository'):
            self._literature_transport_repository = LiteratureTransportRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_transport_repository

    def literature_figure_repository(self):
        """Access selected native experimental figure measurements."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_figure_storage import LiteratureFigureRepository
        if not hasattr(self, '_literature_figure_repository'):
            self._literature_figure_repository = LiteratureFigureRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_figure_repository

    def literature_ratio_source_repository(self, *, evidence_origin='reported_source'):
        """Access selected native source-signal cells with the caller's bound origin."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_ratio_source_storage import LiteratureRatioSourceRepository
        if not hasattr(self, '_literature_ratio_source_repositories'):
            self._literature_ratio_source_repositories = {}
        if evidence_origin not in self._literature_ratio_source_repositories:
            repository = LiteratureRatioSourceRepository(self.services.workflow.store, self.services.workflow.run_id, evidence_origin=evidence_origin)
            self._literature_ratio_source_repositories[evidence_origin] = repository
        return self._literature_ratio_source_repositories[evidence_origin]

    def literature_controlled_response_repository(self, *, expected_descriptor=None, evidence_origin='reported_source'):
        """Access the caller-bound controlled-response repository; choose no work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_controlled_response_storage import LiteratureControlledResponseRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_controlled_response_repositories'):
            self._literature_controlled_response_repositories = {}
        if key not in self._literature_controlled_response_repositories:
            self._literature_controlled_response_repositories[key] = LiteratureControlledResponseRepository(self.services.workflow.store, self.services.workflow.run_id, expected_descriptor=expected_descriptor, evidence_origin=evidence_origin)
        return self._literature_controlled_response_repositories[key]

    def literature_gel_repository(self, *, expected_descriptor=None, evidence_origin='reported_source'):
        """Access the caller-bound gel repository; choose no work."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_gel_storage import LiteratureGelRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_gel_repositories'):
            self._literature_gel_repositories = {}
        if key not in self._literature_gel_repositories:
            self._literature_gel_repositories[key] = LiteratureGelRepository(self.services.workflow.store, self.services.workflow.run_id, expected_descriptor=expected_descriptor, evidence_origin=evidence_origin)
        return self._literature_gel_repositories[key]

    def _endpoint_signal_repository(self):
        """Lazy selected adapter; discovery and reconstruction create no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_endpoint_signal_storage import LiteratureEndpointSignalRepository
        if not hasattr(self, '_endpoint_signal_repo'):
            self._endpoint_signal_repo = LiteratureEndpointSignalRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._endpoint_signal_repo

    def _concentration_window_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_concentration_window_storage import LiteratureConcentrationWindowRepository
        if not hasattr(self, '_concentration_window_repo'):
            self._concentration_window_repo = LiteratureConcentrationWindowRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._concentration_window_repo

    def _measurement_comparison_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_measurement_comparison_storage import LiteratureMeasurementComparisonRepository
        if not hasattr(self, '_measurement_comparison_repo'):
            self._measurement_comparison_repo = LiteratureMeasurementComparisonRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._measurement_comparison_repo

    def _summary_precision_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_kinetic_summary_precision_storage import LiteratureKineticSummaryPrecisionRepository
        if not hasattr(self, '_summary_precision_repo'):
            self._summary_precision_repo = LiteratureKineticSummaryPrecisionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._summary_precision_repo

    def _rate_grid_repository(self):
        return self.literature_rate_observation_repository().grid_projection()

    def _compiled_assay_repository(self):
        """Lazy common-sheet compilation; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_compiled_assay_storage import LiteratureCompiledAssayRepository
        if not hasattr(self, '_compiled_assay_repo'):
            self._compiled_assay_repo = LiteratureCompiledAssayRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._compiled_assay_repo

    def _compiled_assay_v2_repository(self):
        return self._compiled_assay_repository().v2_projection()

    def _compiled_assay_v3_repository(self):
        return self._compiled_assay_repository().v3_projection()

    def _product_coupling_repository(self):
        """Lazy selected product/cofactor adapter; discovery creates no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_product_coupling_storage import LiteratureProductCouplingRepository
        if not hasattr(self, '_product_coupling_repo'):
            self._product_coupling_repo = LiteratureProductCouplingRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._product_coupling_repo

    def _measurement_validation_repository(self):
        """Lazy selected precision/control adapter; discovery creates no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_measurement_validation_storage import LiteratureMeasurementValidationRepository
        if not hasattr(self, '_measurement_validation_repo'):
            self._measurement_validation_repo = LiteratureMeasurementValidationRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._measurement_validation_repo

    def _ion_discrimination_repository(self):
        """Optional lazy adapter; discovery and saved reads create no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_ion_discrimination_storage import LiteratureIonDiscriminationRepository
        if not hasattr(self, '_ion_discrimination_repo'):
            self._ion_discrimination_repo = LiteratureIonDiscriminationRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._ion_discrimination_repo

    def _channel_repository(self):
        """Lazy adapter; only a selected population reads electrical sources."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_channel_storage import LiteratureChannelRepository
        if not hasattr(self, '_channel_repo'):
            self._channel_repo = LiteratureChannelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._channel_repo

    def _completion_time_repository(self):
        """Lazy selected-operation adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_completion_time_storage import LiteratureCompletionTimeRepository
        if not hasattr(self, '_completion_time_repo'):
            self._completion_time_repo = LiteratureCompletionTimeRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._completion_time_repo

    def _active_site_repository(self):
        """Lazy selected-operation adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_active_site_storage import LiteratureActiveSiteRepository
        if not hasattr(self, '_active_site_repo'):
            self._active_site_repo = LiteratureActiveSiteRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._active_site_repo

    def _assay_grading_source_cells(self, context, namespace, sheet_ref, components):
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
        from gene_annotation_episode.episodic_workflow.root.a104.literature_assay_grading_storage import LiteratureAssayGradingRepository
        if not hasattr(self, '_assay_grading_repo'):
            self._assay_grading_repo = LiteratureAssayGradingRepository(self.services.workflow.store, self.services.workflow.run_id, read_cells=self._assay_grading_source_cells)
        return self._assay_grading_repo

    def _a105_aggregation_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_a105_aggregation_storage import LiteratureA105AggregationRepository
        if not hasattr(self, '_a105_aggregation_repo'):
            self._a105_aggregation_repo = LiteratureA105AggregationRepository(self.services.workflow.store, self.services.workflow.run_id, read_cells=lambda context, sheet_ref, components: self._assay_grading_repository().fact_cells(context, [sheet_ref], components=components))
        return self._a105_aggregation_repo

    def _parent_depletion_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_parent_depletion_storage import LiteratureParentDepletionRepository
        if not hasattr(self, '_parent_depletion_repo'):
            self._parent_depletion_repo = LiteratureParentDepletionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._parent_depletion_repo

    def _stoichiometric_balance_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_stoichiometric_balance_storage import LiteratureStoichiometricBalanceRepository
        if not hasattr(self, '_stoichiometric_balance_repo'):
            self._stoichiometric_balance_repo = LiteratureStoichiometricBalanceRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._stoichiometric_balance_repo

    def _product_partition_repository(self):
        """Lazy source-composition adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_product_partition_storage import LiteratureProductPartitionRepository
        if not hasattr(self, '_product_partition_repo'):
            self._product_partition_repo = LiteratureProductPartitionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._product_partition_repo

    def _binding_interaction_model_repository(self):
        """Optional adapter; construction and saved reads install no tables."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_interaction_model_storage import LiteratureBindingInteractionModelRepository
        if not hasattr(self, '_binding_interaction_model_repo'):
            self._binding_interaction_model_repo = LiteratureBindingInteractionModelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._binding_interaction_model_repo

    def _kinetic_model_repository(self):
        """Optional local adapter; discovery and saved reads install no tables."""
        from gene_annotation_episode.episodic_workflow.root.a104.literature_kinetic_model_storage import LiteratureKineticModelRepository
        if not hasattr(self, '_kinetic_model_repo'):
            self._kinetic_model_repo = LiteratureKineticModelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._kinetic_model_repo

    def _ratio_source_repository(self):
        return self.literature_ratio_source_repository(evidence_origin=self.ratio_source_evidence_origin)

    def _controlled_response_repository(self):
        return self.literature_controlled_response_repository(expected_descriptor=self._controlled_response_descriptor, evidence_origin=self.controlled_response_evidence_origin)

    def _gel_repository(self):
        return self.literature_gel_repository(expected_descriptor=self._gel_descriptor, evidence_origin=self.gel_evidence_origin)

    def _native_rate_meaning_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a104.literature_rate_meaning_delivery import source_meaning_projection
        return source_meaning_projection(self.literature_rate_repository())

