# QueF-like retained-source conversion for the proposed A101 sheet

Source DOI **10.1021/cb200361w**. Inspected extent here: complete retained
`../a101_sheet_construction_001/QUEFL_NUMERICAL_CELLS_002.md`. No additional primary
paper, supplement, alignment or sequence search was opened. Full authority reset
R2 followed that packet and preceded this interpretation and the next packet.

The sequence comparison is eight archaeal QueF-like proteins versus the
C-terminal half of *Vibrio cholerae* QueF; the four pocket positions instead
come from *Bacillus subtilis* QueF. The particular supplied *Pyrobaculum
calidifontis* record is 109 aa. Its introduced expression in *E. coli* delta-queF
is associated with archaeosine formation in tRNA. Exact construct/background
contributions and free versus tRNA-bound natural substrate are not resolved in
this inspected packet. These facts cannot turn a bacterial reductase function
into the archaeal protein's demonstrated molecular activity. Comparability of
sequence regions and attribution of the experimental endpoint are separate.

| Proposed sheet cell | Actual source operands | Derived value | Scope |
| --- | --- | ---: | --- |
| Reported sequence identity range | 16–22% | [0.16,0.22] | Across the specified domain comparisons, not a per-pair CI or whole-protein score. |
| Pocket-site compatibility | Four mapped C/D/Y/E matches / four named sites | 4/4 = 1 | Retention of this selected pocket panel. |
| Query full-pattern occurrence count | Complete declared eight-position signature in the 109-aa supplied record | 0 | A sequence qualification; not measured loss of binding or reduction. |
| Source-set pattern presence | Zero records with a complete match / eight records | 0/8 = 0 | The query is included: not independent extra evidence. |
| Native bits/E and exact alignment coverage | Absent | null | The reported identity range cannot supply counts or coverage. |

The proposed numerical split is a recognition panel and a mechanism panel.
Each panel uses a count fraction over its declared features, retaining unknown
maps as intervals. In this case recognition is 4/4; a full-pattern feature is
0/1 for the specified bacterial signature. A proposed linear panel term
`a_recognition * 1 + a_mechanism * 0` retains the shared pocket information.
The coefficients must be printed as proposed policy, never inferred from this
paper or replaced by a global relevance grade. The complete sheet defines the
chosen coefficients and combines these terms with available native evidence;
the case's missing native scores stay missing. No universal multiplication by
the zero motif count is justified.

The signature belongs to the N-terminal domain in bimodular bacterial QueF.
Absence from a C-terminal display is therefore not an observed full-reference
absence. This query's complete-record scan supports its particular zero count;
an arbitrary snippet would leave the unevaluated portion unknown. The scan used
an unrestricted residue at the undefined hydrophobic position: zero matches
under that permissive pattern remains zero for a hydrophobic subset; a positive
match would need the actual allowed alphabet.

Preserve printed reference positions 55/62/70/97 separately from record-byte
positions 56/63/71/98 and query positions 21/28/36/63. The offset cause is unknown.
The structural correspondence that grounded this map is shared evidence, not
another independent A101 replicate; its RMSD and superposed C-alpha counts stay
A102. Complementary native sequence maps and actual substrate/cofactor tests
would address different missing components. Eight sequences, four positions and
multiple renderings are not eight assays, four replications or new papers.

## Additive conversion into convention015

Using the explicitly proposed equal-panel convention, a recognition-only
feature question gives A_recognition=4/4=1. A scoped source-feature comparison
that also asks for the bacterial cofactor signature gives
A_bacterial_features=((4/4)+(0/1))/2=0.5. The 0/8 family frequency is not added;
it includes the same query and answers a different denominator question.

These are a derived count and a proposed weighted combination, respectively.
Neither is a measured function probability. The source has not established
strict indispensability for this scoring exercise, so the motif is not
silently placed in V_F as a necessary-condition veto. The native-score inputs
remain absent. A complete feature-qualified point is therefore unavailable;
its broad mathematical enclosure with C_native in [0,1] is [0,0.5] for the
two-panel form. No estimate is placed inside that interval. Arithmetic is
separately exported to source_arithmetic_002_quefl.json.
