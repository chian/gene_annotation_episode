# A108: numerical organism/sample/environment compatibility sheet — research draft 001

This is one concrete proposed sheet for the A108 contribution of a possible
function. It measures **the fraction of the declared sample opportunities whose
organism state, physical access and local environment jointly satisfy the
function's evidenced contextual requirements**. It is not the probability that
the annotation is correct. A large result means the contextual requirements fit
that sample; it does not establish molecular identity, activity or physiological
causation. The proposal is not adopted or implemented, and no axis is marked
complete.

User definition, verbatim:

> (8) This is a pseudo-grader/literature reading exercise - does the proposed function seem plausible given what we know about the sample and the organism? Does it make sense with the general clade of the organism (if we know that).

## 1. What is scored, and what remains separate

Start from the supplied sequence, selected file record or snippets and whatever
organism/sample context they actually contain. No candidate or public name is
needed initially. As possible functions emerge, each candidate gets a fixed
identity and explicit scope. Its measurements can improve without creating a
new candidate for every revision. No target sequence or context is invented
from a cited protein's name.

Each candidate has only the contextual requirements relevant to its proposed
function: for example local substrate exposure and oxygen compatibility for a
particular respiratory role. Another function may require a particular tissue,
life stage or compartment and have no relevant oxygen constraint. This is not
a mandatory environmental checklist. The requirements and their physical
meanings are part of the sheet, not a replacement investigation prompt.

Clade information can establish which organism trait or life state is relevant
and which environmental measurements can transfer. A clade name alone supplies
no numerical frequency, branch support, phylogenetic distance or probability.
Actual tree placement/HGT remains A104. If only a general clade description is
known, that contextual premise stays unresolved until an explicit organism-trait
or ecological relationship can be stated. A categorical observation such as a
measured physical separation can constrain access; a free-form claim that a
function is 'typical' cannot become an overall score. This draft uses no
unmeasured overall judgment multiplier. The user's narrow judgment exception
is preserved but not needed to fill these worked components.

| Other axis | Boundary and shared-use rule |
|---|---|
| A101/A102 | Target-to-studied-subject correspondence is referenced once, with native results and limits. No extra homology multiplier is invented here. |
| A103 | Gene arrangement is not environmental access. |
| A104 | No phylogenetic score is inferred from organism names or clade plausibility. |
| A105 | An activity/affinity measurement can define an operating requirement. It remains one original assay and receives no second assay contribution in A108. |
| A106 | Perturbation/restoration and organism-performance effects are not added as A108 proof. |
| A107 | Partner presence/co-expression remains separate from physical opportunity to encounter the environment. |
| A110 | Chemical balance, stoichiometry, pathway completion and energetic sufficiency remain separate. |
| A111 | Experimental structures, occupancy and contacts remain separate. |

A108 is conditional on its referenced operating requirements and transfer
relationship. The final multi-axis consumer must retain those dependencies,
rather than treating this output and the A105 input as independent replications.
No A105 quality penalty, recovery correction or subject-transfer correction is
applied a second time in this sheet. W05 owns the final annotation-credit wiring.

## 2. Native observation cells

The population denominator must be stated before calculating a fraction. A unit
can be an independently sampled specimen, or an explicitly measured amount of
sample time/volume. Repeated LC-MS injections and repeated readings of one vial
are technical replicates, not additional environmental opportunities. Unequal
sampling requires recorded design weights; otherwise this draft defaults to
equal weights among independent units from the declared sample frame. It never
weights a source by publication count or reputation.

| Cell | Type and unit | Definition / source of input |
|---|---|---|
| `candidate_id`, `target_material_ref` | fixed references | Emerged function and supplied target material; separate from its revisions |
| `population_scope` | structured fields | Organism/strain if known; compartment; life/infection state; location; time window; specified environmental population |
| `unit_id`, `cluster_id` | references | One unique sampling unit and its independent collection unit |
| `weight` | positive number, common declared unit | 1 for equal-probability independent samples; otherwise actual time/volume or documented inverse-inclusion weight, never a relevance grade |
| `requirement_id` | reference | One necessary contextual condition for the stated function, with declared meaning and source |
| `observed_value` | number or interval | Native local environmental/organism-state observation, with native units and support bounds |
| `observation_status` | controlled enumeration | `measured`, `left_censored`, `right_censored`, `interval_censored`, `missing`, `not_applicable`, `conflicting` |
| `blank`, `recovery` | numeric values/intervals | Procedural background and measured matrix recovery, if correction is needed |
| `correction_state` | enumeration | `raw`, `source_corrected`, `derived_here`; records prohibit repeating the same correction |
| `local_mapping` | identity or measured numeric transformation | Bulk-to-local conversion if supported; absence means unknown, not identity |
| `supported_domain` | numerical intervals or measured discrete state sets | Conditions where the referenced endpoint is supported, including conditioning variables |
| `contradicted_domain` | numerical intervals or measured discrete state sets | Conditions where that endpoint fails with adequate detection; absence of a test is not failure |
| `domain_uncertainty` | bounds / model inputs | Reported threshold/range uncertainty and interpolation assumptions |
| `source_location`, `dependency_ids` | references | Exact table/figure/row and shared original sample/assay identifiers |

For a concentration already on a calibrated concentration scale but requiring
procedural-blank and matrix-recovery correction, the proposed deterministic
conversion is

\[
x=(y-b)/r,
\]

where y is apparent concentration, b is the matched procedural blank in the
same unit, and r=(measured spike increment)/(known spike concentration) is the
dimensionless recovery. For nonnegative concentration bounds:

\[
x^- = \max(0,(y^- - b^+)/r^+),\quad
x^+ = \max(0,(y^+ - b^-)/r^-),\qquad 0<r^-\le r^+.
\]

The bounds require the stated linear recovery model; unknown recovery does not
default to 1. A measurement already corrected in the publication is copied,
not divided again. A nondetect reports a concentration interval derived from
the detection limit and calibration, never a measured zero. Matrix effects,
cross-reactants and sample dilution enter the physical measurement model or
its uncertainty, not an intuitive reliability multiplier.

## 3. Numerical components and exact combination

Let i identify a sample opportunity, j a relevant contextual requirement,
w_i its declared nonnegative design weight, and W=Σ_i w_i>0 the full fixed
population denominator. Let B_ij be the set of plausible corrected local
values for that observation. A point is a singleton set. Let D+_j and D-_j
be disjoint supported and contradicted operating sets for the exact stated
endpoint and matched background. Uncertainty in either the observation or the
operating domain is included in B/domain bounds before membership is resolved.

\[
\ell_{ij}=1\{B_{ij}\subseteq D^+_j\},\qquad
u_{ij}=1-1\{B_{ij}\subseteq D^-_j\}.
\]

Thus a firmly compatible measurement has [ell,u]=[1,1], a measured incompatible
one [0,0], and unresolved data [0,1]. These are logical bounds on a numerical
event, not an ordinal good/moderate/bad ladder. If an uncertainty interval
spans both domains, it remains unresolved. If contradictory reports put the
same condition in both domains, retain the conflict and use [0,1] until the
conditions or measurements are reconciled. Irrelevant requirements are absent
from this candidate's set; missing relevant ones remain in it as [0,1].

For every unit, calculate the joint bounds:

\[
L_i=\prod_j\ell_{ij},\qquad U_i=\prod_j u_{ij}.
\]

The products express simultaneous necessary conditions on the **same unit**.
They do not assume independent requirements. Do not multiply marginal sample
fractions computed on unpaired specimens. Where only marginal fractions p_j
are known, use the general bounds

\[
\max(0,\sum_j p_j-(J-1))\le P(\text{all requirements})\le\min_j p_j,
\]

and preserve the missing pairing. If marginal fractions also have bounds,
insert their lower values on the left and upper values on the right.

The candidate's proposed A108 numerical contribution and uncertainty are:

\[
C_{108}^{-}=\frac{\sum_i w_i L_i}{W},\quad
C_{108}^{+}=\frac{\sum_i w_i U_i}{W},\quad
S_{108}^{-}=100C_{108}^{-},\quad S_{108}^{+}=100C_{108}^{+}.
\]

The percent scale is a proposed display/credit scale, not a biological threshold.
Use C^- as the proposed conservative annotation-support component, accompanied
by C^+ and missingness. This is an explicit bounded proposal, not a request for
the caller to invent an aggregation. All-missing input produces `point=null`,
bounds [0,1], supported mass 0 and unresolved mass 1; it does not claim biological
incompatibility. For partial data, the lower result is an evidenced lower
fraction, not a pessimistic point estimate of truth. The three disjoint masses
are supported=C^-, unresolved=C^+−C^-, and contradicted=1−C^+; they sum to 1.

For a readable fully observed sheet with three relevant components, access A,
substrate exposure E and oxygen condition O, display:

\[
q_A=\frac{W_A}{W},\quad q_{E|A}=\frac{W_{AE}}{W_A},\quad
q_{O|AE}=\frac{W_{AEO}}{W_{AE}},\qquad
C_{108}=q_Aq_{E|A}q_{O|AE}=\frac{W_{AEO}}{W}.
\]

This conditional decomposition explicitly combines the individual components.
It is not a mean of condition grades. If an intermediate denominator is zero,
that conditional cell is null; calculate the joint result directly as W_joint/W.
The final result is invariant to the display order of the requirements.

## 4. Complete synthetic end-to-end example

**Every input in this section is invented for arithmetic verification. None is
a measurement from either paper, from ybhP, or from a new experiment.** An unnamed
sequence target has acquired a candidate function requiring access to an
extracellular electron acceptor in a low-oxygen microhabitat. There are ten
independent, equally sampled microhabitats in a defined specimen frame, one
paired observation each. The physical access observation records whether the
organism and the acceptor occupy connected accessible space. It does not test
for a required protein partner.

For this synthetic endpoint, a separate characterized-function record supplies
a supported domain 2.5–10 mM acceptor and 0–1% O2 by gas volume; observed failures
supply the contrary domains 0–<2.5 mM and >1–10% O2 within the tested ranges.
Other background conditions match and remain fixed. These synthetic numerical
boundaries are specific to that endpoint. They are not adopted ecological cutoffs,
and the 2.5 mM number is not a reinterpretation of the paper's sufficient-dose
result as a real failure threshold.

| Unit | w | Physical access A | Local acceptor E, mM | O2, % v/v | A and E | A and E and O |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 5 | 0.5 | 1 | 1 |
| 2 | 1 | 1 | 4 | 0.3 | 1 | 1 |
| 3 | 1 | 1 | 2 | 0.4 | 0 | 0 |
| 4 | 1 | 1 | 5 | 5.0 | 1 | 0 |
| 5 | 1 | 1 | 3 | 0.5 | 1 | 1 |
| 6 | 1 | 1 | 1 | 0.5 | 0 | 0 |
| 7 | 1 | 1 | 6 | 0.6 | 1 | 1 |
| 8 | 1 | 1 | 9 | 0.9 | 1 | 1 |
| 9 | 1 | 0 | 5 | 0.5 | 0 | 0 |
| 10 | 1 | 0 | 4 | 0.4 | 0 | 0 |

Unit 1 illustrates the concentration conversion: apparent concentration y=4.2 mM,
procedural blank b=0.2 mM and recovery r=0.8 give x=(4.2−0.2)/0.8=5.0 mM.
With synthetic bounds y=[4.1,4.3], b=[0.19,0.21], r=[0.78,0.82],
x=[3.89/0.82,4.11/0.78]=[4.743902,5.269231] mM, wholly within the supported
concentration domain. This uncertainty therefore does not change membership.

The numerical sheet is:

| Component | Numerator / denominator | Value | Meaning |
|---|---:|---:|---|
| Physical access | 8 / 10 | 0.8 | Fraction of sampled opportunities physically accessible |
| Compatible concentration conditional on access | 6 / 8 | 0.75 | Fraction of accessible units in the supported concentration domain |
| Compatible oxygen conditional on both | 5 / 6 | 0.833333 | Fraction also compatible with the oxygen requirement |
| Joint candidate A108 contribution | 0.8×0.75×(5/6)=5/10 | 0.5 | Joint supported environmental opportunity fraction |
| Proposed display scale | 100×0.5 | 50 | A108 compatibility points; not 50% probability of correct annotation |

With all memberships resolved, [S^-,S^+]=[50,50], supported mass=.5,
unresolved mass=0 and contradicted mass=.5. Sampling uncertainty remains even
when analytical membership uncertainty is zero. For the stipulated independent,
equal-probability draws, a distribution-free proposed 95% bound uses
epsilon=sqrt(ln(2/alpha)/(2n)), alpha=.05, n=10. This gives epsilon=0.429469,
and [max(0,.5−epsilon),min(1,.5+epsilon)]=[0.070531,0.929469]. It is deliberately
wide for ten samples. Alpha is a reporting parameter, not an ecological threshold.
If the ten units were a census of the stated finite frame, only that frame's
descriptive result is claimed. If they are correlated subsamples, n=10 is invalid;
use independent cluster averages with equal cluster weights or retain the
sampling interval as unknown. No independent-sample claim is made for the papers.

## 5. Missingness, nondetection and contradiction checks

| Synthetic change from the base example | Defined outcome |
|---|---|
| Unit 3 concentration interval [2.4,2.6] mM | It straddles the boundary: joint lower 5/10, upper 6/10; display [50,60]. |
| Unit 6 concentration is a validated nondetect <0.5 mM | Entire interval [0,0.5) is in the demonstrated failure domain: remains contradictory, not missing. |
| Unit 6 nondetect has LOD 5 mM | Interval [0,5) spans outcomes: lower 5/10, upper 6/10. |
| Unit 2 oxygen readings disagree, 0.3% and 5%, without a resolved reason | Preserve both; use unresolved membership: lower 4/10, upper 5/10. Do not average away the conflict. |
| Unit 2's operating domain comes from an unmatched background with no transfer model | [0,1] for that contextual comparison, not an arbitrary 0.5 penalty. |
| All relevant inputs missing | point=null, bounds [0,1], no-data status; no claim of measured absence. |
| Duplicate report of Unit 1 or three technical injections | Same unique sampling unit and weight; score stays 50. |
| Unit 3 is observed outside a supported domain but no negative test covers it | Unknown, not contradiction; lower 50, upper 60. |

## 6. Contrasting publication-filled cells and exact limits

| Case | Source-filled numerical inputs | Derived result | Score use and limitation |
|---|---|---|---|
| Huc, Grinter 2023, Fig. 1 and gas Methods | Atmospheric benchmark 530 ppbv; Huc residual <~40 ppbv; tested start 3 ppmv=3000 ppbv | benchmark/residual bound >~13.25 | Under the declared monotone-depletion interpolation, 530 lies in [40,3000] ppbv. A **conditional single-benchmark** compatibility component is 1 (100 points), not a target-habitat score. |
| Huc versus E. coli Hyd1 in the same paper | Hyd1 cessation ~4 ppmv=4000 ppbv | 530/4000≈0.1325 | Diagnostic mismatch for the NBT/N2 comparison; cannot claim a matched air comparison with Huc/menadione. Membership for an ambient-air claim remains unresolved. |
| Salmonella/mouse tetrathionate, Winter 2010 Fig. 1E | Plot-derived geometric mean ~3.3 mM, visual reading range 3.2–3.4; separate broth test 2.5 mM sufficient | margin≈1.32, display-reading range [1.28,1.36] | Numerical concentration compatibility clue. Single sufficient dose does not establish a supported interval; no local mapping or individual denominator supports a full A108 point score. |
| Respiration-competent infection, same Fig. 1E | Residual not accumulated/detected; LOD unavailable | concentration and margin unresolved | A consuming system can have low residual despite production. Do not replace with 0 or conclude unavailable substrate. |

The Huc background benchmark is reported context, not a new atmospheric survey.
The tetrathionate value is explicitly a graph-derived approximation, not a
precise source table value. Reported errors, analyst digitization uncertainty
and assumed operating models remain distinct. A complete real target score
cannot be supplied from these papers alone; this is why the fully populated
synthetic example is explicit. No missing scientific operand is invented.

## 7. Component-to-source trace, replication and use limits

| Component or restriction | Inspected source | What it supplies / does not supply |
|---|---|---|
| Exposure versus operating range | Huc primary, Main; Fig. 1 caption; gas chromatography Methods | Quantitative gas benchmark, depleted gas bound, initial conditions; not sampled target ecology |
| Physical local versus bulk access | Winter primary, tetrathionate availability Results; Fig. 1E; Methods Summary | Cecal bulk concentration and infection state; no quantitative local-access fraction |
| Context comparability | Huc gas Methods and strain/purification Methods | Acceptor, gas, enzyme concentration and production-strain differences; no global relevance grade |
| Effect isolation and residual interpretation | Huc no-enzyme controls; Winter Fig. 1E/Results | Background control and consumption qualification; no second A105/A106 contribution |
| Independent-unit definition | Huc Statistics and reproducibility; Winter Fig. 1 caption | Four Huc preparations vs technical triplicates; n≥3 mouse units but exact group n/raw values absent |
| Missingness and detection | Huc <40 ppbv; Winter nondetection with unknown numerical LOD | Censoring bounds and limits, not manufactured zero concentrations |
| Joint fractions, calibration example, uncertainty formula | Explicit research proposal and synthetic inputs in sections 2–5 | Proposed arithmetic, never a formula attributed to either publication |

Independent replication improves estimates of the operating domain or exposure
distribution; it is not an extra multiplier increasing a compatibility fraction
above one. Reports of the same physical sample share a dependency ID. Multiple
modalities on that sample may narrow an interval but cannot add denominator
units. Independent studies of different habitats remain separate strata with
their actual sampling frame; do not average them as if their population weights
were known. If only two different habitat descriptions exist, report two scoped
results until mixture proportions are available. This is a data limitation,
not a stopping or approval rule.

Essential real-input gaps are the target's sample frame, paired local exposures,
physical-access measurements, a transferable supported/contradicted operating
domain and measurement uncertainties. Mathematical operations for supplied
inputs are completely specified here. Biological validity of the proposed
fraction as an A108 annotation-support scale, domain interpolation and the
display choice require user review. Prompt construction, reader implementation,
empirical calibration of score meaning and production W05 consumption remain
unimplemented and unverified.
