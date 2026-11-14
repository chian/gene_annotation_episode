"""Private A104 source repositories."""
from __future__ import annotations
from .contracts import ContractError, json, validate_schema


class LiteraturePopulationRoutes:

    def _population_routes(self, context=None):
        if not self.rate_population:
            return ()
        from gene_annotation_episode.episodic_workflow.root.a104.literature_kinetic_summary_precision_storage import PROVIDER as SUMMARY_PROVIDER, NAMESPACE as SUMMARY_NAMESPACE, REQUESTED as SUMMARY_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a104.literature_product_coupling_storage import PROVIDER as COUPLING_PROVIDER, NAMESPACE as COUPLING_NAMESPACE, REQUESTED as COUPLING_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a104.literature_measurement_validation_storage import PROVIDER as VALIDATION_PROVIDER, NAMESPACE as VALIDATION_NAMESPACE, REQUESTED as VALIDATION_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a104.literature_calibration_recovery_storage import PROVIDER as RECOVERY_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_rate_observation_storage import PROVIDER as OBSERVATION_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_rate_replicate_storage import PROVIDER as REPLICATE_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_rate_storage import COMPONENTS, PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_quantity_storage import COMPONENTS as QUANTITIES, PROVIDER as QUANTITY_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_assay_storage import COMPONENTS as ASSAY_COMPONENTS, PROVIDER as ASSAY_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_ratio_calculations import COMPONENTS as RATIO_COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a104.literature_ratio_storage import PROVIDER as RATIO_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_calculations import COMPONENTS as BINDING_COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_storage import PROVIDER as BINDING_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_models import COMPONENTS as BINDING_MODEL_COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_model_storage import PROVIDER as BINDING_MODEL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_transport_storage import COMPONENTS as TRANSPORT_COMPONENTS, PROVIDER as TRANSPORT_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_figure_storage import COMPONENTS as FIGURE_COMPONENTS, PROVIDER as FIGURE_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_amount_storage import COMPONENTS as AMOUNT_COMPONENTS, PROVIDER as AMOUNT_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_optical_storage import COMPONENTS as OPTICAL_COMPONENTS, PROVIDER as OPTICAL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_kinetic_storage import COMPONENTS as KINETIC_COMPONENTS, PROVIDER as KINETIC_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_kinetic_model_storage import COMPONENTS as KINETIC_MODEL_COMPONENTS, PROVIDER as KINETIC_MODEL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_interaction_storage import COMPONENTS as INTERACTION_COMPONENTS, PROVIDER as INTERACTION_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_binding_interaction_model_storage import COMPONENTS as INTERACTION_MODEL_COMPONENTS, PROVIDER as INTERACTION_MODEL_PROVIDER
        from gene_annotation_episode.episodic_workflow.root.a104.literature_endpoint_signal_storage import PROVIDER as ENDPOINT_PROVIDER, NAMESPACE as ENDPOINT_NAMESPACE, REQUESTED as ENDPOINT_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a104.literature_measurement_comparison_storage import PROVIDER as COMPARISON_PROVIDER, NAMESPACE as COMPARISON_NAMESPACE, REQUESTED as COMPARISON_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a104.literature_concentration_window_storage import PROVIDER as WINDOW_PROVIDER, NAMESPACE as WINDOW_NAMESPACE, REQUESTED as WINDOW_REQUESTED
        result = ((WINDOW_NAMESPACE, WINDOW_REQUESTED, WINDOW_PROVIDER, (), self._concentration_window_repository), (COMPARISON_NAMESPACE, COMPARISON_REQUESTED, COMPARISON_PROVIDER, (), self._measurement_comparison_repository), (SUMMARY_NAMESPACE, SUMMARY_REQUESTED, SUMMARY_PROVIDER, (), self._summary_precision_repository), (ENDPOINT_NAMESPACE, ENDPOINT_REQUESTED, ENDPOINT_PROVIDER, (), self._endpoint_signal_repository), (COUPLING_NAMESPACE, COUPLING_REQUESTED, COUPLING_PROVIDER, (), self._product_coupling_repository), (VALIDATION_NAMESPACE, VALIDATION_REQUESTED, VALIDATION_PROVIDER, (), self._measurement_validation_repository), ('literature_calibration_recovery_cells', 'requested_calibration_recovery_components', RECOVERY_PROVIDER, (), self.literature_calibration_recovery_repository), ('literature_rate_observation_cells', 'requested_rate_observation_components', OBSERVATION_PROVIDER, (), self.literature_rate_observation_repository), ('literature_rate_grid_cells', 'requested_rate_grid_components', OBSERVATION_PROVIDER, (), self._rate_grid_repository), ('literature_rate_replicate_cells', 'requested_rate_replicate_components', REPLICATE_PROVIDER, (), self.literature_rate_replicate_repository), ('literature_rate_cells', 'requested_rate_components', PROVIDER, COMPONENTS, self.literature_rate_repository), ('literature_rate_source_cells', 'requested_rate_components', PROVIDER, COMPONENTS, lambda: self.literature_rate_repository().source_projection()), ('literature_rate_source_domain_cells', 'requested_rate_components', PROVIDER, COMPONENTS, lambda: self.literature_rate_repository().source_domain_projection()), ('literature_rate_source_meaning_cells', 'requested_rate_components', PROVIDER, COMPONENTS, self._native_rate_meaning_repository), ('literature_quantity_cells', 'requested_quantity_components', QUANTITY_PROVIDER, QUANTITIES, self.literature_quantity_repository), ('literature_assay_cells', 'requested_assay_components', ASSAY_PROVIDER, ASSAY_COMPONENTS, self.literature_assay_repository), ('literature_ratio_cells', 'requested_ratio_components', RATIO_PROVIDER, RATIO_COMPONENTS, self.literature_ratio_repository), ('literature_binding_cells', 'requested_binding_components', BINDING_PROVIDER, BINDING_COMPONENTS, self.literature_binding_repository), ('literature_binding_model_cells', 'requested_binding_model_components', BINDING_MODEL_PROVIDER, BINDING_MODEL_COMPONENTS, self.literature_binding_model_repository), ('literature_transport_cells', 'requested_transport_components', TRANSPORT_PROVIDER, TRANSPORT_COMPONENTS, self.literature_transport_repository), ('literature_figure_cells', 'requested_figure_components', FIGURE_PROVIDER, FIGURE_COMPONENTS, self.literature_figure_repository), ('literature_amount_cells', 'requested_amount_components', AMOUNT_PROVIDER, AMOUNT_COMPONENTS, self.literature_amount_repository), ('literature_optical_cells', 'requested_optical_components', OPTICAL_PROVIDER, OPTICAL_COMPONENTS, self.literature_optical_repository), ('literature_kinetic_cells', 'requested_kinetic_components', KINETIC_PROVIDER, KINETIC_COMPONENTS, self.literature_kinetic_repository), ('literature_kinetic_model_cells', 'requested_kinetic_model_components', KINETIC_MODEL_PROVIDER, KINETIC_MODEL_COMPONENTS, self._kinetic_model_repository), ('literature_binding_interaction_cells', 'requested_binding_interaction_components', INTERACTION_PROVIDER, INTERACTION_COMPONENTS, self.literature_binding_interaction_repository), ('literature_binding_interaction_model_cells', 'requested_binding_interaction_model_components', INTERACTION_MODEL_PROVIDER, INTERACTION_MODEL_COMPONENTS, self._binding_interaction_model_repository))
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_ion_discrimination_storage import PROVIDER as ION_PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, ION_PROVIDER, (), self._ion_discrimination_repository),)
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_channel_storage import PROVIDER as CHANNEL_PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, CHANNEL_PROVIDER, (), self._channel_repository),)
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_compiled_assay_storage import PROVIDER as COMPILED_PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, COMPILED_PROVIDER, (), self._compiled_assay_repository),)
            from gene_annotation_episode.episodic_workflow.root.a104.literature_compiled_assay_storage import NAMESPACE_V2, REQUESTED_V2
            result += ((NAMESPACE_V2, REQUESTED_V2, COMPILED_PROVIDER, (), self._compiled_assay_v2_repository),)
            from gene_annotation_episode.episodic_workflow.root.a104.literature_compiled_assay_storage import NAMESPACE_V3, REQUESTED_V3
            result += ((NAMESPACE_V3, REQUESTED_V3, COMPILED_PROVIDER, (), self._compiled_assay_v3_repository),)
        if self.assay_grading_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_assay_grading_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._assay_grading_repository),)
            from gene_annotation_episode.episodic_workflow.root.a104.literature_a105_aggregation_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._a105_aggregation_repository),)
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_product_partition_storage import PROVIDER as PARTITION_PROVIDER, NAMESPACE
            result += ((NAMESPACE, 'requested_product_partition_components', PARTITION_PROVIDER, (), self._product_partition_repository),)
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_completion_time_storage import COMPONENTS as TIME_COMPONENTS, PROVIDER as TIME_PROVIDER, NAMESPACE
            result += ((NAMESPACE, 'requested_completion_time_components', TIME_PROVIDER, (), self._completion_time_repository),)
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_active_site_storage import COMPONENTS as ACTIVE_SITE_COMPONENTS, PROVIDER as ACTIVE_SITE_PROVIDER, NAMESPACE
            result += ((NAMESPACE, 'requested_active_site_components', ACTIVE_SITE_PROVIDER, (), self._active_site_repository),)
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_parent_depletion_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._parent_depletion_repository),)
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_stoichiometric_balance_storage import PROVIDER, NAMESPACE, REQUESTED
            result += ((NAMESPACE, REQUESTED, PROVIDER, (), self._stoichiometric_balance_repository),)
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_ratio_source_storage import COMPONENTS as SOURCE_COMPONENTS, PROVIDER as SOURCE_PROVIDER
            result += (('literature_ratio_source_cells', 'requested_ratio_source_components', SOURCE_PROVIDER, SOURCE_COMPONENTS, self._ratio_source_repository),)
        return result
