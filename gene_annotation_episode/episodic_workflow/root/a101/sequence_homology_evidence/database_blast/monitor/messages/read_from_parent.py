"""What the commissioner gives: the job to check and what it already knows, as record references and one number.

``handoff_refs`` holds the one handoff row of the job ledger that the launch wrote and the parent holds, passed in
custody. ``known_progress_refs`` are the check rows of that job the parent already holds: what it already knows, so a
check earns credit only for what they do not show. ``information_unit`` is the credit of one newly informative check.
This is the only place the assignment is read."""
import math

from method_loop import DeclaredField, Field, RecordForm

VERSION = 'database_blast_monitor_assignment_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', VERSION),
    'handoff_refs': Field('record_refs', 'The handoff row of the job to check: exactly one job ledger row, passed in '
                                         'custody'),
    'known_progress_refs': Field('record_refs', 'The check rows of that job the commissioner already holds'),
    'information_unit': Field('number', 'The credit of one newly informative check (positive)'),
})


def read_from_parent(assignment, message):
    if len(assignment['handoff_refs']) != 1:
        raise ValueError('database_blast_monitor_exactly_one_handoff_row_required')
    unit = assignment['information_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_information_unit_required')
    return {'handoff_ref': assignment['handoff_refs'][0],
            'known_progress_refs': list(assignment['known_progress_refs']), 'information_unit': unit}
