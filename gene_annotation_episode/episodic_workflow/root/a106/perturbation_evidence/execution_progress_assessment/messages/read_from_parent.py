"""What the A106 monitor reads from its parent's assignment (carried from ``from_parent.py`` and ``contracts.py``).

The parent fills ``ASSIGNMENT_FORM``: the subject scope and the ``monitor_assignment_v1`` fields. ``read_from_parent``
is the one place the assignment is read: it admits the ``monitor_assignment_v1`` schema (the old ``_assignment``
schema step) and returns the parent input. The two other steps of the old ``_assignment`` need something this
function is not handed: the target being in scope as an ``execution_handle`` needs the job-access service (it is
made in ``task.decide``). Every known progress reference passed with its snapshot belonging to the target is made
here; the old provider read of a reference passed without a snapshot has no object any more (``credit`` raises
where it is needed).
"""
from __future__ import annotations

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.perturbation_evidence.progress_provider import FIELDS
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    REF, RECORD_SCHEMAS, ContractError, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain

ASSIGNMENT_VERSION = 'monitor_assignment_v1'
REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
REQUESTED_FIELDS = {'type': 'array', 'items': {'enum': list(FIELDS)}, 'uniqueItems': True}
_TEXT = {'type': 'string', 'minLength': 1}
ASSIGNMENT_SCHEMA = obj({'version': {'const': ASSIGNMENT_VERSION}, 'target_handle': _TEXT,
                         'requested_fields': REQUESTED_FIELDS, 'known_progress_refs': REFS,
                         'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True,
                                                              'items': {'enum': sorted(RECORD_SCHEMAS)}}})

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The subject scope fixed by the commissioning parent'),
    'version': DeclaredField('text', 'The monitor assignment version', ASSIGNMENT_VERSION),
    'target_handle': Field('text', 'The execution handle whose progress is observed'),
    'requested_fields': Field('list', 'The progress fields requested from each observation: a subset of '
                                      + ', '.join(FIELDS)),
    'known_progress_refs': Field('list', 'Progress observations of this target the parent already holds'),
    'permitted_committed_record_types': Field('list', 'Committed record types the parent permits to be exposed'),
    'information_unit': Field('number', 'The credit of one newly informative progress observation (positive)'),
    'known_progress_snapshots': Field('record', 'The snapshots of known_progress_refs by reference, as the parent '
                                                'received them', required=False),
})


def read_from_parent(assignment, message):
    """The parent input: the admitted ``monitor_assignment_v1`` fields, the scope and the information unit."""
    value = {name: plain(assignment[name]) for name in ('version', 'target_handle', 'requested_fields',
                                                       'known_progress_refs', 'permitted_committed_record_types')}
    validate_schema(value, ASSIGNMENT_SCHEMA)
    unit = assignment['information_unit']
    if unit <= 0:
        raise ContractError('explicit_positive_monitoring_information_unit_required')
    snapshots = plain(assignment.get('known_progress_snapshots', {}))
    for reference in value['known_progress_refs']:
        if reference in snapshots and snapshots[reference]['target_handle'] != value['target_handle']:
            raise ContractError('monitor_known_progress_target_mismatch')
    return {**value, 'scope': plain(assignment['scope']), 'information_unit': unit,
            'known_progress_snapshots': snapshots, 'launch_instructions': plain(message).get('launch_instructions')}
