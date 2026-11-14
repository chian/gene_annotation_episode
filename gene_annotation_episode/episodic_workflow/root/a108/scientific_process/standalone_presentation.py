"""Original injected standalone projection and saved root-shaped presentation.

The commissioned A108 head uses its own finding-progress projection. A directly
built standalone head can still receive an explicitly injected root projector;
a saved original model context also keeps its original presentation contract.
This module does not implement or select the root annotation task.
"""
from gene_annotation_episode.episodic_workflow.root.a108.runtime import Mapping, json, yield_table

def uses_root_credit_presentation(context):
    return isinstance(context.get('current_credit'), _original_runtime.Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit'

def standalone_frame(source, view, credit_view, state, outcome, feedback):
    from .presentation_fields import scientific_frame
    annotation_axes = isinstance(credit_view['credit'], _original_runtime.Mapping) and credit_view['credit'].get('mode') == 'annotation_axis_credit'
    frame = scientific_frame(source, view, credit_view, state, outcome, feedback, reports=() if annotation_axes else view.child_reports)
    frame['annotation_axes'] = annotation_axes
    if annotation_axes:
        frame['state'] = {}
        controller = frame['controller_state']
        frame['controller_state'] = {key: controller[key] for key in ('arms', 'annotation_credits', 'root_score', 'decision')}
        if outcome is not None and source.last_outcome_index is not None:
            prior = source.workflow.journal.row('runtime_actions', source.episode_id, source.last_outcome_index)
            if prior is not None and _original_runtime.json.loads(prior['action']).get('kind') in {'child', 'episode_child', 'job_child'}:
                frame['outcome'] = {'status': outcome.get('status'), 'record_ref_count': len(outcome.get('record_refs') or ()), 'changed_record_ref_count': len(outcome.get('changed_record_refs') or ())}
                frame['feedback'] = None
        frame['credit'] = {'mode': 'annotation_axis_credit', 'root_score': frame['controller_state']['root_score']}
    frame['completed_work'] = {key: credit_view[key] for key in ('a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
    return frame

def root_annotation_context(credit_view):
    return {'proposed_annotations': [{key: row[key] for key in ('proposed_annotation_ref', 'subject_ref', 'predicate', 'value', 'context_refs', 'scope', 'score', 'support', 'opposition', 'status')} for row in credit_view['proposed_annotations']], 'annotation_comparisons': credit_view['comparisons']}

def decision_yield_table(source, context, index, parameters):
    if uses_root_credit_presentation(context):
        return {'version': 'annotation_axis_yield_table_v1', 'rows': context['controller']['arms'], 'forecast_unit': 'another_whole_axis_invocation', 'source': 'actual_root_controller'}
    return _original_runtime.yield_table(source.workflow.journal, source.episode_id, before=index, parameters=parameters)
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime
