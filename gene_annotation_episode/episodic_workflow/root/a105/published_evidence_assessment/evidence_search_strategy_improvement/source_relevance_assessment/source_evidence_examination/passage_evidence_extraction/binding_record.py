from __future__ import annotations
'Private binding record responsibility for literature_targeted.'
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.source_contracts import VERSION, _binding_source_bytes, _implementation_path, deepcopy, hashlib, json

from gene_annotation_episode.episodic_workflow.root.a105.runtime_assets import required_runtime_asset_fingerprints

class LiteratureBindingRecord:

    def as_record(self):
        implementation = _binding_source_bytes()
        implementation += _implementation_path('runtime_assets.py').read_bytes()
        implementation += json.dumps(required_runtime_asset_fingerprints(), sort_keys=True, separators=(',', ':')).encode('utf8')
        implementation += _implementation_path('source_locations.py').read_bytes()
        implementation += _implementation_path('api_error_feedback.py').read_bytes()
        implementation += _implementation_path('literature_progress_report_contracts.py').read_bytes()
        implementation += _implementation_path('literature_contract_error.py').read_bytes()
        if self.assay_grading_population:
            implementation += _implementation_path('literature_required_grading.py').read_bytes()
            implementation += _implementation_path('literature_source_inputs.py').read_bytes()
            implementation += _implementation_path('literature_work_report.py').read_bytes()
            implementation += _implementation_path('literature_work_results.py').read_bytes()
            implementation += _implementation_path('literature_current_results.py').read_bytes()
        if self.rate_population:
            implementation += _implementation_path('literature_sheet_updates.py').read_bytes()
        if self.rate_population:
            for name in ('literature_population_catalog.py', 'literature_task_families.py', 'literature_sheet_policy.py', 'literature_parent_prompt.py', 'literature_experimental_task.py'):
                implementation += _implementation_path(name).read_bytes()
        configuration = {'outcome_page_size': self.outcome_page_size}
        if self.private_yield_binding:
            configuration['private_yield_binding'] = True
            configuration['yield_bindings'] = deepcopy(self._yield_bindings)
        if self.rate_population:
            configuration['rate_population'] = True
            for name in ('literature_a105_worksheet.py', 'literature_a105_worksheet_render.py', 'literature_experimental_contracts.py', 'literature_rate_reader.py', 'literature_rate_native_inputs.py', 'literature_native_rate_operand_information.py', 'literature_rate_calculations.py', 'literature_rate_storage.py', 'literature_rate_observation_inputs.py', 'literature_rate_observation_calculations.py', 'literature_rate_observation_storage.py', 'literature_rate_observation_prompt.py', 'spreadsheet_tools.py', 'literature_calibration_recovery_inputs.py', 'literature_calibration_recovery_calculations.py', 'literature_calibration_recovery_storage.py', 'literature_calibration_recovery_prompt.py', 'literature_calibration_recovery_render.py', 'literature_measurement_validation_inputs.py', 'literature_measurement_validation_calculations.py', 'literature_measurement_validation_prompt.py', 'literature_measurement_validation_storage.py', 'literature_measurement_validation_render.py', 'literature_product_coupling_inputs.py', 'literature_product_coupling_calculations.py', 'literature_product_coupling_prompt.py', 'literature_product_coupling_storage.py', 'literature_product_coupling_render.py', 'literature_rate_replicate_inputs.py', 'literature_rate_replicate_calculations.py', 'literature_rate_replicate_storage.py', 'literature_rate_replicate_prompt.py', 'episode_services.py', 'literature_rate_source_render.py', 'literature_rate_domains.py', 'literature_rate_meaning_delivery.py', 'literature_rate_meaning_render.py', 'literature_received_fact_render.py', 'literature_experimental_prompt.py', 'literature_task_selection.py', 'literature_numerical_return_presentation.py', 'literature_numerical_contracts.py', 'episode_contract_information.py', 'schema_information_text.py', 'schema_support.py', 'literature_prose_reader.py', 'literature_html_quantity_reader.py', 'literature_activity_calculations.py', 'literature_quantity_storage.py', 'literature_assay_inputs.py', 'literature_assay_storage.py', 'literature_assay_prompt.py', 'literature_reference_parent_prompt.py', 'literature_ratio_reader.py', 'literature_ratio_calculations.py', 'literature_ratio_storage.py', 'literature_binding_reader.py', 'literature_binding_calculations.py', 'literature_binding_storage.py', 'literature_binding_prompt.py', 'literature_binding_models.py', 'literature_binding_model_inputs.py', 'literature_binding_model_storage.py', 'literature_transport_calculations.py', 'literature_transport_inputs.py', 'literature_transport_storage.py', 'literature_transport_prompt.py', 'literature_perturbation_calculations.py', 'literature_perturbation_inputs.py', 'literature_perturbation_source.py', 'literature_perturbation_storage.py', 'literature_perturbation_summary.py', 'literature_perturbation_summary_storage.py', 'literature_perturbation_assessments.py', 'literature_summary_figure_reader.py', 'communication.py', 'literature_source_access.py', 'literature_figure_measurements.py', 'literature_figure_inputs.py', 'literature_figure_storage.py', 'literature_figure_prompt.py', 'literature_endpoint_signal_inputs.py', 'literature_endpoint_signal_calculations.py', 'literature_endpoint_signal_prompt.py', 'literature_endpoint_signal_storage.py', 'literature_endpoint_signal_render.py', 'literature_partner_source_fields.py', 'literature_partner_defined_units.py', 'literature_amount_inputs.py', 'literature_amount_prompt.py', 'literature_amount_calculations.py', 'literature_amount_storage.py', 'literature_optical_inputs.py', 'literature_optical_calculations.py', 'literature_optical_validation.py', 'literature_optical_storage.py', 'literature_kinetic_calculations.py', 'literature_kinetic_inputs.py', 'literature_kinetic_validation.py', 'literature_kinetic_storage.py', 'literature_kinetic_summary_precision_inputs.py', 'literature_kinetic_summary_precision_calculations.py', 'literature_kinetic_summary_precision_prompt.py', 'literature_kinetic_summary_precision_storage.py', 'literature_kinetic_summary_precision_render.py', 'literature_concentration_window_inputs.py', 'literature_concentration_window_calculations.py', 'literature_concentration_window_prompt.py', 'literature_concentration_window_storage.py', 'literature_concentration_window_render.py', 'literature_measurement_comparison_inputs.py', 'literature_measurement_comparison_calculations.py', 'literature_measurement_comparison_prompt.py', 'literature_measurement_comparison_storage.py', 'literature_measurement_comparison_render.py', 'literature_compiled_assay_inputs.py', 'literature_compiled_assay_calculations.py', 'literature_compiled_assay_prompt.py', 'literature_kinetic_model_inputs.py', 'literature_kinetic_model_storage.py', 'literature_kinetic_model_render.py', 'literature_kinetic_model_prompt.py', 'literature_binding_interaction_inputs.py', 'literature_binding_interaction_calculations.py', 'literature_binding_visual_inputs.py', 'literature_binding_interaction_validation.py', 'literature_binding_interaction_storage.py', 'literature_binding_interaction_render.py', 'literature_binding_interaction_model_inputs.py', 'literature_binding_interaction_model_storage.py', 'literature_binding_interaction_model_render.py', 'literature_binding_interaction_model_prompt.py', 'literature_ratio_source_prompt.py', 'literature_ratio_source_render.py', 'literature_completion_time_inputs.py', 'literature_completion_time_calculations.py', 'literature_completion_time_storage.py', 'literature_completion_time_prompt.py', 'literature_completion_time_render.py', 'literature_active_site_inputs.py', 'literature_active_site_calculations.py', 'literature_active_site_storage.py', 'literature_active_site_prompt.py', 'literature_active_site_render.py', 'literature_product_partition_inputs.py', 'literature_product_partition_calculations.py', 'literature_product_partition_storage.py', 'literature_product_partition_prompt.py', 'literature_product_partition_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.assay_grading_population:
            configuration['assay_grading_population'] = True
            for name in ('literature_assay_grading.py', 'literature_assay_grading_inputs.py', 'experimental_database_acquisition.py', 'experimental_database_records.py', 'experimental_database_measurements.py', 'literature_assay_grading_storage.py', 'literature_assay_grading_render.py', 'literature_assay_grading_prompt.py', 'literature_a105_aggregation.py', 'literature_a105_aggregation_storage.py', 'literature_a105_aggregation_prompt.py', 'literature_a105_aggregation_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.ion_discrimination_population:
            configuration['ion_discrimination_population'] = True
            for name in ('literature_ion_discrimination_numbers.py', 'literature_ion_discrimination_inputs.py', 'literature_ion_discrimination_calculations.py', 'literature_ion_discrimination_prompt.py', 'literature_ion_discrimination_storage.py', 'literature_ion_discrimination_render.py', 'literature_compiled_assay_inputs.py', 'literature_compiled_assay_calculations.py', 'literature_compiled_assay_storage.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.channel_population:
            configuration['channel_population'] = True
            for name in ('literature_channel_inputs.py', 'literature_channel_calculations.py', 'literature_channel_storage.py', 'literature_channel_prompt.py', 'literature_channel_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.compiled_assay_population:
            configuration['compiled_assay_population'] = True
            for name in ('literature_compiled_assay_inputs.py', 'literature_compiled_assay_calculations.py', 'literature_compiled_assay_storage.py', 'literature_compiled_assay_prompt.py', 'literature_compiled_assay_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.completion_time_population:
            configuration['completion_time_population'] = True
        if self.active_site_population:
            configuration['active_site_population'] = True
        if self.parent_depletion_population:
            configuration['parent_depletion_population'] = True
            for name in ('literature_parent_depletion_inputs.py', 'literature_parent_depletion_calculations.py', 'literature_parent_depletion_storage.py', 'literature_parent_depletion_prompt.py', 'literature_parent_depletion_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.stoichiometric_balance_population:
            configuration['stoichiometric_balance_population'] = True
            for name in ('literature_stoichiometric_balance_inputs.py', 'literature_stoichiometric_balance_calculations.py', 'literature_stoichiometric_balance_storage.py', 'literature_stoichiometric_balance_prompt.py', 'literature_stoichiometric_balance_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.product_partition_population:
            configuration['product_partition_population'] = True
        if self.ratio_source_population:
            configuration.update(ratio_source_population=True, ratio_source_evidence_origin=self.ratio_source_evidence_origin)
            for name in ('literature_ratio_source_inputs.py', 'literature_ratio_source_validation.py', 'literature_ratio_source_calculations.py', 'literature_ratio_source_storage.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self.controlled_response_population:
            configuration.update(controlled_response_population=True, controlled_response_descriptor=deepcopy(self._controlled_response_descriptor), controlled_response_evidence_origin=self.controlled_response_evidence_origin)
            implementation += json.dumps(self._controlled_response_descriptor, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
            for name in ('literature_controlled_response_prompt.py', 'literature_controlled_response_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self.gel_population:
            configuration.update(gel_population=True, gel_descriptor=deepcopy(self._gel_descriptor), gel_evidence_origin=self.gel_evidence_origin)
            implementation += json.dumps(self._gel_descriptor, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
            for name in ('literature_gel_prompt.py', 'literature_gel_render.py'):
                implementation += _implementation_path(name).read_bytes()
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
            for name in ('composition_information.py', 'schema_information_text.py', 'episode_contract_information.py'):
                implementation += _implementation_path(name).read_bytes()
        return {'version': VERSION, 'binding_id': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': configuration}
