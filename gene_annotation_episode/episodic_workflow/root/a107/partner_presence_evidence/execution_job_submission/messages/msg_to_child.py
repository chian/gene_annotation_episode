"""The commission of one launch child: the request of the chosen resource as the child's assignment, every record
this episode names for the child, and the return fields it selects.

The old ``to_child_<role>_job_execution.assemble_request`` (three copies that differ in their docstrings) only built
the old runner's request envelope (goal, scope, initial report, report-contract declaration, job and episode
assignment, knowledge inheritance). The episode's own content was that the child's assignment is the selected
request of the launch assignment (the old ``episode_assignment``, with the launch instructions materialised),
that the scientific parent task reached the child, and that the initial report was empty. A wrong commission
fails: nothing here checks the request against the child.

Slots keep the old role names: ``launch_api`` (the API service child), ``launch_local`` and ``launch_hpc`` (the
practical execution children). Each child declares ``execution_handoff_refs`` and ``execution_completed`` as
selectable fields; every commission selects both (the old ``required_return_sources`` asked for
``execution_handoff_refs`` of a launch whose parent is the head; both are what this episode reads back).

What the children's own forms need and the launch assignment does not carry as such is passed as the form asks:
the API child takes the request's parts as separate fields, the launch's ``scope``, ``input_refs``, the launch's
``immutable_input_versions`` (a list in the launch assignment; the API child declares a record, so that commission
fails at admission) and ``completion_target`` (the credit one verified handoff earns: ``handoff_unit``). The HPC
child declares no ``record_refs`` field: the records the job inputs name cannot be passed to it."""
from episode_runtime import ChildMessage

SELECTION = ('execution_handoff_refs', 'execution_completed')


def _request(summary, arguments):
    request = dict(summary['assignment']['requests'][arguments['resource_id']])
    if 'launch_instructions' in summary['assignment'] and 'launch_instructions' not in request:
        request['launch_instructions'] = summary['assignment']['launch_instructions']
    return request


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = _request(summary, arguments)
    if slot == 'launch_api':
        assignment = {'scope': summary['scope'], 'version': request['version'], 'service': request['service'],
                      'resource_id': resource_id, 'request': request, 'input_refs': list(summary['record_refs']),
                      'immutable_input_versions': summary['assignment']['immutable_input_versions'],
                      'completion_target': summary['handoff_unit']}
        for name in ('algorithm', 'database', 'launch_instructions'):
            if name in request:
                assignment[name] = request[name]
        task = summary['scientific_task']
        if task is not None:
            assignment['scientific_question'] = task['scientific_question']
            assignment['selected_tool_info'] = task['selected_tool_info']
        return ChildMessage(
            objective='Establish the requested usable handoff of the job on the API resource ' + resource_id,
            message={'initial_report': {}}, assignment=assignment, selection=SELECTION)
    if slot == 'launch_local':
        assignment = {**request, 'record_refs': list(summary['record_refs'])}
        if summary['scientific_task'] is not None:
            assignment['scientific_task'] = summary['scientific_task']
        return ChildMessage(
            objective='Execute the assigned job on the local resource ' + resource_id
                      + ' until its requested handoff exists',
            message={'resource_id': resource_id}, assignment=assignment, selection=SELECTION)
    if slot == 'launch_hpc':
        return ChildMessage(
            objective='Execute the assigned job on the HPC resource ' + resource_id
                      + ' until its requested handoff exists',
            message={'resource_id': resource_id}, assignment=request, selection=SELECTION)
    raise ValueError('execution_launch_slot_unknown:' + slot)
