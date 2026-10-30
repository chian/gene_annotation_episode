# A105 specificity case 038: one reference molecule, three separately assayed substrates

Research proposal for feedback, 2026-10-26. This advances reference-function discrimination, not a target-transfer calculation or an accepted complete A105 sheet. Source: Hatzios, Iavarone and Bertozzi (2008), *Rv2131c from Mycobacterium tuberculosis Is a CysQ 3′-Phosphoadenosine-5′-phosphatase*, DOI 10.1021/bi702453s, [primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC2711008/). All measured numbers below come from this one paper; no synthetic measurements are introduced.

The useful conclusion is **PAP has much greater reported apparent catalytic efficiency than IMP and FBP for the purified Rv2131c construct in the protocols actually tested**. This differs from proving exclusive PAP activity, substrate preference at a single shared condition, or the dominant physiological reaction in M. tuberculosis. Both alternative substrates had reported positive activity. PAPS has no usable kinetic comparison here.

## Experimental definitions before numerical conversion

The source gene was PCR-amplified from **M. tuberculosis H37Rv genomic DNA**, cloned into pET28b with an **N-terminal His6 tag**, expressed in **E. coli BL21(DE3)**, enriched using PAP affinity resin and further purified by size exclusion. The paper describes an approximately 0.8-kb amplicon; a residue-level construct-boundary mapping was not independently established. The measured intact-protein mass was **30578 ± 1 Da**, compared with **30578.5 Da predicted after initiator methionine loss**, and peptide mass fingerprinting covered approximately **83%** of sequence. These are preparation-identity checks, not target alignment scores, purity percentages, or measured zero contaminant activity. Sources: Methods passages 14, 18–19; Results passage 42 in the saved BioC derivative.

The kinetic comparator is **the same named reference molecule and construct acting on distinct chemical substrates**. PAP, IMP (myo-inositol 1-phosphate, not inosine monophosphate), and FBP (fructose 1,6-bisphosphate) were assayed **separately**, not in a competing-substrate mixture. There is no mutant-versus-wild-type protein comparison in Table 1, and no comparison protein replacing another. A common expression/purification protocol does not prove that every assay used the same physical purification batch.

The intended variable is substrate identity. Other protocol variables also changed:

| Condition or measurement | PAP arm | IMP arm | FBP arm |
|---|---|---|---|
| Temperature | 30 °C | 30 °C | 30 °C |
| Tris concentration | 50 mM | 50 mM | 50 mM |
| pH | 8.5 | 9.0 | 9.0 |
| MgCl2 | 0.5 mM | 10 mM | 10 mM |
| Enzyme concentration | 5 nM | 110 nM | 110 nM |
| Reaction duration | 4 min | 15 min | 15 min |
| Substrate range | 0.625–50 µM | 1–5.5 mM | 90–900 µM |
| Measured quantity for initial rates | AMP-assigned product by ESI-MS with GMP internal standard | Released inorganic phosphate by malachite green | Released inorganic phosphate by malachite green |

Methods passages 21–34, Results 53–66, Fig. 6 caption, and Table 1 footnote bind these fields to the kinetic rows. IMP/FBP conditions were selected from previously described optima. Thus the observed efficiency contrast is a **protocol-specific comparison of separately optimized assays**, not a condition correction already measured by the paper. Enzyme concentration and time differ by 22-fold and 3.75-fold; MgCl2 differs by 20-fold. These descriptive ratios are not comparability penalties. Correct molar normalization and linear rates can accommodate different enzyme amounts and durations, but cannot itself remove pH, metal, detector or model differences.

For phosphate assays the paper explicitly used enzyme-free controls to account for substrate background hydrolysis. Numeric blank values and blank uncertainty are not reported here. The ESI progress experiment included a zero-time sample; this is not automatically a fully quantified matched blank for every kinetic concentration. The paper quantified product as AMP using a GMP response normalization factor of **1.5 ± 0.1** from samples collected over three weeks. That factor is not a generic recovery fraction, and its exact equation convention is not reconstructed because the BioC representation omits rendered equations 1–3. No correction factor is applied again to the already fitted Table 1 estimates.

## Populated native cells, not category grades

Table 1 reports these averages from **three independent experiments**. Its footnote does not identify the ± statistic as SD or SEM, nor define biological-preparation independence. The SD language in the Fig. 3 and Fig. 4 captions concerns those figures; it cannot be imported into Table 1.

| Substrate | Km (µM) | kcat (s−1) | Reported kcat/Km (µM−1 min−1) | Untyped error magnitude / efficiency |
|---|---:|---:|---:|---:|
| PAP | 8.1 ± 3.1 | 5.4 ± 1.1 | 42 ± 8 | 0.1904761905 |
| IMP | 7110 ± 1070 | 0.31 ± 0.13 | 0.0027 ± 0.0015 | 0.5555555556 |
| FBP | 566 ± 107 | 0.24 ± 0.05 | 0.025 ± 0.001 | 0.04 |

The last column is a descriptive relative **untyped** error magnitude. It is not a coefficient of variation, mean standard error, inverse-variance weight, confidence interval or reliability score. Reported count=3 remains separate from independent preparation count=null.

Let ηP, ηI and ηF denote the **reported apparent efficiency estimates**, all in µM−1 min−1. They are fitted kinetic parameters, not observed raw rates. The following partial sheet is populated by deterministic arithmetic:

| Numerical cell | Defined operands/calculation | Actual value | Evaluated meaning |
|---|---|---:|---|
| `efficiency_PAP` | Table 1 ηP | 42 | Reported apparent low-concentration catalytic-efficiency parameter for PAP protocol |
| `efficiency_IMP` | Table 1 ηI | 0.0027 | Corresponding parameter for IMP protocol |
| `efficiency_FBP` | Table 1 ηF | 0.025 | Corresponding parameter for FBP protocol |
| `efficiency_difference_PAP_IMP` | ηP−ηI | 41.9973 µM−1 min−1 | Protocol-specific parameter contrast |
| `efficiency_difference_PAP_FBP` | ηP−ηF | 41.975 µM−1 min−1 | Separate alternative contrast |
| `efficiency_ratio_PAP_IMP` | ηP/ηI | 15555.55555556 | Preference magnitude against the specified IMP alternative in these protocols |
| `efficiency_ratio_PAP_FBP` | ηP/ηF | 1680 | Preference magnitude against the specified FBP alternative in these protocols |
| `log_efficiency_contrast_IMP` | eI=ln(ηP/ηI) | 9.652173124255 | Signed discrimination effect, equality boundary 0 |
| `log_efficiency_contrast_FBP` | eF=ln(ηP/ηF) | 7.426549072397 | Second signed discrimination effect |
| `variance_log_contrast_IMP/FBP` | Supported joint uncertainty model | null | ± statistic, cross-assay covariance and fit model not established |
| `common_condition_log_contrast_IMP/FBP` | e observed − measured log condition-response difference | null | No matched-condition substrate-response mapping supplied |
| `source_profile_log_ratio`, `source_signed_index` | Supported profile calculation below | null | Numerical score inputs absent; no default weight or zero/one imputation |

`60 × mean(kcat)/mean(Km)` gives **40**, **0.002616033755**, and **0.025441696113** for PAP/IMP/FBP. These are quotients of the printed parameter means and differ from Table 1's **42**, **0.0027**, **0.025**. Do not silently replace the directly reported efficiency averages or treat the two representations as independent evidence. Rounded summaries and averaging ratios versus taking ratios of averages can differ; the paper does not supply enough raw per-experiment values to resolve the precise cause.

## How these numerical cells enter actual scoring, and exactly what cannot be filled

The useful addition to current sheet sections 3 and 6 is a **kinetic-efficiency contrast with its own endpoint/units/condition scope**. Do not insert η into the existing positive-*rate* fields merely because its ratios are dimensionless. Raw endpoint rates, turnover kcat, Km and catalytic efficiency are distinct measurements/parameters.

For a supported log-summary model, define z=(lnηP,lnηI,lnηF) and its actual covariance Σ. The contrast transform is

    L = [[1,−1,0],[1,0,−1]], e=Lz, V=LΣLᵀ.
    VII=ΣPP+ΣII−2ΣPI
    VFF=ΣPP+ΣFF−2ΣPF
    VIF=ΣPP−ΣPF−ΣPI+ΣIF.

These explicit sums explain why the **same PAP estimate belongs to both contrasts** and why two preference ratios are not two independent replications. If Σ is on the original efficiency scale, first-order propagation uses D=diag(1/ηP,1/ηI,1/ηF) and V=LDΣηDᵀLᵀ; it is an approximation, not an exact normal distribution inferred from arithmetic. A physical preparation/calibration shared across rows remains shared even if differently labeled.

Under the historical sheet's explicitly proposed **known-normal signed-effect** route, and only if that model and V are supported:

    S_IMP=eI|eI|/(2VII)=46.58222301029741 / VII
    B_IMP=tanh(S_IMP/2)=tanh(23.291111505148706 / VII)
    S_FBP=eF|eF|/(2VFF)=27.576815562362633 / VFF
    B_FBP=tanh(S_FBP/2)=tanh(13.788407781181316 / VFF).

Here S is a difference of best fitted log likelihoods between the specified inequality and its complement; B is the sheet's **proposed** bounded transformation, not a probability of function. The available measured operands supply the displayed coefficients, but **VII/VFF and therefore S/B remain null**. No hypothetical variance is supplied to make a final score print. Untyped ± and n=3 do not justify promoting estimated sampling uncertainty into known variance. A suitable finite-sample or original-fit likelihood would need its actual inputs rather than a model choice made for a large score.

If the asserted reference-function distinction requires **both** PAP>IMP and PAP>FBP, retain one joint assertion. For these positive observed contrasts in an unrestricted joint known-normal effect model, distance to the complementary union of halfspaces gives

    S_both = min(46.58222301029741/VII, 27.576815562362633/VFF)
    B_both = tanh(S_both/2).

This is a conditional joint-profile derivation, not the sum of two independent likelihoods. For other directions, boundaries or physical restrictions, use the actual constrained joint model. No final annotation aggregation is performed. For an assertion at a **common biochemical condition**, numerical condition-response corrections must enter e and its covariance first; there is no justified new generic similarity multiplier. The paper permits native contrast cells plus explicit unavailable scoring cells, not a complete reliability score. This gap is a useful result of the case rather than permission to substitute a categorical grade.

## Specific method limitations and what each complement addresses

- **Assay sensitivity versus kinetic design:** colorimetric PAP attempts placed Km below about 20 µM, near that assay's detection limit, motivating ESI-MS. The 20 µM statement is not an instrument-calibrated AMP-product detection threshold, not an alternative-substrate nondetection limit, and not zero activity. ESI-MS supplies a more sensitive product readout but is susceptible to Tris-dependent ion suppression. No measured LOD/noise distribution for the final PAP assay is provided.
- **Initial-rate validity:** the PAP progress curve was linear at 25 µM substrate from 0–6 min (R²=0.993); 4 min corresponded to roughly 37% conversion. At low PAP concentrations the authors could not confirm continued linearity at 4 min. The reported possible initial-rate underestimation is an unquantified systematic limitation, not a variance of zero or a known signed correction to η. A shorter, sensitivity-validated progress series at those concentrations would address it; the high-concentration progress curve does not settle it.
- **Fitted alternative parameters:** IMP's maximum assayed concentration, 5500 µM, is below its reported Km=7110 µM (range maximum/Km=0.7735583685). Substrate inhibition limited the ranges for IMP and FBP. This raises an extrapolation/parameter-identification limitation, particularly for IMP kcat and Km. It does not itself falsify η or prescribe a quality penalty. Retained per-concentration rates and an explicit inhibition-aware fit could reveal whether η is identifiable despite weak saturation coverage.
- **Comparability versus effect isolation:** differing pH/metal/detection conditions limit a shared-condition preference claim. Enzyme-free hydrolysis controls address substrate/background phosphate release; affinity enrichment, size exclusion and protein mass/fingerprinting address preparation identity and gross impurity. Neither proves measured contaminating catalysis is exactly zero. A matched substrate panel on the same preparation with detector cross-validation would address method/condition differences; it is not provided by the same table's reprinted ratios.
- **Chemical resolution:** PAP quantitation uses a product assigned as AMP; IMP/FBP use released phosphate. A general phosphate endpoint does not identify the organic product or which FBP phosphate was removed. Mass alone also does not distinguish AMP positional isomers. Product identity/site resolution beyond the authors' assignment is not independently demonstrated by this text-only inspection; no product m/z or mass-error cell is invented. Orthogonal product separation/identity analysis addresses this distinct limitation.
- **In vivo complement:** the paper separately adds pBAD18-Rv2131c to an E. coli strain with native cysQ disrupted by a transposon, comparing empty vector and sulfite supplementation on M9+arabinose at 24 h. Intact native CysQ is not coexpressed as the reference partner. Restored growth supports functional substitution in that host and addresses whether purified-enzyme activity has any cellular relevance. It does not measure intracellular PAP/PAPS conversion separately, protein abundance equivalence, or the physiological importance of each reaction in M. tuberculosis. No numerical growth rate is extracted from plate appearance, and no A106 grader is built here.
- **PAPS is an unresolved kinetic alternative:** decomposition to PAP and inhibitory lithium in commercial preparations obstructed kinetic characterization. The paper's qualitative, unshown TLC observation does not supply kcat/Km. PAP contamination is competing substrate, not an exact zero PAPS measurement or proof that PAP and PAPS coexist in the three Table 1 substrate assays.

The apparent efficiency table, its ratios, summary prose, and abstract are representations of the same kinetic evidence. Three independent experiments as reported are not automatically three independent protein purifications. The calibration series and progress curve support method aspects; they are not extra independent demonstrations of preference. Complementation is complementary at a different endpoint, not another η measurement to average.

## Paired reader/contract proposal for later feedback

Keep investigation instructions, numerical sheet definitions and readers/calculators separate. The smallest justified extension is a source-bound kinetic-parameter extraction/contrast path, preserving all existing rate and assay paths.

| Proposed extraction fields, each with source witnesses | Numerical sheet cells populated | Missing/conflicting treatment |
|---|---|---|
| `molecule, organism, expression_host, construct, purification, preparation_identity`; `substrate_identity`; `substrates_separate_or_mixed` | Subject bindings, not scores; chooses interpretation of numeric contrasts | Unknown preparation identity remains unknown, not same batch; conflicting identities retained |
| `parameter_kind` (Km/kcat/kcat_over_Km); numerical value/unit; substrate row; model/condition witnesses | η, Km, kcat with exact dimensions; compatible-unit ratios/differences/log contrasts | Never place Km or η into raw-rate slots; unsupported unit remains unavailable |
| `uncertainty_magnitude`, `uncertainty_kind`; count and repetition unit separately; full fit/cross-row covariance if supplied | Error-magnitude ratios; supported V and score cells only when their inputs exist | Table ±→unspecified, n3→reported experiment count3; SD/SEM/prep independence stay null |
| `endpoint_entity`, detector, organic-product identity resolution; blank/recovery/calibration roles | Method-specific quantities and applicability of kinetic inference | Phosphate is not automatically identified organic product; GMP response factor is not generic recovery |
| Conditions per substrate and intended change; explicit same-endpoint condition-response control if measured | Native contrasts, optional common-condition correction and propagated uncertainty | Different conditions preserve qualified native contrast; no invented correction/quality weight |
| Independent observation/fit identities and shared parameters/calibration | LΣLᵀ and joint assertion profile | Shared PAP numerator stays shared; printed summaries do not add rows |

An aspect-specific instruction draft for feedback: **“Determine what the Rv2131c substrate assays establish about PAP preference relative to the separately tested IMP and FBP alternatives. Identify the molecule/construct, endpoint, parameter meaning, assay conditions, errors and repetition basis. Select exact source witnesses for the numerical operands. Distinguish a comparison across the published protocols from a comparison at a common condition, and identify any measured response mapping between them. Preserve positive alternative activities, unsuccessful kinetic characterization, and reported systematic limitations.”**

Allowed meanings should be narrow: `parameter_kind={Km,kcat,kcat_over_Km,unknown,conflicting}`; `substrate_arrangement={separate_assays,mixed_substrates,unknown,conflicting}`; `comparison_scope={reported_protocols,common_condition_supported,condition_mapping_unavailable,unknown,conflicting}`; `error_statistic={sd,sem,confidence_interval,unspecified,unreported,conflicting}`. A known answer needs its actual supporting passage; conflicting answers retain distinct contradictory witnesses. “Three independent experiments” does not alone select preparation independence or a normal model. These enums describe meanings and are not coded numerical scores. This draft is not wired TASK text.

The existing `literature_rate_native_inputs.py` has useful witnessed-number, uncertainty and per-arm source machinery, but RATE_UNITS lacks catalytic-efficiency dimensions and the rate calculator's statistical route does not implement the above kinetic log-contrast. `literature_ratio_reader.py` parses a narrow reported-percent expression and cannot read this table. `literature_assay_inputs.py` accepts q,g,k,E,u,v concentration-rate correction operands; fitting a Km or η into them is invalid. Thus a new kinetic parameter/contrast variant is justified; expanding existing rate meanings silently is not. Current native rate selections should continue returning partial input information, not pretend unsupported efficiency units are measured rates. No production edits, new prompt wiring, reader integration or episode model run were performed.

A targeted next step, if this case is selected for implementation, is to define that kinetic input/return variant, parse this one primary Table 1 plus its binding Methods/footnote, and verify the native contrasts and explicit unavailable S/B. The source's missing error semantics and common-condition mapping are scientific gaps; an executable reader cannot manufacture them. No broader literature sweep or claim of A105 completion follows from this packet.

Additive denominator clarification: kcat is normalized using the assayed enzyme concentration, with concentration obtained from UV absorbance using the stated extinction coefficient **46350 M−1 cm−1**. The source does not report active-site titration or the fraction of catalytically active protein. The values are therefore apparent parameters for this preparation/normalization. If the same unknown multiplicative enzyme-amount calibration applies to both substrates, it cancels in their efficiency ratio and must not be counted twice as independent error or an extra reliability multiplier. Whether precisely the same physical stock/calibration was shared across every independent experiment remains unknown here.
