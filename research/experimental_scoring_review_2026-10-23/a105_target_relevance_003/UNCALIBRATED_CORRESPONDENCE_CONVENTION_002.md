# A105 relevance proposal 002: numerical correspondence when no endpoint calibration exists

2026-10-23. Additive correction to the practical limitation of proposal 001: a calibrated activity mapping cannot be a prerequisite that leaves ordinary novel targets unscorable. Most such targets lack direct molecular activity measurements and paired endpoint calibration. The primary mathematical interface in `TARGET_RELEVANCE_INTERFACE_002.md` remains useful where supported. This separate file supplies a concrete alternative SCORE CONVENTION for available native measurements. It contains only mathematical definitions and explicitly synthetic examples, no paper-specific experimental facts.

This convention has not been accepted. Its purpose is to expose exact component calculations, weights and consequences for user judgment. It does not predict a target rate, give a likelihood ratio or yield an annotation probability. The source's experimental reliability remains separately measured and calculated. An overall reader-assigned relevance grade is not introduced.

## Meaning of the proposed number

Let each `r_j` be a defined numerical correspondence index between the actual assayed subject/system and the target, using actual sequence, structure, mapped-site, evolutionary or system measurements. For an explicitly declared set of applicable component families and weights:

```
R_available = sum_(j observed)(w_j*r_j) / sum_(j observed)(w_j)
C_target_conventional = B_source * R_available
```

`R_available` is the weighted mean of the stated NORMALIZED CORRESPONDENCE MEASUREMENTS that are actually available. The multiplication is a proposed allocation of the source's signed evidence index to this target based on those measured relationships. It is an explicit scoring convention, not a claim that these measurements have empirically calibrated predictive power for target function.

`B_source` can be the contribution sheet's signed, bounded directional index for the actual molecular finding. Once multiplied by this uncalibrated R, the product must be labeled `conventional_correspondence_adjusted_index`; it cannot retain the interpretation of a likelihood contrast or function probability. Raw source likelihood/statistic and R components remain visible.

This permits a number when, for example, a sequence alignment and structural comparison exist but no target assay exists. It does not manufacture a correspondence when NONE is measured. A single available modality can supply a conditional index; missing modalities are identified and do not become zero or mandatory prerequisites.

## Concrete component definitions

These five component families follow the user's specified relationships. They are not five new evidence axes. They consume relevant numerical relationships supplied during A105 investigation. Only families relevant to the actual molecular inference belong in the declared configuration; for example, a statement confined to intrinsic chemistry at a stated assay condition need not assume the native organism's conditions.

| Family and exact fields | Proposed calculation | Exact meaning and limit |
|---|---|---|
| Sequence: `pair_raw_score`, `source_self_raw_score`, `target_self_raw_score`, same pairwise alignment configuration | `r_seq = 2*S_st/(S_ss+S_tt)` for the supported scoring convention described below | Fraction of the combined self-alignment score recovered by the pair alignment. This uses actual sequence score; it is not shared-function probability. |
| Structure: native `TM_source_normalized`, `TM_target_normalized`, same mapped structural comparison | `r_structure = min(TM_s,TM_t)` | Native normalized global structural correspondence in the more demanding direction. It remains a fold/geometric score; it does not assert matching chemistry. |
| Function site: `declared_sites`, `mapped_observed_sites`, `exact_match_count` or measured contact correspondences | For a completely observed declared site set, `r_site=n_exact_matches/n_declared_sites` | Fraction of specified source functional-site residues/contacts whose mapped identities are retained. Counts are factual, not numerical category grades. Equal site weighting is an explicit convention; it is not a claim that all residues have equal functional importance. |
| Evolution: `eligible_tree_replicates`, `replicates_supporting_declared_placement` | `r_evolution=n_supporting/n_eligible` | Original numerical support for the declared target placement relative to experimentally characterized references and stated alternative clades. This measures tree-placement stability, not probability of biochemical function. |
| System: measured source/target descriptor vectors `c_s,c_t` and declared reference covariance `Sigma_c` | `r_system=exp[-0.5*(c_t-c_s)^T*inverse(Sigma_c)*(c_t-c_s)]` | Continuous similarity of the measured condition vectors relative to a specified reference scale. It describes condition similarity, not the response of the enzyme to those conditions. |

The sequence normalization is specifically for a nonnegative local pairwise score with nonpositive gap penalties, positive self-substitution scores and substitution entries satisfying `s(a,b) <= [s(a,a)+s(b,b)]/2`. With each residue used at most once, `0 <= 2*S_st/(S_ss+S_tt) <= 1`. The two self scores account for compared sequence extent; do not multiply a coverage fraction again if that repeats the same normalization. An arbitrary HMM bit score or E-value is not inserted into this raw-score formula. Its native value stays recorded; use a declared supported normalization or calculate an actual compatible pairwise score. No category is substituted.

Where the available native sequence measurement is an alignment's identical-residue count rather than the required raw scores, an explicitly DIFFERENT measurement entry can use `r_identity = n_identical_aligned / max(n_source,n_target)`, with the denominator restricted to the actual supplied/known molecule spans. It measures the fraction of the longer compared span covered by identical residues. It can be chosen as the sequence family's numerical basis, not added as a second independent factor. A snippet-only match must be labeled as correspondence over those snippets, not a whole-protein value. Native scores remain retained even when a particular normalization is not yet filled.

A native bounded structure score is preferred. If only RMSD and coverage are available, a concrete OPTIONAL conversion is

```
r_structure_RMSD = coverage / [1 + (RMSD/d0)^2]
```

with `coverage = min(n_aligned_source/n_source, n_aligned_target/n_target)` and a declared `d0`. A proposed convention is d0 = 2 Å: at that RMSD the coverage contribution is halved. The scale and kernel are analyst-proposed scoring choices, NOT a native TM-score, learned activity effect or a statistical uncertainty. Report the native RMSD/counts, d0 and resulting number separately. A synthetic coverage 0.8 and RMSD 3 Å gives `0.8/[1+(3/2)^2] = 0.2461538462`. A user may prefer this declared convention or require native normalized scores; the choice is visible. No silent scaling by an unspecified “structural similarity” occurs.

The functional-site set must be defined from the proposed reaction/binding/transport mechanism or actual characterized source before looking for favorable target matches. Exact residue identity is one measurable index, not proof that a substituted residue has lost the function. If weights proportional to measured functional effects exist, use those in a separately declared weighted version with their uncertainty and assay dependence; do not invent them. Unmapped/unobserved sites remain unknown. If k of n declared sites are observed and m match, the full-set fraction is bounded by `[m/n,(m+n-k)/n]`; the missing positions are not entered as observed mismatches. An observed-sites-only fraction m/k is labeled accordingly, with coverage k/n and the full-set bounds. The same source mutation experiment cannot become independent source activity and independent site evidence without its shared measurement being retained.

The phylogenetic placement must have a definite statement, fixed reference members and explicit competing placements; “in some clade” is insufficient. The numerator uses the actual tree replicates supporting that statement. Reconstructing a tree from the same alignment creates a correlated measurement, not another independent molecular experiment. Unknown tree support is absent, not 0. A plausible horizontal-transfer explanation can be discussed separately; this convention does not invent its numerical probability.

The system descriptor set excludes the deliberately tested variable when scoring experimental comparability. Source and target temperature, pH, free substrate, metal, partners or membrane composition can matter, but nominal labels cannot be turned into fictitious concentrations. `Sigma_c` is an actual measured reference variability/covariance matrix or an explicitly proposed scale matrix whose numerical entries and units are stated. A source/reference covariance from a biologically irrelevant population would not make a sound compatibility comparison. Missing descriptors are not entered as zero differences. The index concerns only its declared observed descriptor set. Changes in enzyme response need the measured h mapping when available; this kernel is not substituted for an actual measured response ratio.

## Weights, correlated measurements and available modalities

For the example and the concrete initial convention, choose `w_seq=w_structure=w_site=w_evolution=w_system=1` among the families declared applicable. Equal weights mean equal influence of the normalized family measurements. This is a DESIGN CHOICE for review, not a fact learned from a paper and not an adopted biological assertion. Different weighting requires stating the actual new numbers and meaning; “high relevance” is not a weight.

Within a family, multiple tools/readouts share that family's fixed total weight. For example, if two applicable sequence methods are deliberately combined, `r_seq=0.5*r_method1+0.5*r_method2`, and the family still has weight 1. Reprinting one alignment or rerunning it on unchanged inputs does not add a term. Alternative normalizations of the same measurement are alternatives, not repeated evidence. Structure derived from that same sequence, site conservation derived from the same alignment, and the resulting phylogeny can remain correlated. This average makes no independence or likelihood-factorization claim; the weights expose how much correlated aspects influence the convention. No multiplication of their evidential probabilities is claimed.

With unknown families, print all of:

```
R_available = weighted mean over observed relevant families
observed_weight_fraction = sum(w_observed)/sum(w_declared_relevant)
R_full_lower = sum(w_observed*r_observed)/sum(w_declared_relevant)
R_full_upper = [sum(w_observed*r_observed)+sum(w_unknown)]/sum(w_declared_relevant)
```

The last two values are identification bounds for a hypothetical full mean when missing component values are somewhere in [0,1]. They do NOT fill missing values with 0 or 1. Under this proposed scoring convention, the CONDITIONAL point contribution uses R_available and is labeled with its observed basis and the bounds; it is not silently advertised as the fully measured result. If only sequence is observed, it can yield this conditional score; a missing structure does not veto it. If no relevant component is measured, R_available is unknown rather than a fabricated default.

These bounds make the consequence of missing inputs visible. The user may choose to use the conditional point, retain only bounds for the final annotation calculation, or choose different weights. The concrete proposal here is the conditional point plus bounds; adoption of that design is unresolved. This explicit choice is preferable to silently deleting the ordinary novel-target use case.

## Fully filled SYNTHETIC example

All values in this section are invented for arithmetic. None describe a project protein or a published source. The supplied target is complete, the source and target are different proteins, and the system descriptors refer to stated assay/native-condition comparison scope. No target activity measurement or fitted endpoint-transfer calibration is supplied.

| Component | Native/specified inputs | Calculation | Result |
|---|---|---|---:|
| Sequence score correspondence | Pair score 240; source self 300; target self 320, same valid local scoring setup | 2×240/(300+320) | 0.7741935484 |
| Structure correspondence | Native TM scores 0.90 and 0.85 in opposite normalization directions | min(0.90,0.85) | 0.8500000000 |
| Functional-site correspondence | Ten predefined sites fully observed; eight exact residue matches | 8/10 | 0.8000000000 |
| Evolutionary placement | 85 of 100 eligible tree replicates support the predefined placement | 85/100 | 0.8500000000 |
| System similarity | Differences 7 °C and 0.5 pH units; declared synthetic reference covariance diag(100 °C²,1 pH-unit²), zero cross-covariance | exp[-0.5×(7²/100+0.5²/1)] | 0.6907343306 |
| Combined available correspondence | Five equal family weights | Sum of the preceding five values / 5 | 0.7929855758 |

Assume the separate source assay has signed profile log likelihood `S_source=log(19)=2.9444389792`, giving its bounded directional source index `B_source=tanh(S_source/2)=0.9`. Then the PROPOSED CONVENTIONAL target contribution is

```
C_target_conventional = 0.9 * 0.7929855758 = 0.7136870182
```

That is a filled target evidence index for a novel target with no measured target activity and no calibrated functional mapping. It is not “71.37% probability of the annotation,” nor a likelihood ratio, nor an estimated target rate.

Now let the evolutionary measurement be unavailable, while the other four values remain observed. The missing cell stays unknown:

```
R_available = (0.7741935484+0.85+0.8+0.6907343306)/4 = 0.7787319698
observed_weight_fraction = 4/5 = 0.8
R_full ∈ [0.6229855758, 0.8229855758]
C_target_conventional = 0.9*0.7787319698 = 0.7008587728
possible full-convention contribution ∈ [0.5606870182,0.7406870182]
```

The conditional point changes because the observed measurement set changes, not because missing evolutionary support was scored zero. The hypothetical full result is an interval. For a negative source contribution the interval endpoints reverse under multiplication and must be reordered with min/max.

## Limits and how this connects to measured h

This index summarizes correspondence; its scientific predictive validity is uncalibrated. High global correspondence can coexist with a changed molecular activity, and an equal-weight average can dilute a decisive local mismatch. Those are material limitations of THIS explicit convention, not reasons to suppress the requested numerical option. The functional-site definition/weights and the aggregate's sensitivity should be shown to the user. A direct molecular contradiction is a measured result with its own sign/endpoint; it cannot be overruled by the native similarity index or hidden by selecting only favorable sources.

Where a measured condition response or calibrated molecular mapping exists, use it to transform the actual effect and its uncertainty through h. Do not also use the same observations as another correspondence multiplier. A HYBRID is possible only with declared nonoverlap: apply measured h for the supported system correction, then use a conventional R built from the remaining, uncalibrated molecular correspondence measurements. The final hybrid index has conventional score semantics, not a calibrated likelihood. The source measurement itself enters once.

The unresolved choice for the user is concrete: adopt this available-measurement convention and its visible weights/normalizations for uncalibrated relationships, revise those choices, or restrict final compilation to the identification bounds. Calibrated h remains available where supported. The proposal does not force every novel target to have experimental calibration before any numerical annotation contribution can be recorded.

## Verification and scope

`uncalibrated_arithmetic_002.json` retains every synthetic operand and checked result. The arithmetic was executed with Python's standard library. No calibration study, literature measurement, actual target relationship, production scorer/reader, library publication or scientific run was fabricated or implemented. The original proposal and source packets remain unchanged.
