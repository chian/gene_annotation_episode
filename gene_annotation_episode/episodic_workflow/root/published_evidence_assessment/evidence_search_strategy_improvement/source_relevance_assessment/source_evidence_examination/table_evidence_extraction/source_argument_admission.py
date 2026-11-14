from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

class LiteratureSourceArgumentAdmission:

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        return self._tool_arguments_after_assignment(context, tool_name, arguments, assignment)

    def _tool_arguments_after_assignment(self, context, tool_name, arguments, assignment):
        entries = {entry["name"]: entry for entry in
                   self.catalog(context, _accept_legacy_quotes=True)}
        if tool_name not in entries:
            raise ContractError("tool_not_available_to_literature_role")
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]["input_schema"])
        page = assignment.get("page")
        if page:
            selected_arguments = arguments["arguments"] if tool_name == "execution.estimate" else arguments
            source_ref = selected_arguments.get("source_ref")
            if tool_name == "source.archive.extract":
                member = self._require(arguments["member_ref"], context.scope, "archive_member")
                source_ref = member["source_ref"]
            if source_ref is not None and not self._within_source(source_ref, page["source_ref"], context.scope):
                from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.source_rejection import rejection_detail
                raise ContractError("literature_reading_outside_assigned_source", detail=
                    rejection_detail(getattr(self.services, 'workflow', None),
                        context, page["source_ref"], [source_ref]))
            if (tool_name == "source.xlsx.rows"
                    and "sheet_key" in assignment["selection"]):
                if arguments["sheet_key"] != assignment["selection"]["sheet_key"]:
                    raise ContractError("literature_table_sheet_mismatch")
            if tool_name in {"literature.concentration_window.populate", "literature.measurement_comparison.populate", "literature.product_coupling.populate", "literature.measurement_validation.populate", "literature.ion_discrimination.populate", "literature.channel.populate", "literature.assay.components.populate", "literature.calibration.recovery.populate", "literature.rate.observations.populate", "literature.rate.replicates.populate", "literature.rate.source.populate", "literature.assay.populate", "literature.ratio.populate", "literature.ratio.source.populate", "literature.binding.populate", "literature.binding.model.populate", "literature.transport.response.populate", "literature.perturbation.populate", "literature.structure.populate", "literature.reaction.populate", "literature.reaction.source.populate", "literature.figure.populate", "literature.partner.populate", "literature.partner.source.populate", "literature.amount.populate", "literature.completion_time.populate", "literature.active_site.populate", "literature.product_partition.populate", "literature.optical.populate", "literature.kinetic.populate", "literature.kinetic.model.populate", "literature.binding.interaction.populate", "literature.binding.interaction.model.populate", "literature.controlled_response.source_v3.populate", "literature.gel.populate", "literature.parent_depletion.populate", "literature.stoichiometric_balance.populate", "literature.assay_grading.populate", "literature.intervention_grading.populate", "literature.a106.finalize", "literature.a105.aggregate", "literature.a108_grading.populate", "literature.a108.aggregate"}:
                def sources(value):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key == "metadata_source_ref" and isinstance(child, str):
                                yield child
                                continue
                            if (key == "sheet_ref" and tool_name in {"literature.assay_grading.populate", "literature.intervention_grading.populate", "literature.a106.finalize", "literature.a105.aggregate", "literature.a108_grading.populate", "literature.a108.aggregate", "literature.measurement_validation.populate", "literature.assay.components.populate", "literature.ion_discrimination.populate"} or key == "original_source_ref" and tool_name == "literature.binding.interaction.populate" or key in {"source_ref", "covariance_source_ref", "activity_covariance_source_ref", "model_source_ref", "km_sheet_ref", "data_source_ref", "coordinate_source_ref", "validation_source_ref"}) and isinstance(child, str):
                                yield child
                            elif key == 'covariance_source_refs' and tool_name == 'literature.measurement_comparison.populate':
                                yield from child
                            else:
                                yield from sources(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from sources(child)
                    elif isinstance(value, str) and (value in arguments.get("visual_source_refs", ())
                            or value in arguments.get("covariance_source_refs", ())):
                        yield value
                blocked = next((ref for ref in set(sources(arguments))
                    if not self._within_source(ref, page["source_ref"], context.scope)), None)
                if blocked is not None:
                    from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.source_rejection import rejection_detail
                    raise ContractError("literature_reading_outside_assigned_source", detail=
                        rejection_detail(getattr(self.services, 'workflow', None),
                            context, page["source_ref"], [blocked]))
        if self.rate_population:
            repo = self._endpoint_signal_repository()
            if tool_name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'}:
                representation = 'original' if tool_name in {'source.sequence.references', 'source.experimental.records'} else arguments.get('representation', 'text')
                repo.authorize_source_access(context, arguments['source_ref'], representation, tool_name)
                self._summary_precision_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
                self._measurement_comparison_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
                self._concentration_window_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
            elif tool_name == 'state.query' and 'refs' in arguments:
                for ref in arguments['refs']:
                    repo.authorize_record_access(context, self.services.read_record(ref))
                    self._summary_precision_repository().authorize_record_access(context, self.services.read_record(ref))
                    self._measurement_comparison_repository().authorize_record_access(context, self.services.read_record(ref))
                    self._concentration_window_repository().authorize_record_access(context, self.services.read_record(ref))
        if self._enabled('a108_context_evidence', context):
            for repository in (self._a108_grading_repository(), self._a108_aggregation_repository()):
                if isinstance(arguments.get('source_ref'), str) and (
                        tool_name.startswith('source.') or tool_name in {'image.view', 'material.from_source'}):
                    representation = arguments.get('representation', 'original' if tool_name in {
                        'source.sequence.references', 'source.experimental.records'} else 'text')
                    repository.authorize_source_access(context, arguments['source_ref'], representation, tool_name)
                elif tool_name == 'state.query' and 'refs' in arguments:
                    for ref in arguments['refs']:
                        repository.authorize_record_access(context, self.services.read_record(ref))
        return arguments

