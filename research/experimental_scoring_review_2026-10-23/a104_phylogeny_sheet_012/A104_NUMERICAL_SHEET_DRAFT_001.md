# A104 numerical sheet draft: evolutionary history and phylogeny

**Goal of this draft:** produce a usable, explicitly numerical account of how
the target's position among characterized functional alternatives, its branch
distance, and its agreement or explained disagreement with organism history
contribute to an annotation. The formulas below are fully specified proposals
for review. They are not paper facts, fitted coefficients, probabilities of
function, adopted scoring policy, implemented readers, or an axis-completion
claim. A105 remains first and unfinished; the ten-axis completion count is not
changed by this document.

The deliverable contains defined numerical cells, explicit compilation,
contrasting published placement examples, a completely filled synthetic
endpoint, checked arithmetic, uncertainty/missingness rules, source trace, and
exact proposed reader outputs. There is no remaining unspecified coefficient
inside this proposed calculation. There are substantial **missing source
operands**, stated below, and the proposal still needs human judgment. No
production scoring or biological computation was run.

## 1. Scope and numerical endpoint

The investigation can begin with a supplied sequence, selected record, region,
or snippets. A public identifier or candidate function is not required. A sheet
row is created when a functional possibility and its relevant characterized
alternatives emerge. Its scope is one target homologous region and one declared
reference comparison. Different proteins, nonhomologous replacements, and
different regions are not silently combined into one tree.

The proposed endpoint retains three numbers:

* `A104_positive` in [0,1]: positive phylogenetic support under the proposed scale.
* `A104_opposing` in [0,1]: placement supporting a characterized functional alternative.
* `A104_signed = A104_positive − A104_opposing` in [−1,1].

The signed number is the explicit net proposed A104 contribution. Its positive
and opposing terms must accompany it so conflicting placements cannot disappear
inside a mean. W05 would decide how this axis contributes to overall annotation
credit. No cross-axis combination is adopted here.

These are **numerical phylogenetic compatibility coordinates**, not calibrated
function probabilities. An output of 0.6 does not mean a 60% chance of the
function. No amount of branch support changes an uncharacterized reference
into an experimentally characterized one.

## 2. Numerical cells and exact inputs

Every numerical input carries `value` or `null`, `lower`/`upper` if available,
`unit`, `source_locator`, and `status` from
`observed`, `derived`, `explicit_judgment`, `synthetic`, `unreported`,
`not_measured`, `unresolved`, or `invalid`. These statuses are not numerical
grades. Reported uncertainty retains its method and coverage; a missing interval
is not a zero-width interval.

Host provenance separately identifies target material, homologous-region
boundaries, reference identities and characterization records, alignment/site
block, tree method and root, organism-tree data, taxon/copy mapping, and any
transfer-event explanation. Provenance does not itself earn points.

| Numerical cell | Type and units | Exact input and denominator | What it evaluates / missingness |
| --- | --- | --- | --- |
| `N_fg` | Positive integer, triplets | Number of predeclared pairs in R_f × R_g; R_f and R_g contain characterized references for candidate f and alternative g | Fixed comparison size; not number of organisms supporting a function. Empty set gives unknown placement. |
| `n_f,n_g,n_out,n_unresolved` | Nonnegative integer counts; sum must equal N_fg | Rooted query/reference triplets classified by their topology, defined below | Relative placement. Unknown tips or polytomies remain unresolved. |
| `P_fg` | Real [−1,1] or interval | `(n_f−n_g)/N_fg` when all triplets are resolved | Signed placement among functional references; not sequence identity. |
| `d_qf` | Nonnegative real, substitutions/site | Minimum patristic distance from query to a member of R_f in this tree | Target's nearest characterized functional reference distance. |
| `s_f` | Positive real, substitutions/site | Median over r in R_f of its nearest distance to another member of R_f | Within-function reference spacing; at least two distinct references and positive spacing required. |
| `O_f` | Real [0,1] | `min(1,s_f/d_qf)`; defined as 1 if d_qf=0 and s_f>0 | Long-distance/outlier discount. Missing units, unreported branch lengths, one reference, or zero spacing leave O_f unknown. Same definition for each O_g. |
| `N_hist` | Positive integer, rooted triplets | Number of predeclared query-anchored species triplets over matched one-copy taxon representatives | Fixed denominator for agreement with organism history. |
| `n_vertical,n_discordant,n_hist_unresolved` | Nonnegative integers; sum N_hist | Equality or inequality of the resolved rooted triplet in gene and organism trees | Measured topology correspondence, not organism occurrence count. |
| `t_contact,t_observed` | Nonnegative real hours; contact ≤ observed; observed>0 | Time within a declared potential transfer route in which donor and recipient overlap, divided by valid monitored time | Route-specific contact fraction C; ordinary shared biome labels do not populate these durations. |
| `x_dr,n_dr; x_bg,n_bg; x_ref,n_ref` | Transfer-event counts and eligible-recipient counts | Matched donor–recipient, background, and positive-control observations; r=x/n, all same exposure window and assay definition | Quantitative support for a proposed transfer mechanism, not protein functional activity. |
| `C_k` | Real [0,1] | `t_contact/t_observed` for proposed transfer event k | Contact-route component of a specific discordance explanation. |
| `M_k` | Real [0,1] | `clip((r_dr−r_bg)/(r_ref−r_bg),0,1)` with r_ref>r_bg | Mechanistic transfer compatibility relative to a stated matched positive control. Not a historical transfer probability. |
| `E_k` | Real [0,1] | `(C_k+M_k)/2` | Explicitly proposed adequacy coordinate for that transfer explanation. |
| `H` | Real [0,1] | `(n_vertical + Σ_k d_k E_k)/N_hist`, d_k defined below | Organism-history agreement, including partially explained discordances. |
| `R` | Positive integer | Number of trees in ONE declared bootstrap or posterior ensemble | Resampling/inference extent, not biological replication or extra positive evidence. |
| Native branch support | Real with method-specific scale | Exact labeled split, reported value and bootstrap denominator or posterior method | Uncertainty about that split. Kept separate from function probabilities and from point placement. |

Patristic distance is the sum of the branch lengths along the tree path. This
sheet's native distance unit is substitutions per site; another explicitly
documented branch metric requires a separately labeled version and consistent
units for all ratio operands. Branch drawing pixels and percent sequence
identity are not branch lengths. The reference spacing is recomputed within
each tree, on the same region and branch-length model as the query distance.

### Relative position among characterized alternatives

For every f-reference r and g-reference a, restrict the rooted tree to q,r,a:

* `qr|a`: q and r share a more recent ancestor than either shares with a;
  increment n_f.
* `qa|r`: increment n_g.
* `ra|q`: resolved outside placement; increment n_out. This tree separates q
  from both reference branches and does not discriminate in favor of f or g.
* Polytomy, missing tip, ambiguous copy, or unresolved root: increment
  n_unresolved, and retain the triplet's possible resolved states.

For a completely resolved comparison, `P_fg=(n_f−n_g)/N_fg`. A positive value
locates q preferentially with characterized f references, a negative value
locates it preferentially with g references. The denominator stays fixed when
a triplet becomes unresolved: dropping inconvenient triplets would inflate
placement. With u unresolved triplets and no additional constraints,

`P_fg ∈ [(n_f−n_g−u)/N_fg, (n_f−n_g+u)/N_fg]`.

For example, n_f=2, n_g=1, n_out=0, u=1, N=4 gives [0,0.5], **not** a point
estimate of 0.25. A fully resolved outside topology contributes zero because
its specified relation is nondiscriminating; missing topology is unknown.

Reference functions must be grounded in actual characterized endpoints at the
resolution being compared. Predicted annotation names do not qualify merely
because they occur inside the clade. A multifunctional reference cannot be
placed in mutually exclusive f and g sets without an explicit activity contrast;
otherwise it is not a discriminating reference for this row.

Each distinct reference contributes equally to the declared topology contrast.
This is a proposed normalization convention, not an independence claim. Extra
copies of the same reference are removed before N is defined. Related but
distinct references may still change the geometry; report the reference set
and sensitivity to its sampling. Adding papers about existing references does
not add triplets or credit.

### Outlier distance

`O_f=min(1,s_f/d_qf)` gives full distance compatibility while the target's nearest
reference is no farther away than the median nearest-neighbor spacing within
the characterized f set. If the query is twice that distance away, O_f is 0.5;
if four times away, it is 0.25. These fractions follow measured distance ratios,
not category labels. This continuous inverse-ratio choice and the onset at one
reference spacing are proposed policy conventions.

Sparse or unrepresentative characterized references can make this scale poor.
Closely clustered references can discount a remote but functional target, and
broadly spaced references can be permissive. Additional characterized
references, branch-length/model sensitivity and placement of measured functional
alternatives address those limitations. We do not claim this normalization is
empirically calibrated. Reference sampling remains visible, not replaced by a
generic relevance grade.

### Agreement with organism history and an HGT explanation

The organism tree must use information independent of the focal gene's sites.
First establish the gene-to-species and copy mapping. A naive species-triplet
comparison is invalid when unresolved paralogs or gene duplications determine
which copy is being compared. Missing taxa, unresolved roots and unresolved
orthology produce unknown cells, not vertical agreement or absence evidence.

Use all predeclared unordered pairs of other eligible species with query species
Q. For m other species, N_hist=m(m−1)/2. The gene-tree triplet and organism-tree
triplet either match, disagree, or remain unresolved. Retain `n_vertical/N_hist`
as the native-derived concordance fraction even when HGT could explain a
disagreement. The explanation never edits the observed discordance count.

For each discordant triplet, a specified reconciliation hypothesis may associate
it with transfer event k. Let d_k be the number assigned to that event. One
triplet belongs to at most one event in this calculation. If several competing
events or nontransfer explanations remain viable, calculate separate scenarios
or retain an interval. Do not add explanations or choose the most favorable
one without reporting the alternatives. A single event explaining several
triplets reuses the same E_k; these are several affected tree relations, not
independent demonstrations of transfer.

The proposed history factor is:

\[
H(T,U)=\frac{n_{\rm vertical}+\sum_k d_kE_k}{N_{\rm hist}},\qquad
E_k=\tfrac12C_k+\tfrac12M_k.
\]

Concordant triplets contribute their observed agreement. A discordant triplet
with a fully specified explanation contributes its measured or explicitly
estimated explanation coordinate. Unresolved triplets, unassigned discordances,
or unknown explanation inputs stay interval-valued. When every relation agrees,
H=1 without requiring HGT information. When all disagree, H is determined by
their specific explanations. Tree disagreement alone is not a confirmed HGT.

The one-half coefficients give contact opportunity and mechanism compatibility
equal influence on this **proposed explanation coordinate**. They are not fitted
or published coefficients and do not assert statistical independence. The mean
allows one supported aspect to provide partial explanation while the other is
unmeasured; neither aspect alone can establish the maximum. A product would be
a different, stricter policy and is not silently substituted here.

For C, the actual route/window and numerator/denominator matter: concurrent
presence in a demonstrated ingestion or shared-contact route is different from
two organisms being called marine. For M, control, background and donor–recipient
rates must use compatible recipient denominators, exposure windows and cargo/
delivery definitions. A mobile-element size, sequence identity, taxonomic label,
or number of PCR cycles cannot substitute for a transfer rate. Present-day
contact or transfer compatibility can support the proposed route; it does not
date or prove an ancient event. This limitation is separate from tree support.

Where native quantities do not exist, the user allowed a narrowly scoped
pseudo-grader for the HGT explanation. Its optional output here is **two
separate continuous estimates or intervals of the already defined C and M
coordinates**, with the route, comparison benchmark, source constraints and
assumptions attached. It cannot replace P, O, native rates, or measured tree
agreement. It cannot return an overall “plausible” grade. A point estimate
requires a stated quantitative interpretation on those scales; an unsupported
estimate is not required. If the source supplies only broad ecological prose or
no defensible numerical comparison, C/M remain unknown. The published examples
below do not invent such estimates. This optional grader is unimplemented.

## 3. Explicit compilation and uncertainty

For each gene-tree replicate T_r and one declared organism-tree scenario U,
calculate, for candidate f and each declared alternative g:

\[
s_{fg,r}=\max(P_{fg,r},0)\,O_{f,r}\,H_r,\qquad
c_{fg,r}=\max(-P_{fg,r},0)\,O_{g,r}.
\]

Then, when there are several distinct alternative functions:

\[
s_{f,r}=\min_g s_{fg,r},\quad c_{f,r}=\max_g c_{fg,r};\qquad
A^+_f=\frac1R\sum_{r=1}^{R}s_{f,r},\quad
A^-_f=\frac1R\sum_{r=1}^{R}c_{f,r},\quad
A^{\rm signed}_f=A^+_f-A^-_f.
\]

For one alternative, min/max return its single term. With no characterized
alternative, discriminatory placement and the compiled endpoint are unknown;
we do not award full credit merely for lacking a comparator. The fixed
alternative set comes from the investigated functional scope, not a required
initial annotation. Newly discovered alternatives create a revised comparison;
the old score remains an earlier result, not additional evidence.

All constants and operations have explicit proposed meanings:

* `1/N_fg` assigns equal weight to the declared reference-pair relationships.
* `s_f/d_qf` rescales query distance by within-function reference spacing.
* `1/N_hist` assigns equal weight to the declared organism-history relationships.
* `1/2` in E assigns equal influence to the two specific explanation components.
* The positive term is a product: placement, nonoutlier distance and historical
  compatibility must jointly support transfer of a characterized function.
* The opposing term uses placement with the competing function and its own
  distance scale. A plausible HGT story cannot rescue placement with a different
  characterized function, so H does not discount this contrary placement.
* min/max retain the most difficult declared functional alternative. Several
  easy or duplicated alternatives cannot dilute a strong contrary placement.
* `1/R` averages the complete calculation under one declared ensemble. More
  bootstrap replicates refine the resampling summary; they do not add evidence
  points. The outer subtraction retains opposition as well as support.

Every factor is bounded, so A+ and A− are in [0,1] and their difference is in
[−1,1]. No fitted calibration constants or unexplained weights are required to
execute this proposed sheet once its operands are supplied.

### Bootstrap, posterior, and point-tree outputs are different

Calculate the **complete expression within each replicate**, then average.
Do not multiply the means of P, O and H: their common-tree dependence matters.
Do not multiply several branch percentages as if the splits were independent.
Printed branch labels alone generally do not reconstruct the needed tree
ensemble or the joint relationships among these quantities.

With a standard bootstrap ensemble, A+/A− are resampling-average geometric
coordinates. Report the original-tree calculation separately, R, the empirical
distribution of signed replicate scores, and fractions of replicates with
positive or opposing contributions. An empirical 2.5th–97.5th percentile range
is a spread of these scores; it is not automatically a calibrated confidence
interval for annotation truth. For this draft, empirical quantile p is sorted
element `max(1,ceil(pR))`, one-based, so the calculation is explicit.

With posterior trees, use the post-burn-in equally weighted sampled trees for
the same geometric calculation, retaining chain and effective-sample-size
diagnostics. The resulting distribution is conditional on the phylogenetic
model and prior. A posterior clade probability differs from a bootstrap
resampling frequency; neither is a direct function probability. Do not pool
bootstrap and posterior trees, or standard and alternative support methods,
as interchangeable replicates. A weighted set of trees must declare its native
weights; otherwise the equally weighted ensemble interface does not apply.

If only one point tree exists, report the fully specified point-tree calculation
and `ensemble_unavailable`; do not relabel it a resampling-average endpoint or
give it a zero-width uncertainty interval. If organism-tree uncertainty is also
material, calculate separate declared organism-tree scenarios and report their
range. A joint statistical ensemble requires a documented joint sampling model;
do not invent one by pairing arbitrarily numbered gene/species bootstrap draws.

Method, root, taxon selection and evolutionary-model alternatives based on the
same alignment are sensitivity scenarios, not independent biological repeats.
If those choices yield conflicting placements, retain their individual outputs
and the envelope; do not pool them or select the largest result.

## 4. Contrasting published numerical examples

The source-specific packets preserve their inspection and full-authority-reset
records. The table below brings their already converted cells into this sheet;
it is not a claim that the source authors used this formula.

| Published comparison / native observation | Observed or extracted inputs | Derived numerical cell | Role and missing aggregate inputs |
| --- | --- | --- | --- |
| Hehemann 2010 Fig. 3, Bp1689; porphyranase vs agarase | R_f={PorA,PorB}; R_g={AgaA,AgaB}; all four rooted reference-pair comparisons favor q with f | n_f=4,n_g=0,N=4; P=+1 | Positive point-tree placement. O_f, organism-tree H and complete resampling ensemble are missing; no compiled point or ensemble A104 is reported. |
| Same published tree and same reference comparison, Bp1670 | All four comparisons favor q with g | n_f=0,n_g=4,N=4; P=−1 | Opposing point-tree placement for porphyranase. O_g and ensemble are missing; no completed A104 value. |
| Hehemann 2010, Bp1689–PorE sister feature | Bootstrap label 99; 100 resamplings | 99/100=0.99 | Split stability only. PorE was not experimentally characterized there. |
| Hehemann 2010, encompassing porphyranase clade | Bootstrap label 55; same 100 resamplings | 55/100=0.55 | Different split in the same analysis; not a second experiment or a function probability. |
| Hehemann 2012 porphyran follow-up seed | Native tree/reconciliation quantities absent from inspected main article | P, O, H and A104 unknown | Mobile-element observations do not create phylogenetic measurements; the inaccessible supplement remains uninspected. |
| Leduc 2007 ThyX replacement seed | No native tree in inspected article | P, O, H and A104 unknown | Nonorthologous functional replacement is not common-tree placement; growth measurements are not A104 inputs. |

The opposite Bp1689/Bp1670 signs are actual, contrasting published placements
with checked arithmetic, not synthetic trees. The counts are derived by this
reader from Fig. 3; the authors did not publish this four-triplet scoring table.
The 99 and 55 are published support values. The contrast between those two
split values also exposes why a high nearest-sister support cannot substitute
for function-specific comparison or whole-clade uncertainty.

The 2010/2012 porphyran observations concern overlapping biological history;
they are not independent phylogenetic replications. Absence of a usable tree in
the two seed articles is a missing-data result, not counterevidence against
their proteins' functions. For all real examples here, the full proposed
ensemble endpoint is deliberately **unknown**. The complete synthetic example
below demonstrates the finite calculation without inventing missing paper data.

## 5. Fully filled synthetic endpoint — no biological claim

Everything in this section is invented arithmetic input. The tree geometry,
counts and endpoint are calculated by `arithmetic_checks_001.py`; results are
retained in `arithmetic_results_001.json`. No target sequence, alignment, gene
tree, organism tree, experiment or scientific run was generated or analyzed.
The small synthetic ensemble illustrates the formula, not adequate empirical
sampling or calibrated uncertainty.

Candidate f and alternative g have two characterized reference labels each:
R_f={f1,f2}, R_g={g1,g2}. The five leaves represent distinct species with one
matched gene each. Branch lengths below are synthetic substitutions/site.
The organism-tree topology is U=T_minus, estimated from hypothetical independent
information. Its branch lengths are not used.

```text
T_plus  = (((q:0.6,f1:0.2):0.1,f2:0.3):0.2,(g1:0.2,g2:0.2):0.2);
T_minus = ((f1:0.2,f2:0.2):0.2,((q:0.6,g1:0.2):0.1,g2:0.1):0.2);
U       = topology(T_minus)
```

The synthetic ensemble has 10 equally weighted tree replicates: eight T_plus
and two T_minus. A single hypothetical transfer of q's gene from the f lineage
is the specified explanation scenario for T_plus's query-anchored discordances.
The four other leaves have the same pruned topology in T_plus and U, so this is
not an attempt to explain unrelated reference rearrangements with q's transfer.
T_minus agrees with U and needs no HGT explanation.

The explanation has a fully specified synthetic numerical input:

| Cell | Synthetic value and calculation |
| --- | --- |
| Contact route/window | 8 hours of donor–recipient overlap out of 10 valid monitored hours; C=8/10=0.8. |
| Recipient denominators | 100,000 eligible viable recipients in each matched transfer, background and control condition. |
| Transfer counts | x_dr=32, x_bg=2, x_ref=52 in the same exposure window. |
| Rates | r_dr=0.00032, r_bg=0.00002, r_ref=0.00052 per eligible recipient. |
| Mechanism coordinate | M=(0.00032−0.00002)/(0.00052−0.00002)=30/50=0.6. |
| Explanation coordinate | E=(0.8+0.6)/2=0.7. |

These stipulated values are exact inputs for the arithmetic fixture. They do
not purport to have sampling-error estimates or historical-transfer validity.
An actual application would retain the measured count/rate uncertainty and the
contact-window limitations rather than inherit the fixture's exactness.

| Complete numerical cell | T_plus | T_minus |
| --- | ---: | ---: |
| n_f / n_g / n_out / n_unresolved | 4 / 0 / 0 / 0 | 0 / 4 / 0 / 0 |
| N_fg | 4 | 4 |
| P_fg | +1 | −1 |
| Candidate spacing s_f | 0.6 | 0.4 |
| Query distance d_qf | 0.8 | 1.3 |
| O_f | 0.6/0.8=0.75 | 0.4/1.3=4/13≈0.307692 |
| Alternative spacing s_g | 0.4 | 0.4 |
| Query distance d_qg | 1.3 | 0.8 |
| O_g | 4/13≈0.307692 | 0.4/0.8=0.5 |
| N_hist, from four other species | 4×3/2=6 | 6 |
| n_vertical / n_discordant / n_hist_unresolved | 0 / 6 / 0 | 6 / 0 / 0 |
| Native concordance fraction | 0/6=0 | 6/6=1 |
| Explained discordances | d_1=6, E_1=0.7 | No discordances; empty sum |
| H | (0+6×0.7)/6=0.7 | (6+0)/6=1 |
| Positive term | 1×0.75×0.7=0.525 | 0 |
| Opposing term | 0 | 1×0.5=0.5 |
| Signed point-tree term | +0.525 | −0.5 |
| Ensemble multiplicity | 8 | 2 |

The complete proposed endpoint is therefore:

\[
A^+=(8\times0.525+2\times0)/10=0.42,\qquad
A^-=(8\times0+2\times0.5)/10=0.10,\qquad
A^{\rm signed}=0.42-0.10=\mathbf{0.32}.
\]

The signed replicate-score empirical 2.5th–97.5th percentile range under the
defined order-statistic rule is [−0.5,0.525]. Positive-score and opposing-score
fractions are respectively 8/10 and 2/10, which describe the stipulated tree
ensemble and are not probabilities that f or g is true. The opposing two trees
remain visible despite the positive net.

Holding T_plus and its distances fixed shows the intended behavior:

| History input scenario | H | T_plus positive term |
| --- | ---: | ---: |
| Gene and organism triplets all agree | 1 | 0.75 |
| Six discordances with the fully specified E=0.7 explanation above | 0.7 | 0.525 |
| Both explanation coordinates unmeasured | Unknown [0,1] | Unknown [0,0.75] |
| Only C=0.8 known; M unmeasured | E in [0.4,0.9] | [0.30,0.675] |

With explanation entirely unmeasured for the eight T_plus replicates, the same
ensemble's signed endpoint is an interval [−0.10,0.50], not the earlier 0.32
point and not zero. The unchanged negative placements are still retained.

## 6. Missingness, nondetection and dependence

Unknown values never become category grades. Propagate component intervals
through the stated monotone products, min/max and mean; output conservative
bounds and `value=null` when a point is unidentified. Preserve shared operand
identity so a reused E or tree is not independently varied several times.
When feasible joint completions are known, use them to tighten the bounds;
otherwise label the interval conservative. An exactly zero multiplier can
make its product known even when another factor is unknown, but this does not
change the unknown factor itself.

| Situation | Required numerical treatment |
| --- | --- |
| No usable tree | P, O and the endpoint remain unknown; no zero score is assigned for missing analysis. The broad signed range is [−1,1]. |
| Unresolved root, polytomy, missing leaf or copy mapping | Retain the fixed denominator and interval over possible triplet states. Do not quietly remove the triplet or call it an outside placement. |
| No branch lengths, unknown units, or zero within-reference spacing | O unknown. Do not substitute identity, species distance, figure pixels or a guessed branch-length scale. |
| No independent organism tree | H unknown. Taxonomic names alone cannot fill a tree-concordance ratio. |
| Discordance without a quantitative explanation | Its contribution is unknown [0,1], not automatically zero or automatically HGT. Report competing reconciliation hypotheses. |
| No contact observed | Preserve monitored duration and detection sensitivity; no observed contact is not proof of no historical contact. Only the actual declared route/window contributes to C. |
| No transfer event detected | Preserve count, denominator and detection bound. A censored or insensitive assay does not justify M=0 with zero uncertainty. If only an upper bound exists, propagate an interval. |
| Positive-control rate indistinguishable from background | M undefined/unknown, because its normalization denominator is not established. No divide-by-zero repair or default grade. |
| Homolog not found | Preserve search scope and sensitivity separately. Nondetection is not a leaf absence in an evolutionary tree, nor evidence that a function was lost. |
| Same alignment in several papers or tools | One evidence block; alternative methods are sensitivity scenarios. No sum over publications, branch labels, tool names or repeated downloads. |
| Bootstrap trees or posterior samples | Uncertainty samples, not independent functional experiments. Average complete calculations once; preserve the support method. |
| Several domains with different histories | Separate region-specific sheets and report conflict. No automatic whole-protein average; assigning one region's history to the whole protein would exceed the row's defined scope. |
| Contradictory independent gene-tree studies | Retain independent data scopes and separate outputs plus their envelope. Do not add their positive scores or average incompatible target regions. Whole-protein integration is not defined by this region-specific draft. |
| Molecular characterization reused to label references | Link the original assay identity; it anchors the function labels but is not rescored as an additional A104 experiment. |
| Gene neighborhood, partner expression or ecology also used elsewhere | Retain shared evidence identity. Here only quantities needed for a specified tree/history question may enter. No generic neighborhood, partner or ecology bonus is added. |

Multiple domain histories and genuinely incompatible target scopes cannot be
made into a scientifically meaningful single scalar by declaring a convenience
weight. This draft supplies a complete calculation for its explicit single
homologous-region scope. A request for a whole-protein aggregate across such
histories is a separate unresolved scientific integration problem, and this
sheet must return `scope_not_combinable`, not invent that aggregate.

## 7. Source-to-cell trace and complements

| Inspected source / source record | Cells it can populate here | What remains unknown; exact complement |
| --- | --- | --- |
| Hehemann 2010, Fig. 3 and full Methods; `PAPER03_PORPHYRAN_2010_PHYLOGENY_001.md` | Rooted topology/reference comparisons; P=+1 and −1; branch labels 99 and 55; resampling denominator 100; tree method | Machine-readable branch lengths and bootstrap trees for O and the full ensemble; independently estimated organism tree and gene/species mapping for H. |
| Same paper, biochemical Results and figure labels | Which functional references were actually characterized; PorE exclusion | Direct PorE substrate-specific activity would resolve whether the high-support nearest sister is a valid functional anchor. Broader characterized alternatives would test reference-sampling dependence. |
| Hehemann 2012 main article; `PAPER01_PORPHYRAN_2012_BOUNDARY_001.md` | Context/provenance for a possible transfer explanation, not numerical P/O/H | Quantitative route contact and compatible transfer measurements, or explicitly justified bounded judgments, for C/M; no inferred transfer rate from PCR effort. Supplement remains uninspected. |
| Leduc 2007 full article; `PAPER02_THYX_2007_BOUNDARY_001.md` | Missing-tree and nonorthologous-replacement boundary | A phylogenetic analysis appropriate to each actual homologous family; replacement phenotypes cannot supply that analysis. |
| Newly invented trees and counts in this document | Every calculation, including the proposed complete endpoint | Mathematical illustration only. Biological calibration and reader implementation are not established. |
| User's A104 direction and corrected numerical template | Need for tree placement, organism-history comparison, outlier and HGT treatment; numerical combination | The particular inverse-distance scale, equal explanation weighting and conservative alternative comparison need review; their numerical meanings are already fixed in this draft. |

Full citations and retained source bytes are in the individual paper packets.
The additional 2010 primary was announced and authorized before inspection.
All three source inspections were followed by a full authority reset before
conversion, recorded in `authority_reset_paper01_001.json`,
`authority_reset_paper02_001.json`, and `authority_reset_paper03_001.json`.

## 8. Exact future-reader boundaries — all unimplemented

This section specifies functions targeted to these cells. It is not executable
reader code, an investigation prompt, or a generic grader to be retrofitted
later. Literature and datasets may supply the same typed operands. Manual
extraction must keep source locations and distinguish printed values from
derived counts.

| Proposed function | Exact required input fields | Exact output fields and deterministic responsibility |
| --- | --- | --- |
| `read_tree_bundle` | `target_material_ref, region, tree_bytes_or_figure_locator, tip_map, root_spec, branch_unit, method, ensemble_kind, original_tree, replicate_trees, replicate_weights, support_labels` | `tree_bundle_status, rooted_topologies, branch_lengths, branch_unit, ensemble_kind, R, native_split_support[{split_taxa,value,scale,method,denominator}], missing_fields`; parse tree files deterministically, with separately flagged manual figure extraction. |
| `read_characterized_references` | `reference_id, sequence_or_tip_ref, functional_endpoint, assayed_subject, characterization_source, shared_experiment_id, candidate_or_alternative_scope` | Unique `R_f` and each `R_g`, reference-function mappings and excluded nondiscriminating or prediction-only references; no numeric relevance grade. |
| `calculate_placement` | `rooted_topology, q_tip, R_f, R_g, fixed_triplet_manifest` | Per-triplet topology states; `N_fg,n_f,n_g,n_out,n_unresolved,P_fg,P_bounds`; validates exact count sum and prevents missing-denominator shrinkage. |
| `calculate_tree_distances` | `branch_lengths, branch_unit, q_tip, R_f, R_g` | All query/reference and reference/reference distances; `d_qf,s_f,O_f` and each alternative's corresponding cells; invalid/unknown reasons. |
| `compare_organism_history` | `gene_tree, independent_organism_tree, root_specs, species_copy_map, fixed_history_triplet_manifest, reconciliation_scenarios` | `N_hist,n_vertical,n_discordant,n_hist_unresolved`, per-triplet comparison, `event_assignment` and each `d_k`; no inference from genome occurrence counts. |
| `read_transfer_explanation_inputs` | For each `event_id`: `donor_lineage, recipient_lineage, route, time_window, t_contact,t_observed`, assay/window/cargo identifiers and `x_dr,n_dr,x_bg,n_bg,x_ref,n_ref`, bounds, detection limits, shared-source identity | Native C/M operands and measurement uncertainty; incompatible comparison flags; missing values remain null. |
| `grade_missing_transfer_coordinate` | Specific event, unavailable coordinate C or M, its defined scale/benchmark, source evidence and constraints | Optional `{coordinate,point_or_null,lower,upper,quantitative_interpretation,assumptions,source_refs,status:explicit_judgment}`; cannot output an overall function/HGT score or override native measurements. Unjustifiable estimates return null with [0,1]. |
| `compile_A104_region` | All P/O/history/event cells for each tree, fixed function alternatives, one ensemble method and weighting, scope and shared-dependency map | Per-tree `H,s_fg,c_fg,s_f,c_f`; `A104_positive,A104_opposing,A104_signed` or intervals, original-tree endpoint, defined empirical quantiles and sign fractions, missing-operand list, sensitivity scenarios, `scope_not_combinable` when applicable. No other-axis or whole-annotation credit wiring. |

The interfaces reject inconsistent counts, overlapping incompatible reference
roles, undefined control denominators, silent branch-unit conversion, and
double-counted aliases as malformed records. That is validation of numerical
meaning, not a scientific approval gate, extra episode or stopping criterion.

What is actually implemented here is only a small research arithmetic fixture.
It checks the published count arithmetic, synthetic rooted-triplet counts and
patristic distances, the complete synthetic endpoint, explicit missingness
examples and bounded outputs. It reads no biological data and implements none
of the future reader bindings above.

## 9. Review status and finite outstanding work

Within the declared region/ensemble scope, all component calculations and
coefficients are explicit; no “future unknown weight” is needed to reproduce
the synthetic endpoint. The real examples have missing branch-length,
organism-tree, ensemble and explanation operands, so their endpoint remains
unknown. Those are data gaps, not invented zero scores.

The inverse-distance normalization, equal contact/mechanism weighting, and
min/max treatment of alternatives are concrete policy proposals for user
judgment. They are not claimed to be validated by the three papers. A general
whole-protein score across incompatible domain histories is deliberately not
supplied by a single-region sheet. Reader implementation, real dataset
population, calibration, reviewed prompt text, and W05 integration remain
unimplemented and outside this worker's authorization. This draft therefore
does not complete A104 or alter the fixed ten-axis checklist.
