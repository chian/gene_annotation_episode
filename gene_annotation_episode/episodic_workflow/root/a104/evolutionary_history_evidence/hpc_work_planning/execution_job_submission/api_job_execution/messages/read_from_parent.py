"""What the commissioning ``execution_job_submission`` (the launch) gives this episode: one per-resource API request,
the records it names, the two operational credit units and the parent's scientific question.

Carried from the old ``from_parent.py`` (``assignment_schema`` -> ``ASSIGNMENT_FORM``; ``prepare_assignment``,
``_check_parent_inputs``, ``initial_references`` -> the form and ``input_refs``) and ``parent_request_contracts.py``.
The old assignment schema had two versions (``api_execution_assignment``, the EBI HMMER legacy request, and
``api_service_assignment``, whose ``request`` the actual service closes); the form carries every property of both
under the old names, and the properties of only one version are optional here. Nothing else is read from the
assignment anywhere in this episode: the yield estimator reads what this function returns."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': Field('text', "The assignment version: 'api_service_assignment' or 'api_execution_assignment'"),
    'resource_id': Field('text', 'The bound API resource this job runs on'),
    'service': Field('text', 'The service (ncbi_blast, bvbrc_appservice, bvbrc_data, ebi_hmmer, uniprot)'),
    'request': Field('record', "The service's own closed request (api_service_assignment)", required=False),
    'subject_ref': Field('text', 'The single protein query subject (api_execution_assignment, EBI HMMER)',
                         required=False),
    'algorithm': Field('text', 'The EBI HMMER algorithm: phmmer or hmmscan (api_execution_assignment)',
                       required=False),
    'database': Field('text', 'The EBI HMMER database (api_execution_assignment)', required=False),
    'parameters': Field('record', 'The EBI HMMER parameters (api_execution_assignment)', required=False),
    'page_size': Field('integer', 'The EBI HMMER page size (api_execution_assignment)', required=False),
    'endpoint': Field('text', "The requested endpoint: 'usable_handoff'"),
    'constraints': Field('record', "The launch's constraints on resource and kind"),
    'launch_instructions': Field('record', 'The launch instruction sections the launch selected', required=False),
    'input_refs': Field('record_refs', 'The records the request names (the query subject, masking and utility '
                                       'inputs), passed in custody'),
    'handoff_unit': Field('number', 'Operational credit for each new distinct handoff; also the commission target'),
    'acquired_record_unit': Field('number', 'Operational credit for each new distinct acquired result'),
})
_OWN = ('input_refs', 'handoff_unit', 'acquired_record_unit')


def read_from_parent(assignment, message):
    return {'assignment': {name: value for name, value in assignment.items() if name not in _OWN},
            'input_refs': list(assignment['input_refs']),
            'handoff_unit': assignment['handoff_unit'],
            'acquired_record_unit': assignment['acquired_record_unit'],
            'scientific_question': message['scientific_question'],
            'selected_tool_info': message['selected_tool_info']}
