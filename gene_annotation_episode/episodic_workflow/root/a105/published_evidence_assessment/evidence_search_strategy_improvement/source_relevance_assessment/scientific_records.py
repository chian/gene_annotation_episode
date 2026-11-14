from __future__ import annotations
'Private scientific records responsibility for literature_search.'
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_contracts import json, validate_schema
from gene_annotation_episode.domain import ContractError

class LiteratureScientificRecords:

    def literature_rate_repository(self):
        """Expose the selected source-sheet adapter; own no decisions or credit."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_storage import LiteratureRateRepository
        if not hasattr(self, '_literature_rate_repository'):
            self._literature_rate_repository = LiteratureRateRepository(self.services.workflow.store, self.services.workflow.run_id)
        else:
            self._literature_rate_repository._ensure_storage()
        return self._literature_rate_repository

    def literature_calibration_recovery_repository(self):
        """Access selected recovery controls and exact saved numerical subsets."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
        if not hasattr(self, '_literature_calibration_recovery_repository'):
            self._literature_calibration_recovery_repository = LiteratureCalibrationRecoveryRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_calibration_recovery_repository

    def literature_rate_observation_repository(self):
        """Access selected original XLSX entries and saved requested subsets."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_storage import LiteratureRateObservationRepository
        if not hasattr(self, '_literature_rate_observation_repository'):
            self._literature_rate_observation_repository = LiteratureRateObservationRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_rate_observation_repository

    def literature_rate_replicate_repository(self):
        """Access explicitly selected raw-rate tables and saved typed subsets."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_replicate_storage import LiteratureRateReplicateRepository
        if not hasattr(self, '_literature_rate_replicate_repository'):
            self._literature_rate_replicate_repository = LiteratureRateReplicateRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_rate_replicate_repository

    def literature_quantity_repository(self):
        """Access committed source-native quantities without owning episode work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_quantity_storage import LiteratureQuantityRepository
        if not hasattr(self, '_literature_quantity_repository'):
            self._literature_quantity_repository = LiteratureQuantityRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_quantity_repository

    def literature_assay_repository(self):
        """Access source-bound numerical assay calculations; own no decisions."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_storage import LiteratureAssayRepository
        if not hasattr(self, '_literature_assay_repository'):
            self._literature_assay_repository = LiteratureAssayRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_assay_repository

    def literature_amount_repository(self):
        """Access selected source amount components without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_amount_storage import LiteratureAmountRepository
        if not hasattr(self, '_literature_amount_repository'):
            self._literature_amount_repository = LiteratureAmountRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_amount_repository

    def literature_optical_repository(self):
        """Access selected optical q/Vq inputs without choosing scientific work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_optical_storage import LiteratureOpticalRepository
        if not hasattr(self, '_literature_optical_repository'):
            self._literature_optical_repository = LiteratureOpticalRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_optical_repository

    def literature_kinetic_repository(self):
        """Access selected native kinetic parameter components, without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_storage import LiteratureKineticRepository
        if not hasattr(self, '_literature_kinetic_repository'):
            self._literature_kinetic_repository = LiteratureKineticRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_kinetic_repository

    def literature_binding_interaction_repository(self):
        """Access selected four-cell source binding interaction components."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_storage import LiteratureBindingInteractionRepository
        if not hasattr(self, '_literature_binding_interaction_repository'):
            self._literature_binding_interaction_repository = LiteratureBindingInteractionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_binding_interaction_repository

    def literature_ratio_repository(self):
        """Access retained relative-signal components without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_storage import LiteratureRatioRepository
        if not hasattr(self, '_literature_ratio_repository'):
            self._literature_ratio_repository = LiteratureRatioRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_ratio_repository

    def literature_binding_repository(self):
        """Access saved source binding parameters without choosing work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_storage import LiteratureBindingRepository
        if not hasattr(self, '_literature_binding_repository'):
            self._literature_binding_repository = LiteratureBindingRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_binding_repository

    def literature_binding_model_repository(self):
        """Read and populate explicitly selected conditional binding models."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_model_storage import LiteratureBindingModelRepository
        if not hasattr(self, '_literature_binding_model_repository'):
            self._literature_binding_model_repository = LiteratureBindingModelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_binding_model_repository

    def literature_transport_repository(self):
        """Access explicitly selected source kinetic-response calculations."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_transport_storage import LiteratureTransportRepository
        if not hasattr(self, '_literature_transport_repository'):
            self._literature_transport_repository = LiteratureTransportRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_transport_repository

    def literature_figure_repository(self):
        """Access selected native experimental figure measurements."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_figure_storage import LiteratureFigureRepository
        if not hasattr(self, '_literature_figure_repository'):
            self._literature_figure_repository = LiteratureFigureRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_figure_repository

    def literature_ratio_source_repository(self, *, evidence_origin='reported_source'):
        """Access selected native source-signal cells with the caller's bound origin."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_storage import LiteratureRatioSourceRepository
        if not hasattr(self, '_literature_ratio_source_repositories'):
            self._literature_ratio_source_repositories = {}
        if evidence_origin not in self._literature_ratio_source_repositories:
            repository = LiteratureRatioSourceRepository(self.services.workflow.store, self.services.workflow.run_id, evidence_origin=evidence_origin)
            self._literature_ratio_source_repositories[evidence_origin] = repository
        return self._literature_ratio_source_repositories[evidence_origin]

    def literature_controlled_response_repository(self, *, expected_descriptor=None, evidence_origin='reported_source'):
        """Access the caller-bound controlled-response repository; choose no work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import LiteratureControlledResponseRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_controlled_response_repositories'):
            self._literature_controlled_response_repositories = {}
        if key not in self._literature_controlled_response_repositories:
            self._literature_controlled_response_repositories[key] = LiteratureControlledResponseRepository(self.services.workflow.store, self.services.workflow.run_id, expected_descriptor=expected_descriptor, evidence_origin=evidence_origin)
        return self._literature_controlled_response_repositories[key]

    def literature_gel_repository(self, *, expected_descriptor=None, evidence_origin='reported_source'):
        """Access the caller-bound gel repository; choose no work."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_gel_storage import LiteratureGelRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_gel_repositories'):
            self._literature_gel_repositories = {}
        if key not in self._literature_gel_repositories:
            self._literature_gel_repositories[key] = LiteratureGelRepository(self.services.workflow.store, self.services.workflow.run_id, expected_descriptor=expected_descriptor, evidence_origin=evidence_origin)
        return self._literature_gel_repositories[key]

    def _endpoint_signal_repository(self):
        """Lazy selected adapter; discovery and reconstruction create no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_endpoint_signal_storage import LiteratureEndpointSignalRepository
        if not hasattr(self, '_endpoint_signal_repo'):
            self._endpoint_signal_repo = LiteratureEndpointSignalRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._endpoint_signal_repo

    def _concentration_window_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_concentration_window_storage import LiteratureConcentrationWindowRepository
        if not hasattr(self, '_concentration_window_repo'):
            self._concentration_window_repo = LiteratureConcentrationWindowRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._concentration_window_repo

    def _measurement_comparison_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_comparison_storage import LiteratureMeasurementComparisonRepository
        if not hasattr(self, '_measurement_comparison_repo'):
            self._measurement_comparison_repo = LiteratureMeasurementComparisonRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._measurement_comparison_repo

    def _summary_precision_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_summary_precision_storage import LiteratureKineticSummaryPrecisionRepository
        if not hasattr(self, '_summary_precision_repo'):
            self._summary_precision_repo = LiteratureKineticSummaryPrecisionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._summary_precision_repo

    def _rate_grid_repository(self):
        return self.literature_rate_observation_repository().grid_projection()

    def _compiled_assay_repository(self):
        """Lazy common-sheet compilation; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import LiteratureCompiledAssayRepository
        if not hasattr(self, '_compiled_assay_repo'):
            self._compiled_assay_repo = LiteratureCompiledAssayRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._compiled_assay_repo

    def _compiled_assay_v2_repository(self):
        return self._compiled_assay_repository().v2_projection()

    def _compiled_assay_v3_repository(self):
        return self._compiled_assay_repository().v3_projection()

    def _product_coupling_repository(self):
        """Lazy selected product/cofactor adapter; discovery creates no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_coupling_storage import LiteratureProductCouplingRepository
        if not hasattr(self, '_product_coupling_repo'):
            self._product_coupling_repo = LiteratureProductCouplingRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._product_coupling_repo

    def _measurement_validation_repository(self):
        """Lazy selected precision/control adapter; discovery creates no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_validation_storage import LiteratureMeasurementValidationRepository
        if not hasattr(self, '_measurement_validation_repo'):
            self._measurement_validation_repo = LiteratureMeasurementValidationRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._measurement_validation_repo

    def _ion_discrimination_repository(self):
        """Optional lazy adapter; discovery and saved reads create no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ion_discrimination_storage import LiteratureIonDiscriminationRepository
        if not hasattr(self, '_ion_discrimination_repo'):
            self._ion_discrimination_repo = LiteratureIonDiscriminationRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._ion_discrimination_repo

    def _channel_repository(self):
        """Lazy adapter; only a selected population reads electrical sources."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_channel_storage import LiteratureChannelRepository
        if not hasattr(self, '_channel_repo'):
            self._channel_repo = LiteratureChannelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._channel_repo

    def _completion_time_repository(self):
        """Lazy selected-operation adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_completion_time_storage import LiteratureCompletionTimeRepository
        if not hasattr(self, '_completion_time_repo'):
            self._completion_time_repo = LiteratureCompletionTimeRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._completion_time_repo

    def _active_site_repository(self):
        """Lazy selected-operation adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_active_site_storage import LiteratureActiveSiteRepository
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

    def _parent_depletion_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_parent_depletion_storage import LiteratureParentDepletionRepository
        if not hasattr(self, '_parent_depletion_repo'):
            self._parent_depletion_repo = LiteratureParentDepletionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._parent_depletion_repo

    def _stoichiometric_balance_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_stoichiometric_balance_storage import LiteratureStoichiometricBalanceRepository
        if not hasattr(self, '_stoichiometric_balance_repo'):
            self._stoichiometric_balance_repo = LiteratureStoichiometricBalanceRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._stoichiometric_balance_repo

    def _product_partition_repository(self):
        """Lazy source-composition adapter; discovery installs no state."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_partition_storage import LiteratureProductPartitionRepository
        if not hasattr(self, '_product_partition_repo'):
            self._product_partition_repo = LiteratureProductPartitionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._product_partition_repo

    def _binding_interaction_model_repository(self):
        """Optional adapter; construction and saved reads install no tables."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_model_storage import LiteratureBindingInteractionModelRepository
        if not hasattr(self, '_binding_interaction_model_repo'):
            self._binding_interaction_model_repo = LiteratureBindingInteractionModelRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._binding_interaction_model_repo

    def _kinetic_model_repository(self):
        """Optional local adapter; discovery and saved reads install no tables."""
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_model_storage import LiteratureKineticModelRepository
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
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_meaning_delivery import source_meaning_projection
        return source_meaning_projection(self.literature_rate_repository())

    def _population_routes(self, context=None):
        if not self.rate_population:
            return ()
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_summary_precision_storage import PROVIDER as SUMMARY_PROVIDER, NAMESPACE as SUMMARY_NAMESPACE, REQUESTED as SUMMARY_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_coupling_storage import PROVIDER as COUPLING_PROVIDER, NAMESPACE as COUPLING_NAMESPACE, REQUESTED as COUPLING_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_validation_storage import PROVIDER as VALIDATION_PROVIDER, NAMESPACE as VALIDATION_NAMESPACE, REQUESTED as VALIDATION_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_calibration_recovery_storage import PROVIDER as RECOVERY_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_storage import PROVIDER as OBSERVATION_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_replicate_storage import PROVIDER as REPLICATE_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_storage import COMPONENTS, PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_quantity_storage import COMPONENTS as QUANTITIES, PROVIDER as QUANTITY_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_storage import COMPONENTS as ASSAY_COMPONENTS, PROVIDER as ASSAY_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_calculations import COMPONENTS as RATIO_COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_storage import PROVIDER as RATIO_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_calculations import COMPONENTS as BINDING_COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_storage import PROVIDER as BINDING_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_models import COMPONENTS as BINDING_MODEL_COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_model_storage import PROVIDER as BINDING_MODEL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_transport_storage import COMPONENTS as TRANSPORT_COMPONENTS, PROVIDER as TRANSPORT_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_figure_storage import COMPONENTS as FIGURE_COMPONENTS, PROVIDER as FIGURE_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_amount_storage import COMPONENTS as AMOUNT_COMPONENTS, PROVIDER as AMOUNT_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_optical_storage import COMPONENTS as OPTICAL_COMPONENTS, PROVIDER as OPTICAL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_storage import COMPONENTS as KINETIC_COMPONENTS, PROVIDER as KINETIC_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_model_storage import COMPONENTS as KINETIC_MODEL_COMPONENTS, PROVIDER as KINETIC_MODEL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_storage import COMPONENTS as INTERACTION_COMPONENTS, PROVIDER as INTERACTION_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_model_storage import COMPONENTS as INTERACTION_MODEL_COMPONENTS, PROVIDER as INTERACTION_MODEL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_endpoint_signal_storage import PROVIDER as ENDPOINT_PROVIDER, NAMESPACE as ENDPOINT_NAMESPACE, REQUESTED as ENDPOINT_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_comparison_storage import PROVIDER as COMPARISON_PROVIDER, NAMESPACE as COMPARISON_NAMESPACE, REQUESTED as COMPARISON_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_concentration_window_storage import PROVIDER as WINDOW_PROVIDER, NAMESPACE as WINDOW_NAMESPACE, REQUESTED as WINDOW_REQUESTED
        result = ((WINDOW_NAMESPACE, WINDOW_REQUESTED, WINDOW_PROVIDER, (), self._concentration_window_repository), (COMPARISON_NAMESPACE, COMPARISON_REQUESTED, COMPARISON_PROVIDER, (), self._measurement_comparison_repository), (SUMMARY_NAMESPACE, SUMMARY_REQUESTED, SUMMARY_PROVIDER, (), self._summary_precision_repository), (ENDPOINT_NAMESPACE, ENDPOINT_REQUESTED, ENDPOINT_PROVIDER, (), self._endpoint_signal_repository), (COUPLING_NAMESPACE, COUPLING_REQUESTED, COUPLING_PROVIDER, (), self._product_coupling_repository), (VALIDATION_NAMESPACE, VALIDATION_REQUESTED, VALIDATION_PROVIDER, (), self._measurement_validation_repository), ('literature_calibration_recovery_cells', 'requested_calibration_recovery_components', RECOVERY_PROVIDER, (), self.literature_calibration_recovery_repository), ('literature_rate_observation_cells', 'requested_rate_observation_components', OBSERVATION_PROVIDER, (), self.literature_rate_observation_repository), ('literature_rate_grid_cells', 'requested_rate_grid_components', OBSERVATION_PROVIDER, (), self._rate_grid_repository), ('literature_rate_replicate_cells', 'requested_rate_replicate_components', REPLICATE_PROVIDER, (), self.literature_rate_replicate_repository), ('literature_rate_cells', 'requested_rate_components', PROVIDER, COMPONENTS, self.literature_rate_repository), ('literature_rate_source_cells', 'requested_rate_components', PROVIDER, COMPONENTS, lambda: self.literature_rate_repository().source_projection()), ('literature_rate_source_domain_cells', 'requested_rate_components', PROVIDER, COMPONENTS, lambda: self.literature_rate_repository().source_domain_projection()), ('literature_rate_source_meaning_cells', 'requested_rate_components', PROVIDER, COMPONENTS, self._native_rate_meaning_repository), ('literature_quantity_cells', 'requested_quantity_components', QUANTITY_PROVIDER, QUANTITIES, self.literature_quantity_repository), ('literature_assay_cells', 'requested_assay_components', ASSAY_PROVIDER, ASSAY_COMPONENTS, self.literature_assay_repository), ('literature_ratio_cells', 'requested_ratio_components', RATIO_PROVIDER, RATIO_COMPONENTS, self.literature_ratio_repository), ('literature_binding_cells', 'requested_binding_components', BINDING_PROVIDER, BINDING_COMPONENTS, self.literature_binding_repository), ('literature_binding_model_cells', 'requested_binding_model_components', BINDING_MODEL_PROVIDER, BINDING_MODEL_COMPONENTS, self.literature_binding_model_repository), ('literature_transport_cells', 'requested_transport_components', TRANSPORT_PROVIDER, TRANSPORT_COMPONENTS, self.literature_transport_repository), ('literature_figure_cells', 'requested_figure_components', FIGURE_PROVIDER, FIGURE_COMPONENTS, self.literature_figure_repository), ('literature_amount_cells', 'requested_amount_components', AMOUNT_PROVIDER, AMOUNT_COMPONENTS, self.literature_amount_repository), ('literature_optical_cells', 'requested_optical_components', OPTICAL_PROVIDER, OPTICAL_COMPONENTS, self.literature_optical_repository), ('literature_kinetic_cells', 'requested_kinetic_components', KINETIC_PROVIDER, KINETIC_COMPONENTS, self.literature_kinetic_repository), ('literature_kinetic_model_cells', 'requested_kinetic_model_components', KINETIC_MODEL_PROVIDER, KINETIC_MODEL_COMPONENTS, self._kinetic_model_repository), ('literature_binding_interaction_cells', 'requested_binding_interaction_components', INTERACTION_PROVIDER, INTERACTION_COMPONENTS, self.literature_binding_interaction_repository), ('literature_binding_interaction_model_cells', 'requested_binding_interaction_model_components', INTERACTION_MODEL_PROVIDER, INTERACTION_MODEL_COMPONENTS, self._binding_interaction_model_repository))
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ion_discrimination_storage import PROVIDER as ION_PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, ION_PROVIDER, (), self._ion_discrimination_repository),)
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_channel_storage import PROVIDER as CHANNEL_PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, CHANNEL_PROVIDER, (), self._channel_repository),)
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import PROVIDER as COMPILED_PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, COMPILED_PROVIDER, (), self._compiled_assay_repository),)
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import NAMESPACE_V2, REQUESTED_V2
            result += ((NAMESPACE_V2, REQUESTED_V2, COMPILED_PROVIDER, (), self._compiled_assay_v2_repository),)
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_compiled_assay_storage import NAMESPACE_V3, REQUESTED_V3
            result += ((NAMESPACE_V3, REQUESTED_V3, COMPILED_PROVIDER, (), self._compiled_assay_v3_repository),)
        if self._enabled('assay_grading_population', context):
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._assay_grading_repository),)
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._a105_aggregation_repository),)
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_partition_storage import PROVIDER as PARTITION_PROVIDER, NAMESPACE
            result += ((NAMESPACE, 'requested_product_partition_components', PARTITION_PROVIDER, (), self._product_partition_repository),)
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_completion_time_storage import COMPONENTS as TIME_COMPONENTS, PROVIDER as TIME_PROVIDER, NAMESPACE
            result += ((NAMESPACE, 'requested_completion_time_components', TIME_PROVIDER, (), self._completion_time_repository),)
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_active_site_storage import COMPONENTS as ACTIVE_SITE_COMPONENTS, PROVIDER as ACTIVE_SITE_PROVIDER, NAMESPACE
            result += ((NAMESPACE, 'requested_active_site_components', ACTIVE_SITE_PROVIDER, (), self._active_site_repository),)
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_parent_depletion_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._parent_depletion_repository),)
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_stoichiometric_balance_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._stoichiometric_balance_repository),)
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_storage import COMPONENTS as SOURCE_COMPONENTS, PROVIDER as SOURCE_PROVIDER
            result += (('literature_ratio_source_cells', 'requested_ratio_source_components', SOURCE_PROVIDER, SOURCE_COMPONENTS, self._ratio_source_repository),)
        return result
