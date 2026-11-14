"""Commissioned own-axis scientific credit presentation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json
from gene_annotation_episode.episodic_workflow.root.a106.runtime import _category_yield_parameters, yield_table

class CommissionedScientificPresentation:

    def decision_state(self, view):
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
            forms = [(self.report_values, self.interpret_schema)]
            forms.extend(((report.as_record(), _plain(report.contract.measurements['schema'])) for report in view.child_reports))
            controller_state = _plain(view.controller_state)
            basis = _references_in({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
            context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **({'investigation_progress': {key: credit_view[key] for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages') if key in credit_view}} if self.workflow.receipt_projection(self) else {}), 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': FACT_MEANINGS[name]} for name in sorted(FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=view.child_reports)
            if self.workflow.is_scientific_source(self):
                context.update(self.workflow.annotation_context(self.scope, source=self))
            if 'monitoring_information_credit' in credit_view:
                context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
            specialist = self.workflow.specialist(self)
            if specialist is not None:
                context.update(specialist.decision_context(self.workflow.binding_context(self), view))
            context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('source_contributions',) if key in credit_view}
            contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
            if callable(contract_catalog):
                context['available_report_facts'] = contract_catalog(context)
        return context

    def completed_work(self, context, index):
        work_results = context.pop('_completed_work_axis_results', {})
        if 'literature_completed_work' not in context:
            from gene_annotation_episode.episodic_workflow.root.a106.episode_work_report import completed_action_reports
            context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)
        return context

    def exchange_yield_table(self, context, index, journal):
        parameters = _category_yield_parameters(self.workflow.controller_binding)
        table = yield_table(journal, self.episode_id, before=index, parameters=parameters)
        return table


def _bind_scientific_runtime_providers(namespace):
    from ..library.live_runtime_functions import bind_functions
    names = {'decision_state': 'CommissionedScientificPresentation.decision_state', 'exchange_yield_table': 'CommissionedScientificPresentation.exchange_yield_table'}
    functions = bind_functions(namespace, {name: CommissionedScientificPresentation.__dict__[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a106.scientific_process.commissioned_credit_presentation')
    for name, function in functions.items():
        setattr(CommissionedScientificPresentation, name, function)

from .. import runtime as _original_runtime
_bind_scientific_runtime_providers(vars(_original_runtime))
