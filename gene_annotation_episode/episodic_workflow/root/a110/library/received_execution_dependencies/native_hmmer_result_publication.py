from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.materials import artifact_path

def _subject_chunks(store, reference, start=0, end=None, reverse=False):
    """Read actual Store sequence symbols with bounded windows, including features."""
    row = store.get(reference)
    length = store.subject_length(reference)
    end = length if end is None else end
    if not 0 <= start <= end <= length:
        raise ContractError('native_hmmer_subject_window_invalid')
    if row['record_type'] == 'feature':
        if row['strand'] == '-':
            start, end, reverse = (length - end, length - start, not reverse)
        segments, cursor = ([], 0)
        for segment in row['segments']:
            n = segment['end'] - segment['start']
            a, b = (max(start, cursor), min(end, cursor + n))
            if a < b:
                segments.append((segment['start'] + a - cursor, segment['start'] + b - cursor))
            cursor += n
        for a, b in reversed(segments) if reverse else segments:
            yield from _subject_chunks(store, row['subject_ref'], a, b, reverse)
        return
    path = artifact_path(store, row['sequence_ref']) if row.get('sequence_ref') else None
    if path is None and row['record_type'] != 'read_subject':
        raise ContractError('native_hmmer_subject_sequence_unavailable')
    import gene_annotation_episode.episodic_workflow.root.a110.materials_packing as materials_packing
    molecule = store.subject_molecule(reference)
    if reverse and molecule not in {'dna', 'rna'}:
        raise ContractError('native_hmmer_reverse_sequence_model_invalid')

    def read(a, b):
        if path is not None:
            with path.open('rb') as handle:
                handle.seek(a)
                return handle.read(b - a)
        return materials_packing.component_window(store, store.get(row['member_ref']), 'sequence', a, b - a)
    cursor = end if reverse else start
    while cursor > start if reverse else cursor < end:
        a, b = (max(start, cursor - 65536), cursor) if reverse else (cursor, min(end, cursor + 65536))
        chunk = read(a, b).decode('ascii').upper()
        if len(chunk) != b - a:
            raise ContractError('native_hmmer_subject_sequence_truncated')
        if reverse:
            chunk = chunk.translate(str.maketrans('ACGTRYSWKMBDHVNU', 'TGCAYRSWMKVHDBNA'))[::-1]
            if molecule == 'rna':
                chunk = chunk.replace('T', 'U')
        yield chunk.encode('ascii')
        cursor = a if reverse else b
