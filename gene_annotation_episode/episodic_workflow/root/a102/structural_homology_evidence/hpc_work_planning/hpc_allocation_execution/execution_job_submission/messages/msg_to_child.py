"""The commission of one resource child (carried from ``to_child_api_job_execution.py``,
``to_child_local_job_execution.py`` and ``to_child_hpc_job_execution.py``, which were the same text).

Each child is commissioned with the request this launch holds for the explicit ``resource_id`` of the
``ChildCall``: the request's own fields under their old names, the subject scope, the records the job reads (named
here, because a pass carries only the records named), the pinned launch-instruction selection (the child
materialises it from its own library), and the optional return fields wanted. The old report-contract declaration
and the receipt inheritance are old-runner machinery (the child's return form is its own; custody is the
system's). A request this launch does not hold raises ``StopIteration``: a wrong commission fails."""
from episode_runtime import ChildMessage

PRACTICAL_FIELDS = ('version', 'assignment_id', 'resource_id', 'resource_kind', 'workspace', 'endpoint',
                    'requested_job', 'progress_requirements', 'completion_keys', 'initial_context',
                    'inventory_snapshot', 'constraints')
API_OPTIONAL = ('algorithm', 'database')
SELECTION = ('execution_handoff_refs', 'execution_result_refs', 'execution_completed')
# practical_receipt_artifact_refs is a required field of the local child: it is always returned, never selected.
INITIAL_REPORT = 'nothing yet'


def _instructions(request, summary):
    selection = request.get('launch_instructions', summary['launch_instructions'])
    return {} if selection is None else {'launch_instructions': selection}


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = next(item for item in summary['requests'] if item['resource_id'] == resource_id)
    objective = 'Execute the permitted request on resource ' + resource_id + ' and return its usable handoff'
    message = {'initial_report': INITIAL_REPORT}
    if slot == 'api':
        assignment = {'scope': summary['scope'], 'version': request['version'], 'service': request['service'],
                      'resource_id': resource_id, 'request': request, 'input_refs': list(summary['input_refs']),
                      'immutable_input_versions': summary['immutable_input_versions'],
                      'completion_target': summary['handoff_unit'], **_instructions(request, summary),
                      **{name: request[name] for name in API_OPTIONAL if request.get(name) is not None}}
    elif slot in ('local', 'hpc'):
        assignment = {name: request[name] for name in PRACTICAL_FIELDS} | _instructions(request, summary)
        if slot == 'local':
            assignment['scope'] = summary['scope']
            assignment['input_refs'] = list(summary['input_refs'])
            if summary['scientific_task'] is not None:
                assignment['scientific_task'] = summary['scientific_task']
    else:
        raise LookupError('execution_job_submission_has_no_slot:' + slot)
    return ChildMessage(objective=objective, message=message, assignment=assignment, selection=SELECTION)
