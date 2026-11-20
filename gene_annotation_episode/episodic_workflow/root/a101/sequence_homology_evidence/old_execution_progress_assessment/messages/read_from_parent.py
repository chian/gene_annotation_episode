"""What the commissioner gives: the job, passed in custody, and the limits of the assessment.

The job is named by a record, never by text: ``handoff_refs`` holds the one handoff row of the job ledger that the
launch wrote (``job_access.launch``) and the commissioner holds. ``known_progress_refs`` are the check rows of that
job the commissioner already holds: what it already knows, so a check earns credit only for what they do not show
(the old ``known_progress_refs`` baseline, now records in custody). ``dependency_handoff_refs`` are the handoff rows
of the jobs the target directly depends on: the monitor may assess one of them through a monitor of its own kind,
and can reach no other job (the old exposed direct dependencies; custody is what exposes them now).
``requested_fields`` is what the monitor may observe of the job; ``information_unit`` the credit of one newly
informative check.

``blast_status_target`` is A101's own: whether the job is a BLAST status target (the old
``target_identity.is_blast_job``: an ``api`` job of the service ``ncbi_blast``). The commissioner holds the handoff
row and reads it there (the row's ``kind`` and its ``native`` service); it replaces the old ``target_description``
record. ``yield_estimator.py`` chooses the controller from it: it reads what this file returns, never the
assignment, and is handed no record.

Not carried from the old ``monitor_assignment_v1``: ``target_handle`` (the handoff row names the job) and
``permitted_committed_record_types`` (a job's results are records only after the result-acquisition child fetched
them; a monitor returns none). This is the only place the assignment is read."""
from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import FIELDS

FIELD_OPTIONS = (*FIELDS, 'log_windows')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The version of this assignment form', 'monitor_assignment_v2'),
    'handoff_refs': Field('record_refs', 'The handoff row of the job to assess: exactly one job ledger row, '
                                         'passed in custody'),
    'known_progress_refs': Field('record_refs', 'The check rows of that job the commissioner already holds'),
    'dependency_handoff_refs': Field('record_refs', 'The handoff rows of the jobs the target directly depends on, '
                                                    'which the monitor may assess through a monitor of its own '
                                                    'kind'),
    'requested_fields': SubsetField('text', 'What the monitor may observe of the job; it never observes more',
                                    FIELD_OPTIONS),
    'information_unit': Field('number', 'The credit of one newly informative check (positive)'),
    'blast_status_target': Field('boolean', 'Whether the job is a BLAST status target (an api job of the service '
                                            'ncbi_blast): its monitor visit is complete after one informative '
                                            'status check'),
})


def read_from_parent(assignment, message):
    (handoff_ref,) = assignment['handoff_refs']
    return {'handoff_ref': handoff_ref,
            'known_progress_refs': list(assignment['known_progress_refs']),
            'dependency_handoff_refs': list(assignment['dependency_handoff_refs']),
            'requested_fields': list(assignment['requested_fields']),
            'information_unit': assignment['information_unit'],
            'blast_status_target': assignment['blast_status_target']}
