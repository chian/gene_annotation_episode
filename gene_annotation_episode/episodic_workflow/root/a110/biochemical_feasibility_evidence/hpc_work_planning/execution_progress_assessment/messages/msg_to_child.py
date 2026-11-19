"""The commission of a child monitor, carried from ``to_child_execution_progress_assessment.py``
(``prepare_dependency_request``) and the monitor branch of ``from_parent.prepare_assignment``: a monitor assignment
whose target is one exposed direct dependency of this monitor's own target and whose permitted committed record
types do not exceed its own. The only child is this episode's own kind (slot ``monitor``).

Both old refusals are kept as the errors this function raises while it builds the commission:
``monitor_child_target_not_exposed_direct_dependency`` and ``monitor_child_expands_permitted_record_types``. The
parent selects the child's return fields it needs: the progress observation identities and their snapshots (the
snapshots are a new field, see ``read_from_child.py``)."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    if slot != 'monitor':
        raise ValueError('monitor_child_slot_unknown:' + repr(slot))
    handle = arguments['dependency_handle']
    if handle not in [row['handle'] for row in summary['monitor_direct_dependencies']]:
        raise ValueError('monitor_child_target_not_exposed_direct_dependency')
    permitted = summary['permitted_committed_record_types']
    wanted = arguments.get('permitted_committed_record_types', permitted)
    if not set(wanted) <= set(permitted):
        raise ValueError('monitor_child_expands_permitted_record_types')
    return ChildMessage(
        objective='Investigate which further exposed progress information is useful for the direct dependency '
                  + handle + ' of ' + summary['target_handle'] + '; no descendant traversal, fanout, cadence or '
                  'depth is prescribed.',
        message={'launch_instructions': summary['launch_instructions']},
        assignment={'version': 'monitor_assignment_v1', 'target_handle': handle,
                    'requested_fields': list(summary['requested_fields']), 'known_progress_refs': [],
                    'permitted_committed_record_types': list(wanted),
                    'information_unit': summary['information_unit']},
        selection=('monitoring_progress_refs', 'monitoring_progress_snapshots'))
