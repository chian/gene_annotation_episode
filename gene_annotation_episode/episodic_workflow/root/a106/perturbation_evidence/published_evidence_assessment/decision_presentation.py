"""Own original completed-work and scalar/saved-root yield presentation.

These are presentation branches, not new credit or continuation policies.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import Mapping
from gene_annotation_episode.episodic_workflow.root.a106.runtime import Mapping, _category_yield_parameters, yield_table

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
    names = {'prepare_completed_work': 'prepare_completed_work', 'decision_yield_table': 'decision_yield_table'}
    functions = bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names, defining_module='gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.decision_presentation')
    globals().update(functions)

from gene_annotation_episode.episodic_workflow.root.a106 import runtime as _a106_original_runtime
_bind_original_task_runtime_providers(vars(_a106_original_runtime))
