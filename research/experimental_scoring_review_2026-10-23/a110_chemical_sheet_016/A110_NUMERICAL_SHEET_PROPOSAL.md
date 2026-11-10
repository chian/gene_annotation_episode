# PROPOSED A110 numerical sheet: chemical and pathway account

The outcome is a numerical contribution for the chemical/resource account of an emerging function: measured stoichiometry and atom origin, conservation, and resource supply relative to the account's stated demand. This is a complete arithmetic proposal for feedback, with source-populated examples and explicitly missing operands; it is not adopted scoring policy, a production reader, an implemented axis or an assertion that the ten-sheet goal has advanced beyond 0/10.

The scientific investigation can begin with supplied sequence, selected file contents, a region or snippets. No initial annotation or searchable gene name is required. Once a possible chemical function emerges, this sheet records the particular account and its alternatives. The historical reference experiments below are examples for constructing the sheet, not experiments on the supplied annotation target.

Only the numerical sheet and future populating IO are specified here. The investigation prompt remains a separate responsibility; this sheet is not a prompt insert. W05 owns eventual use in annotation credit. No global score, hypervolume, continuation rule, runtime gate or required experimental itinerary is changed.

## The numerical entries

| Cell | Actual numerical inputs | Calculation and units | Meaning |
|---|---|---|---|
| Chemical quantity y | Moles consumed/formed, calibrated isotope-bin amounts, or other directly relevant chemical measurements, with actual denominators | Reaction ratio, fraction vector, electron or atom equivalent per declared turnover; exact form specified per row | What chemical quantity was measured, distinct from A105 activity magnitude |
| Comparability correction b_comp | Measured covariate-response coefficients and condition differences, or paired calibration experiments | Σ_l β_l Δx_l, in y units; corrected y subtracts this quantity | Expected bias from differences other than the intended variable; no count of matching metadata fields |
| Effect-isolation correction b_iso, recovery r and mixture fraction λ | Actual blank/interference measurements, recovery standards, component concentrations and response factors | Defined measurement equation below; b_iso has y units, r and λ are dimensionless | How the readout relates to the intended chemical quantity; separate from condition comparability |
| Claim and alternative predictions c, a | Stated stoichiometric coefficients, label-transfer model, measured nuisance values; alternative's identity and assumptions | Same units and measurement operator as y | The quantitative distinction this row can test |
| Residuals e_c and e_a | Corrected experiment-level y values and predictions | Mean squared residual, in squared y units, or squared dimensionless fraction distance | Absolute chemical mismatch to each account; must remain visible beside the normalized result |
| Signed chemical constraint s | e_c,e_a≥0 | (e_a−e_c)/(e_a+e_c), range [−1,1]; if both zero, 0 | Relative fit of the stated chemical account to the named alternative, not probability or catalytic proof |
| Resource demand coverage f | Same-period available/reactive resource budgets, stoichiometric requirements, measured capacities, requested output flux/amount v*>0 | f=min(1,z/v*), where z is maximum output allowed by those measured constraints; dimensionless | Fraction of stated chemical demand supportable; no surplus bonus |
| Signed resource cell s_supply | f∈[0,1] | 2f−1, range [−1,1] | Proposed continuous conversion: deficiency versus sufficiency of that exact demand |
| Conservation deficit D | Signed reaction coefficients, atom counts, charges and electron half-reactions, with species/protonation identities | Maximum normalized closed-balance residual, defined below; [0,1] | Bookkeeping contradiction in the stated closed account; zero earns no independent positive observation |
| A110 contribution C | Prespecified question weights w_g, each constraint s_g, D | S=Σ_g w_g s_g; C=(1−D)S−D | Explicit proposed compilation into a bounded signed chemical-account contribution |

Every input and proposed transformation retains its own origin. The source papers do not supply the signed score, normalization, weights or compilation formula. Those are new proposals. No inspected source supplied a native pathway model score that could replace this arithmetic; none is invented. A future native flux/model score must retain its objective, feasible set, bounds, units and uncertainty before any numerical conversion is proposed.

## 1. Define the measured question before calculating its component

Each row names its measured subject, chemical account, reaction direction, target scope, numerator, denominator, reaction basis and alternative. One mole of turnover must mean the same thing on both sides of a ratio. Supplied substrate is not automatically consumed substrate. A steady-state concentration is not an available flux. Net NAD(P)H signal is not separately measured NADPH. Formal electron equivalents are not observed electron-transfer rates.

The NfnAB example supplies two chemically distinct tests within one reaction account: reverse H2 per supplied NADPH and forward net reduced pyridine nucleotide per supplied NADH. The UbiUV example supplies label-count information about an oxygen donor, but leaves donor-pool dilution and a redox sink unresolved. These cases motivate the numerical cells; a generic paper-quality checklist does not supply them.

For a scalar assay, use the actual measurement model, for example:

    y_read = r [ λ y_intended + (1−λ)y_other ] + b_iso
    y_comparable = ((y_read−b_iso)/r − (1−λ)y_other)/λ − b_comp
    b_comp = Σ_l β_l (x_test,l−x_reference,l).

Here r>0 is calibrated recovery, λ>0 the measured signal-contributing fraction, b_iso the measured additive background, and β a measured response per unit of the confounding condition. This is not a universal mixing model: it is used only when linear response/additive mixing is established. For compound ratios the numerator and denominator receive their own calibrated transformations **before** division. Unknown response coefficients do not become zero because conditions look similar. Unknown λ does not become a categorical “transfer” weight.

Both corrections numerically enter y through sums/products/division. They are not duplicate score rows. The same chemical observation has one final residual comparison. Source-limited calculations may display a point conditional on r=1, λ=1 and b=0, but that is a declared model assumption, not a measured reliability result. An unconstrained correction leaves a wide or unknown contribution, not an invented confidence number.

For an exact stoichiometric prediction, pH or enzyme amount need not alter the predicted ratio when the specified chemical products, reaction basis and readout mapping remain valid. This invariance is an explicit property of the model; it is not a generic claim that the experiments match. NfnAB's two directions are not pooled as identical assays. UbiUV's labeled/unlabeled comparison uses the same mutant and supplementation, while the added-4-HB and WT arms remain separate.

## 2. Convert chemical measurements into signed constraint cells

For independent experimental units i=1,…,n and scalar y_i:

    e_h = (1/n) Σ_i (y_i−μ_hi)^2
    s_c,a = (e_a−e_c)/(e_a+e_c).

The experiment, not each time point or each technical injection, is the unit. A report of mean y_bar, sample SD s_y and known n for a common constant prediction permits the exact descriptive identity:

    e_h = (y_bar−μ_h)^2 + ((n−1)/n)s_y^2.

This retains observed variability. It does not use sample count as a score multiplier or claim a likelihood. When only an approximate published mean is available, calculate the explicitly conditional central residual and label between-unit variation unknown. Do not silently treat the mean as a perfectly replicated measurement.

For an isotope distribution, use a whole vector of normalized fractions from each experiment:

    e_h = (1/n) Σ_i Σ_j (y_ij−μ_hij)^2.

All entries are dimensionless; j denotes the fixed declared ion windows. Covariance is retained for uncertainty propagation. The squared distance is not a chi-square statistic and makes no assertion that bins are independent. Different-dimensional or different-unit errors are never pooled directly; their per-question signed contrasts are combined at the next step.

For scalar intervals Y=[yL,yU], M=[mL,mU], conservative error bounds are fully specified:

    e_min = max(0, yL−mU, mL−yU)^2
    e_max = max(|yL−mU|, |yU−mL|)^2.

Then s lies within [(e_a,min−e_c,max)/(e_a,min+e_c,max), (e_a,max−e_c,min)/(e_a,max+e_c,min)]. If a bound encounters 0/0, include 0 and the feasible limiting values; if all errors are identically zero, the interval is [0,0]. Interval relaxation may widen the answer when inputs are shared; it never makes the shared measurements independent. Exact joint bounds, when available, replace that conservative enclosure. The physical parameter domain and covariance remain part of the stored calculation.

Preserve multiple named alternatives. Within one question, s_g=min_a s_c,a is the proposed conservative summary across the **declared** alternatives; all pairwise values remain visible. Repeating an alternative changes nothing. Missing predictions for a required named alternative leave its s unknown and the question's bounds correspondingly wider. This is a numerical comparison, not an acceptance gate; it does not authorize an assertion that all conceivable alternatives were excluded.

The signed contrast can favor one badly fitting account over a worse one. For that reason e_c, e_a, physical residuals, tested conditions and absolute measurement uncertainty are compulsory numerical companions. C is a relative chemical-account contribution, not a universal reliability or probability. An isolated positive value cannot establish catalysis, enzyme identity or physiological use.

## 3. Calculate resource sufficiency without inventing flux

For a simple batch reaction with fixed nonnegative stoichiometric consumption coefficients a_i (mol resource/mol product), measured usable amounts U_i (mol) and requested product amount v*>0 (mol), the simplest explicit budget is:

    z = min_{i:a_i>0} U_i/a_i
    f = min(1,z/v*)
    s_supply = 2f−1.

The same calculation applies to matched steady-state flux units when U_i is a measured available rate and v* a required rate. A cofactor regenerated internally is represented by its regeneration reaction and capacity; its entire catalytic turnover must not be charged as irreversible cofactor consumption. Pool sizes alone do not define sustained flux. Compartment access, competing consumption and time basis must be part of the measured budget.

For a branching/recycling network, define z by this explicit optimization, not by summing separate pathway guesses:

    maximize z = v_target
    subject to S_internal v = observed accumulation rates,
               l_j ≤ v_j ≤ u_j for every directed reaction/exchange,
               measured shared-resource constraints Gv ≤ h.

Reaction columns carry molar stoichiometry. Bounds carry identical flux units and the direction convention. Required partner reactions and candidate alternate routes appear as separate columns with preserved identity and evidence. Measured capacities populate u/l; gene presence or a homology score does not become an enzyme capacity. Unknown capacities remain open bounds. Infeasibility is a model/data contradiction to report, not automatically a measured zero biological flux. No optimizer or dataset reader implementing this proposal exists in this workload.

When only ranges for capacities or demands are known, take the attainable minimum/maximum of f over their declared joint domain. No input scenario may allocate the same shared resource twice. If v*=0, do not divide or assign a maximum score; the stated positive-demand question is not applicable and the sheet must name a meaningful demand before a resource cell exists. If v* is unknown, the cell remains unknown. No fully measured pathway is required before an investigation can continue.

The transformation 2f−1 is an explicit proposed scoring choice: it reports a continuous demand-coverage scale, with f=0.5 at zero contribution. That midpoint is not a biological threshold or native publication score. Whether another continuous normalization is preferable is a concrete feedback choice; the present arithmetic is defined and runnable.

Available free energy can constrain a resource budget only under its stated concentrations, direction and thermodynamic model. For ATP output n_ATP with available energy E>0 and per-ATP cost g>0, conditional coverage is min(1,E/(n_ATP g)). In NfnAB's discussion E=100 and g∈[60,80] kJ/mol imply ATP capacity [1.25,1.666667]. That is an author-scenario calculation, not measured native energetic support. It stays out of the empirical score.

## 4. Preserve conservation as a distinct numerical constraint

Use negative stoichiometric coefficients ν_i for reactants and positive coefficients for products. Specify species formulas, charge/protonation, compartment and reaction direction. Cancel identical species present on both sides before computing a deficit. For element l:

    R_l=Σ_{ν_i<0}|ν_i| n_il; P_l=Σ_{ν_i>0}ν_i n_il
    r_l=P_l−R_l                [mol atoms/mol declared turnover]
    d_l=|r_l|/max(R_l,P_l),    with d_l=0 when R_l=P_l=0.

For charge:

    r_Q=Σ_i ν_i q_i; d_Q=|r_Q|/Σ_i |ν_i q_i|,
    with d_Q=0 if every term is zero.

For explicitly paired redox half-reactions with donated E_d and accepted E_a mol electrons/turnover:

    d_e=|E_d−E_a|/max(E_d,E_a), with d_e=0 if both are zero.
    D=max(d_l for all declared elements, d_Q, d_e).

The atom basis and full list of residuals remain visible. Formula charges may be symbolic for unchanged molecular skeletons; algebraic cancellation must be shown. An open half-reaction with an unidentified electron acceptor is not a false measured balance violation. If the requested scope is a complete net reaction, its D stays unknown until the missing term is specified. A narrower oxygen-source question may separately report its atom-source component, without relabeling that component “complete redox balance.”

D is a proposed normalized description of the written account's conservation defect, not a severity inferred from prose. Exact stoichiometry has exact algebraic residuals; empirical flux residuals instead carry measured uncertainty and belong to the measurement rows. No arbitrary universal 5% or 10% tolerance replaces source uncertainty. All d values are invariant to a common change in reaction normalization after species cancellation.

NfnAB's stated relative redox account has atom-skeleton cancellation, equal formal charge and 4 donated/4 accepted electrons, so D=0 on that declared basis. Balanced chemistry alone supplies no positive score. UbiUV's proposed donor half-reaction can be balanced while the catalytic net and its electron sink remain unspecified.

## 5. Explicit compilation and missingness

Declare the finite physical question set g and weights w_g≥0, Σ_g w_g=1 for the specific account. The default proposal is an equal split between the **distinct prespecified physical constraints**, never between papers, database hits or repeated portrayals. Splitting one question into redundant rows does not give it extra weight. Component and cross-axis shared-observation references preserve dependence; the result is a descriptive weighted sum, not an independence-based probability.

    S = Σ_g w_g s_g
    C_A110 = (1−D)S−D, in [−1,1].

This explicit conservation penalty is proposed. At D=0 it leaves the measured constraint sum unchanged; at D=1 the written closed account is maximally contradictory on this scale. It never rewards algebraic balance as an extra experiment. There is no veto on investigation or tool use.

Unknown s_g retains the full possible interval [−1,1] unless actual constraints narrow it. Keep its weight in the denominator; do not renormalize unknown components away. For s_g∈[L_g,U_g], S∈[ΣwL,ΣwU]. Since C increases with S and decreases with D on the stated domain:

    C ∈ [(1−D_U)S_L−D_U, (1−D_L)S_U−D_L].

Unknown D gives [0,1]. This bound is arithmetic, not a fabricated sampling interval. Sources of uncertainty are labeled separately: sampling, calibration, plot extraction, model parameter, unmeasured resource, missing identity, and unresolved alternative. Statistical confidence level remains null when it is unknown. A conditional nominal result never replaces this record.

The weighting and conservation penalty are concrete choices for user feedback. Changing the question set or chemical scope changes the estimand and must be named. In particular, a result for a purified reaction account cannot be compared to a full physiological pathway result as if they had the same filled denominator.

## Checked complete compilation: NfnAB reaction account

Scope: does the stated reversible coupled redox/cofactor account match the reported purified-system stoichiometry, relative to the two named simple uncoupled accounts? This is not a claim that native flux supply is established.

| Physical constraint | Source quantity | Claim prediction | Named alternative | e_c | e_a | s | Weight |
|---|---:|---:|---:|---:|---:|---:|---:|
| Reverse H2 per NADPH supplied | 1/2.2=5/11 mol/mol | 1/2 | 1, uncoupled NADPH→Fd | 1/484 | 36/121 | 143/145=0.986206897 | 1/2 |
| Forward net NAD(P)H increase per NADH supplied | 0.10/0.11=10/11 mol/mol | 1 | 0, simple transhydrogenation | 1/121 | 100/121 | 99/101=0.980198020 | 1/2 |

    D=0 for the declared formal redox account
    S = 0.5(143/145) + 0.5(99/101)
      = 14399/14645 = 0.9832024581768521
    C_A110 = (1−0)S−0 = 0.9832024581768521.

Every arithmetic operand in this **conditional point compilation** is filled. Inputs are approximate reported ratios; recovery, actual substrate consumption, between-preparation uncertainty and systematic readout effects are unmeasured here. Thus 0.983202458 is not a calibrated reliability or confidence. If those nuisance quantities are unconstrained for the requested interpretation, the honest unconditional contribution bound is [−1,1]. This distinction is part of the output, not a footnote erased during compilation.

For the broader native pathway account, use three declared question blocks with equal 1/3 weights: the reaction-stoichiometry block above, native resource-capacity coverage and measured energy coverage. The latter two are unknown in the inspected source. Keeping the first block's nominal point conditional:

    S_pathway ∈ [(0.983202458−2)/3,(0.983202458+2)/3]
              = [−0.338932514,0.994400819].

This interval assumes D=0 for the proposed pathway bookkeeping and conditions on the nominal stoichiometry block. Allowing its unmeasured nuisance effects widens the result to [−1,1]. The author-proposed Fd allocation 5−(2+2.5+0.5)=0 does not fill resource capacities. The conditional ATP ceiling does not fill measured energy support.

## Contrasting UbiUV compilation boundary

The source supplies p=.64±.012 and a three-experiment isotope pattern. The full-pattern formula, nuisance model and alternatives are specified in `paper_02_ubiuv.md`. Its exact empirical errors cannot be calculated from the available text and plotted means alone. The deliberately limited two-bin example has actual image-derived quantities and checked signed contrasts, but its broad bounds and missing pool calibration prevent it from replacing the full pattern.

If the requested account includes the oxygen donor, redox closure and native resource supply, the final full-pattern cell, net-reaction D and supply cells all remain unknown. Its full C bound is [−1,1]. The measured precursor fraction, calculated predicted distribution, coarse observed ratios and conditional contrasts remain useful populated components. They do not produce a fabricated precise pathway score.

## Dependence, consistency, negative results and transfer

| Situation | Numerical treatment |
|---|---|
| Two representations of one experiment | Same observation reference and one residual; no new weight or n |
| Technical repetitions | Reduce instrument uncertainty within the experimental unit when the actual design permits; not independent preparations |
| New independent preparations | Retain each unit or mean/SD/n; calculate mean squared residual with variation, not a publication-count bonus |
| Complementary directions/readouts | Separate physical constraints within a fixed block weight; not assumed replicates or independent probabilities |
| Contradictory matched units | Keep all residuals and variability; do not retain only favorable means. With unequal conditions, use separate cells or measured b_comp; no invented pooling |
| Alternative explaining one feature but not another | Retain the full joint question, predictions and per-alternative values. The UbiUV first-two-bin example demonstrates the danger of dropping higher bins |
| Nondetection | Use [0,LOD] only for a documented calibrated amount/rate limit for that assay and background model; propagate interval. Absence of a plotted bar or textual mention is not zero and not a known LOD |
| Signed consumption/production | Retain reaction direction and signed stoichiometry; reverse direction is not a negative activity artifact |
| Shared A105 measurements | Link the activity/readout's same observation. A110 uses chemical ratios/budget consistency, not a second activity-magnitude reward |
| Shared A106 perturbation evidence | Link causal attribution; do not count deletion/rescue as a new atom-tracing or electron-balance measurement |
| Shared A107 partner measurements | Use identities to construct a possible reaction network; do not re-award gene-homology/coexpression scores or turn them into measured capacity |
| Reference-to-target relation | Preserve actual assayed subject and measured correspondence. Chemical law may transfer to an identical specified reaction, but protein identity, cofactor preference and physiological deployment do not follow from it. Unmapped relations remain unknown; no blanket applicability weight |

No source inspection established measurements on the project's current annotation target. The two examples populate reference-account sheets only. Relevance can be established through more than sequence similarity, but the relevant measured relationship must be identified before a reference result is asserted for a different target.

## Feedback choices and deliverable boundary

Concrete choices to review are the squared-error contrast versus other continuous transforms; the minimum across declared alternatives; the equal physical-question weights; the 2f−1 demand-coverage normalization; and the conservation penalty (1−D)S−D. All are explicitly defined here rather than deferred to future calibration. Their biological usefulness across more cases remains unvalidated. Unknown source values are not undefined mathematics.

`reader_io.md` defines the exact targeted fields and UNIMPLEMENTED populators. `component_source_table.md` traces each component to inspected evidence and distinguishes support from gaps. `check_arithmetic.py` only recomputes research examples and boundary properties. It does not read publications, populate a production sheet, solve a target pathway or implement any callable episode operation. `PRINT_READY.md` supplies concise formulas and examples for the parent to print for user feedback.

Source-specific conversion and inspection/reset records remain separate in `paper_01_nfnab.md`, `paper_02_ubiuv.md` and `authority_reads.md`. No user acceptance, reader implementation, full target scientific result or axis completion is claimed.

## Additive source-filled supplied-resource illustration

The same NfnAB Fig. 3B quantities fill a limited reagent budget as well as the ratio constraint: U_NADPH≈2.2 µmol supplied, a_NADPH=2 mol/mol H2 under the proposed coupled reaction, and v*≈1 µmol H2 as the reported endpoint to be accounted for. Therefore z=1.1 µmol H2, f=min(1,1.1/1)=1 and proposed s_supply=1. The derived 0.2 µmol excess is not a measured residual. This is a retrospective supplied-reagent sufficiency calculation, not a future demand forecast or native intracellular capacity. It receives zero additional weight in the compiled reaction score because Fig. 3B already supplies the reverse stoichiometry constraint. The separate five-assertion arithmetic record is `budget_arithmetic_results.json`; the source-specific interpretation is appended to `paper_01_nfnab.md`.
