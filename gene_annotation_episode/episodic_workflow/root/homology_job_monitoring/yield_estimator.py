from __future__ import annotations
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.decision_history import yield_table
from gene_annotation_episode.episodic_workflow.root.yield_parameters import _category_yield_parameters

def decision_yield_table(self, context, index, journal):
    parameters = _category_yield_parameters(self.workflow.controller_binding)
    if isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit':
        table = {'version': 'annotation_axis_yield_table_v1', 'rows': context['controller']['arms'], 'forecast_unit': 'another_whole_axis_invocation', 'source': 'actual_root_controller'}
    else:
        table = yield_table(journal, self.episode_id, before=index, parameters=parameters)
    return table
