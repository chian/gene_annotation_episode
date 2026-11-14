from __future__ import annotations
from .execution_contracts import deepcopy
from .execution_contracts import plain
from gene_annotation_episode.episodic_workflow.root.a110.runtime import FACT_MEANINGS
from gene_annotation_episode.episodic_workflow.root.a110.runtime import FACT_SOURCES
from gene_annotation_episode.episodic_workflow.root.a110.runtime import Mapping
from gene_annotation_episode.episodic_workflow.root.a110.runtime import _plain
from gene_annotation_episode.episodic_workflow.root.a110.runtime import _references_in
from gene_annotation_episode.episodic_workflow.root.a110.runtime import json

def native_decision_snapshot(self, view):
    with self.workflow.store.read_snapshot():
        state = self.workflow.working_state(self)
        row = self.workflow.journal.db.execute("SELECT CASE\n                        WHEN json_extract(action,'$.kind')='tool'\n                         AND json_extract(action,'$.tool')='image.view'\n                         AND json_extract(result,'$.status')='completed'\n                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END\n                        FROM runtime_actions WHERE run_id=? AND episode_id=?\n                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (self.workflow.run_id, self.episode_id)).fetchone()
        visual_evidence = _live_original_runtime.json.loads(row[0]) if row and row[0] is not None else []
        subset = getattr(self.workflow.store, 'reference_subset', None)
        presented_outcome = self.workflow.local_outcome_preview(self.last_outcome, decision_index=self.last_outcome_index)
        presented_feedback = self.feedback
        if isinstance(self.last_outcome, _live_original_runtime.Mapping) and self.feedback is self.last_outcome.get('feedback') and isinstance(presented_outcome, _live_original_runtime.Mapping):
            presented_feedback = presented_outcome.get('feedback')
        credit_view = self.workflow.source_credit_view(self)
        annotation_axes = isinstance(credit_view['credit'], _live_original_runtime.Mapping) and credit_view['credit'].get('mode') == 'annotation_axis_credit'
        forms = [(self.report_values, self.interpret_schema)]
        if not annotation_axes:
            forms.extend(((report.as_record(), _live_original_runtime._plain(report.contract.measurements['schema'])) for report in view.child_reports))
        controller_state = _live_original_runtime._plain(view.controller_state)
        if annotation_axes:
            state = {}
            controller_state = {key: controller_state[key] for key in ('arms', 'annotation_credits', 'root_score', 'decision')}
            if presented_outcome is not None and self.last_outcome_index is not None:
                prior = self.workflow.journal.row('runtime_actions', self.episode_id, self.last_outcome_index)
                if prior is not None and _live_original_runtime.json.loads(prior['action']).get('kind') in {'child', 'episode_child', 'job_child'}:
                    presented_outcome = {'status': presented_outcome.get('status'), 'record_ref_count': len(presented_outcome.get('record_refs') or ()), 'changed_record_ref_count': len(presented_outcome.get('changed_record_refs') or ())}
                    presented_feedback = None
        basis = _live_original_runtime._references_in({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
        context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': {'mode': 'annotation_axis_credit', 'root_score': controller_state['root_score']} if annotation_axes else credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **{}, 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': _live_original_runtime.FACT_MEANINGS[name]} for name in sorted(_live_original_runtime.FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=() if annotation_axes else view.child_reports)
        if 'monitoring_information_credit' in credit_view:
            context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
        specialist = self.workflow.specialist(self)
        if specialist is not None:
            context.update(specialist.decision_context(self.workflow.binding_context(self), view))
        context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
        contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
        if callable(contract_catalog):
            context['available_report_facts'] = contract_catalog(context)
    return context

class NativeInternalSummary:

    def _with_selected_execution_task(self, context, value):
        """Present only this episode's selected flux balance work."""
        assignment = plain(context.assignment)
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding, scientific_job_view
        if is_compact_launch(assignment) or is_compact_assignment(assignment):
            control = read_request_binding(self.store, self.run_id, context.episode_id)
            requests = {row['resource_id']: row['assignment'] for row in control['requests']}
        else:
            requests = {assignment.get('resource_id'): assignment}
        if any((not isinstance(request, dict) or not isinstance(request.get('requested_job', {}).get('native_flux_balance'), dict) for request in requests.values())):
            return value
        callback = getattr(self.services, 'scientific_parent_task', None)
        parent = None if callback is None else callback(context)
        if parent is None:
            return value
        selected = []
        for resource_id, request in requests.items():
            selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'], 'endpoint': deepcopy(request.get('endpoint')), 'constraints': deepcopy(request.get('constraints', {})), 'job': scientific_job_view(request['requested_job']['native_flux_balance']), 'resource': self._resource_information(resource_id)})
        value['selected_execution_task'] = deepcopy({'version': 'selected_execution_task_v1', 'scientific_question': parent['scientific_question'], 'selected_tool_info': parent['selected_tool_info'], 'requests': selected, 'constraints': assignment.get('constraints', {}), 'selector': assignment.get('selector'), 'result_description': value.get('execution_target_description')})
        return value

    def decision_context(self, context, current_view):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment
        if is_compact_assignment(plain(context.assignment)):
            state = self.state(context)
            progress = state.credit_view()
            return {'practical_assignment': plain(context.assignment), 'practical_progress': {key: deepcopy(progress[key]) for key in ('credit', 'satisfied_keys') if key in progress}, 'practical_completed': state.completion_proof() is not None}
        return self._with_selected_execution_task(context, self._delegate(context).decision_context(context, current_view))
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _live_original_runtime
