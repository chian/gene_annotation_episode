from pathlib import Path
import json
from Bio import SeqIO
from Bio.Align import PairwiseAligner, substitution_matrices
run_dir = Path('/lus/flare/projects/BioReason-Aurora-Test/chian/runs/gene-annotation-aurora-20261022T151552Z')
query = SeqIO.read(run_dir / 'target.faa', 'fasta')
references = list(SeqIO.parse(run_dir / 'reported-references.faa', 'fasta'))
if not query.seq or not references:
    raise ValueError('A nonempty query and at least one reference are required')
if any(not reference.seq for reference in references):
    raise ValueError('Empty reference sequence')
aligner = PairwiseAligner(mode='global',
    substitution_matrix=substitution_matrices.load('BLOSUM62'),
    open_gap_score=-10, extend_gap_score=-0.5)
rows = [{'reference_id': reference.id, 'query_length': len(query),
         'reference_length': len(reference),
         'alignment_score': float(aligner.score(str(query.seq), str(reference.seq)))}
        for reference in references]
rows.sort(key=lambda row: (-row['alignment_score'], row['reference_id']))
output = {'query_id': query.id, 'reference_count': len(references),
    'method': {'algorithm': 'pairwise alignment', 'mode': 'global',
        'substitution_matrix': 'BLOSUM62', 'open_gap_score': -10,
        'extend_gap_score': -0.5}, 'comparisons': rows}
(run_dir / 'alignment_scores.json').write_text(
    json.dumps(output, indent=2, allow_nan=False) + '\n')
print(json.dumps({'reference_count': len(rows), 'top_matches': rows[:3]}))
