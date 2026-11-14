"""Private A108 scientific decision presentation from actual working state and received outcomes."""
from gene_annotation_episode.episodic_workflow.root.a108.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, _references_in, json
from .presentation_fields import frame_for, annotation_context, attach_native_timing

def build_decision_inputs(self, view):
    with self.workflow.store.read_snapshot():
        state = self.workflow.working_state(self)
        row = self.workflow.journal.db.execute("SELECT CASE\n                        WHEN json_extract(action,'$.kind')='tool'\n                         AND json_extract(action,'$.tool')='image.view'\n                         AND json_extract(result,'$.status')='completed'\n                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END\n                        FROM runtime_actions WHERE run_id=? AND episode_id=?\n                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (self.workflow.run_id, self.episode_id)).fetchone()
        visual_evidence = _original_runtime.json.loads(row[0]) if row and row[0] is not None else []
        subset = getattr(self.workflow.store, 'reference_subset', None)
        presented_outcome = self.workflow.local_outcome_preview(self.last_outcome, decision_index=self.last_outcome_index)
        presented_feedback = self.feedback
        if isinstance(self.last_outcome, _original_runtime.Mapping) and self.feedback is self.last_outcome.get('feedback') and isinstance(presented_outcome, _original_runtime.Mapping):
            presented_feedback = presented_outcome.get('feedback')
        credit_view = self.workflow.source_credit_view(self)
        frame = frame_for(self, view, credit_view, state, presented_outcome, presented_feedback)
        state = frame['state']
        forms = frame['forms']
        controller_state = frame['controller_state']
        presented_outcome = frame['outcome']
        presented_feedback = frame['feedback']
        basis = _original_runtime._references_in({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
        context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': frame['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **({'investigation_progress': {key: credit_view[key] for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages') if key in credit_view}} if self.workflow.receipt_projection(self) else {}), 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': _original_runtime.FACT_MEANINGS[name]} for name in sorted(_original_runtime.FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=frame['reports'])
        if self.workflow.is_scientific_source(self):
            context.update(annotation_context(self, frame, credit_view))
        attach_native_timing(context, credit_view)
        specialist = self.workflow.specialist(self)
        if specialist is not None:
            context.update(specialist.decision_context(self.workflow.binding_context(self), view))
        context['_completed_work_axis_results'] = frame['completed_work']
        contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
        if callable(contract_catalog):
            context['available_report_facts'] = contract_catalog(context)
    return context
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime
