"""What the A106 monitor sends the monitor it may commission (carried from ``to_child_execution_progress_assessment.py``
and the dependency branch of ``from_parent.prepare_assignment``).

Its one child slot is a monitor of its own kind (self-nesting). The child's target must be one of this target's
exposed direct dependencies and the child's permitted committed record types must not exceed this monitor's: the
old runner checked both inside the child (``prepare_dependency_request`` reading ``parent.assignment``); here they
are made in ``task.action`` before this function is reached (the model's selection is rejected, no unit). The
assignment sends the old ``monitor_assignment_v1`` keys, the scope and the information unit; the baseline
snapshots are those this monitor holds for the references it passes. The parent selects the child's return
fields it reads: the progress observation identities and their snapshots.
"""
from __future__ import annotations

from episode_runtime import ChildMessage

from ..goal import GOAL

ASSIGNMENT_VERSION = 'monitor_assignment_v1'
RESULT_CONTRACT = {'decision': 'Use the child finding in the parent cycle', 'measurements': {},
                   'information': {'finding': 'What the child established, with its record references'}}


def msg_to_child(slot, arguments, summary):
    references = list(arguments['known_progress_refs'])
    return ChildMessage(
        objective=GOAL,
        message={'result_contract': RESULT_CONTRACT, 'target_handle': arguments['target_handle']},
        assignment={'scope': summary['scope'], 'version': ASSIGNMENT_VERSION,
                    'target_handle': arguments['target_handle'],
                    'requested_fields': list(arguments['requested_fields']),
                    'known_progress_refs': references,
                    'permitted_committed_record_types': list(arguments['permitted_committed_record_types']),
                    'information_unit': summary['information_unit'],
                    'known_progress_snapshots': {reference: summary['progress_snapshots'][reference]
                                                 for reference in references}},
        selection=('monitoring_progress_refs', 'monitoring_progress_snapshots'))
