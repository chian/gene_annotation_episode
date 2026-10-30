# A104 paper 03: a numerical tree-placement example

Research conversion only; no adopted policy, implemented reader, completed axis,
or new analysis of biological sequences. This paper was authorized after the
2012 seed lacked a native phylogenetic measurement. The full post-paper reset is
recorded in `authority_reset_paper03_001.json` and preceded this conversion.

## Source and inspection

Hehemann et al. (2010), *Transfer of carbohydrate-active enzymes from marine
bacteria to Japanese gut microbiota*, Nature 464:908–912,
[DOI 10.1038/nature08937](https://doi.org/10.1038/nature08937).
Full article and online Methods were read from the
[public university-hosted original PDF](https://hahana.soest.hawaii.edu/cmoreserver/summercourse/2012/documents/delong_06-05-12/sushi_microbiome.pdf),
retained as `porphyran2010_main_001.pdf`. The complete normalized extraction is
`porphyran2010_main_normalized_001.txt`.

[Publisher Fig. 3](https://www.nature.com/articles/nature08937/figures/3) was
visually inspected in retained `porphyran2010_fig3_001.jpg`. Supplemental
text, tables, and captions were read in full after repairing an initially
truncated whitespace-heavy extraction; `porphyran2010_supp_normalized_001.txt`
is the readable extraction. Supplemental figure graphics were not separately
visually inspected. The publisher's subscription preview and failed main-PDF
request are retained and are not claimed as the full article.

## Published observations, distinct from our calculations

| Source location | Observation relevant to A104 |
| --- | --- |
| Fig. 3 and Methods, sequence/phylogenetic analysis | Maximum-likelihood GH16 tree; PhyML; bootstrap based on 100 resamplings. |
| Fig. 3 | B. plebeius Bp1689 falls in the porphyranase group; Bp1670 in the agarase group. |
| Fig. 3 | Bp1689–Zg3640/PorE sister grouping has bootstrap label 99; the encompassing porphyranase clade has label 55. |
| Main Results, recombinant enzymes | PorA (Zg2600) and PorB (Zg1017) were characterized. PorC/D/E were not characterized successfully there; PorE is not a measured-function anchor. |
| Fig. 3 and main text | AgaA (Zg4203) and AgaB (Zg3573) supply experimentally characterized alternative-function references. |
| Fig. 3 | No numerical branch-length scale is supplied for conversion to substitutions per site. |
| Main text/Methods | No matched organism tree or formal gene-tree/organism-tree reconciliation is supplied. |

These observations concern one comparative analysis, not independent evidence
from every leaf or branch. Characterization provenance is attached to the
references; this packet does not score those biochemical experiments as A104.

## Exact conversion into numerical placement cells

Use candidate function **porphyranase** for both examples. Define the reference
sets before counting: F = {PorA, PorB}; G = {AgaA, AgaB}. For each of the four
F×G pairs, restrict the rooted published topology to query q, reference f and
alternative g. A result `qf|g` means q and f have a more recent common ancestor
than either does with g; `qg|f` has the opposite meaning. The third resolved
topology `fg|q` is an outside placement, contributing neither sign. An unresolved
triplet is missing, not that third topology.

The proposed component is P = (n_qf − n_qg)/N, with fixed N = |F|×|G| = 4.
It is a signed topological contrast, not a probability of function, a count of
genomes, or four independent experiments. The equal per-triplet normalization
and the signed contrast are this draft's numerical convention, not a formula
reported by the authors.

| Published query | q–PorA versus AgaA | q–PorA versus AgaB | q–PorB versus AgaA | q–PorB versus AgaB | n_qf | n_qg | n_outside | n_unresolved | Derived P |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Bp1689 | qf\|g | qf\|g | qf\|g | qf\|g | 4 | 0 | 0 | 0 | (4−0)/4 = +1 |
| Bp1670 | qg\|f | qg\|f | qg\|f | qg\|f | 0 | 4 | 0 | 0 | (0−4)/4 = −1 |

This contrasts two actual published placements while holding the functional
question and characterized reference sets fixed. Reversing the candidate and
alternative functions reverses the signs; it does not create new evidence.
The arithmetic check in `arithmetic_checks_001.py` checks these ratios. It does
not independently reconstruct the published tree: these four relationships
were read from the figure.

The published bootstrap labels produce separate native uncertainty cells:

| Exact tree feature | Printed support | Resampling denominator | Derived resampling fraction | Permitted interpretation |
| --- | ---: | ---: | ---: | --- |
| Bp1689 with PorE | 99 | 100 | 99/100 = 0.99 | Stability of this sister grouping under the stated resampling procedure. |
| Porphyranase clade | 55 | 100 | 55/100 = 0.55 | Stability of this larger grouping under that procedure. |

Do not multiply 0.99 by a functional annotation or call it 99% confidence in
porphyranase activity. Its nearest named sister was not experimentally
characterized in this study. Nor is 0.55 the support of every query/reference
triplet: marginal split supports do not reconstruct their joint distribution.
The full resampled trees would allow each complete proposed score to be
recalculated and averaged while retaining contradictory placements. Printed
split percentages alone do not fill that ensemble.

## How these cells enter the proposed A104 compilation

For a fully measured tree replicate, the separate sheet proposes a positive
term `max(P,0) × O_F × H` and an opposing term `max(−P,0) × O_G`, where O_F and
O_G measure branch-distance outlier status within the respective characterized
reference sets, and H measures agreement with the organism tree plus quantified
explanations of specific discordances. The final contribution averages the
complete positive and opposing terms across one declared tree ensemble.

For Bp1689, the point-tree positive term is therefore `1 × unknown × unknown`;
for Bp1670 it is exactly zero and the opposing term is `1 × unknown`.
These are **partial component calculations**, not two completed A104 scores.
The paper does not supply the distance scale, organism comparison, quantitative
HGT-explanation operands, or full resampled trees needed to compile the proposed
ensemble endpoint. All remain unknown. A point-tree opposing term of zero for
Bp1689 does not prove the ensemble opposing term is zero.

## Missing operands, dependence, and specific complements

| Material ambiguity | Exact complement that would resolve it |
| --- | --- |
| Long-branch/outlier status | Machine-readable original tree with branch lengths and units; calculate query-to-reference and within-reference patristic distances. Do not infer units from figure pixels. |
| Stability of the scored placement | Original bootstrap trees, including rooting and taxon labels; calculate the entire score within each replicate. A new alignment/run was not performed here. |
| Agreement with organism evolution | Independently estimated organism tree over matched, unambiguously mapped taxa; account for paralogs before counting query-anchored triplets. |
| HGT versus duplication, loss, contamination, or sampling | Gene-tree/species-tree reconciliation with supported taxon and copy mappings, plus sequence/sample provenance and alternative-model sensitivity. Marine versus gut labels alone are not a discordance count. |
| A concrete transfer explanation | Evidence addressing the specified donor–recipient contact route and transfer compatibility, with numerical operands or separately stated bounded judgments. Generic environmental plausibility is not a replacement tree metric. |
| PorE as nearest reference | Direct substrate-specific activity measurement for PorE would resolve its function. Its name and high split support do not do so. |
| Functional reference coverage | Additional independently characterized functional alternatives and their exact placement, preserving discovery scope and shared characterization provenance. |

The 2012 follow-up and this 2010 paper overlap in the biological locus and
history being discussed. Reading both does not provide independent tree
replication. The 2012 packet's lack of a native tree remains unchanged. Its
mobile-element observations may complement a specified transfer mechanism, but
element size, repeat length, and excision-PCR effort do not numerically fill a
tree-concordance or transfer-probability cell. The ThyX replacement seed remains
a distinct missing-tree boundary case; successful functional replacement is
not proof of shared phylogenetic placement.

Source facts, derived topology counts, proposed transformations, and missing
data are separated above. The cross-case formula and fully synthetic endpoint
belong in `A104_NUMERICAL_SHEET_DRAFT_001.md`, for later parent review.
