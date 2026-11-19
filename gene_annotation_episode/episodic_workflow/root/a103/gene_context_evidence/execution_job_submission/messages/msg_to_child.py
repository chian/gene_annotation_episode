"""The commission of one launch child: the request of the chosen resource as the child's assignment, every record
this episode names for the child, and the return fields it selects.

The old ``to_child_<role>_job_execution.assemble_<role>_job_execution_request`` (three copies that differ only in the
role name) built the old runner's envelope (goal, expanded return form, ``scope``, ``initial_report``, the
materialised ``launch_instructions`` of the episode assignment, ``job_assignment``, the receipts ledger binding, the
saved-form declaration). That envelope is the system's now. The episode's own content was that the child's
assignment is the selected request of the launch assignment (with the launch instructions materialised), that the
scientific parent task reached the child, and that the initial report was empty. A wrong commission fails: nothing
here checks the request against the child.

Slots keep the old role names: ``launch_api`` (the API service child), ``launch_local`` and ``launch_hpc`` (the
practical execution children). Each child declares ``execution_handoff_refs`` and ``execution_completed`` as
selectable fields; every commission selects both (the old ``required_return_sources`` asked for
``execution_handoff_refs`` of a launch whose parent is the A103 head; both are what this episode reads back).

What the children's own forms need and the launch assignment does not carry as such is passed as the form asks: the
API child takes the request's parts as separate fields (an ``api_service_assignment_v1`` request as ``request``),
the launch's ``scope``, ``input_refs``, the launch's ``immutable_input_versions`` (a list in the launch assignment;
the API child declares a record, so the list is passed as ``{'versions': [...]}``) and ``completion_target`` (the
credit one verified handoff earns: ``handoff_unit``). The HPC child declares no ``record_refs`` field: the records
the job inputs name cannot be passed to it (contract_misfits)."""
from episode_runtime import ChildMessage

SELECTION = ('execution_handoff_refs', 'execution_completed')
API_V1_FIELDS = ('version', 'resource_id', 'service', 'subject_ref', 'algorithm', 'database', 'parameters',
                 'page_size', 'endpoint', 'constraints')


def _request(summary, arguments):
    request = dict(summary['assignment']['requests'][arguments['resource_id']])
    if 'launch_instructions' in summary['assignment'] and 'launch_instructions' not in request:
        request['launch_instructions'] = summary['assignment']['launch_instructions']
    return request


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = _request(summary, arguments)
    if slot == 'launch_api':
        if request['version'] == 'api_execution_assignment_v1':
            assignment = {name: request[name] for name in API_V1_FIELDS}
        else:
            assignment = {name: request[name] for name in ('version', 'resource_id', 'service', 'request',
                                                           'endpoint', 'constraints')}
        if 'launch_instructions' in request:
            assignment['launch_instructions'] = request['launch_instructions']
        assignment.update({'scope': summary['scope'], 'input_refs': list(summary['record_refs']),
                           'immutable_input_versions': {'versions': list(
                               summary['assignment']['immutable_input_versions'])},
                           'completion_target': summary['handoff_unit']})
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
