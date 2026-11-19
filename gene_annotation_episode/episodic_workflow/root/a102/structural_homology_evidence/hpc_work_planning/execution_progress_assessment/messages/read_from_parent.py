"""What this monitor reads from its parent's assignment (carried from ``from_parent.py`` and ``contracts.py``).

The parent commissions one ``monitor_assignment_v1``: the one execution target to observe, the fields an
observation may request, the progress observations it already holds and the committed record types it permits
to be delivered. The runner admits the typed ``ASSIGNMENT_FORM``; ``admit_assignment`` then makes the old
semantic checks over the run's progress provider: the target is an execution handle inside the assigned scope
and every known progress observation is of that target.
"""
from __future__ import annotations

from copy import deepcopy

from episode_runtime import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    REF, RECORD_SCHEMAS, ContractError, obj, plain, validate_schema)

ASSIGNMENT_VERSION = 'monitor_assignment_v1'
FIELDS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
          'result_available')
STATES = ('pending', 'executing', 'returned', 'admitted')
REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
FIELDS_SCHEMA = {'type': 'array', 'items': {'enum': list(FIELDS)}, 'uniqueItems': True}
TEXT = {'type': 'string', 'minLength': 1}
ASSIGNMENT_SCHEMA = obj({'version': {'const': ASSIGNMENT_VERSION}, 'target_handle': TEXT,
                         'requested_fields': FIELDS_SCHEMA, 'known_progress_refs': REFS,
                         'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True,
                                                              'items': {'enum': sorted(RECORD_SCHEMAS)}}})

# The typed commission the runner admits: the scope it observes in and the monitor_assignment_v1 fields.
ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The subject scope fixed by the commissioning A102 parent'),
    'version': DeclaredField('text', 'The monitor assignment version', ASSIGNMENT_VERSION),
    'target_handle': Field('text', 'The execution handle whose progress is observed'),
    'requested_fields': Field('list', 'The progress fields an observation may request'),
    'known_progress_refs': Field('list', 'Progress observations the parent already holds (the information baseline)'),
    'permitted_committed_record_types': Field('list', 'Committed record types the parent permits to be delivered'),
})


def assignment_schema():
    """The JSON Schema of the monitor assignment (old ``assignment_schema`` hook)."""
    return deepcopy(ASSIGNMENT_SCHEMA)


def role_assignment(assignment):
    """The monitor_assignment_v1 record inside the admitted commission (everything but the scope)."""
    return {name: value for name, value in plain(assignment).items() if name != 'scope'}


def admit_assignment(progress, assignment, scope):
    """The admitted monitor assignment (old ``MonitorAssignment._assignment``).

    ``progress`` is the run's progress provider. ``reference_in_scope(target, scope, 'execution_handle')`` of the
    old services is the provider's own ``resolve``; ``read_progress`` reads a delivered observation in scope.
    """
    value = plain(assignment)
    validate_schema(value, ASSIGNMENT_SCHEMA)
    if not progress.resolve(value['target_handle'], plain(scope), 'execution_handle'):
        raise ContractError('progress_target_unavailable_or_outside_scope')
    for reference in value['known_progress_refs']:
        snapshot = progress.read_progress(reference, plain(scope))
        if snapshot['target_handle'] != value['target_handle']:
            raise ContractError('monitor_known_progress_target_mismatch')
    return value


def admitted_scope(store, scope):
    """The assignment's scope, which must be exactly the scope the run's Store admits."""
    value = plain(scope)
    if plain(store.validate_scope(value)) != value:
        raise ContractError('monitor_scope_must_be_store_admitted')
    return value
