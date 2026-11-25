"""The grader of one geNomad run on one sequence: the facts of its native tables, with its taxon names turned into taxon ids.

geNomad says two things. What kind of DNA the sequence is: three scores that sum to 1, ``chromosome_score``,
``plasmid_score`` and ``virus_score`` (its aggregated classification: a neural network on the sequence and the markers on
its genes). And, from the genes that match its markers, a virus taxonomy: the number of genes with a taxonomy, their
``agreement`` (the share of their weight that agrees on the lineage) and the lineage as names, from the realm down to the
deepest rank the genes agree on (never below family).

The sheet states: the three scores; the gene taxonomy when there is one (the counts, the agreement, the names as written);
for each name of the lineage that resolves in the prepared NCBI taxonomy its taxon row, the deepest resolved one as
``deepest_taxon_id``, and the names that did not resolve with why (``unknown`` or ``ambiguous``); and the rows of the two
taxa a kind of DNA names: Viruses, and cellular organisms (a chromosome or a plasmid is of a cell). No threshold and no
judgement is here."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.ncbi_taxonomy import (
    RESOLVED, identity, resolve, taxon_row)

SHEET = 'genomad_classification_sheet'
VIRUSES, CELLULAR = 10239, 131567
SCORES = ('chromosome_score', 'plasmid_score', 'virus_score')


def _rows(text, required):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError('genomad_table_empty')
    header = lines[0].split('\t')
    if any(name not in header for name in required):
        raise ValueError('genomad_table_header_unexpected')
    return [dict(zip(header, line.split('\t'), strict=True)) for line in lines[1:]]


def grade_genomad_classification(*, aggregated_text, taxonomy_text, sequence_name, taxonomy):
    """``{'sheet': ...}`` of the sequence ``sequence_name``: its row of the aggregated classification (required) and of the
    gene taxonomy (``taxonomy_text`` may be ``None`` or hold no row of it: no gene matched a marker with a taxonomy)."""
    scored = [row for row in _rows(aggregated_text, ('seq_name', *SCORES)) if row['seq_name'] == sequence_name]
    if len(scored) != 1:
        raise ValueError('genomad_classification_has_not_one_row_of_the_sequence')
    kind = {name: float(scored[0][name]) for name in SCORES}
    found = [] if taxonomy_text is None else [
        row for row in _rows(taxonomy_text, ('seq_name', 'n_genes_with_taxonomy', 'agreement', 'lineage'))
        if row['seq_name'] == sequence_name]
    if len(found) > 1:
        raise ValueError('genomad_taxonomy_has_more_than_one_row_of_the_sequence')
    genes, taxa, unresolved = None, [], []
    if found:
        names = [name for name in found[0]['lineage'].split(';') if name]
        genes = {'n_genes_with_taxonomy': int(found[0]['n_genes_with_taxonomy']), 'agreement': float(found[0]['agreement']),
                 'lineage_names': names}
        for name in names:
            taxon, state = resolve(taxonomy, name)
            if state == RESOLVED:
                taxa.append(taxon_row(taxonomy, taxon))
            else:
                unresolved.append({'name': name, 'state': state})
    return {'sheet': {'schema': SHEET, 'sequence': {'name': sequence_name}, 'kind': kind, 'gene_taxonomy': genes,
                      'taxa': taxa, 'deepest_taxon_id': taxa[-1]['taxon_id'] if taxa else None,
                      'unresolved_names': unresolved,
                      'kind_taxa': {'virus': taxon_row(taxonomy, VIRUSES), 'cellular': taxon_row(taxonomy, CELLULAR)},
                      'taxonomy': identity(taxonomy)}}


__all__ = ['CELLULAR', 'SHEET', 'VIRUSES', 'grade_genomad_classification']
