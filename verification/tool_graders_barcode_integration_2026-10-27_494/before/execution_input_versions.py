"""Validate supplied execution identities within their original received scope.

Exact selected ATAC BAMs and expression matrices use authenticated Store metadata
here. Their bounded native drivers verify actual bytes before execution. Generic inputs keep
the existing byte-validation behavior. This helper grants no action or credit.
"""
from __future__ import annotations

import hashlib

from .communication import plain


def validate_execution_input_versions(owner, versions, scope, *, context, atac_assignments=(),
                                      nmf_assignments=()):
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
    for supplied in versions:
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
