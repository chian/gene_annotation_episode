"""Authenticate A110 flux balance inputs and ordinary scoped execution inputs."""
from __future__ import annotations

import hashlib

from .communication import plain
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import digest
from .flux_balance_operands import _check_version


def _flux_balance_witnesses(execution, versions, scope, context, assignments):
    selected = {}
    for assignment in assignments:
        if assignment.get('requested_job', {}).get('native_flux_balance') is None:
            continue
        frozen = None
        if (context.role == 'launch_local'
                and (EpisodeReturnRecords._equal(plain(context.assignment), plain(assignment))
                    or execution._matches_flux_balance_assignment(context, plain(assignment)))):
            frozen = execution.flux_balance_inputs.received(context, required=False)
        if frozen is None:
            binding = execution.flux_balance_inputs.validate_selected(
                context, assignment, input_versions=versions)
            records = None
        else:
            binding = frozen['receipt']['binding']
            records = {row['reference']: row['record'] for row in frozen['receipt']['witness_records']}
        receiving_scope = execution.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        if not EpisodeReturnRecords._equal(binding['scope'], receiving_scope):
            raise ValueError('flux_balance_input_scope_conflict')
        if not EpisodeReturnRecords._equal(binding['input_versions'], plain(versions)):
            raise ValueError('flux_balance_input_version_conflict')
        for row in [binding['model'], *binding['prior_sources']]:
            for witness in row['witnesses']:
                reference = witness['reference']
                version = witness['input_version']
                if version['reference'] != reference or version not in binding['input_versions']:
                    raise ValueError('flux_balance_input_witness_selection_conflict')
                record = execution.store.get(reference) if records is None else records[reference]
                if digest(record) != witness['record_sha256']:
                    raise ValueError('flux_balance_input_witness_record_conflict')
                previous = selected.get(reference)
                if previous is not None and (not EpisodeReturnRecords._equal(previous[0], record)
                        or not EpisodeReturnRecords._equal(previous[1], version)):
                    raise ValueError('flux_balance_input_witness_record_conflict')
                selected[reference] = (record, version, records is not None)
    return selected


def validate_execution_input_versions(execution, versions, scope, *, context, flux_balance_assignments=()):
    witnesses = _flux_balance_witnesses(execution, versions, scope, context, flux_balance_assignments)
    for index, supplied in enumerate(versions):
        witness = witnesses.get(supplied['reference'])
        if witness is not None and witness[2]:
            _check_version(execution.store, witness[0], supplied, '/input_versions/' + str(index))
            continue
        if (execution.native_flux_balance_results is not None
                and execution._flux_balance_reference_access(context, supplied['reference'], None) is False):
            raise ValueError('flux_balance_input_protected_reference_denied')
        if witness is not None:
            if not EpisodeReturnRecords._equal(supplied, witness[1]):
                raise ValueError('flux_balance_input_version_conflict')
            _check_version(execution.store, witness[0], supplied, '/input_versions/' + str(index))
            continue
        record = execution.store.get(supplied['reference'])
        if not execution.store.reference_subset([supplied['reference']], plain(scope)):
            raise ValueError('execution_input_outside_assigned_scope')
        if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
            raise ValueError('execution_input_version_conflict')
        if supplied['content_sha256'] is not None:
            artifact = (record['id'] if record['record_type'] == 'artifact' else
                record.get('sequence_ref', record.get('artifact_ref')))
            if artifact is None or hashlib.sha256(execution.store.get_artifact(artifact)).hexdigest() != supplied['content_sha256']:
                raise ValueError('execution_input_version_conflict')
