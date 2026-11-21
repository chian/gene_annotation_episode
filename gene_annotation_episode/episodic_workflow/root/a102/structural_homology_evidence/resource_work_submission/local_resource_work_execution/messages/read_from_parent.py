"""What the parent gives: the selected local resource, the work to launch and what a handoff is worth. This is the
only place the assignment is read.

Controlled messaging: the work is not written into the assignment. It is a record the commissioner holds (a JSON
artifact ``{"command": [argv...], "environment": {name: value}, "inputs": {file name: reference}}``) and passes by
reference in ``work_refs``; the artifacts it stages as input files are passed in ``input_refs``. The launch tool
reads the record through custody and hands it to the library's one execution point for local resources. The other
fields are an identifier of the run's job services and two numbers."""
from method_loop import DeclaredField, Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'resource_launch_assignment_v1'),
    'resource_id': Field('text', "The selected local resource: a resource id of the run's job services"),
    'work_refs': Field('record_refs', 'One record: the work to launch, a JSON artifact with command, environment '
                                      'and inputs, held by the commissioner'),
    'input_refs': Field('record_refs', 'The artifacts the work stages as its input files, passed in custody'),
    'handoff_unit': Field('number', 'The credit of holding the handoff record of the launched work'),
    'check_unit': Field('number', 'The credit of holding a receiving check that found the launched job in a known '
                                  'state'),
})


def read_from_parent(assignment, message):
    """The parent input. The completion target is what the commission can earn: the handoff and its check."""
    return {'resource_id': assignment['resource_id'], 'work_ref': assignment['work_refs'][0],
            'input_refs': list(assignment['input_refs']),
            'credit_units': {'handoff': assignment['handoff_unit'], 'usable_check': assignment['check_unit']},
            'completion_target': assignment['handoff_unit'] + assignment['check_unit']}
