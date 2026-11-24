"""Data products: files a unit made or fetched that other units may use again, labelled and kept for reuse.

A data product is one artifact (content-addressed: its reference is the SHA-256 of its bytes, so the same bytes are
always the same product and changed bytes are never the old one) with one row of the declared work table
``data_products`` that says, in established vocabularies:

- WHAT IT IS: its EDAM data type and EDAM format (https://edamontology.org; the terms in ``KINDS`` were taken
  from EDAM's own release file, EDAM.tsv, on 2026-11-20 (the terms with no date beside them) or on the date
  written beside the term, none of them obsolete). A step that needs a product
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
    # The two other texts the scan grades, of the same data type. EDAM.tsv, read 2026-11-21 (https://edamontology.org/EDAM.tsv),
    # none obsolete: the per-sequence table is whitespace-aligned like the domain table (format_2330 Textual format); the
    # report hmmscan writes on standard output is format_1421 HMMER profile alignment (sequences versus HMMs) ("Format used by
    # the HMMER package for an alignment of a sequence against a hidden Markov model database").
    'profile_scan_sequence_hits': ('http://edamontology.org/data_0858', 'http://edamontology.org/format_2330',
                                   'Sequence signature matches, textual (HMMER hmmscan per-sequence table)'),
    'profile_scan_report': ('http://edamontology.org/data_0858', 'http://edamontology.org/format_1421',
                            'Sequence signature matches, HMMER profile alignment (sequences versus HMMs): the hmmscan report'),
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
    # The BV-BRC records of a search's hits (``bvbrc_hit_metadata``: the genome_feature, protein_family_ref and genome
    # documents of the named hits, BV-BRC's field names unchanged; the hits' product names come from them). EDAM.tsv, read
    # 2026-11-21 (https://edamontology.org/EDAM.tsv), neither obsolete: data_0896 Protein report, synonym "Gene product
    # annotation" ("An informative human-readable report about one or more specific protein molecules ... derived from
    # analysis of primary (sequence or structural) data"): each record is one hit protein's product name, families, genome
    # and length. Not data_0849 Sequence record ("A molecular sequence and associated metadata"): the records hold no
    # sequence, only its MD5; not data_1277 Protein features or data_1255 Sequence features: those are positional
    # annotation, and these records have no positions. format_3464 JSON (the canonical JSON of the lookup).
    'search_hit_metadata': ('http://edamontology.org/data_0896', 'http://edamontology.org/format_3464',
                            'Protein report (gene product annotation), JSON (BV-BRC feature, family and genome records of '
                            'the hits of a search)'),
    # A tool's graded sheet as retained (``tool_grading_artifacts.retain_tool_grading``: the provider, the graded artifact
    # and the grading, canonical JSON). EDAM.tsv, read 2026-11-21, neither obsolete: data_2048 Report ("computer-generated
    # reports of analysis of primary data (e.g. sequence or structural) ... You can use this term by default for any textual
    # report, in case you can't find another, more specific term"): the sheets grade a database search, a profile scan, an
    # alignment, a clustering and an analysis of alignment positions, and no narrower term covers each of them
    # (data_0867 Sequence alignment report fits the alignment sheet only; data_1772 Score is one value, a sheet is many,
    # with what they were read from). format_3464 JSON.
    'tool_grading_sheet': ('http://edamontology.org/data_2048', 'http://edamontology.org/format_3464',
                           'Report, JSON (the graded sheet of one tool result)'),
    # A model of the target's structure (A102 ``get_model``: the AlphaFold DB model of an identical UniProt sequence, or an
    # ESMFold prediction), as the PDB text the source returned. EDAM.tsv, read 2026-11-21 (https://edamontology.org/EDAM.tsv),
    # neither obsolete: data_1460 Protein structure ("3D coordinate and associated data for a protein tertiary (3D) structure");
    # not data_0883 Structure (it is for any macromolecule) and not data_1469 Protein structure (all atoms), which is obsolete.
    # format_1476 PDB ("Entry format of PDB database in PDB format"): both sources write PDB text, with the per-residue
    # confidence (pLDDT) in the B-factor column.
    'protein_structure_model': ('http://edamontology.org/data_1460', 'http://edamontology.org/format_1476',
                                'Protein structure, PDB (a model of the target: AlphaFold DB or ESMFold)'),
    # The result of one Foldseek server search of a structure database with one model (``structure_search``: per hit the
    # alignment, its statistics and the hit's aligned C-alpha coordinates). EDAM.tsv, read 2026-11-21, neither obsolete:
    # data_0887 Structure alignment report ("An informative report of molecular tertiary structure alignment-derived data"):
    # the report is the alignments of the target's model with the hits. Not data_0885 Structure database search results, which
    # is obsolete in this release, and not data_0886 Structure alignment (that is the superimposed coordinates; the result
    # holds the alignments and the hits' own C-alpha coordinates, not a superposition). format_3464 JSON.
    'structure_search_results': ('http://edamontology.org/data_0887', 'http://edamontology.org/format_3464',
                                 'Structure alignment report, JSON (Foldseek server result of one search)'),
    # The residue-level functional sites of the hits of a graded structure search, as the services answered (A102
    # ``site_correspondence``: UniProt's active-site, binding-site and site features of the hits' accessions, or the M-CSA
    # catalytic residues, with the request, status and checksum of each reply). EDAM.tsv, read 2026-11-21
    # (https://edamontology.org/EDAM.tsv), neither obsolete: data_1277 Protein features ("An informative report on intrinsic
    # positional features of a protein sequence"): the replies are positions in the hits' sequences. Not data_1321 Protein
    # features (sites), which is obsolete in this release, and not data_0896 Protein report (that is a report of the protein
    # as a whole, with no positions). format_3464 JSON.
    'functional_site_annotations': ('http://edamontology.org/data_1277', 'http://edamontology.org/format_3464',
                                    'Protein features, JSON (UniProt site features or M-CSA catalytic residues of the hits '
                                    'of a structure search)'),
    # A solved structure the unit fetched (A102 ``partner_contacts``: the biological-assembly file of a PDB entry,
    # ``<ID>-assembly<N>.cif.gz`` of https://files.rcsb.org/download/, kept as the mmCIF text it unpacks to). EDAM.tsv, read
    # 2026-11-21 (https://edamontology.org/EDAM.tsv), neither obsolete: data_1460 Protein structure ("3D coordinate and
    # associated data for a protein tertiary (3D) structure, or part of a structure, possibly in complex with other molecules"):
    # the files hold the protein with its bound ligands and nucleic acids. Not data_0883 Structure (any macromolecule, wider
    # than what is fetched) and not data_1461 Protein-ligand complex (many files hold no ligand). format_1477 mmCIF ("Entry
    # format of PDB database in mmCIF format"). The gzip transfer form is in the settings (``download_bytes``,
    # ``download_sha256``), not the format.
    'experimental_structure': ('http://edamontology.org/data_1460', 'http://edamontology.org/format_1477',
                               'Protein structure, mmCIF (the biological-assembly file of a solved PDB entry)'),
    # The result of the pairwise structural alignments of one ``partner_contacts`` job batch (``usalign_driver``: per pair both
    # TM-scores with their normalisations, RMSD, aligned length, sequence identity, the aligned residue pairs, the rotation and the
    # translation). EDAM.tsv, read 2026-11-21, neither obsolete: data_0887 Structure alignment report ("An informative report of
    # molecular tertiary structure alignment-derived data"), the same data type as ``structure_search_results``; format_3464 JSON.
    'pairwise_structure_alignments': ('http://edamontology.org/data_0887', 'http://edamontology.org/format_3464',
                                      'Structure alignment report, JSON (US-align alignments of the target with hit chains)'),
    # AlphaFill's answer for the accession of one AlphaFold DB model (A102 ``ligand_transplants``: ``GET https://alphafill.eu/v1/aff/
    # <accession>/json``, kept as the service answered, also the 404 body of an accession it has no entry for): per solved homolog
    # the ligands transplanted into the model with their local RMSD, clash score and the model residues near them. EDAM.tsv, read
    # 2026-11-21 (https://edamontology.org/EDAM.tsv), neither obsolete: data_1277 Protein features ("An informative report on
    # intrinsic positional features of a protein sequence"), the data type of ``functional_site_annotations`` for the same reason
    # (positions in the protein's sequence; the answer holds no coordinates). Not data_1461 Protein-ligand complex ("The structure of
    # a protein in complex with a ligand"): the answer is not a structure. format_3464 JSON.
    'ligand_transplant_results': ('http://edamontology.org/data_1277', 'http://edamontology.org/format_3464',
                                  'Protein features, JSON (AlphaFill ligand transplants of an AlphaFold DB model)'),
    # A102 ``rna_family_scan`` (Infernal ``cmscan`` of an RNA over the covariance models of Rfam) and ``rna_structure_agreement``
    # (``cmalign`` of the hit span to each family's model). The data types and the format are the ones this file already uses and
    # read from EDAM.tsv: data_0858 Sequence signature matches (a sequence scanned against a database of models, as
    # ``profile_scan_results``), data_0863 Sequence alignment (as ``multiple_sequence_alignment``), format_2330 Textual format (as
    # the HMMER tables: the cmscan table has whitespace-aligned columns, so TSV would mislabel it). EDAM has no Infernal format and
    # the Stockholm alignment is labelled with the general format too; EDAM.tsv was not read again for a closer term (no outside
    # request was allowed in the task that added these kinds), so the closer terms are not claimed.
    'rna_family_scan_results': ('http://edamontology.org/data_0858', 'http://edamontology.org/format_2330',
                                'Sequence signature matches, textual (Infernal cmscan table, format 2)'),
    'rna_family_scan_report': ('http://edamontology.org/data_0858', 'http://edamontology.org/format_2330',
                               'Sequence signature matches, textual (Infernal cmscan report with the alignments of the hits)'),
    'rna_family_alignments': ('http://edamontology.org/data_0863', 'http://edamontology.org/format_2330',
                              'Sequence alignment, textual (Stockholm alignment of the span of the target to one covariance model, by cmalign)'),
    # The scores of one A102 ``partner_cofolding`` job (``scores.json`` of ``run_chai.py``: per ligand and sample the interface and
    # chain scores and the clash flags of Chai-1's prediction of the target with that ligand). Data type data_2048 Report (a
    # generic report; EDAM.tsv was not read again for a closer term, no outside request was allowed in the task that added
    # this kind, so no closer term is claimed); format_3464 JSON. The scores are the model's confidence, never measured binding.
    'cofolding_results': ('http://edamontology.org/data_2048', 'http://edamontology.org/format_3464',
                          'Report, JSON (Chai-1 co-folding scores of the target with each of several ligands)'),
    # The protein genes one run of the gene finder called on a piece of DNA (parts discovery ``find_genes``: per gene its
    # positions, strand, start codon, ends cut off by the piece, ribosome-binding site, the finder's scores and confidence, with
    # the finder's version, mode and genetic code). data_1255 Sequence features ("positional features of a sequence": the term
    # named in the EDAM.tsv reading of 2026-11-21 in the comment of ``functional_site_annotations`` above, where it was set aside
    # for a protein because it is positional; the calls are positions on DNA); format_3464 JSON. EDAM.tsv was not read again for
    # this kind (no outside request was allowed in the task that added it): data_1255 is to be confirmed as not obsolete.
    'gene_calls': ('http://edamontology.org/data_1255', 'http://edamontology.org/format_3464',
                   'Sequence features, JSON (the protein genes called by a gene finder on a piece of DNA)'),
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
