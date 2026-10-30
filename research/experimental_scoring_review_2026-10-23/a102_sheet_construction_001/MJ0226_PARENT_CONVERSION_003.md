# MJ0226: partial structural correspondence and numerical scope

New parent research conversion; no changes to prior papers, packets, scoring,
readers or prompts. Source: Hwang et al. (1999), DOI 10.1038/10745,
https://www.researchgate.net/publication/12895555_Structure-based_identification_of_a_novel_NTPase_from .

The parent read MJ0226_sheet_conversion_001.md completely, including its
additive decimal correction, and the current cross-case sheet in full after
repairing a truncated initial combined read. The author-posted primary main
text, Methods, tabular text and figure captions were inspected through
acknowledgments (web lines 0–1168; displayed reference text through 1257 was
also visible). The parent did not inspect figure pixels, all references,
coordinates, a native alignment, or the reference synthetase papers. Publisher
access redirected to an unavailable authentication endpoint; the author copy
provided the primary text. The saved RCSB length response was read directly;
the parent did not rerun that metadata request.

After this source inspection, all six groups of the complete required authority
set were read, with the active goal attachment and latest human direction last.
No other primary was opened before this conversion. The historical A105-only
assignment is subordinate to the current ten-sheet goal; its A105/A106 boundary
still applies.

## What was compared

MJ0226 from Methanococcus jannaschii was expressed from PET3a in E. coli BL21.
The cloned sequence was checked. Its apo structure was determined by multiple
isomorphous replacement. The comparisons are between separate coordinate
models, not between protein amounts in a mixed experimental sample. Protein
identity differs deliberately; exact selected chains, comparison states,
maps, and their uncertainties remain unrecovered.

The primary reports one MJ0226 lobe resembling the C-terminal domains of
histidyl-tRNA synthetase (1ADJ) and glycyl-tRNA synthetase (1ATI). It names DALI
and SHEBA without unambiguously assigning each printed statistic to a software
version. The respective native reported numbers are:

| Comparison | Z | C-alpha RMSD | Matched C-alpha pairs |
|---|---:|---:|---:|
| MJ0226–1ADJ | 5.9 | 2.7 angstrom | 76 |
| MJ0226–1ATI | 4.6 | 3.1 angstrom | 75 |

These are partial structural matches. They do not demonstrate the catalytic
function of either entire synthetase. The native Z values stay as reported
statistics, not normal-tail probabilities of function. The two comparisons
share the target structure and are not independent replicate experiments.

## Numerical cells and compilation of the available measurements

The retained metadata's exact field is
`entity_poly.rcsb_sample_sequence_length`: 1B78 entity 1 = 193,
1ADJ entity 1 = 421, 1ATI entity 1 = 505 residues. These are whole deposited
polymer denominators. They are not lengths of the matched domains, observed
coordinate counts, or automatically the sequence versions used in 1999.

Using the worker's explicit proposed RMSD convention:

    C = 2*matched_positions/(target_scope_length + reference_scope_length)
    G = 1/(1 + (RMSD/2 angstrom)^2)
    B = C*G

| Derived or proposed cell | MJ0226–1ADJ | MJ0226–1ATI |
|---|---:|---:|
| Target deposit coverage | 76/193 = 0.3937823834 | 75/193 = 0.3886010363 |
| Reference deposit coverage | 76/421 = 0.1805225653 | 75/505 = 0.1485148515 |
| C | 152/614 = 0.2475570033 | 150/698 = 0.2148997135 |
| G | 400/1129 = 0.3542958370 | 400/1361 = 0.2939015430 |
| B | 0.0877084157 | 0.0631593574 |
| Squared-distance sum from rounded RMSD | 76*(2.7)^2 = 554.04 angstrom squared | 75*(3.1)^2 = 720.75 angstrom squared |

The last row is algebra on rounded reported C-alpha RMSDs, not a new exact
coordinate measurement. The 2-angstrom scale is an unadopted proposed scoring
parameter. B is a dimensionless whole-deposit extent/geometry descriptor;
it is not a functional confidence or a domain-normalized score.

A domain-specific question requires defined domain boundaries before scoring
its coverage. Cropping each sequence to the successfully aligned residues
would artificially make coverage complete. No such crop is supplied here.

## Comparability and isolation

Comparability concerns differences in selected construct, state, assembly and
model that could affect the geometric comparison beyond the intended protein
difference. These are not recoverable quantitative correction operands in the
published alignment excerpts. Missing details do not justify a general grade.

Isolation concerns what the geometric relationship establishes. A partial lobe
match establishes limited structural correspondence; it does not isolate
activity, ligand specificity, or whole-enzyme function. The source's subsequent
binding and reaction tests address different evidence questions. Their values
are not additional independent A102 measurements. Nondetection in an assay with
unreported sensitivity cannot fill a missing structural-similarity value of zero.

The primary's ligand-contact distances are observed within one structure, not
distances between homologous sites after superposition. They cannot fill the
worker's required between-protein feature-distance cells. Actual pair maps and
local feature geometry therefore remain null.

## Source-to-cell trace

| Inspected input | Numerical cells or limit |
|---|---|
| Primary Structure-based functional analyses, pp. 692–693 | Z/RMSD/pair-count triplets; partial-domain scope; two named search programs |
| Primary Methods and Coordinates, pp. 695–696 | Construct/source identity; MIR determination; apo/bound deposition distinction |
| Primary nucleotide-site text, pp. 693–694 | Why within-model contacts are not homologous-site displacement measurements |
| Retained RCSB length receipt | Exact deposited-polymer denominator field and values |
| Proposed sheet equations | 2-angstrom compression and symmetric extent; neither is a published calibration |

Exact fields for a future reader are the numerical native count/RMSD/Z cells,
their atom choice and scope, separate length fields with denominator type, and
nullable map/state/site cells. A reader must preserve qualifiers and missing
inputs. This research supplies no reader implementation or current-target
sequence mapping. Parent arithmetic is checked in check_a102_review_002.py.
