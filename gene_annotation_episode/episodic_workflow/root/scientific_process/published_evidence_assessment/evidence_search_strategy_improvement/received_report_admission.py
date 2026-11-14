from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.family import member_for_role


class LiteratureReceivedReportAdmission:

    def validate_received_report(self, context, form, schema):
        from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import LEADS, SCREENING
        from .task_answers import lead_dispositions, screening_answers
        task = context.assignment.get('literature_task')
        if task is not None:
            for name, node in schema.get('properties', {}).items():
                source = node.get('x-source')
                if source in (LEADS, SCREENING):
                    reader = lead_dispositions if source == LEADS else screening_answers
                    expected = reader(self.services.workflow.store, context)
                    if plain(form[name]) != expected:
                        raise ReportBoundaryError('Literature answer differs from its original saved work',
                            code='literature_task_answer_differs_from_saved', field=name)
        if not (self.rate_population or self.a108_context_evidence):
            return
        requested_sources = {node.get('x-source') for node in schema.get('properties', {}).values()
            if node.get('x-source')}
        for namespace, requested_field, _, _, repository in self._population_routes(context if context.role in ROLES else None):
            for name, node in schema.get("properties", {}).items():
                if node.get("x-source") != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                stale_channel_receipt = (namespace in {"literature_assay_grading_cells", "literature_intervention_grading_cells", "literature_a106_subscore_cells", "literature_a105_aggregation_cells", "literature_a108_grading_cells", "literature_a108_aggregation_cells", "literature_concentration_window_cells", "literature_measurement_comparison_cells", "literature_kinetic_summary_precision_cells", "literature_endpoint_signal_cells", "literature_rate_grid_cells", "literature_compiled_assay_v3_cells", "literature_product_coupling_cells", "literature_measurement_validation_cells", "literature_channel_cells", "literature_ion_discrimination_cells"}
                    and bool(set(repository().selected_sheet_refs(context)) - permitted))
                if any(row["sheet_ref"] not in permitted for row in rows) or stale_channel_receipt:
                    # Refresh only the exact child's later durable receipts.
                    selection = self.services.record_selection(context)
                    if (selection.get("run_id") != context.run_id
                            or selection.get("episode_id") != context.episode_id):
                        raise ReportBoundaryError("Literature return receiver differs",
                            code="literature_rate_receiver_mismatch", field=name)
                    permitted.update(selection["known_record_refs"])
                try:
                    if (namespace in {'literature_rate_observation_cells', 'literature_rate_grid_cells', 'literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells'}
                            and not rows and context.assignment.get(requested_field) not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if (namespace in {"literature_rate_cells", "literature_rate_source_cells", "literature_rate_source_domain_cells", "literature_rate_source_meaning_cells"}
                            and not rows and context.assignment.get("requested_rate_components") not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if (namespace in {"literature_perturbation_cells", "literature_perturbation_summary_cells"}
                            and not rows and context.assignment.get(requested_field) not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if (namespace in {"literature_reaction_cells", "literature_reaction_semantic_cells"}
                            and not rows and context.assignment.get(requested_field) not in ([], ())):
                        # A caller may request both independently typed views.
                        # A legacy numerical sheet has no semantic projection;
                        # return its real cells and an empty semantic view.
                        # Keep the wrong-family guard for a lone empty view.
                        other_namespace = ("literature_reaction_semantic_cells"
                            if namespace == "literature_reaction_cells" else "literature_reaction_cells")
                        companion_returned = any(other_node.get('x-source') == other_namespace
                            and bool(form[other_name])
                            for other_name, other_node in schema.get('properties', {}).items())
                        if not companion_returned:
                            repository().validate_empty_return_family(context)
                    # This hook validates the REPORTING episode (also when C4
                    # reconstructs a child's original contract), before its
                    # form is admitted to the distinct receiving parent.
                    repository().validate_fact_values(replace(context,
                        received_record_refs=tuple(permitted)), rows)
                    requested = context.assignment.get(requested_field,
                        [] if namespace in {"literature_assay_grading_cells", "literature_intervention_grading_cells", "literature_a106_subscore_cells", "literature_a105_aggregation_cells", "literature_a108_grading_cells", "literature_a108_aggregation_cells", "literature_concentration_window_cells", "literature_measurement_comparison_cells", "literature_kinetic_summary_precision_cells", "literature_endpoint_signal_cells", "literature_product_coupling_cells", "literature_measurement_validation_cells", "literature_calibration_recovery_cells", "literature_rate_observation_cells", "literature_rate_grid_cells", "literature_rate_replicate_cells", "literature_completion_time_cells", "literature_product_partition_cells", "literature_active_site_cells", "literature_parent_depletion_cells", "literature_stoichiometric_balance_cells", "literature_compiled_assay_cells", "literature_compiled_assay_v2_cells", "literature_compiled_assay_v3_cells", "literature_channel_cells", "literature_ion_discrimination_cells"} else None)
                    permitted_components = repository()._components(requested or []) if namespace == "literature_rate_grid_cells" else requested
                    if namespace == 'literature_perturbation_operand_cells':
                        permitted_components = context.assignment.get(requested_field, [])
                    if permitted_components is not None and any(row["component"] not in permitted_components for row in rows):
                        raise ContractError("unrequested_literature_rate_component")
                    if namespace == "literature_rate_replicate_cells" and rows:
                        # Preserve the exact available requested subset. A
                        # receiver cannot expand possession merely by knowing
                        # the complete saved sheet's reference.
                        from gene_annotation_episode.domain import canonical
                        expected = repository().fact_cells(replace(context,
                            received_record_refs=tuple(permitted)),
                            list(dict.fromkeys(row["sheet_ref"] for row in rows)),
                            components=requested or [])
                        if canonical(rows) != canonical(expected):
                            raise ContractError("literature_rate_replicate_requested_subset_mismatch")
                    if namespace in {"literature_assay_grading_cells", "literature_intervention_grading_cells", "literature_a106_subscore_cells", "literature_a105_aggregation_cells", "literature_a108_grading_cells", "literature_a108_aggregation_cells", "literature_concentration_window_cells", "literature_measurement_comparison_cells", "literature_kinetic_summary_precision_cells", "literature_endpoint_signal_cells", "literature_product_coupling_cells", "literature_measurement_validation_cells", "literature_rate_observation_cells", "literature_rate_grid_cells", "literature_calibration_recovery_cells", "literature_parent_depletion_cells", "literature_stoichiometric_balance_cells", "literature_compiled_assay_cells", "literature_compiled_assay_v2_cells", "literature_compiled_assay_v3_cells", "literature_channel_cells", "literature_ion_discrimination_cells"}:
                        from gene_annotation_episode.domain import canonical
                        owned = repository().available_sheet_refs(replace(context,
                            received_record_refs=tuple(permitted)))
                        selected = list(dict.fromkeys([*(row["sheet_ref"] for row in rows), *owned]))
                        expected = repository().fact_cells(replace(context,
                            received_record_refs=tuple(permitted)), selected, components=requested or [])
                        if canonical(rows) != canonical(expected):
                            raise ContractError("a108_requested_subset_mismatch" if namespace in _A108_NAMESPACES else "literature_assay_grading_requested_subset_mismatch" if namespace == "literature_assay_grading_cells" else "literature_concentration_window_requested_subset_mismatch" if namespace == "literature_concentration_window_cells" else "literature_measurement_comparison_requested_subset_mismatch" if namespace == "literature_measurement_comparison_cells" else "literature_product_coupling_requested_subset_mismatch" if namespace == "literature_product_coupling_cells" else "literature_measurement_validation_requested_subset_mismatch" if namespace == "literature_measurement_validation_cells" else "literature_ion_discrimination_requested_subset_mismatch" if namespace == "literature_ion_discrimination_cells" else "literature_channel_requested_subset_mismatch" if namespace == "literature_channel_cells" else "literature_compiled_assay_requested_subset_mismatch" if namespace in {"literature_compiled_assay_cells", "literature_compiled_assay_v2_cells", "literature_compiled_assay_v3_cells"} else "literature_calibration_recovery_requested_subset_mismatch" if namespace == "literature_calibration_recovery_cells" else "literature_rate_grid_requested_subset_mismatch" if namespace == "literature_rate_grid_cells" else "literature_rate_observation_requested_subset_mismatch")
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        if self.controlled_response_population and "literature_controlled_response_component_cells" in requested_sources:
            adapter = self._controlled_response_repository()
            for name, node in schema.get("properties", {}).items():
                if node.get("x-source") != "literature_controlled_response_component_cells":
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any(row["sheet_ref"] not in permitted for row in rows):
                    selection = self.services.record_selection(context)
                    if (selection.get("run_id") != context.run_id
                            or selection.get("episode_id") != context.episode_id):
                        raise ReportBoundaryError("Literature return receiver differs",
                            code="literature_controlled_response_receiver_mismatch", field=name)
                    permitted.update(selection["known_record_refs"])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    adapter.validate_fact_values(reporting, rows)
                    allowed = {reference: set(adapter.requested_component_keys(reference, context.assignment))
                        for reference in dict.fromkeys(row["sheet_ref"] for row in rows)}
                    if any(row["component_key"] not in allowed[row["sheet_ref"]] for row in rows):
                        raise ContractError("unrequested_literature_controlled_response_component")
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        if self.gel_population and "literature_gel_component_cells" in requested_sources:
            adapter = self._gel_repository()
            for name, node in schema.get("properties", {}).items():
                if node.get("x-source") != "literature_gel_component_cells":
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any(row["sheet_ref"] not in permitted for row in rows):
                    selection = self.services.record_selection(context)
                    if (selection.get("run_id") != context.run_id
                            or selection.get("episode_id") != context.episode_id):
                        raise ReportBoundaryError("Literature return receiver differs",
                            code="literature_gel_receiver_mismatch", field=name)
                    permitted.update(selection["known_record_refs"])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    adapter.validate_fact_values(reporting, rows)
                    allowed = {reference: set(adapter.requested_component_keys(reference, context.assignment))
                        for reference in dict.fromkeys(row["sheet_ref"] for row in rows)}
                    if any(row["component_key"] not in allowed[row["sheet_ref"]] for row in rows):
                        raise ContractError("unrequested_literature_gel_component")
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error

        from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_native_return_contracts import NAMESPACE, POSITIONS_FIELD
        native_adapter = (self.services.literature_reaction_repository().native_observations_projection()
            if NAMESPACE in requested_sources else None)
        for name, node in schema.get("properties", {}).items():
            if node.get("x-source") != NAMESPACE:
                continue
            rows = form[name]
            permitted = set(context.received_record_refs)
            if any(row["sheet_ref"] not in permitted for row in rows):
                selection = self.services.record_selection(context)
                if selection.get("run_id") != context.run_id or selection.get("episode_id") != context.episode_id:
                    raise ReportBoundaryError("Literature return receiver differs", code="literature_reaction_native_receiver_mismatch", field=name)
                permitted.update(selection["known_record_refs"])
            try:
                native_adapter.validate_fact_rows(replace(context, received_record_refs=tuple(permitted)), rows)
                requested = native_adapter._positions(context.assignment.get(POSITIONS_FIELD, ["all"]))
                if requested != ("all",) and any(row["observation_position"] not in requested for row in rows):
                    raise ContractError("unrequested_literature_reaction_native_observation")
            except ContractError as error:
                raise ReportBoundaryError(str(error), code=str(error), field=name) from error


        # Interpretation-only report_update values lack the bound numerical
        # fields. Check their relationships at the complete ordinary admission
        # boundary, including valid empty numerical partials.
        from gene_annotation_episode.episodic_workflow.root.literature_a105_worksheet import FAMILIES as WORKSHEET_FAMILIES, validate_a105_worksheet_links
        if requested_sources.intersection(WORKSHEET_FAMILIES):
            known = set(context.received_record_refs)
            def read_public_record(reference):
                if reference not in known:
                    try:
                        selection = self.services.record_selection(context)
                    except (AttributeError, LookupError):
                        return None
                    if (selection.get('run_id') != context.run_id
                            or selection.get('episode_id') != context.episode_id):
                        raise ReportBoundaryError('Worksheet reference receiver differs',
                            code='a105_worksheet_receiver_mismatch')
                    known.update(selection.get('known_record_refs', ()))
                return self.services.read_record(reference) if reference in known else None
            try:
                validate_a105_worksheet_links(form, schema, context.assignment,
                    read_public_record=read_public_record)
            except ContractError as error:
                raise ReportBoundaryError(str(error), code=str(error)) from error

