from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.action_contracts import action_schema as _private_action_schema
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.report_facts import FACT_MEANINGS
from gene_annotation_episode.episodic_workflow.root.report_facts import FACT_SOURCES
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.task_values import _plain
from gene_annotation_episode.episodic_workflow.root.reference_selection import _references_in
from gene_annotation_episode.episodic_workflow.root.progress_observations import _unique
import json
from gene_annotation_episode.episodic_workflow.root.communication import plain

def _own_progress_refs(self, context):
    refs, offset = ([], 0)
    while True:
        page = self.services.own_outcomes(context.episode_id, tools=None, offset=offset, limit=self.outcome_page_size)
        for row in page['records']:
            refs.extend(row.get('progress_refs', ()))
        if page['next_offset'] is None:
            return _unique(refs)
        offset = page['next_offset']

def _received(self, context):
    value = self._assignment(context.assignment, context.scope)
    selection = getattr(self.services, 'progress_selection', None)
    if callable(selection):
        return _unique(selection(context)['known_progress_refs'])
    return _unique([*value['known_progress_refs'], *self._own_progress_refs(context), *self.services.received_progress_refs(context.episode_id)])

def decision_context(self, context, current_view):
    self._role(context.role)
    task = getattr(self.services, 'macs2_peak_monitor_task', None)
    selected_task = task(context) if callable(task) else None
    value = self._assignment(context.assignment, context.scope)
    describe = getattr(self.services, 'describe_progress_target', None)
    result = {'monitor_assignment': value, 'monitor_target_description': describe(value['target_handle'], context.scope) if describe else None, 'monitor_direct_dependencies': plain(self.services.dependencies(value['target_handle'], context.scope)), 'monitor_received_progress_refs': self._received(context), 'monitor_information_meaning': 'Exposed direct relationships and already delivered observations. Empty measurements/log windows do not assert absence or a stall.'}
    if selected_task is not None:
        result['selected_execution_task'] = selected_task
    return result

class MonitorTaskSummary:

    def _decision_inputs(self, view, *, delivery_ref=None):
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
            context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': {'mode': 'annotation_axis_credit', 'root_score': controller_state['root_score']} if annotation_axes else credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **{}, 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': FACT_MEANINGS[name]} for name in sorted(FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=() if annotation_axes else view.child_reports)
            if 'monitoring_information_credit' in credit_view:
                context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
            specialist = self.workflow.specialist(self)
            if specialist is not None:
                context.update(specialist.decision_context(self.workflow.binding_context(self), view))
            context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
            contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
            if callable(contract_catalog):
                context['available_report_facts'] = contract_catalog(context)
        schema = _invoke_private_policy(self.workflow.action_schema, _private_action_schema, self)
        if delivery_ref is not None:
            context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
        return (context, schema)
