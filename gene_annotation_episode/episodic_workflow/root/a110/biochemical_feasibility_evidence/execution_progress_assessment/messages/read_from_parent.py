"""What the A110 monitor reads from its parent's assignment (carried from ``from_parent.py`` and ``contracts.py``).

The parent fills ``ASSIGNMENT_FORM``: one field per property of the old ``monitor_assignment_v1`` schema under its
old name (``version``, ``target_handle``, ``requested_fields``, ``known_progress_refs``,
``permitted_committed_record_types``), plus the two new fields the old monitor took from elsewhere
(``information_unit``, ``known_progress_snapshots``). ``read_from_parent`` is the one place the assignment is read.

The old admission steps that need the old progress provider are not made here (this function is handed no records
and no services): the target being an execution handle in scope is made at the first decision (``task.decide``
reads the job-access service, BLOCKED-ON-JOB-SERVICE); a known progress ref passed with its snapshot is checked
against the target here; the old provider read of a ref passed without a snapshot has no object any more
(``credit`` raises where it is needed)."""
from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.biochemical_feasibility_evidence.progress_provider import (
    FIELDS)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    ContractError, RECORD_SCHEMAS)

ASSIGNMENT_VERSION = 'monitor_assignment_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The version of this assignment form', ASSIGNMENT_VERSION),
    'target_handle': Field('text', 'The execution handle whose progress is observed'),
    'requested_fields': SubsetField('text', 'The exposed fields the monitor may observe; it never observes more',
                                    FIELDS),
    'known_progress_refs': Field('list', 'Progress observations of this target the commissioner already holds'),
    'permitted_committed_record_types': SubsetField(
        'text', 'The record types whose committed records the monitor may return', tuple(sorted(RECORD_SCHEMAS))),
    'information_unit': Field('number', 'The credit of one newly informative received progress snapshot (the old '
                                        'monitor configuration value; positive)'),
    'known_progress_snapshots': Field('record', 'The snapshots of known_progress_refs by reference, as the '
                                                'commissioner received them', required=False),
})


def read_from_parent(assignment, message):
    """The parent input: the admitted ``monitor_assignment_v1`` fields, the information unit and the baseline."""
    unit = assignment['information_unit']
    if unit <= 0:
        raise ContractError('explicit_positive_monitoring_information_unit_required')
    snapshots = plain(assignment.get('known_progress_snapshots', {}))
    refs = plain(assignment['known_progress_refs'])
    for reference in refs:
        if reference in snapshots and snapshots[reference]['target_handle'] != assignment['target_handle']:
            raise ContractError('monitor_known_progress_target_mismatch')
    return {'version': assignment['version'], 'target_handle': assignment['target_handle'],
            'requested_fields': plain(assignment['requested_fields']), 'known_progress_refs': refs,
            'permitted_committed_record_types': plain(assignment['permitted_committed_record_types']),
            'information_unit': unit, 'known_progress_snapshots': snapshots,
            'launch_instructions': plain(message).get('launch_instructions')}
