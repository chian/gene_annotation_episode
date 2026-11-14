from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, parse_sequences

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
