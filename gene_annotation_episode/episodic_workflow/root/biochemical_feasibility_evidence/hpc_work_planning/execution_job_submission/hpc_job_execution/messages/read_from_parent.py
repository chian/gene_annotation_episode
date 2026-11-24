"""What the parent gives: one practical assignment for one configured HPC resource (the old
``practical_assignment`` of ``execution_job_submission``'s launch request).

This is the only place the assignment is read. ``read_from_parent`` admits it as the old ``prepare_assignment``
did (the practical assignment contract, the resource kind) and returns the parent input: the assignment, the
validations of its initial context (the baseline the credit counts from), the class of the request (the key of
the yield profile) and the credit the commissioned requirements add up to (the completion target)."""
import math

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    assess_validations, validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': Field('text', 'The assignment contract version (practical_assignment)'),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_kind': Field('text', 'The kind of resource the job runs on (hpc)'),
    'workspace': Field('text', 'The absolute workspace on the resource every command stays inside'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'requested_job': Field('record', 'The requested job: its argv and environment'),
    'progress_requirements': Field('list', 'The requirements (key, credit, predicate) whose satisfaction earns credit'),
    'completion_keys': Field('list', 'The requirement keys whose satisfaction completes the assignment'),
    'initial_context': Field('record', 'The working directory and environment the work starts from (revision 0)'),
    'inventory_snapshot': Field('record', 'Historical resource inventory: context, not proof of present usability'),
    'constraints': Field('record', 'The caller constraints (account, queue, resources, allocation)'),
    'launch_instructions': Field('record', 'The exact launch instruction sections the launching parent selected',
                                 required=False),
    'resource_id': Field('text', 'The configured resource this assignment is for'),
    'native_flux_balance_execution': Field('record', 'The flux balance execution environment selection',
                                           required=False),
})

# The fixed time of the baseline validations: a pure function of the assignment, the same on every call.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'


def request_yield_class(request):
    """The class of the original execution request (the old ``_request_yield_class``, practical form)."""
    native = sorted(key for key in request['requested_job'] if key.startswith('native_'))
    parts = ['practical', request['resource_kind'], *native,
             {'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']]]
    return '_'.join(parts)


def read_from_parent(assignment, message):
    request = validate_assignment(dict(assignment))
    if request['resource_kind'] != 'hpc':
        raise ValueError('execution_resource_assignment_mismatch')
    initial = assess_validations(request, {'facts': {}}, request['initial_context'], checked_at=BASELINE_CHECKED_AT)
    return {'assignment': request, 'initial_validations': initial, 'yield_class': request_yield_class(request),
            'credit_target': math.fsum(item['credit'] for item in request['progress_requirements'])}
