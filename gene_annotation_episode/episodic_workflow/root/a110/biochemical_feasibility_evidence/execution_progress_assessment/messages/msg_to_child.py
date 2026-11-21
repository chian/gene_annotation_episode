"""The commission of a dependency monitor: a monitor of this episode's own kind (slot ``monitor``) for one job the
target directly depends on.

Carried from ``to_child_execution_progress_assessment.py`` (``prepare_dependency_request``). The dependency is one
whose handoff row the commissioner passed to this monitor (``dependency_handoff_refs``); this function passes that
row on in custody, with the check rows of that job this monitor already holds as the child's baseline. The child
is handed no dependencies of its own: no descendant traversal. A handle that is not one of the passed dependencies
fails here with its ``KeyError`` (the old ``monitor_child_target_not_exposed_direct_dependency``). The child's
required fields (credit, finding, check rows) are all this monitor needs, so nothing more is selected."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    dependency = {row['handle']: row for row in summary['dependencies']}[arguments['dependency_handle']]
    return ChildMessage(
        objective='Assess the progress of job ' + dependency['handle'] + ', which job '
                  + summary['job']['handle'] + ' directly depends on.',
        message={},
        assignment={'version': 'monitor_assignment_v2', 'handoff_refs': [dependency['handoff_ref']],
                    'known_progress_refs': list(dependency['check_refs']), 'dependency_handoff_refs': [],
                    'requested_fields': list(summary['requested_fields']),
                    'information_unit': summary['information_unit']},
        selection=())
