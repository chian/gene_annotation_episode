"""Pure, occurrence-preserving readers for selected ``blastdbcmd`` sequences.

The fixed native format is ``%o	%i	%a	%l	%s``. The existing sequence
parser owns alphabet interpretation. This supporting reader adds no scientific
score, acquisition, file access or native invocation.
"""
from __future__ import annotations
import hashlib
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, parse_sequences

def _failure(stage, code, occurrence_id=None, record_key=None, line_number=None, native_returncode=None):
    return {'stage': stage, 'code': code, 'occurrence_id': occurrence_id, 'record_key': record_key, 'line_number': line_number, 'native_returncode': native_returncode}

def _check(name, status, subjects, method, evidence, reason=None):
    return {'name': name, 'status': status, 'subject_refs': list(dict.fromkeys(subjects)), 'method': method, 'reason': reason, 'evidence_occurrence_ids': list(dict.fromkeys(evidence))}

def _check_bytes(content, occurrence):
    if type(content) is not bytes:
        raise ContractError('blast_utility_bytes_required')
    if len(content) != occurrence['size_bytes'] or hashlib.sha256(content).hexdigest() != occurrence['sha256']:
        raise ContractError('blast_utility_input_identity_mismatch')
    return _check('custody', 'pass', [occurrence['occurrence_id']], 'identity_digest', [occurrence['occurrence_id']])

def normalize_blast_utility_sequence_symbols(original: str, molecule: str) -> tuple[str, int | None]:
    """Use the established alphabet parser, retaining invalid source symbols."""
    normalized = original.upper()
    if not original or any((c.isspace() for c in original)):
        return (normalized, None)
    try:
        parsed = parse_sequences(original, format='raw', molecule=molecule)[0]
    except ContractError:
        return (normalized, None)
    if 'unexpected_symbol_for_declared_molecule' in parsed.issues:
        return (normalized, None)
    return (parsed.sequence, len(parsed.sequence))
