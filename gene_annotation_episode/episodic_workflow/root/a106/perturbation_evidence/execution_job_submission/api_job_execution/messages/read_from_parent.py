"""What the commissioning launch parent gives (carried from ``from_parent.py``, ``from_parent_launch.py`` and the
request message).

Old assignment: one concrete API request for one configured resource (``resource_id`` required, the service's
request form, here an AppService request ``bvbrc_appservice_request``). The old code re-read the parent launch's own
assignment (``immutable_input_versions``, ``launch_instructions``): in the final form the parent copies what this
episode reads into the assignment (``msg_to_child``), so each is a field here. Fields the old code did not have are
listed in the carry-over record as new fields: ``scope``, ``input_refs``, ``completion_target``. The executor's
per-resource assignment schema is outside the episode trees, so the service-specific request parameters ride in
``request``; ``service`` names the configured service of the resource.
"""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The subject scope fixed by the commissioning parent'),
    'service': Field('text', 'The configured API service that carries out the work'),
    'algorithm': Field('text', 'The service algorithm, when the service has one', required=False),
    'database': Field('text', 'The service database, when the service has one', required=False),
    'resource_id': Field('text', 'The configured API resource that runs the work'),
    'request': Field('record', "The parent's request for this resource, in the service's request form"),
    'input_refs': Field('record_refs', 'The input records the request names, passed in custody'),
    'immutable_input_versions': Field('record', 'The input versions that stay fixed while the work runs'),
    'launch_instructions': Field('record', 'The launch instruction selection chosen for this assignment',
                                 required=False),
    'completion_target': Field('number', 'The credit one verified handoff earns: the commission is complete there'),
})


def read_from_parent(assignment, message):
    """The parent input: every assignment field (``None`` for an omitted optional one) and the message's values."""
    return {'service': assignment['service'], 'algorithm': assignment.get('algorithm'),
            'database': assignment.get('database'), 'resource_id': assignment['resource_id'],
            'scope': assignment['scope'], 'request': assignment['request'],
            'input_refs': list(assignment['input_refs']),
            'immutable_input_versions': assignment['immutable_input_versions'],
            'launch_instructions': assignment.get('launch_instructions'),
            'completion_target': assignment['completion_target'],
            'initial_report': message['initial_report']}
