"""What the commissioning parent (the job submission) supplies: one assigned API job, an
``api_service_assignment_v1`` (resource_id, service, request, endpoint, constraints, launch_instructions). Each
property of the old assignment schema is a field under its old name. Two fields are new: ``completion_target``
(the credit a verified handoff earns, which the completion controller needs from the commission) and
``input_refs`` (the records the service operations read, passed in custody).

Carried from the old ``from_parent.py`` (``assignment_schema``, ``_validate_request``). The old
``prepare_assignment`` checks of the commission against the parent's own launch assignment (``_launch``,
``_permitted``, ``_constraints``, ``_versions``, the role test) are checks of a commission and are not carried."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.execution_contracts import (
    validate_api_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': Field('text', 'api_service_assignment_v1'),
    'resource_id': Field('text', 'The bound API resource the work runs on'),
    'service': Field('text', 'The API service'),
    'request': Field('record', 'The exact service request'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff'),
    'constraints': Field('record', 'The parent constraints, kept fixed'),
    'launch_instructions': Field('record', 'The selected launch instruction sections', required=False),
    'completion_target': Field('number', 'The credit a verified original handoff earns'),
    'input_refs': Field('record_refs', 'The records the service operations read, passed in custody',
                        required=False),
})

OLD_PROPERTIES = ('version', 'resource_id', 'service', 'request', 'endpoint', 'constraints', 'launch_instructions')


def read_from_parent(assignment, message):
    original = {name: assignment[name] for name in OLD_PROPERTIES if name in assignment}
    validate_api_assignment(original)
    return {**original, 'completion_target': assignment['completion_target'],
            'input_refs': assignment.get('input_refs', []), 'message': message}
