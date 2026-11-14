"""Private scientific decision context from original saved and received state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, SourceEnd, WorkflowError, _plain, _references_in, json, nullcontext

class SourceInvestigationTaskContext:

    def assemble_decision_context(self, view):
        with self.workflow.store.read_snapshot():
            state = self.workflow.working_state(self)
            row = self.workflow.journal.db.execute("SELECT CASE\n                        WHEN json_extract(action,'$.kind')='tool'\n                         AND json_extract(action,'$.tool')='image.view'\n                         AND json_extract(result,'$.status')='completed'\n                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END\n                        FROM runtime_actions WHERE run_id=? AND episode_id=?\n                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (self.workflow.run_id, self.episode_id)).fetchone()
            visual_evidence = json.loads(row[0]) if row and row[0] is not None else []
            subset = getattr(self.workflow.store, 'reference_subset', None)
            presented_outcome = self.workflow.local_outcome_preview(self.last_outcome, decision_index=self.last_outcome_index)
            presented_feedback = self.feedback
            if isinstance(self.last_outcome, Mapping) and self.feedback is self.last_outcome.get('feedback') and isinstance(presented_outcome, Mapping):
                presented_feedback = presented_outcome.get('feedback')
            credit_view = self.workflow.source_credit_view(self)
            annotation_axes = isinstance(credit_view['credit'], Mapping) and credit_view['credit'].get('mode') == 'annotation_axis_credit'
            forms = [(self.report_values, self.interpret_schema)]
            if not annotation_axes:
                forms.extend(((report.as_record(), _plain(report.contract.measurements['schema'])) for report in view.child_reports))
            controller_state = _plain(view.controller_state)
            if annotation_axes:
                state = {}
                controller_state = {key: controller_state[key] for key in ('arms', 'annotation_credits', 'root_score', 'decision')}
                if presented_outcome is not None and self.last_outcome_index is not None:
                    prior = self.workflow.journal.row('runtime_actions', self.episode_id, self.last_outcome_index)
                    if prior is not None and json.loads(prior['action']).get('kind') in {'child', 'episode_child', 'job_child'}:
                        presented_outcome = {'status': presented_outcome.get('status'), 'record_ref_count': len(presented_outcome.get('record_refs') or ()), 'changed_record_ref_count': len(presented_outcome.get('changed_record_refs') or ())}
                        presented_feedback = None
            basis = _references_in({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
            context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': {'mode': 'annotation_axis_credit', 'root_score': controller_state['root_score']} if annotation_axes else credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **({'investigation_progress': {key: credit_view[key] for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages') if key in credit_view}} if self.workflow.receipt_projection(self) else {}), 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': FACT_MEANINGS[name]} for name in sorted(FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=() if annotation_axes else view.child_reports)
            if self.workflow.is_scientific_source(self):
                if annotation_axes:
                    context.update(proposed_annotations=[{key: row[key] for key in ('proposed_annotation_ref', 'subject_ref', 'predicate', 'value', 'context_refs', 'scope', 'score', 'support', 'opposition', 'status')} for row in credit_view['proposed_annotations']], annotation_comparisons=credit_view['comparisons'])
                else:
                    context.update(self.workflow.annotation_context(self.scope, source=self))
            if 'monitoring_information_credit' in credit_view:
                context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
            specialist = self.workflow.specialist(self)
            if specialist is not None:
                context.update(specialist.decision_context(self.workflow.binding_context(self), view))
            context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
            contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
            if callable(contract_catalog):
                context['available_report_facts'] = contract_catalog(context)
        return context


def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'SourceInvestigationTaskContext.assemble_decision_context': SourceInvestigationTaskContext.__dict__['assemble_decision_context']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.decision_context')
    setattr(SourceInvestigationTaskContext, 'assemble_decision_context', bound['SourceInvestigationTaskContext.assemble_decision_context'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
