"""What the commissioning launch parent gives (carried from ``from_parent.py``, ``from_parent_launch.py`` and the
request message).

Old assignment properties, under the same names: ``version`` (``api_execution_assignment`` or
``api_service_assignment``), ``service``, ``algorithm``, ``database``, ``resource_id``. The old code re-read the
parent launch's own assignment (``requests``, ``immutable_input_versions``, ``constraints``,
``launch_instructions``) and the parent's scientific task through ``services.scientific_parent_task``
(``scientific_question``, ``selected_tool_info``, used for an ``ebi_hmmer`` request): in the final form the parent
copies what this episode reads into the assignment (``msg_to_child``), so each is a field here. Fields the old code
did not have are listed in the carry-over record as new fields: ``scope``, ``request``, ``input_refs``,
``completion_target``.
"""
from method_loop import ChoiceField, Field, RecordForm

VERSIONS = ('api_execution_assignment', 'api_service_assignment')

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The subject scope fixed by the commissioning parent'),
    'version': ChoiceField('text', 'The assignment version; the service-job version permits waiting', VERSIONS),
    'service': Field('text', 'The configured API service that carries out the work'),
    'algorithm': Field('text', 'The service algorithm, when the service has one', required=False),
    'database': Field('text', 'The service database, when the service has one', required=False),
    'resource_id': Field('text', 'The configured API resource that runs the work'),
    'request': Field('record', "The parent's request for this resource, in the service's request form"),
    'input_refs': Field('record_refs', 'The input records the request names, passed in custody'),
    'immutable_input_versions': Field('record', 'The input versions that stay fixed while the work runs'),
    'launch_instructions': Field('record', 'The launch instruction selection chosen for this assignment',
                                 required=False),
    'scientific_question': Field('record', "The parent's scientific question, shown for an ebi_hmmer request",
                                 required=False),
    'selected_tool_info': Field('record', "The parent's selected tool information, shown for an ebi_hmmer request",
                                required=False),
    'completion_target': Field('number', 'The credit one verified handoff earns: the commission is complete there'),
})


def read_from_parent(assignment, message):
    """The parent input: every assignment field (``None`` for an omitted optional one) and the message's values."""
    return {'version': assignment['version'], 'service': assignment['service'],
            'algorithm': assignment.get('algorithm'), 'database': assignment.get('database'),
            'resource_id': assignment['resource_id'], 'scope': assignment['scope'],
            'request': assignment['request'], 'input_refs': list(assignment['input_refs']),
            'immutable_input_versions': assignment['immutable_input_versions'],
            'launch_instructions': assignment.get('launch_instructions'),
            'scientific_question': assignment.get('scientific_question'),
            'selected_tool_info': assignment.get('selected_tool_info'),
            'completion_target': assignment['completion_target'],
            'initial_report': message['initial_report']}
