"""The Foldseek server's result for one database, parsed into controlled hit rows.

Input: the parsed JSON of ``GET /api/result/{ticket}/0`` of a search made with ``mode=tmalign`` (the structure file as
the query). Output: ``{'database', 'mode', 'query_sequence', 'hits'}``; one row per hit, in the server's order (rank 1
first). A malformed result raises ``ValueError`` (no fallback, nothing repaired).

What the server reports, kept as reported (names say so with ``_as_reported``):

* ``score_as_reported`` and ``eval_as_reported``. The Foldseek README
  (https://github.com/steineggerlab/foldseek, read 2026-11-21) says: "If alignment type is set to tmalign
  (``--alignment-type 1``), the results will be sorted by the TMscore normalized by query length. The TMscore is used for
  reporting two fields: the e-value=(qTMscore+tTMscore)/2 and the score=(qTMscore*100). All output fields (e.g., pident,
  fident, and alnlen) are calculated based on the TMalign alignment." So, in ``tmalign`` mode only, ``score_as_reported``
  is the query-normalised TM-score x 100 and ``eval_as_reported`` is the mean of the query- and target-normalised
  TM-scores. They are NOT an e-value or a bit score. ``prob`` and ``seq_id`` are as reported (``seqId`` is a percent).
* The aligned residue pairs come from ``qAln`` and ``dbAln`` (``-`` is a gap): a column where neither side is a gap is a
  pair (query residue, target residue), both 1-based, counted from ``qStartPos`` and ``dbStartPos``. The aligned letters
  are checked against the query sequence and the hit's ``tSeq`` (a mismatch raises).
* ``tCa`` is the comma-separated list ``x,y,z,x,y,z,...``. Finding (data of 2026-11-21, direct check: afdb-swissprot, 976
  hits of the CspA model, and pdb100, 548 hits): it covers the WHOLE target chain, not only the aligned span. In every
  hit ``len(tCa)/3 == len(tSeq) == dbLen``, also in the 863 + 530 hits with ``dbStartPos > 1`` or ``dbEndPos < dbLen``
  (for example ``AF-P36995-F1-model_v6``: 71 residues in ``tCa``, ``dbLen`` 71, aligned 1 to 70; pdb100
  ``3i2z-assembly3.cif.gz_A``: 71, 71, aligned 2 to 71). So residue ``i`` (1-based) of the target has the coordinate
  ``tCa[3(i-1) : 3i]``, and each aligned pair takes the coordinate of its own target residue. The coordinates are in the
  target's own frame, not superposed on the query.
"""
import re

HIT_KEYS = ('query', 'target', 'seqId', 'alnLength', 'missmatches', 'gapsopened', 'qStartPos', 'qEndPos', 'dbStartPos',
            'dbEndPos', 'prob', 'eval', 'score', 'qLen', 'dbLen', 'qAln', 'dbAln', 'tCa', 'tSeq', 'taxId', 'taxName')
# ``AF-<UniProt accession>[-<isoform number>]-F<fragment>-model_v<version> <description>``: the accession is that of the
# UniProt ENTRY (an isoform's structure, ``AF-Q41188-2-F1-model_v6``, belongs to the entry Q41188; 32 of the 976 hits of the
# CspA search of afdb-swissprot are isoforms)
ALPHAFOLD_TARGET = re.compile(r'^AF-([A-Z0-9]+)(?:-(\d+))?-F(\d+)-model_v(\d+)$')


def _require(condition, code):
    if not condition:
        raise ValueError('foldseek_result_' + code)


def _number(value, name):
    _require(type(value) in (int, float) and value == value and abs(value) != float('inf'), 'number_required:' + name)
    return value


def _integer(value, name):
    _require(type(value) is int, 'integer_required:' + name)
    return value


def target_name(target):
    """``(target_id, description, accession)`` of the server's ``target`` string: the id is the text before the first
    space, the description the rest (``None`` when there is none); ``accession`` is the UniProt accession of an
    AlphaFold database target (``AF-<accession>-F1-model_v6 ...``, or ``AF-<accession>-<isoform>-F1-model_v6 ...``: the
    entry's accession) and ``None`` for any other target."""
    _require(type(target) is str and target, 'target_required')
    identifier, _, description = target.partition(' ')
    found = ALPHAFOLD_TARGET.match(identifier)
    return identifier, description or None, found.group(1) if found else None


def aligned_pairs(q_aln, db_aln, q_start, db_start):
    """``[(query residue, target residue)]``, 1-based, for the columns of the alignment where neither side is a gap."""
    _require(type(q_aln) is str and type(db_aln) is str and len(q_aln) == len(db_aln), 'alignment_strings_differ')
    q, t, pairs = q_start, db_start, []
    for a, b in zip(q_aln, db_aln):
        if a != '-' and b != '-':
            pairs.append((q, t))
        q += a != '-'
        t += b != '-'
    return pairs


def _coordinates(text, length):
    values = text.split(',')
    _require(len(values) == 3 * length, 'tca_does_not_cover_the_target_chain')
    try:
        numbers = [float(value) for value in values]
    except ValueError as error:
        raise ValueError('foldseek_result_tca_not_numeric') from error
    _require(all(n == n and abs(n) != float('inf') for n in numbers), 'tca_not_finite')
    return [tuple(numbers[3 * i:3 * i + 3]) for i in range(length)]


def _hit(rank, row, query_sequence):
    _require(isinstance(row, dict) and set(row) == set(HIT_KEYS), 'hit_keys:' + str(rank))
    identifier, description, accession = target_name(row['target'])
    q_start, q_end, db_start, db_end = (_integer(row[k], k) for k in ('qStartPos', 'qEndPos', 'dbStartPos', 'dbEndPos'))
    q_len, db_len = _integer(row['qLen'], 'qLen'), _integer(row['dbLen'], 'dbLen')
    _require(1 <= q_start <= q_end <= q_len == len(query_sequence) and 1 <= db_start <= db_end <= db_len, 'span:' + identifier)
    _require(type(row['tSeq']) is str and len(row['tSeq']) == db_len, 'tseq_length:' + identifier)
    coordinates = _coordinates(row['tCa'], db_len)
    pairs = aligned_pairs(row['qAln'], row['dbAln'], q_start, db_start)
    q_letters, t_letters = row['qAln'].replace('-', ''), row['dbAln'].replace('-', '')
    _require(q_letters == query_sequence[q_start - 1:q_end] and len(q_letters) == q_end - q_start + 1
             and t_letters == row['tSeq'][db_start - 1:db_end], 'aligned_letters_differ:' + identifier)
    return {'rank': rank, 'target': row['target'], 'target_id': identifier, 'description': description,
            'accession': accession, 'seq_id': _number(row['seqId'], 'seqId'), 'prob': _number(row['prob'], 'prob'),
            'score_as_reported': _number(row['score'], 'score'), 'eval_as_reported': _number(row['eval'], 'eval'),
            'aln_length': _integer(row['alnLength'], 'alnLength'), 'q_start': q_start, 'q_end': q_end,
            'db_start': db_start, 'db_end': db_end, 'query_length': q_len, 'target_length': db_len,
            'q_aln': row['qAln'], 'db_aln': row['dbAln'], 'tax_id': row['taxId'], 'tax_name': row['taxName'],
            'pairs': [{'query': q, 'target': t, 'target_xyz': coordinates[t - 1]} for q, t in pairs]}


def parse_foldseek_result(result, database):
    """The hits of ``database`` in the parsed result JSON ``result`` of a ``tmalign`` search, as
    ``{'database', 'mode', 'query_sequence', 'hits'}`` (one row per hit, rank 1 first; the row keys are those of
    ``_hit``: ``rank``, ``target`` (raw), ``target_id``, ``description``, ``accession``, ``seq_id``, ``prob``,
    ``score_as_reported``, ``eval_as_reported``, ``aln_length``, the aligned span, both lengths, both alignment
    strings, ``tax_id``, ``tax_name`` and ``pairs``: ``{'query', 'target', 'target_xyz'}`` per aligned pair). A result
    that is not one tmalign search of one query with ``database`` in it raises."""
    _require(isinstance(result, dict) and result.get('type') == 'structuresearch', 'type')
    _require(result.get('mode') == 'tmalign', 'mode_is_not_tmalign')
    _require(isinstance(result.get('queries'), list) and len(result['queries']) == 1, 'one_query_required')
    query_sequence = result['queries'][0]['sequence']
    _require(type(query_sequence) is str and query_sequence, 'query_sequence')
    found = [entry for entry in result.get('results', ()) if entry.get('db') == database]
    _require(len(found) == 1, 'database_not_in_result:' + str(database))
    alignments = found[0]['alignments']
    _require(isinstance(alignments, list) and len(alignments) == 1 and isinstance(alignments[0], list), 'alignments_shape')
    return {'database': database, 'mode': 'tmalign', 'query_sequence': query_sequence,
            'hits': [_hit(rank, row, query_sequence) for rank, row in enumerate(alignments[0], 1)]}


__all__ = ['parse_foldseek_result', 'aligned_pairs', 'target_name', 'HIT_KEYS']
