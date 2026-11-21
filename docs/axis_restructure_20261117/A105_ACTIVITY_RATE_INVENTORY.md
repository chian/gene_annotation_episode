# A105 `activity_rate` experiment inventory (SOP step 0, DRAFT for the owner to correct)

Written 2026-11-21 under `A105_EXPERIMENT_SOP.md` step 0. Read-only search; this file is the only file written.

**Status: DRAFT.** The owner has not supplied an `activity_rate` list (as the owner did for binding, SOP 0a, trace line
35001). Following SOP 0a item 2, the list below is drafted from the sources found plus domain knowledge. **Nothing
here is owner-confirmed.** It is one entry per reapplicable protocol ("assay generally refers to a type of protocol
that can be reapplied to anything", owner, `EXPERIMENT_INVENTORY_SEARCH_2.md` 2(d)), not per paper or per case.

**Update 2026-11-21 (SOP 0b, 0c, 0d done in code and docs, no experiment type yet).** `catalyzes` is now in
`CLAIM_PREDICATES_BY_CLASS`; the class list is copied into `A105_SCORING_DESIGN.md` section 6b; the class-scoped direction
function and its anchors exist in `G`. Class decisions are recorded in section 6 ("decided 2026-11-21, owner to confirm").
`EXPERIMENT_TYPES` and `CLASS_OF_EXPERIMENT_TYPE` still hold the 25 binding types only.

The generic judgement forms (`d = n/(n + 1)` and similar) that this draft first proposed were REJECTED by the owner and are
deleted; section 4 now points to SOP step 3 (researched per-assay values made gradual) and gives the direction form.

---

## 1. Sources searched and what was found

| Place | Found | Used for |
| --- | --- | --- |
| `docs/axis_restructure_20261117/EXPERIMENT_INVENTORY_SEARCH.md`, `..._SEARCH_2.md` | No per-technique enzyme-assay list. The Codex 6+2 roster puts activity under "1. Biochemical activity/rate assays", "2. Enzyme kinetics and substrate specificity", "5. NADH optical-rate assays", "6. Partner-removal/addback". The owner's biochemical questions (`..._SEARCH_2.md` 2(c)): sensitivity, kinetic parameters, heating, in vitro / in vivo, realism of the chemistry, expected signal in messy samples, a control for spontaneous reaction. | The owner questions are mapped to every entry (section 3). The roster's four activity families are merged into one class here, as the current code does. |
| `docs/axis_restructure_20261117/A105_SCORING_DESIGN.md` sections 6-7 | The template; binding list only. No filled template for any type exists anywhere (grep for "native outputs/units" hits only the SOP and the design doc). | Template. |
| `verification/biochemical_assay_guides_318/REPORT.md` | Guide-sourced considerations (STRENDA lists 1A/1B; NCBI Assay Guidance Manual "Basics of Enzymatic Assays", "Mechanism of Action", "Identity, Mass Purity and Enzymatic Purity", "Fluorescence and Absorbance interference"; ICH M10). Direct versus coupled, continuous versus stopped; detector versus reaction-time linearity; no-enzyme, inactive-enzyme and reporter-only controls answer different questions; mass purity is not activity purity. | Controls and noise fields; the common record core (section 2). |
| `verification/biochemical_fourteen_graders_319/REPORT.md` | The 14 old biochemical entrypoints are readers/calculators, not 14 assays. Named assays in their fixtures: NADH 340 nm photometric, TTC reduction, H2 formation (Bcd/Etf, *C. kluyveri*); oxygen consumption (synthetic); U/mg workbook rates (BbPK); HPLC NAD+/nicotinamide accounting (PARP1); photometric 320 nm MTZ trace; P450cam NADH 340 nm plus GC/MS product. | Past-work fields; confirms "one class sheet, several detection protocols". |
| `verification/a105_sheet_reader_inventory_315/SHEETS.tsv` | Old sheets under prior type 1/2/5: corrected endpoint activity (1), source rate contrast (2), NADH optical rate (11), kinetic parameter contrast (12), kinetic statistical model (14), controlled response (16), rate observations (21), concentration-rate curve precision (22), raw rate replicate contrast (23), kinetic summary precision (30). | Past-work fields. These are calculations, not types. |
| `verification/a105_arad_kinetic_selected_300`, `a105_pa0142_kinetic_selected_303` | Kinetic-parameter cases (Fan 2013 JACS pterin deaminase; Hall 2010 JACS 8-oxoguanine deaminase). Assay method not restated in the report headers read. | Past work for steady-state kinetic outputs (method-agnostic). |
| `verification/tool_graders_biochemical_measurement_boundaries_2026-10-28_532/README.md` | Biomni `analyze_protease_kinetics` (MM fit; turnover units wrong without calibration) and an ITC binding tool (binding only, no ITC kinetics). | Noise notes for fluorogenic/protease and ITC entries. |
| `research/experimental_scoring_review_2026-10-23/template_a105_reactions_001/11_component_synthesis_001.md` and paper notes 01-09 | Nine primary papers: CsiD/LhgO (PMC6265302, Clark O2 electrode, NMR, LC-MS), HFP (PMC12051542), CysQ (PMC2711008, colour assay vs AMP MS), FrsA (PMC6450606, pNPA spectrophotometric, Smax/Km), F420 (PMC8764529, coupled partner), TriA/AtzA (PMC95154, nondetection limit), QueF (PMC555470, NMR, 2 NADPH per product), RidA (PMC3270999, coupled ketoacid/ferricyanide trapping), FolM (PMC2805310, composite extinction coefficients). Proposed same-paper forms: `v = v_sample - v_blank`, `Ru = 1/(1 + V/v^2)`, `Rcal = min(r, 1/r)`, `Smax/(Km + Smax)`. | Noise and certainty fields; same-paper quantities the sheet side can compare (the generic forms once derived from them are deleted, section 4). |
| `.../template_a105_reactions_002/` (`reaction_component_proposal.md`, `frsa_2013_review.md`, `moral_2011_review.md`) | FrsA 2013 ADH/NADH coupled assay (coupling-enzyme activity checked by adding acetaldehyde at the end); OxDC 2011 continuous MIMS versus quenched FDH-coupled formate endpoint; calibrated channel rate `y = (s - b)/m`. | Coupled-assay and continuous-MS entries. |
| `.../a105_raw_rate_primary_case_164/REPORT_001.md` | BbPK (PLOS Biol, 10.1371/journal.pbio.3002285): coupled NADPH 340 nm (AckA/HK/G6PDH), direct HPLC acetate, chromogenic AcP; U/mg workbook values not bound to one method. | Coupled, chromatographic and stopped-colorimetric entries; the "value not bound to its method" risk. |
| `.../a105_optical_case_031/FINDINGS.md` | Bcd/EtfAB (PMC2223550): NADH 340 nm with stated epsilon 6.2 mM^-1 cm^-1 but no raw slope, blank slope or path length; methyl viologen changes H2 rate 5 to 0.02 and NADH rate 7 to 5 umol/min/mg. | Direct spectrophotometric and redox-mediator entries. |
| `.../a105_dataset_example_004/01_csid_numerical_dataset_001.md` | CsiD Clark electrode, umol O2/min; uncoupled O2 consumption not excluded by O2 uptake alone. | Oxygen-electrode entry. |
| `.../a105_active_site_amount_case_150/PROPOSAL_001.md` | Fluorogenic peptide cleavage after active-site titration. | Fluorogenic entry. |
| `.../molecular_measurement/summary.md`, `EMERGING_LANES.md`, `SYNTHESIS.md` | Readout weaknesses: O2 uptake can be uncoupled; artificial mediators bypass coupled reactions (`chem_bcd_etf`, `chem_hydabc`, `chem_mvh_hdr`, `chem_nfnab`); a coupled partner can set the observed preference (`chem_f420_precursor_partner`); contaminant activity (`spec_aquifex_hfp_coupling_contamination`). | Controls fields. |
| Library `grading/experimental_activity_evidence/literature_assay_grading.py` | `QUANTITY_KINDS['activity_rate']` = rate, rate_difference, rate_ratio, turnover, catalytic_efficiency, kinetic_parameter(_difference/_ratio), log_kinetic_parameter_ratio, partner_rate_difference, partner_response_fraction. `CRITERIA_BY_TYPE['activity_rate']` = `COMMON_CRITERIA` + rate_regime, normalization_basis, kinetic_model, partner_perturbation. Rate unit vocabulary: U/mg, U/mL, uM/min, uM/s, mM/min, mM/s, nM/min, nM/s, mmol/min, umol/min, nmol/min, nmol/s, pmol/min, umol/min/mg, nmol/min/mg, pmol/min/mg, per_min, per_s, s^-1, min^-1; turnover and efficiency vocabularies alongside. | Native outputs and units (section 2). |
| Library `grading/experimental_activity_evidence/literature_row_contract.py`, `literature_claim.py` | `CLAIM_PREDICATES_BY_CLASS` holds only `ligand_binding: ('binds',)`; the comment names `catalyses` as an example for the other classes. `claim_of_hypothesis` accepts only `term_ref` / `reference` values. | Predicate (section 5). |
| `root/a105/.../tests/grading_world.py` (three copies) and `episode_support/grading/evolutionary_history_evidence/characterization.py` | Existing A105 test hypotheses use `predicate: 'catalyzes'` with `value: {'type': 'term_ref', 'ref': <reaction term>}`. A104's characterization maps `catalyzes` to {activity_rate, endpoint_conversion, product_distribution, reaction_coupling}. | Predicate spelling `catalyzes` and the partner-type problem (section 5). |
| Library `inputs/experimental_activity_evidence/literature_{rate_native,rate_observation,rate_replicate,optical,kinetic,kinetic_model,measurement_validation}_inputs.py` (headers only) | Old readers: source-bound rate operands, workbook cells, raw replicate tables, optical operands, kinetic estimates. All by display/data shape, none by technique. | Readers field. |
| `docs/EVIDENCE_AXIS_LEDGER.md` (grep) | "coupled" there means coupled grading actions, not coupled assays. No technique list. | Nothing. |
| Git history (`git log --all --grep` for activity_rate / inventory) | No hits. | Nothing. |
| Codex sessions `/home/chia/.codex/sessions/2026/10/` | **Not searched.** The grep was refused by the permission system. | Nothing. |

**Conclusion:** no prior per-technique enzyme-activity list or per-technique criteria exist in the places searched,
as for binding. The prior work is organised by calculation (rate contrast, optical rate, kinetic fit, replicate
table, corrected activity). The list below is new, drafted from those cases plus domain knowledge.

---

## 2. What all `activity_rate` types share (the class core)

So that each type entry below lists only what differs.

**Evidences:** sheet `activity_rate` (predicate `catalyzes`, section 5).

**Native quantities common to every quantitative type** (each a record operand, `point` or `unavailable` with a
reason, never 0, never omitted):

- `rate` with its unit from the class vocabulary above (concentration/time, amount/time, amount/time/mass, U/mg, U/mL,
  or per-enzyme `s^-1`), plus `rate_spread` and `spread_kind` (SD, SEM, CI, fit SE, unstated "±"); the old cases
  show an unstated "±" must stay unstated, never read as SD (`01_csid_lhgo_001.md`).
- `control_rate` beside the test rate, same unit: no-enzyme, heat-inactivated, catalytic-mutant or no-substrate
  control (each a different control; `biochemical_assay_guides_318`).
- `enzyme_amount` and its basis (molar, mass of total protein, mass of target, active sites); the
  `normalization_basis` criterion. Mass purity is not active fraction.
- `substrate_concentration` (and co-substrate), and `km` with its spread when stated; `kcat`, `kcat_over_km` with
  spreads when stated. A kinetic parameter is an output of any type below, not a type of its own.
- `concentration_series` (count, lowest, highest) when a saturation curve is stated.
- `time_window` of the rate and `fraction_converted` (or initial and remaining substrate) in that window; the
  `rate_regime` criterion.
- `replicate_count` and `replicate_kind` (technical repeats, independent reactions, independent preparations);
  count only, no cut-off.
- `detection_limit` (or quantification limit) when stated, for nondetection results.
- Identity block (automatic): `target_id` (the enzyme as written), optional `partner_id`, `temperature_c`, pH.

**Facts common to every type** (`yes` / `no` / `unknown` / `not_applicable`): no-enzyme control done; inactive-enzyme
(heat or mutant) control done; no-substrate control done; rate taken from the linear part of the progress curve;
native substrate (versus surrogate); purified enzyme (versus extract or cells); product chemically identified.

**Owner biochemical questions mapped to the core:** sensitivity -> `detection_limit`, rate over control; kinetic
parameters -> `km`, `kcat`, series; heating -> `temperature_c` and a heating/pretreatment fact; in vitro / in vivo ->
purified-enzyme fact; realism of chemistry -> native-substrate fact, pH; expected signal in messy samples ->
calibration recovery (where the type has one); spontaneous reaction -> `control_rate` and the no-enzyme fact.

**Certainty, quantitative types:** the effect is the rate (or a rate ratio) read against the paper's own control
and its own spread. **Qualitative types** (zymogram; any type that only reports "activity detected" / "no activity
detected") carry a statement and no constant.

**Readers that supply it (all types):** text paragraphs (Methods + Results) and tables (`table` and `report` leaves).
Progress curves, Michaelis-Menten and Lineweaver-Burk plots and figure-only rates are **unavailable** today (SOP
Known gaps: figures are not read). Workbook/XLSX supplements were read by the old readers
(`literature_rate_observation_inputs.py`) but are not wired into the current leaves.

---

## 3. The draft experiment list (19 types)

Grouped by family. Type ids are snake_case and do not collide with the 25 binding ids (`itc` is taken, so the ITC
kinetics type is `itc_kinetics`). Decided 2026-11-21, owner to confirm: all 19 stand, none merged (section 6, decision 1).

| # | Type id | Experiment | Family |
| --- | --- | --- | --- |
| 1 | `spectro_direct` | Continuous direct spectrophotometric (absorbance) assay | Optical, continuous |
| 2 | `coupled_enzyme` | Continuous coupled (auxiliary-enzyme) assay | Optical, continuous, indirect |
| 3 | `redox_mediator` | Artificial electron donor/acceptor dye assay (stays apart from 1, decided) | Optical, continuous, indirect |
| 4 | `fluorogenic` | Fluorogenic / fluorescent substrate or product assay | Optical, continuous |
| 5 | `luminescent` | Luminescent product-detection assay (luciferase-coupled ATP/ADP etc.) | Optical, plate, stopped or continuous |
| 6 | `stopped_flow` | Stopped-flow rapid mixing (pre-steady-state, single turnover) | Rapid kinetics, continuous |
| 7 | `quench_flow` | Rapid chemical quench-flow (stays apart from 6, decided) | Rapid kinetics, discontinuous |
| 8 | `chromatographic` | Discontinuous HPLC / LC-MS / GC product (or substrate) quantification | Separation, discontinuous |
| 9 | `stopped_colorimetric` | Stopped assay with colorimetric derivatization (malachite green phosphate, DNS, DTNB, chromogenic) | Optical, discontinuous |
| 10 | `radiometric` | Radiolabelled substrate, product separated and counted | Isotope, discontinuous |
| 11 | `separation_band` | Gel / TLC separation of substrate and product (nuclease, ligase, protease, kinase) with densitometry | Separation, discontinuous |
| 12 | `oxygen_electrode` | O2 consumption/evolution by Clark-type or optical O2 sensor | Electrode, continuous |
| 13 | `ph_stat` | pH-stat titration of released protons (esterase, lipase, carbonic anhydrase) | Electrode, continuous |
| 14 | `protein_film_electrochem` | Protein-film voltammetry / chronoamperometry catalytic current | Electrode, continuous |
| 15 | `itc_kinetics` | Isothermal titration calorimetry enzyme kinetics (heat rate) | Calorimetric, continuous |
| 16 | `continuous_ms` | Continuous mass spectrometry (membrane-inlet MS, real-time ESI-MS) | MS, continuous |
| 17 | `nmr_timecourse` | Real-time NMR progress curve | NMR, continuous |
| 18 | `product_immunodetection` | Antibody detection of the modified product (TR-FRET/HTRF, ELISA, AlphaScreen read-out of phospho- or other product) | Immuno, stopped |
| 19 | `zymogram` | In-gel activity staining (zymography) | Gel, qualitative |

**Considered and not listed as types** (with the reason):

- *Steady-state Michaelis-Menten / kinetic parameter determination*: an analysis applied to rates from any type above;
  recorded as `km`/`kcat`/series quantities and the `kinetic_model` criterion, not a protocol of its own.
- *Partner omission / addback*: an experimental design (the `partner_perturbation` criterion, quantity kinds
  `partner_rate_difference`, `partner_response_fraction`) run with any detection type; a fact set on the record, not
  a type. Ask the owner whether it should instead be its own type, since the Codex roster had it as a family (6).
- *Inhibition (IC50, Ki)*: measured with these assays, but it bears on "inhibitor binds/inhibits enzyme", a different
  claim; `QUANTITY_KINDS['activity_rate']` has no IC50 kind. Out of this class unless the owner rules otherwise.
- *Endpoint conversion, product spectrum, coupling stoichiometry*: the `endpoint_conversion`, `product_distribution`
  and `reaction_coupling` classes (completion time, NMR equilibrium fractions, P450cam product/NADH coupling).
- *Whole-cell / extract activity and growth*: a context fact (purified versus extract) on any type; growth belongs to
  A106.
- *Polarimetry, conductometry, manometry (Warburg), capillary electrophoresis*: rare or covered by 8/12; add if a real
  paper needs them.

### 3.1 `spectro_direct`

```text
experiment:            continuous direct spectrophotometric assay        (type id spectro_direct)
family:                optical, continuous, direct chromophore
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  absorbance slope (dA/min) and wavelength (nm); extinction coefficient (M^-1 cm^-1 or
                       mM^-1 cm^-1) and path length (cm) when stated; rate in the class rate units after conversion;
                       km, kcat, kcat/km when a series is fitted
controls required:     no-enzyme blank slope (spontaneous substrate/cofactor change, e.g. NADH oxidation);
                       inactive-enzyme control; no-substrate control (enzyme-dependent cofactor turnover);
                       stated extinction coefficient at the assay pH (FolM: composite coefficients differ ~2x)
noise expectations:    paper states the rate spread and its kind; blank slope beside the test slope; absorbance
                       range (detector linearity) separately from time linearity; inner-filter at high substrate
replicates needed:     replicate_count + replicate_kind (technical traces vs independent reactions vs preparations)
certainty:             quantitative: net rate (test - blank) against its own spread and against the blank
readers that supply it:text (Methods: wavelength, coefficient, conditions; Results: rates), tables (specific activity,
                       kinetic tables); progress-curve figures unavailable
past work (where):     a105_optical_case_031 (Bcd/EtfAB NADH 340 nm, PMC2223550); FrsA pNPA (PMC6450606,
                       template_a105_reactions_001/04); FolM (PMC2805310, 09); LhgO UQ1 reduction (PMC6265302, 01);
                       old sheet "NADH optical rate" (SHEETS.tsv 11), literature_optical_inputs.py
```

### 3.2 `coupled_enzyme`

```text
experiment:            continuous coupled-enzyme assay                   (type id coupled_enzyme)
family:                optical, continuous, indirect (reporter enzyme converts product to a chromophore change)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  reporter slope (dA/min at 340 nm for NAD(P)H, or other); rate in class units; coupling
                       enzyme amounts (U or U/mL) and the measured primary rate, so their ratio is available;
                       lag time (min or s) when stated
controls required:     no-primary-enzyme control (reporter background); coupling-system check by adding the
                       intermediate (FrsA 2013 added acetaldehyde at the end to show ADH was active); test that the
                       rate scales with primary-enzyme amount; no-substrate control; check the test compound does
                       not inhibit the coupling enzymes
noise expectations:    paper states the spread; coupling capacity relative to the measured rate (excess); reporter
                       stoichiometry per product (e.g. 1 NADH per product); stated or not, the lag phase
replicates needed:     count + kind, no cut-off
certainty:             quantitative: rate of the primary reaction only if coupling is not limiting; the degree falls
                       as the coupling capacity approaches the measured rate (the curve is researched by the type's builder, SOP step 3)
readers that supply it:text, tables
past work (where):     frsa_2013_review.md (ADH/NADH, 10.1021/bi400093y); moral_2011_review.md (FDH-coupled formate,
                       10.1016/j.ab.2011.06.031); a105_raw_rate_primary_case_164 (BbPK AckA/HK/G6PDH NADPH);
                       RidA (PMC3270999); F420 partner-coupled pair (PMC8764529: a downstream partner can set the
                       observed preference); old literature_rate_native_inputs.py
```

### 3.3 `redox_mediator` (stays apart from `spectro_direct`: decided 2026-11-21, owner to confirm)

```text
experiment:            artificial electron donor/acceptor assay          (type id redox_mediator)
family:                optical, continuous, indirect (DCPIP, ferricyanide, methyl/benzyl viologen, TTC, quinones)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  dye slope (dA/min at the dye wavelength); dye coefficient; rate in class units (often
                       umol/min/mg or U/mg)
controls required:     no-enzyme dye reduction/oxidation; no-substrate (electron-donor) control; anaerobic control
                       where O2 reoxidises the dye; a physiological-acceptor comparison when the claim is the native
                       reaction (a mediator can bypass the native partner)
noise expectations:    spread; dye background slope; mediator-bypass statement (Bcd/Etf: methyl viologen drops H2
                       rate 5 -> 0.02 and NADH rate 7 -> 5 umol/min/mg)
replicates needed:     count + kind
certainty:             quantitative rate, with the surrogate-acceptor fact lowering assertion relevance, not the rate
readers that supply it:text, tables
past work (where):     a105_optical_case_031 Table 2; molecular_measurement chem_bcd_etf, chem_hydabc, chem_mvh_hdr,
                       chem_nfnab; test_literature_assay_grading_primary.py (activity_rate rate_ratio, TTC substrate
                       omission, C. kluyveri Bcd/Etf table, via read_rate_table)
why separate:          the controls (dye background, mediator bypass, O2) differ from a direct chromophore; if the
                       owner prefers, it becomes spectro_direct with a surrogate-acceptor fact
```

### 3.4 `fluorogenic`

```text
experiment:            fluorogenic / fluorescent substrate or product    (type id fluorogenic)
family:                optical, continuous (AMC/AFC peptides, resorufin, MUF glycosides, NADH fluorescence, FRET
                       peptide substrates)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  fluorescence slope (RFU/min, arbitrary); excitation/emission (nm); calibration slope of free
                       fluorophore (RFU per uM) when stated; rate in class units only after calibration
controls required:     no-enzyme (substrate autohydrolysis); free-fluorophore standard curve in the same buffer;
                       inner-filter/quenching check at the substrate concentrations used; test-compound
                       autofluorescence/quench control (AGM fluorescence interference)
noise expectations:    spread; background RFU slope; calibration stated or not (RFU/min alone cannot give kcat,
                       verification 532 on protease kinetics)
replicates needed:     count + kind
certainty:             quantitative when calibrated; otherwise a relative rate (ratio to the paper's own control or
                       reference arm) with the absolute rate unavailable
readers that supply it:text, tables
past work (where):     a105_active_site_amount_case_150 (fluorogenic peptide after active-site titration);
                       verification/tool_graders_biochemical_measurement_boundaries_..._532 (protease kinetics)
```

### 3.5 `luminescent`

```text
experiment:            luminescent product detection                     (type id luminescent)
family:                optical, plate (ADP-Glo, Kinase-Glo, NAD(P)H-Glo, luciferase-coupled PPi detection)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  RLU (arbitrary), signal over background, % conversion from an ATP/ADP standard series,
                       time point(s) (min); rate in class units only via the standard series
controls required:     no-enzyme; no-substrate (autophosphorylation/ATPase background for kinases); ADP/ATP
                       standard series; luciferase-inhibition counter-screen when test compounds are present
noise expectations:    spread; Z' or signal/background when stated; standard series range relative to the
                       measured signal
replicates needed:     count + kind
certainty:             quantitative (calibrated) or relative to the paper's own control
readers that supply it:text, tables
past work (where):     none found in the places searched
```

### 3.6 `stopped_flow`

```text
experiment:            stopped-flow rapid mixing                         (type id stopped_flow)
family:                rapid kinetics, continuous (absorbance or fluorescence, ms dead time)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  observed rate constant k_obs (s^-1) with fit error; burst amplitude (fraction of enzyme or
                       uM); single-turnover rate (s^-1); dead time (ms); concentration dependence of k_obs
controls required:     mix with buffer (no-substrate) trace; enzyme-free trace; dead time stated; enzyme in
                       excess over substrate for single turnover (or stated otherwise)
noise expectations:    fit SE of k_obs; number of averaged shots; k_obs relative to the dead time (a k_obs close to
                       1/dead time is less certain)
replicates needed:     shots averaged (count) and independent experiments (count + kind)
certainty:             quantitative: a chemical-step rate constant; bears on catalyzes when the step forms product
readers that supply it:text, tables; traces are figures (unavailable)
past work (where):     none found in the places searched
```

### 3.7 `quench_flow` (stays apart from `stopped_flow`: decided 2026-11-21, owner to confirm)

```text
experiment:            rapid chemical quench-flow                         (type id quench_flow)
family:                rapid kinetics, discontinuous (acid/base quench, product quantified by HPLC, radioactivity
                       or MS)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  product formed per time point (uM or fraction of enzyme); burst amplitude; k_obs / k_chem
                       (s^-1); quench time range (ms)
controls required:     zero-time (quench before mix) control; no-enzyme control; quench efficiency stated
noise expectations:    fit SE; number of time points; spread of points
replicates needed:     count + kind
certainty:             quantitative: directly product-identified rate of a chemical step
readers that supply it:text, tables
past work (where):     none found
why separate:          product is chemically identified (not an optical proxy) and the controls differ; the owner
                       may merge it with stopped_flow as "pre-steady-state kinetics"
```

### 3.8 `chromatographic`

```text
experiment:            discontinuous chromatographic product/substrate quantification   (type id chromatographic)
family:                separation, discontinuous (HPLC-UV, LC-MS, GC, GC-MS headspace gas, ion chromatography)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  product (or substrate) amount per time point (uM, nmol); rate in class units; retention
                       time and m/z of the product; standard curve and internal standard when stated; LOD/LOQ
controls required:     authentic product standard (identity and calibration); no-enzyme; boiled or catalytic-
                       mutant enzyme; zero-time sample; internal standard for MS; matrix-matched calibration for
                       extracts
noise expectations:    spread; number of time points defining the rate (one endpoint gives an average, not an
                       initial rate); calibration recovery of a known standard
replicates needed:     count + kind
certainty:             quantitative, product chemically identified; nondetection bounded by the stated LOD
readers that supply it:text, tables
past work (where):     PARP1 HPLC concentration window (319 entry 12); BbPK direct HPLC acetate (case 164); CysQ AMP
                       MS with internal standard (PMC2711008); CsiD LC-MS identity (PMC6265302); Bcd/Etf H2 formation
                       (PMC2223550); old literature_rate_replicate_inputs.py, calibration_recovery sheet (SHEETS 24)
```

### 3.9 `stopped_colorimetric`

```text
experiment:            stopped assay with colorimetric derivatization    (type id stopped_colorimetric)
family:                optical, discontinuous (malachite green / molybdate phosphate, DNS or BCA reducing sugar,
                       DTNB thiol, hydroxamate, Nessler/Berthelot ammonia, chromogenic AcP)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  absorbance at the reagent wavelength; product amount from a standard curve (nmol, uM); rate
                       per time point or per window; LOD when stated
controls required:     product standard curve in the reaction buffer; no-enzyme and zero-time blanks; substrate-
                       only blank (substrate reacting with the reagent, e.g. free phosphate in ATP)
noise expectations:    spread; blank beside the test; standard-curve range relative to measured amounts; number of
                       time points
replicates needed:     count + kind
certainty:             quantitative; a product class (phosphate, reducing end, thiol) rather than a named product
readers that supply it:text, tables
past work (where):     BbPK chromogenic AcP (case 164); CysQ colour assay (cannot resolve low-uM kinetics,
                       molecular_measurement spec_cysq_pap_not_imp)
```

### 3.10 `radiometric`

```text
experiment:            radiolabelled substrate assay                     (type id radiometric)
family:                isotope, discontinuous (14C, 3H, 32P, 35S; product separated by TLC, filter binding, ion
                       exchange, or released as 14CO2; counted by scintillation or phosphorimager)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  counts (cpm, dpm) or PSL; specific radioactivity of substrate (Ci/mol, cpm/nmol); product
                       amount and rate in class units after conversion
controls required:     no-enzyme; boiled enzyme; zero-time; separation control (substrate alone through the
                       separation step, gives carry-over background); stated specific activity
noise expectations:    spread; background counts beside test counts; counting efficiency stated or not
replicates needed:     count + kind
certainty:             quantitative and very sensitive; identity of product depends on the separation
readers that supply it:text, tables
past work (where):     none found in the places searched
```

### 3.11 `separation_band`

```text
experiment:            gel / TLC separation of substrate and product with densitometry   (type id separation_band)
family:                separation, discontinuous (nuclease, ligase, polymerase, protease cleavage, kinase with
                       mobility shift; TLC of nucleotides/lipids)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  fraction of substrate converted per time point (fraction or %); band intensities; rate
                       (fraction/min, nM/min, or k_obs min^-1) from a time course
controls required:     no-enzyme lane; catalytic-mutant lane; size/product markers; metal-free (EDTA) lane for
                       metal-dependent enzymes
noise expectations:    spread across gels; densitometry linear range; number of time points
replicates needed:     count + kind
certainty:             quantitative (fraction converted over time) or qualitative (product band present/absent)
readers that supply it:text, tables; gel images are figures (unavailable)
past work (where):     none found for activity (the old gel sheet, SHEETS 17, is protein bands: protein_signal)
```

### 3.12 `oxygen_electrode`

```text
experiment:            O2 consumption/evolution by electrode or optical O2 sensor   (type id oxygen_electrode)
family:                electrode, continuous (Clark-type, Oroboros, optode)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  O2 rate (nmol O2/min, umol O2/min/mg, uM/min); stated O2 solubility/calibration (air-
                       saturated O2 concentration at the temperature)
controls required:     no-enzyme and no-substrate O2 drift; electrode calibration (air and zero O2); catalase or
                       product check to separate coupled from uncoupled O2 use (CsiD: O2 uptake alone can be
                       uncoupled oxygenase chemistry)
noise expectations:    spread; background drift beside the test rate
replicates needed:     count + kind
certainty:             quantitative O2 rate; the reaction is assigned only with product identification (a fact)
readers that supply it:text, tables
past work (where):     CsiD Clark electrode (a105_dataset_example_004, PMC6265302, 53 +/- 3 umol/min/mg, ± kind
                       unstated); LhgO membrane O2 (01_csid_lhgo_001.md); read_assay_inputs and
                       literature_rate_replicate tests (synthetic O2 consumption)
```

### 3.13 `ph_stat`

```text
experiment:            pH-stat titration                                  (type id ph_stat)
family:                electrode, continuous (protons released or consumed, titrant added to hold pH)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  titrant addition rate (umol/min); rate in class units (U/mg); pH set point
controls required:     no-enzyme (substrate/emulsion autohydrolysis); CO2 exclusion; titrant standardization;
                       stated proton yield per product at the set pH
noise expectations:    spread; background titrant rate beside test
replicates needed:     count + kind
certainty:             quantitative
readers that supply it:text, tables
past work (where):     none found
```

### 3.14 `protein_film_electrochem`

```text
experiment:            protein-film voltammetry / chronoamperometry      (type id protein_film_electrochem)
family:                electrode, continuous (enzyme adsorbed on an electrode, catalytic current)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  catalytic current (nA, uA) or current density; turnover (s^-1) when electroactive coverage
                       (pmol/cm^2) is stated; potential (V vs reference)
controls required:     bare-electrode (no-enzyme) current; no-substrate current; electroactive coverage
                       measurement; film-loss correction
noise expectations:    spread across films; film decay over the measurement
replicates needed:     count of films/electrodes + kind
certainty:             quantitative (relative unless coverage is measured)
readers that supply it:text, tables
past work (where):     none found (the old channel sheet, SHEETS 33, is transport currents)
ROLE mapping note:     the only type here with an immobilized enzyme: enzyme -> immobilized, electrode -> surface
```

### 3.15 `itc_kinetics`

```text
experiment:            isothermal titration calorimetry enzyme kinetics  (type id itc_kinetics)
family:                calorimetric, continuous (thermal power proportional to rate x reaction enthalpy)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  thermal power (ucal/s, uW); apparent reaction enthalpy (kcal/mol, kJ/mol); rate in class
                       units; km, kcat from a single or multiple-injection experiment
controls required:     substrate into buffer (dilution heat); enzyme into buffer; separately measured reaction
                       enthalpy (single-injection full conversion)
noise expectations:    fit SE; baseline noise beside the signal; dilution heat beside reaction heat
replicates needed:     count + kind
certainty:             quantitative, label-free, any product; no product identity
readers that supply it:text, tables
past work (where):     none found (verification 532 covers an ITC binding tool only)
```

### 3.16 `continuous_ms`

```text
experiment:            continuous mass spectrometry                       (type id continuous_ms)
family:                MS, continuous (membrane-inlet MS for gases, real-time ESI-MS)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  ion current at m/z (A or counts/s); calibration to concentration; rate in class units;
                       isotope label (e.g. 13C) when used
controls required:     no-enzyme; calibration with known gas/analyte amounts; isotope-label control separating
                       enzymatic from background product
noise expectations:    spread; calibration stated or not; background ion current beside test
replicates needed:     count + kind
certainty:             quantitative with product identity by mass
readers that supply it:text, tables
past work (where):     moral_2011_review.md (OxDC MIMS versus FDH-coupled endpoint, 10.1016/j.ab.2011.06.031)
```

### 3.17 `nmr_timecourse`

```text
experiment:            real-time NMR progress curve                      (type id nmr_timecourse)
family:                NMR, continuous (1H, 13C, 31P, 19F)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  integral per species per time (relative or uM against an internal standard); rate in class
                       units; chemical shift (ppm) assignments
controls required:     no-enzyme spectrum series; internal concentration standard; authentic product reference
                       spectrum
noise expectations:    spread; signal/noise of integrals when stated; number of time points
replicates needed:     count + kind
certainty:             quantitative with product identity; low sensitivity (high enzyme/substrate amounts, which
                       affects condition_scope)
readers that supply it:text, tables
past work (where):     QueF NMR (PMC555470); sulfoglycolysis (molecular_measurement); HFP NMR fractions
                       (PMC12051542, used under product_distribution, not this class)
```

### 3.18 `product_immunodetection`

```text
experiment:            antibody detection of the modified product       (type id product_immunodetection)
family:                immuno, stopped (TR-FRET/HTRF, ELISA, AlphaScreen/AlphaLISA product read-outs; phospho-,
                       methyl-, acetyl- or ubiquitin-product)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  signal ratio (665/620 for TR-FRET), absorbance, counts; product amount from a product
                       standard series when stated; time point(s)
controls required:     no-enzyme; no-cofactor (no ATP / no SAM / no acetyl-CoA); catalytic mutant; product
                       standard series; antibody specificity for the product over the substrate
noise expectations:    spread; Z' or signal/background; standard range relative to signal
replicates needed:     count + kind
certainty:             quantitative (calibrated) or relative to the paper's own control
readers that supply it:text, tables; blots are figures (unavailable)
past work (where):     none found
boundary note:         a western blot of a phospho-substrate in cells overlaps protein_signal; the owner should
                       rule where cell-based phospho-blots go
```

### 3.19 `zymogram`

```text
experiment:            in-gel activity staining (zymography)            (type id zymogram)
family:                gel, qualitative (gelatin/casein zymography, in-gel dehydrogenase staining with NBT/PMS,
                       esterase/amylase activity stains)
evidences (sheet):     activity_rate                                     (predicate: catalyzes)
native outputs/units:  no constant; statement "activity band detected at the protein's migration position" or
                       "not detected"; band position (kDa) when stated
controls required:     no-substrate (or no-cofactor) stained lane; inactive mutant or heat-treated lane; inhibitor
                       lane (e.g. EDTA for metalloproteases); a protein stain of the same gel for band assignment
noise expectations:    statement only; negative-control lane free of the band (a band in the negative lane is
                       conflicting)
replicates needed:     count + kind
certainty:             qualitative: activity detected / not detected (needs a QUALITATIVE_STATEMENT decision,
                       section 6)
readers that supply it:text (figure legends and Results text); gel images unavailable
past work (where):     none found
```

---

## 4. Direction and judgement for the class (decided 2026-11-21, owner to confirm)

The draft of this section proposed generic forms (`d = n/(n + 1)`, `d = (f - 1)/f`, `d = 1 - p` and similar) for every
criterion. **The owner rejected generic forms of that kind. They are deleted and must not be used.** The per-criterion
judgement of each experiment type is SOP step 3: the values are researched for that assay (its method literature and its
physics), each carries its reason and is tagged `EXPERT_REVIEW`, "owner to confirm", and each is made gradual around the
researched value (full agreement at the researched good value, smooth fall towards a researched no-longer-meaningful
value; never a step; unknown when the paper states nothing; an unknown weight is never part of a degree). The builder of
each type researches them with that type's controls and noise (the per-type entries in section 3 list what each paper must
state).

**Direction and strength of a quantitative activity result** (class-scoped; code in
`G/literature_activity_direction.py`, constants in `G/literature_row_contract.py` section 5c). Same paradigm as binding
(`G/literature_direction.py`, `QUANTITATIVE_STRENGTH_ANCHORS`):

```text
p = clip( (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), 0, 1 )      (for rates LARGER is stronger)
s = (3 p^2 - 2 p^3) / (1 + r^2),    r = sd / e    (0 when no spread is stated)
log_ratio = QUALITATIVE_LOG_RATIO[type] * s
```

- A stated rate SUPPORTS by its graded strength `s`; `s == 0` (at or under the noise end) is neutral. A quantitative result
  never opposes. Controls, blanks, the initial-rate regime and the other sheet criteria lower the WEIGHT only, never the
  direction (as for binding).
- The paper itself showing no activity above its own control or detection limit is the measured-zero / not-detected
  case: the qualitative path (statement `interaction_not_detected`, read "activity not detected"), which opposes.
- Anchors are per QUANTITY, not per experiment type (the physics is the same in every assay). Each is `EXPERT_REVIEW`,
  owner to confirm; the literature figures are from memory and must be verified:

| Quantity | Unit | noise_end | strong_end | Reason |
| --- | --- | --- | --- | --- |
| catalytic efficiency kcat/Km | M^-1 s^-1 | 1e2 | 1e6 | Bar-Even et al. 2011 Biochemistry 50:4402 (from memory): median natural kcat/Km near 1e5, upper quartile near 1e6. Promiscuous (side) activities sit near 1e3 (Khersonsky and Tawfik 2010 Annu Rev Biochem 79:471, from memory); the noise end is one decade under that. |
| turnover kcat | s^-1 | 1e-2 | 1e2 | Same source: median kcat near 10 s^-1, upper quartile near 70, rounded to 1e2. Promiscuous kcat is about 1e-2 to 1 s^-1; the noise end is the low end. |
| specific activity | U/mg | kcat noise end at the enzyme mass | kcat strong end at the enzyme mass | `U/mg = kcat x 60 x 1000 / M` (M in g/mol): the ends are derived from the kcat ends at the stated enzyme mass, else at the reference mass 5e4 g/mol (50 kDa, a typical subunit; `REFERENCE_ENZYME_MASS_G_PER_MOL`). At 50 kDa the ends are 0.012 and 120 U/mg. |
| rate over the paper's own control | fold | 1 | 1e3 | No better than the control is the noise end; three orders over background is the practical dynamic range of most activity assays. A fold at or under 1 is strength 0 (neutral), never opposition. |

- Consistency of the two scales: the median natural enzyme sits at `p = 0.75` on both the kcat/Km and the kcat scale.
- The effect used when a record states several is the best-determined one, in the order catalytic efficiency, turnover,
  specific activity, rate over control (`ACTIVITY_EFFECT_ORDER`, `select_activity_effect`). Why: kcat/Km is a ratio of two
  fitted constants and needs neither the active-site amount nor saturation; kcat needs the active-site concentration and a
  saturating curve; specific activity needs only a protein mass, which includes inactive protein, at one substrate
  concentration; a fold is relative to a control whose own activity differs between papers.
- `direction_field_support` is the support class of the field that fixes the direction (the chosen effect).
- A converter of an `activity_rate` type must also return `enzyme_mass_g_per_mol` (the stated molar mass, or None);
  `literature_page_update` passes it to the direction function.
- `QUALITATIVE_LOG_RATIO[type]` (the per-type maximum) is added with each type; whether a per-type constant stands under the
  no-threshold rule is still open (SOP Known gaps).

---

## 5. Claim predicate (decided 2026-11-21, owner to confirm; the options below are kept as the record of the question)

**Decided and implemented in `G`:** `catalyzes` is in `CLAIM_PREDICATES_BY_CLASS['activity_rate']`, not symmetric. Subject =
the enzyme (the record's `target_id`). When the hypothesis value is a `reference` to a molecule record, that molecule is the
claim's partner (the substrate); the record's stated substrate must then agree, else `different_subject`
(`partner_contradicts_claim`). When the value is a `term_ref` (the existing A105 hypotheses carry a reaction term), the
claim's partner is null and bearing is by the target alone (`literature_claim.TERM_PARTNER_IS_NOT_A_MOLECULE`). **Limit:** G
sees only the labels of the records, not the term type, so a `term_ref` that is a chemical (a substrate given as a term) is
also read as target-only. Keeping it as a substrate partner needs the caller (the page's `hypothesis_claim` in `task.py`)
to pass the term types: a change outside G, reported, not made.

Earlier analysis:

- **Predicate:** `catalyzes` (spelling already used by A105 test hypotheses in `root/a105/.../tests/grading_world.py`
  and by A104 `characterization.py`; the contract comment's `catalyses` spelling should not be used).
- **Classes:** `activity_rate` (and, per the SOP 0b proposal and A104's mapping, `endpoint_conversion`,
  `product_distribution`, `reaction_coupling` when those classes are added).
- **Symmetric:** **no.** "E catalyzes R" is not "R catalyzes E". Do not add it to `SYMMETRIC_PREDICATES`.
- **Subject:** the enzyme (record `target_id`, the assayed protein as written).
- **Partner:** optional. **Problem found, raise with the owner, do not patch silently** (SOP 0b): the existing A105
  hypotheses carry `value: {'type': 'term_ref', 'ref': <reaction term>}` (term_type `reaction`, label e.g.
  "Hydrolysis"). `claim_of_hypothesis` accepts `term_ref`, so a claim **is** read, but its `partner_id` becomes the
  reaction term's label. A leaf names the partner "as written" in the passage, normally a substrate ("p-nitrophenyl
  acetate"), and bearing compares partner names by normalized equality. A reaction label and a substrate name will
  almost never be equal, so a stated partner gives `different_subject` instead of `direct`. Options for the owner:
  1. Partner = the substrate (hypothesis value a `reference` to the substrate molecule); the leaf states the substrate
     as `partner_id` with `partner_role` substrate. Fits "a claim names molecules only".
  2. Partner = null for `catalyzes`; bearing by target only; the reaction stays a hypothesis value the sheet does not
     read. Simplest; loses substrate specificity.
  3. Partner = the reaction term, with the leaf asked for the reaction name. Breaks "a claim names molecules only".
  Draft recommendation: option 1, with option 2 as the behaviour when the hypothesis has no substrate.
- **No second predicate proposed.** Candidates for the owner: `activates` / `is_required_for_activity_of` for
  partner omission/addback results (quantity kinds `partner_rate_difference`, `partner_response_fraction`), and
  `inhibits` for IC50/Ki (outside this class's quantity kinds today).

---

## 6. Class decisions before the first type (SOP 0c), as read from the code (decisions of 2026-11-21 below the table)

| Item | Finding | Proposal (owner to decide) |
| --- | --- | --- |
| `QUANTITY_KINDS['activity_rate']`, `CRITERIA_BY_TYPE` | 11 kinds; criteria `COMMON_CRITERIA` + rate_regime, normalization_basis, kinetic_model, partner_perturbation; `_required_criteria` makes kinetic_model optional for plain rates and rate_regime/normalization_basis optional for kinetic parameters. | Use as is. Each type's converter fills `rate` / `rate_ratio` / `turnover` / `catalytic_efficiency` / `kinetic_parameter` as stated. |
| `QUALITATIVE_STATEMENT` | Binding wording only (`interaction_detected`, ...). | Needed by `zymogram`, by `separation_band` when only a band is reported, and by any type reporting "no activity detected". Decided: no new values (decision 3 below); `interaction_detected` reads "activity detected". |
| `ROLE`, `IMMOBILIZATION_SIDES`, `ROW_DEPENDENCE_KEYS` | Binding-flavoured (`analyte`, `immobilized`, `surface`). | Enzyme preparation -> `analyte_preparation_ref`; substrate/coupling system -> `immobilized_preparation_ref` None; `surface_ref` None; except `protein_film_electrochem` (enzyme -> immobilized, electrode -> surface). Each converter documents its mapping. |
| Direction | `literature_direction` is nM-binding only. | Decided: a separate class-scoped function, section 4. |
| Hypothesis value type | `catalyzes` hypotheses carry a reaction `term_ref`. | Section 5. |
| One value, one method | The BbPK case shows U/mg values not bound to one of three methods in the same paper. | A leaf records a rate under a type only when the passage ties that rate to that method; otherwise no type can be named and the SOP's "a leaf that cannot name its type has no experiment" applies. |

---

### Decided 2026-11-21 (the owner told the coordinator to decide by the standing rules; owner to confirm)

1. **The 19 draft types stand, none merged.** `redox_mediator` stays apart from `spectro_direct` (its own controls: dye
   autoxidation, mediator specificity) and `quench_flow` apart from `stopped_flow` (chemical quench and separation, not an
   optical trace).
2. **Predicate `catalyzes`**, not symmetric; subject the enzyme; partner per section 5. Implemented in `G`.
3. **Qualitative results keep the existing `QUALITATIVE_STATEMENT` values** (no contract change). They state whether the
   CLAIMED RELATION was detected; for this class `interaction_detected` reads "activity detected",
   `interaction_not_detected` reads "activity not detected", `interaction_not_stated` reads "activity not stated". The
   earlier proposal to add `activity_detected` and the like is dropped. The reading is written beside the vocabulary in
   `G/literature_row_contract.py`.
4. **Preparations** map onto the existing keys as the table above proposes: enzyme preparation to
   `analyte_preparation_ref`; `immobilized_preparation_ref` and `surface_ref` None, except a type with an immobilized
   enzyme or an electrode (`protein_film_electrochem`: enzyme to immobilized, electrode to surface).
5. **Direction and strength** of a quantitative activity result: section 4 (same paradigm as binding, class-scoped function,
   anchors per quantity, larger is stronger, best-determined quantity first).

## 6c. Built: `spectro_direct` (the first type, 2026-11-21; all numbers EXPERT_REVIEW, owner to confirm)

Built by SOP steps 1 to 8; the other 18 types copy it. Files (`G` and `F` as in the SOP): `F/literature_spectro_direct_record.py`,
`F/literature_spectro_direct_extraction.py`, `G/literature_spectro_direct_criteria.py`, `G/literature_spectro_direct_grader.py`,
`G/literature_spectro_direct_converter.py`, the registrations (SOP step 4) and the tests listed in the build report.

- **Record** (30 fields): the four effect quantities each with its own spread (`catalytic_efficiency`, `turnover`, `specific_activity`,
  `rate_over_control`), `km`, `substrate_concentration`, `enzyme_concentration`, `substrate_consumed_percent`, `wavelength`,
  `extinction_coefficient`, `absorbance_max`, `enzyme_mass`, `replicate_count`, the substrate series, the spread kind and 11 facts (three
  controls, enzyme dependence, linear progress curve, active-site determination, native substrate, purified enzyme, product identified,
  independent replicates, activity detected above the control). Unit vocabularies per quantity; the converter turns another unit of the
  vocabulary into the anchor unit by an exact factor (FIXED_BY_DEFINITION).
- **Effect** = the best-determined stated quantity (class order); the spread of THAT quantity gives the variance (standard error, or standard
  deviation over n with independent replicates supported; a confidence interval is not converted).
- **Qualitative path** (decision 5): only when no quantity is stated, the fact `activity_detected_above_control` gives `interaction_detected`
  ("activity detected") or `interaction_not_detected` ("activity not detected", opposes).
- **Criteria** (13, grader) -> sheet criteria: background_alternatives (spontaneous_reaction_control, substrate_independent_signal),
  attribution_supported (enzyme_dependence, product_identity), calibration_applicability (extinction_coefficient_stated, absorbance_range),
  rate_regime (initial_rate_regime, enzyme_substrate_ratio), kinetic_model (substrate_range), normalization_basis (active_enzyme_amount),
  sampling_basis (replicates), assertion_relevance (native_reaction), condition_scope (purified_enzyme).
- **Researched curves** (reasons in the converter docstring, Q1-Q5): share of the substrate consumed 10 percent full to 90 percent zero, judged on
  the bias 1 - f / -ln(1 - f) of the averaged rate; enzyme over substrate plus Km 0.01 full to 1 zero (log scale); substrate series 6 concentrations
  full, 2 zero (residual degrees of freedom), lowest at most 0.2 Km and highest at least 10 Km (zero end 1 Km, fractional saturation); highest
  absorbance 1 full to 3 zero on the stray-light bias at 1 percent stray light; replicates sqrt(n / 3).
- **Unknown weights**: type default 0.85; background_alternatives 0.75, attribution_supported 0.80, calibration_applicability 0.90,
  normalization_basis 0.90, sampling_basis 0.90 (chain in the converter docstring and `A105_ASSAY_CALIBRATION_DETAILS.md`).
- **QUALITATIVE_LOG_RATIO** 1.2 (a stated rate at full strength, and "activity not detected").
- **Class gaps found by the build and fixed in `G` (decided 2026-11-21, owner to confirm)**: (1) `literature_assay_grading._quantity_unit_supported`
  accepts the unit `fold` for the kind `rate_ratio` (the class anchor unit of the rate over the paper's own control); (2) the result field `effect_unit`
  is now a unit spelling (`UNIT_PATTERN`, new field kind `unit`) instead of a record reference, because the activity units hold `^` (`s^-1`,
  `M^-1s^-1`); the page run failed on it; (3) `literature_row.NOT_POOLED_CLASSES = ('activity_rate',)`: the effect of a result is one of four
  quantities in different units, so the row's pooled effect, variance and precision are null for the class (the page run would have raised
  "no pooled unit is declared"). A claim whose partner is a named substrate must match the record's stated substrate (partner_contradicts_claim).
- **Real paragraph**: the Results paragraph on the steady-state kinetics of the flavin reductase ThdF, J Biol Chem 2025, doi
  10.1016/j.jbc.2024.108128, PMC11795597, PMID 39725031, CC BY 4.0 (Europe PMC full-text XML; the publisher's non-breaking spaces and minus signs
  kept). It states Km for NADH (19.5 uM) and FAD (0.34 uM) and kcat 0.21 +- 0.08 s^-1 (12.7 +- 4.9 min^-1) for ThdF, and cites the constants of
  three other enzymes (the distractors). A first choice, a paragraph on DfrA and DfrB (PMC6193120), was dropped: it names two enzymes, the model left
  the target unavailable as ambiguous in the page run (twice), so no claim could bear.

## 7. What is still open

- Owner confirmation or correction of the 19 types, including the boundary questions that are not about merging
  (partner omission/addback as a type or a design, inhibition, cell-based phospho-blots).
- Owner confirmation of every number in section 4 (all `EXPERT_REVIEW`; the literature figures are from memory).
- A change outside `G` for chemical `term_ref` partners (section 5).
- SOP 0d placement: the class list is copied into `A105_SCORING_DESIGN.md` section 6b, marked draft.
- The Codex sessions were not searched (permission refused); the October 150-paper inventory remains unfound.
- No real published paragraph has been found for any type yet (SOP step 6); the "past work" papers above are
  candidates, and only those with PMC ids (PMC2223550, PMC6265302, PMC6450606, PMC2805310, PMC2711008, PMC555470,
  PMC3270999, PMC8764529) are reachable through Europe PMC; their licences were not checked.
