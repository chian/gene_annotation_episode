"""The grading of a multiple sequence alignment of the target with reference sequences (``msa_alignment_sheet_v1``).

The aligned FASTA is read by the existing ``phylogeny_formats.parse_aligned_fasta`` (first whitespace token is the row's
name). Each row, with its gaps removed, must be the sequence that was given for it (``alignment_row_differs_from_input``
otherwise), the alignment must be rectangular and hold every given sequence once. Per reference sequence: the alignment
columns where both it and the target have a residue (``paired_columns``), how many of those are identical
(``identical_columns``; case-insensitive) and its value: ``identical_columns`` divided by the target's length (0 to 1).
The alignment's own facts: ``sequences``, ``columns`` and the target's row. Nothing here reads a file or a service."""
import hashlib

from gene_annotation_episode.episodic_workflow.episode_support.readers.phylogeny.phylogeny_formats import (
    parse_aligned_fasta)

SCHEMA = 'msa_alignment_sheet_v1'


def grade_alignment(aligned, *, given, target_name, aligner, alphabet, source_ref):
    """The sheet of the aligned FASTA ``aligned`` (bytes). ``given`` is the plan's rows, in the order given to the
    aligner: ``[{'name', 'sequence', 'candidate', 'accession', 'md5'}]`` for the references and the target's own
    ``{'name': target_name, 'sequence'}`` first."""
    parsed = parse_aligned_fasta(aligned, artifact={'raw_artifact_ref': source_ref, 'source_ref': source_ref,
                                                    'sha256': hashlib.sha256(aligned).hexdigest()},
                                 id_rule='first_whitespace_token')
    if parsed['status'] != 'ok':
        raise ValueError('alignment_unreadable:' + ','.join(item['code'] for item in parsed['diagnostics']))
    rows = {row['member_label']: row['sequence'] for row in parsed['value']['rows']}
    if len(rows) != len(parsed['value']['rows']) or set(rows) != {item['name'] for item in given}:
        raise ValueError('alignment_rows_differ_from_the_sequences_given')
    columns = parsed['value']['observed_column_count']
    for item in given:
        if rows[item['name']].replace('-', '').upper() != item['sequence'].upper():
            raise ValueError('alignment_row_differs_from_input:' + item['name'])
    target = rows[target_name]
    length = len(target.replace('-', ''))
    references = []
    for item in given:
        if item['name'] == target_name:
            continue
        row = rows[item['name']]
        paired = [(a, b) for a, b in zip(target, row) if a != '-' and b != '-']
        identical = sum(1 for a, b in paired if a.upper() == b.upper())
        references.append({'name': item['name'], 'candidate': item['candidate'], 'accession': item['accession'],
                           'aa_sequence_md5': item['md5'], 'length': len(item['sequence']),
                           'paired_columns': len(paired), 'identical_columns': identical, 'value': identical / length})
    return {'sheet': {'schema': SCHEMA, 'aligner': aligner, 'alphabet': alphabet,
                      'alignment': {'sequences': len(rows), 'columns': columns, 'target_row': [item['name'] for item in
                                    given].index(target_name), 'target_name': target_name, 'target_length': length},
                      'references': references}}


__all__ = ['SCHEMA', 'grade_alignment']
