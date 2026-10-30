"""Validate supplied execution identities within their original received scope.

Exact selected ATAC BAMs, expression matrices and FBA witnesses use
authenticated Store metadata here. Their bounded native drivers verify actual
bytes before execution. Generic inputs keep the existing byte-validation
behavior. This helper grants no action or credit.
"""
from __future__ import annotations

import hashlib

from .communication import plain


def _flux_balance_witnesses(owner, versions, scope, context, assignments):
    """Select only records authenticated by the existing FBA input binding."""
    selected = {}
    for assignment in assignments:
        if assignment.get('requested_job', {}).get('native_flux_balance') is None:
            continue
        from .episode_return_records import EpisodeReturnRecords
        from .execution_contracts import digest
        frozen = None
        if (context.role == 'launch_local'
                and (EpisodeReturnRecords._equal(plain(context.assignment), plain(assignment))
                    or callable(getattr(owner, '_matches_flux_balance_assignment', None))
                    and owner._matches_flux_balance_assignment(context, plain(assignment)))):
            frozen = owner.flux_balance_inputs.received(context, required=False)
        if frozen is None:
            binding = owner.flux_balance_inputs.validate_selected(context, assignment,
                input_versions=versions)
            records = None
        else:
            binding = frozen['receipt']['binding']
            records = {row['reference']: row['record'] for row in frozen['receipt']['witness_records']}
        receiving_scope = owner.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        if not EpisodeReturnRecords._equal(binding['scope'], receiving_scope):
            raise ValueError('flux_balance_input_scope_conflict')
        if not EpisodeReturnRecords._equal(binding['input_versions'], plain(versions)):
            raise ValueError('flux_balance_input_version_conflict')
        for row in [binding['model'], *binding['prior_sources']]:
            for witness in row['witnesses']:
                reference = witness['reference']
                version = witness['input_version']
                if (version['reference'] != reference or version not in binding['input_versions']):
                    raise ValueError('flux_balance_input_witness_selection_conflict')
                record = owner.store.get(reference) if records is None else records[reference]
                if digest(record) != witness['record_sha256']:
                    raise ValueError('flux_balance_input_witness_record_conflict')
                previous = selected.get(reference)
                if previous is not None and (not EpisodeReturnRecords._equal(previous[0], record)
                        or not EpisodeReturnRecords._equal(previous[1], version)):
                    raise ValueError('flux_balance_input_witness_record_conflict')
                selected[reference] = (record, version, records is not None)
    return selected


def _check_flux_balance_version(owner, supplied, witness, index):
    from .flux_balance_operands import _check_version
    from .episode_return_records import EpisodeReturnRecords
    if not EpisodeReturnRecords._equal(supplied, witness[1]):
        raise ValueError('flux_balance_input_version_conflict')
    _check_version(owner.store, witness[0], supplied, '/input_versions/' + str(index))


def validate_execution_input_versions(owner, versions, scope, *, context, atac_assignments=(),
                                      nmf_assignments=(), fluorescence_assignments=(),
                                      flux_balance_assignments=()):
    # Only exact selected BAMs already admitted through original receipt
    # inheritance may use bare artifact custody. Generic artifacts retain
    # their ordinary Store scope requirement.
    selected_files = {}
    failure_prefixes = {}
    for assignment in atac_assignments:
        admitted = owner._atac_inputs(context, assignment)
        job = assignment.get('requested_job', {}).get('native_atac_differential')
        if job is None:
            continue
        owner.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        for occurrence in job['request']['inputs']:
            file = occurrence['file']
            if file['artifact_ref'] not in admitted:
                raise ValueError('atac_input_not_received')
            selected_files[file['artifact_ref']] = file
            failure_prefixes[file['artifact_ref']] = 'atac'
    for assignment in nmf_assignments:
        job = assignment.get('requested_job', {}).get('native_expression_nmf')
        if job is None:
            continue
        admitted = owner._expression_nmf_inputs(context, assignment)
        owner.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        file = job['input']
        if file['artifact_ref'] not in admitted:
            raise ValueError('expression_nmf_input_not_received')
        selected_files[file['artifact_ref']] = file
        failure_prefixes[file['artifact_ref']] = 'expression_nmf'
    for assignment in fluorescence_assignments:
        job = assignment.get('requested_job', {}).get('native_fluorescence')
        if job is None:
            continue
        admitted = owner._fluorescence_inputs(context, assignment)
        owner.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        files = [row['source']['file'] for row in job['inputs']]
        files.extend(row['file'] for row in job['support_inputs'])
        files.extend(row['file'] for row in job.get('report_inputs', []))
        for file in files:
            if file['artifact_ref'] not in admitted:
                raise ValueError('fluorescence_input_not_received')
            selected_files[file['artifact_ref']] = file
            failure_prefixes[file['artifact_ref']] = 'fluorescence'
    flux_balance_witnesses = _flux_balance_witnesses(owner, versions, scope, context,
        flux_balance_assignments)
    for index, supplied in enumerate(versions):
        witness = flux_balance_witnesses.get(supplied['reference'])
        if witness is not None and witness[2]:
            # The host authenticated original admission, frozen witnesses and
            # permission controls. Current source aliases cannot replace them.
            _check_flux_balance_version(owner, supplied, witness, index)
            continue
        if (getattr(owner, 'native_flux_balance_results', None) is not None
                and owner._flux_balance_reference_access(context, supplied['reference'], None) is False):
            raise ValueError('flux_balance_input_protected_reference_denied')
        if (getattr(owner, 'native_fluorescence_results', None) is not None
                and owner._fluorescence_reference_access(context, supplied['reference'], None) is False):
            raise ValueError('fluorescence_input_protected_reference_denied')
        if (getattr(owner, 'native_expression_nmf_results', None) is not None
                and owner._expression_nmf_reference_access(context, supplied['reference'], None) is False):
            raise ValueError('expression_nmf_input_protected_reference_denied')
        if owner._atac_reference_access(context, supplied['reference'], None) is False:
            raise ValueError('atac_input_protected_reference_denied')
        if owner._chromatin_reference_access(context, supplied['reference'], None) is False:
            raise ValueError('chromatin_input_protected_reference_denied')
        if owner._protein_reference_access(context, supplied['reference'], None) is False:
            from .protein_structure_authority import ProteinStructureOperandError
            from .protein_structure_contracts import issue
            raise ProteinStructureOperandError(issue('original_commission_mismatch',
                stage='authority', field='receipt'))
        if witness is not None:
            _check_flux_balance_version(owner, supplied, witness, index)
            continue
        record = owner.store.get(supplied['reference'])
        if not owner.store.reference_subset([supplied['reference']], plain(scope)):
            selected = selected_files.get(supplied['reference'])
            if selected is None or record['record_type'] != 'artifact':
                raise ValueError('execution_input_outside_assigned_scope')
            from .native_file_capture import _metadata
            metadata = _metadata(owner.store, supplied['reference'])
            if metadata['sha256'] != selected['sha256'] or metadata['size'] != selected['size_bytes']:
                raise ValueError(failure_prefixes[supplied['reference']] + '_input_artifact_metadata_mismatch')
        if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
            raise ValueError('execution_input_version_conflict')
        if supplied['content_sha256'] is not None:
            selected = selected_files.get(supplied['reference'])
            if selected is not None and record['record_type'] == 'artifact':
                from .native_file_capture import _metadata
                metadata = _metadata(owner.store, supplied['reference'])
                if metadata['sha256'] != selected['sha256'] or metadata['size'] != selected['size_bytes']:
                    raise ValueError(failure_prefixes[supplied['reference']] + '_input_artifact_metadata_mismatch')
                if metadata['sha256'] != supplied['content_sha256']:
                    raise ValueError('execution_input_version_conflict')
            else:
                artifact = (record['id'] if record['record_type'] == 'artifact' else
                    record.get('sequence_ref', record.get('artifact_ref')))
                if artifact is None or hashlib.sha256(owner.store.get_artifact(artifact)).hexdigest() != supplied['content_sha256']:
                    raise ValueError('execution_input_version_conflict')
