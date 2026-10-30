# Case167: measured NADPH calibration and enzyme-spike recovery

Research proposal only, A105. No production code, runtime, W05, controller, or historical record was changed. This one case supplies numerical validity components and exposes limits; it does not complete A105.

Original paper: [Application of WST-8 based colorimetric NAD(P)H detection for quantitative dehydrogenase assays](https://doi.org/10.1186/s12858-019-0108-1), [PMC6454709](https://pmc.ncbi.nlm.nih.gov/articles/PMC6454709/). The exact XML was acquired from [Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6454709/fullTextXML), SHA256 `86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698`. It is CC-BY4.0; source measurements below retain attribution. Original XML, seven publisher figures, URLs and digests are under `source/`. Numerical table cells and byte-exact XML witnesses are in `selected_operands.json` and `source_witnesses.json`.

## Experimental definition

The focused functional assay is human glucose-6-phosphate dehydrogenase (G6PD), expressed in *E. coli* BL21(DE3), affinity purified, dialyzed, and quantified by Bradford (Methods Par28). Allele, construct boundaries, active fraction, and numerical purity are not established in this article. A separate commercial Bacillus GDH model is not a human G6PD replicate.

G6PD reactions use 0.1ug enzyme in150uL, 20mM Tris-HCl pH8.0,10mM MgCl2,500uM glucose-6-phosphate (G6P),200uM NADP+,200uM WST-8;25C,10min (Par29,33,45,58). WST-8/1-mPMS converts NADPH reducing capacity into formazan absorbance at450nm with600nm reference. WST-8 is a reporter reagent; the assayed enzyme is G6PD. This endpoint bears on G6P-dependent NADP+ reduction. It does not measure the sugar reaction product's identity or quantify the fraction of signal due to that product formation.

There are three distinct experiments with different numerator/denominator meanings:

1. **Buffer NADPH measurement validation:** known NADPH amounts are measured with the same WST-8 detection chemistry in150uL,20mM Tris pH8,200uM WST-8/8uM1-mPMS (Par31–32;Table2). The recipe omits assay G6P,NADP+,MgCl2 and sample matrix. Thus it validates detector response in that buffer; exact full-assay matrix equivalence is not shown.
2. **FBS enzyme-spike recovery:**0.2ug human G6PD is added to1.5uL fetal bovine serum; measured activity of FBS alone is subtracted; triplicate readings are reported (Par37;Table4). The intended change is enzyme addition to an existing serum matrix, so endogenous contributors coexist with the spike. The reference denominator is the paper's expected activity, not a measured amount of NADPH. Its derivation is not provided. This is actual same-functional-assay activity recovery. It combines matrix modulation of catalysis and detector response; it cannot isolate either one.
3. **WST-8 versus340nm method comparison:** purified G6PD activity is normalized perug protein for both methods (Par33,39;Table3). This is not substitution of one enzyme variant for another. Reporter chemistry/method is the intended variable. Conditions match in pH,temperature,G6P,NADP+ and nominalMgCl2, but enzyme concentration differs:0.1ug/0.150mL versus0.5ug/1mL, ratio4/3. This additional difference could affect the response. A measured concentration-response correction is absent.

## Paired numerical sheet and extraction proposal

These are aspect-specific numerical components, not category grades or a paper-wide reliability score. Every source amount must keep its analyte, matrix, endpoint, unit and experiment linkage.

| Meaning / exact source inputs to extract | Numerical sheet cell and calculation | Populated result | Scope and limitation |
|---|---|---:|---|
| Table2 NADPH prepared4.3nmol, measured4.39nmol | Recovery r=M/N; relative bias100(r−1) |1.02093023; +2.093023%| Buffer NADPH quantitative measurement check |
| Table2 NADPH prepared8.6nmol, measured8.72nmol | Same r=M/N and bias |1.01395349; +1.395349%| Independent unknown sample has not been corrected |
| Table2 NADPH prepared12.9nmol, measured12.98nmol | Same r=M/N and bias |1.00620155; +0.620155%| Recovery is concentration-specific; three points do not supply a universal constant |
| Fig3B actual printed fit, NADPH | A=mN+b |m=0.0999AU/nmol;b=0.0166AU;R²=.9994| Source-reported fit in0–19nmol;Table1 LLOQ.4nmol,LOD.29nmol. No residual SD,point data or slope uncertainty supplied |
| Table2,8.6nmol NADPH row | Source-reported within-run and between-run CV |0.8%;1.7%| Distinct precision meanings; not false-positive probability or known variance |
| Table3 purifiedG6PD WST-8 mean12.51,SD.36nmol/min/ug | Descriptive relative spread SD/mean |.02877698 (2.877698%)| Triplicate assay readings; independent preparations not established |
| Table4 G6PD expected1.024,measured1.235±.004nmol/min | Activity recovery1.235/1.024;excess1.235−1.024 |1.2060546875;+.211nmol/min| Net FBS spike recovery; expected-rate provenance and its uncertainty unreported |
| Table4 G6PD measured mean1.235,SD.004 | Descriptive CV .004/1.235 |.00323887 (.323887%)| Does not include expected denominator uncertainty |
| Table3 G6PD WST-8 andUV specific activities12.51 and14.88 | Method contrast12.51/14.88;fractional difference ratio−1 |.84072581;−15.927419%| Matched endpoint but unequal enzyme concentration; not an experimentally isolated detector-gain factor |
| Par33,39 mass and volume | Concentration comparability(.1/.150)/(.5/1) |4/3| Quantifies a non-intended difference; no arbitrary comparability grade |

The buffer standard measurements are actual experimental numbers, replacing the earlier synthetic9.8/10 example for this narrowly scoped validity aspect. They do not fill every operand of `(q−g)*v/(k*E*u)`.

Explicit compilation is physical arithmetic, not an intuitive average:

- The calibration relation is the sum `A=mN+b`; its inverse is `N=(A−b)/m`.
- For **matched same-matrix** sample and no-reaction blank with the same calibration relation, the intercept cancels: `rate=(A_sample−A_blank)/(m*t)`nmol/min. Divide by assayed protein mass only for a per-mass activity. If the absorbance has already been blank subtracted, do not subtract the fitted intercept again. A source-supported linear rate interval is still required.
- Only an independently justified applicable measured recovery `r` supplies another multiplier `1/r`. At the8.6nmol buffer check, `1/r=.9862385321`; it is not applied to G6PD or serum. Correcting8.72 by the r derived from8.72 merely returns8.6 algebraically and supplies no independent validation. Likewise the FBS inverse response `.8291497976` is a numerical descriptor, not an established reporter correction for another sample.
- Combining unknown components is unavailable. No sum of dimensioned activity,bias,CV andR² is justified. No independence or overall reliability weight is inferred. W05 aggregation remains untouched.

## Uncertainty, contradictions, isolation and specificity

Par43 labels results mean±SD. Buffer validation is triplicate on five successive days (Par32); this establishes repeated measurement occasions, not15 biological preparations. Table2 precision is retained as reported rather than reverse-engineering pooled SD from an unspecified CV calculation. FBS expected-rate uncertainty, pairing, covariance, calibration covariance and independent preparation counts remain unknown.

For FBS G6PD, Table4 reports recovery120.57±.33%, while arithmetic on displayed rates gives120.60546875%. If expected1.024 were exact and fixed, the displayed rateSD.004 would give recoverySD.390625percentage points, rather than.33. Preserve both source and derived values; unavailable unrounded data and denominator uncertainty prevent reconciliation. Also, Table3's12.51nmol/min/ug times the0.2ug spike is2.502nmol/min, not Table4's expected1.024. Do not silently bind Table3 as that denominator. The authors' prose characterizes recovery as within80–120%; the numerical Table4 G6PD value is120.57%. That wording supplies no accepted reliability threshold.

The no-substrate background subtraction is described (Par29), and the FBS-only rate is subtracted (Par37), but numerical uncorrected sample/blank pairs are not reported. Thus matched blank magnitude,effect fraction and sample/blank ratio are unknown. The340nm Methods calls its blank omission “glucose substrate,” creating a wording ambiguity for G6PD's G6P assay; do not silently resolve it from familiarity.

Fig5 andPar38/50 directly test signal without NAD(P)H. Fructose and reducing agents can produce formazan independently. This is a measured assay-specific weakness, not an abstract quality warning. No raw numeric interference table is supplied, and no graph values were invented here. A substrate-present no-enzyme or appropriately inactivated control would quantify this contribution under the relevant assay condition; a substrate-omission blank alone cannot remove substrate-dependent reporter chemistry. Direct chemical product quantification would address reaction-product identity and productive coupling; its quantitative attribution fraction remains unknown here. The340nm comparison is complementary reporter information, while both readouts depend on NADPH; it is not independent proof of sugar-product identity.

The article's functional screening application (Par36,55;Table6) uses crude *E. coli* lysate expressing an uncharacterized *B.pseudomallei* SDR, subtracting lysate without SDR. It does not establish the exact same calibration matrix. Substrate doses are only50–250mM collectively, so an activity ratio across substrates would not establish intrinsic selectivity. Neither the FBS G6PD recovery nor buffer NADPH recovery may be transferred to this SDR screen as knownk. This preserves possible biological functions emerging from the investigation without forcing a specific annotation.

## Proposed aspect-specific TASK wording

**Investigation insert, proposal only:** Examine the activity experiments that could explain the supplied sequence or selected material. Identify the assayed molecule, input, measured endpoint and proposed output separately. Look for numerical standard measurements, assay-background controls, reporter-interference controls and matched comparisons that establish whether the reported activity is measurable and attributable under those conditions. Distinguish recovery of an added analyte from recovery of an added enzyme's activity. A calibration in buffer does not establish response in serum or lysate. Preserve the measurements, the experimental links they establish and unresolved alternatives; possible functions may emerge from the evidence. Keep scientific task detail separate from factual prior-work steering.

**Calibration extraction/judgment TASK, proposal only:** For the selected standard or spike experiment, identify what was physically added and what was measured. Return the exact nominal/measured quantities,units,uncertainty labels,background treatment and calibration range from the supplied source. Choose a supported meaning: analyte-amount measurement validation,enzyme-spike activity recovery,or unresolved; these are operand meanings,not grades. Determine whether the analyte,matrix,reagent recipe,temperature,endpoint and time window establish application to the requested functional assay. Return the specific mismatches and unknowns with witnesses. Distinguish an independently assayed standard from a value predicted by the same fitted curve. Preserve separately a reported recovery and one calculable from displayed operands when they differ. Do not calculate numbers,choose thresholds,substituteepsilon for recovery,or turn absence into zero or one. The deterministic reader and calculator perform numerical extraction and arithmetic.

The separate requested response must constrain relation meanings such as `same_quantity`, `enzyme_activity_response`, `chemistry_only_matrix_unverified`, `unknown` and `conflicting`; these label experimental relationships, not numerical scores. Model-facing TASK is not the whole numerical sheet; exact source bytes and IDs stay with host custody.

## Targeted implementation gaps

Complete inspected contracts: `literature_activity_calculations.py`, `literature_assay_inputs.py`, `literature_assay_storage.py`, `literature_assay_prompt.py`, `literature_optical_calculations.py`, and raw rate observation/replicate inputs and calculators. The optical calculator is explicitly NADH depletion with extinction conversion; it is not the positive formazan calibration in this case. Optical input/storage implementation was therefore not claimed inspected or appropriate to populate these numbers.

1. Current assay point input can receive a literal dimensionlessk. It does not read a nominal/measured NADPH standard pair in nmol and derive its recovery, nor does it parse an assay recovery supplied only as percent. Exact XML table cell selection needs paired nominal/measured operands,units,analyte,matrix,uncertainty,and dependency identities.
2. A targeted calibration calculator needs point recoveries,relative errors,and separately preserved reported values. A source-reported linear fit needs a bound mathematical relation and units; a fitted line'sR² cannot populate unknown residual variance. No raw points are available here to refit it.
3. Enzyme-spike activity recovery must remain a separate cell from isolated reporter gain. Its denominator provenance and source disagreements must survive storage and the typed return. A single scalar k without that linkage is inadequate.
4. Current six-operand correction must retain unavailable molarE,quantitativecontaminantg,conditionresponseu/v and residual variance. Existing mass-specific activity cannot silently supply unnormalizedq or molarE. Raw rate mean/SD/SE readers do not resolve any of these missing scientific facts.
5. Same-matrix blank subtraction and linear-calibration conversion need explicit dependencies so the intercept/blank or shared standard is not counted twice. Typed literature returns should carry these aspect-specific cells and unknown relationships once selected, without new episode types or a report-composition call. This report did not exercise that integration.

`build_research_packet.py` reads only retained source XML and writes this owned research directory. Its exact Fraction arithmetic is independently checked against high-precision Decimal arithmetic. It verifies source cell selections and byte anchors. No computational biology suite, experimental rerun,provider/model request,real conversation/log inspection or production test was performed. No source author was contacted for unavailable raw data.

## Dependency and correction-availability addendum

The paper does not state that Table 2 validation amounts were held out from fitting Figure 3, independently prepared from the calibration standards, or prepared from independent stocks. Stock concentration uncertainty and calibration covariance are unreported. Five days of measurements do not establish those independence relationships. Recovery, relative error and any inverse multiplier calculated from one nominal/measured pair reuse that pair; they cannot be added as separate proofs. Figure 3 R² and slope likewise come from one fitted calibration, and a high R² does not measure accuracy against an independent material. No effective independent-validation count is populated.

The finite, justified populated expressions are `M/N`, `100*(M/N−1)`, the reported calibration relation `A=mN+b`, and the explicitly named descriptive rate contrasts/CVs. The corrected functional activity is **unavailable**: no sample and matched blank absorbance operands were supplied, the buffer calibration is not established for the complete reaction/serum matrix, isolated reporter gain is unknown, and contaminant attribution, molar active enzyme amount and off-target condition correction remain unknown. No value of one is supplied for these missing relationships. The FBS-only rate was subtracted according to the source, but its magnitude remains unavailable. The Table 4 expected rate remains a source-reported expectation with an unreproducible derivation, rather than an independent reference measurement.

## Read-provenance exception

A discovery helper unintentionally printed the beginning of the first retained AF2372 packet, including its reported observation summary. Web discovery also returned numerical snippets from unselected papers. None was converted into sheet components or used as scientific support in this report. The selected WST-8 paper was opened before a full reset after those exposures, so strict reset-before-next-packet sequencing was not fully followed. The full prescribed authority set and relevant complete contracts were independently reread after the WST-8 source reading and before every component interpretation and arithmetic presented here. This exception is retained explicitly; no absent reset is claimed and no other agent's reset is borrowed.
