"""What the commissioning parent (the job submission) gives (carried from ``from_parent.py``).

Old assignment properties, each a field under its old name: ``version`` (``api_execution_assignment`` or
``api_service_assignment``), ``resource_id``, ``service``, ``endpoint``, ``constraints``, ``launch_instructions``
and, per version, ``subject_ref``, ``algorithm``, ``database``, ``parameters``, ``page_size`` (the first version) or
``request`` (the second). The old ``prepare_assignment`` validated the request (``validate_api_assignment``, in the
library) and, against the parent's own launch assignment, the BLAST selection, masking and utility inputs, the
immutable input versions and the native/standard BLAST job inputs: those are checks of this episode's commission
against its parent and are not carried (rule 1: a wrong commission fails). What the child read from the parent's
assignment is a field here, which the parent copies into this assignment: ``immutable_input_versions``,
``scientific_question`` and ``selected_tool_info`` (old ``services.scientific_parent_task``). Fields the old code
did not have: ``scope`` (old ``context.scope``), ``input_refs`` (the records the service operations read, passed in
custody) and ``completion_target`` (the credit one verified handoff earns).
"""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.execution_contracts import (
    validate_api_assignment)

VERSIONS = ('api_execution_assignment', 'api_service_assignment')

ASSIGNMENT_FORM = RecordForm({
    'version': ChoiceField('text', 'The assignment version; the service-job version permits waiting', VERSIONS),
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
    'immutable_input_versions': Field('record', 'The input versions that stay fixed while the work runs'),
    'scientific_question': Field('text', "The parent's scientific question", required=False),
    'selected_tool_info': Field('list', "The parent's selected tool information (name, resources, description, "
                                "instructions)", required=False),
    'scope': Field('record', 'The subject scope fixed by the commissioning parent'),
    'input_refs': Field('record_refs', 'The records the service operations read, passed in custody'),
    'completion_target': Field('number', 'The credit one verified original handoff earns'),
})

ASSIGNMENT_PROPERTIES = ('version', 'resource_id', 'service', 'endpoint', 'constraints', 'launch_instructions',
                  'subject_ref', 'algorithm', 'database', 'parameters', 'page_size', 'request')


def read_from_parent(assignment, message):
    """The parent input: the old assignment properties that were given, the fields the child read from its parent,
    the new fields and the commission's message."""
    original = {name: assignment[name] for name in ASSIGNMENT_PROPERTIES if name in assignment}
    validate_api_assignment(original)
    return {**original, 'immutable_input_versions': assignment['immutable_input_versions'],
            'scientific_question': assignment.get('scientific_question'),
            'selected_tool_info': assignment.get('selected_tool_info'), 'scope': assignment['scope'],
            'input_refs': list(assignment['input_refs']), 'completion_target': assignment['completion_target'],
            'message': message}
