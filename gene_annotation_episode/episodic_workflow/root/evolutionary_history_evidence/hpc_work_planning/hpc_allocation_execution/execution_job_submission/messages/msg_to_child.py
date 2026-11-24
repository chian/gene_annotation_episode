"""The commission of one launch child: the request of the chosen resource as the child's assignment, every record
this episode names for the child, and the return fields it selects.

The old ``to_child_<role>_job_execution.assemble_request`` only built the old runner's request envelope; the
episode's own content was that the child's assignment is the selected request of the launch assignment (the old
``episode_assignment``). A wrong commission fails: nothing here checks the request against the child.

Slots: ``launch_api`` (the API service child), ``launch_local`` and ``launch_hpc`` (the practical execution
children). The API child declares ``execution_handoff_refs`` and ``execution_completed`` as required return fields;
the other two declare them selectable, and this commission selects both (the old ``required_return_sources``
under an annotation task parent)."""
from episode_runtime import ChildMessage


def _request(summary, arguments):
    request = dict(summary['assignment']['requests'][arguments['resource_id']])
    if 'launch_instructions' in summary['assignment'] and 'launch_instructions' not in request:
        request['launch_instructions'] = summary['assignment']['launch_instructions']
    return request


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = _request(summary, arguments)
    if slot == 'launch_api':
        task = summary['scientific_task']
        return ChildMessage(
            objective='Establish the requested usable handoff of the job on the API resource ' + resource_id,
            message={'scientific_question': task['scientific_question'],
                     'selected_tool_info': task['selected_tool_info']},
            assignment={**request, 'input_refs': list(summary['record_refs']),
                        'handoff_unit': summary['handoff_unit'],
                        'acquired_record_unit': summary['acquired_record_unit']},
            selection=())
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
            message={'resource_id': resource_id}, assignment={**request, 'record_refs': list(summary['record_refs'])},
            selection=('execution_handoff_refs', 'execution_completed'))
    raise ValueError('execution_launch_slot_unknown:' + slot)
