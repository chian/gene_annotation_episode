"""Private A106 results decision state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json

from .decision_presentation import present_credit_state

class OperationalDecisionState:

    def decision_state(self, view):
        with self.workflow.store.read_snapshot():
            state = self.workflow.working_state(self)
            row = self.workflow.journal.db.execute("SELECT CASE\n                        WHEN json_extract(action,'$.kind')='tool'\n                         AND json_extract(action,'$.tool')='image.view'\n                         AND json_extract(result,'$.status')='completed'\n                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END\n                        FROM runtime_actions WHERE run_id=? AND episode_id=?\n                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (self.workflow.run_id, self.episode_id)).fetchone()
            visual_evidence = _a106_original_global_json().loads(row[0]) if row and row[0] is not None else []
            subset = _a106_original_global_getattr()(self.workflow.store, 'reference_subset', None)
            presented_outcome = self.workflow.local_outcome_preview(self.last_outcome, decision_index=self.last_outcome_index)
            presented_feedback = self.feedback
            if _a106_original_global_isinstance()(self.last_outcome, _a106_original_global_Mapping()) and self.feedback is self.last_outcome.get('feedback') and _a106_original_global_isinstance()(presented_outcome, _a106_original_global_Mapping()):
                presented_feedback = presented_outcome.get('feedback')
            credit_view = self.workflow.source_credit_view(self)
            annotation_axes, forms, controller_state, state, presented_outcome, presented_feedback = present_credit_state(self, view, credit_view, state, presented_outcome, presented_feedback)
            basis = _a106_original_global__references_in()({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
            context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': {'mode': 'annotation_axis_credit', 'root_score': controller_state['root_score']} if annotation_axes else credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **({'investigation_progress': {key: credit_view[key] for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages') if key in credit_view}} if self.workflow.receipt_projection(self) else {}), 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': _a106_original_global_FACT_MEANINGS()[name]} for name in _a106_original_global_sorted()(_a106_original_global_FACT_SOURCES())} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=() if annotation_axes else view.child_reports)
            if 'monitoring_information_credit' in credit_view:
                context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
            specialist = self.workflow.specialist(self)
            if specialist is not None:
                context.update(specialist.decision_context(self.workflow.binding_context(self), view))
            context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
            contract_catalog = _a106_original_global_getattr()(self.workflow.tools, 'model_contract_catalog', None)
            if _a106_original_global_callable()(contract_catalog):
                context['available_report_facts'] = contract_catalog(context)
        return context


def _a106_original_global_FACT_MEANINGS():
    return FACT_MEANINGS


def _a106_original_global_FACT_SOURCES():
    return FACT_SOURCES


def _a106_original_global_Mapping():
    return Mapping


def _a106_original_global__references_in():
    return _references_in


def _a106_original_global_callable():
    return callable


def _a106_original_global_getattr():
    return getattr


def _a106_original_global_isinstance():
    return isinstance


def _a106_original_global_json():
    return json


def _a106_original_global_sorted():
    return sorted


def _bind_original_task_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a106.library.live_runtime_functions import bind_functions
    getters = {'_a106_original_global_FACT_MEANINGS': '_a106_original_global_FACT_MEANINGS', '_a106_original_global_FACT_SOURCES': '_a106_original_global_FACT_SOURCES', '_a106_original_global_Mapping': '_a106_original_global_Mapping', '_a106_original_global__references_in': '_a106_original_global__references_in', '_a106_original_global_callable': '_a106_original_global_callable', '_a106_original_global_getattr': '_a106_original_global_getattr', '_a106_original_global_isinstance': '_a106_original_global_isinstance', '_a106_original_global_json': '_a106_original_global_json', '_a106_original_global_sorted': '_a106_original_global_sorted'}
    globals().update(bind_functions(namespace, {name: globals()[name] for name in getters},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=getters, defining_module='gene_annotation_episode.episodic_workflow.root.a106.scientific_process.execution_result_acquisition.decision_state'))

from gene_annotation_episode.episodic_workflow.root.a106 import runtime as _a106_original_runtime
_bind_original_task_runtime_providers(vars(_a106_original_runtime))
