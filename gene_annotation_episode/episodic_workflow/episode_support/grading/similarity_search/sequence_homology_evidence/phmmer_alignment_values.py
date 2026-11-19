"""Original phmmer alignment geometry and measured-value assembly."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.phmmer_format import paired_segments

def alignment_geometry(row, sequence, symbols, qs, qe, rs, re):
    if not (0 <= qs < qe <= len(sequence) and 0 <= rs < re <= len(symbols)):
        raise ValueError('native_alignment_interval_outside_operand')
    intervals, paired, identical = paired_segments(row, sequence, symbols)
    return intervals, paired, identical


def alignment_measurement(row, reference, sequence, intervals, paired, identical):
    measured = {'kind': 'alignment', **row, 'paired_intervals': intervals, 'paired_residues': paired,
        'identical_paired_residues': identical, 'query_length': len(sequence),
        'reference_length': reference['length'], 'sequence_evalue': reference['sequence_evalue'],
        'sequence_bitscore': reference['sequence_bitscore']}
    return measured
