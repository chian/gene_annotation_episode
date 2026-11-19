"""What the A110 monitor sends the monitor it may commission (carried from
``to_child_execution_progress_assessment.py`` (``prepare_dependency_request``) and the dependency branch of
``from_parent.prepare_assignment``).

Its one child slot is a monitor of its own kind (self-nesting). The child's target must be one of this target's
exposed direct dependencies and the child's permitted committed record types must not exceed this monitor's: both
old refusals are errors this function raises while it builds the commission (a wrong commission fails), under the
old codes ``monitor_child_target_not_exposed_direct_dependency`` and ``monitor_child_expands_permitted_record_types``.
The assignment sends the old ``monitor_assignment_v1`` keys and the information unit; the baseline snapshots are
those this monitor holds for the references it passes (a reference it holds no snapshot of raises ``KeyError``).
The parent selects the child's return fields it reads: the progress observation identities and their snapshots."""
from episode_runtime import ChildMessage

from ..goal import GOAL

ASSIGNMENT_VERSION = 'monitor_assignment_v1'


def msg_to_child(slot, arguments, summary):
    if slot != 'monitor':
        raise ValueError('monitor_child_slot_unknown:' + repr(slot))
    handle = arguments['dependency_handle']
    if handle not in [row['handle'] for row in summary['monitor_direct_dependencies']]:
        raise ValueError('monitor_child_target_not_exposed_direct_dependency')
    if not set(arguments['permitted_committed_record_types']) <= set(summary['permitted_committed_record_types']):
        raise ValueError('monitor_child_expands_permitted_record_types')
    references = list(arguments['known_progress_refs'])
    return ChildMessage(
        objective=GOAL,
        message={'target_handle': handle, 'launch_instructions': summary['launch_instructions']},
        assignment={'version': ASSIGNMENT_VERSION, 'target_handle': handle,
                    'requested_fields': list(arguments['requested_fields']),
                    'known_progress_refs': references,
                    'permitted_committed_record_types': list(arguments['permitted_committed_record_types']),
                    'information_unit': summary['information_unit'],
                    'known_progress_snapshots': {reference: summary['progress_snapshots'][reference]
                                                 for reference in references}},
        selection=('monitoring_progress_refs', 'monitoring_progress_snapshots'))
