# A105 optical/coupled-assay case031 — draft research handoff

Status: one fresh primary-paper review, no implementation or scientific run. The ten-axis literature goal remains incomplete. This packet is for the parent to print and discuss; the parent must perform its own full post-paper reset before further interpretation.

## Concrete example to print

Li et al., *Coupled Ferredoxin and Crotonyl Coenzyme A (CoA) Reduction with NADH Catalyzed by the Butyryl-CoA Dehydrogenase/Etf Complex from Clostridium kluyveri*, J Bacteriol 190:843–850, DOI 10.1128/JB.01417-07, [primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/).

The actual assayed subject is a native purified Bcd/EtfAB complex from C. kluyveri DSM555, not a recombinant single Bcd construct. C. pasteurianum ferredoxin and hydrogenase coexist with it as electron carrier and downstream reporter. Table 2 shows that adding methyl viologen changes the H2 specific activity from 5 to 0.02 µmol/min/mg: retained fraction 0.004 and fractional decrease 0.996. In a separate optical NADH assay it changes 7 to 5 µmol/min/mg: retained fraction 0.714286 and decrease 0.285714. These are endpoint-specific contrasts; neither is an overall reliability multiplier. The assays differ in temperature, substrates and reporter amounts, so their rates cannot yield a productive-coupling fraction.

The paper supplies the NADH extinction coefficient, 6.2 mM⁻¹ cm⁻¹ at 340 nm, but no raw absorbance slope, matched blank slope, optical path length, or numerical recovery experiment. The extinction coefficient cannot fill the sheet's dimensionless recovery k. The correct partial result retains the reported rates and leaves optical reconstruction, k, uncertainty and source likelihood unknown. This case justifies distinguishing optical conversion from recovery and upstream consumption from downstream reporter output.

## What was actually inspected

Retained group `chem_bcd_etf`, molecular_measurement/case_reviews.jsonl line22 and corpus chemistry/cases.jsonl line1, identified the paper. Their old categorical scoring proposal was not adopted. SOURCE_CORRECTIONS.md was read fully: its YeaG correction does not change this case; no YeaG endpoints are reused. Reading those retained packets was followed by a full reset before the primary read. After primary text inspection, the required authority documents, current sheet and relevant assay/rate extraction/calculation contracts were reread before the component interpretation below. See PROVENANCE.md for exact coverage, repaired truncation and actual access failures; read_hash_manifest.json records hashes.

Full acquired PMC HTML text was read in sequential primary.txt line ranges 1–145,146–280,281–403. This covers abstract, introduction, complete Methods, Tables1/2 and footnotes, Results, Discussion, captions, references and site material. Figure images, plotted coordinates, raw instrument files, original optical traces, gas calibration data and cited papers were not inspected. No graph-digitized number or measured path length is claimed. Source choice was narrow: this retained case directly tests reporter uncoupling and gives optical calibration coefficients plus a completion-yield experiment.

## Experimental definitions and relationships

The complex was purified from native C. kluyveri cells grown on ethanol/acetate. No engineered mutation, tag, truncated construct, expression host, replacement with a reference protein, or coexisting mutant/WT mixture is established. Partial sequences identify Bcd CKL_0455, EtfA CKL_0457 and EtfB CKL_0456. Subunit masses are apparent SDS-PAGE values. The gel-filtration mass and suggested subunit stoichiometry do not supply a validated molar concentration for every active species; no conversion of protein mass to catalytic-site concentration is made.

All activity assays are anoxic. The Bcd/EtfAB complex, Fd and hydrogenase are distinct system components. Within Table2, full-system versus methyl-viologen-added or substrate-omitted arms deliberately alter the electron acceptor or substrate; these intended alterations are not comparability penalties. Other listed conditions follow the relevant assay block, with preparation-level pairing and run identities unknown. A single purified preparation is not measured zero contamination. C. pasteurianum reporter components do not establish the native in-cell partner identity or physiological throughput.

| Assay | Endpoint and denominator | Conditions/roles from Table2 and Methods | What it can substantiate; remaining isolation limit |
|---|---|---|---|
| Optical NADH oxidation | NADH disappearance; 1 U =1 µmol NADH/min; per mg purified complex | 1 mL,25°C,pH7.5,0.1mM NADH,0.1mM crotonyl-CoA,5µM FAD,2mM DTT,0.01mg complex; selected additions20µM Fd,0.4U Hyd,1mM methyl viologen | Consumption depends on system composition. Does not quantify productive crotonyl-CoA/Fd coupling or prove product formation in that measurement. At37°C the source lists14U/mg for full system; other composition changes still differ from H2 assay. |
| Hydrogenase-coupled assay | H2 formation by gas chromatography; 1 U =1 µmol H2/min; per mg complex | 0.5mL,37°C,pH7.5,2.5mM NADH,1mM crotonyl-CoA,10µM FAD,2mM DTT,0.05mg complex; selected50µM Fd,1.6U Hyd,1mM methyl viologen | Reports electron delivery through Fd to Hyd under this reconstitution. Omission controls address dependency; reporter completeness/linearity and native flux remain unquantified. |
| TTC optical assay | TTC reduction; 1 U =1µmol TTC/min; per mg complex | 1mL,25°C,pH7.5,0.2mM NADH,0.1mM crotonyl-CoA,5µM FAD,0.4mM TTC,2mM DTT,0.01mg complex | Artificial acceptor can receive electrons without Fd. Therefore TTC reduction does not numerically establish Fd reduction. |
| Ferrocenium optical assay | 1 U =2µmol ferrocenium/min | Butyryl/hexanoyl-CoA oxidation, artificial one-electron acceptor | Different direction and source unit definition; no generic U conversion or physiological direction inference. |
| MALDI-TOF samples | 836Da peak replaced by838Da peak on incubation;1min sampling | Separate product-identification method | Supports conversion consistent with butyryl-CoA. No quantitative productive yield, exact-mass error, blank correction or sampling covariance supplied. |
| Fig2 completion experiment | H2 amount versus limiting NADH or crotonyl-CoA amount, to completion |0.5mL,37°C,0.2mg complex,20µM Fd,0.4U Hyd;2.5mM NADH inA,5mM crotonyl-CoA inB;A has regeneration | Reported stoichiometric slopes give2.2 NADH/H2 and1.4 crotonyl-CoA/H2. These are completion-yield relationships, not the Table2 rate ratio or exact fully coupled stoichiometry. |

Table1 is a crude-lysate system containing multiple enzymes and regeneration. Its 10min H2 amounts are distinct from purified-complex rates. Crotonyl-CoA is depleted after2min for the indicated arm. Consequently0.5µmol/10min=0.05µmol/min is only the full-interval mean; it cannot reconstruct an initial slope or maximal activity. Multiple 1min gas samples are time points, not independent preparations.

## Exact source selectors and deliberately short quotations

All local selectors below refer to the acquired primary.txt (SHA256 in provenance), with corresponding byte selectors in verification/optical_case_031/source_line_selectors.json. The retained HTML is authoritative source representation; primary.txt is explicitly a deterministic text rendering.

- Methods, NADH oxidation assay, primary.txt line216: “ɛ340 = 6.2 mM−1 cm−1”. This is an extinction coefficient, not observed/reference standard recovery.
- Methods, H2 determination, line224: “The peak heights were correlated to a standard curve.” No numerical standard-curve coefficients or recovery values are given.
- Results, catalytic properties, line248: “considerable lag period” and “not always proportional”. These qualifications prevent treating any arbitrary time interval or protein dose as a validated linear rate regime.
- Table2, lines166–214: select the named block and arm together with the Table2 unit-definition footnote. The header U/mg alone cannot establish molecular endpoint.
- Stoichiometry Results, line263, Fig2 caption,line269: separate reported completion slopes from the authors' fully coupled extrapolation.
- Table1 title/10min header and footnote h,lines123–164: static-time amount and substrate-depletion qualification.

## Paired extraction fields and numerical cells

Values marked reported are source summaries, not newly reconstructed raw measurements. Arithmetic uses their printed numbers without inventing additional precision or sampling errors. These cells evaluate a scoped experimental distinction; they are neither a probability nor final annotation credit.

| Reader fields and scientific meaning | Numerical cell, formula and actual result | Missing/uncertainty/dependence handling |
|---|---|---|
| `endpoint=NADH_depletion`; `wavelength=340nm`; `epsilon=6.2mM^-1cm^-1`; selected assay relationship | `optical_conversion_coefficient`=6.2mM^-1cm^-1,reported. Proposed q_NADH=−1000(s_sample−s_blank)/(epsilon*l),µM/min | s_sample,s_blank,l unknown, so q reconstruction null. A valid Beer–Lambert linear relation over selected interval is conditional, not inferred from method name. No default1cm path. |
| `standard_measured`, `standard_reference`, common analyte/units/assay | Existing `recovery_k`=measured/reference | Both missing; k=null. A molar extinction coefficient and a statement about a GC standard curve are not dimensionless recovery. |
| Table2 H2 full-system arm5 and methyl-viologen arm0.02; same H2 endpoint and per-complex-mg normalization | Existing reference_rate=5,test_rate=.02µmol/min/mg; difference=4.98; retained_fraction=.004; fractional_decrease=.996 | Independent unit count, spread and between-arm covariance unreported. MeanSE,differenceSE,S/B null. This contrast concerns the added mediator; it is not an optical or no-enzyme blank. |
| Table2 NADH full-system7 and methyl-viologen arm5; same optical endpoint/protocol | Existing reference_rate=7,test_rate=5µmol/min/mg; difference=2; retained_fraction=5/7=.714285714286; fractional_decrease=2/7=.285714285714 | Same missing uncertainty; no independent proof bonus from different representation. This is consumption, not H2/product rate. |
| Table2 NADH full-system7 and no-addition.1; source table scope | difference=6.9µmol/min/mg; retained_fraction=.1/7=.014285714286 | Results separately gives.3–.4U/mg without Fd/Hyd, with broader preparation variability. Keep that as a distinct source statement/qualification; do not silently substitute, average, or call them identical observations. |
| Table2 H2 full-system5 and substrate-omitted<.01 | Individual threshold<.01µmol/min/mg; exact point contrast null | Under an explicitly proposed nonnegative activity domain and treating printed5 as fixed reported operand only: difference in(4.99,5], retained fraction in[0,.002), fractional decrease in(.998,1]. These are identification bounds on reported summaries, not confidence bounds. Source parser's current point-pair route correctly leaves these derived cells unavailable. |
| Source-defined amount per unit and per-mg denominator | H2 and NADH U/mg→µmol/min/mg multiply by1 for their respective entity definitions; ferrocenium U/mg→µmol ferrocenium/min/mg multiply by2 | Endpoint entity and definition association mandatory. Dimension equality alone does not make cross-endpoint rates comparable. |
| Table2 volume/mass for optical assay V=1mL,m=.01mg | Mass-specific optical rate proposed R=−(s_sample−s_blank)*V/(epsilon*l*m),µmol/min/mg | No raw slope/path, so null. Mass is not molar E. Reported7 survives without claiming its reconstruction or using7 as unnormalized q. |
| Table1 amount_H2=.5µmol, elapsed10min; entire interval; substrate depleted2min | `interval_mean_amount_rate`=.5/10=.05µmol/min,derived | Never relabel initial_rate. Unknown time-resolved slope, lag/window/covariance remain unknown. Not a second independent rate observation in addition to the same amount. |
| Completion slopes: NADH/H2=2.2,crotonyl-CoA/H2=1.4; endpoint amount relationships | Native `completion_consumption_ratio`2.2 and1.4 mol/mol,reported author derivation | No error model or joint covariance, so no likelihood. Extrapolated fully coupled2:1:1 remains a proposed mechanistic relationship, not measured conversion efficiency. |
| Cross-endpoint rate candidates: NADH14 at37°C,H2 5 at37°C | Arithmetic14/5=2.8,diagnostic ratio of reported specific activities under different protocols | Quantitative coupling cell remains null: substrate concentrations, Fd/Hyd,volume,protein dose differ and source warns nonproportional rates. Same temperature and mass denominator are insufficient. Do not use2/2.8 as a correction. |

For a future valid optical trace, uncertainty follows the actual ordered primitive vector x=(s_sample,s_blank,epsilon,l), full covariance Σ, and q as above: Vq=JΣJᵀ, J=(−1000/(epsilon*l),+1000/(epsilon*l),−q/epsilon,−q/l). This includes reused-blank/calibration covariance; unknown covariance is unknown. Trace points cannot supply between-preparation variability. A source-specific linear fit would retain its interval, slopes, residual definition and fit covariance; no automatic linearity diagnostic threshold is proposed here.

## Fit to the numerical sheet; sums/multipliers and overlap

The existing sheet's native quantities and correction components remain distinct. Where source design supports them, the optical conversion supplies the existing q=s−b and Vq upstream of a=(q−g)v/(kEu). The appropriate same-endpoint blank is subtracted once. E remains molecular concentration, and g/k/u/v retain their separately established scientific meanings. The optical conversion's epsilon and path length are not a new reliability factor. If calibration recovery is already incorporated into a trace calibration, applying it again through k would double correct; preserve the actual calibration model and operand reuse.

A valid corrected effect with supported uncertainty can enter the existing source statistical route. For its specifically supported known-normal presence model, S=max(0,a)^2/(2V), B=tanh(S/2); for a supported signed contrast use its specified source model instead. This paper supplies neither those complete corrected operands nor an applicable full uncertainty model, so source S/B remain null. Multiplying.996×.285714, summing all Table2 rows as independent evidence, or applying an arbitrary recovery default would not repair that gap.

The two mediator contrasts diagnose different measured endpoints in one coupled system. They can constrain an explicit joint mechanistic observation model only if its common conditions, stoichiometric linkage, nuisance terms and shared errors are supported. None is supplied here. MALDI supports product identity qualitatively without repairing missing productive-rate attribution. Fig2's completion observations address stoichiometric relationships without becoming rate replicates; their measured2.2 and1.4 must not be forced to the idealized2 and1. Partner omissions constrain experimental dependency rather than adding a generic quality score. No source→target correspondence, final A105 coordinate, W05 aggregation, or extra axis is calculated.

## Narrow interface proposal — unimplemented, for discussion

A supported finite gap is source-bound optical-slope conversion into an existing endpoint rate; present readers accept reported rates or already net q but do not implement this formula. The primary source demonstrates required distinctions but cannot supply a fully populated optical-conversion demonstration because raw slopes and path are absent. A coding workload must be separately assigned; this packet authorizes no shared edits.

Propose `read_optical_rate_operands(selection, *, read_source)` returning witnessed primitives and scientific relation interpretations. Closed selection fields:

- `source_ref`, `source_kind`;
- `assay`: nullable source witnesses for molecule,construct,preparation,condition,measured_entity;
- `signal`: `kind` enum absorbance_slope|absorbance_difference|static_absorbance|unknown, `sample_slope` and `blank_slope` nullable number/unit selectors, and selected time-window witnesses;
- `calibration`: nullable source-bound epsilon and path_length selectors with their units, wavelength selector, `relation` enum applicable_extinction_relation|not_applicable|unknown|conflicting with witnesses;
- `comparison`: blank_role enum matched_no_reaction_background|condition_reference|component_omission|unknown|conflicting with witnesses; same_endpoint and matched_window enum same|different|unknown; `rate_window` enum source_supported_rate_interval|interval_mean_only|static_only|unknown with witnesses;
- `covariance_source_ref`: nullable retained covariance with exact primitive-owner order, units and known|estimated|unknown status. Native blank/sample covariance and shared calibration ownership cannot be inferred from labels.

The numerical calculator, separate from the reader and TASK, consumes parsed x=(sample_slope,blank_slope,epsilon,path_length) in absorbance/min,absorbance/min,mM⁻¹cm⁻¹,cm plus explicit endpoint sign/relationship interpretation. Initial scope should support substrate-depletion NADH; do not guess a product extinction difference or reporter stoichiometry. It returns source net depletion rate inµM/min, original primitive identities, covariance/variance only when supplied, endpoint and unavailable reasons. No source score or activity normalization is added. Missing coefficients/slopes/path, static-only signal, unmatched windows, unresolved blanks, or unvalidated relation leave dependent outputs null, retaining usable observations. If later normalization byV/m is selected, it requires separate witnessedV,m and full dependence propagation and emitsµmol/min/mg; it cannot populate molar E.

Proposed meaningful tests for a separate coding owner: supplied synthetic slopes/path reproduce a known rate; missing path remains null; static absorbance is rejected as a slope; sign is preserved for negative net depletion; a no-substrate dependency arm is not silently accepted as matched optical background; shared calibration/blank identities preserve covariance; mismatched wavelength/endpoint/window returns partial fields with reasons; Table2 reported rates remain usable without optical reconstruction; source-defined ferrocenium2-unit branch never leaks into NADH/H2 conversions; actual primary case returns epsilon6.2 with unavailable reconstructed rate. These are proposed tests, not tests run here.

## Draft aspect-specific TASK — print for human feedback before coding

Determine what the Bcd/EtfAB experiments measure through NADH absorbance and hydrogenase-coupled H2 formation. Start with the supplied experimental material and examine the actual native complex, added ferredoxin/hydrogenase, substrates, mediator arms and assay conditions. Distinguish a measured NADH-depletion rate from H2 output, chemical product identification and completion yield. Preserve which component is deliberately changed and which other conditions differ; decide comparability and effect isolation separately.

For optical quantification, identify the measured species, wavelength, extinction relation, optical path and actual time-dependent signal. An extinction coefficient is not recovery from a known standard. Determine whether a matched background is reported for the same endpoint and interval; a component-omission experiment may establish dependency without providing that background. Inspect lag, selected rate interval and dose proportionality. A static amount divided by total elapsed time gives an interval mean and cannot establish an initial rate. Retain unknown path, slopes, windows and uncertainty instead of supplying defaults.

For coupled readouts, determine which added components deliver or report electrons and whether a mediator permits consumption without the intended downstream output. Keep each arm's endpoint and source-defined activity unit with its conditions. Product identification can complement consumption without quantifying productive coupling. A fully coupled stoichiometry proposed from the data must remain distinct from measured completion slopes and from ratios of rates taken under different protocols. Preserve source limitations and identify which specific observation could resolve them.

Nominate source passages and operand meanings for the requested typed return. Leave parsing, unit conversion, arithmetic and covariance propagation to deterministic functions. Keep preparation counts, time points, shared blanks/calibration and independent experiments distinct. Preserve useful reported rates when raw optical reconstruction is unavailable. Return the bounded functional assertion, supported experimental relationships and unresolved quantities in the parent's declared fields; do not compose an extra report call, invent a reliability category, transfer weight or final annotation score.

Draft STEERING example, separately rendered: H2 mediator contrast5→.02µmol/min/mg; NADH mediator contrast7→5µmol/min/mg; different assay protocols; optical slopes/path/blank and sampling uncertainty unreported. The recurring TASK above must remain complete on every iteration. Host hashes and tracking stay outside the prompt. The parent must collect running human feedback before treating this draft as settled.

## Additive selector correction001

The first draft's source-line numbers were offset. Source custody verification against the complete retained text corrects those locators without changing the measurements or interpretations:

| First-draft locator | Correct primary.txt locator |
|---|---|
| NADH extinction coefficient,line216 | line223 |
| H2 standard-curve method,line224 | line231 |
| Lag/nonproportionality,line248 | line258 |
| Table2,lines166–214 | lines170–221, especially data lines174–216 and footnotes219/221 |
| Stoichiometry Results,line263 | line269 |
| Fig2 caption,line269 | line274 |
| Table1,lines123–164 | starts line121; Table1 footnoteh is lines168–169 |

`source_selectors_corrected_001.json` is the replacement locator aid. The first locator file is preserved as the superseded draft. These later selected-source checks verified source positions/byte custody only; no new paper, graph data or scientific component interpretation was introduced. No Git repository metadata exists at this working-directory level (`git status` failed), so preservation is reported as restricted file ownership, not as a clean-Git-tree assertion.

## Additive interface precision002

For a separate coding assignment, fix the first calculator signature as `calculate_nadh_optical_rate(operands)`. Its closed operands are `{version:'a105_nadh_optical_rate_operands_v1', sample_slope, blank_slope, epsilon, path_length, covariance, covariance_status, relation, blank_role, same_endpoint, matched_window, rate_window, primitive_observation_refs}`. Values are nullable finite numbers in the fixed canonical units above; epsilon/path must be positive when present. Covariance is null or4×4 in the declared primitive order. `covariance_status` is known|estimated|unknown. The interpretation values are exactly the enums already proposed. `primitive_observation_refs` preserves the four nullable original measurement identities. Wavelength remains reader context; the reader must retain the literal epsilon/wavelength association rather than infer a universal NADH coefficient. The sign is fixed by this first route's measured NADH-depletion endpoint, so no model-authored sign or stoichiometric multiplier is accepted.

Closed numerical output: `{version:'a105_nadh_optical_rate_cells_v1', endpoint:'NADH_depletion', net_depletion_rate, net_depletion_variance, primitive_observation_refs, input_snapshot}`. Each numerical cell is `{value,unit,status,formula,origin,unavailable_reason,conditional_on}`, with status populated|unavailable and value null when unavailable. Reasons include missing_sample_slope|missing_blank_slope|missing_epsilon|missing_path_length|optical_relation_unknown|optical_relation_conflicting|blank_role_unresolved|blank_role_not_background|endpoint_mismatch_or_unknown|window_mismatch_or_unknown|rate_interval_unestablished|covariance_unreported. Nonpositive denominators, nonfinite values, asymmetric/indefinite covariance and incompatible units produce explicit field errors. A nonnegative clipping rule is not permitted: a negative noisy depletion estimate survives. This output is an input-population result for existing rate/assay cells, not a new scoring sheet or another contribution to sum. No implementation or integration is asserted.
