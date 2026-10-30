# A105 binding case042: experimental distinctions and numerical population

Research-only packet, 2026-10-26. One selected primary paper: Rajagopalan et al., 2013, *Studies of IscR reveal a unique mechanism for metal-dependent regulation of DNA binding specificity*, DOI10.1038/nsmb.2568, [PMC3676455](https://pmc.ncbi.nlm.nih.gov/articles/PMC3676455/). Retained group `reg_iscR_state_target_specificity`. No companion primary or retained actual_observations packet was read. Complete main article and Table3 image were read; supplemental curves were unavailable. Required own full post-paper authority/contract reset completed before this interpretation; see READ_RECEIPT.json. A105 remains one incomplete axis sheet with several experimental components; ten total axes remain. No A101/target-transfer/W05 calculation is proposed here.

## Experimental definitions before scoring

The measured molecule is E. coli IscR or separately purified alanine variants. This is a purified protein–DNA experiment, not a mixed WT/mutant culture activity endpoint. Plasmid variants were made from T7-driven pPK6161 and overexpressed in PK7878 (BL21(DE3) ΔhimA::tet ΔiscR::kan; main text lines291–292). The DNA-binding purification section identifies WT PK8581 and E43A PK9124, with the other variant strain IDs separately listed (301–302). Binding preparation amino-acid boundaries, affinity tag status, numerical purity, independent preparation count, exact final concentration uncertainty and contaminant binding contributions are not established by the accessible main Methods. Do not borrow the C-terminal His tag, triple Cys substitutions or truncation of a crystallography construct into the binding sample.

Crystallography uses C92/98/104A clusterless constructs, with additional E43A as applicable, and an unbound 1–133 truncation. Those constructs and a 29bp crystallization DNA are distinct from the biochemical binding preparations and 30bp labeled assay DNA (293–305). The main source itself discusses structural flexibility and proposes, rather than directly observes, the holo-induced rearrangement (284–286). Structural results may address A111 later; they do not add an independent repetition to a competition IC50.

For the principal numerical case, Table3 and Methods306 establish **equilibrium competition fluorescence assays on apo-WT IscR and apo-IscR-E43A**. Anaerobically purified protein was cluster-stripped with EDTA and dithionite until 420nm absorbance no longer decreased, then processed to remove EDTA. Iron measurements were background-corrected and cluster occupancy calculated assuming2 Fe per IscR monomer (302). No numeric residual cluster detection limit is supplied for the apo samples. Anaerobically isolated samples elsewhere in this paper have partial occupancy:40–50% WT and27–50% mutant in purification; the assay paragraph gives27–56%. These are reported ranges in distinct passages, not variant-specific occupancy correction operands.

The binding target/readout is a Texas-Red-labeled hya promoter DNA probe (type2 DNA site) plus an unlabeled competitor. The competitor is hya itself, shuffled DNA, or a single7C/8C nucleotide substitution. Both DNA species coexist in a tube; WT and E43A proteins are assayed separately. Methods304 provides the hya 30mer as5′-ATAAATCCACACAGTTTGTATTGTTTTGTG-3′; the source also defines the type1 iscRB30mer separately. The tracer is5nM, competitor input8–1000nM; buffer40mM Tris-Cl pH7.9,250mM KCl,5% glycerol,10µM DTT, anaerobic. WT nominal protein input22nM; E43A20nM. Fluorescence is measured as described for the direct isotherms, whose incubation is12min and ambient-light delay10s (305–306). No assay temperature is explicitly supplied there. Nominal added concentrations are reported; free DNA/protein/competitor concentrations are not measured.

In each within-protein comparison the intended variable is competitor sequence. The tracer, protein label/state, nominal protein input and described buffer stay fixed. Across WT/E43A comparisons, mutation is intended but nominal protein input also changes22→20nM; separate preparation/folding/active fraction may differ and are not quantitatively matched. Protein concentration is **not** another mutation penalty inside a WT-only competitor comparison. A numerical comparability correction would require an actual same-endpoint protein-input response, rather than assigning a categorical similarity grade.

The measured signal is fluorescence anisotropy/polarization change. Competition response is normalized as(A−Afree)/(Abound−Afree): Afree is DNA without IscR; Abound is the signal **without competitor** at the chosen protein input (306). This normalization references its own no-competitor response; it is not independently established absolute molecular occupancy or fully saturated tracer binding. A four-parameter logistic fit supplies IC50. Table3 footnote defines it as the unlabeled competitor concentration halving the maximum binding response to labeled hya. It is **not Kd**, catalytic activity or transcriptional activation. No applicable competitive-binding conversion to intrinsic affinity is supplied.

## Paired extracted operands and actual numerical cells

Table3 is an embedded image, so values below are **visual transcriptions of reported table cells**, not graph-derived points, OCR or raw instrument traces. TABLE3_RETAINED_VISUAL_TRANSCRIPTION.json retains twelve source cells, expressions and cell image regions. NUMERICAL_CELLS.json contains ten actual calls through the existing pure reader/calculator; CALCULATION_RECEIPT.json records scope. Source nM units are established by Methods306. Each ± is the source's reported fit-derived standard deviation: fit of a four-parameter logistic curve to the average of at least three independent titration experiments (Table3 footnotec, lines253–254). It is not a sample SD of independently fitted IC50 values, SEM, known sampling variance or a biological-preparation count. The exact count remains unknown; at least3 assay occasions is supported (306).

| Competitor | WT IC50, nM | E43A IC50, nM | WT test/self-hya ratio | E43A test/self-hya ratio |
|---|---:|---:|---:|---:|
| hya self |32±2|11±1|same reference, not extra evidence|same reference, not extra evidence|
| shuffled |>1000|>1000|>31.25|>90.90909091|
| hya7C→G |>510|17±3|>15.9375|1.545454545|
| hya8C→G |>740|7±3|>23.125|0.636363636|
| hya8C→A |>1000|6±1|>31.25|0.545454545|
| hya8C→T |>1000|8±1|>31.25|0.727272727|

These greater-than calculations preserve **printed-limit arithmetic**. They are not confidence bounds or identified bounds on the true parameter ratio: the denominator is a noisy fitted point and the reporting/noise mechanism for each limit is not supplied. In particular>510 is preserved; it is not silently replaced by the overall1000nM maximum input.

For a selected protein/state/assay, define p0=IC50 for self-hya and pm=IC50 for the changed competitor. The existing numerical cells are `reference_parameter=p0`, `test_parameter=pm`, each `*_reported_spread` in nM when printed, `*_relative_spread=spread/p`, `native_parameter_ratio=pm/p0`, and `log_native_parameter_ratio=ln(pm)−ln(p0)`. The ratio divides two concentrations under one experiment; it evaluates sensitivity of the competition result to that particular nucleotide substitution. The log is the same contrast on another scale, not a second independent result. WT7C→G gives printed arithmetic>15.9375 and log>2.768674822919. E43A7C→G gives1.545454545455 and log0.435318071258. WT self relative fit spread is2/32=.0625; E43A self1/11=.09090909; E43A7C→G3/17=.17647059. These evaluate reported fit spread relative to its parameter, not total experimental reliability. Neither the relative spread nor the control ratio is an independently applied quality multiplier.

Functional bearing is narrower than “binding protein is valid”: WT hya competition changes sharply on these selected substitutions, whereas E43A's fitted competition parameters are much less sensitive in this panel. Shuffled competitor remains poorly competitive for both proteins. This differentiates loss of particular base discrimination from a blanket conclusion that E43A binds all DNA indiscriminately. The panel does not exhaust other DNA sequences or establish genome-wide specificity; retained specificity at other positions is stated as data not shown (245), so no invented parameter enters the sheet.

## Explicit combination for the functional distinction, and its limits

To compare the **change in selectivity**, a proposed source-level component is the four-cell ratio of ratios, not32/11 treated as an affinity gain:

D_m = (pWT,m/pWT,0)/(pE43A,m/pE43A,0)
    = pWT,m × pE43A,0 /(pWT,0 × pE43A,m).

Its log is the signed sum

e_m = −ln(pWT,0)+ln(pWT,m)+ln(pE43A,0)−ln(pE43A,m).

PROPOSED_FOUR_CELL_ARITHMETIC.json computes actual printed-cell arithmetic:

| Changed competitor | Dm, printed-limit arithmetic | em, same arithmetic on log scale |
|---|---:|---:|
|7C→G|>10.3125|>2.333356751661|
|8C→G|>36.339285714286|>3.592899407142|
|8C→A|>57.291666666667|>4.048155179753|
|8C→T|>42.96875|>3.760473107301|

This multiplies/divides measured source operands and explicitly compares two specificity contrasts. It does **not** remove the22vs20nM protein-input difference, unspecified free concentrations or shared curve/nuisance effects. It is a proposed descriptive sheet extension, not an established mutation-only effect, final A105 grade or adopted template replacement. The two censored shuffled IC50s do not produce a corresponding four-cell directional bound. A much larger D does not automatically mean greater experimental reliability.

The eventual statistical component needs the actual joint observation model. With four uncensored natural-log parameter estimates y=(ln pWT,0,ln pWT,m,ln pE43A,0,ln pE43A,m) and a scientifically supported known sampling covariance C, c=(−1,1,1,−1), then e=cᵀy and **V=cᵀCc=Σ_iΣ_j c_i Cij c_j**. Only for an applicable known-normal contrast about an explicitly chosen zero boundary would S=e|e|/(2V), B=tanh(S/2) be the existing sheet's proposed bounded source component. The current four-cell values include censored fitted parameters, so substituting the printed limit into that uncensored formula is invalid. A censored route requires its actual joint likelihood/reporting event and nuisance model. No such finite profile is calculated here. S,B,V remain null; the paper's ± and minimum3 do not identify them.

Several nucleotide contrasts reuse each protein's self-hya denominator and potentially preparation/baseline. If all parameter logs had independent errors aside from the shared self measurement, two within-protein contrasts would still have covariance Var(log p0); independence of those original errors itself is not established here. Use the real covariance, not that illustrative simplification. The four substitutions, self control, shuffled control, Table3 and the same underlying curves are not five independent replications. Source identities survive alternate representations. Numerical pooling of papers, target correspondence and final annotation credit are outside this packet.

## Comparability, effect isolation and complementarity remain distinct

**Comparability:** within a protein's Table3 competitor panel, same stated buffer/input protein/tracer, intended change in competitor sequence. Across proteins, different nominal inputs and separate preparations must remain visible. Direct isotherms use150mM KCl, while competition uses250mM (305–306); do not calibrate one against the other without a measured response. Temperature is unknown. No measured control response supplies the old sheet's `condition_test_rate/condition_reference_rate` or activity h factor for this binding experiment.

**Isolation:** no-protein Afree and no-competitor Abound isolate normalized signal baselines; self competition and shuffled DNA address sequence-dependent versus nonspecific competition. They do not quantify a contaminating protein's binding contribution, optical interference from each DNA variant, active IscR concentration, folding equivalence or residual cluster contribution. Purification does not fill `contaminant_rate=0` or `fraction_intended=1`. A nonspecific competitor control cannot be repurposed as a numerical subtractable blank binding rate.

**Endpoint validity:** binding supports DNA-recognition specificity under this in vitro system. It does not establish repression/activation, native physiological function, catalysis, transport or a proposed chemical reaction. The paper cites in vivo regulation from other sources; no new numerical in vivo endpoint is extracted into this single-paper binding component. An expression/reporter experiment could address regulation but would be a distinct endpoint requiring its own controls, not another replication of IC50.

**Complementary evidence in this paper:** Table2 reports fitted Hill Kd for hya, WT17±1nM and E43A22±1nM, alongside Hill slopes3.7±.2 and4.0±.5 and maximum anisotropy. It shows that affinity-like response magnitude and sequence discrimination can change differently, but is not a second IC50 estimate. The accessible main table does not explicitly identify each Table2 molecular state; supplementary legends were unavailable. Do not assign an apo/pure-holo state by importing a crystallography label. These raw numbers are retained as qualified supporting facts only, not fed into the same-protein ligand calculator or used as a correction to Table3.

The direct isotherm model is A=Afree+(Abound−Afree)[IscR]^n/(Kd^n+[IscR]^n), using stated IscR concentration (305). The authors state the physical interpretation of n>2 is unknown, argue the fitted n does not affect their fitted Kd (supplementary figure7 uninspected), and cannot rigorously exclude an effect of monomer–dimer equilibrium. Thus “reported Hill Kd” must stay distinct from a thermodynamic one-site dissociation constant. No one-site occupancy L/(Kd+L) is populated; nominal protein titration is not a measured free-ligand series. Table4 and Figures4–5 test type1-site/state/variant distinctions, with partial cluster occupancy and qualitative figure statements preserved; no plot points or error bars were digitized here and no new type1 affinity/occupancy score is invented.

## Existing grader acceptance and exact unfinished functions

Complete modules read in own reset: literature_binding_reader/calculations/model_inputs/models/prompt/storage/model_storage.py and literature_experimental_contracts.py; full source hashes/line coverage are in READ_RECEIPT.json. No production module or tests were changed. This packet executed pure functions only, not LiteratureEpisodes or model decisions.

1. `read_binding_parameter_table` **accepts the manually retained Table3 transcription**, literal subject/state/experiment and ordered ligand selection, ic50, nM, fit_to_averaged_curve and minimum3. It parses exact> tokens/± and preserves image locators. It does not read image pixels or determine that the selected biology is correct.
2. `populate_binding_contrast` **actually populated ten selected within-protein comparisons** here. It preserves point/one-limit arm facts, spread/relative spread, ratio/log and unknown preparation count. Different protein/state/experiment rows cannot be combined to manufacture a ratio. Missing/ambiguous/conflicting source cells have explicit unavailable/conflict paths in the read code; this packet did not run new adversarial tests.
3. `populate_binding_model(sheet,model=None)` was actually called ten times. Native log facts survive and profiles are correctly unavailable with `binding_sampling_model_unreported`. The existing optional known-normal log-covariance model requires source-owned covariance and, for a limit, threshold_of_log_estimate reporting; neither is inferred here. This proves actual source-derived **partial population**, not a fitted likelihood or complete experimental grade.
4. The storage modules can retain selected source inputs, design/arrangement witnessed interpretations and requested typed cells; source receipt/image lineage are enforced in code. This packet did not commission, persist or return a cell through an episode repository. Its local source strings are research identifiers, not fabricated admitted application references. Integration capability/engineering receipts are owned by041; no integrated execution is claimed here.

Necessary missing population/calculation work, precisely scoped:

- An image-table extraction/custody route still requires retained human/model transcription; the existing reader is a JSON token reader, not an automatic Table3 image reader. This packet supplies an honest retained transcription, without changing that implementation claim.
- A source relationship/control reader must populate tracer/competitor/nominal protein inputs, buffer changes, baseline definitions, actual molecular-state/preparation ownership and source uncertainty meaning as typed experiment operands. Current design/arrangement enums plus witnesses do not numerically account for22vs20nM or unknown active fraction.
- A **between-protein change-in-specificity calculator** and matching four-owner joint model interface are missing. Existing two-arm binding contrast requires one protein/state/experiment; it cannot calculate the four-cell interaction with its shared controls, censoring and actual correction for additional differences. Proposed fields and equations above define this finite extension; no production code is added.
- A curve-level binding/competition reader/fitter with actual anisotropy baselines, replicate structure, concentration basis and model validation would be needed to estimate joint sampling/censor information from original curves. It must not reinterpret table fit spreads as known log covariance. Unavailable raw/supplemental data is a separate scientific-input limitation from absence of this function.
- A numeric comparability response or active-fraction/isolation correction requires measured controls and an applicable binding model; no universal scalar quality ladder is supplied. Missing measurements stay unknown rather than becoming a new research-derived default0/1.

## Draft aspect-specific interpretation questions for later feedback

These are proposed scientific question/allowed-meaning pairs, not a newly wired TASK template or an additional report-composition call. Deterministic functions perform arithmetic after meanings/operands are established.

| Concrete scientific question | Required source inputs | Allowed returned meaning / unknown or conflict |
|---|---|---|
| Does the readout come from added competitor titration or protein titration, and which parameter was fitted? | Methods305–306, Table2/3 headings/footnotes, selected curve/axis if available | competition_ic50 / reported_hill_kd / other_explicit / unknown / conflicting; do not infer intrinsic Kd from ic50 |
| Are WT and E43A mixed, or separately assayed? What else changes? | Expression/purification and actual assay arms, protein inputs22/20, buffer | separate_protein_preparations / protein_mixture / unknown / conflicting; paired numeric additional-difference operands retained; DNA coexistence is distinct |
| What does the competition normalization denominator actually measure? | Literal Afree/Abound definitions and assay input | no_competitor_signal_at_selected_input / independently_saturated_binding / unknown / conflicting; output cannot turn the former into absolute occupancy |
| Does this comparison test hya nucleotide discrimination or generic binding magnitude? | Competitor identities, self comparator, within-protein and cross-protein relationships | specified_nucleotide_competition_contrast / direct_binding_parameter_contrast / four_cell_change_in_competition_contrast / unknown / conflicting; this does not assert activation |
| What is the reported uncertainty and repetition unit? | Table footnotes, repeat statement, individual fits if actually supplied | fit_to_average_curve / between_independent_fits / other_explicit / unknown / conflicting; exact n and prep count remain null if only minimum3 assays is given |
| What event generated each greater-than parameter? | Fit/reporting procedure, tested range, curve/noise model | explicit_parameter_estimate_threshold / other_explicit_reporting_rule / unknown / conflicting; unknown preserves printed-limit arithmetic and blocks finite censored likelihood |
| Does a proposed correction address comparability or signal attribution? | Actual additional changed condition, control response and shared-observation ownership | same_endpoint_condition_response / measured_other_contributor / unsupported_numeric_correction / unknown / conflicting; no zero contaminant or unit correction from absence of data |

No field above is an overall quality category encoded as a number. The useful numerical results are the native parameters, reported spreads, selectivity ratios/logs and explicitly qualified four-cell arithmetic. Their unavailable statistical compilation is an actual unresolved model/input boundary. This packet neither adopts historical target-transfer/source-pooling formulae nor declares A105 or the active goal complete.
