# CodA retained-source conversion for the proposed A101 sheet

Source DOI **10.1021/bi200680y**. Inspected extent here: complete retained
`../a101_sheet_construction_001/CODA_NUMERICAL_CELLS_001.md`; no new primary
article, supplementary file, sequence or search was opened. The retained packet
records the parent's primary article and supplement inspection. This worker's
claims are limited to that packet. Full post-packet authority reread R1 was
completed before this conversion or opening another paper-specific packet.

The compared material is the initially uncharacterized *Picrophilus torridus*
protein expressed in *E. coli*, with a proposed relationship to an SAH-deaminase
subgroup. The separately purified, functionally studied *E. coli* CodA is a
different molecule. Genotype, exact constructs, full sequences, pairwise
alignment and target coordinates are unavailable in the inspected packet.
Host contributors were not isolated for the initial archaeal preparation.
Experimental comparability and effect isolation therefore cannot be inferred
from the sequence-network cutoff. The purified CodA result cannot supply the
missing activity or sequence match for the archaeal material.

| Sheet cell | Reported operands | Derived value | Meaning and limit |
| --- | --- | ---: | --- |
| Named-site exact-identity fraction | H/Q, one observed comparison among one declared position | 0/1 = 0 | Exact residue mismatch at this named comparison; allowed functional substitutions and target coordinate remain unknown. |
| Named-site assessment fraction | One observed comparison / one declared comparison | 1/1 = 1 | Observation completeness for this one-site question. Multiplication by its exact-identity fraction gives the same 0/1, not extra support. |
| Network threshold | E cutoff 10^-70 | Native parameter retained | It is not any target/reference hit E-value. |
| Raw score, bit score, pair E, query/reference coverage | Not supplied | null | No threshold substitution or zero imputation. |
| Grounded CodA site positions | Q156, E217, H246, D313, D314 | Count 5 | Defines possible reference positions; target mapping and compatibility remain null. |
| Source-identifying peptide coverage | Ten nonoverlapping intervals totaling 142 residues, as retained | 142 residues | Preparation identification, not target/reference alignment coverage. Whole length is absent. |

For a grounded site panel of N positions, m assessable mappings and k compatible
positions, the proposed sheet keeps m/N, k/m (if m>0), and k/N with missing-data
bounds [k/N,(k+N-m)/N]. Their product identity m/N × k/m = k/N prevents counting
the same fact twice. Here the H/Q result populates exact identity only; it does
not establish functional compatibility. The eventual combination must not
convert that absence of compatibility knowledge into a function zero.

The retained rounded kinetic ratio 6.7/1.5 = 4.4666666667 concerns CodA molecular
activity and stays A105. Knockout evidence stays A106. They ground or qualify the
reference endpoint but are not added as A101 sequence observations. A search
network edge, a biochemical comparison, a structural position and a peptide
identification are different measurements; no replicate count follows from
their appearance in one paper or several records.

Required complementary information for a numerical A101 transfer index is an
actual scoped native comparison and coordinate mapping to a functionally
characterized reference. Missing operands leave this case's joined A101 index
unavailable; source-populated component cells remain usable. No experimental
reliability grade or made-up native score fills the gap.

## Additive conversion into convention015

The network cutoff has no entry in f_t(B), because it is not B or an observed
hit E-value. The one exact H/Q comparison remains 0/1 in its own site-identity
cell; it does not identify an allowed-substitution panel for the proposed
function. Thus neither the native index nor a function-compatible A_F point is
available here. This is missing-input behavior under defined formulas, not a
new zero score. Source arithmetic is separately exported to
source_arithmetic_001_coda.json for paper-by-paper review.
