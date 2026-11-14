from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

from .population_task_context import LiteraturePopulationTaskContext

from .reference_parent_context import LiteratureReferenceParentContext

class LiteratureSummary(LiteratureReferenceParentContext, LiteraturePopulationTaskContext):
    def initial_decision_context(self, context):
        """Caller literature job; an empty source list starts source discovery."""
        if (self.reference_parent_sources is None or context.role != "annotation"
                or len(context.path) != 1):
            return {}
        return self._initial_reference_parent_context(context)

    def decision_context(self, context, current_view):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        return self._decision_context_after_assignment(context, current_view, assignment)

    def _decision_context_after_assignment(self, context, current_view, assignment):
        page = assignment.get("page")
        sources = ([page["source_ref"]] if page else assignment.get("source_refs", []))
        custody = []
        for reference in sources:
            source = self._require(reference, context.scope, "source")
            custody.append({"source_ref": reference, **{key: source.get(key) for key in
                ("version", "artifact_ref", "text_ref", "stdout_ref", "stderr_ref", "parent_source_refs")}})
        result = {"literature_assignment": assignment, "literature_source_custody": custody,
            "own_literature_outcomes": plain(self.services.own_outcomes(context.episode_id,
                tools=(*(_A108_ACQUISITION_TOOLS if self._enabled('a108_context_evidence', context) else _ACQUISITION_TOOLS), *_READ_TOOLS), offset=0, limit=self.outcome_page_size)),
            "literature_history_meaning": "Own outcome metadata only. Read exact previous outcomes together through episode.history with view=records and selected decision_indices. The request_context own_attempt_detail lookup reads selected inputs only. Source delivery does not establish understanding, absence or resolved science."}
        if self._enabled('a108_context_evidence', context) or self._enabled('assay_grading_population', context) and not self._enabled('a106_intervention', context):
            from gene_annotation_episode.episodic_workflow.root.library.literature_source_inputs import own_source_inputs
            examined = own_source_inputs(self.services.workflow.store, context)
            if examined:
                result['literature_examined_source_inputs'] = examined
        if self._enabled('a106_intervention', context):
            from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.analysis_contract import received_application_rows
            result["received_intervention_analysis_rows"] = received_application_rows(self.services, context)
        if self.rate_population or self._enabled('a108_context_evidence', context):
            result["literature_experimental_work"] = {
                "version": "literature_experimental_task_v1", "aspect": "source_experimental_evidence",
                **({"evidence_axis": "A108"} if self._enabled('a108_context_evidence', context) else {"evidence_axis": "A106"} if self._enabled('a106_intervention', context) else {})}
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
        from gene_annotation_episode.episodic_workflow.root.library.literature_source_origin import component_axis_source_origin
        origin = component_axis_source_origin(self.services, context)
        if origin is not None:
            result['component_axis_source_origin'] = origin
        result.update(self.current_report_facts(context))
        return result

