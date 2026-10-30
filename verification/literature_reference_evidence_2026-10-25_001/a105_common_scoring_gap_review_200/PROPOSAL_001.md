The present code has separate population modules for coordinated A105 numerical sections. It does not yet supply a complete common reliability or claim-specific evidence evaluation. Attribution asks how much of an endpoint belongs to the studied molecule/process. Relevance asks what functional assertion that endpoint establishes. A quantitative NADPH assay can be precise while leaving the identity and productive yield of the organic reaction product unresolved.

This is a scientific proposal for review, not adopted scoring policy, production implementation, or completion of A105. The original supplied immutable goal is unchanged. No production, test, shared integration, historical research or amendment file was edited.

## Requirement to implemented component: bounded code audit

All paths below are relative to the repository. The complete code files named in the first five rows were read; exact hashes and function boundaries are in CODE_READ_PROVENANCE_001.json. This is not an exhaustive audit of every literature implementation.

| Required scientific responsibility | Actual executable component and exact proof | What is still missing |
| --- | --- | --- |
| Reliability and method validity | `literature_calibration_recovery_calculations.py:159` populates measured/nominal recovery, signed/relative bias, inverse recovery and SD/mean when spread is explicitly SD. `literature_activity_calculations.py:102` calculates corrected endpoint and conditional JΣJᵀ uncertainty. | These are particular numerical components. No within-/between-run CV input, Z′ control-separation input, calibration-fit/blank conversion, or bias-plus-precision loss exists in these interfaces. Their complete enumerated components and input schemas prove these bounded omissions. Known-normal presence profile is not general experimental reliability. |
| Comparability outside the intended change | `literature_compiled_assay_inputs.py:41` declares u/v links specifically excluding the intended variable. `literature_compiled_assay_calculations.py:128` applies v/u only under the selected source meanings and correction stages. | A same-endpoint nuisance response must actually be measured and applicable. Different enzyme concentrations, matrices, temperatures or detectors cannot be converted to universal comparability penalties. Present partial-normalization uncertainty and bypassed-stage covariance are explicitly unimplemented. |
| Effect isolation/attribution | The same compiled calculator uses q−g, with q already sample-minus-blank; `literature_compiled_assay_inputs.py:126` rejects an enzyme-activity spike as reporter recovery. | Unknown mixed contributors are not zero. A net preparation endpoint is not automatically the studied protein's productive chemical activity. Quantitative product coupling and molecular contributor relationships remain separate. |
| Claim-specific relevance | `literature_compiled_assay_calculations.py:50` defines corrected activity as a compiled **source endpoint**; the returned sheet scope is `compiled_source_endpoint`. `literature_product_partition_calculations.py:23` calculates selected fractions, closure and their ratio. | Neither function contains an endpoint-to-identified-product conversion. Selected signal fractions are not productive rate, intrinsic specificity or molecular attribution. The broad assertion remains context, rather than a numerically evaluated relation to the actual endpoint. |
| Independence/dependence | `literature_rate_replicate_calculations.py:108` averages within actual units, then equally weights unit means; `:208` separates paired/independent/unknown contrasts. `literature_compiled_assay_inputs.py:155` tracks canonical spans and opaque dependencies; `:242` binds joint covariance to actual operand keys/units. | Dependence representation does not itself construct source covariance. Distinct namespaces are not independent experiments. Within-/between-run source precision bases still require explicit meanings; a complete cross-assay dependency account is not established. |
| Complementarity/contradiction | The compiled sheet contains only the enumerated correction/measurement/uncertainty components, with a declared `no_cross_assay_grand_score` limit; `literature_compiled_assay_render.py` preserves endpoint/assertion distinction and shared quantities. | No numerical common claim model in the inspected path connects a named weakness to the independent or shared contribution of a complementary experiment. Different endpoints/conditions and source rounding disagreements must be separated from scientific contradiction. A future joint comparison needs explicit common quantities/mean functions and covariance, not paper counts. |

The persistence paths were also read completely: `literature_calibration_recovery_storage.py` and `literature_compiled_assay_storage.py` save selected source/sheet snapshots, authenticate original operation records, and project requested rows without recalculating them. Their renderers preserve qualifications. This establishes inspected custody machinery, not an actual execution of the new proposal or a new configured-model run. Shared integration files were searched for ownership planning only; their complete behavior was not audited here.

## One original case: what is actually compared

Original paper: Application of WST-8 based colorimetric NAD(P)H detection for quantitative dehydrogenase assays, DOI 10.1186/s12858-019-0108-1. Retained original XML SHA256 `86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698`; exact byte witnesses and the actual Fig.3 native-image witness are in SOURCE_PACKET_001.json. The retained case167 report supplied context; its proposed scores are not authority. No second paper was opened.

There are distinct experimental arrangements, not one interchangeable validation:

1. **Prepared NADPH standards in buffer:** commercial NADPH amounts, 150μL, 20mM Tris pH8, 200μM WST-8/8μM 1-mPMS (Par31–32). Formazan absorbance450nm reports reducing cofactor through the reporter system. Measurements were triplicate on five days. That is repeated measurement, not fifteen independent G6PD preparations. The article does not define how the Table2 CVs pool the observations, whether calibration/validation stocks or observations are independent, or raw positive/negative control distributions.
2. **Purified human G6PD:** expressed in E.coli BL21(DE3), affinity purified, dialyzed and quantified by Bradford (Par28). Construct boundaries, allele and active fraction are not specified. WST assay: 0.1μg in150μL, pH8,10mM MgCl₂,500μM G6P,200μM NADP+,25°C,10min (Par29/33/45/58). UV assay:0.5μg in1mL with the same stated G6P,NADP+,pH,MgCl₂ and25°C, monitored340nm (Par39). Intended change is reporter/detection method; nominal enzyme concentration also differs by `(0.1/0.150)/(0.5/1)=4/3`. These are separate assay arms of the enzyme, not coexisting WT/mutant forms. Same preparation across arms is not explicitly established.
3. **G6PD spiked into serum:** 0.2μg G6PD coexists with endogenous FBS contributors; FBS-only activity is subtracted (Par37). This measures net enzyme-spike activity response, not recovery of a known NADPH amount. Existing recovery169/173 already preserves this distinction. Its missing expected-rate provenance and denominator uncertainty are source gaps, not a new detector gain to implement.

The buffer recipe omits the functional assay's G6P, NADP+, MgCl₂ and serum/lysate matrix. It therefore cannot automatically supply k or a precision distribution for the complete functional assay. A no-substrate blank (Par29) is also different from a substrate-present no-enzyme/inactivated-enzyme control: the latter addresses substrate-dependent direct reporter reduction. Par38/50 establishes that fructose and reducing agents can generate formazan without NAD(P)H. These controls address a specific alternative explanation, not the identity of an organic reaction product.

## Proposed numerical reliability component: bias and precision combined with defined meaning

Use a **relative squared measurement deviation from the stated nominal standard**, rather than a numerical category or probability of correct function.

For standard quantity N>0, measured random quantity Y with finite mean μ and SD σ:

`L = E[(Y−N)²]/N² = ((μ−N)/N)² + σ²/N²`.

This sum is the squared-error decomposition. It requires no Gaussian distribution or independence between bias and noise. It evaluates the error of a future measurement from the specified measurement population relative to its stated nominal standard, if that population's μ and σ are known. Lower L means less squared measurement deviation; it is not a calibrated confidence score or a probability.

For this source, a **proposed plug-in illustration** substitutes displayed measured amount M for μ and source CV c for σ/μ:

`L̂_basis = (M/N−1)² + (c_basis × M/N)²`.

The numerator of the second term is `(c_basis M)²`, not `(c_basis N)²`. The numerical result is dimensionless relative squared error. `100 sqrt(L̂)` is a percent relative root-mean-square deviation, retained as the same contribution in a more readable scale. Do not award an additional contribution for the root transform.

This substitution is conditional: the source has not established that its displayed M is the mean on exactly the same basis/denominator used for either CV. Thus the populated proposal is labeled `conditional_plugin`, not a source-reported MSE or a verified predictive distribution. It is also not the unbiased finite-sample MSE estimator or exact empirical average squared residual; no unavailable sample-size or pooling adjustment is fabricated. Nominal stock uncertainty remains unknown. N is the stated reference value, not established physical truth.

Table2 supplies three original NADPH contrasts:

| Prepared N (nmol) | Measured M (nmol) | Within-run CV | Between-run CV | Proposed within L̂ | Proposed within relative RMS | Proposed between relative RMS |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4.3 | 4.39 |2.2%|4.5%|0.0009425471|3.07009%|5.04849%|
| 8.6 | 8.72 |0.8%|1.7%|0.0002604983|1.61400%|2.21770%|
| 12.9 |12.98|1.5%|2.1%|0.0002662586|1.63174%|2.20215%|

For the8.6nmol row, the exact displayed relative bias is `8.72/8.6−1=0.01395348837`; the proposed within relative SD is `.008×8.72/8.6=.008111627907`. Their squares sum to `.0002604983451`. This is a justified compilation of bias and precision for a declared measurement population, with no invented weight. The source's within- and between-run CVs are **alternative precision bases**, not automatically independent variance components. Do not add their squares; between-run precision may already include within-run variation. Raw day/replicate observations and the source's estimator definition would be required to fit a hierarchical variance decomposition. Five days do not establish biological replication.

Paired extraction and sheet interface for this component:

| Reader fields, kept together | Populated cell / calculation | Necessary scientific question |
| --- | --- | --- |
| Standard analyte, matrix, method, endpoint; exact nominal and measured amount spans/units; which measurement population M summarizes | Existing recovery `M/N`, signed bias and new conditional loss operands | Are N and M the same quantity under this standard experiment? Is the nominal reference independent/uncertain? |
| Reported CV number, explicit percent/fraction unit, within-run versus between-run label, repeated unit, number of days/readings, source definition of the CV denominator and pooling | `reported_within_run_CV`, `reported_between_run_CV`; normalize percent by100; preserve source basis | Does c actually equal SD/M for the same population? Unknown/conflicting basis leaves interpreted loss unavailable, while native CV remains useful. |
| Supported M↔precision relationship, whether standard observations/stocks were held out from fitting, dependence identities | `relative_bias_squared`, `relative_variance_plugin`, `relative_MSE_plugin`; optional root display | A relationship is not established merely by adjacent rows. Source-reported, derived and proposed origins remain distinct. |

Recovery, bias, inverse recovery, squared loss and RMS reuse the same standards. They are not independent validations and must not all be added as evidence. This component also must not be added to another uncertainty model that already represents those same calibration measurements.

## Control separation: a different numerical validity section

Par49 defines `Z′=1−3(σpos+σneg)/abs(μpos−μneg)`. Its3 is the source's chosen band multiplier, not a fitted model weight here. The number evaluates separation of the selected positive/negative control distributions relative to their spreads. It does not evaluate whether G6PD produces a particular sugar product.

Table2 NADPH Z′ values are .90,.99,.98 at prepared4.3,8.6,12.9nmol. Keep them as **reported**. The underlying positive/negative means, SDs, controls and their sampling bases are not given, so numerical recalculation from source operands is unavailable. The descriptive inverse `(1−Z′)/3` gives .0333333,.0033333,.0066667 for `(σpos+σneg)/abs(mean separation)`, conditional on the source formula. It is the same reported statistic in another scale, not a second control result. In particular, do not use the CV as σpos or infer the negative-control SD from it: the source does not establish that population identity.

Additive scientific correction: Par49 says Z′ lies between0and1, but its displayed formula permits negative values when control bands exceed mean separation. A future deterministic implementation must preserve negative Z′, zero or signed mean differences as appropriate, SD≥0 and unknown means/spreads. It must return undefined for zero separation, rather than clamp, divide by zero or invent a reliability floor. No paper-specific acceptance threshold becomes a universal A105 scoring rule.

## Calibration and blank arithmetic: explicit combination, no borrowed signal

The actual Fig3B inset prints `A = .0999 N + .0166`, R²=.9994, with A absorbance and N nmol NADPH. Par31/46 establish the standard's buffer context and0–19nmol fitted range; Table1 gives NADPH LLOQ.4nmol and ULOQ19nmol. R² is a property of one fitted calibration, not residual variance, validation independence or assay specificity.

For one raw measurement under that applicable calibration, `N=(A−b)/m`. For sample and matched blank using the **same slope and intercept**:

`Nnet = ((As−b)−(Ab−b))/m = (As−Ab)/m`.

For a source-supported elapsed interval t and amount basis, `q = (As−Ab)/(m t)`nmol/min; mass normalization, if appropriate, is another division by assayed mass. This is a sum and multipliers with physical meanings, not an average of validity labels. It requires actual source signals, an applicable matrix/relation and supported time interval; none of those raw signals is provided for the selected G6PD assays. The conversion therefore remains unavailable, not zero.

The fitted intercept corresponds algebraically to `.0166/.0999=.166166166nmol`. Subtracting b again after an already matched-blank-corrected difference produces a downward amount error of .166166166nmol. Relative to8.6nmol that is−1.93216%; relative to the reported.4nmol LLOQ it is−41.54154%. These are consequences of the published fit and correction operation, **not observed sample errors or invented absorbance measurements**. They show why correction stages change reliability materially. Separate sample/blank calibration fits do not necessarily cancel their intercepts.

For matched raw signals the proposed first-order variance is `JΣJᵀ`, with operands `(As,Ab,m,t)` and `J=(1/(mt),−1/(mt),−q/m,−q/t)`. The common intercept cancels before propagation. Unknown covariance stays unknown; source raw calibration/signal covariance is absent. This extends the physical calibration route; the existing optical calculator is explicitly negative NADH-depletion extinction conversion with ε/path length, not positive WST-formazan source-fit conversion. It must not be repurposed by entering m as ε.

## Claim-specific relevance and complementarity remain scientific work

For the narrow assertion “this preparation supports G6P-dependent NADP+ reduction under these conditions,” a calibrated net NADPH-equivalent endpoint is relevant. Quantifying its origin in the studied G6PD remains an attribution question; purification is not measured zero contamination. For the more specific assertion of a named organic product, the missing bridge is productive coupling to identified product.

A proposed numerical bridge, when the necessary measurements exist, is:

`φ = qP/(νP/H qH)`, then `aP = νP/H × φ × aH`.

Here qP is the background/contaminant-corrected measured formation rate of the **identified** organic product, qH the corresponding corrected cofactor-equivalent rate on the same amount/time/condition basis, and νP/H the supported stoichiometric product-per-cofactor coefficient. φ evaluates the measured productive fraction/coupling relative to that declared chemical relation; it is not a universal applicability probability. Its numerator, denominator and stoichiometry must retain actual subjects/constructs, preparations, aliquot/time relationships, response calibrations and exact dependencies. Product mass agreement alone does not supply qP. A ratio above1 remains a diagnostic inconsistency/limitation, not a clamped valid fraction. qH=0 leaves φ undefined while direct qP may remain useful; signed or bounded rates keep their domains.

For this paper qP and its source-supported stoichiometry/coupling measurement are missing, so φ and aP cannot be numerically populated. That is a **source-information gap**. The inspected A105 interfaces also do not implement this bridge, which is a separate **implementation gap**. Printing an unknown φ is not completion of claim-specific relevance. Literal chemistry/stoichiometry facts can also inform A110; this proposal does not merge A110 into A105 or implement final cross-axis credit.

The450nm versus340nm assay is complementary regarding WST-specific reporter interference. Both depend on NADPH, so they share a weakness for organic-product identity and possibly common cofactor/stock errors. Table3 G6PD activities are12.51±.36 versus14.88±.39nmol/min/μg (mean±SD, triplicate). Their descriptive difference is−2.37 and ratio.840725806; these are already representable native arithmetic, not a new method to code. Their nominal enzyme concentration also differs4/3. No measured concentration-response correction, pairing or covariance is supplied, and a nonsignificant test is not proof of equivalence. Keep the two scoped endpoints and their differences; do not declare independent functional confirmation, multiply two reliability grades, or label them scientific contradiction without common-condition semantics. Direct identified-product quantification would address the shared product-identity/coupling weakness. A matched substrate-present no-enzyme control would quantify substrate-dependent reporter interference. Neither new measurement is performed or claimed here.

Do not multiply φ by another correction which subtracts the **same** off-pathway signal. The bridge and correction sections need a shared physical contribution/correction-stage map. Otherwise adding a complementary measurement can manufacture support or remove the same contaminant twice.

## Proposed instructions and separate implementation ownership

Investigation TASK proposal, for root to print and review before coding:

> Determine what the activity measurements establish about the studied molecule under the stated conditions. Identify the measured reporter or chemical species, the asserted reaction and the tested alternatives separately. Examine standards, matched blanks, interference controls and replicate structure. Distinguish the deliberately tested variable from other condition/amount changes. Determine which measurement population each reported precision statistic describes and whether its mean/denominator belongs to the same experiment. Preserve calibration range, already applied corrections, shared standards and missing relationships. A precise reporter response does not identify an organic product or establish its productive coupling. Use the published measurements to answer these specific questions; possible functions can emerge from the evidence. Deterministic readers and calculators populate the requested numerical components.

This TASK is not the sheet. A reader's separate constrained interpretation contract should ask concrete questions: `mean_precision_population = same / different / unknown / conflicting`; `precision_scope = within_run / between_run / between_preparation / unspecified`; `cv_denominator = displayed_measured_mean / other_reported_mean / unknown / conflicting`; `validation_relation = held_out_observations_and_stock_supported / shared_fit_or_stock / unknown / conflicting`; `blank_stage = raw_pair / already_differenced / other / unknown / conflicting`; `calibration_relation = applicable_same_matrix_endpoint / different / unknown / conflicting`. Evidence witnesses must support actual meanings. These are semantic values, not numeric grades. Unknown inputs preserve native partials; a separate calculator performs all arithmetic. No additional model call is needed to compose a report.

Before new coding, define a versioned `measurement_validation` section with exact source-number selectors, explicit precision units/bases and calibrated relation operands. Proposed ownership:

- One fresh owner implements new `literature_measurement_validation_inputs.py` and `_calculations.py`, with closed sheet schema and finite conditional-model meanings. Reuse existing recovery components via actual received selections; do not duplicate169/173 arithmetic or reinterpret old receipts. That owner also owns narrowly scoped new tests. Optional raw-control and raw-day routes remain distinctly unimplemented until their actual contracts/estimators are designed; reported values are not raw routes.
- A separate fresh owner, after the pure contract is frozen, implements corresponding `_storage.py`, `_render.py` and `_prompt.py`: selected action, immutable input/calculation snapshots, requested typed rows and reconstruction without reacquisition/recalculation. Reported CV/Z′ and proposed plug-in losses retain distinct origins and relationship limits. A new loss remains unavailable for unestablished precision-population links, even if a controlled proposal fixture can illustrate it.
- Root alone owns shared changes in `literature_episodes.py`, `episode_services.py`, `communication.py`, `literature_experimental_prompt.py` and `literature_numerical_return_presentation.py`, and any authorized compiled-selector change. Current references in these shared files were located, not fully audited. Read complete affected paths before changing them. Preserve existing kinetic196, recovery173, channel188 and ion194/199 ownership/frozen behavior. No changes to continuation, credit projection or historical bindings.
- The endpoint-to-functional-product bridge needs its own concrete measured-product case and reviewed typed scope before implementation. Do not treat the present null example as permission to code a generic relevance grader. A later fresh workload should use a case that actually measures product/cofactor stoichiometry, with its own required post-paper reset.

These are subsequent workload/file-boundary proposals. No new files named above have been created and no production API is adopted by this report.

## Validation and full A105 gaps

The owned oracle independently cross-checks exact Fraction arithmetic with65-digit Decimal calculations in10 checks and authenticates the retained original XML hash and selected byte spans. Three standard rows have18 exact numeric field witnesses;16 Methods/Results paragraphs,4 tables and actual Fig3B printed fit retain source custody. It imports no production module, invokes no provider/model, executes no scientific episode and runs no production test. Fixture/model-backed execution is not claimed. POST_AUDIT_RESET_001.json and POST_WST8_RESET_002.json record this agent's actual complete authority rereads; truncated combined displays were reread, and latest human text was displayed last. Root/receiving agents must perform their own reset after this paper-specific packet before interpreting/coding from it.

Unfinished A105 responsibilities remain: full claim-specific endpoint/product linkage; method-specific validity relationships across relevant assay types; source-grounded nonintended-condition corrections; mixed-contributor attribution; valid partial/bounded uncertainty and covariance production; preparation-level replication and distinct precision populations; complementary measurements resolving named alternatives without duplicate credit; and scientific contradictions at matching subjects/endpoints/conditions. The proposed relative-loss component addresses one part of reliability, not those other responsibilities. Current local arithmetic and operation counts do not establish a completed common sheet or fullA105 adequacy. The broader immutable literature goal, later appropriate literature axes, ordinary LiteratureEpisode selected execution and typed scientific handoff remain active work. W05 target correspondence/final annotation-credit compilation is untouched.
