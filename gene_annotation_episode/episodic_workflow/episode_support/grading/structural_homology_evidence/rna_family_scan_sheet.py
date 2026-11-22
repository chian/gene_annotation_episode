"""The grader and the sheet of A102's ``rna_family_scan``: which structured RNA family (Rfam) is the target, by a covariance model.
Design note ``docs/plan/designs/a102_rna_tools.md``; the facts it rests on are in ``runs/a102_rna_probe/NOTES.md``.

INPUT. The table of one ``cmscan`` of Infernal 1.1.5 over the covariance models of Rfam: ``--tblout`` in format 2 (``--fmt 2``, with
the clan file, so a hit that a better hit of the same clan overlaps is kept and marked), by Rfam's own documented command
(``cmscan -Z <Mb> --cut_ga --rfam --nohmmonly --tblout <file> --fmt 2 --clanin Rfam.clanin Rfam.cm <sequence>``, one CPU), and the
family index of the database (per accession its name, model length and gathering threshold GA, read from the GA line of each model
of ``Rfam.cm`` when the database was installed). Format 2 has 29 columns (Infernal user guide, ``tabular.tex``, "Target hits table
format 2"): ``idx``, target name, accession, query name, accession, clan name, ``mdl``, model from and to, sequence from and to,
strand, ``trunc``, ``pass``, ``gc``, ``bias``, bit score, E-value, ``inc``, ``olp``, ``anyidx``, ``afrct1``, ``afrct2``, ``winidx``,
``wfrct1``, ``wfrct2``, model length, sequence length and the target's description (free text of the database: not read).

THE RULE. Per hit (a row): every number and mark of the table is copied (E-value included: it depends on ``-Z``, so it weighs nothing),
with the family's GA from the index. ``x = bits / GA`` and ``value = x^2 / (1 + x^2)``: one minus the axis's kernel
``1 / (1 + x^2)`` of ``1 / x`` (GA is the bit score Rfam's curators set as the lowest for a member of the family, so a hit at GA has
value one half and the rise is gradual, never a cut). With ``--cut_ga`` every hit has at least GA bits, so ``x >= 1`` and the value is
in [0.5, 1) (a hit below GA is not in the table; the grader raises on one, as it does on a hit not marked as included). A hit that a
better hit of the same clan overlaps (``olp`` ``$`` or ``=``) is a row and a candidate like any other (it is the competing family);
the mark is recorded. A candidate is ``rna_family:<Rfam accession>`` (the name shown is Rfam's identifier of the family); its value
is the value of its BEST hit (several hits of one family on one sequence are several places, not replicates), with the count of its
hits. A sequence with no hit has outcome ``no_family``: a graded sheet with no row and no candidate.

The sheet is controlled data: numbers, marks of the table's own vocabulary, accessions, family names and clan names of the database,
and record references."""
GRADING_VERSION = 'rfam_gathering_threshold_over_cmscan_format_2'
SCHEMA = 'a102_rna_family_scan_sheet_v1'
PROVIDER = 'rna_family_scan'
OUTCOMES = ('families', 'no_family')
TRUNCATIONS = ('no', "5'", "3'", "5'&3'")
OVERLAP_MARKS = ('*', '^', '$', '=')
STRANDS = ('+', '-')
COLUMNS = 29
HEADER = ('#idx target name          accession query name           accession clan name mdl mdl from   mdl to seq from   seq to '
          'strand trunc pass   gc  bias  score   E-value inc olp anyidx afrct1 afrct2 winidx wfrct1 wfrct2 mdl len seq len '
          'description of target')


def _require(condition, code):
    if not condition:
        raise ValueError('a102_rna_family_scan_' + code)


def value_of(bits, ga):
    """The value of a hit of ``bits`` in a family of gathering threshold ``ga``: ``x^2 / (1 + x^2)`` with ``x = bits / ga``."""
    x = bits / ga
    return x * x / (1 + x * x)


def parse_tblout(text):
    """The rows of a ``cmscan --tblout --fmt 2`` table, in the file's order (the comment lines are skipped; the first line must
    be the format-2 header). Raises ``ValueError`` for a header or a row that is not of format 2."""
    lines = text.splitlines()
    _require(lines and ' '.join(lines[0].split()) == ' '.join(HEADER.split()), 'table_is_not_format_2')
    rows = []
    for line in lines:
        if line.startswith('#'):
            continue
        fields = line.split(None, COLUMNS - 1)
        _require(len(fields) == COLUMNS, 'row_is_not_format_2')
        rows.append(fields)
    return rows


def hit_rows(fields_rows, index):
    """The sheet rows of the parsed table, with the GA of each family from ``index`` (``{accession: {'name', 'clen', 'ga'}}``)."""
    rows = []
    for position, fields in enumerate(fields_rows, 1):
        (idx, name, accession, _query, _query_accession, clan, mode, model_from, model_to, seq_from, seq_to, strand, trunc, passes,
         gc, bias, bits, evalue, included, olp, *_overlap, model_length, seq_length, _description) = fields
        _require(int(idx) == position, 'hit_index_is_out_of_order')
        _require(accession in index and index[accession]['name'] == name, 'family_is_not_in_the_database')
        _require(mode == 'cm' and strand in STRANDS and trunc in TRUNCATIONS and olp in OVERLAP_MARKS, 'mark_is_not_of_the_table')
        _require(included == '!' and int(model_length) == index[accession]['clen'], 'hit_is_not_included_or_model_length_differs')
        ga = index[accession]['ga']
        _require(float(bits) >= ga, 'hit_is_below_the_gathering_threshold')
        rows.append({
            'rank': position, 'family_accession': accession, 'family_name': name, 'clan': None if clan == '-' else clan,
            'model_from': int(model_from), 'model_to': int(model_to), 'model_length': int(model_length),
            'seq_from': int(seq_from), 'seq_to': int(seq_to), 'seq_length': int(seq_length), 'strand': strand, 'truncation': trunc,
            'pass': int(passes), 'gc': float(gc), 'bias': float(bias), 'bit_score': float(bits), 'evalue': float(evalue),
            'inclusion': included, 'overlap_mark': olp, 'overlapped_by_a_better_hit_of_the_clan': olp in ('$', '='),
            'ga': ga, 'x': float(bits) / ga, 'value': value_of(float(bits), ga)})
    return rows


def candidates(rows):
    """The family candidates of the rows: per accession (first appearance first) its hit count and the value of its best hit
    (``best_row``: its index in ``rows``; the first on a tie)."""
    found = {}
    for index, row in enumerate(rows):
        found.setdefault(row['family_accession'], []).append(index)
    return [{'candidate': 'rna_family:' + accession, 'kind': 'rna_family', 'identifier': accession,
             'name': rows[indices[0]]['family_name'], 'hit_count': len(indices), 'best_value': rows[best]['value'], 'best_row': best}
            for accession, indices in found.items() for best in [max(indices, key=lambda index: rows[index]['value'])]]


def grade_rna_family_scan(tblout, *, index, query, database, z_megabases):
    """The sheet of one ``cmscan`` table. ``index`` is the database's family index; ``query`` the facts ``{'query_ref',
    'length'}`` of the scanned sequence; ``database`` ``{'name', 'version', 'model_count'}``; ``z_megabases`` the ``-Z`` the scan was
    run with."""
    rows = hit_rows(parse_tblout(tblout), index)
    _require(all(row['seq_length'] == query['length'] for row in rows), 'sequence_length_differs_from_the_query')
    found = candidates(rows)
    return {'schema': SCHEMA, 'grading_version': GRADING_VERSION, 'provider': PROVIDER, 'query_ref': query['query_ref'],
            'query_length': query['length'], 'database': database['name'], 'database_version': database['version'],
            'families_in_database': database['model_count'], 'z_megabases': z_megabases,
            'outcome': 'families' if rows else 'no_family', 'hit_count': len(rows),
            'overlapped_hit_count': sum(row['overlapped_by_a_better_hit_of_the_clan'] for row in rows),
            'candidates_measured': len(found), 'rows': rows, 'candidates': found}


__all__ = ['OUTCOMES', 'PROVIDER', 'SCHEMA', 'candidates', 'grade_rna_family_scan', 'hit_rows', 'parse_tblout', 'value_of']
