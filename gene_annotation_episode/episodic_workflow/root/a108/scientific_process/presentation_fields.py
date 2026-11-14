"""A108 commissioned scientific findings and supplemental observation display.

Scientific credit remains the original projector's scalar. Native timing is
separate supplied information and never substituted for finding progress.
"""
from gene_annotation_episode.episodic_workflow.root.a108.runtime import _plain

def scientific_frame(source, view, credit_view, state, outcome, feedback, *, reports=None):
    reports = view.child_reports if reports is None else reports
    forms = [(source.report_values, source.interpret_schema)]
    forms.extend(((report.as_record(), _original_runtime._plain(report.contract.measurements['schema'])) for report in reports))
    return {'state': state, 'forms': forms, 'controller_state': _original_runtime._plain(view.controller_state), 'outcome': outcome, 'feedback': feedback, 'credit': credit_view['credit'], 'reports': reports, 'annotation_axes': False, 'completed_work': {key: credit_view[key] for key in ('source_contributions',) if key in credit_view}}

def frame_for(source, view, credit_view, state, outcome, feedback):
    from .standalone_presentation import standalone_frame, uses_root_credit_presentation
    if len(source.path) == 1 or uses_root_credit_presentation({'current_credit': credit_view['credit']}):
        return standalone_frame(source, view, credit_view, state, outcome, feedback)
    return scientific_frame(source, view, credit_view, state, outcome, feedback)

def annotation_context(source, frame, credit_view):
    if frame['annotation_axes']:
        from .standalone_presentation import root_annotation_context
        return root_annotation_context(credit_view)
    return source.workflow.annotation_context(source.scope, source=source)

def attach_native_timing(context, credit_view):
    if 'monitoring_information_credit' in credit_view:
        context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime
