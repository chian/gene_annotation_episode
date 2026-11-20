"""What the commissioner gives: the old ``resource_launch_assignment_v1`` and the records of the job's inputs.

Carried from the old ``from_parent.py`` (``OperationalAssignment``): ``assignment_schema`` (a copy of
``LAUNCH_SCHEMA``: one field per property, same names) and the admission part of ``prepare_assignment`` that read
only the child's own assignment (schema validation, the required non-null resource selection, the kind ``hpc``).
The comparison with the launch parent's own assignment (``resource_assignment_conflict``,
``resource_selection_conflict`` against the parent, ``launch_instruction_inheritance_conflict``) read the parent's
assignment and is not carried: the parent copies what it fixes into this assignment in its ``msg_to_child``. The
check that the selected resource has a declared capability of kind ``hpc`` that the constraints permit needs the
adapter's capabilities and is made in ``task.decide``. ``initial_references`` was ``[]``.

New field (not in the old schema): ``input_refs``, the records of the job's inputs, passed in custody."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    LAUNCH_SCHEMA, LAUNCH_VERSION, RESOURCE_ROLES, _validate)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'job_request': Field('record', "The scientific parent's job, fixed"),
    'immutable_input_versions': Field('list', 'The input versions (reference, version, content_sha256) the job '
                                      'uses, fixed'),
    'constraints': Field('record', 'Constraints the chosen resource must satisfy (allowed_resource_ids, '
                         'allowed_kinds, resource_id, kind)'),
    'resource_selection': Field('record', 'The one selected resource: resource_id, kind, allocation '
                                '(cpu, memory_bytes, scratch_bytes), capability_binding_ref'),
    'software_knowledge_refs': Field('list', 'Software knowledge entries, fixed'),
    'resource_knowledge_refs': Field('list', 'Resource knowledge entries, fixed'),
    'launch_instructions': Field('record', 'The pinned launch-instruction selection (library_id, sections)',
                                 required=False),
    'input_refs': Field('record_refs', "The records of the job's inputs, passed in custody"),
})


def read_from_parent(assignment, message):
    assignment = plain(assignment)
    launch = {name: assignment[name] for name in LAUNCH_SCHEMA['properties'] if name in assignment}
    launch.setdefault('launch_instructions', None)
    launch = _validate(launch, LAUNCH_SCHEMA)
    validate_selection(launch['launch_instructions'])
    selection = launch['resource_selection']
    if selection is None:
        raise ValueError('explicit_resource_selection_required')
    if selection['kind'] != RESOURCE_ROLES['launch_hpc']:
        raise ValueError('resource_selection_conflict')
    return {'assignment': launch, 'input_refs': list(assignment['input_refs']), 'message': plain(message)}
