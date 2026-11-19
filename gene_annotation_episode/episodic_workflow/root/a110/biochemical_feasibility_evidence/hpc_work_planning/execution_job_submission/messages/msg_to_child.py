"""The commission of one route child (the old ``to_child_hpc_job_execution.assemble_request`` and
``to_child_local_job_execution.assemble_request``): the selected request, unchanged, as the child's practical
assignment (with the launch-level launch_instructions the old envelope's episode_assignment carried), and the return fields this launch wants. A resource_id that is not a request of this launch, or a
slot that does not match its kind, fails the commission with the error itself.

Not carried: the old envelope's scope, ``inprocess_completion_order``, ``report_contract_declaration``,
``knowledge_inheritance`` and ``biochemical_feasibility_evidence`` message parts (runner machinery)."""
from episode_runtime import ChildMessage

SELECTION = ('execution_handoff_refs', 'execution_completed')


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = summary['requests'][resource_id]
    assignment = dict(request)
    if 'launch_instructions' in summary:
        assignment['launch_instructions'] = summary['launch_instructions']
    if slot == 'local_job_execution':
        if summary['record_refs']:
            assignment['record_refs'] = list(summary['record_refs'])
        if 'scientific_task' in summary:
            assignment['scientific_task'] = summary['scientific_task']
    return ChildMessage(
        objective='Execute the requested job on the assigned resource ' + resource_id + ' and return the handoff '
                  'to the actual job (endpoint ' + request['endpoint'] + ')',
        message={'resource_id': resource_id, 'resource_kind': request['resource_kind'],
                 'endpoint': request['endpoint']},
        assignment=assignment, selection=SELECTION)
