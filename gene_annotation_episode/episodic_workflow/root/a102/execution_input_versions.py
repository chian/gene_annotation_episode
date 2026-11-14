"""A102 validation of exact structure-execution input versions."""

import hashlib

from .communication import plain
from .protein_structure_authority import ProteinStructureOperandError
from .protein_structure_contracts import issue


def validate_execution_input_versions(owner, versions, scope, *, context):
    owner.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
    for supplied in versions:
        reference = supplied['reference']
        if owner._protein_reference_access(context, reference, None) is False:
            raise ProteinStructureOperandError(issue('original_commission_mismatch',
                stage='authority', field='receipt'))
        if not owner.store.reference_subset([reference], plain(scope)):
            raise ValueError('execution_input_outside_assigned_scope')
        record = owner.store.get(reference)
        if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
            raise ValueError('execution_input_version_conflict')
        expected = supplied['content_sha256']
        if expected is None:
            continue
        artifact = (record['id'] if record['record_type'] == 'artifact' else
            record.get('sequence_ref', record.get('artifact_ref')))
        if artifact is None or hashlib.sha256(owner.store.get_artifact(artifact)).hexdigest() != expected:
            raise ValueError('execution_input_version_conflict')
