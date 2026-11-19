"""What the commissioner gives: the old ``resource_launch_assignment_v1`` (carried from ``from_parent.py``,
``OperationalAssignment.assignment_schema``, ``prepare_assignment`` and ``execution_contracts.py``) and the values the
old episode obtained from its runner.

``ASSIGNMENT_FORM`` has one field per property of the old ``LAUNCH_SCHEMA``, under the same name: ``version``,
``job_request``, ``immutable_input_versions``, ``constraints``, ``resource_selection``, ``software_knowledge_refs``,
``resource_knowledge_refs`` and ``launch_instructions``. A form has no null: ``resource_selection`` (null while the
commissioner leaves the choice of resource to this episode) and ``launch_instructions`` (null when nothing is
pinned) are omitted for null.

New fields (listed in the carry-over record as ``new field``): ``scope`` (the old request scope: the reasoning commit
names it and the API and local children are commissioned within it), ``scope_refs`` (the records the scope names,
passed in custody), ``input_refs`` (the records of ``immutable_input_versions`` that the resource operations read,
passed in custody) and ``completion_target`` (the credit one usable execution handoff earns: the API child takes it
as its own completion target and ``credit.py`` counts handoffs in this unit).

This is the only place the assignment is read. The schema validation and the checks of ``prepare_assignment`` that read
only this episode's own assignment are carried (schema, pinned instruction selection, explicit positive credit
unit). The old comparison of the assignment with a ``launch`` parent's own assignment (``resource_assignment_conflict``,
``resource_selection_conflict``, ``launch_instruction_inheritance_conflict``) read the parent's assignment, which
this episode cannot read; the commissioner states what it fixes in this assignment."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    LAUNCH_SCHEMA, LAUNCH_VERSION, _validate)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'job_request': Field('record', "The scientific parent's job, fixed"),
    'immutable_input_versions': Field('list', 'The input versions (reference, version, content_sha256) the job '
                                      'uses, fixed'),
    'constraints': Field('record', 'Constraints the chosen resource must satisfy: allowed_resource_ids, '
                         'allowed_kinds, resource_id and kind, each optional'),
    'resource_selection': Field('record', 'The one resource the commissioner already selected (resource_id, kind, '
                                'allocation, capability_binding_ref); omitted when this episode chooses',
                                required=False),
    'software_knowledge_refs': Field('list', 'Software knowledge entries, fixed'),
    'resource_knowledge_refs': Field('list', 'Resource knowledge entries, fixed'),
    'launch_instructions': Field('record', 'The pinned launch-instruction selection (library_id, sections)',
                                 required=False),
    'scope': Field('record', 'The subject scope of the work (the old request scope)'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'input_refs': Field('record_refs', 'The records of the immutable input versions that the resource operations '
                        'read, passed in custody'),
    'completion_target': Field('number', 'The credit one usable execution handoff earns'),
})


def read_from_parent(assignment, message):
    assignment = plain(assignment)
    launch = {name: assignment[name] for name in LAUNCH_SCHEMA['properties'] if name in assignment}
    launch.setdefault('resource_selection', None)
    launch.setdefault('launch_instructions', None)
    launch = _validate(launch, LAUNCH_SCHEMA)
    launch['launch_instructions'] = validate_selection(launch['launch_instructions'])
    if not assignment['completion_target'] > 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    return {'assignment': launch, 'scope': assignment['scope'], 'scope_refs': list(assignment['scope_refs']),
            'input_refs': list(assignment['input_refs']), 'completion_target': assignment['completion_target'],
            'message': plain(message)}
