# Proposed numerical scoring rubrics: A101–A104

Status: concrete proposal for the user's review, not an approved calibration or a changed global annotation formula. The entries now carry executable `scoring_rubric` descriptors. This document supplies their meaning, examples and scientific limits. The existing evidence rows and their limitations are unchanged.

## The score being calculated

Each route returns an actual numerical score with its unit, direction, relevant claim and evidence chain. For a native score `x`, `identity(x) = x`. For a strictly positive expectation or significance value, `neg_log10(x) = -log10(x)`. For two actual matched counts, `ratio(k,n) = k/n`, requiring `0 <= k <= n` and `n > 0`. The permitted HGT explanation grade uses the numerical levels below.

A route's `eligible_when` lists the exact claim-interpretation criteria that must be `met` before that score can be reported as support for that claim. The recorded native measurement always remains available as a fact. If a required criterion is `unknown`, the claim-support score is unavailable with that missing condition; if `not_met`, it is unavailable for that claim with the contradiction retained. Neither state becomes a fabricated native zero. These are conditions on what a number means, not a rule stopping an episode, requiring an experiment or accepting an annotation.

The output keeps supporting, opposing and non-discriminating routes distinct. A low similarity value, missing hit or high p-value is not automatically a demonstrated contradiction. A measured contrary effect or an incompatible characterized comparison must retain its actual relationship to the claim. Native quantities do not acquire a negative multiplier merely because a model calls them negative evidence.

Scores with different units are not added or averaged. In particular, BLAST bit score, HMMER profile score, DALI Z, TM-score, a context p-value and bootstrap percentage are not a common confidence scale. A future scalar combination must declare its calibration dataset, comparison task, held-out validation and dependence treatment. No such calibration has been fitted to these case descriptions. These rubrics supply numerical axis evidence now without inventing that missing fit.

## A101 — sequence homology

The score belongs to a specified target/comparator match and a specified annotation claim. For its transfer to support that claim, require all four existing criteria: an actual scored correspondence, experimentally characterized comparator property, correspondence of relevant features, and a claim no more specific than the comparison supports. A family-level claim and an exact-substrate claim can therefore have different eligibility for the same numerical alignment.

| Route | Exact numerical rule | Comparison meaning |
|---|---|---|
| Bit score | `s = reported bitscore`, in bits; larger is stronger alignment evidence | Preserve method/configuration and aligned subject/region. This is not a posterior probability of function. |
| Raw alignment | `s = reported alignment_score`, in native scoring units | Compare within the declared matrix, gap penalties and alignment mode; preserve compared spans. |
| Profile/model | `s = reported model_score`, retaining program/model units | Keep profile identity and score definition. Do not equate it with a different program's score. |
| Expectation | `s = -log10(E)` for actual `E > 0` | `E=10^-20` gives `20`; `E=2` gives approximately `-0.30103`. Preserve search-space scope. |
| Identity | `s = actual identity_fraction` | `63/192 = 0.328125` is a measured identity fraction, not 32.8% confidence in the function. |
| Matched extent | `s = actual query_coverage` or `actual target_coverage` | Keep these separate extent descriptors; do not multiply them into another score as pseudo-applicability weights. |

The [NCBI score statistics](https://www.ncbi.nlm.nih.gov/BLAST/tutorial/Altschul-1.html) define raw-score statistical normalization and explain the search-space dependence of E-values. Their null-alignment meaning does not establish functional specificity. The log transform here changes presentation/order, not that meaning.

**Case and dataset checks.** The saved [HemK analysis](../../corpus/sequence/hemk_live_routes.json) used one explicit local BLOSUM62 configuration: gap-open −11, extension −1. In the PrmB-versus-proteome search, actual raw scores were HemK `254`, TrmN6 `103`, RsmC `92`; the first margin is `151` native score units. The inspected HemK–PrmB alignment had `63` identities in `192` residue pairs, or `0.328125`. These numbers prioritize a related catalytic family. Published assays distinguish PrmB's L3 substrate from HemK's release-factor substrates, so copying L3 specificity is not eligible merely because the score is largest. The other saved route's `7/19 = 0.368421...` identity covers a short comparison and does not outrank the broader relationship by identity alone.

The [TriA/AtzA case](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/) differs at only nine of 475 residues while giving different substrate reactions; its implied identity is `466/475 = 0.9810526...`. The [HisN case](https://link.springer.com/article/10.1186/s12866-017-1069-4) retains the counterexample of a more similar candidate missing motif 5 and failing complementation. These cases justify the feature/specificity conditions; they do not justify a new universal identity cutoff.

## A102 — structural homology

Require an actual quantified comparison, correctly retained structure origins, correspondence of the functional geometry needed for the claim, and a transfer bounded to the characterized comparator property. Global fold similarity alone leaves the functional-geometry criterion unknown for a specific chemical assignment.

| Route | Exact numerical rule | Comparison meaning |
|---|---|---|
| TM-score | `s = reported TM-score` | `0.72` remains `0.72` on its native scale. Retain the normalization length and whether correspondence was specified or optimized. |
| DALI | `s = reported DALI Z` | `11.4` remains `11.4` in DALI units; no invented conversion to probability. |
| RMSD | `s = reported RMSD`, in Å; lower is closer | `1.8 Å` remains `1.8 Å` with aligned atom/residue selection and matched extent. Comparing arbitrary different-size alignments solely by RMSD is unsupported. |
| Other named native structural score | `s = actual score`, in its native method units | Keep the named method, score definition and comparison class. |
| Matched residue count | `s = actual aligned residue count` | A non-discriminating extent measurement; it is not independent extra functional support. |

The [TM-score authors' definition](https://zhanggroup.org/TM-score/) supplies its native bounded similarity scale and the importance of the normalization structure. That scale is topological similarity, not biochemical annotation probability. A structure prediction's confidence is not a structural homology score. The [DALI methods paper](https://doi.org/10.1002/pro.3749) explains DALI scores and structural comparisons; its Z statistic is retained rather than equated with TM-score or RMSD.

**Case checks and data limit.** The current A102 source rows describe functional counterexamples, not a complete table of scored structural alignments. MJ0577's global DALI matches were functionally uninformative; EnvC resembles active LytM but lacks the requisite zinc-coordinating architecture; Arad3529 and the aminotransferase cases require relevant local comparisons. The retained PDBe contact datasets identify actual ligand/contact records; they are not newly computed TM-scores, DALI results or RMSDs. Consequently there is no fitted structural-to-function calibration, and an absent native result leaves that numerical route unavailable. The numerical `0.72`, `11.4` and `1.8` examples above illustrate arithmetic only; they are not attributed to those cases.

## A103 — gene context

Require the actual locus/assembly/arrangement, grounded identities of relevant neighboring components, an arrangement bearing on the proposed relationship, and a claim limited to what context establishes. A neighbor's homology score identifies that neighbor; it does not become a score for gene-context association.

| Route | Exact numerical rule | Comparison meaning |
|---|---|---|
| Native context association | `s = actual method-specific association score` | Retain the method's unit and ordering. An unspecified score direction is not silently ranked upward. |
| STRING neighborhood channel | `s = actual nscore` on its retained returned scale | Use the API neighborhood channel on its native0–1 scale rather than combined/text-mining/coexpression/profile evidence. `0.83` remains `0.83`; a1000-scale download is not silently accepted as the same metric. |
| Context significance | `s = -log10(p)` for actual `0 < p <= 1` | `p=0.001` gives `3`; preserve the test, null, effect direction and multiple-testing treatment. A small p for a contrary relationship is not supporting evidence. |
| Counted context conservation | `s = k/n`, where actual `k` genomes meet the declared arrangement and actual `n` homolog-containing genomes are evaluable | `8/10 = 0.8`. This is a descriptive fraction, not an independent-sample probability or p-value. Closely related genomes are not counted as independent experiments. |

The [STRING API documentation](https://string-db.org/help/api/) identifies `nscore` as its neighborhood channel, distinct from the combined and other channels. The exact source/version/scale stays attached to the number. STRING's own calibrated association interpretation is not silently expanded into proof of exact reaction, direct binding or indispensable complex membership.

**Case checks and data limit.** The archaeal shikimate-kinase case shows an informative arrangement in other genomes despite dispersed pathway genes in the target genome. MJ0044 similarly lacks the arrangement in the target while conserved contexts elsewhere guide the alternative substrate question. BioY's approximately one-third linkage to BioMN demonstrates a non-universal relationship and does not imply the absent partner is essential. Those descriptions do not supply an exact supporting count and denominator, so they cannot produce an invented `k/n`. None of the retained A103 instruction observations supplies a native context p-value table. The `8/10` and `p=0.001` examples are explicit numerical illustrations; actual scores require actual records.

## A104 — evolutionary history and phylogenetic placement

For clade-support scores, require a real phylogeny/placement and a target placement among characterized members bearing the proposed property. Organism-history compatibility and HGT explanation are distinct comparisons; a plausible HGT story neither creates a tree nor increases its bootstrap support.

| Route | Exact numerical rule | Comparison meaning |
|---|---|---|
| Bootstrap percentage | `s = actual relevant-branch support percent` | `92` stays `92%`, retaining standard/ultrafast method and alignment/tree scope. |
| Counted bootstrap fraction | `s = k/n` for actual supporting replicates and actual total replicates | `920/1000 = 0.92`; this is the same branch-support contribution as `92%`, not a second independent fact. |
| Clade posterior | `s = actual model-conditioned posterior` | `0.97` remains `0.97` for the clade under that model, not 97% annotation confidence. |
| Gene/organism history comparison | `s = actual method-specific congruence/reconciliation statistic` | Retain native unit, null/model and sign convention; no environmental narrative is turned into a native tree statistic. |
| HGT explanation | proposed ordinal grade below | Separate from tree score; never a multiplicative weight on it. |

The [IQ-TREE documentation](https://iqtree.github.io/doc/Frequently-Asked-Questions) distinguishes standard and ultrafast bootstrap interpretations and limits single-gene recommendations. Therefore even two percentages are not silently treated as one calibrated annotation-confidence scale. No universal functional-confidence cutoff is introduced here.

The user explicitly permitted a pseudo-grader for an outlying gene-history explanation when a suitable native numerical measure is absent. The following is a **proposed numerical coding of the existing firm conditions**, not a probability:

| Grade | Numeric score | Required condition |
|---|---:|---|
| `contradicted` | 0 | Received biological, source/recipient or sequence/genomic evidence contradicts the stated transfer explanation. Retain that contrary evidence. |
| `plausible_only` | 1 | Actual source/recipient circumstances permit the proposed explanation, but independent evidence does not distinguish it from retained alternatives. Shared environment alone can reach this level, never the next. |
| `corroborated` | 2 | The explanation fits the actual outlying placement and source/recipient circumstances and has independent received support bearing on transfer; retain unresolved alternatives and sampling/paralog limitations. |
| `unknown` | no point score; possible interval `[0,2]` | Actual outlying placement, relevant context or evidence needed to assign a level is missing. Do not substitute 0; the interval is the range of possible rubric levels, not a statistical confidence interval. |

The HGT numerical route requires an actual phylogeny. The criterion being graded is not additionally required to be `met`: otherwise `contradicted` and `plausible_only` could never be represented. A statement incompatible with vertical inheritance does not alone prove HGT or refute the proposed function.

**Case checks and data limit.** The preserved YjeH case actually reports an APC-transporter tree placing YjeH with an efflux branch, while OarX is in a distinct clade from coexisting FabG. The remaining co-distribution cases remain such; they are not relabeled as newly reconstructed phylogenies or demonstrated HGT events. Their retained instruction observations do not include native bootstrap/posterior arrays or a fitted HGT dataset. Thus `92%`, `920/1000` and `0.97` are arithmetic examples, not newly reported measurements of those proteins.

## Common input, missing data and dependence

Published findings and analysis of experimental datasets use the same formal evidence unit: actual original experiment/measurement identity, its representation, actual native numeric facts, typed criterion judgment and actual witnesses. A paper is one representation; a deposited dataset is another. There is no bonus for source type.

The same underlying experiment/measurement represented by a paper and a dataset is one contribution with two provenance records. Re-reading, repeated delivery, alternative numeric displays and multiple tools operating on the same underlying comparison do not automatically add evidence. Conflicting reported values for one underlying measurement are retained as a conflict, not averaged. A ratio requires its actual matched numerator/denominator set, not arbitrary pairing across experiments. Different independently grounded observations remain separate route results unless a declared calibrated combination is supplied.

A missing value is unavailable. A stated negative assay or incompatible placement is a received finding with its measured meaning. A no-hit result needs the actual detection/search scope and does not establish absence outside it. Bounded native numbers retain their bounds and uncertainty: `E < 10^-50` yields `-log10(E) > 50`, not an exact 50. Displayed zero without a positive reporting limit does not become infinity or an arbitrary epsilon. The numerical proposal adds no action, stopping condition, forced study order or requirement to obtain every route.

Native domains are explicit in the descriptors: p-values, identity/coverage fractions, TM-score and posterior support are in `[0,1]`; E-values and counts are nonnegative; branch support expressed in percent is in `[0,100]`. The generic method-dependent scores do not receive invented bounds. The API neighborhood metric accepts its native0–1 scale only. A value outside its declared native domain is reported unavailable rather than transformed or clipped. Count fractions require `k <= n`; `12/10` is an invalid fraction input, not a score of1.2.
