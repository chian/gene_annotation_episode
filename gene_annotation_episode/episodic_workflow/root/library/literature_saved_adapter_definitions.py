"""Exact historical saved sheet-adapter defining coordinates.

Unknown descriptors retain the caller's ordinary import/getattr behavior.
These coordinates do not rewrite saved records or scientific release identities.
"""

_HISTORICAL_ADAPTERS = {
    ('gene_annotation_episode.literature_a105_aggregation_storage', 'LiteratureA105AggregationRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_a105_aggregation_storage', 'LiteratureA105AggregationRepository'),
    ('gene_annotation_episode.literature_a106_subscore_storage', 'LiteratureA106SubscoreRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_a106_subscore_storage', 'LiteratureA106SubscoreRepository'),
    ('gene_annotation_episode.literature_a108_aggregation_storage', 'LiteratureA108AggregationRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_a108_aggregation_storage', 'LiteratureA108AggregationRepository'),
    ('gene_annotation_episode.literature_a108_grading_storage', 'LiteratureA108GradingRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_a108_grading_storage', 'LiteratureA108GradingRepository'),
    ('gene_annotation_episode.literature_a108_storage', 'A108SheetRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_a108_storage', 'A108SheetRepository'),
    ('gene_annotation_episode.literature_active_site_storage', 'LiteratureActiveSiteRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_active_site_storage', 'LiteratureActiveSiteRepository'),
    ('gene_annotation_episode.literature_amount_storage', 'LiteratureAmountRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_amount_storage', 'LiteratureAmountRepository'),
    ('gene_annotation_episode.literature_assay_grading_storage', 'LiteratureAssayGradingRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_assay_grading_storage', 'LiteratureAssayGradingRepository'),
    ('gene_annotation_episode.literature_assay_storage', 'LiteratureAssayRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_assay_storage', 'LiteratureAssayRepository'),
    ('gene_annotation_episode.literature_binding_interaction_model_storage', 'LiteratureBindingInteractionModelRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_binding_interaction_model_storage', 'LiteratureBindingInteractionModelRepository'),
    ('gene_annotation_episode.literature_binding_interaction_storage', 'LiteratureBindingInteractionRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_binding_interaction_storage', 'LiteratureBindingInteractionRepository'),
    ('gene_annotation_episode.literature_binding_model_storage', 'LiteratureBindingModelRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_binding_model_storage', 'LiteratureBindingModelRepository'),
    ('gene_annotation_episode.literature_binding_storage', 'LiteratureBindingRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_binding_storage', 'LiteratureBindingRepository'),
    ('gene_annotation_episode.literature_calibration_recovery_storage', 'LiteratureCalibrationRecoveryRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_calibration_recovery_storage', 'LiteratureCalibrationRecoveryRepository'),
    ('gene_annotation_episode.literature_channel_storage', 'LiteratureChannelRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_channel_storage', 'LiteratureChannelRepository'),
    ('gene_annotation_episode.literature_compiled_assay_storage', 'LiteratureCompiledAssayRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage', 'LiteratureCompiledAssayRepository'),
    ('gene_annotation_episode.literature_completion_time_storage', 'LiteratureCompletionTimeRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_completion_time_storage', 'LiteratureCompletionTimeRepository'),
    ('gene_annotation_episode.literature_concentration_window_storage', 'LiteratureConcentrationWindowRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_concentration_window_storage', 'LiteratureConcentrationWindowRepository'),
    ('gene_annotation_episode.literature_controlled_response_storage', 'LiteratureControlledResponseRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_controlled_response_storage', 'LiteratureControlledResponseRepository'),
    ('gene_annotation_episode.literature_endpoint_signal_storage', 'LiteratureEndpointSignalRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_endpoint_signal_storage', 'LiteratureEndpointSignalRepository'),
    ('gene_annotation_episode.literature_figure_storage', 'LiteratureFigureRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_figure_storage', 'LiteratureFigureRepository'),
    ('gene_annotation_episode.literature_gel_storage', 'LiteratureGelRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_gel_storage', 'LiteratureGelRepository'),
    ('gene_annotation_episode.literature_intervention_storage', 'LiteratureInterventionRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_intervention_storage', 'LiteratureInterventionRepository'),
    ('gene_annotation_episode.literature_ion_discrimination_storage', 'LiteratureIonDiscriminationRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_ion_discrimination_storage', 'LiteratureIonDiscriminationRepository'),
    ('gene_annotation_episode.literature_kinetic_model_storage', 'LiteratureKineticModelRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_kinetic_model_storage', 'LiteratureKineticModelRepository'),
    ('gene_annotation_episode.literature_kinetic_storage', 'LiteratureKineticRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_kinetic_storage', 'LiteratureKineticRepository'),
    ('gene_annotation_episode.literature_kinetic_summary_precision_storage', 'LiteratureKineticSummaryPrecisionRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_kinetic_summary_precision_storage', 'LiteratureKineticSummaryPrecisionRepository'),
    ('gene_annotation_episode.literature_measurement_comparison_storage', 'LiteratureMeasurementComparisonRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_measurement_comparison_storage', 'LiteratureMeasurementComparisonRepository'),
    ('gene_annotation_episode.literature_measurement_validation_storage', 'LiteratureMeasurementValidationRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_measurement_validation_storage', 'LiteratureMeasurementValidationRepository'),
    ('gene_annotation_episode.literature_optical_storage', 'LiteratureOpticalRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_optical_storage', 'LiteratureOpticalRepository'),
    ('gene_annotation_episode.literature_parent_depletion_storage', 'LiteratureParentDepletionRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_parent_depletion_storage', 'LiteratureParentDepletionRepository'),
    ('gene_annotation_episode.literature_partner_storage', 'LiteraturePartnerRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_partner_storage', 'LiteraturePartnerRepository'),
    ('gene_annotation_episode.literature_perturbation_operands', 'LiteraturePerturbationOperandProjection'):
        ('gene_annotation_episode.episodic_workflow.root.literature_perturbation_operands', 'LiteraturePerturbationOperandProjection'),
    ('gene_annotation_episode.literature_perturbation_storage', 'LiteraturePerturbationRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_perturbation_storage', 'LiteraturePerturbationRepository'),
    ('gene_annotation_episode.literature_perturbation_summary_storage', 'LiteraturePerturbationSummaryProjection'):
        ('gene_annotation_episode.episodic_workflow.root.literature_perturbation_summary_storage', 'LiteraturePerturbationSummaryProjection'),
    ('gene_annotation_episode.literature_product_coupling_storage', 'LiteratureProductCouplingRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_product_coupling_storage', 'LiteratureProductCouplingRepository'),
    ('gene_annotation_episode.literature_product_partition_storage', 'LiteratureProductPartitionRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_product_partition_storage', 'LiteratureProductPartitionRepository'),
    ('gene_annotation_episode.literature_quantity_storage', 'LiteratureQuantityRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_quantity_storage', 'LiteratureQuantityRepository'),
    ('gene_annotation_episode.literature_rate_meaning_delivery', 'LiteratureRateSourceMeaningProjection'):
        ('gene_annotation_episode.episodic_workflow.root.literature_rate_meaning_delivery', 'LiteratureRateSourceMeaningProjection'),
    ('gene_annotation_episode.literature_rate_observation_storage', 'LiteratureRateObservationRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_rate_observation_storage', 'LiteratureRateObservationRepository'),
    ('gene_annotation_episode.literature_rate_observation_storage', 'LiteratureReportedCurveRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_rate_observation_storage', 'LiteratureReportedCurveRepository'),
    ('gene_annotation_episode.literature_rate_replicate_storage', 'LiteratureRateReplicateRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_rate_replicate_storage', 'LiteratureRateReplicateRepository'),
    ('gene_annotation_episode.literature_rate_storage', 'LiteratureRateRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_rate_storage', 'LiteratureRateRepository'),
    ('gene_annotation_episode.literature_rate_storage', 'LiteratureRateSourceProjection'):
        ('gene_annotation_episode.episodic_workflow.root.literature_rate_storage', 'LiteratureRateSourceProjection'),
    ('gene_annotation_episode.literature_rate_storage', 'LiteratureRateSourceDomainProjection'):
        ('gene_annotation_episode.episodic_workflow.root.literature_rate_storage', 'LiteratureRateSourceDomainProjection'),
    ('gene_annotation_episode.literature_ratio_source_storage', 'LiteratureRatioSourceRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_ratio_source_storage', 'LiteratureRatioSourceRepository'),
    ('gene_annotation_episode.literature_ratio_storage', 'LiteratureRatioRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_ratio_storage', 'LiteratureRatioRepository'),
    ('gene_annotation_episode.literature_reaction_native_storage', 'LiteratureReactionNativeObservations'):
        ('gene_annotation_episode.episodic_workflow.root.literature_reaction_native_storage', 'LiteratureReactionNativeObservations'),
    ('gene_annotation_episode.literature_reaction_storage', 'LiteratureReactionRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_reaction_storage', 'LiteratureReactionRepository'),
    ('gene_annotation_episode.literature_reaction_storage', 'LiteratureReactionSemanticProjection'):
        ('gene_annotation_episode.episodic_workflow.root.literature_reaction_storage', 'LiteratureReactionSemanticProjection'),
    ('gene_annotation_episode.literature_stoichiometric_balance_storage', 'LiteratureStoichiometricBalanceRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_stoichiometric_balance_storage', 'LiteratureStoichiometricBalanceRepository'),
    ('gene_annotation_episode.literature_structure_storage', 'LiteratureStructureRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_structure_storage', 'LiteratureStructureRepository'),
    ('gene_annotation_episode.literature_transport_storage', 'LiteratureTransportRepository'):
        ('gene_annotation_episode.episodic_workflow.root.literature_transport_storage', 'LiteratureTransportRepository'),
}


def defining_adapter_coordinates(module, name):
    return _HISTORICAL_ADAPTERS.get((module, name), (module, name))
