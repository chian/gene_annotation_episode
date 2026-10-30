# MJ0226: contrasting published structural correspondences

This primary-specific research conversion follows the complete reset in `authority_reset_002.json`. The cross-case formula is a separate draft. No alignment was run.

## Source facts and experimental definitions

[Hwang et al. (1999), DOI 10.1038/10745](https://doi.org/10.1038/10745) was read through its [author-posted full text](https://www.researchgate.net/publication/12895555_Structure-based_identification_of_a_novel_NTPase_from). MJ0226 from *Methanococcus jannaschii* was expressed using PET3a in *E. coli* BL21; cloning sequence was checked. Apo deposition: 1B78. The comparisons concern separate coordinate models, not coexpression. Protein identity is the intended contrast; construct/state/model differences remain uncontrolled. The structure was determined by multiple isomorphous replacement.

| Reference named by primary | Reported Z | Reported Cα RMSD | Matched Cα pairs | Scope |
| --- | ---: | ---: | ---: | --- |
| Histidyl-tRNA synthetase, 1ADJ | 5.9 | 2.7 Å | 76 | C-terminal domain versus one MJ0226 lobe |
| Glycyl-tRNA synthetase, 1ATI | 4.6 | 3.1 Å | 75 | C-terminal domain versus one MJ0226 lobe |

Primary pp. 692–693 name DALI and SHEBA; exact per-result software version, chains, residue maps and score uncertainty are unavailable. Figure 3 was inspected at 312×234 pixels without numerical digitization. Reported tRNA, GAR-transformylase and FMN tests did not establish those functions; methods/detection limits are incomplete. Reported nucleotide-site differences constrain transfer. Binding/activity and occupancy observations remain A105/A111.

## Metadata denominators and arithmetic

Independent RCSB polymer-entity metadata queried with the RCSB skill gives deposited sample sequence lengths of 193 residues for [1B78 entity 1](https://data.rcsb.org/rest/v1/core/polymer_entity/1b78/1), 421 for [1ADJ entity 1](https://data.rcsb.org/rest/v1/core/polymer_entity/1adj/1), and 505 for [1ATI entity 1](https://data.rcsb.org/rest/v1/core/polymer_entity/1ati/1). The queried field is `entity_poly.rcsb_sample_sequence_length`. These are deposited polymer denominators, not recovered C-terminal-domain lengths, observed-coordinate counts, or independently established native full-length proteins. Reference chain selection remains unknown. No historical sequence version is reconstructed.

| Derived cell | 1B78–1ADJ | 1B78–1ATI | Meaning |
| --- | --- | --- | --- |
| Target deposit coverage | 76/193 = 0.3937823834 | 75/193 = 0.3886010363 | Fraction of deposited target polymer represented by the published matched count |
| Reference deposit coverage | 76/421 = 0.1805225653 | 75/505 = 0.1485148515 | Extent relative to whole deposited reference, not its matched domain |
| Symmetric deposit coverage | 152/614 = 0.2475570033 | 150/698 = 0.2148997135 | Single symmetric extent factor |
| Proposed RMSD compression, scale 2 Å | 1/[1+(2.7/2)²] = 0.3542958370 | 1/[1+(3.1/2)²] = 0.2939015429 | Explicit operational geometry convention, not a probability |
| Proposed whole-deposit pair descriptor | (152/614)/[1+(2.7/2)²] = 0.0877084183 | (150/698)/[1+(3.1/2)²] = 0.0631593580 | Geometry × matched extent for the named denominator scope |
| Squared-distance sum implied by rounded RMSD | 76×2.7² = 554.04 Å² | 75×3.1² = 720.75 Å² | Algebra from rounded Cα RMSD, not a newly observed coordinate sum |

These are whole-deposit descriptors. They cannot be relabeled as domain-normalized scores. They also cannot establish whole aminoacyl-tRNA synthetase function: the compared region is an accessory domain. A future domain-specific row requires the source-defined target and reference domain intervals, their lengths, the exact map, and function-relevant site correspondences. The denominator must be chosen for the functional scope, before judging its magnitude; cropping each protein to its matched residues would mechanically erase the coverage limitation.

## Conversion into the user's sheet

The native RMSD and count fill the structural-correspondence cells directly. The coverage fractions make the partial nature of correspondence numerical. The proposed product evaluates extent-weighted geometry, with an explicit 2 Å distance scale. Z is retained as the reported comparison statistic, with the unresolved DALI/SHEBA attribution stated; it is not added to RMSD as an independent experiment. No Gaussian-tail probability or exact native DALI formula is inferred from the paper's printed Z values.

Comparability asks whether the compared constructs, states and modelling conditions permit an informative geometric comparison beyond the intended protein difference. The unavailable chains/states prevent a numerical state-matched correction. Isolation asks what this structural endpoint identifies: it identifies a geometric relationship for a partial protein region. It does not isolate catalysis or unique ligand specificity. Those limitations differ even when one numerical row describes both.

A site correspondence term must evaluate the geometry of the function-relevant site under the same parent scaffold superposition. Merely sharing a lobe is insufficient. A documented nucleotide contact in MJ0226 is not itself a between-protein comparison, and a different binding mode cannot be turned into an invented site RMSD. Site cells are therefore null, with missingness propagated into bounded function-specific support. The cross-case sheet supplies a complete synthetic site/competitor calculation rather than fabricating those measurements for this primary.

The two references are not repeated measurements of the same function: their domain-level correspondences share target coordinates but support distinct, limited comparisons. Their rows are preserved. For a broad nucleotide-related hypothesis they might be compatible contextual observations; for a whole synthetase annotation they do not match the required catalytic scope. A function distinction must be defined by the annotation under consideration, not by different protein names alone. Possible functions can emerge during investigation of supplied material; these historical public identifiers are example labels.

## Inspection and source-to-cell coverage

| Source inspected | Cells/meaning supported | Limit |
| --- | --- | --- |
| Primary, pp. 692–693, Structure-based functional analyses | Printed Z/RMSD/count triplets; partial-domain scope | No native alignment output, map or exact chain pairing |
| Primary, pp. 695–696, Methods and Coordinates | Expression/construct checks; apo versus bound deposit identities | Detailed comparison settings absent |
| Primary Fig. 3, publisher GIF | Visual confirmation of displayed scope | Small image; no atom distances or exact intervals extracted |
| RCSB three polymer-entity API responses | Explicit sample-sequence length denominators | Modern deposit metadata; no claim of domain/coordinate lengths |
| Primary discussion/site text | Limits on copying a specific function from fold resemblance | Activity/occupancy numerical evidence not counted on A102 |

The complete author-posted article body, captions, tables and references were read; unrelated citation-list text and search-result snippets were not used as evidence. Publisher access first failed or supplied an abstract preview. The author-page extraction changed line numbering between retrievals; coverage is recorded by retained retrieval segments and article sections, not a false single contiguous line range. No coordinate files, homolog searches, alignment jobs, production code, readers or scientific episodes were executed.

Status: contrasting source conversion and bounded arithmetic ready for the draft. Exact source-side function-specific site and domain operands remain absent. This limits filling these published examples; it does not leave the proposed sheet's arithmetic unspecified.

### Additive arithmetic correction, checked before handoff

The displayed whole-deposit pair-descriptor decimals above contain transcription errors in their last digits. Correct values are **0.0877084157** for 1B78–1ADJ and **0.0631593574** for 1B78–1ATI. The displayed formulas and all source operands are unchanged. The cross-case table and machine-readable checked examples use these corrected values. This correction preserves the initial written row rather than silently replacing it.
