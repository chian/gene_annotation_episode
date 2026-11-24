"""What the commissioning parent gives: the one authorised HPC job (the practical assignment of its launch request)
and, in custody, the records the job's inputs are read from. The only place an assignment is read."""
from method_loop import ChoiceField, DeclaredField, Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The practical assignment contract version', 'practical_assignment'),
    'assignment_id': Field('text', 'Identity of the assignment'),
    'resource_kind': DeclaredField('text', 'The resource kind this episode executes on: an HPC resource', 'hpc'),
    'workspace': Field('text', 'Absolute path the commands are confined to on the resource'),
    'endpoint': ChoiceField('text', 'The commissioned endpoint', ('usable_handoff', 'completed_job_outputs')),
    'requested_job': Field('record', 'The requested job: generic argv and environment, or one native family'),
    'progress_requirements': Field('list', 'The original requirements, each with a key, a credit and a predicate'),
    'completion_keys': Field('list', 'The requirement keys whose satisfaction completes the endpoint'),
    'initial_context': Field('record', 'The working directory and environment the first command starts in'),
    'inventory_snapshot': Field('record', 'The recorded inventory of the resource (context, not proof of usability)'),
    'constraints': Field('record', 'The caller constraints on the work'),
    'launch_instructions': Field('record', 'The launch instruction sections the parent selected', required=False),
    'resource_id': Field('text', 'The configured resource the job runs on'),
    'scientific_manifest': Field('record', 'The scientific run plan of a native BLAST database job', required=False),
    'input_refs': Field('record_refs', 'The records the job inputs are read from, passed in custody', required=False),
})


def read_from_parent(assignment, message):
    """The parent input: the practical assignment as the old code read it, and the input records passed."""
    return {'assignment': {name: value for name, value in assignment.items() if name != 'input_refs'},
            'input_refs': list(assignment.get('input_refs', []))}
