"""The sheet of one scan of a DNA sequence for RNA genes: the hits Infernal's covariance models of Rfam report on it, by Rfam's
own documented command (``cmscan -Z <Mb> --cut_ga --rfam --nohmmonly --cpu 1 --tblout <file> --fmt 2 --clanin Rfam.clanin``): each
family's own gathering threshold GA decides what the program reports, both strands are searched and reported. This module states
the table's facts only; which hits a caller counts, and how, is the caller's.

INPUT. The ``--tblout`` table in format 2 (29 columns, Infernal user guide ``tabular.tex``: ``idx``, target name, accession, query
name, accession, clan name, ``mdl``, model from and to, sequence from and to, strand, ``trunc``, ``pass``, ``gc``, ``bias``, bit
score, E-value, ``inc``, ``olp``, ``anyidx``, ``afrct1``, ``afrct2``, ``winidx``, ``wfrct1``, ``wfrct2``, model length, sequence
length, description) and the family index of the database (per accession the name, the model length and GA).

THE SHEET: per hit (a row of ``hits``) the family accession and name, its clan, ``begin`` and ``end`` on the piece (1-based,
inclusive, begin below end, whatever the strand), ``strand``, ``bit_score``, ``ga``, the E-value (it depends on ``-Z`` and weighs
nothing), the model span, ``truncation`` (the table's ``trunc``), ``overlap_mark`` (the table's ``olp``) and ``overlapped``: true
when the mark is ``=`` (the user guide: a ``=`` hit overlaps a lower-E-value hit of its clan, which is itself marked ``^``; a ``$``
hit overlaps only hits that are removed). ``hit_count`` counts the rows.

The sheet is controlled data: numbers, marks of the table's own vocabulary, accessions, family and clan names of the database and
record references."""
SCHEMA = 'rna_gene_scan_sheet'
PROVIDER = 'rna_gene_finding'
TRUNCATIONS = ('no', "5'", "3'", "5'&3'")
OVERLAP_MARKS = ('*', '^', '$', '=')
STRANDS = ('+', '-')
COLUMNS = 29
HEADER = ('#idx target name          accession query name           accession clan name mdl mdl from   mdl to seq from   seq to '
          'strand trunc pass   gc  bias  score   E-value inc olp anyidx afrct1 afrct2 winidx wfrct1 wfrct2 mdl len seq len '
          'description of target')


def _require(condition, code):
    if not condition:
        raise ValueError('rna_gene_scan_' + code)


def parse_tblout(text):
    """The rows of a ``cmscan --tblout --fmt 2`` table, in the file's order (comment lines skipped; the first line must be the
    format-2 header). Raises ``ValueError`` for a header or a row that is not of format 2."""
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
        (idx, name, accession, _query, _query_accession, clan, mode, model_from, model_to, seq_from, seq_to, strand, trunc, _passes,
         _gc, _bias, bits, evalue, included, olp, *_overlap, model_length, seq_length, _description) = fields
        _require(int(idx) == position, 'hit_index_is_out_of_order')
        _require(accession in index and index[accession]['name'] == name, 'family_is_not_in_the_database')
        _require(mode == 'cm' and strand in STRANDS and trunc in TRUNCATIONS and olp in OVERLAP_MARKS, 'mark_is_not_of_the_table')
        _require(included == '!' and int(model_length) == index[accession]['clen'], 'hit_is_not_included_or_model_length_differs')
        ga = index[accession]['ga']
        _require(float(bits) >= ga, 'hit_is_below_the_gathering_threshold')
        _require((int(seq_from) <= int(seq_to)) == (strand == '+'), 'span_is_not_in_the_order_of_its_strand')
        rows.append({
            'rank': position, 'family_accession': accession, 'family_name': name, 'clan': None if clan == '-' else clan,
            'begin': min(int(seq_from), int(seq_to)), 'end': max(int(seq_from), int(seq_to)), 'strand': strand,
            'bit_score': float(bits), 'ga': ga, 'evalue': float(evalue), 'model_from': int(model_from), 'model_to': int(model_to),
            'model_length': int(model_length), 'seq_length': int(seq_length), 'truncation': trunc, 'overlap_mark': olp,
            'overlapped': olp == '='})
    return rows


def grade_rna_gene_finding(tblout, *, index, piece, database, z_megabases):
    """The sheet of one ``cmscan`` table. ``index`` is the database's family index; ``piece`` the facts ``{'piece_ref',
    'length'}`` of the scanned piece; ``database`` ``{'name', 'version', 'model_count'}``; ``z_megabases`` the ``-Z`` the scan was
    run with."""
    rows = hit_rows(parse_tblout(tblout), index)
    _require(all(row['seq_length'] == piece['length'] and row['end'] <= piece['length'] for row in rows),
             'sequence_length_differs_from_the_piece')
    return {'schema': SCHEMA, 'provider': PROVIDER, 'piece_ref': piece['piece_ref'], 'piece_length': piece['length'],
            'database': database['name'], 'database_version': database['version'], 'families_in_database': database['model_count'],
            'z_megabases': z_megabases, 'hit_count': len(rows), 'hits': rows}


__all__ = ['PROVIDER', 'SCHEMA', 'grade_rna_gene_finding', 'hit_rows', 'parse_tblout']
