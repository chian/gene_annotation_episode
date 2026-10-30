# Proposed common A105 evidence evaluation: one paper, unresolved quality remains visible

Design proposal for conversation feedback, not an approved policy, complete A105 sheet or implementation. Exactly ten axes remain; A105 is the present scope. Existing readers/calculators would populate sections of **one logical sheet indexed by the assayed molecule and functional assertion**. Their software modules do not create separate scientific scores or independent experiments. W05, target correspondence and controller behavior are outside this proposal.

Attribution means isolation of the measured effect to the intended molecule/change. Functional relevance asks whether the endpoint answers the functional assertion. Comparability concerns differences outside the intended change. Validity concerns whether the measurement and its interpretation work as claimed; reliability includes repeatability and uncertainty. These questions intersect mathematically without being interchangeable labels or four numeric category grades.

## 1. Actual experiment and assertions

Kim, Heo and Ortiz de Montellano (2008), DOI 10.1016/j.abb.2008.02.044, PMC2577879, assays purified *Pseudomonas putida* P450cam/CYP101, with separately assayed WT, T252N, T252N/V253T and T252A forms. Mutant constructs have C-terminal 6His tags, were sequence verified and expressed in *E. coli*. WT/mutant P450 molecules do not coexist in one assay arm. Each is reconstituted with putidaredoxin and putidaredoxin reductase, nominally 200/1000/200 pmol P450/Pd/PdR, phosphate pH 7.4, 37°C. Mutant versus WT is the intended change; matched active fraction, all tagging/preparation history and actual normalization calibration are not established. Table1 expression/purification yields are not the amounts assayed.

Keep these separate emerging assertions and resolutions:

- F-product: the assayed P450 preparation converts camphor to chemically identified 5-exo-hydroxycamphor in the stated reconstituted system.
- F-turnover: a selected mutant retains a specified amount of product-forming turnover relative to WT. Table2 fitted saturation turnover and Table3 reported turnover are distinct estimands.
- F-low-substrate: relative product formation per substrate at low substrate under the kinetic model. This is more specific than simply retaining some catalytic activity.
- F-binding-only: the product-turnover difference can be explained by altered equilibrium substrate occupancy alone, with post-binding turnover, active amount and other assay response unchanged. This is an explicit alternative explanation to evaluate conditionally, not an author-measured mechanism.

GC-MS co-chromatography and mass-spectral comparison against authentic standards address product identity (Methods P11, Results P17, Fig4). NADH loss is a reporter with productive and unproductive routes. Spectral Kd addresses camphor binding, not hydroxylation. No numerical no-P450 blank, active fraction or Table3 covariance is supplied. Fig5 reports triplicate mean/SD for plotted kinetic points; it does not identify Table2/4 fitted-parameter ± terms or Table3 uncertainty. Do not construct parameter SEs from those triplicates.

## 2. Shared binding before arithmetic

The common sheet needs a binding record in addition to numeric cells:

`assertion -> intended contrast -> assays -> endpoint estimates -> measurement owners -> controls/models`.

A functional assertion specifies the studied subject/construct, transformation or binding event, functional resolution, system/condition scope and whether the question is existence, relative effect or a named alternative explanation. Assays specify their own preparation, arm, endpoint, denominator, conditions, timing, intended variable and nuisance differences. An endpoint estimate has both its source quantity owner and its actual measurement population; two different table numbers do not establish two independent preparations. Assertion links are witnessed restricted interpretations: `direct_product`, `reporter_requires_conversion`, `binding_addresses_occupancy`, `alternative_product`, `incompatible_scope`, `unknown`, `conflicting`. They are not numerical relevance weights.

A dependence record separates `same_measurement_view`, `shared_primitive`, `same_sampling_unit`, `independent_sampling_units_supported`, `complementary_endpoint` and `unknown`. Complementarity and shared measurement can both apply: chemically identified product plus the coupling ratio address reporter ambiguity, but reuse P. A contradiction comparison requires the same estimand/subject/scope or an explicit model connecting them. Binding and catalysis are not inconsistent repeated measurements merely because their values differ.

All cells carry their exact operand owners, model/relationship owners, units, origin, numerical status, dependence and separate reasons for source absence, relationship uncertainty and unimplemented conversion. This supports numerical evaluation; these records alone do not satisfy the scoring-sheet requirement.

## 3. Populated common numerical sections

The numerical oracle file preserves exact rational results. Displayed decimals here are shortened. None is a final evidence grade, function probability or annotation credit.

| Common numerical cell and meaning | WT | T252N | T252N/V253T | T252A |
|---|---:|---:|---:|---:|
| Table3 reported product turnover P, min^-1 |206|92|132|native 0; negligible/ND, limit unknown|
| Table3 reported NADH turnover H, min^-1 |289|216|343|427|
| Identified product per reporter, rho=P/H |0.712803|0.425926|0.384840|physical point unavailable|
| Product-turnover contrast R_P=P/P_WT |reference|0.446602|0.640777|physical point unavailable|
| Reporter contrast R_H=H/H_WT |reference|0.747405|1.186851|1.477509|
| Productive-use contrast R_rho=rho/rho_WT |reference|0.597537|0.539896|physical point unavailable|
| Table2 saturation turnover contrast kcat/kcat_WT |reference|0.435484|1.330645|ND, limit unknown|
| Table2 low-substrate catalytic-efficiency contrast (kcat/Km)/(kcat_WT/Km_WT) |reference|0.136089|0.102885|unavailable|
| Table4 binding Kd, µM |1.8 ±0.1|34 ±2|12 ±1|2.9 ±0.2|

The Table2 efficiency calculation uses central fitted values, not invented joint fit covariance. It evaluates functional resolution: the double mutant has 1.3306 times WT fitted saturation turnover but only 0.1029 times WT low-substrate efficiency. Scoring the broad phrase “retains function” without this resolution would conflate different functional assertions. It does not establish equivalent activity in an unknown physiological substrate regime.

The source's Table3 author-coupling convention has nu=1 NADH per product. A productive fraction eta=nu*rho is **conditional** because detailed preparation/conditions/normalization matching remains unknown; descriptive rho survives. rho*H reconstructs P and is the same contribution. For T252N:

`R_P = R_H * R_rho = 0.7474048443 * 0.5975368572 = 0.4466019417`.

This is useful endpoint-specificity decomposition, but does not measure measurement quality, contamination or causal isolation. The existing212 implementation supplies the single-arm piece; the common cross-arm assembly and its uncertainty are unfinished.

### A numerical assessment of the binding-only alternative

The source explicitly uses 2 mM camphor for the NADH assay (P12), but does not explicitly connect that concentration to Table3 product sampling. Binding titration shares phosphate/pH but its temperature, preparation linkage and one-site fit details are not established. Therefore the following cells belong in a **conditional scenario**, never the populated physical-correction field.

Declare the scenario completely: free substrate S=2000 µM in both compared product assays; single-site equilibrium occupancy theta=S/(S+Kd); binding Kd transfers to those catalytic preparations/conditions; nominal normalization, recovery and active fractions are equal; product formation is proportional to occupancy with unchanged post-binding turnover for the binding-only alternative. These are model assumptions, not source observations. Use total 2mM as free 2mM only within this stated scenario; no silent depletion correction is claimed.

| Scenario cell | T252N | T252N/V253T | T252A |
|---|---:|---:|---:|
| theta=S/(S+Kd) |0.9832841691|0.9940357853|0.9985520995|
| Occupancy-only predicted R_theta=theta/theta_WT |0.9841691249|0.9949304175|0.9994507963|
| Binding-only prediction error d=R_P-R_theta |−0.5375671831|−0.3541537185|unavailable: ND has no numeric limit|
| Post-binding residual R_a=R_P/R_theta |0.4537857676|0.6440417217|unavailable|
| Log residual D=ln(R_P)-ln(R_theta) |−0.7901300699|−0.4399917698|unavailable|

These are numerical assessment cells for a named alternative explanation: with these assumptions, occupancy-only loss is small while product-turnover loss is much larger. The residual asks how much additional relative activity change must remain after the modeled occupancy difference. It does not identify its cause. Unequal active fraction, preparation effects, contaminating activity or method bias can also change that residual. It cannot be relabeled “fraction due to catalytic chemistry.” T252A's modeled high occupancy and native negligible product qualitatively dissociate binding from catalysis, but absent LOD prevents a numerical residual bound or calibrated evidence score.

The common sheet combines complementary binding and catalytic information through the explicit model relation `R_P=R_theta*R_a`, or equivalently `ln R_P=ln R_theta+D`. Unlike repeating the212 identity, this compares a measured product contrast to an independently interpreted binding-based prediction. Independence of sampling units is still unknown; no independent evidence count follows.

### Reliability, validity, comparability and effect-isolation sections

| Cell / exact combination | What it evaluates and required inputs | This paper |
|---|---|---|
| B_i: additional same-endpoint background/other-molecule rate; f_isolated,i=(P_i−B_i)/P_i | Fraction of the measured product signal remaining after a source-supported other-contribution subtraction. Requires a relevant no-P450/partner-only or selectively depleted control on the same normalization; it is not product identity. Shared prior blank subtraction cannot be repeated. |Unknown B; no numerical isolation fraction. Separate mutants do not imply B=0.|
| Instrument recovery k_i=m_i/n_i; relative bias b_i=k_i−1; relative loss L_i=b_i²+(CV_i*k_i)² | Accuracy/repeatability of the endpoint measurement against an applicable standard, for an explicitly matched measurement population and actual SD/CV. Chemical authentic-standard matching is identity evidence, not a recovery measurement. |m,n, SD/CV absent; L unknown.205 supplies the bounded component family, not this paper's values.|
| Active fraction f_i=active_i/nominal_i | Adequacy of the per-molecule denominator, with matching preparation and amount method. Fig3 P420 suggests a double-mutant weakness but supplies no numeric fraction. |Unknown; Table1 yield is excluded as a denominator.|
| Nuisance response c_i/c_WT from control experiment excluding intended mutation | Quantifies a particular condition/preparation difference outside the intended change. A physical response model is required; do not average pH/temperature/tag metadata into C. |No applicable numeric nuisance control; unknown.|
| Var(D)=J_D Sigma J_D^T (+ separately identified distinct model-discrepancy variance when required) | Uncertainty of the *binding-only residual*, with actual joint owners P_i,P_WT,Kd_i,Kd_WT,S and all reused calibration/normalization. Estimated covariance remains estimated. |Absent joint covariance; no z or significance. Table2/4 ± tokens do not supply it.|
| z_D=D/sqrt(Var(D)); lack-of-fit Q_D=D²/Var(D) | Signed standardized disagreement and squared standardized disagreement with the named binding-only alternative. A defined joint model/variance, positive variance and compatible estimand are required; neither is a function probability. |Unavailable for missing variance and conditional scenario. Common conversion itself also unimplemented.|

The mean correction can connect these sections without arbitrary weights. Under a specifically declared multiplicative response model on the native normalized scale,

`P_i−B_i = k_i * f_i * c_i * theta_i * a_i`,

so

`a_i/a_WT = [(P_i−B_i)/(P_WT−B_WT)] * (k_WT/k_i) * (f_WT/f_i) * (c_WT/c_i) * (theta_WT/theta_i)`.

Each multiplier answers a named weakness and needs its own applicable measurement/model. c is the measured nuisance-response factor, not a generic comparability judgment. This proposal does **not** assume all molecular rates always obey that factorization. Nonlinear interactions or an incompatible standard require a different declared response model, or an unsupported combined cell. For this paper the fully corrected a ratio stays unknown. The displayed occupancy residual is a separately labeled conditional sensitivity case, not the full correction with missing factors defaulted to one.

Bias/repeatability loss L does not get blindly multiplied into a_i or its uncertainty: it first needs the source measurement-population link. A reported mean CV is not uncertainty of k or the SE of a mean. If a calibrated bias vector b and covariance Sigma for the *actual selected estimates* exist, residual mean-square error can be proposed as `(J_D b)^2 + J_D Sigma J_D^T` under a stated first-order error model. This is an explicit sum of squared bias and variance, not an overall reliability average. It cannot be populated here. Positive activity and low reporter coupling are not substitutes for those quantities.

## 4. Dependence, complementary evidence and apparent disagreements

- P, rho, eta, percentages, reconstructions and R decompositions share measurements. Retain primitive Jacobians and covariance once; do not add them as independent scores. Contrasts sharing WT are correlated even if mutant preparations were independent.
- GC-MS identity narrows the chemical event being evaluated. It supplies no measured ppm error, similarity score, recovery or false-identification rate in this paper. Preserve its specific witnessed interpretation, with the quantitative identity-validation cell explicitly unpopulated; do not assign it an invented 1.
- Binding and turnover jointly constrain the binding-only alternative through the declared occupancy model. They are complementary endpoints, not repeated estimates to average. Without the model link, keep both numeric results and no cross-endpoint residual.
- Table2 and Table3 give different turnover values. Do not calculate a standardized contradiction between fitted kcat and an author-reported assay turnover without the missing normalization/preparation/condition relationship. In particular the Table3 WT value206 exceeds fitted Table2 kcat124; silently fitting both to one Michaelis–Menten curve would misrepresent the source.
- Author-coupling versus displayed coupling differences (WT0.2802768, N0.5925926, double0.4839650 percentage points) are local arithmetic discrepancies. They do not calibrate an error penalty.
- H2O2 was measured; WT/N/double printed zeros retain nondetection with unknown limits. Water was calculated as (H−P−H2O2)/2. Its apparent balance supplies no independent validation. T252A peroxide33/427=0.0772834 is a conditional share of reporter consumption assigned to that measured branch under the reaction convention, not a reliability grade.
- Fig4's displayed T252N/V253N conflicts with text/table T252N/V253T. Keep panel-to-row identity conflicting. Do not silently derive a numerical chromatogram for the double-mutant row.

## 5. Specific next implementation

After the coordinator prints and discusses this proposal, implement a **versioned common-assessment request in the existing A105 compiler**, consuming actually received component rows and explicit assertion/assay/model bindings. Do not create another disconnected assay namespace. Preserve old saved forms and values. First bounded behavior: same-estimand native contrasts; Table2 central kcat/Km contrasts; typed binding-occupancy scenario and residual; exact dependencies; reason-specific partial returns. Uncertainty must use the actual cross-arm/cross-endpoint joint block and cannot be synthesized from marginal spreads. Existing215 repairs within-assay component covariance; it does not implement this cross-assay scientific comparison.

The future functions and full case-specific investigation instructions are in `FUNCTION_IO_001.md` and `INVESTIGATION_INSTRUCTIONS_001.md`. Root must print the useful proposal in conversation before code. This is design feedback, not a runtime approval stage. A bounded calculation remains useful even when complete quality compilation cannot yet be populated. A105 remains incomplete until common-sheet design and functions cover the required scientific relationships, selected LiteratureEpisodes persistence/typed delivery/reconstruction and contrasting validated cases. No new literature source is needed to expose or implement the bounded distinctions above.
