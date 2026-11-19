"""The commission of one resource child (carried from ``to_child_api_job_execution.py``,
``to_child_hpc_job_execution.py`` and ``to_child_local_job_execution.py``, which were the same text).

Each child is commissioned with the concrete request this launch holds for the explicit ``resource_id`` of the
``ChildCall``, exactly as the assignment states it (the old ``job_assignment``), the pinned launch-instruction
selection when the request carries none (the old ``episode_assignment``), and every record the job reads, named
here because a pass carries only the records named (the old ``initial_references``). New fields of the children's
forms: ``completion_target`` of the API child is the credit one usable handoff earns (``handoff_unit``); the HPC
child takes the records as ``input_refs`` and the local child as ``record_refs``; the local child also takes the
ancestor's ``scientific_task``. The old report-contract declaration, the in-process completion order, the goal of
the child and the knowledge inheritance were old-runner machinery (the child's return form is its own; custody is
the system's). A resource this launch holds no request for raises ``KeyError``: a wrong commission fails.

Selection: the API and HPC children always return their handoff references and completion; the local child
declares both selectable, so this launch selects them."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = dict(summary['requests'][resource_id])
    if 'launch_instructions' not in request and summary['launch_instructions'] is not None:
        request['launch_instructions'] = summary['launch_instructions']
    objective = 'Execute the permitted request on resource ' + resource_id + ' and return its usable handoff'
    message = {'resource_id': resource_id, 'initial_report': 'nothing yet'}
    if slot == 'api_job_execution':
        assignment = {**request, 'completion_target': summary['handoff_unit'], 'input_refs': list(summary['input_refs'])}
        selection = ()
    elif slot == 'hpc_job_execution':
        assignment = {**request, 'input_refs': list(summary['input_refs'])}
        selection = ()
    elif slot == 'local_job_execution':
        assignment = {**request, 'record_refs': list(summary['input_refs'])}
        if summary['scientific_task'] is not None:
            assignment['scientific_task'] = summary['scientific_task']
        selection = ('execution_handoff_refs', 'execution_completed')
    else:
        raise LookupError('execution_job_submission_has_no_slot:' + slot)
    return ChildMessage(objective=objective, message=message, assignment=assignment, selection=selection)
