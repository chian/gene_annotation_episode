"""The grader and the sheet of A102's ``rna_structure_agreement``: can the target form the consensus base pairs of each family a held
``rna_family_scan`` listed. Design note ``docs/plan/designs/a102_rna_tools.md``; facts and the reference counts in
``runs/a102_rna_probe/NOTES.md`` (Item 7).

INPUT. For every family of the scan (its best hit), the Stockholm alignment ``cmalign`` (Infernal 1.1.5, local mode by default,
one CPU) wrote for the hit's span of the target against the family's model (``cmfetch`` of the model out of ``Rfam.cm``). The span,
not the whole sequence: ``cmalign`` aligns, it does not search, and the flanks of a leader aligned the model only in part in the
probe. The alignment holds the family's consensus structure (``#=GC SS_cons``), the consensus residues (``#=GC RF``: a ``.`` marks a
column that is an insertion relative to the model) and one row, the target's span.

THE RULE. Base pairs are the matched ``<>``, ``()``, ``[]`` and ``{}`` of the WUSS notation of ``SS_cons`` (a stack per bracket type, over the match columns of the alignment, the model's consensus, in which an insertion of the target cuts no
helix; Infernal's user guide, ``formats.tex``: Infernal cannot handle pseudoknots and its output carries none, so no pseudoknot letter names a
pair here). Per family: ``consensus_pairs`` P; of them the ``pairs_present`` (both columns hold a residue of the target, not ``-``
or ``.``) and of those the ``pairs_canonical`` (AU, GC, GU either way; T is read as U). ``value = pairs_canonical / P``, in [0, 1]:
the share of the family's base pairs this sequence can form. A family whose consensus has no pair (P = 0) has no value (null, never a
zero) and no measurement. Facts that weigh nothing: per consensus stem (the maximal helices of ``SS_cons``, by
``calculations/rna_structure_topology.parse_rna_topology`` on the nested brackets) its pairs, pairs present and pairs canonical; the
counts of the stems wholly formable (every pair present and canonical), partly (some pair canonical) and not at all; the target's
residues in insertion columns and the consensus columns with no target residue. No boundary decides kept or lost: the fractions are
the record. A candidate is ``rna_family:<Rfam accession>``, the same as the scan's.

The sheet is controlled data: numbers, accessions and names of the database, pair names and record references."""
from gene_annotation_episode.episodic_workflow.episode_support.calculations.rna_structure_topology import parse_rna_topology
from gene_annotation_episode.episodic_workflow.episode_support.forms.rna_structure.rna_structure_contracts import COORDINATE_SYSTEM

GRADING_VERSION = 'canonical_pairs_over_consensus_pairs_of_cmalign_span'
SCHEMA = 'a102_rna_structure_agreement_sheet_v1'
PROVIDER = 'rna_structure_agreement'
OPEN, CLOSE = '<([{', '>)]}'
CANONICAL = ('AU', 'UA', 'GC', 'CG', 'GU', 'UG')
ABSENT = '-.'


def _require(condition, code):
    if not condition:
        raise ValueError('a102_rna_structure_agreement_' + code)


def read_stockholm(text):
    """``(SS_cons, RF, target name, target row)`` of a ``cmalign`` Stockholm alignment of one sequence (its blocks joined; the
    ``#=GR`` lines are not read)."""
    _require(text.startswith('# STOCKHOLM 1.0'), 'alignment_is_not_stockholm')
    ss, rf, rows = '', '', {}
    for line in text.splitlines():
        if line.startswith('#=GC SS_cons'):
            ss += line.split(None, 2)[2]
        elif line.startswith('#=GC RF'):
            rf += line.split(None, 2)[2]
        elif line and not line.startswith('#') and line != '//':
            name, row = line.split(None, 1)
            rows[name] = rows.get(name, '') + row.strip()
    _require(len(rows) == 1, 'alignment_is_not_of_one_sequence')
    ((name, row),) = rows.items()
    _require(len(row) == len(ss) == len(rf), 'alignment_rows_differ_in_length')
    return ss, rf, name, row.upper().replace('T', 'U')


def consensus_pairs(ss):
    """The base pairs ``(i, j)`` (columns, 0-based, sorted) of the WUSS string ``ss``: the matched brackets of each type."""
    stacks = {opener: [] for opener in OPEN}
    pairs = []
    for column, mark in enumerate(ss):
        if mark in OPEN:
            stacks[mark].append(column)
        elif mark in CLOSE:
            _require(stacks[OPEN[CLOSE.index(mark)]], 'closing_bracket_without_an_opening')
            pairs.append((stacks[OPEN[CLOSE.index(mark)]].pop(), column))
    _require(not any(stacks.values()), 'opening_bracket_without_a_closing')
    return sorted(pairs)


def stems_of(ss, pairs):
    """The maximal stems of ``ss`` as lists of pairs, by ``parse_rna_topology`` on the nested brackets (every bracket type written
    as one: the pairs of a valid WUSS string nest), after the check that its pairs are the ones read here."""
    nested = ''.join('(' if mark in OPEN else ')' if mark in CLOSE else '.' for mark in ss)
    topology = parse_rna_topology(nested, coordinate_system=COORDINATE_SYSTEM)
    _require(topology['status'] == 'valid' and sorted((pair['i'], pair['j']) for pair in topology['pairs']) == pairs,
             'topology_differs_from_the_pairs')
    by_key = {pair['pair_key']: (pair['i'], pair['j']) for pair in topology['pairs']}
    return [sorted(by_key[key] for key in stem['pair_keys']) for stem in topology['stems']]


def family_row(accession, name, hit, stockholm):
    """The sheet row of one family: ``hit`` is the scan sheet's row of its best hit (``rna_family_scan_sheet.hit_rows``) and
    ``stockholm`` the ``cmalign`` text of its span."""
    full_ss, rf, sequence_name, full_row = read_stockholm(stockholm)
    _require(all(mark.isalpha() or mark in ABSENT for mark in full_row), 'target_row_has_a_mark_that_is_not_a_residue_or_a_gap')
    # The consensus is the model's: its columns are the match columns (``RF`` not ``.``); a target residue in an insertion column is
    # counted apart and cuts no helix of the consensus.
    match = [column for column, mark in enumerate(rf) if mark != '.']
    ss, row = ''.join(full_ss[column] for column in match), ''.join(full_row[column] for column in match)
    pairs = consensus_pairs(ss)
    present = [(i, j) for i, j in pairs if row[i] not in ABSENT and row[j] not in ABSENT]
    canonical = [(i, j) for i, j in present if row[i] + row[j] in CANONICAL]
    present_set, canonical_set = set(present), set(canonical)
    stems = [{'outer_pair_first_column': stem[0][0], 'outer_pair_last_column': stem[0][1], 'pairs': len(stem),
              'pairs_present': sum(pair in present_set for pair in stem), 'pairs_canonical': sum(pair in canonical_set for pair in stem)}
             for stem in stems_of(ss, pairs)]
    inserted = sum(1 for column, mark in enumerate(rf) if mark == '.' and full_row[column] not in ABSENT)
    unoccupied = sum(mark in ABSENT for mark in row)
    return {
        'candidate': 'rna_family:' + accession, 'family_accession': accession, 'family_name': name,
        'scan_rank': hit['rank'], 'scan_bit_score': hit['bit_score'], 'strand': hit['strand'],
        'span_from': min(hit['seq_from'], hit['seq_to']), 'span_to': max(hit['seq_from'], hit['seq_to']),
        'span_length': sum(mark not in ABSENT for mark in full_row), 'alignment_columns': len(full_ss),
        'consensus_columns': len(match),
        'consensus_pairs': len(pairs), 'pairs_present': len(present), 'pairs_canonical': len(canonical),
        'pairs_noncanonical': len(present) - len(canonical),
        'stem_count': len(stems), 'stems_formable': sum(item['pairs_canonical'] == item['pairs'] for item in stems),
        'stems_partly_formable': sum(0 < item['pairs_canonical'] < item['pairs'] for item in stems),
        'stems_not_formable': sum(item['pairs_canonical'] == 0 for item in stems),
        'inserted_residues': inserted, 'unoccupied_consensus_positions': unoccupied, 'stems': stems,
        'value': len(canonical) / len(pairs) if pairs else None}


def grade_rna_structure_agreement(families, *, scan_source_ref, query_ref):
    """The sheet of one agreement test over the families of the held scan ``scan_source_ref`` of ``query_ref``. ``families`` is
    ``[{'accession', 'name', 'hit', 'stockholm'}]`` in the scan's order of candidates."""
    rows = [family_row(item['accession'], item['name'], item['hit'], item['stockholm']) for item in families]
    found = [{'candidate': row['candidate'], 'kind': 'rna_family', 'identifier': row['family_accession'],
              'name': row['family_name'], 'value': row['value']} for row in rows if row['value'] is not None]
    return {'schema': SCHEMA, 'grading_version': GRADING_VERSION, 'provider': PROVIDER, 'scan_source_ref': scan_source_ref,
            'query_ref': query_ref, 'canonical_pairs': list(CANONICAL), 'family_count': len(rows),
            'candidates_measured': len(found), 'families_without_pairs': len(rows) - len(found), 'rows': rows, 'candidates': found}


__all__ = ['CANONICAL', 'PROVIDER', 'SCHEMA', 'consensus_pairs', 'family_row', 'grade_rna_structure_agreement', 'read_stockholm',
           'stems_of']
