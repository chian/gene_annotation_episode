"""Private A106 literature_strategy received evidence."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_contracts import ContractError, ROLES, ReportBoundaryError, plain, replace

class LiteratureReceivedEvidence:

    def received_report_sources(self, role):
        return self._rate_fact_sources() if role not in ROLES else {}

    def received_report_facts(self, context):
        if context.role in ROLES:
            return {}
        result = {}
        for namespace, _, _, _, repository in self._population_routes():
            cells = repository().received_cells(context)
            if cells or namespace == 'literature_rate_cells':
                result[namespace] = cells
        if self.controlled_response_population:
            cells = self._controlled_response_repository().received_cells(context)
            if cells:
                result['literature_controlled_response_component_cells'] = cells
        if self.gel_population:
            cells = self._gel_repository().received_cells(context)
            if cells:
                result['literature_gel_component_cells'] = cells
        return self._complete_requested_received_arrays(context, result)

    def _complete_requested_received_arrays(self, context, result):
        """Supply selected declared arrays even when no cells were delivered.

        Empty means no received cells of that requested type. It does not
        report an unavailable numerical component as zero, infer a biological
        absence or expose unrequested cells from a known sheet reference.
        """
        contract = plain(context.request).get('report_contract') or {}
        schema = contract.get('measurements', {}).get('schema', {})
        declared = self.received_report_sources(context.role)
        for node in schema.get('properties', {}).values():
            source = node.get('x-source')
            if source in declared and declared[source].get('type') == 'array' and (source not in result):
                result[source] = []
        return result

    def received_form_references(self, context, form, schema, operation_key):
        for namespace, _, _, _, repository in self._population_routes():
            cells = []
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') == namespace:
                    cells.extend(form[name])
            if cells:
                repository().receive_cells(context, cells, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_sheet_updates import current_sheet_refs
        references = current_sheet_refs(self.services.workflow.store, context)
        window_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_concentration_window_cells' for row in form[name]]
        references.extend(self._concentration_window_repository().cell_record_refs(window_cells))
        comparison_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_measurement_comparison_cells' for row in form[name]]
        references.extend(self._measurement_comparison_repository().cell_record_refs(comparison_cells))
        summary_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_kinetic_summary_precision_cells' for row in form[name]]
        references.extend(self._summary_precision_repository().cell_record_refs(summary_cells))
        endpoint_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_endpoint_signal_cells' for row in form[name]]
        references.extend(self._endpoint_signal_repository().cell_record_refs(endpoint_cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_coupling_storage import NAMESPACE as COUPLING_NAMESPACE
        coupling_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == COUPLING_NAMESPACE for row in form[name]]
        references.extend(self._product_coupling_repository().cell_record_refs(coupling_cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_validation_storage import NAMESPACE as VALIDATION_NAMESPACE
        validation_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == VALIDATION_NAMESPACE for row in form[name]]
        references.extend(self._measurement_validation_repository().cell_record_refs(validation_cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_calibration_recovery_storage import NAMESPACE as RECOVERY_NAMESPACE
        recovery_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == RECOVERY_NAMESPACE for row in form[name]]
        references.extend(self._a106_repository('calibration_recovery').cell_record_refs(recovery_cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_observation_storage import NAMESPACE as OBSERVATION_NAMESPACE
        observation_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == OBSERVATION_NAMESPACE for row in form[name]]
        references.extend(self._a106_repository('rate_observation').cell_record_refs(observation_cells))
        grid_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_rate_grid_cells' for row in form[name]]
        references.extend(self._rate_grid_repository().cell_record_refs(grid_cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_replicate_storage import NAMESPACE as REPLICATE_NAMESPACE
        replicate_cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == REPLICATE_NAMESPACE for row in form[name]]
        references.extend(self._a106_repository('rate_replicate').cell_record_refs(replicate_cells))
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_ion_discrimination_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._ion_discrimination_repository().cell_record_refs(cells))
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_channel_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._channel_repository().cell_record_refs(cells))
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_compiled_assay_storage import NAMESPACE, NAMESPACE_V2, NAMESPACE_V3
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') in {NAMESPACE, NAMESPACE_V2, NAMESPACE_V3} for row in form[name]]
            references.extend(self._compiled_assay_repository().cell_record_refs(cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_operands import NAMESPACE
        cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
        references.extend(self._perturbation_operand_repository().cell_record_refs(cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_storage import NAMESPACE
        cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
        references.extend(self._intervention_grading_repository().cell_record_refs(cells))
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore import NAMESPACE
        cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
        references.extend(self._a106_subscore_repository().cell_record_refs(cells))
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_partition_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._product_partition_repository().cell_record_refs(cells))
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_completion_time_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._completion_time_repository().cell_record_refs(cells))
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_active_site_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._active_site_repository().cell_record_refs(cells))
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_depletion_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._parent_depletion_repository().cell_record_refs(cells))
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_stoichiometric_balance_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._stoichiometric_balance_repository().cell_record_refs(cells))
        if self.controlled_response_population:
            adapter = self._controlled_response_repository()
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_controlled_response_component_cells' for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        if self.gel_population:
            adapter = self._gel_repository()
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == 'literature_gel_component_cells' for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        return list(dict.fromkeys(references))

    def received_evidence_tokens(self, context):
        """Identify validated received component subsets, including zero-value cells.

        A sheet reference alone does not deliver its other components. These
        readers authenticate the original typed delivery before exposing each
        immutable cell; renamed form fields and repeated subsets add no token.
        """
        from gene_annotation_episode.episodic_workflow.root.a106.method_loop.durable import content_digest
        tokens = []

        def include(namespace, cells):
            tokens.extend(('received_cell:' + namespace + ':' + content_digest(cell) for cell in cells))
        for namespace, _, _, _, repository in self._population_routes():
            include(namespace, repository().received_cells(context))
        if self.controlled_response_population:
            include('literature_controlled_response_component_cells', self._controlled_response_repository().received_cells(context))
        if self.gel_population:
            include('literature_gel_component_cells', self._gel_repository().received_cells(context))
        return list(dict.fromkeys(tokens))

    def validate_received_report(self, context, form, schema):
        from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.goal import LEADS
        from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.goal import SCREENING
        from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.credit import lead_dispositions
        from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.credit import screening_answers
        task = context.assignment.get('literature_task')
        if task is not None:
            for name, node in schema.get('properties', {}).items():
                source = node.get('x-source')
                if source in (LEADS, SCREENING):
                    reader = lead_dispositions if source == LEADS else screening_answers
                    expected = reader(self.services.workflow.store, context)
                    if plain(form[name]) != expected:
                        raise ReportBoundaryError('Literature answer differs from its original saved work', code='literature_task_answer_differs_from_saved', field=name)
        requested_sources = {node.get('x-source') for node in schema.get('properties', {}).values() if node.get('x-source')}
        for namespace, requested_field, _, _, repository in self._population_routes(context if context.role in ROLES else None):
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                stale_channel_receipt = namespace in {'literature_intervention_grading_cells', 'literature_a106_subscore_cells', 'literature_concentration_window_cells', 'literature_measurement_comparison_cells', 'literature_kinetic_summary_precision_cells', 'literature_endpoint_signal_cells', 'literature_rate_grid_cells', 'literature_compiled_assay_v3_cells', 'literature_product_coupling_cells', 'literature_measurement_validation_cells', 'literature_channel_cells', 'literature_ion_discrimination_cells'} and bool(set(repository().selected_sheet_refs(context)) - permitted)
                if any((row['sheet_ref'] not in permitted for row in rows)) or stale_channel_receipt:
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_rate_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    if namespace in {'literature_rate_observation_cells', 'literature_rate_grid_cells', 'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells'} and (not rows) and (context.assignment.get(requested_field) not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if namespace in {'literature_rate_cells', 'literature_rate_source_cells', 'literature_rate_source_domain_cells', 'literature_rate_source_meaning_cells'} and (not rows) and (context.assignment.get('requested_rate_components') not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if namespace in {'literature_perturbation_cells', 'literature_perturbation_summary_cells'} and (not rows) and (context.assignment.get(requested_field) not in ([], ())):
                        repository().validate_empty_return_family(context)
                    repository().validate_fact_values(replace(context, received_record_refs=tuple(permitted)), rows)
                    requested = context.assignment.get(requested_field, [] if namespace in {'literature_intervention_grading_cells', 'literature_a106_subscore_cells', 'literature_concentration_window_cells', 'literature_measurement_comparison_cells', 'literature_kinetic_summary_precision_cells', 'literature_endpoint_signal_cells', 'literature_product_coupling_cells', 'literature_measurement_validation_cells', 'literature_calibration_recovery_cells', 'literature_rate_observation_cells', 'literature_rate_grid_cells', 'literature_rate_replicate_cells', 'literature_completion_time_cells', 'literature_product_partition_cells', 'literature_active_site_cells', 'literature_parent_depletion_cells', 'literature_stoichiometric_balance_cells', 'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells', 'literature_channel_cells', 'literature_ion_discrimination_cells'} else None)
                    permitted_components = repository()._components(requested or []) if namespace == 'literature_rate_grid_cells' else requested
                    if namespace == 'literature_perturbation_operand_cells':
                        permitted_components = context.assignment.get(requested_field, [])
                    if permitted_components is not None and any((row['component'] not in permitted_components for row in rows)):
                        raise ContractError('unrequested_literature_rate_component')
                    if namespace == 'literature_rate_replicate_cells' and rows:
                        from gene_annotation_episode.episodic_workflow.root.a106.domain import canonical
                        expected = repository().fact_cells(replace(context, received_record_refs=tuple(permitted)), list(dict.fromkeys((row['sheet_ref'] for row in rows))), components=requested or [])
                        if canonical(rows) != canonical(expected):
                            raise ContractError('literature_rate_replicate_requested_subset_mismatch')
                    if namespace in {'literature_intervention_grading_cells', 'literature_a106_subscore_cells', 'literature_concentration_window_cells', 'literature_measurement_comparison_cells', 'literature_kinetic_summary_precision_cells', 'literature_endpoint_signal_cells', 'literature_product_coupling_cells', 'literature_measurement_validation_cells', 'literature_rate_observation_cells', 'literature_rate_grid_cells', 'literature_calibration_recovery_cells', 'literature_parent_depletion_cells', 'literature_stoichiometric_balance_cells', 'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells', 'literature_channel_cells', 'literature_ion_discrimination_cells'}:
                        from gene_annotation_episode.episodic_workflow.root.a106.domain import canonical
                        owned = repository().available_sheet_refs(replace(context, received_record_refs=tuple(permitted)))
                        selected = list(dict.fromkeys([*(row['sheet_ref'] for row in rows), *owned]))
                        expected = repository().fact_cells(replace(context, received_record_refs=tuple(permitted)), selected, components=requested or [])
                        if canonical(rows) != canonical(expected):
                            raise ContractError('literature_concentration_window_requested_subset_mismatch' if namespace == 'literature_concentration_window_cells' else 'literature_measurement_comparison_requested_subset_mismatch' if namespace == 'literature_measurement_comparison_cells' else 'literature_product_coupling_requested_subset_mismatch' if namespace == 'literature_product_coupling_cells' else 'literature_measurement_validation_requested_subset_mismatch' if namespace == 'literature_measurement_validation_cells' else 'literature_ion_discrimination_requested_subset_mismatch' if namespace == 'literature_ion_discrimination_cells' else 'literature_channel_requested_subset_mismatch' if namespace == 'literature_channel_cells' else 'literature_compiled_assay_requested_subset_mismatch' if namespace in {'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells'} else 'literature_calibration_recovery_requested_subset_mismatch' if namespace == 'literature_calibration_recovery_cells' else 'literature_rate_grid_requested_subset_mismatch' if namespace == 'literature_rate_grid_cells' else 'literature_rate_observation_requested_subset_mismatch')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        if self.controlled_response_population and 'literature_controlled_response_component_cells' in requested_sources:
            adapter = self._controlled_response_repository()
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != 'literature_controlled_response_component_cells':
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_controlled_response_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    adapter.validate_fact_values(reporting, rows)
                    allowed = {reference: set(adapter.requested_component_keys(reference, context.assignment)) for reference in dict.fromkeys((row['sheet_ref'] for row in rows))}
                    if any((row['component_key'] not in allowed[row['sheet_ref']] for row in rows)):
                        raise ContractError('unrequested_literature_controlled_response_component')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        if self.gel_population and 'literature_gel_component_cells' in requested_sources:
            adapter = self._gel_repository()
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != 'literature_gel_component_cells':
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_gel_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    adapter.validate_fact_values(reporting, rows)
                    allowed = {reference: set(adapter.requested_component_keys(reference, context.assignment)) for reference in dict.fromkeys((row['sheet_ref'] for row in rows))}
                    if any((row['component_key'] not in allowed[row['sheet_ref']] for row in rows)):
                        raise ContractError('unrequested_literature_gel_component')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error


from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a106.library.intervention_execution_lookup import _execution

def received_application_rows(services, context, source_ref=None, fields=None):
    """Use exact typed receipts, never reopen a child's unrequested sheet."""
    binding = _execution(services, context=context)
    if binding is None:
        if source_ref is not None:
            raise ContractError("intervention_analysis_execution_unbound")
        return []
    groups = binding.api_execution.application_returns.received_context(context)
    rows = [row for group in groups for row in group["facts"]]
    if source_ref is None:
        return deepcopy(rows)
    result = [row for row in rows if row["source_ref"] == source_ref and row["field"] in fields]
    by_field = {row["field"]: row for row in result}
    if len(result) != len(by_field) or set(by_field) != set(fields):
        raise ContractError("intervention_analysis_field_not_received")
    return [deepcopy(by_field[name]) for name in fields]
