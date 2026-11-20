"""What the commissioning launch parent gives: where the job runs, its query in custody, the parameters of the
service's request the parent fixed, and the credit the handoff earns.

Every field is controlled data: ids, record references, a number, and ``fixed_request``, whose names are parameters
of the service's request form and whose values ``task.action`` holds the built request to. The old assignment
(``api_execution_assignment_v1`` / ``api_service_assignment_v1``: ``version``, ``service``, ``algorithm``,
``database``, ``resource_id``, and the parent launch's ``requests`` re-read through the old runner) reaches this
form as: ``service`` and ``resource_id`` under the same names; the request's sequence subject as
``query_subject_refs`` (the old code read it from the Store by reference); its program (old ``algorithm``),
database and hit-list size, where the parent fixed them, in ``fixed_request``. ``completion_target`` is the
parent's ``handoff_unit``. Not carried: ``version`` (it only decided whether the old ``wait`` action was offered),
``scope`` and ``immutable_input_versions`` (custody passes the records), the ``initial_report`` message and the
``ebi_hmmer`` task fields (``scientific_question``, ``selected_tool_info``: no route to that service is bound).

This is the only place the assignment is read."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'resource_id': Field('text', 'The resource of the job service the job is submitted on (a bound API route)'),
    'service': Field('text', 'The public web service of that resource, by its name'),
    'query_subject_refs': Field('record_refs', 'The one sequence subject that is the query of the job'),
    'input_refs': Field('record_refs', "The records the query is read from: the subject's sequence artifact"),
    'fixed_request': Field('record', "The parameters of the service's request the parent fixed, by parameter "
                                     'name (empty when it fixed none); the rest is built in this episode'),
    'launch_instructions': Field('record', 'The launch instruction sections the parent selected for this job',
                                 required=False),
    'completion_target': Field('number', 'The credit the established handoff earns: the commission is complete '
                                         'there'),
})


def read_from_parent(assignment, message):
    query, = assignment['query_subject_refs']
    return {'resource_id': assignment['resource_id'], 'service': assignment['service'], 'query_subject_ref': query,
            'fixed_request': dict(assignment['fixed_request']),
            'launch_instructions': assignment.get('launch_instructions'),
            'completion_target': assignment['completion_target']}
