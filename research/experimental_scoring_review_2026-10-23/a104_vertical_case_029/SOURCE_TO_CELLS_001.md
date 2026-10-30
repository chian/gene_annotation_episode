# Bounded TyrA conserved-function example for A104

2026-10-24. Research conversion only; the A104 owner supplies the sheet and
combination proposal. This record is not an adopted score, a completed A104
sheet, or evidence about ybhP. The complete authority reset was performed after
the source inspection and before this conversion; see AUTHORITY_RESET_001.json.

The selected source is Song, Bonner, Wolinsky and Jensen (2005), **The TyrA family
of aromatic-pathway dehydrogenases in phylogenetic context**, *BMC Biology* 3:13,
[DOI 10.1186/1741-7007-3-13](https://doi.org/10.1186/1741-7007-3-13),
[PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC1173090/).
My initial selection message incorrectly called its journal Genome Biology;
this is the additive correction. The prior commentary interpreting the word
congruent preceded completion of the reset and was provisional. The conclusions
below are the post-reset reassessment.

## Fixed source example and experiment definitions

The example is the displayed **Pseudomonas/Azotobacter TyrA subgroup**, scoped
to five named leaves: Paer, Pstu, Pflu, Pput and Avin. It is not the whole TyrA
superfamily or the entire natural clade. Figure 2 contains selected sequences;
the authors explicitly say not all members of a group were necessarily shown.

The functional resolution is **NAD+-dependent cyclohexadienyl dehydrogenase
accepting both prephenate (PPA) and L-arogenate (AGN)**. This is one conserved
two-substrate functional profile, not a claim of PPA-only specificity. Table 4
reports that profile for P. aeruginosa and P. stutzeri; the other three displayed
members are not independently established as assayed by the inspected material.
The same source contrasts a related Acinetobacter branch with NADP specificity;
do not expand this exact cofactor claim to that larger subtree.

| Experimental definition | What can be retained |
|---|---|
| Actual assayed subjects | Author-reported P. aeruginosa TyrA and P. stutzeri TyrA; original assay references are Table 4 refs 17 and 1. These original assay papers were not opened in this bounded task. |
| Genotype and strain correspondence | Figure/Table 2 names P. aeruginosa PAO1; the original experimental strain/clone-to-tree-tip identity was not independently checked. P. stutzeri strain is unspecified in Table 2. |
| Construct | Results, “The catalytic-core domain of TyrA proteins,” says the P. stutzeri core was engineered from a TyrA–AroF fusion. Native/full-length and isolated-core evidence must retain this distinction. |
| Intended experimental comparison | Whether the enzyme accepts PPA and AGN, and which pyridine nucleotide it accepts. No jointly matched two-species experiment is reported in this paper. |
| Coexistence and background | Separate organism/protein studies are cited. The original assay mixtures, endogenous contributions, substrate contamination controls and purification details were not inspected; no mixture fraction is assumed. |
| Measured endpoint available here | Reported accepted substrate/cofactor sets; rates, assay concentrations, blank measurements, effect sizes, replicate numbers and uncertainty are unavailable in Table 4. |
| Experimental comparability | Shared endpoint/substrate names are known. Matched temperatures, pH, concentrations, preparation and construct conditions are unknown; no comparability number is assigned. |
| Effect isolation | A molecule-specific biochemical assignment is reported, but the original purification and negative controls have not been checked. No numerical isolation score follows from the tree or the table. |

## Leaf and functional-label mapping

The following are source identifiers, not newly resolved current accessions.
Unknown function rows are not negative tests or verified function-pure members.

| Figure leaf / intended member | Table 2 organism context | Table S1 TyrA identifier | Function status in this read |
|---|---|---|---|
| Paer | P. aeruginosa PAO1 | Paer_1, GI 15598360 | Table 4 explicitly reports NAD+, PPA/AGN; reported experimental assignment, original assay identity not rechecked |
| Pstu | P. stutzeri | GI 5712093 | Table 4 explicitly reports NAD+, PPA/AGN; reported experimental assignment, engineered core noted |
| Pflu | P. fluorescens PfO-1 | GI 23061127 | No individual experimental assignment verified here |
| Pput | P. putida KT2440 | GI 26988501 | No individual experimental assignment verified here |
| Avin | Azotobacter vinelandii | Displayed GI **53612601**, but hyperlink target **13105295** | Identifier conflict retained; no individual experimental assignment verified here |

The Avin discrepancy is in Table S1 itself. Do not select one identifier silently,
drop Avin, or calculate a favorable score on only the other four leaves. The
original table remains intact. This discrepancy concerns a protein identifier;
it does not erase the named organism from the intended denominator.

## Source-to-cell conversion

“Available” below means available at the declared source resolution, not an
implemented reader or a verified complete target sheet.

| Proposed sheet/input cell | Actual source and location | Populated value / deterministic operation | Meaning and limit |
|---|---|---|---|
| Intended displayed member count | Figure 2 subgroup, Table 2 and Table S1 five rows above | n_displayed = 5 | Fixed small example scope; not all extant members of the natural clade |
| Source-listed characterized members | Table 4 rows P. aeruginosa and P. stutzeri; Results cyclohexadienyl dehydrogenases | k_reported = 2 | Two named experimental assignments reported by this source; not two independent preparations or independently rechecked exact protein/strain matches |
| Source-listed function coverage | Same fixed five-member scope and the two Table 4 entries | k_reported / n_displayed = 2/5 = **0.4** | Observed literature-label coverage within this displayed example; not purity, annotation probability, or a whole A104 score |
| Function sets at the declared resolution | Table 4; Results pyridine-nucleotide specificity | Both reported references have the same NAD+/PPA+AGN profile | No known conflicting profile among those two; three other members remain unverified. This does not prove the complete clade contains only that profile. |
| Canonical-protein k and C_f for the owner's sheet | Exact assay-to-tip crosswalk plus all intended reference identities | **Unavailable** in a strictly identity-validated sheet | The 0.4 source ratio cannot silently fill this stronger cell while the original assay crosswalk and Avin identity are unresolved. |
| Organismal comparison provenance | Results “Phylogenetically congruent TyrA groupings”; Methods “Congruency groupings” | Reference is 16S rRNA genealogy; authors report group-level correspondence | Methods explicitly allow different internal branching orders. The named grouping is not a native numerical tree-agreement result. |
| Shared taxon/copy map | Tables 2/S1 give source labels; no matched organism-tree tips supplied | Five intended organism slots; exact shared-map status **unavailable** | Retain the same five-slot denominator, including unresolved mapping. Copy labels must not be inferred from a suffix alone. |
| Triplet/quartet denominator | Five intended organism slots; arithmetic only | choose(5,3)=10; choose(5,4)=5 | Conditional denominator checks. Rooted-triplet comparison is not justified by the radial tree. The unrooted route would have five quartets only after matching actual trees/copies. Neither number is a match count. |
| M, D, U and F = M/N | Need the common-leaf gene and independent organismal trees/native samples | **Unavailable** | No trees were reconstructed or compared. Do not set M=N from “congruency,” or turn absent trees into biological conflict. |
| Native gene-tree method | Methods “Alignments” | PHYLIP neighbor joining; Protdist Dayhoff PAM; **1,000 bootstrap resamples** | Published analysis, not rerun. Resamples are not 1,000 independent experiments or target placements. |
| Native branch support | Figure 2 legend | Filled symbols report >988; open symbols report >900, with B=1,000 | Integer-count interpretation gives at least 989/1,000 and 901/1,000 respectively. Exact support of this particular subgroup boundary was not extracted; these are legend conventions, not its assigned score. |
| Native branch units | Figure 2 scale/caption | 0.1 substitutions/site scale bar | No numerical path length was digitized; the scale bar itself cannot fill pendant distance, d, b, or O. |
| Query-pruned crown / J / placement weights | Need a supplied query and native placement/ensemble result | **Unavailable** | No query was placed; there is no original query-pruned crown measurement. No bootstrap frequency is substituted for placement mass. |
| Nearest-reference d, within-clade b, O; EDPL | Need branch values and placement data | **Unavailable** | EDPL would be dispersion, not an outlier score. Neither metric is supplied by the source table. |

The checkable scalar here is the real-source coverage ratio **2/5 = 0.4**.
Its numerator and denominator are explicit, rather than a verbal confidence
category mapped to 0.4. It can inform the owner's coverage component once the
source-label/canonical-protein distinction is resolved. It cannot replace tree
agreement, membership, or distance measurements.

## Connection to the owner's existing proposal

The owner supplied the working expression

`association = C_f × Σ_z w_z F_z J_z O_z`.

This record does not redefine it. The source-level demonstration supplies the
counting operation `2/5`; stricter canonical C_f, F, J and O remain unavailable.
Even if the owner explicitly accepts the source assignments for a displayed-scope
illustration, `0.4 × Σ_z w_z F_z J_z O_z` has **no numerical value** until the
other operands are supplied. Missing operands are not set to 1 or 0. No final
annotation-credit point or whole-target score is claimed.

The positive result is narrowly useful: two characterized relatives share the
same precise catalytic profile within a source-described phylogenetic subgroup
whose relationship to organismal genealogy is discussed. It does not establish
the user's full two-condition A104 test. The broad superfamily includes other
substrates/cofactors; that broader scope cannot inherit this local inference.

## Dependence, qualifications and repairable gaps

Table 4, figure colors and prose restate related evidence; they are not three
independent contributions. Two accepted substrates measured on one enzyme are
one multi-substrate function profile here. The original experimental reports
would be needed to score experimental comparability, purification/background
isolation and quantitative specificity; a tree cannot supply these controls.
Full-length and engineered-core experiments can complement one another without
being interchangeable. A source label is not evidence that all alternative
functions were excluded.

The intended five members stay fixed if a reader later resolves identities or
retrieves trees. Group-level reported congruence can motivate that comparison
but cannot predetermine its result. No reference tree was reverse-engineered
from the gene tree. No universal vertical-inheritance claim or absence-of-HGT
claim is made. Whole-clade purity is unknown; no majority credit for a narrower
function is introduced. Outliers and unmeasured branches supply no opposition
merely because they remain unmeasured.

## Read coverage and retrieval

Retained discovery came first: case_index.jsonl (all 142 case-group names), the
A101–A104 crosswalk, CURRENT_SLOT_SOURCES.md/OPTION_SOURCES.md search hits, and
an rg search of retained corpus JSON/JSONL/Markdown for organismal/species trees,
vertical inheritance/descent and 16S-tree phrases. This did not identify a
ready independent-tree case outside the excluded transfer/transporter lanes;
it was a bounded discovery search, not a full reread of all 142 primary cases.
No retained paper-specific conversion packet was consumed.

One new primary research paper was inspected: Song 2005. Complete inspected
sections were Background; Results subsections “Background of TyrA diversity,”
“Phylogenetically congruent TyrA groupings,” “Distribution in nature of TyrA
specificity subclasses for the cyclohexadienyl substrate,” “The catalytic-core
domain of TyrA proteins,” and “Specificity for the pyridine nucleotide
co-substrate within the TyrA superfamily”; and Methods in full. Figure 2 and its
caption were inspected. Tables 2, 3 and 4 were inspected in full; Table S1's
header, specified subgroup rows, ancillary low-GC rows and terminal footnote
were inspected. Captions for Figures 3 and 4 were incidentally read while
listing assets. The remaining synteny/regulation sections, original assay
papers, current sequence records, historical AroPath site and independent
16S trees were not inspected. Downloading a complete XML or supplement archive
is not a claim to have read every element in it.

The successful full-text XML route was
https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1173090/fullTextXML
and the successful supplementary archive route was
https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1173090/supplementaryFiles .
Table S1 is archive member `1741-7007-3-13-S1.html`. Its direct PMC URL returned
a download-preparation page, retained separately. Figure 2 is
https://cdn.ncbi.nlm.nih.gov/pmc/blobs/e473/1173090/93b3e4ac3120/1741-7007-3-13-2.jpg .

Early combined tool outputs were truncated. Authority truncation was repaired
by complete individual rereads; primary sections required here were reread
from the retained XML with adequate budgets. Source discovery search truncation
was narrowed to complete case names and A104 crosswalk rows. No omitted snippet
was used as evidence. All final conversion claims follow the documented full
post-paper authority reset. Only download/parsing/count arithmetic was run;
no scientific phylogeny, annotation, native bioinformatics or HPC job ran.
