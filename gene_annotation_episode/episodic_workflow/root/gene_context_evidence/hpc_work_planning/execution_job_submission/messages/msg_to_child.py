"""The commission of a resource child (carried from ``child_commissioning.py`` and the three ``to_child_<role>.py``,
which were the same text): the child runs the one request this episode selected for the chosen resource.

The old envelope sent the child a goal with this episode's result contract, the ``scope``, an ``initial_report``,
``job_assignment``, ``episode_assignment`` (its ``launch_instructions`` materialised), ``gene_context_evidence`` and
the old runner's bookkeeping (in-process completion order, report-contract declaration, knowledge inheritance:
machinery, not carried). The selected request itself was the child's assignment. Here the parent states what each
child takes in its own form: the request, the pinned launch instructions when the request carries none (the old
``episode_assignment``), the values the child's form names that the old code did not name (``completion_target`` and
``input_refs`` of the API child, ``record_refs`` and ``scientific_task`` of the local child) and the selectable
return fields it wants. Every record the child's code will read is named, because a pass carries only the records
named. A commission the child does not admit fails (rule 1); nothing is checked here.

The slots keep the old child role names: ``launch_api``, ``launch_local``, ``launch_hpc``. The API child declares
its handoff references and completion as required return fields (always returned), so this episode selects
nothing from it; the HPC and local children declare both selectable, and this episode selects them."""
from episode_runtime import ChildMessage

SELECTION = ('execution_handoff_refs', 'execution_completed')


def pinned_request(request, summary):
    """The request with the launch instructions the commissioner pinned for this launch, when the request carries
    none of its own."""
    request = dict(request)
    if 'launch_instructions' not in request and summary['launch_instructions'] is not None:
        request['launch_instructions'] = summary['launch_instructions']
    return request


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = pinned_request(summary['requests'][resource_id], summary)
    if slot == 'launch_api':
        assignment = {**request, 'completion_target': summary['handoff_unit'],
                      'input_refs': list(summary['input_refs'])}
        selection = ()
    elif slot == 'launch_hpc':
        assignment = request
        selection = SELECTION
    elif slot == 'launch_local':
        assignment = {**request, 'record_refs': list(summary['input_refs'])}
        if summary['scientific_task'] is not None:
            assignment['scientific_task'] = summary['scientific_task']
        selection = SELECTION
    else:
        raise ValueError('execution_job_submission_slot_unknown:' + slot)
    return ChildMessage(objective=('Run the permitted concrete execution request on resource ' + resource_id
                                   + ' and return its usable handoff'),
                        message={'resource_id': resource_id, 'initial_report': {}},
                        assignment=assignment, selection=selection)
