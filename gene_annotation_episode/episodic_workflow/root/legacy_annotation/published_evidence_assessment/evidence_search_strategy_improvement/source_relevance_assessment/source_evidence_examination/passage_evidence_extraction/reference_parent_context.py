from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)


class LiteratureReferenceParentContext:
    def _initial_reference_parent_context(self, context):
        custody = []
        for reference in self.reference_parent_sources:
            if reference not in context.received_record_refs:
                raise ContractError("literature_parent_source_not_received")
            source = self._require(reference, context.scope, "source")
            custody.append({"source_ref": reference, **{name: source.get(name) for name in (
                "artifact_ref", "text_ref", "version", "parent_source_refs")}})
        result = {"reference_evidence_parent": {"version": "reference_evidence_parent_v1",
                    **({"evidence_axis": "A108"} if self._enabled('a108_context_evidence', context) else {"evidence_axis": "A106"} if self._enabled('a106_intervention', context) else {}),
                    "source_refs": list(self.reference_parent_sources), "source_custody": custody,
                    "child_population_operations": [
                        {name: entry[name] for name in ("name", "description")}
                        for entry in (_a108_population_catalog() if self._enabled('a108_context_evidence', context) else _population_catalog(a106_intervention=self._enabled('a106_intervention', context), assay_grading_population=self._enabled('assay_grading_population', context),
                            ratio_source_population=self.ratio_source_population,
                            controlled_response_population=self.controlled_response_population, gel_population=self.gel_population,
                            completion_time_population=self.completion_time_population,
                            active_site_population=self.active_site_population,
                            parent_depletion_population=self.parent_depletion_population,
                            stoichiometric_balance_population=self.stoichiometric_balance_population,
                            product_partition_population=self.product_partition_population,
                            compiled_assay_population=self.compiled_assay_population,
                            channel_population=self.channel_population,
                            ion_discrimination_population=self.ion_discrimination_population))]},
                "literature_experimental_work": {"version": "literature_experimental_task_v1",
                    "aspect": "reference_evidence_parent"}}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_source_render import admitted_return_meanings
            result["literature_ratio_source_return_meanings"] = admitted_return_meanings(
                context, self._ratio_source_repository())
        if self.controlled_response_population:
            result["literature_controlled_response_return_bindings"] = self._controlled_response_bindings(context)
        if self.gel_population:
            result.update(self._gel_display_context(context))
        if self.rate_population:
            result.update(self._native_rate_display_context(context))
            result.update(self._native_rate_domain_display_context(context))
            result.update(self._native_rate_meaning_display_context(context))
            result.update(self._received_fact_display_context(context))
            result.update(self._endpoint_signal_display_context(context))
            result.update(self._summary_precision_display_context(context))
            result.update(self._measurement_comparison_display_context(context))
            result.update(self._concentration_window_display_context(context))
        if self.rate_population or self._enabled('a108_context_evidence', context):
            if not self.rate_population:
                result.update(self._received_fact_display_context(context))
            result.update(self._population_task_context(context))
        result.update(self.current_report_facts(context))
        return result

