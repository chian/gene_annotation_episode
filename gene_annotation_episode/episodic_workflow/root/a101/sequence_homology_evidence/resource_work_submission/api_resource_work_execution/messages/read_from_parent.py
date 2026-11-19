"""What the commissioning launch parent supplies: the persisted ``resource_launch_assignment_v1`` (old
``from_parent.py`` ``assignment_schema`` = ``LAUNCH_SCHEMA``), one field per property of that schema under its old
name, and the values the old request message carried beside it.

New fields (the old code had them in the request message or in the old runner, not in the assignment):
``scope`` and ``scope_refs`` (the subject scope of the old request, with the records it names, passed in custody),
``input_refs`` (the records of ``immutable_input_versions`` that the resource operations read) and
``completion_target`` (the credit a usable handoff earns, which the completion controller needs).

Not carried (a commission is never checked, README 3b C3): the equality of the fields with the launch parent's
own assignment (``resource_assignment_conflict``), the retention of the parent's pinned instruction sections
(``launch_instruction_inheritance_conflict``) and the equality of ``resource_selection`` with the parent's
(``resource_selection_conflict``): the parent copies its values into this assignment in ``msg_to_child``."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    LAUNCH_SCHEMA, RESOURCE_ROLES, _validate)

ASSIGNMENT_FORM = RecordForm({
    'version': Field('text', 'resource_launch_assignment_v1'),
    'job_request': Field('record', "The scientific parent's job, fixed"),
    'immutable_input_versions': Field('list', 'reference, version and content_sha256 of each input, fixed'),
    'constraints': Field('record', 'allowed_resource_ids, allowed_kinds, resource_id, kind; fixed'),
    'resource_selection': Field('record', 'The one chosen resource: resource_id, kind, allocation, '
                                'capability_binding_ref'),
    'software_knowledge_refs': Field('list', 'Knowledge entries about the software, fixed'),
    'resource_knowledge_refs': Field('list', 'Knowledge entries about the resource, fixed'),
    'launch_instructions': Field('record', 'The pinned launch-instruction selection (library_id, sections)',
                                 required=False),
    'scope': Field('record', 'The subject scope of the work (the old request scope)'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'input_refs': Field('record_refs', 'The records of the immutable input versions the resource operations read'),
    'completion_target': Field('number', 'The credit a usable execution handoff earns'),
})

OLD_PROPERTIES = tuple(LAUNCH_SCHEMA['properties'])


def read_from_parent(assignment, message):
    launch = {name: assignment[name] for name in OLD_PROPERTIES if name in assignment}
    launch.setdefault('launch_instructions', None)
    launch = _validate(launch, LAUNCH_SCHEMA)
    if launch['resource_selection'] is None:
        raise ValueError('explicit_resource_selection_required')
    if launch['resource_selection']['kind'] != RESOURCE_ROLES['launch_api']:
        raise ValueError('resource_selection_conflict')
    return {'assignment': launch, 'scope': assignment['scope'], 'scope_refs': assignment['scope_refs'],
            'input_refs': assignment['input_refs'], 'completion_target': assignment['completion_target'],
            'message': message}
