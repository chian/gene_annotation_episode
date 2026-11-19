"""What the commissioner gives: the monitor assignment (old ``monitor_assignment_v1``, from ``from_parent.py``
``MonitorAssignment.assignment_schema``): the target, the fields the monitor may observe, the progress observations
the commissioner already has and the record types whose committed records it may return.

Two fields are new (listed in the carry-over record): ``information_unit`` (the old binding took it from its
configuration; the credit needs it and ``credit`` has no settings) and ``known_progress_snapshots`` (the old
``known_progress_refs`` named observations the old progress provider held; a commission carries no provider, so the
commissioner passes the observations it received, by reference, beside the references).

The old admission of the assignment (``MonitorAssignment._assignment``) is carried as far as this function can: a
known progress observation passed with its snapshot must be an observation of the same target
(``monitor_known_progress_target_mismatch``). That the target handle is an execution handle in scope (the old
provider check) needs the job service and is not made here: a target that is not one fails at its first
observation."""
from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    ContractError, RECORD_SCHEMAS)

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
    'known_progress_snapshots': Field('record', 'The snapshots of known_progress_refs, by reference, as the '
                                                'commissioner received them', required=False),
})


def read_from_parent(assignment, message):
    snapshots = assignment.get('known_progress_snapshots', {})
    for reference in assignment['known_progress_refs']:
        if reference in snapshots and snapshots[reference]['target_handle'] != assignment['target_handle']:
            raise ContractError('monitor_known_progress_target_mismatch')
    return {'target_handle': assignment['target_handle'],
            'requested_fields': list(assignment['requested_fields']),
            'known_progress_refs': list(assignment['known_progress_refs']),
            'known_progress_snapshots': dict(snapshots),
            'permitted_committed_record_types': list(assignment['permitted_committed_record_types']),
            'information_unit': assignment['information_unit'],
            'launch_instructions': message.get('launch_instructions')}
