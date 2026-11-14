"""Ordinary BLAST/Rfam protocols and read-only historical provider job records.

HMMER execution belongs to bounded API episode operations.
"""
from __future__ import annotations
import hashlib
from gene_annotation_episode.episodic_workflow.root.a110.acquisition import AcquisitionError
HMMER_IDENTITY_VERSION = 'hmmer_single_fasta_sequence_v2'

def request_identity_feedback(request: dict) -> dict:
    if request.get('provider', 'hmmer') == 'hmmer' and request.get('identity_version') != HMMER_IDENTITY_VERSION:
        return {'identity_compatibility': 'unsupported_historical_hmmer_request', 'stored_identity_version': request.get('identity_version'), 'supported_identity_version': HMMER_IDENTITY_VERSION}
    return {}

def require_hmmer_identity_version(request: dict) -> None:
    feedback = request_identity_feedback(request)
    if feedback:
        raise AcquisitionError('hmmer_request_identity_version_unsupported', phase='local_request_identity', operational=feedback)

def validate_remote_identity(native: dict, request: dict, remote_id: str, *, result: bool=False) -> None:
    """Check present source identities, without requiring undocumented fields."""
    import uuid
    require_hmmer_identity_version(request)
    checks = {'id': remote_id, 'algo': request['algorithm'], 'database': request['database']}
    result_body = native.get('result')
    if result and (not isinstance(result_body, dict)):
        raise AcquisitionError('provider_result_representation')
    fields = result_body.get('stats', {}) if result else native
    if not isinstance(fields, dict):
        raise AcquisitionError('provider_result_representation')
    for key, expected in checks.items():
        actual = fields.get(key)
        if isinstance(actual, dict) and key == 'database':
            actual = actual.get('id')
        if actual is None:
            continue
        if key == 'id':
            try:
                actual = str(uuid.UUID(actual))
            except (ValueError, TypeError, AttributeError):
                pass
        if actual != expected:
            raise AcquisitionError('remote_identity_conflict_' + key)
    if not result and isinstance(native.get('input'), str) and ('sequence_sha256' in request):
        from gene_annotation_episode.episodic_workflow.root.a110.domain import parse_sequences
        try:
            sequences = parse_sequences(native['input'], format='fasta' if native['input'].lstrip().startswith('>') else 'raw', molecule='protein')
        except ValueError as error:
            raise AcquisitionError('remote_identity_conflict_input') from error
        if len(sequences) != 1 or hashlib.sha256(sequences[0].sequence.encode()).hexdigest() != request['sequence_sha256']:
            raise AcquisitionError('remote_identity_conflict_input')
