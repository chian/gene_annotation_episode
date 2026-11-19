"""The commission of a resource child (carried from ``to_child_api_job_execution``, ``to_child_local_job_execution``
and ``to_child_hpc_job_execution`` (``assemble_request``: the same text in the three files) and ``to_children``):
the child carries out the one request this episode selected for the chosen resource.

The old envelope sent the child a goal with this episode's result contract, the ``scope``, an ``initial_report``,
the selected request as the child's assignment (its ``launch_instructions`` materialised) and the old runner's
bookkeeping (report-contract declaration, expanded contract form, binding lookup, knowledge inheritance: machinery,
not carried). Here the parent states what each child takes in its own words, under the old names. A commission the
child does not admit fails (rule 1); nothing is checked here.

* ``launch_api`` (``api_job_execution``): the request's ``version``, ``service``, ``algorithm`` and ``database``,
  the request itself (``request``), ``scope``, the records the request names (``input_refs``), the immutable
  input versions, the pinned launch instructions and the credit a verified handoff earns (``completion_target``,
  the old ``handoff_unit``). The child declares ``immutable_input_versions`` as a record, this episode holds a
  list (the old assignment): the list travels under the key ``input_versions``.
* ``launch_local`` (``local_job_execution``) and ``launch_hpc`` (``hpc_job_execution``): the request is the
  practical assignment, field for field. The local child also takes the records the job inputs name
  (``record_refs``) and the scientific task of a native protein-structure job (``scientific_task``).

Every record the child's code will read is named: ``input_refs``, which this episode holds from its commissioner.
The slots keep the old role names. The fields it selects are the handoff references and the completion; the
child's credit and finding are always returned."""
from episode_runtime import ChildMessage

SELECTION = ('execution_handoff_refs', 'execution_completed')


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = summary['requests'][resource_id]
    instructions = request.get('launch_instructions')
    if instructions is None:
        instructions = summary['launch_instructions']
    if slot == 'launch_api':
        assignment = {'scope': summary['scope'], 'version': request['version'], 'service': request['service'],
                      'resource_id': resource_id, 'request': request, 'input_refs': list(summary['input_refs']),
                      'immutable_input_versions': {'input_versions': list(summary['immutable_input_versions'])},
                      'completion_target': summary['handoff_unit']}
        for name in ('algorithm', 'database'):
            if name in request:
                assignment[name] = request[name]
    elif slot == 'launch_local':
        assignment = {**request, 'record_refs': list(summary['input_refs'])}
        if summary['scientific_task'] is not None:
            assignment['scientific_task'] = summary['scientific_task']
    elif slot == 'launch_hpc':
        assignment = dict(request)
    else:
        raise ValueError('execution_job_submission_slot_unknown:' + slot)
    if instructions is not None:
        assignment['launch_instructions'] = instructions
    return ChildMessage(objective=('Carry out the permitted concrete execution request on resource ' + resource_id
                                   + ' and return its usable handoff'),
                        message={'resource_id': resource_id, 'initial_report': {}},
                        assignment=assignment, selection=SELECTION)
