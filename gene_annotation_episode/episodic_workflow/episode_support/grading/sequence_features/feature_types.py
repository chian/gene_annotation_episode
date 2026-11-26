"""The types of feature a sequence can hold and how they are nested: the one list of feature types of the code base, held
by feature calling and read by everything else (the kinds a feature record may have, ``domain.FEATURE_KINDS``, are this
list). The owner, 2026-11-25: "only the feature_calling arm should hold onto it (and even then it will be public, not
private)".

The nesting is by type, not by size (the owner, the same day: "finer candidate has to do with feature type not size ...
within a gene you might have a motif or a secondary structure or a protein region (ATP binding site) or something like that.
That's nested. But two proteins are not nested."). The hierarchy agreed with the owner:

    transcription unit (an operon is a transcription unit with several genes)
        regulatory element (promoter, operator, ribosome binding site, terminator)
        gene
            coding sequence (the protein)
                mature peptide (a protein cut out of the translated one; it can hold the types below)
                protein domain
                    protein site, protein motif, protein structural element
                protein site, protein motif, protein structural element outside any domain
            RNA gene: non-coding RNA; a tRNA and an rRNA are kinds of it
                RNA structural element
    mobile element, repeat: stand alone
    sequence region: states no type; above every type

Every type can stand alone when what would hold it has not been found. This module holds data only and imports nothing."""

STRANDS = ('+', '-', '.')
CODING = 'CDS'
# For each type, every type that can hold it, the nearest first.
_UNIT = ('transcription_unit', 'sequence_region')
_GENE = ('gene', *_UNIT)
_PROTEIN = (CODING, *_GENE)
_MATURE = ('mature_peptide', *_PROTEIN)
_RNA = ('ncRNA', *_GENE)
ABOVE = {
    'sequence_region': (), 'transcription_unit': ('sequence_region',), 'mobile_element': ('sequence_region',),
    'repeat': ('sequence_region',), 'regulatory_element': _UNIT, 'gene': _UNIT, CODING: _GENE, 'ncRNA': _GENE,
    'tRNA': _RNA, 'rRNA': _RNA, 'rna_structural_element': ('tRNA', 'rRNA', *_RNA),
    'mature_peptide': _PROTEIN, 'protein_domain': _MATURE, 'protein_site': ('protein_domain', *_MATURE),
    'protein_motif': ('protein_domain', *_MATURE), 'protein_structural_element': ('protein_domain', *_MATURE)}
KINDS = tuple(ABOVE)
# The types that are parts of a protein: within a coding sequence they are read in its frame.
PROTEIN_PARTS = ('mature_peptide', 'protein_domain', 'protein_site', 'protein_motif', 'protein_structural_element')

__all__ = ['ABOVE', 'CODING', 'KINDS', 'PROTEIN_PARTS', 'STRANDS']
