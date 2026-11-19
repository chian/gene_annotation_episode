"""The commission of a resource child (carried from ``to_children.py`` and the three identical
``to_child_<role>.py``): the child runs the one request this episode selected for the chosen resource.

The old envelope sent the child a goal with this episode's result contract, the ``scope``, an ``initial_report``,
the selected request as the child's assignment (its ``launch_instructions`` materialised) and the old runner's
bookkeeping (in-process completion order, report-contract declaration, knowledge inheritance: machinery, not
carried). Here the parent states what each child takes in its own words: the request (and, for the API child, the
values its form names), every record the child's code will read (``input_refs``, which this episode holds from its
commissioner) and the selectable return fields it wants. A commission the child does not admit fails (rule 1);
nothing is checked here.

The slots keep the old role names: ``launch_api``, ``launch_local``, ``launch_hpc``."""
from episode_runtime import ChildMessage

SELECTION = ('execution_handoff_refs', 'execution_completed')


def _pinned(request, summary):
    """The launch instructions the child's assignment carries: the request's own selection, else the selection
    the commissioner pinned for this launch (the old goal: preserve pinned instructions)."""
    return request.get('launch_instructions', summary['launch_instructions'])


def _api_assignment(resource_id, request, summary):
    assignment = {'scope': summary['scope'], 'version': request['version'], 'service': request['service'],
                  'resource_id': resource_id, 'request': request, 'input_refs': list(summary['input_refs']),
                  'immutable_input_versions': {'versions': list(summary['immutable_input_versions'])},
                  'completion_target': summary['handoff_unit']}
    for field in ('algorithm', 'database'):
        if field in request:
            assignment[field] = request[field]
    instructions = _pinned(request, summary)
    if instructions is not None:
        assignment['launch_instructions'] = instructions
    return assignment


def _practical_assignment(request, summary):
    assignment = dict(request)
    instructions = _pinned(request, summary)
    if instructions is not None:
        assignment['launch_instructions'] = instructions
    return assignment


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = summary['requests'][resource_id]
    if slot == 'launch_api':
        assignment = _api_assignment(resource_id, request, summary)
    elif slot == 'launch_hpc':
        assignment = _practical_assignment(request, summary)
    elif slot == 'launch_local':
        assignment = {**_practical_assignment(request, summary), 'record_refs': list(summary['input_refs'])}
        if summary['scientific_task'] is not None:
            assignment['scientific_task'] = summary['scientific_task']
    else:
        raise ValueError('execution_job_submission_slot_unknown:' + slot)
    return ChildMessage(objective=('Run the permitted concrete execution request on resource ' + resource_id
                                   + ' and return its usable handoff'),
                        message={'resource_id': resource_id, 'initial_report': {}},
                        assignment=assignment, selection=SELECTION)
