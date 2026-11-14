# CsiD original-source increment: A105 experimental reference evidence

This is one paper plus its necessary supplement, not a new collection. The inspected reference is Knorr et al., *Widespread bacterial lysine degradation proceeding via glutarate and L-2-hydroxyglutarate*, Nature Communications 9, 5071 (2018), DOI [10.1038/s41467-018-07563-6](https://doi.org/10.1038/s41467-018-07563-6), PMID 30498244, PMCID PMC6265302. This report evaluates the reference experiment only. It contains no alignment, reference-to-target transfer, A101/A105 merger or annotation-credit calculation.

## Actual native source and deterministic anchor

The retained original JATS/XML has **zero `table-wrap` elements**. The requested native rate table is therefore absent from this artifact. The specific activity and two apparent kinetic constants occur in **section `Sec3`, “Characterisation of glutarate hydroxylase CsiD”, first direct paragraph**. A deterministic reader can address `//sec[@id='Sec3']/p[1]`, flatten inline `italic`/`sup` text in document order, and bind exact local quantity phrases and substrate names. It must retain the raw artifact identity, selector, matched original text and normalized unit. Inline superscripts and Unicode minus/spaces require declared normalization; no 14-column normalized TSV exists in the paper.

Original bytes and request metadata are retained locally:

- [PMC6265302_original.xml](PMC6265302_original.xml), obtained from [Europe PMC fullTextXML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6265302/fullTextXML); SHA256 `918d148cfc54a638bd9e36d42ebe5c6cf8b72332a3c674ed320d2f86d63a1558`.
- [41467_2018_7563_MOESM1_ESM.pdf](41467_2018_7563_MOESM1_ESM.pdf), obtained using the PMC advertised versioned asset, [original supplement](https://pmc-oa-opendata.s3.amazonaws.com/PMC6265302.1/41467_2018_7563_MOESM1_ESM.pdf?md5=45bc4faf68c76e2c601e5da98a2708bb); SHA256 `4ee4d71758929f9b3910a73e5fd16d00d248c834d75fe33360f9a4c58b6f6056`; MD5 matches advertised `45bc4faf68c76e2c601e5da98a2708bb`.
- [supplement_layout.txt](supplement_layout.txt) is a locally generated `pdftotext -layout` derivative, not a publisher table. Supplementary Fig. 5 caption is at text lines 161–168. Supplementary Tables 2/3 occur in the inspected text interval 330–389. Text line locations are derivative-specific; retain the original PDF as the authority.
- Request provenance, PMC version/listing responses and original search response are in the same directory. The attempted publisher-CDN download failed DNS; the PMC asset succeeded. No graph was newly digitized or rendered in this worker.

## Experimental definition and paired fields

The Methods identify E. coli BW25113 as the gene source; CsiD was expressed as an N-terminal 6×His construct using pET28a in E. coli BL21(DE3), Ni-NTA purified, and checked by SDS gel. These are the assayed reference construct and expression host, not a newly queried protein. Construct boundaries beyond this reported description are not inferred. `Sec11` and `Sec13` provide the construct/preparation context.

The Clark-electrode assay (`Sec15`) uses 100 mM MOPS, 70 mM NaCl, 20 mM KCl, pH 7.2, 400 µM ascorbate, 4 µM Fe(NH4)2SO4, 180 nM CsiD and 30 °C with stirring. Glutarate Km was measured at 1 mM α-ketoglutarate; α-ketoglutarate Km at 5 mM glutarate. Initial oxygen-consumption rates were fit to Michaelis–Menten curves. Do not combine those curves into an unreported independent bi-substrate model.

| Native measurement and location | Required extraction fields | Numerical cell and meaning | Uncertainty / unavailable operands |
|---|---|---|---|
| `Sec3/p[1]`: specific activity **53 ± 3 µmol min−1 mg−1** | actual CsiD preparation, Clark-electrode oxygen endpoint, protein-mass denominator, value 53, error magnitude 3, error kind unspecified, n null, sampling basis unspecified, reported origin; `Sec15` assay conditions | `native_specific_oxygen_activity=53 umol/min/mg`: source preparation oxygen consumption per mg protein. This is an actual functional-magnitude component, not product formation or a confidence probability. | No demonstrated blank subtraction, recovery, contaminant contribution, independent-unit count or error-statistic definition in the inspected kinetic passage. The reported error cannot populate variance or SE. |
| Same paragraph: glutarate apparent Km **650 ± 20 µM** | quantity role `apparent_Km`, varied ligand glutarate, value 650, error magnitude 20, error kind unspecified, paired assay condition αKG 1 mM | `Km_glutarate=650 uM`: location/curvature parameter of the reported preparation response, not catalytic efficiency or specificity by itself. | n, fit uncertainty meaning and parameter covariance unavailable in inspected source. Do not use Km alone as a score of function quality. |
| Same paragraph: α-ketoglutarate Km **100 ± 7 µM** | role `Km`, varied ligand αKG, value 100, error magnitude 7, error kind unspecified, paired assay condition glutarate 5 mM | `Km_alphaKG=100 uM`: separate substrate/co-substrate response parameter. | Same missing fit/error operands; no cross-curve covariance or independent-curve assumption. |

The first cell already includes protein-mass normalization. A reader must not divide it by protein amount again, infer reaction volume, or convert it to µM/min. The current shared unit contract contains the required `specific_amount_rate` dimension. The two Km cells require a kinetic-parameter extraction route; they cannot pass through a contract restricted to rate rows.

A single positive specific-activity summary is **not** a pair of comparison arms. Do not manufacture a zero blank, invent a reference arm or reuse this value as two independent rate observations. The paper gives actual numeric alternatives to a native rate table, but it does not directly supply the first normalized two-arm TSV interface.

## How these cells enter numerical evidence components

The numerical sheet retains native measurements before any source-evidence statistic. For a source-preparation activity route, keep `q_specific=53 umol/min/mg`. Where an actual experiment supplies nuisance controls, the explicit corrected molecular effect is

`a_specific = (q_specific − blank_specific − non-CsiD_specific) / (recovery × condition_response)`.

Each subtraction has the same native specific-rate unit; recovery and condition response are dimensionless experimentally supported ratios. The intended perturbation is excluded from the condition correction. No second protein-mass denominator is applied. The numerator and denominator must refer to the same preparation endpoint and compatible conditions. Shared controls enter once, with joint covariance propagated through this equation.

The native report supplies only q and an untyped ± magnitude. The other operands and covariance are **unavailable**, so this paper read does not numerically fill corrected molecular activity, variance or a full source-evidence likelihood. It also does not establish that the reported 53 is uncorrected or already corrected: the reader must preserve that ambiguity rather than subtract a fictitious blank.

When an actual supported nonnegative-presence observation model supplies corrected activity a and known variance V>0, the current sheet's source calculation is `S=max(0,a)^2/(2V)`, then `B=tanh(S/2)`. Unknown V is not 3²; unknown controls are not zero, and B remains null here. No transfer multiplier R or target index D is calculated. Native q/Km values remain valid partial components even while the inferential result is unavailable. They do not exhaust the scientific evidence in the paper.

For Michaelis–Menten condition comparison, the current sheet's exact response calculation is `h=[Ss/(Km+Ss)]/[Sr/(Km+Sr)]` only for the same applicable preparation/endpoint/model, with actual source and reference substrate concentrations and their joint uncertainty. The inspected source supplies Km and assay co-substrate concentrations, but no commissioned new reference-condition comparison. Therefore no numerical h or arbitrary “saturation-quality” score is filled. A lower Km is not intrinsically stronger annotation evidence.

This keeps the three responsibilities distinct: investigation instructions establish what the experiment means; the numerical sheet defines native/corrected activity, response and source-evidence components; deterministic readers/calculators populate only identified operands and calculations.

## Endpoint, effect isolation and complementary experiments

Oxygen consumption can include nonproductive turnover. The electrode result alone does not identify the product, exact coupling, contaminant activity or purified CsiD-specific chemical turnover. The paper's NMR/LC-MS and stereospecificity experiments (`Sec3`, `Sec14`, `Sec16`, Supplementary Figs. 1–3) address different weaknesses: product assignment and L-2-hydroxyglutarate stereochemistry. Their value is complementary endpoint identification; they are not independent repeat electrode-rate measurements or automatic numerical reliability multipliers. NMR assay substrate concentrations and incubation differ from the kinetic electrode conditions, so do not treat their products as a calibrated stoichiometric rate for the 53 value.

The source reports other dicarboxylic substrates were not converted, but an inspected quantitative threshold/noise model is absent. These are reported negative findings, not exact zeros or infinite specificity ratios.

## Supplement controls and native numerical alternatives

Supplementary Fig. 5 compares no-inhibitor Ctrl to inhibitor conditions (NOG, L2HG, D2HG). Ctrl is **not** no enzyme. Its caption says triplicate measurements with SD, with **D2HG n=2**. The caption does not establish independent biological preparations. The source's separate Fig. 2d legend describes biological duplicates plus technical duplicates for intracellular glutarate; this legend must not be assigned to kinetic panels 2b/2c or to the specific-activity/Km sentence.

The Fig. 5 caption reports CsiD L2HG inhibition as an **estimated Ki >10 mM**, not an exact measured constant. Retain both the inequality and estimated status. The nearby 628 ± 0.036 µM Ki concerns cited αKG-dependent dioxygenases, not CsiD. No newly extracted bar heights are supplied here; earlier graph reconstructions remain separate representations of the same underlying figure.

An actual native numeric table is Supplementary Table 2: compound retention time and LC-MS ion m/z (e.g. glutarate 4.9 min /131.0350, succinate 5.4 min /117.0193, L2HG 10.0 min /147.0299, αKG 12.0 min /145.0425). These are identification/quantification parameters, **not measured oxygen-rate rows or observed-vs-expected mass pairs**. They cannot yield a mass-error score without the missing measured counterpart or be repurposed as rate values. Supplementary Table 3 is cellular metabolite/isotope information; it must not silently fill an isolated molecular-rate assay.

## Necessary revisions and limits of this increment

1. Add a source-native JATS selected-prose representation with exact section/paragraph/span custody. Do not label manually normalized TSV as the original table.
2. Accept one source measurement without forcing a two-arm contrast. Preserve specific-rate normalization and untyped uncertainty. The initial two-arm calculator can correctly return unavailable when invoked without an actual comparison.
3. Add a distinct kinetic-parameter representation if Km values are to be populated. Numerical proximity cannot resolve which ligand a value belongs to.
4. Preserve estimated bounds separately from exact measurements and censored measured observations. The Ki caption needs both reported-estimate origin and `gt` relation.
5. Keep source oxygen activity, product identity, stereochemistry, attribution and statistical evidence separate. Numerical merging requires their actual experimental linkage and uncertainty, not a generic quality weight.

Only local source/provenance/report artifacts were created. No production code, tests, grader, episode, model-backed literature run, biological experiment or final annotation scoring was performed by this worker. The original source does not eliminate real statistical/attribution gaps.
