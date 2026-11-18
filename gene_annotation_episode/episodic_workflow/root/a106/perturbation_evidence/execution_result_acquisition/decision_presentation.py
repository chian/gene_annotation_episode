"""Present this private task's original credit state, completed work and yield table.

Saved root-credit and scalar branches remain intact; no continuation policy.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import Mapping, _plain, json
from gene_annotation_episode.episodic_workflow.root.a106.runtime import Mapping
from gene_annotation_episode.episodic_workflow.root.a106.runtime import Mapping, _category_yield_parameters, yield_table

def present_credit_state(self, view, credit_view, state, presented_outcome, presented_feedback):
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
    return annotation_axes, forms, controller_state, state, presented_outcome, presented_feedback


def prepare_completed_work(self, context, index):
    work_results = context.pop('_completed_work_axis_results', {})
    if 'literature_completed_work' not in context and (not (isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit')):
        from gene_annotation_episode.episodic_workflow.root.a106.episode_work_report import completed_action_reports
        context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)


def decision_yield_table(self, context, journal, index):
    parameters = _category_yield_parameters(self.workflow.controller_binding)
    if isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit':
        table = {'version': 'annotation_axis_yield_table_v1', 'rows': context['controller']['arms'], 'forecast_unit': 'another_whole_axis_invocation', 'source': 'actual_root_controller'}
    else:
        table = yield_table(journal, self.episode_id, before=index, parameters=parameters)
    return table


def _bind_original_task_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a106.library.live_runtime_functions import bind_functions
    names = {'present_credit_state': 'present_credit_state', 'prepare_completed_work': 'prepare_completed_work', 'decision_yield_table': 'decision_yield_table'}
    functions = bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names, defining_module='gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_result_acquisition.decision_presentation')
    globals().update(functions)

from gene_annotation_episode.episodic_workflow.root.a106 import runtime as _a106_original_runtime
_bind_original_task_runtime_providers(vars(_a106_original_runtime))
