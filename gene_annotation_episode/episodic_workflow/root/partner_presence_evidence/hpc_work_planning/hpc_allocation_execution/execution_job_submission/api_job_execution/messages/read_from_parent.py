"""What the commissioning parent (the job submission) supplies: one assigned API job, either an
``api_execution_assignment`` (service ebi_hmmer, subject_ref, algorithm, database, parameters, page_size) or an
``api_service_assignment`` (service, request, endpoint, constraints). Each property of the old assignment
schema is a field under its old name (the old ``from_parent.py`` took them from the validated api execution
assignment schema of the configured resource). Two fields are new: ``completion_target`` (the credit a verified
handoff earns, which the completion controller needs from the commission) and ``input_refs`` (the records the
service operations read, passed in custody).

``read_from_parent`` is the only place the assignment is read. It checks the assignment against the axis's own
assignment contract (the old ``_validate_request``)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.execution_contracts import (
    validate_api_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': Field('text', 'api_execution_assignment or api_service_assignment'),
    'resource_id': Field('text', 'The bound API resource the work runs on'),
    'service': Field('text', 'The API service'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff'),
    'constraints': Field('record', 'The parent constraints, kept fixed'),
    'launch_instructions': Field('record', 'The selected launch instruction sections', required=False),
    'subject_ref': Field('text', 'The subject record of an api_execution_assignment', required=False),
    'algorithm': Field('text', 'The search algorithm of an api_execution_assignment', required=False),
    'database': Field('text', 'The search database of an api_execution_assignment', required=False),
    'parameters': Field('record', 'The service parameters of an api_execution_assignment', required=False),
    'page_size': Field('integer', 'The result page size of an api_execution_assignment', required=False),
    'request': Field('record', 'The exact service request of an api_service_assignment', required=False),
    'completion_target': Field('number', 'The credit a verified original handoff earns'),
    'input_refs': Field('record_refs', 'The records the service operations read, passed in custody',
                        required=False),
})

ASSIGNMENT_PROPERTIES = ('version', 'resource_id', 'service', 'endpoint', 'constraints', 'launch_instructions',
                  'subject_ref', 'algorithm', 'database', 'parameters', 'page_size', 'request')


def read_from_parent(assignment, message):
    original = {name: assignment[name] for name in ASSIGNMENT_PROPERTIES if name in assignment}
    validate_api_assignment(original)
    return {**original, 'completion_target': assignment['completion_target'],
            'input_refs': assignment.get('input_refs', []), 'message': message}
