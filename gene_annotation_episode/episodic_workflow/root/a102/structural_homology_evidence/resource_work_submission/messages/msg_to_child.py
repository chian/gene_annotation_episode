"""The commission of a resource child (``launch_api``, ``launch_local``, ``launch_hpc``): launch the assigned work
on the chosen resource and return at handoff.

Everything in it is controlled: the objective is a fixed value, the message is empty, and the assignment is the
chosen resource id, the work and its inputs as record references (this episode holds them, so it may pass them)
and the two credit units of a launch (the even split of this episode's own completion target). No selectable
return field is asked for: the handoff and check rows are required fields of the child's return. The commission is
written for the child's own form; one the child's form does not admit fails there (nothing is checked here)."""
from episode_runtime import ChildMessage

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import LAUNCH_VERSION

OBJECTIVE = 'launch_the_assigned_work_and_return_at_handoff'


def msg_to_child(slot, arguments, summary):
    assignment = {'version': LAUNCH_VERSION, 'resource_id': arguments['resource_id'],
                  'work_refs': [summary['work_ref']], 'input_refs': list(summary['input_refs']),
                  'handoff_unit': summary['launch_units']['handoff_unit'],
                  'check_unit': summary['launch_units']['check_unit']}
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=())
