"""The commission of the API launch child: the request of the chosen resource as the child's assignment, every record
this episode names for the child, and the return fields it selects.

The old ``to_child_api_job_execution.prepare_commission`` built the old runner's envelope (scope, expanded return
form, initial report, the child's ``prepare_assignment`` of the selected request). The episode's own content was that
the child's assignment is the selected request of the launch assignment (with the launch instructions materialised)
and that the initial report was empty. Its ``required_return_sources`` (``execution_handoff_refs`` when the parent is
the perturbation head and the annotation task is required) is not carried as a condition: the slot keeps the old role
name ``launch_api`` and every commission selects the sources this episode returns. A wrong commission fails: nothing
here checks the request against the child.

The child takes the request's parts as separate fields: the service, the service's own request (the ``request`` of
the closed API service envelope), the launch's ``scope``, ``input_refs``, the launch's ``immutable_input_versions`` (a
list in the launch assignment; the API child declares a record, so the list is passed as ``{'versions': [...]}``) and
``completion_target`` (the credit one verified handoff earns: ``handoff_unit``)."""
from episode_runtime import ChildMessage

SELECTION = ('execution_handoff_refs', 'execution_completed', 'bvbrc_appservice_support_refs',
             'bvbrc_application_outcomes')


def msg_to_child(slot, arguments, summary):
    if slot != 'launch_api':
        raise ValueError('execution_launch_slot_unknown:' + slot)
    resource_id = arguments['resource_id']
    envelope = summary['assignment']['requests'][resource_id]
    assignment = {'scope': summary['scope'], 'service': envelope['service'], 'resource_id': resource_id,
                  'request': envelope['request'], 'input_refs': list(summary['record_refs']),
                  'immutable_input_versions': {'versions': list(summary['assignment']['immutable_input_versions'])},
                  'completion_target': summary['handoff_unit']}
    for name in ('algorithm', 'database'):
        if name in envelope:
            assignment[name] = envelope[name]
    instructions = envelope.get('launch_instructions', summary['assignment'].get('launch_instructions'))
    if instructions is not None:
        assignment['launch_instructions'] = instructions
    return ChildMessage(
        objective='Establish the requested usable handoff of the job on the API resource ' + resource_id,
        message={'initial_report': {}}, assignment=assignment, selection=SELECTION)
