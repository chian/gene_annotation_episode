"""What the A102 monitor reads from its parent's assignment (carried from ``from_parent.py`` and ``contracts.py``).

The parent fills ``ASSIGNMENT_FORM``: the subject scope and the ``monitor_assignment_v1`` fields. ``admit`` is
the old ``MonitorAssignment._assignment``: the assignment's schema, its target inside the scope as an
``execution_handle`` and every known progress reference on that target.
"""
from __future__ import annotations

from episode_runtime import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.structural_homology_evidence.progress_provider import FIELDS
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    REF, RECORD_SCHEMAS, ContractError, obj, plain, validate_schema)

VERSION = 'monitor_episode_binding_v1'
ASSIGNMENT_VERSION = 'monitor_assignment_v1'
STATES = ('pending', 'executing', 'returned', 'admitted')
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
})


def monitor_assignment(assignment):
    """The ``monitor_assignment_v1`` record inside the admitted commission (everything but ``scope``)."""
    return {name: value for name, value in plain(assignment).items() if name != 'scope'}


def admit(provider, assignment, scope):
    """The old ``_assignment``: schema, target in scope, known progress on that target."""
    value = monitor_assignment(assignment)
    validate_schema(value, ASSIGNMENT_SCHEMA)
    if not provider.resolve(value['target_handle'], plain(scope), 'execution_handle'):
        raise ContractError('progress_target_unavailable_or_outside_scope')
    for reference in value['known_progress_refs']:
        if provider.read_progress(reference, plain(scope))['target_handle'] != value['target_handle']:
            raise ContractError('monitor_known_progress_target_mismatch')
    return value


def store_scope(store, scope):
    """The assignment's scope, exactly as the run's Store admits it."""
    value = plain(scope)
    if plain(store.validate_scope(value)) != value:
        raise ContractError('monitor_scope_must_be_store_admitted')
    return value


__all__ = ['ASSIGNMENT_FORM', 'ASSIGNMENT_SCHEMA', 'ASSIGNMENT_VERSION', 'REFS', 'REQUESTED_FIELDS', 'STATES',
           'VERSION', 'admit', 'monitor_assignment', 'store_scope']
