"""Data products: files a unit made or fetched that other units may use again, labelled and kept for reuse.

A data product is one artifact (content-addressed: its reference is the SHA-256 of its bytes, so the same bytes are
always the same product and changed bytes are never the old one) with one row of the declared work table
``data_products`` that says, in established vocabularies:

- WHAT IT IS: its EDAM data type and EDAM format (https://edamontology.org; the terms in ``KINDS`` were taken
  from EDAM's own release file, EDAM.tsv, on 2026-11-20, none of them obsolete). A step that needs a product
  asks for its kind (``require_product``), never for a file name.
- WHERE IT CAME FROM, in the three links of W3C PROV: ``generated_by`` (the activity that made it: the job's
  handoff row, or the source record of the unit), ``used`` (the records and artifacts it was made from) and
  ``derived_from`` (earlier data products it was made from); with ``settings``, the parameters of that activity.
- WHERE ELSE IT LIVES: ``locations``, beside the local artifact (for example its path in the BV-BRC workspace,
  which BV-BRC's applications take as an input without a second upload).
- HOW TO FIND IT INSTEAD OF MAKING IT AGAIN: ``reuse_key``, a digest of the kind, the inputs it used and the
  settings. The same inputs with the same settings give the same key, so a step can look for a held product
  with that key before it launches a job (``find_reusable``), the way workflow systems cache their steps.

Rows are custody items (``episode_runtime/work_tables.py``): a product is passed to a child or returned to a parent
by naming its row reference, and only an Episode that holds the row can read it. Nothing here reads a file or the
network; the caller writes through ``ctx.store`` and reads through the reader it is given.
"""
import hashlib

from episode_runtime import TableDeclaration
from method_loop.jsonvalue import canonical

# kind -> (EDAM data type, EDAM format, what it is in words)
KINDS = {
    'multiple_sequence_alignment': ('http://edamontology.org/data_0863', 'http://edamontology.org/format_1984',
                                    'Sequence alignment, FASTA-aln'),
    'protein_sequences': ('http://edamontology.org/data_1233', 'http://edamontology.org/format_1929',
                          'Sequence set (protein), FASTA'),
    'sequence_search_results': ('http://edamontology.org/data_0857', 'http://edamontology.org/format_3464',
                                'Sequence search results, JSON (BLAST JSON report)'),
    # data_0858 Sequence signature matches (synonym: Sequence-profile alignment): a sequence scanned against a profile
    # database (data_0857 is a search of a database of sequences). EDAM.tsv, read 2026-11-21: neither obsolete. The
    # HMMER domain table has whitespace-aligned columns, not tabs, so TSV (format_3475) would mislabel it; EDAM has no
    # format for it closer than format_2330 Textual format.
    'profile_scan_results': ('http://edamontology.org/data_0858', 'http://edamontology.org/format_2330',
                             'Sequence signature matches, textual (HMMER hmmscan domain table)'),
    # The three products of the all-vs-all child. EDAM.tsv, read 2026-11-21 (https://edamontology.org/EDAM.tsv), none obsolete.
    # data_1233 Sequence set (protein) for the prepared BLAST database: EDAM has no term for a BLAST database, so the closest
    # one is the protein sequence set it holds, in format_3981 TAR format (the files makeblastdb wrote, packed in one archive).
    'blast_protein_database': ('http://edamontology.org/data_1233', 'http://edamontology.org/format_3981',
                               'Sequence set (protein), TAR (the files of a BLAST protein database)'),
    # data_2082 Matrix ("a broad data type ... a placeholder for other, more specific types"): EDAM has no sequence-similarity
    # matrix of pair scores (data_0870 Sequence distance matrix is evolutionary distance); format_3475 TSV (query, subject, bit score).
    'sequence_similarity_matrix': ('http://edamontology.org/data_2082', 'http://edamontology.org/format_3475',
                                   'Matrix, TSV (BLAST bit score of each ordered pair of a sequence set)'),
    # data_1245 Sequence cluster (protein) in format_2171 Sequence cluster format (protein) (one cluster per line).
    'sequence_clusters': ('http://edamontology.org/data_1245', 'http://edamontology.org/format_2171',
                          'Sequence cluster (protein), one cluster per line'),
    'alignment_position_report': ('http://edamontology.org/data_0867', 'http://edamontology.org/format_3475',
                                  'Sequence alignment report, TSV (statistics per alignment position)'),
}
EDAM_SOURCE = 'https://edamontology.org/EDAM.tsv, read 2026-11-20'

DATA_PRODUCTS = TableDeclaration(
    name='data_products',
    columns=('artifact_ref', 'kind', 'edam_data', 'edam_format', 'generated_by', 'used', 'derived_from',
             'settings', 'locations', 'reuse_key'),
    key=('artifact_ref',),
    record_refs=('artifact_ref', 'generated_by', 'used', 'derived_from'))


def reuse_key(kind, used, settings):
    """The digest a product is found again by: its kind, the references of what it used (in any order: the set
    counts) and its settings (closed JSON)."""
    if kind not in KINDS:
        raise ValueError('data_product_kind_unknown:' + str(kind))
    body = canonical({'kind': kind, 'used': sorted(set(used)), 'settings': settings})
    return hashlib.sha256(body.encode() if isinstance(body, str) else body).hexdigest()


def record_product(store, *, artifact_ref, kind, generated_by, used, settings, derived_from=(), locations=()):
    """Label the held artifact ``artifact_ref`` as a data product of ``kind`` and return its row. ``generated_by``
    is the reference of the activity's record (a job's handoff row or a source record); ``used`` and
    ``derived_from`` are lists of held references; ``locations`` a list of ``{'service', 'path'}`` where the same
    bytes also lie."""
    data, form, _ = KINDS[kind] if kind in KINDS else (None, None, None)
    if data is None:
        raise ValueError('data_product_kind_unknown:' + str(kind))
    rows = list(locations)
    if any(set(row) != {'service', 'path'} or not all(type(row[name]) is str and row[name] for name in row)
           for row in rows):
        raise ValueError('data_product_location_must_be_service_and_path')
    return store.table(DATA_PRODUCTS).put({
        'artifact_ref': artifact_ref, 'kind': kind, 'edam_data': data, 'edam_format': form,
        'generated_by': generated_by, 'used': list(used), 'derived_from': list(derived_from),
        'settings': settings, 'locations': rows, 'reuse_key': reuse_key(kind, used, settings)})


def products(reader, kind=None):
    """The held data products, in receipt order: all of them, or those of ``kind``."""
    return reader.table(DATA_PRODUCTS).select(None if kind is None else {'kind': kind})


def find_reusable(reader, kind, used, settings):
    """The held product of ``kind`` made from exactly ``used`` with ``settings``, or ``None``."""
    found = reader.table(DATA_PRODUCTS).select({'reuse_key': reuse_key(kind, used, settings)})
    return found[0] if found else None


def require_product(reader, row_ref, kind):
    """The held product row ``row_ref``, which must be of ``kind``: the problem code to report otherwise
    (``data_product_not_held``, ``data_product_kind_mismatch``), else ``None`` beside the row."""
    rows = [row for row in reader.table(DATA_PRODUCTS).select(None) if row['id'] == row_ref]
    if not rows:
        return None, 'data_product_not_held'
    if rows[0]['kind'] != kind:
        return rows[0], 'data_product_kind_mismatch'
    return rows[0], None


__all__ = ['DATA_PRODUCTS', 'EDAM_SOURCE', 'KINDS', 'find_reusable', 'products', 'record_product',
           'require_product', 'reuse_key']
