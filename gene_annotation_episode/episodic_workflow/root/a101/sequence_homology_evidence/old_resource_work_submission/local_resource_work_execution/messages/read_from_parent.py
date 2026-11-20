"""What the launch parent gives: the resource launch assignment, with the one local resource it selected.

``ASSIGNMENT_FORM`` has one field per property of the old ``LAUNCH_SCHEMA`` (old ``from_parent.py``
``assignment_schema``), under the same name. The old schema allowed a null ``launch_instructions``; the form has no
null type, so that field is omitted when there is none. ``resource_selection`` is required (the old
``explicit_resource_selection_required``) and its ``kind`` is declared ``local`` (the old ``RESOURCE_ROLES``
check). The subject ``scope`` and the parent's ``initial_report`` are fields of the commission's message, as in the
old request message."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    LAUNCH_VERSION, RESOURCE_ROLES)

SELECTION_FORM = RecordForm({
    'resource_id': Field('text', 'The one actual local resource this episode works on'),
    'kind': DeclaredField('text', 'The kind of the selected resource', RESOURCE_ROLES['launch_local']),
    'allocation': Field('record', 'The allocation: cpu, memory_bytes and scratch_bytes, each an integer or null'),
    'capability_binding_ref': Field('text', 'The execution registry the selected capability is bound to'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'job_request': Field('record', "The scientific parent's job (fixed)"),
    'immutable_input_versions': Field('list', 'reference, version and content_sha256 of each input (fixed)'),
    'constraints': Field('record', 'May hold allowed_resource_ids, allowed_kinds, resource_id and kind (fixed)'),
    'resource_selection': Field('record', 'The selected resource and its allocation', form=SELECTION_FORM),
    'software_knowledge_refs': Field('list', 'Software knowledge entries (fixed)'),
    'resource_knowledge_refs': Field('list', 'Resource knowledge entries (fixed)'),
    'launch_instructions': Field('record', 'The pinned launch-instruction selection (library_id and sections)',
                                 required=False),
})


def _permitted(assignment):
    """The old ``_permitted``: the selection satisfies the constraints (the selection is the capability's own
    ``resource_id`` and ``kind``)."""
    constraints, selection = assignment['constraints'], assignment['resource_selection']
    return (('allowed_resource_ids' not in constraints or selection['resource_id'] in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or selection['kind'] in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or selection['resource_id'] == constraints['resource_id'])
            and ('kind' not in constraints or selection['kind'] == constraints['kind']))


def read_from_parent(assignment, message):
    if not _permitted(assignment):
        raise ValueError('resource_selection_conflict')
    return {**assignment, 'scope': message['scope'],
            'initial_report': message['initial_report'] if 'initial_report' in message else None}
