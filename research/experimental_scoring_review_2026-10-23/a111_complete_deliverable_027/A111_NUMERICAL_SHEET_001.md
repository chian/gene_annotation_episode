# A111 — one current numerical research sheet

**Status:** complete finite research proposal for the calculations specified here; every transformation, weight and normalization is proposed, not user-approved policy. This document is the current, self-contained mathematical specification in this directory. Earlier A111 files remain historical research. No production scorer, reader, prompt, credit function, saved observation, checklist or completion count is changed.

The quantity is **documented structural evidence for a target's specified molecular features**, including experiments on another molecule joined through explicit molecular correspondence. It is an index, not a probability that an annotation is correct. X-ray local RSCC, cryo-EM local Q, and assigned NMR proton-distance restraints have finite defined branches. No general XL-MS, tomography or solution-stoichiometry fit conversion is claimed.

The investigation may start with supplied sequence, a selected file record/region, or snippets. Candidate functions can emerge later. A name or candidate annotation is not an input prerequisite. The investigation prompt, this numerical sheet, and the future targeted functions that populate it are three distinct things. This work specifies the latter two responsibilities without implementing a reader or changing a prompt. W05 remains responsible for any production connection to annotation credit.

## Fillable numerical cells

One row concerns one actual source observation, a fixed physical question, a source-to-target correspondence, and a complete current model/assignment scenario. Keep the actual measured molecule and target separate. Conditions, constructs, endpoint identities, provenance and dependencies accompany the numbers; they are not confidence grades.

| Cell | Exact inputs, denominator and proposed calculation | Units / numerical meaning |
| --- | --- | --- |
| `q` | Refined/measured occupancy fraction, or observed eligible objects / all eligible objects under a stated sampling design. A selected deposited state may instead use the explicitly **conditional** definition q=1. | [0,1]. Fraction represented by the observation. Fixed deposited occupancy is a model parameter, not measured population occupancy or its probability. |
| `D_X` | Nonempty fixed required local endpoint panel; `D=min_j(max(0,RSCC_j)^2)`. Native RSCC must be in [−1,1]. | [0,1] local map/model agreement index. Squaring and weakest-endpoint selection are proposals. |
| `D_EM` | Same calculation using actual local `Q_j` at one declared atom or residue granularity: `D=min_j(max(0,Q_j)^2)`. Native Q must be in [−1,1]. | [0,1] local resolvability index. Global resolution/FSC, particle count and residue-to-atom relabeling do not fill this panel. |
| `D_NMR` | Fixed J>0 distinct experimental NOE restraints. Native allowed interval [L_j,U_j] Å, effective modeled distance d_j Å. `v_j=max(0,L_j−d_j,d_j−U_j)`; `s_j=exp(−v_j²/(2τ²))`; `D=Σs_j/J`, with proposed τ=.50 Å. | [0,1] local restraint agreement conditional on assignments and model. τ is a scoring tolerance, not a measured SD. Restraints used for fitting are not held-out validation. |
| `G+`, `G−` | Fixed J_G>0 physical constraints. For each measured quantity declare a supporting set S_j+ and an incompatible set S_j− with empty intersection; an allowed gap may remain. `G+=Σ1[x_j∈S_j+]/J_G`, `G−=Σ1[x_j∈S_j−]/J_G`. A genuinely fractional predicate requires its actual numerator and eligible denominator. | Fractions in [0,1], with G++G−≤1 for this paired panel. Distances Å, angles degrees, counts/subunits, areas Å² or exact chemical-role identities remain native cells. A failed positive predicate is not automatically opposition; it must meet the declared incompatible predicate. Unknown quantities remain unknown. |
| `T` | K>0 required molecular roles, with p_k=1 for an explicitly met role predicate, 0 for an established mismatch, unknown otherwise. `T=Σp_k/K`; if c preserved, d incompatible, u unresolved, `T∈[c/K,(c+u)/K]`, K=c+d+u. | [0,1] fraction of the required feature's molecular roles preserved in the target. This is not a generic homology/relevance grade. |
| `C` | Fixed n relevant nuisance variables excluding the deliberately changed variable. Continuous variables: `c_k=exp(−(x_A−x_B)²/(2τ_k²))`, τ_k>0 in the same units. Construct comparison: `c_k=matching_positions/union_positions`, excluding the intentional change. `C=(Πc_k)^(1/n)`. | [0,1] experimental comparability. Each τ has a measurement-derived or explicitly proposed basis. A genuinely single-state statement with no between-condition comparison has C=1 by definition, conditional on that state. |
| `I` | Y≥0 observed signal/effect magnitude and measured upper bound B≥0 on contributions other than the intended component/change, in the **same** units. `I=max(0,1−B/Y)` for Y>0; I=0 for Y=0. | [0,1] conservative attributable fraction under that bound. Comparability does not supply B. A purely within-model atom-geometry statement can condition on the atom assignment and define B=0; broader identity or causal claims cannot inherit that condition silently. |
| `N` | For calibrated nondetection only: explicitly entailed minimum occupancy q_req>0 and calibrated occupancy upper bound q_U under the interrogated conditions. `N=max(0,1−q_U/q_req)`. | [0,1] contradiction of that entailed minimum. q_U≥q_req gives zero opposition, not support. No missing peak, omitted atom or unquantified “no density” fills q_U. |
| Directed row products | Detected event: `p=q D G+ T C I`, `o=q D G− T C I`. Calibrated nondetection: p=0, `o=N D G_examined T C I`; `G_examined` is observed required site coverage, with a fixed explicit denominator. | [0,1] each. These are dependent factors of **one chain**, not independent likelihoods. The actual observed site markers supply D for nondetection; an absent ligand does not receive a fabricated fit score. |

The standard geometry panel supports distances, angles, subunit counts, explicit identity/topology predicates, and reported interface areas. An interface area only becomes a geometric predicate under its stated surface/area convention. Recomputing area is outside these demonstrated readers unless algorithm, atomic radii, probe radius and buried-area convention are supplied. Missing geometry is not a zero predicate. Separate questions with different panels retain fixed weights; duplicating one constraint does not create a new question or extra weight.

Native resolution, Rwork/Rfree, RSR, geometry Z/RMSZ, clashes, occupancy parameters, model coverage, alignment scores/E-values, local alignment probabilities, RMSD/TM-score, restraint bounds and their fit use remain available with their units. None is replaced by an overall quality adjective. None is automatically averaged into D or multiplied again as an independent proof. A high local fit can coexist with an incorrect chemical assignment; identity alternatives and the appropriate experimental observations remain necessary to distinguish those claims.

## Molecular correspondence has several measurable routes

T always evaluates explicit required **roles**, not sequence percentage alone. The same role enters its fixed denominator once, even if several routes support it.

| Route | Exact role calculation |
| --- | --- |
| Sequence correspondence | Retained alignment maps the required source role to a target position. p_k=1 if the target has the specified required atom set/allowed chemical class; 0 if its known chemistry fails; unknown for missing/unresolved mapping. Native alignment statistics are retained. |
| Structural correspondence | Retained superposition maps the role to target atoms. The declared atom identity plus distance/angle/placement predicates determine p_k. All selected model/atom alternatives remain scenarios. Native superposition statistics are retained. |
| Measured interchangeability | A controlled replacement/role-specific measurement supplies a declared native response ratio r and a **stated equivalence interval [a,b]** for that exact role. p_k=1 when r lies in [a,b], 0 when known outside; uncertainty overlapping its boundary gives [0,1]. An interval entirely inside or outside gives the corresponding fixed bound. Missing denominator, unresolved coexisting contributors or an endpoint that does not identify the role leaves it unknown. The equivalence margin is a proposed or source-established criterion, never an overall confidence grade. |

For example, under an explicitly proposed [.8,1.2] equivalence interval, three independently identified role ratios .95,1.02,1.45 give T=2/3. Ratios .95,1.02,unknown give T=null [2/3,1]. These synthetic ratios illustrate the calculation; they do not establish interchangeability for a paper or the target. Evidence for one role by multiple routes is one role, and any reused underlying experiment retains the same dependency identity. A contradictory source measurement does not establish a contradiction in the target when its correspondence is actually zero.

## Exact NMR distance branch

An Xplor assignment `t l u` means [t−l,t+u], with 0≤L≤U; it does not mean t±u. Native allowed bounds are not confidence intervals. Do not add a pseudoatom correction already included in them. Homology-imposed disulfides, inferred hydrogen bonds and force-field geometry are not experimental NOE restraints.

For named single protons, d is their Euclidean distance. For a genuinely reported grouped convention and complete endpoint/pair selection:

| Convention | Effective distance |
| --- | --- |
| `single` | `||x_a−x_b||₂` |
| `R-6` | `[(Σ_ab r_ab^−6)/N_pairs]^−1/6` |
| `SUM` | `[(Σ_ab r_ab^−6)/n_mono]^−1/6`, with the native strictly positive monomer normalization |
| `CENTER` | `||mean_a x_a−mean_b x_b||₂` |

For distances 3 and 10 Å, R-6 gives 3.366977181406 Å and SUM with n_mono=1 gives 2.999635654922 Å. Unknown atom aliases, averaging or actually required bound corrections leave d/D unresolved. A zero proton separation is invalid. Alternative assignments are separate complete scenarios unless the source defines their joint ambiguous-restraint averaging. The shortest fitting proton is not a default choice.

## Current aggregation: strongest documented support and strongest opposition

**This explicitly replaces the old mean over a changing experiment roster.** A111's operands describe how a particular observed structural feature reaches the target. Appending an experiment with T=0 establishes no new target support or opposition. Dividing the old support by the new roster length consequently changes a denominator with no change to the contribution being evaluated. A fixed physical sampling population can justify a mean; an expanding evidence inventory is not that population.

The current convention measures the strongest available supporting and incompatible chains for each **fixed question**. It is deliberately insensitive to numbers of files, papers and weak repetitions. This is a bounded evidence index, not evidence accumulation, a population mean or a posterior. It is reasoned from A111's observed-feature chain; no A105/A106 formula is imported.

Before reducing, resolve the following physical relationships:

1. Paper, table, coordinates, validation and restraint-file representations of one observation have one canonical identity. Equal numbers alone do not establish identity. Conflicting representations become unresolved alternatives unless an explicit source reconciliation chooses their valid current value.
2. Keep only the explicitly selected **current fit/version** of that observation. Superseded analyses remain history, never competitors in a maximum. A revised lower fit can lower current support. Multiple still-admissible fits are complete uncertainty scenarios; do not select the best score.
3. Actual equivalent copies under one declared dataset question have fixed copy membership and equal weights 1/L, or measured normalized sampling weights. Average their **complete** p/o products. An unread required copy stays in the denominator with unknown values. A repeated representation of a copy adds no copy. Average only genuinely equivalent objects; non-equivalent sites belong to distinct scoped questions or an explicitly defined population.
4. Same-experiment conformers, alternative assignments and alternative state interpretations are dependent alternatives. One complete scenario is used at a time. NMR ensemble membership supplies neither occupancy nor physical weights. Different experimental conditions are not repetitions of one unchanged state: score a named state, a specifically defined paired contrast, or a population with actual weights. A paired contrast keeps both states in one observation and uses its actual C and I. Do not take favorable parts from mutually incompatible states.
5. For measured physical state weights π_m≥0, Σπ_m=1, use `p_obs=Σπ_m p_m`, `o_obs=Σπ_m o_m` before any evidence reduction. Unknown weights give no population point. Complete scenario envelopes retain the possible states; any measured weight uncertainty stays joint with the states and normalization.
6. Group shared raw observations, samples, templates and model dependencies. Within a complete admissible scenario s, let e range over current canonical **simultaneously valid** observations in dependency group g for question fj:

   `P_fjg(s)=max({0} ∪ {p_e(s)})`, `O_fjg(s)=max({0} ∪ {o_e(s)})`.

   Then `P_fj(s)=max_g P_fjg(s)`, `O_fj(s)=max_g O_fjg(s)`, `Z_fj=P_fj−O_fj`.

The nested maxima are numerically associative for fully specified simultaneous rows. The grouping remains essential for current-version custody, joint alternatives, shared uncertainty and valid independent sample counts. Grouping is not permission to turn alternative fits into simultaneous observations. Strongest opposition can come from the same mixed observation or a different observation. It never gets erased by a larger number of supporting rows.

For fixed nonnegative elementary-question weights β_fj summing to one within each family and family weights α_f summing to one:

`P111=Σ_f α_f Σ_j β_fj P_fj`; `O111=Σ_f α_f Σ_j β_fj O_fj`;

`Z111=P111−O111`; **`A111=max(0,Z111)`**; optional display `100 A111`.

P/O/A lie in [0,1], Z in [−1,1]. P and O can both be high; report both alongside Z so cancellation is visible. Apply the nonnegative transform **once at the final axis**, not separately to each family. Fixed question/family weights define the requested structural scope; they are not experiment counts. Default equal weights apply to the original declared questions/families. Splitting or renaming a question conserves its original weight. Changing scope/weights is a new prospective sheet, not a retrospective change to saved work. Missing questions do not cause weight renormalization.

The price of the maximum convention is explicit: additional weaker agreeing experiments do not raise the scalar; two modest independent experiments need not outweigh one stronger contrary chain. It is not a calibrated confirmation calculus. Report replication counts, compatible-repeat spread and disagreement alongside the score. For n≥2 genuinely independent estimates of the same endpoint/state, `SD=sqrt(Σ(x_i−mean(x))²/(n−1))` and `descriptive_SE=SD/sqrt(n)`; below n=2 they are null. These statistics are not a second multiplier on the same data and are not the uncertainty of a maximum. Genuine repetition may improve a **current native fit** when a stated measurement model combines it, but the old fits must then be superseded rather than retained as competing evidence. Different states/endpoints have separate summaries; citations, spectra, models and symmetry copies do not increase independent n.

## Empty evidence, missing values and uncertainty

**An empty evidence inventory has P=O=Z=A=0 documented support and `coverage=unexamined`.** This is the algebraic identity of a reducer over no received contributions, not a finding that a feature is absent or false, and not a confidence interval on biology. A declared family without evidence retains its fixed weight and this explicit coverage status. Appending a proved-zero chain leaves the numerical result unchanged. Empty groups also reduce to zero; they cannot supply experimental n.

This differs from an **existing observation with a missing required operand**. Its contribution is unknown, with a logical interval; it is not dropped or set to zero. An unread required Q endpoint with another endpoint .8 gives D=null [0,.64]. One NMR restraint with v=.5 Å and one unread required restraint gives D=null [.303265329856,.803265329856]. Empty required endpoint/role/geometry panels are invalid-denominator unknowns, not perfect fit. No-experiment coverage zero and invalid-analysis unknown are distinct fields.

Every native quantity retains point, units, reported uncertainty, source and scope. Unreported uncertainty stays unreported. Source decimal precision is not an error bar, a B factor is not an automatic coordinate SE, and an ensemble range is not a physical distribution. Source-local calculations may be conditional on reported numbers/model assignments; their calculation bounds do not claim calibrated sampling coverage. In particular, an unconditional population q remains null when only fixed deposited occupancy is available.

The exact interval calculations used here are:

* Correlation branches: transform each native interval monotonically through `max(0,r)^2`, then take the endpoint minima. Missing required correlation spans [−1,1], giving transformed [0,1].
* NMR with fixed [L,U] and d∈[dL,dU]: `v_min=max(0,L−dU,dL−U)`, `v_max=max(0,L−dL,dU−U)`; s bounds are `exp(−v_max²/(2τ²))` and `exp(−v_min²/(2τ²))`. Average with the fixed restraint denominator. Alternative bounds/assignments are coupled scenarios.
* A physical predicate is [1,1] when the entire admissible quantity set meets it, [0,0] when none does, and [0,1] when it crosses the boundary. Do this jointly for paired positive/opposing predicates. Role counts retain their fixed K.
* For continuous comparability, the smallest possible absolute difference of x_A∈[a,b], x_B∈[c,d] is `max(0,a−d,c−b)`; the largest is `max(abs(a−d),abs(b−c))`. Substitute largest/smallest into the Gaussian for its lower/upper bounds. Count-ratio intervals retain their actual denominators; a zero denominator is invalid. Unknown declared nuisance factors span [0,1].
* For Y∈[YL,YU], B∈[BL,BU], YU>0: `IU=max(0,1−BL/YU)`; `IL=0` if YL=0, otherwise `max(0,1−BU/YL)`. YU=0 gives I=0. Missing nonnegative B gives I=null [0,1].
* For q_req∈[rL,rU] with rL>0 and q_U∈[uL,uU]: `NL=max(0,1−uU/rL)`, `NU=max(0,1−uL/rU)`. If the required lower minimum is not established, N remains null with logical bounds rather than division by zero.
* Nonnegative product bounds multiply; known exact zero makes the product exactly zero even when other operands remain null. This is algebraic determination, not filling the missing operands. Without a determining zero, missing points propagate unless the result is otherwise identical over every allowed value.
* For simultaneous row intervals, `P_L=max(0,p_eL)`, `P_U=max(0,p_eU)` over the admitted rows; O analogously. `Z∈[P_L−O_U,P_U−O_L]`; fixed positive-weight sums propagate endpoints; A bounds apply max(0,·). This is a conservative outer enclosure when P/O or factors share inputs, not an independence assumption.

For discrete model/mapping/state alternatives, calculate the **whole candidate result in every admitted joint scenario first**, then take minima/maxima. Do not take a support maximum from one alternative and opposition maximum from a mutually exclusive alternative to create a point score. If a single dataset permits signed outcomes +.6 or −.4, its point is null and signed scenario envelope is [−.4,.6], not the fabricated point .2. A separately named current model can have a conditional point, with the alternatives still reported. Measured state weights may give a point; e.g. π=(.7,.3) applied to (+.4,−.2) gives P=.28, O=.06, Z=.22.

For continuous uncertainty with known dependency but no joint samples, retain the dependency constraints and label interval arithmetic as an **outer sensitivity bound**; do not claim its endpoints are jointly attainable. Native uncertainty not bounded by supplied information has `unconditional_uncertainty=unreported`, even when a model-conditional index can be calculated. An unknown contribution direction admits its positive and negative possibilities jointly, rather than assigning an intuitive sign or .5 grade.

## Candidate-level direction and contrast

For each emerging candidate H, use the same source observations, fixed scope/weights and explicit expected/contrary physical predicates. A shared ATP-site observation supports ATP binding and ATP hydrolysis equally if both candidates predict that same physical feature; that observation alone gives ΔZ=0. It does not produce an activity, affinity or physiological-metal measurement.

Return Z(H), A(H), P(H), O(H), coverage, unresolved operands, conditional assumptions and bounded direction. Bounds wholly above zero establish positive **index direction**; wholly below zero negative; [0,0] zero; crossing zero leaves direction unresolved. A positive point with a zero-crossing envelope does not establish robust positive direction. A=0 never removes negative Z or recorded opposition.

For H_A versus H_B calculate `ΔZ(s)=Z(H_A,s)−Z(H_B,s)` **within each shared scenario** and then bound it. Shared evidence can cancel exactly even when separate candidate intervals are wide. Unexamined candidate predicates give an unresolved contrast. The formula does not select a candidate, gate scientific completion, redefine investigation progress, or change continuation.

## Numerical repair and finite choices

| Same fixed question | Old experiment-roster mean Z | Proposed strongest-support-minus-opposition Z |
| --- | ---: | ---: |
| One positive chain .3655125 | .3655125 | .3655125 |
| Append independent known T=0 chain | .18275625 | .3655125 |
| Add a weaker .2885625 supporting experiment instead | .3270375 | .3655125 |
| Positive .3655125, positive .2885625, opposition .486 | .056025 | −.1204875 |

Duplicate representations do not change either a properly deduplicated old mean or the proposed result. Revising the sole current .3655125 fit to .2 gives .2; keeping the stronger superseded value would be wrong. A genuine opposing result changes O, unlike a known-zero addition.

The full worked file supplies all native and synthetic inputs, including corrected mixed-sign geometric panels, cross-modality candidate totals and checked envelopes. The retained two-family X-ray example changes from historical .1240125 to proposed .03575625, with declared sensitivity Z bounds [−.0937404,.2965130125] and A bounds [0,.2965130125]. This is a prospective change of the reducer's meaning, not a reinterpretation of a saved run.

Choices offered for judgment: local correlation square/minimum; the NMR .50 Å kernel; the product; role/geometry definitions; nuisance scales; fixed family/question weights; and strongest support minus strongest opposition instead of count-dependent averaging. Their arithmetic is fully specified here. Empirical correctness calibration and human adoption are not additional research-completion prerequisites; neither is claimed. Unsupported modalities and actual missing measurements remain explicit limits.

Exact targeted fields and future function IO are in `READER_FIELD_CROSSWALK_001.md`. `WORKED_EXAMPLES_001.md` supplies calculations, `SOURCE_TO_COMPONENT_001.md` attributes source coverage, `PRINT_READY_HANDOFF_001.md` is the concise conversation handoff, and `READ_AND_VERIFICATION_001.md` states actual reading and testing. These are parts of this one proposal, not successive patches with competing rules.
