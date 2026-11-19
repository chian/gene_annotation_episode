"""What the commissioner gives: the monitor assignment (old ``monitor_assignment_v1``, from ``from_parent.py``
``MonitorAssignment.assignment_schema``): the target, the fields the monitor may observe, the progress observations
the commissioner already has and the record types whose committed records it may return. The information unit of
the monitor's credit is a new field: the old binding took it from its configuration.

The old admission (the target handle must be an execution handle in scope, every known progress ref an observation
of that same target: ``MonitorAssignment.prepare_assignment`` reading the old progress provider) is not carried
here: this function is handed no records and no services. A target that is not an execution handle in scope fails
at the first observation of it; a known progress ref that is not an observation of the target fails when the
summary reads its snapshot (``messages/internal_summary.py``)."""
from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    RECORD_SCHEMAS)

FIELD_OPTIONS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
                 'result_available')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The version of this assignment form', 'monitor_assignment_v1'),
    'target_handle': Field('text', 'The execution handle to assess'),
    'requested_fields': SubsetField('text', 'The exposed fields the monitor may observe; it never observes more',
                                    FIELD_OPTIONS),
    'known_progress_refs': Field('list', 'Progress observations the commissioner already has, each an observation '
                                         'of the same target'),
    'permitted_committed_record_types': SubsetField('text', 'The record types whose committed records the monitor '
                                                            'may return', tuple(sorted(RECORD_SCHEMAS))),
    'information_unit': Field('number', 'The credit of one newly informative received progress snapshot (the '
                                        'old monitor configuration value; positive)'),
})


def read_from_parent(assignment, message):
    return {'target_handle': assignment['target_handle'],
            'requested_fields': list(assignment['requested_fields']),
            'known_progress_refs': list(assignment['known_progress_refs']),
            'permitted_committed_record_types': list(assignment['permitted_committed_record_types']),
            'information_unit': assignment['information_unit'],
            'launch_instructions': message.get('launch_instructions')}
