from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.family import member_for_role




class LiteratureNumericalReportProjection:

    def _rate_facts(self, context, references):
        from gene_annotation_episode.episodic_workflow.root.literature_sheet_updates import current_sheet_refs
        current = current_sheet_refs(self.services.workflow.store, context)
        references = list(dict.fromkeys([*references, *current]))
        context = replace(context, received_record_refs=tuple(dict.fromkeys([
            *context.received_record_refs, *current])))
        result = {}
        for namespace, requested_field, provider, defaults, repository in self._population_routes(context):
            selected = []
            adapter = repository()
            for reference in references:
                if reference not in context.received_record_refs:
                    continue
                row = self.services.read_record(reference)
                if row.get("record_type") == "source" and row.get("provider") == provider:
                    if namespace in {'literature_figure_cells', 'literature_endpoint_signal_cells'}:
                        if row.get('version') not in {'literature_figure_record_v1', 'literature_figure_endpoint_signal_record_v1'}:
                            raise ContractError('literature_figure_projection_version_mismatch')
                        if row.get('version') != adapter.record_version:
                            continue
                    if namespace in {"literature_rate_cells", "literature_rate_source_cells", "literature_rate_source_domain_cells", "literature_rate_source_meaning_cells"}:
                        if row.get("version") not in {"literature_rate_population_record_v1", "literature_rate_population_record_v2"}:
                            raise ContractError("literature_rate_projection_version_mismatch")
                        if row.get("version") != adapter.record_version:
                            continue
                    if namespace in {"literature_rate_observation_cells", "literature_rate_grid_cells"}:
                        if row.get("version") not in {"literature_reported_rate_observation_record_v1", "literature_reported_rate_observation_record_v2"}:
                            raise ContractError("literature_rate_grid_projection_version_mismatch")
                        if row.get("version") != adapter.record_version:
                            continue
                    if namespace == "literature_ratio_source_cells" and row.get("version") != adapter.record_version:
                        raise ContractError("literature_ratio_source_projection_version_mismatch")
                    if namespace in {"literature_perturbation_cells", "literature_perturbation_summary_cells"}:
                        if row.get("version") not in {"literature_perturbation_record_v1", "literature_perturbation_record_v2"}:
                            raise ContractError("literature_perturbation_projection_version_mismatch")
                        if row.get("version") != adapter.record_version:
                            continue
                    if namespace in {"literature_reaction_cells", "literature_reaction_semantic_cells"}:
                        if row.get("version") not in {"literature_reaction_record_v2", "literature_reaction_record_v3"}:
                            raise ContractError("literature_reaction_projection_version_mismatch")
                        if row.get("version") != adapter.record_version:
                            continue
                    if namespace in {"literature_compiled_assay_cells", "literature_compiled_assay_v2_cells", "literature_compiled_assay_v3_cells"}:
                        if row.get("version") not in {"literature_compiled_assay_record_v1", "literature_compiled_assay_record_v2", "literature_compiled_assay_record_v3"}:
                            raise ContractError("literature_compiled_assay_projection_version_mismatch")
                        if row.get("version") != adapter.record_version:
                            continue
                    selected.append(reference)
            components = tuple(context.assignment.get(requested_field, defaults))
            result[namespace] = adapter.fact_cells(context, selected, components=components)
        if not self.rate_population:
            return result
        if self.controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.literature_controlled_response_storage import PROVIDER
            adapter = self._controlled_response_repository()
            rows = []
            for reference in dict.fromkeys(references):
                if reference not in context.received_record_refs:
                    continue
                record = self.services.read_record(reference)
                if record.get("record_type") == "source" and record.get("provider") == PROVIDER:
                    keys = adapter.requested_component_keys(reference, context.assignment)
                    rows.extend(adapter.fact_cells(context, [reference], components=keys))
            result["literature_controlled_response_component_cells"] = rows
        if self.gel_population:
            from gene_annotation_episode.episodic_workflow.root.literature_gel_storage import PROVIDER
            adapter = self._gel_repository()
            rows = []
            for reference in dict.fromkeys(references):
                if reference not in context.received_record_refs:
                    continue
                record = self.services.read_record(reference)
                if record.get("record_type") == "source" and record.get("provider") == PROVIDER:
                    keys = adapter.requested_component_keys(reference, context.assignment)
                    rows.extend(adapter.fact_cells(context, [reference], components=keys))
            result["literature_gel_component_cells"] = rows
        from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_native_return_contracts import NAMESPACE, POSITIONS_FIELD
        rows = []
        positions = context.assignment.get(POSITIONS_FIELD, ["all"])
        if positions:
            adapter = self.services.literature_reaction_repository().native_observations_projection()
            for reference in dict.fromkeys(references):
                if reference not in context.received_record_refs:
                    continue
                record = self.services.read_record(reference)
                if (record.get("record_type") == "source" and record.get("provider") == "literature.experimental.reaction"
                        and record.get("version") == "literature_reaction_record_v3"):
                    saved = self.services.literature_reaction_repository().read(reference)
                    if "native_observations" in saved:
                        rows.extend(adapter.fact_rows(context, [reference], positions=positions))
        result[NAMESPACE] = rows
        return result

