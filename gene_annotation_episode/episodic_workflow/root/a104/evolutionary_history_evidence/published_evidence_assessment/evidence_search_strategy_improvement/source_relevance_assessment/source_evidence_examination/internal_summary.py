"""Private A104 internal summary."""
from __future__ import annotations
from .contracts import ContractError, _ACQUISITION_TOOLS, _READ_TOOLS, identity, json, plain

from .report_facts import LiteratureReportFacts

from .population_task_context import LiteraturePopulationTaskContext

class LiteratureSummary(LiteraturePopulationTaskContext, LiteratureReportFacts):

    def decision_context(self, context, current_view):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope, context=context)
        context.role == 'literature_page'
        page = assignment
        sources = [page['source_ref']] if page else assignment.get('source_refs', [])
        custody = []
        for reference in sources:
            source = self._require(reference, context.scope, 'source')
            custody.append({'source_ref': reference, **{key: source.get(key) for key in ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')}})
        result = {'literature_assignment': assignment, 'literature_source_custody': custody, 'own_literature_outcomes': plain(self.services.own_outcomes(context.episode_id, tools=(*_ACQUISITION_TOOLS, *_READ_TOOLS), offset=0, limit=self.outcome_page_size)), 'literature_history_meaning': 'Own outcome metadata only. Read exact previous outcomes together through episode.history with view=records and selected decision_indices. The request_context own_attempt_detail lookup reads selected inputs only. Source delivery does not establish understanding, absence or resolved science.'}
        if self.assay_grading_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_source_inputs import own_source_inputs
            examined = own_source_inputs(self.services.workflow.store, context)
            if examined:
                result['literature_examined_source_inputs'] = examined
        if self.rate_population:
            result['literature_experimental_work'] = {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'}
        if self.ratio_source_population:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_ratio_source_render import admitted_return_meanings
            result['literature_ratio_source_return_meanings'] = admitted_return_meanings(context, self._ratio_source_repository())
        if self.controlled_response_population:
            result['literature_controlled_response_return_bindings'] = self._controlled_response_bindings(context)
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
        if self.rate_population:
            result.update(self._population_task_context(context))
        result.update(self.current_report_facts(context))
        return result

