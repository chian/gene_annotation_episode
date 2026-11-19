"""What the parent gives: the one practical HPC job assignment (``practical_assignment_v1``) to run.

The form has one field per property of the old assignment schema. ``read_from_parent`` is the only place the
assignment is read: it admits the assignment with the library's closed practical-assignment contract and
requires the HPC resource kind."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import validate_assignment

ASSIGNMENT_FORM = RecordForm({
    'version': Field('text', 'The assignment contract version: practical_assignment_v1'),
    'assignment_id': Field('text', 'The identity of the assigned job'),
    'resource_kind': Field('text', 'The kind of the assigned resource: hpc'),
    'workspace': Field('text', 'The absolute workspace of the job on the resource'),
    'endpoint': Field('text', 'The endpoint to validate: usable_handoff or completed_job_outputs'),
    'requested_job': Field('record', 'The requested job: argv and environment, or a native job request'),
    'progress_requirements': Field('list', 'The original requirements: key, credit and predicate of each'),
    'completion_keys': Field('list', 'The requirement keys whose satisfaction completes the assignment'),
    'initial_context': Field('record', 'The working context at revision zero: cwd and environment'),
    'inventory_snapshot': Field('record', 'The inventory snapshot supplied with the assignment'),
    'constraints': Field('record', 'The scheduler constraints of the assignment'),
    'launch_instructions': Field('record', 'The launch instruction sections selected for the job', required=False),
    'resource_id': Field('text', 'The configured resource the job is assigned to'),
    'scientific_manifest': Field('record', 'The native database run plan the job executes', required=False),
})


def read_from_parent(assignment, message):
    admitted = validate_assignment(dict(assignment))
    if admitted['resource_kind'] != 'hpc':
        raise ValueError('execution_resource_kind_conflict')
    return admitted
