"""What the commissioning parent supplies: the original handoff (named in custody) and the selector of the results
to acquire, an ``execution_results_assignment``. Each property of the old assignment schema
(``RESULTS_SCHEMA``: version, handoff_ref, selector) is a field under its old name.

New fields (listed in the carry-over record): ``service``. The old continuation read the service through the
original target behind the handoff (``job_progress_provider.targets.read_target(...)``, BLOCKED-ON-JOB-SERVICE),
and ``yield_controller`` is handed only the parent input, so the parent copies the service of the job it handed
off. ``handoff_ref`` is a ``record_refs`` field that holds exactly one reference (the old field was one text):
the handoff is passed in custody, and it is this episode's initial known record.

Carried from the old ``from_parent.py`` (``assignment_schema``, ``child_assignment_schema``, ``_api_context``
(results branch: exactly these three properties, the version)) and ``execution_contracts.py``
(``RESULTS_VERSION``, ``RESULTS_SCHEMA``, ``ROLES``). ``prepare_assignment`` read the original target through the
handoff and validated the selector against it (``api_execution.validate_result_selector``), and
``_recorded_results_assignment`` restored the assignment of an original Results commission; both are checks of a
commission or old-runner restoration and are not carried: a selector the service does not admit fails where the
service is asked. ``initial_references`` is the handoff (``parent_input['handoff_ref']``)."""
from method_loop import DeclaredField, Field, RecordForm

RESULTS_VERSION = 'execution_results_assignment'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', RESULTS_VERSION),
    'handoff_ref': Field('record_refs', 'The original handoff the results are acquired through (exactly one)'),
    'selector': Field('record', 'The selector naming which original results to acquire'),
    'service': Field('text', 'The API service of the original job, for the continuation profile'),
})


def read_from_parent(assignment, message):
    handoffs = assignment['handoff_ref']
    if len(handoffs) != 1:
        raise ValueError('execution_results_one_handoff_required')
    return {'version': assignment['version'], 'handoff_ref': handoffs[0], 'selector': assignment['selector'],
            'service': assignment['service'], 'message': message}
