"""Incoming source assignment and its original typed response requirements."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_contracts import REF, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _TEXT, _WINDOW, deepcopy, json, obj, plain, validate_schema
from gene_annotation_episode.domain import ContractError

class SourceAssignment:

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        schema = _PAGE
        schema = deepcopy(schema)
        from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.goal import task_schema
        task = task_schema()
        if self.private_yield_binding:
            for case in task['anyOf']:
                case['required'].remove('credit_unit')
            schema['required'].extend(('literature_task', 'proposed_annotation_ref'))
        schema['properties']['literature_task'] = task
        schema['properties']['proposed_annotation_ref'] = REF
        if self.rate_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_concentration_window_storage import REQUESTED as WINDOW_REQUESTED, COMPONENTS as WINDOW_COMPONENTS
            schema['properties'][WINDOW_REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(WINDOW_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_measurement_comparison_storage import REQUESTED as COMPARISON_REQUESTED, COMPONENTS as COMPARISON_COMPONENTS
            schema['properties'][COMPARISON_REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPARISON_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_kinetic_summary_precision_storage import REQUESTED as SUMMARY_REQUESTED, COMPONENTS as SUMMARY_COMPONENTS
            schema['properties'][SUMMARY_REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(SUMMARY_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_rate_storage import COMPONENTS
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_rate_observation_storage import COMPONENTS as OBSERVATION_COMPONENTS, GRID_REQUESTED
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_rate_observation_calculations import reported_curve_precision_selector_schema
            schema['properties'][GRID_REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': reported_curve_precision_selector_schema()}
            schema['properties']['requested_rate_observation_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(OBSERVATION_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_calibration_recovery_storage import COMPONENTS as RECOVERY_COMPONENTS
            schema['properties']['requested_calibration_recovery_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(RECOVERY_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_product_coupling_storage import COMPONENTS as COUPLING_COMPONENTS, REQUESTED as COUPLING_REQUESTED
            schema['properties'][COUPLING_REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COUPLING_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_measurement_validation_storage import COMPONENTS as VALIDATION_COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(VALIDATION_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_rate_replicate_storage import COMPONENTS as REPLICATE_COMPONENTS
            schema['properties']['requested_rate_replicate_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(REPLICATE_COMPONENTS)}}
            schema['properties']['requested_rate_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_quantity_storage import COMPONENTS as QUANTITIES
            schema['properties']['requested_quantity_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(QUANTITIES)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_assay_storage import COMPONENTS as ASSAY_COMPONENTS
            schema['properties']['requested_assay_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(ASSAY_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_ratio_calculations import COMPONENTS as RATIO_COMPONENTS
            schema['properties']['requested_ratio_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(RATIO_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_binding_calculations import COMPONENTS as BINDING_COMPONENTS
            schema['properties']['requested_binding_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(BINDING_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.tools.literature_binding_models import COMPONENTS as BINDING_MODEL_COMPONENTS
            schema['properties']['requested_binding_model_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(BINDING_MODEL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_transport_calculations import COMPONENTS as TRANSPORT_COMPONENTS
            schema['properties']['requested_transport_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(TRANSPORT_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_endpoint_signal_storage import COMPONENTS as ENDPOINT_COMPONENTS, REQUESTED as ENDPOINT_REQUESTED
            schema['properties'][ENDPOINT_REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(ENDPOINT_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_figure_storage import COMPONENTS as FIGURE_COMPONENTS
            schema['properties']['requested_figure_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(FIGURE_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_amount_calculations import COMPONENTS as AMOUNT_COMPONENTS
            schema['properties']['requested_amount_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(AMOUNT_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_optical_storage import COMPONENTS as OPTICAL_COMPONENTS
            schema['properties']['requested_optical_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(OPTICAL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_kinetic_storage import COMPONENTS as KINETIC_COMPONENTS
            schema['properties']['requested_kinetic_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(KINETIC_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_kinetic_model_storage import COMPONENTS as KINETIC_MODEL_COMPONENTS
            schema['properties']['requested_kinetic_model_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(KINETIC_MODEL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_binding_interaction_model_storage import COMPONENTS as INTERACTION_MODEL_COMPONENTS
            schema['properties']['requested_binding_interaction_model_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(INTERACTION_MODEL_COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_binding_interaction_storage import COMPONENTS as INTERACTION_COMPONENTS
            schema['properties']['requested_binding_interaction_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(INTERACTION_COMPONENTS)}}
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_ion_discrimination_storage import COMPONENTS as ION_COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(ION_COMPONENTS)}}
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_channel_storage import COMPONENTS as CHANNEL_COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(CHANNEL_COMPONENTS)}}
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_compiled_assay_storage import COMPONENTS as COMPILED_COMPONENTS, REQUESTED, COMPONENTS_V2, REQUESTED_V2, REQUESTED_V3
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_compiled_assay_calculations import COMMON_COMPONENTS
            schema['properties'][REQUESTED_V3] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMMON_COMPONENTS)}}
            schema['properties'][REQUESTED_V2] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS_V2)}}
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPILED_COMPONENTS)}}
        if self._enabled('assay_grading_population', context):
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.grading.literature_assay_grading_storage import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_a105_aggregation_storage import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_product_partition_calculations import COMPONENTS as PARTITION_COMPONENTS
            schema['properties']['requested_product_partition_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(PARTITION_COMPONENTS)}}
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_completion_time_calculations import COMPONENTS as TIME_COMPONENTS
            schema['properties']['requested_completion_time_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(TIME_COMPONENTS)}}
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_active_site_calculations import COMPONENTS as ACTIVE_SITE_COMPONENTS
            schema['properties']['requested_active_site_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(ACTIVE_SITE_COMPONENTS)}}
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_parent_depletion_storage import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_stoichiometric_balance_storage import COMPONENTS, REQUESTED
            schema['properties'][REQUESTED] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_ratio_source_storage import COMPONENTS as SOURCE_RATIO_COMPONENTS
            schema['properties']['requested_ratio_source_components'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(SOURCE_RATIO_COMPONENTS)}}
        if self.controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_controlled_response_storage import COMPONENTS as CONTROLLED_COMPONENTS, VIEWS
            schema['properties'].update({'requested_controlled_response_components': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(CONTROLLED_COMPONENTS)}}, 'requested_controlled_response_views': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(VIEWS)}}, 'requested_controlled_response_component_keys': {'type': 'array', 'uniqueItems': True, 'items': dict(_TEXT)}})
        if self.gel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.literature_gel_storage import COMPONENTS as GEL_COMPONENTS, VIEWS
            schema['properties'].update({'requested_gel_components': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(GEL_COMPONENTS)}}, 'requested_gel_views': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(VIEWS)}}, 'requested_gel_component_keys': {'type': 'array', 'uniqueItems': True, 'items': dict(_TEXT)}})
        return schema

    def _validate_page(self, page, scope):
        source = self._require(page['source_ref'], scope, 'source')
        if self._artifact(source, page['representation']) != page['artifact_ref']:
            raise ContractError('literature_source_artifact_mismatch', detail={'reference': page['source_ref'], 'artifact_ref': page['artifact_ref'], 'representation': page['representation']})
        self._require(page['artifact_ref'], scope, 'artifact')
        for reference in (*page['question_context_refs'], *page['prior_delivery_refs']):
            self._require(reference, scope)

    def _validate_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema(role, context=context))
        if role in {'literature_page', 'literature_table', 'literature_ordered', 'literature_targeted'}:
            page = value if role == 'literature_page' else value['page']
            self._validate_page(page, scope)
            if role != 'literature_page':
                selected = value['selection']
                windows = selected['spans'] if role == 'literature_targeted' else [selected]
                for window in windows:
                    if window['source_ref'] != page['source_ref']:
                        raise ContractError('literature_reading_source_mismatch')
                    if 'representation' in window and window['representation'] != page['representation']:
                        raise ContractError('literature_reading_representation_mismatch')
                    if 'representation' in window:
                        artifact = self.services.read_record(page['artifact_ref'])
                        if window['offset'] > artifact['size']:
                            raise ContractError('source_offset_out_of_bounds')
        else:
            for field, references in value.items():
                if field.endswith('_refs'):
                    for reference in references:
                        self._require(reference, scope, None if field == 'question_context_refs' else 'source')
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        selection = plain(selection)
        if self.private_yield_binding:
            from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.goal import _task_key
            task = selection.get('literature_task')
            if not isinstance(task, dict):
                raise ContractError('literature_original_task_required')
            try:
                key = _task_key(task)
            except (KeyError, TypeError) as error:
                raise ContractError('literature_original_task_invalid') from error
            declaration = self._yield_bindings.get(key)
            if declaration is None:
                raise ContractError('literature_yield_binding_missing_for_task:' + key)
            yield_settings = {name: declaration[name] for name in ('kind', 'cutoff', 'uncertainty_alpha')}
            if 'credit_unit' in task and task['credit_unit'] != declaration['credit_unit'] or ('yield_settings' in task and task['yield_settings'] != yield_settings):
                raise ContractError('literature_task_supplied_yield_binding_mismatch:' + key)
            selection['literature_task'] = {**task, 'credit_unit': declaration['credit_unit'], 'yield_settings': yield_settings}
        value = self._validate_assignment(role, selection, scope, context=parent)
        if 'literature_task' in value:
            annotation_for = getattr(self.services, 'proposed_annotation_for', None)
            proposed = annotation_for(parent) if annotation_for is not None else parent.assignment.get('proposed_annotation_ref')
            if proposed is not None and value.get('proposed_annotation_ref') != proposed:
                raise ContractError('literature_child_proposed_annotation_differs_from_parent')
        if parent.role == 'literature_page' and role in _CHILDREN['literature_page']:
            original = self._validate_assignment(parent.role, parent.assignment, parent.scope, context=parent)
            if not self._within_source(value['page']['source_ref'], original['source_ref'], scope):
                raise ContractError('literature_reading_outside_assigned_source')
        return value
