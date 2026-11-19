"""The commission of the API job execution child (carried from ``to_child_api_job_execution.prepare_commission``):
the child carries out the one request this episode selected for the chosen resource.

The old envelope sent the child a goal with this episode's result contract, the ``scope``, an ``initial_report``,
the selected request as the child's assignment (its ``launch_instructions`` materialised) and the old runner's
bookkeeping (report-contract declaration, expanded contract form, binding lookup, knowledge inheritance: machinery,
not carried). Here the parent states what the child takes in its own words: the request's fields under the old
names (``version``, ``resource_id``, ``service``, ``request``, ``endpoint``, ``constraints``,
``launch_instructions``), the credit a verified handoff earns (``completion_target``, the old ``handoff_unit``),
every record the child's code will read (``input_refs``, which this episode holds from its commissioner) and the
selectable return field it wants (the support receipts of the old ``bvbrc_appservice_support_refs``; the handoff
references and the completion are required fields of the child's return). A commission the child does not admit
fails (rule 1); nothing is checked here.

The slot keeps the old role name ``launch_api``."""
from episode_runtime import ChildMessage

SELECTION = ('bvbrc_appservice_support_refs',)
OLD_PROPERTIES = ('version', 'resource_id', 'service', 'request', 'endpoint', 'constraints')


def msg_to_child(slot, arguments, summary):
    if slot != 'launch_api':
        raise ValueError('execution_job_submission_slot_unknown:' + slot)
    resource_id = arguments['resource_id']
    request = summary['requests'][resource_id]
    assignment = {name: request[name] for name in OLD_PROPERTIES}
    instructions = request.get('launch_instructions')
    if instructions is None:
        instructions = summary['launch_instructions']
    if instructions is not None:
        assignment['launch_instructions'] = instructions
    assignment['completion_target'] = summary['handoff_unit']
    assignment['input_refs'] = list(summary['input_refs'])
    return ChildMessage(objective=('Carry out the permitted concrete execution request on resource ' + resource_id
                                   + ' and return its usable handoff'),
                        message={'resource_id': resource_id, 'initial_report': {}},
                        assignment=assignment, selection=SELECTION)
