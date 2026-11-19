"""What the parent gives: the resource launch assignment for the selected local resource (the old
``resource_launch_assignment_v1``: one field per property of the old ``LAUNCH_SCHEMA``, under the same names), the
job assignment the selected resource adapter prepared from it, the scope and the records the job names.

This is the only place the assignment is read. The old ``prepare_assignment`` of this episode checked the
commissioning launch request against its parent (every inherited field equal to the parent's, the pinned launch
instruction sections retained, the resource selection unchanged and permitted by the constraints) and asked the
selected adapter to prepare the job assignment. Those are checks of a commission (a wrong commission fails) and the
old runner's parent lookups: they are not carried. What this episode needs from the commission is checked here
because it raises on what it cannot use: the job assignment must be a valid ``practical_assignment_v1`` of resource
kind ``local`` for the selected resource, and the credit its requirements declare must be reachable."""
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'resource_launch_assignment_v1'),
    'job_request': Field('record', "The scientific parent's job request, preserved unchanged"),
    'immutable_input_versions': Field('list', 'The input versions of the job: reference, version, content digest'),
    'constraints': Field('record', "The commissioner's constraints (allowed resource ids and kinds, allocation)"),
    'resource_selection': Field('record', 'The selected local resource: resource_id, kind local, allocation and '
                                          'capability_binding_ref (old value: null before a selection; this '
                                          'episode requires one)'),
    'software_knowledge_refs': Field('list', 'The software knowledge entries the job refers to'),
    'resource_knowledge_refs': Field('list', 'The resource knowledge entries the job refers to'),
    'launch_instructions': Field('record', 'The exact launch instruction sections selected for this job '
                                           '(entry_id, section_id, sha256 per section)', required=False),
    # New fields the final form needs (the old code read them from the commissioning request and the adapter).
    'adapter_assignment': Field('record', 'The immutable job assignment the selected local resource adapter '
                                          'prepared (old adapter.prepare_assignment): a practical_assignment_v1'),
    'scope': Field('record', 'The subject scope fixed by the commissioning parent (old message scope)'),
    'record_refs': Field('record_refs', 'Every record the job inputs name, passed in custody', required=False),
})

LAUNCH_FIELDS = ('version', 'job_request', 'immutable_input_versions', 'constraints', 'resource_selection',
                 'software_knowledge_refs', 'resource_knowledge_refs', 'launch_instructions')


def read_from_parent(assignment, message):
    """The launch assignment, the validated job assignment, the scope and the completion target as the parent
    input. The target is the credit the commissioned requirements can earn: the sum of the credits of every
    original requirement, which the practical credit (the sum of the satisfied ones) cannot pass."""
    selection = assignment['resource_selection']
    if selection['kind'] != 'local':
        raise ValueError('explicit_local_resource_selection_required')
    practical = validate_assignment(assignment['adapter_assignment'])
    if practical['resource_id'] != selection['resource_id']:
        raise ValueError('resource_selection_conflict')
    requirements = practical['progress_requirements']
    credited = {item['key'] for item in requirements if item['credit'] > 0}
    outside = sorted(credited - set(practical['completion_keys']))
    if outside:
        raise ValueError('local_resource_credited_requirement_outside_completion_keys:' + ','.join(outside))
    target = math.fsum(item['credit'] for item in requirements)
    if not target > 0:
        raise ValueError('local_resource_completion_target_must_be_positive')
    launch = {name: assignment[name] for name in LAUNCH_FIELDS if name in assignment}
    return {'launch': launch, 'assignment': practical, 'scope': assignment['scope'], 'completion_target': target,
            'record_refs': list(assignment.get('record_refs', []))}
