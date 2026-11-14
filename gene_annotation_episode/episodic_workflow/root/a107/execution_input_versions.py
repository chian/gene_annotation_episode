"""Validate A107 execution identities and received expression-matrix custody."""

import hashlib

from .communication import plain


def validate_execution_input_versions(binding, versions, scope, *, context, nmf_assignments=()):
    binding.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
    selected_files = {}
    failure_prefixes = {}
    for assignment in nmf_assignments:
        job = assignment.get('requested_job', {}).get('native_expression_nmf')
        if job is None:
            continue
        admitted = binding._expression_nmf_inputs(context, assignment)
        binding.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        file = job['input']
        if file['artifact_ref'] not in admitted:
            raise ValueError('expression_nmf_input_not_received')
        selected_files[file['artifact_ref']] = file
        failure_prefixes[file['artifact_ref']] = 'expression_nmf'
    for supplied in versions:
        if (getattr(binding, "native_expression_nmf_results", None) is not None
                and binding._expression_nmf_reference_access(context, supplied["reference"], None) is False):
            raise ValueError("expression_nmf_input_protected_reference_denied")
        record = binding.store.get(supplied['reference'])
        if not binding.store.reference_subset([supplied['reference']], plain(scope)):
            selected = selected_files.get(supplied['reference'])
            if selected is None or record['record_type'] != 'artifact':
                raise ValueError('execution_input_outside_assigned_scope')
            from .native_file_capture import _metadata
            metadata = _metadata(binding.store, supplied['reference'])
            if metadata['sha256'] != selected['sha256'] or metadata['size'] != selected['size_bytes']:
                raise ValueError(failure_prefixes[supplied['reference']] + '_input_artifact_metadata_mismatch')
        if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
            raise ValueError('execution_input_version_conflict')
        if supplied['content_sha256'] is not None:
            selected = selected_files.get(supplied['reference'])
            if selected is not None and record['record_type'] == 'artifact':
                from .native_file_capture import _metadata
                metadata = _metadata(binding.store, supplied['reference'])
                if metadata['sha256'] != selected['sha256'] or metadata['size'] != selected['size_bytes']:
                    raise ValueError(failure_prefixes[supplied['reference']] + '_input_artifact_metadata_mismatch')
                if metadata['sha256'] != supplied['content_sha256']:
                    raise ValueError('execution_input_version_conflict')
            else:
                artifact = (record['id'] if record['record_type'] == 'artifact' else
                    record.get('sequence_ref', record.get('artifact_ref')))
                if artifact is None or hashlib.sha256(binding.store.get_artifact(artifact)).hexdigest() != supplied['content_sha256']:
                    raise ValueError('execution_input_version_conflict')
