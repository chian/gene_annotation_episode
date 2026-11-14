from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

class LiteratureAssignmentFields:

    def _assignment_fields(self, schema, *, context=None):
        schema = deepcopy(schema)
        from gene_annotation_episode.episodic_workflow.root.library.literature_task_schema import task_schema
        task = task_schema()
        if self.private_yield_binding:
            for case in task['anyOf']:
                # The owner fills both exact credit units and yield settings.
                # The model may choose the scientific task, not its threshold.
                case['required'].remove('credit_unit')
            schema['required'].extend(('literature_task', 'proposed_annotation_ref'))
        schema['properties']['literature_task'] = task
        schema['properties']['proposed_annotation_ref'] = REF
        if self.rate_population:
            from gene_annotation_episode.episodic_workflow.root.literature_concentration_window_storage import REQUESTED as WINDOW_REQUESTED, COMPONENTS as WINDOW_COMPONENTS
            schema['properties'][WINDOW_REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(WINDOW_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_metadata import REQUESTED as COMPARISON_REQUESTED
            from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_return_contracts import COMPONENTS as COMPARISON_COMPONENTS
            schema['properties'][COMPARISON_REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPARISON_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_summary_precision_metadata import REQUESTED as SUMMARY_REQUESTED
            from gene_annotation_episode.episodic_workflow.root.literature_kinetic_summary_precision_storage import COMPONENTS as SUMMARY_COMPONENTS
            schema['properties'][SUMMARY_REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(SUMMARY_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_rate_return_schema import COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_return_contracts import COMPONENTS as OBSERVATION_COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_operation_contracts import GRID_REQUESTED
            from gene_annotation_episode.episodic_workflow.root.library.literature_reported_curve_precision_contracts import reported_curve_precision_selector_schema
            schema["properties"][GRID_REQUESTED] = {"type": "array", "uniqueItems": True,
                "items": reported_curve_precision_selector_schema()}
            schema["properties"]["requested_rate_observation_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(OBSERVATION_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_calibration_recovery_storage import COMPONENTS as RECOVERY_COMPONENTS
            schema["properties"]["requested_calibration_recovery_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(RECOVERY_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_product_coupling_storage import COMPONENTS as COUPLING_COMPONENTS, REQUESTED as COUPLING_REQUESTED
            schema["properties"][COUPLING_REQUESTED] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(COUPLING_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_validation_calculations import COMPONENTS as VALIDATION_COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.literature_measurement_validation_storage import REQUESTED
            schema["properties"][REQUESTED] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(VALIDATION_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_rate_replicate_storage import COMPONENTS as REPLICATE_COMPONENTS
            schema["properties"]["requested_rate_replicate_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(REPLICATE_COMPONENTS)}}
            schema["properties"]["requested_rate_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_quantity_storage import COMPONENTS as QUANTITIES
            schema["properties"]["requested_quantity_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(QUANTITIES)}}
            from gene_annotation_episode.episodic_workflow.root.literature_assay_storage import COMPONENTS as ASSAY_COMPONENTS
            schema["properties"]["requested_assay_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(ASSAY_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_return_schema import COMPONENTS as RATIO_COMPONENTS
            schema["properties"]["requested_ratio_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(RATIO_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_binding_return_contracts import COMPONENTS as BINDING_COMPONENTS
            schema["properties"]["requested_binding_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(BINDING_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_binding_model_return_contracts import COMPONENTS as BINDING_MODEL_COMPONENTS
            schema["properties"]["requested_binding_model_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(BINDING_MODEL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_transport_return_contracts import COMPONENTS as TRANSPORT_COMPONENTS
            schema["properties"]["requested_transport_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(TRANSPORT_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_calculations import COMPONENTS as PERTURBATION_COMPONENTS
            schema["properties"]["requested_perturbation_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(PERTURBATION_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_summary import COMPONENTS as PERTURBATION_SUMMARY_COMPONENTS
            schema["properties"]["requested_perturbation_summary_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(PERTURBATION_SUMMARY_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_structure_calculations import COMPONENTS as STRUCTURE_COMPONENTS
            schema["properties"]["requested_structure_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(STRUCTURE_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_calculations import COMPONENTS as REACTION_COMPONENTS
            schema["properties"]["requested_reaction_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(REACTION_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_native_return_contracts import positions_schema as reaction_native_positions_schema
            schema["properties"]["requested_reaction_native_positions"] = reaction_native_positions_schema()
            from gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_contracts import COMPONENTS as ENDPOINT_COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_metadata import REQUESTED as ENDPOINT_REQUESTED
            schema["properties"][ENDPOINT_REQUESTED] = {"type": "array", "uniqueItems": True,
                "items": {"enum": list(ENDPOINT_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_figure_input_contracts import COMPONENTS as FIGURE_COMPONENTS
            schema["properties"]["requested_figure_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(FIGURE_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_partner_calculations import COMPONENTS as PARTNER_COMPONENTS
            schema["properties"]["requested_partner_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(PARTNER_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_amount_calculations import COMPONENTS as AMOUNT_COMPONENTS
            schema["properties"]["requested_amount_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(AMOUNT_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_optical_storage import COMPONENTS as OPTICAL_COMPONENTS
            schema["properties"]["requested_optical_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(OPTICAL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_kinetic_storage import COMPONENTS as KINETIC_COMPONENTS
            schema["properties"]["requested_kinetic_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(KINETIC_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_model_metadata import COMPONENTS as KINETIC_MODEL_COMPONENTS
            schema["properties"]["requested_kinetic_model_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(KINETIC_MODEL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_model_metadata import COMPONENTS as INTERACTION_MODEL_COMPONENTS
            schema["properties"]["requested_binding_interaction_model_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(INTERACTION_MODEL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_return_contracts import COMPONENTS as INTERACTION_COMPONENTS
            schema["properties"]["requested_binding_interaction_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(INTERACTION_COMPONENTS)}}
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_calculations import COMPONENTS as ION_COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.literature_ion_discrimination_storage import REQUESTED
            schema["properties"][REQUESTED] = {"type": "array", "uniqueItems": True,
                "items": {"enum": list(ION_COMPONENTS)}}
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_channel_return_contracts import COMPONENTS as CHANNEL_COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.literature_channel_storage import REQUESTED
            schema["properties"][REQUESTED] = {"type": "array", "uniqueItems": True,
                "items": {"enum": list(CHANNEL_COMPONENTS)}}
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage import COMPONENTS as COMPILED_COMPONENTS, REQUESTED, COMPONENTS_V2, REQUESTED_V2, REQUESTED_V3
            from gene_annotation_episode.episodic_workflow.root.library.literature_compiled_assay_calculations import COMMON_COMPONENTS
            schema['properties'][REQUESTED_V3] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMMON_COMPONENTS)}}
            schema["properties"][REQUESTED_V2] = {"type": "array", "uniqueItems": True,
                "items": {"enum": list(COMPONENTS_V2)}}
            schema["properties"][REQUESTED] = {"type": "array", "uniqueItems": True,
                "items": {"enum": list(COMPILED_COMPONENTS)}}
        if self._enabled('a106_intervention', context):
            from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_operand_contracts import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_assay_grading import COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.literature_intervention_storage import REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.library.literature_a106_subscore import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
        if self._enabled('a108_context_evidence', context):
            from gene_annotation_episode.episodic_workflow.root.literature_a108_grading_storage import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_a108_aggregation_storage import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
        if self._enabled('assay_grading_population', context):
            from gene_annotation_episode.episodic_workflow.root.library.literature_assay_grading import COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.literature_assay_grading_storage import REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.literature_a105_aggregation_storage import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_return_schema import COMPONENTS as PARTITION_COMPONENTS
            schema["properties"]["requested_product_partition_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(PARTITION_COMPONENTS)}}
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_return_schema import COMPONENTS as TIME_COMPONENTS
            schema["properties"]["requested_completion_time_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(TIME_COMPONENTS)}}
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_active_site_return_schema import COMPONENTS as ACTIVE_SITE_COMPONENTS
            schema["properties"]["requested_active_site_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(ACTIVE_SITE_COMPONENTS)}}
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_parent_depletion_return_schema import COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.literature_parent_depletion_storage import REQUESTED
            schema['properties'][REQUESTED]={'type':'array','uniqueItems':True,'items':{'enum':list(COMPONENTS)}}
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_stoichiometric_balance_return_schema import COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.literature_stoichiometric_balance_storage import REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True,
                'items': {'enum': list(COMPONENTS)}}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.literature_ratio_source_storage import COMPONENTS as SOURCE_RATIO_COMPONENTS
            schema["properties"]["requested_ratio_source_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(SOURCE_RATIO_COMPONENTS)}}
        if self.controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.literature_controlled_response_storage import COMPONENTS as CONTROLLED_COMPONENTS, VIEWS
            schema["properties"].update({
                "requested_controlled_response_components": {"type": "array", "uniqueItems": True,
                    "items": {"enum": list(CONTROLLED_COMPONENTS)}},
                "requested_controlled_response_views": {"type": "array", "uniqueItems": True,
                    "items": {"enum": list(VIEWS)}},
                "requested_controlled_response_component_keys": {"type": "array", "uniqueItems": True,
                    "items": dict(_TEXT)}})
        if self.gel_population:
            from gene_annotation_episode.episodic_workflow.root.literature_gel_storage import COMPONENTS as GEL_COMPONENTS, VIEWS
            schema["properties"].update({
                "requested_gel_components": {"type": "array", "uniqueItems": True,
                    "items": {"enum": list(GEL_COMPONENTS)}},
                "requested_gel_views": {"type": "array", "uniqueItems": True,
                    "items": {"enum": list(VIEWS)}},
                "requested_gel_component_keys": {"type": "array", "uniqueItems": True,
                    "items": dict(_TEXT)}})
        return schema

