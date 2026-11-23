"""The grading of a multiple sequence alignment of the target with reference sequences (``msa_alignment_sheet``).

The aligned FASTA is read by the existing ``phylogeny_formats.parse_aligned_fasta`` (first whitespace token is the row's
name). Each row, with its gaps removed, must be the sequence that was given for it (``alignment_row_differs_from_input``
otherwise), the alignment must be rectangular and hold every given sequence once. Per reference sequence: the alignment
columns where both it and the target have a residue (``paired_columns``), how many of those are identical
(``identical_columns``; case-insensitive) and its value: ``identical_columns`` divided by the target's length (0 to 1).
The alignment's own facts: ``sequences``, ``columns`` and the target's row.

The CONSERVED-SITE GRADING (``conserved_sites``, the owner's rule of 2026-11-21, from the alignment already read, no new job)
is the section the head's credit reads. The groups are the alignment's candidate groups (the reference sequences of each
product candidate; the target is in no group). A conserved site of a group is an alignment column where at least
``MINIMUM_SHARE`` of the group's sequences carry the same residue (not a gap), for a group of at least ``MINIMUM_GROUP_SIZE``
sequences. A distinguishing site is a conserved site of a group whose residue differs from the residue another group
conserves at the same column; each pair of groups at a column is recorded once (``pairs``) and each group's site once
(``sites``, with the groups it differs from). Every column maps to the target's residue position through the target's row; a
column where the target has a gap maps to no position and is recorded as ``target_gap`` (it is neither matched nor
mismatched). A site is identified by (target position, the group's conserved residue, the group's candidate), never by column
or job. Per candidate group: ``matched_sites`` are its distinguishing sites where the target carries the group's residue,
``mismatched_sites`` those where the target carries another residue. Nothing here reads a file or a service."""
import hashlib

from gene_annotation_episode.episodic_workflow.episode_support.readers.phylogeny.phylogeny_formats import (
    parse_aligned_fasta)

SCHEMA = 'msa_alignment_sheet'
# the owner accepted: at least 80% of the group's sequences share the residue, and the group has at least 3 sequences
MINIMUM_SHARE = 0.8
MINIMUM_GROUP_SIZE = 3


def conserved_sites(rows, groups, target_name):
    """The conserved-site grading of an alignment: ``rows`` is ``{row name: aligned sequence}``, ``groups`` is
    ``{candidate: [row names of its reference sequences]}``. Returns the section described at the top of this module:
    ``minimum_share``, ``minimum_group_size``, ``groups`` (each candidate with its ``size`` and ``conserved_count``;
    a group smaller than ``MINIMUM_GROUP_SIZE`` has none), ``sites`` (each distinguishing site of a group: ``column``
    (1-based), ``target_position`` (1-based, ``None`` at a target gap), ``target_gap``, ``target_residue``, ``candidate``,
    ``residue``, ``differs_from`` (the other candidates conserving another residue there), ``matched``), ``pairs`` (each
    pair of groups that conserve different residues at a column, once) and ``candidates`` (each candidate's
    ``matched_sites`` and ``mismatched_sites``)."""
    target = rows[target_name]
    positions, position = [], 0
    for residue in target:
        if residue != '-':
            position += 1
        positions.append(None if residue == '-' else position)
    conserved = {}
    for candidate, names in groups.items():
        if len(names) < MINIMUM_GROUP_SIZE:
            continue
        for column in range(len(target)):
            counts = {}
            for name in names:
                residue = rows[name][column].upper()
                if residue != '-':
                    counts[residue] = counts.get(residue, 0) + 1
            for residue, count in counts.items():
                if count / len(names) >= MINIMUM_SHARE:
                    conserved[candidate, column] = residue
    sites, pairs = [], []
    for (candidate, column), residue in conserved.items():
        others = [other for other in groups if other != candidate and (other, column) in conserved
                  and conserved[other, column] != residue]
        if others:
            carried = target[column].upper()
            sites.append({'column': column + 1, 'target_position': positions[column], 'target_gap': carried == '-',
                          'target_residue': None if carried == '-' else carried, 'candidate': candidate,
                          'residue': residue, 'differs_from': others, 'matched': None if carried == '-' else carried == residue})
    order = list(groups)
    for column in range(len(target)):
        for first in order:
            for second in order[order.index(first) + 1:]:
                if (first, column) in conserved and (second, column) in conserved and conserved[first, column] != conserved[second, column]:
                    pairs.append({'column': column + 1, 'target_position': positions[column],
                                  'first': {'candidate': first, 'residue': conserved[first, column]},
                                  'second': {'candidate': second, 'residue': conserved[second, column]}})
    sites.sort(key=lambda site: (site['column'], order.index(site['candidate'])))
    return {'minimum_share': MINIMUM_SHARE, 'minimum_group_size': MINIMUM_GROUP_SIZE,
            'groups': [{'candidate': candidate, 'size': len(names),
                        'conserved_count': sum(1 for key in conserved if key[0] == candidate)}
                       for candidate, names in groups.items()],
            'sites': sites, 'pairs': pairs,
            'candidates': [{'candidate': candidate,
                            'matched_sites': sum(1 for site in sites if site['candidate'] == candidate and site['matched']),
                            'mismatched_sites': sum(1 for site in sites if site['candidate'] == candidate
                                                    and site['matched'] is False)}
                           for candidate in groups]}


def grade_alignment(aligned, *, given, target_name, aligner, alphabet, source_ref):
    """The sheet of the aligned FASTA ``aligned`` (bytes). ``given`` is the plan's rows: the target's own
    ``{'name': target_name, 'sequence'}`` and the references ``{'name', 'candidate', 'accession', 'md5'}`` (a reference
    row, gaps removed, must have the MD5 of its hit's protein sequence, BV-BRC's ``aa_sequence_md5``) or with a
    ``sequence`` the row must equal."""
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
        ungapped = rows[item['name']].replace('-', '').upper()
        if 'sequence' in item:
            if ungapped != item['sequence'].upper():
                raise ValueError('alignment_row_differs_from_input:' + item['name'])
        elif hashlib.md5(ungapped.encode('ascii')).hexdigest() != item['md5']:
            raise ValueError('alignment_row_differs_from_the_hit_md5:' + item['name'])
        item.setdefault('length', len(ungapped))
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
                           'aa_sequence_md5': item['md5'], 'length': item['length'],
                           'paired_columns': len(paired), 'identical_columns': identical, 'value': identical / length})
    groups = {}
    for item in given:
        if item['name'] != target_name:
            groups.setdefault(item['candidate'], []).append(item['name'])
    return {'sheet': {'schema': SCHEMA, 'aligner': aligner, 'alphabet': alphabet,
                      'alignment': {'sequences': len(rows), 'columns': columns, 'target_row': [item['name'] for item in
                                    given].index(target_name), 'target_name': target_name, 'target_length': length},
                      'references': references, 'conserved_sites': conserved_sites(rows, groups, target_name)}}


__all__ = ['MINIMUM_GROUP_SIZE', 'MINIMUM_SHARE', 'SCHEMA', 'conserved_sites', 'grade_alignment']
