"""The commission of one launch child: the request of the chosen resource as the child's assignment, every record
this episode names for the child, and the return fields it selects.

The old ``to_child_<role>_job_execution.assemble_request`` only built the old runner's request envelope; the
episode's own content was that the child's assignment is the selected request of the launch assignment (the old
``episode_assignment``; ``prepare_child_request`` passed it through unchanged). A wrong commission fails: nothing
here checks the request against the child.

Slots: ``launch_local`` and ``launch_hpc`` (the practical execution children). The local child takes the records
the job inputs name (``record_refs``) and the scientific parent task; the HPC child's assignment form admits
neither, so neither is sent to it. Both declare ``execution_handoff_refs`` and ``execution_completed`` selectable,
and this commission selects both (the old ``required_return_sources`` under an annotation task parent)."""
from episode_runtime import ChildMessage


def _request(summary, arguments):
    request = dict(summary['assignment']['requests'][arguments['resource_id']])
    if 'launch_instructions' in summary['assignment'] and 'launch_instructions' not in request:
        request['launch_instructions'] = summary['assignment']['launch_instructions']
    return request


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = _request(summary, arguments)
    if slot == 'launch_local':
        assignment = {**request, 'record_refs': list(summary['record_refs'])}
        if summary['scientific_task'] is not None:
            assignment['scientific_task'] = summary['scientific_task']
        return ChildMessage(
            objective='Execute the assigned job on the local resource ' + resource_id
                      + ' until its requested handoff exists',
            message={'resource_id': resource_id}, assignment=assignment,
            selection=('execution_handoff_refs', 'execution_completed'))
    if slot == 'launch_hpc':
        return ChildMessage(
            objective='Execute the assigned job on the HPC resource ' + resource_id
                      + ' until its requested handoff exists',
            message={'resource_id': resource_id}, assignment=request,
            selection=('execution_handoff_refs', 'execution_completed'))
    raise ValueError('execution_launch_slot_unknown:' + slot)
