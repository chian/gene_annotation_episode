"""Validate A103 execution input identities against the assigned scope."""
from __future__ import annotations

import hashlib

from .communication import plain


def validate_execution_input_versions(execution, versions, scope, *, context):
    for supplied in versions:
        reference = supplied['reference']
        record = execution.store.get(reference)
        if not execution.store.reference_subset([reference], plain(scope)):
            raise ValueError('execution_input_outside_assigned_scope')
        if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
            raise ValueError('execution_input_version_conflict')
        if supplied['content_sha256'] is not None:
            artifact = (record['id'] if record['record_type'] == 'artifact' else
                record.get('sequence_ref', record.get('artifact_ref')))
            if artifact is None or hashlib.sha256(execution.store.get_artifact(artifact)).hexdigest() != supplied['content_sha256']:
                raise ValueError('execution_input_version_conflict')
