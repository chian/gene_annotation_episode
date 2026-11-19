"""The commission of one launch child: the request of the chosen resource as the child's assignment, every record
this episode names for the child, and the return fields it selects.

The old ``to_child_<role>_job_execution.assemble_request`` (three identical copies) only built the old runner's request
envelope (goal, scope, initial report, report-contract declaration, job and episode assignment, receipt inheritance).
The episode's own content was that the child's assignment is the launch request (the old ``prepare_child_request``
returned the assignment unchanged for the three roles; the children chose their own request among its ``requests``,
which a child can no longer read, so this commission names it). A wrong commission fails: nothing here checks the
request against the child.

Slots: ``launch_api`` (the API service child), ``launch_local`` and ``launch_hpc`` (the practical execution
children). The API child declares ``execution_handoff_refs`` and ``execution_completed`` as required return fields;
the other two declare them selectable, and this commission selects both (the old ``required_return_sources`` under an
annotation task parent: ``execution_handoff_refs``)."""
from episode_runtime import ChildMessage


def _request(summary, arguments):
    request = dict(summary['assignment']['requests'][arguments['resource_id']])
    if 'launch_instructions' in summary['assignment'] and 'launch_instructions' not in request:
        request['launch_instructions'] = summary['assignment']['launch_instructions']
    return request


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = _request(summary, arguments)
    task = summary['scientific_task']
    if slot == 'launch_api':
        message = {} if task is None else {'scientific_question': task['scientific_question'],
                                           'selected_tool_info': task['selected_tool_info']}
        return ChildMessage(
            objective='Establish the requested usable handoff of the job on the API resource ' + resource_id,
            message=message,
            assignment={**request, 'completion_target': summary['handoff_unit'],
                        'input_refs': list(summary['record_refs'])},
            selection=())
    if slot == 'launch_local':
        assignment = {**request, 'record_refs': list(summary['record_refs'])}
        if task is not None:
            assignment['scientific_task'] = task
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
