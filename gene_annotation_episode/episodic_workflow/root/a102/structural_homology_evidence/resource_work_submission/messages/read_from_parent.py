"""What the commissioner supplies: the persisted ``resource_launch_assignment_v1`` (old ``from_parent.py``
``ResourceFromParent.assignment_schema`` = ``LAUNCH_SCHEMA``), one field per property of that schema under its old
name. This is the only place the assignment is read.

Old ``prepare_assignment`` kept the schema properties and validated them; it returned the assignment unchanged
(there is no adapter preparation at this level). ``resource_selection`` may be null in the old schema (no resource
chosen yet); a form has no null, so the field is optional here and ``read_from_parent`` gives the old ``None``.

New fields (the old code had them in the request message or in the old runner, not in the assignment):
``scope`` and ``scope_refs`` (the subject scope of the old request and the records it names, passed in custody),
``input_refs`` (the records of ``immutable_input_versions`` that the resource operations read),
``completion_target`` (the credit a usable execution handoff earns, which the completion controller needs) and
``adapter_assignment`` (optional: the existing immutable job assignment a local resource adapter prepared; the
local child's form requires it and this parent has no adapter preparation to make it)."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    LAUNCH_SCHEMA, LAUNCH_VERSION, _validate)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'job_request': Field('record', "The scientific parent's job, fixed"),
    'immutable_input_versions': Field('list', 'reference, version and content_sha256 of each input, fixed'),
    'constraints': Field('record', 'allowed_resource_ids, allowed_kinds, resource_id, kind; fixed'),
    'resource_selection': Field('record', 'The one chosen resource: resource_id, kind, allocation, '
                                'capability_binding_ref; omitted while no resource is chosen', required=False),
    'software_knowledge_refs': Field('list', 'Knowledge entries about the software, fixed'),
    'resource_knowledge_refs': Field('list', 'Knowledge entries about the resource, fixed'),
    'launch_instructions': Field('record', 'The pinned launch-instruction selection (library_id, sections)',
                                 required=False),
    'adapter_assignment': Field('record', 'The existing immutable job assignment a local resource adapter '
                                'prepared (a practical_assignment_v1); needed to commission the local child',
                                required=False),
    'scope': Field('record', 'The subject scope of the work (the old request scope)'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'input_refs': Field('record_refs', 'The records of the immutable input versions the resource operations '
                        'read, passed in custody'),
    'completion_target': Field('number', 'The credit a usable execution handoff earns'),
})

OLD_PROPERTIES = tuple(LAUNCH_SCHEMA['properties'])


def read_from_parent(assignment, message):
    launch = {name: assignment[name] for name in OLD_PROPERTIES if name in assignment}
    launch.setdefault('resource_selection', None)
    launch.setdefault('launch_instructions', None)
    launch = _validate(launch, LAUNCH_SCHEMA)
    return {'assignment': launch, 'adapter_assignment': assignment.get('adapter_assignment'),
            'scope': assignment['scope'], 'scope_refs': assignment['scope_refs'],
            'input_refs': assignment['input_refs'], 'completion_target': assignment['completion_target'],
            'message': message}
