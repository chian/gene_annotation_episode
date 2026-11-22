# A105 `transport_response` experiment inventory (SOP step 0, DRAFT for the owner to correct)

Written 2026-11-22 under `A105_EXPERIMENT_SOP.md` step 0, modelled on `A105_ACTIVITY_RATE_INVENTORY.md`. Read-only search; nothing was run
(no Python, no test, no script). Files written for this class: this document, `G/literature_transport_response_direction.py` and
`runs/a105_class_drafts/registration/CLASS_transport_response.md` (the exact source for the contract, pooling and page update).
G = `gene_annotation_episode/episodic_workflow/episode_support/literature/grading/experimental_activity_evidence`.

**Status: DRAFT for the owner to correct.** The owner has not supplied a `transport_response` list. Following SOP 0a item 2 the list
below is drafted from the sources found plus domain knowledge. **Nothing here is owner-confirmed.** It is one entry per reapplicable
protocol (a way of measuring), not per paper or per case. Every number marked EXPERT_REVIEW is for the owner to confirm; where it says
"from memory, not verified" the figure is recalled, not checked against the paper.

---

## 1. Sources searched and what was found

| Place | Found | Used for |
| --- | --- | --- |
| `docs/axis_restructure_20261117/A105_EXPERIMENT_SOP.md`, `A105_ACTIVITY_RATE_INVENTORY.md` | The protocol, the template and the one existing class inventory. | Structure of this document. |
| `docs/axis_restructure_20261117/EXPERIMENT_INVENTORY_SEARCH.md`, `..._SEARCH_2.md` | No per-technique transport list. The Codex roster has "4. Transport/substrate-response comparisons" as one family (transport 3/3 graders in the 315 inventory). The owner's remark that families are not graders and that each family holds several assays. | The class is one sheet with several protocols. |
| `verification/a105_sheet_reader_inventory_315/SHEETS.tsv` | Two old sheets: 7 "Transport substrate response" (`transport_response_cells_schema`, `read_transport_inputs`) and 33 "Electrical channel measurements" (`channel_cells_schema`, `read_channel_inputs`). Calculations, not techniques. | Past work fields; the electrophysiology types. |
| `research/experimental_scoring_review_2026-10-23/template_a105_transport_001/` (`01_bioy_2007.md`, `02_fluc_2013.md`, `03_yjeh_2015.md`, `04_fucp_2011_pnas.md`, `05_handoff_corrections_and_components.md`) | Four primary papers: BioY biotin uptake in E. coli (Hebbeln 2007, PNAS, filtration of 3H biotin, Vmax 60 pmol/min/mg, half-saturation 250 nM, 3.5 h accumulation about 1000-fold); Fluc fluoride channel (Stockbridge 2013, eLife 01084: ion-selective electrode on liposomes, planar bilayer single channels, 1.8 pA at -200 mV, reversal +53 mV, about 7.1 pS); YjeH amino-acid export in E. coli (Liu 2015, AEM, silicone-oil separation and DNFB-HPLC, nmol/min/mg dry weight); FucP fucose uptake in C. jejuni (Stahl 2011, PNAS, 14C fucose filtration, initial velocity over 120 s). | Whole-cell tracer, medium analysis, vesicle ion-electrode and planar-bilayer types; the units and the controls. |
| `.../template_a105_transport_002/` (`02_btst_2018_components.md`, `03_csta_ybdd_2018_endpoint.md`, `04_vbnc_pyruvate_2019_components.md`, `06_murj_2014_accessibility_components.md`, `08_transport_sheet_reconciliation.md`, `08_synthetic_arithmetic.json`, the PMC html and txt files) | BtsT pyruvate/H+ symport (Kristoficova 2018, J Bacteriol, whole cells 14C, Km 16.5 +/- 6.4 uM, uptake about 6x empty vector, proteoliposomes with imposed delta-pH and delta-psi); CstA/YbdD pyruvate disappearance from the medium (10 min interval, Cedex analyzer); pyruvate uptake in VBNC cells (nmol/mg protein over 20 s); MurJ lipid-II flippase read by a reporter (a flipping assay, boundary); `07_pxpt_pxpr` and `05_hpnn` are binding and localization boundary notes. The reconciliation note lists the transport quantities (net rate, endpoint amount, fraction over blank, per-molecule rate) and the controls. | The record quantities, controls and noise fields; the "endpoint is not an initial rate" rule; the boundary list in section 3. |
| `research/experimental_scoring_review_2026-10-23/a105_transport_channel_case_174/` (`REPORT.md`, source xml of eLife 01084) | The Fluc channel case in full (current, reversal potential, selectivity ratio). | Electrophysiology fields. |
| `research/experimental_scoring_review_2026-10-23/molecular_measurement/summary.md`, `EMERGING_LANES.md`, `SYNTHESIS.md` (grep) | Transport shows up as lanes of readout weakness (surface binding, trapping, metabolism, residual host uptake). No technique list. | Controls and attribution fields. |
| `verification/biochemical_assay_guides_318`, `verification/biochemical_fourteen_graders_319` | Enzyme assays only; no transport entry. | Nothing. |
| `G/literature_assay_grading.py` | `QUANTITY_KINDS['transport_response']` = transport_rate, transport_rate_ratio, log_transport_rate_ratio, accumulated_amount, transport_parameter, substrate_saturation, substrate_response_ratio, log_substrate_response, electrical_current, electrical_conductance, charge_equivalent_rate. `CRITERIA_BY_TYPE['transport_response']` = `COMMON_CRITERIA` + membrane_system, transport_endpoint, transport_driving_force, transport_specificity, transport_response_model. The criterion questions and the unit rules (`_quantity_unit_supported`) are quoted in section 2 and 3. | Native quantities, units, criteria. Gaps are reported in `CLASS_transport_response.md`, section 4. |
| `G/literature_row_contract.py`, `literature_direction.py`, `literature_activity_direction.py`, `literature_page_update.py`, `literature_row.py`, `literature_claim.py`, `literature_relevance.py` | `CLAIM_PREDICATES_BY_CLASS` has `ligand_binding` and `activity_rate`; `domain.py` already lists `transports` as a hypothesis predicate; `stated_strength` and `NOT_POOLED_CLASSES` carry the activity class by name; `TERM_PARTNER_IS_NOT_A_MOLECULE = ('catalyzes',)`. | Sections 4 to 6. |
| Codex sessions | Not opened (rule of this task). | Nothing. |

**Conclusion:** as for binding and activity, no prior per-technique transport list exists. The prior work is organised by calculation
(rate, accumulated amount, kinetic parameter, current, conductance). The list below is new, drafted from the cases above and domain
knowledge. No real published paragraph has yet been found for any type (SOP step 6); the papers named under "past work" are candidates.

---

## 2. What all `transport_response` types share (the class core)

**Evidences:** sheet `transport_response` (predicate `transports`, section 5). What is measured: the movement of a substrate or an ion
across a membrane by the protein (the transporter, channel or pump): uptake or efflux in cells, vesicles or proteoliposomes,
counterflow, an accumulated amount, a transport rate or Km, or a current or conductance by electrophysiology. A transport result is
always read against a matched background (empty vector, protein-free liposomes, uninjected oocytes, no substrate, no gradient): the
background is part of the measurement, not an extra.

**Native quantities common to the quantitative types** (each a record operand, `point` or `unavailable` with a reason, never 0, never
omitted; the unit vocabulary of the record is a subset of the sheet's `_quantity_unit_supported` set and the converter converts exactly):

| Record quantity | Sheet kind | Units in the record | Anchor unit |
| --- | --- | --- | --- |
| `km` (Km or K0.5 of the substrate) and its spread | `transport_parameter` | nM, uM, mM, M | uM |
| `turnover` per transporter molecule or channel | `transport_rate` | s^-1, 1/s, min^-1, per_min | s^-1 |
| `normalized_rate` (rate per mass: nmol/min/mg of cell protein, dry weight or purified protein) with `rate_basis` (a choice: protein, dry_weight, purified_protein) | `transport_rate` | pmol/min/mg, nmol/min/mg, umol/min/mg | nmol/min/mg |
| `vmax` (maximal rate, same units as the rate) | `transport_rate` | as above | context, not an effect |
| `fold_over_control` and the control's own value | `transport_rate_ratio` or `substrate_response_ratio` | dimensionless (a stated "n-fold" is read as that) | dimensionless |
| `accumulated_amount` at a stated time (nmol/mg, uM, mM, pmol per sample) and the `accumulation_ratio` (inside over outside) | `accumulated_amount` | uM, mM, nM, pmol, nmol, umol | context, not an effect |
| `unitary_conductance` (single channel, already divided by V minus Vrev) | `electrical_conductance` | pS, nS, uS, S | pS |
| `current` with its holding voltage, `reversal_potential` | `electrical_current` | pA, nA, uA, A; mV | context, not an effect |
| `charge_rate` (current over e, per channel) | `charge_equivalent_rate` | elementary_charge_equivalents_per_s | same |
| `rate_spread` and `spread_kind` (SD, SEM, CI, fit SE, unstated plus-minus) | `effect_variance` | as the quantity, squared | |
| `time_window` of the rate (s, min), `substrate_concentration`, `temperature_c`, pH, `replicate_count` and `replicate_kind` | context | | |

An unstated plus-minus stays unstated (never read as SD); the old Fluc and BioY cases show the same ("error semantics unknown where the caption only says plus-minus").

**Facts common to every type** (`yes` / `no` / `unknown` / `not_applicable`): negative control done (empty vector, protein-free
liposome, uninjected oocyte, parent strain, mutant); background subtracted; no-substrate or no-gradient control done; initial-rate
regime shown (several time points in the linear part, or the paper says linear); saturation shown (a series of concentrations, or a Km
fit); specificity control done (competitor, substituted ion, inhibitor); expression or membrane insertion confirmed; membrane integrity
checked (vesicle leak, cell viability, seal resistance); purified protein (against cells or extract); substrate identity of the moving
label shown (the transported molecule recovered unchanged, not a metabolite); native substrate (against a surrogate or analogue);
transport detected above the control (the qualitative statement).

**Owner biochemical questions mapped to the core:** sensitivity -> rate over background and the stated detection floor; kinetic
parameters -> `km`, `vmax`, the concentration series; heating -> `temperature_c`; in vitro against in vivo -> the purified-protein
and the system facts; realism of the chemistry -> native-substrate fact, pH, ion and gradient conditions; expected signal in messy
samples -> the matrix and endogenous-transport background (other transporters, metabolism, trapping); spontaneous reaction -> here
passive diffusion and leak, the protein-free control.

**Certainty, quantitative types:** a measured effect, the Km, the turnover, the conductance, or the rate over the paper's own
control, read against its own spread. **Result stated in words:** "uptake was observed", "no transport was detected" (section 4).

**Sheet criteria the class fills** (the `CRITERIA_BY_TYPE['transport_response']` list, with the criterion question in short):

| Sheet criterion | Question in short | What the record supplies (typical) |
| --- | --- | --- |
| `measurement_identity` | Do subject, construct, preparation, endpoint, units and denominator identify the estimate? | target and partner stated, unit and normalizer stated |
| `calibration_applicability` | Do calibration and response range apply? | tracer specific activity, standard curve, dye or electrode calibration |
| `matrix_interference` | Matrix, detector and handling effects? | quenching, background counts, endogenous channels |
| `background_alternatives` | Controls for passive and competing contributions? | empty vector, protein-free liposome, uninjected oocyte |
| `attribution_supported` | Is the signal isolated to the studied protein? | expression level, mutant, complementation, the net fraction |
| `assertion_relevance` | Does the endpoint address the asserted transport? | native substrate, direction (in or out) |
| `condition_scope` | Substrate, pH, temperature, cofactors, in vitro or in vivo? | temperature, pH, buffer, system |
| `variance_correspondence` | Is the variance for this estimate? | spread and its kind of the chosen quantity |
| `sampling_basis` | Sampling units, repeats and independence? | replicate count and independence fact |
| `membrane_system` | Actual membrane, preparation, integrity and background controls? | cell, vesicle, oocyte, bilayer; integrity checks |
| `transport_endpoint` | Accumulation, initial flux, saturation response, current, conductance or charge, not converted silently? | time window, linear interval fact |
| `transport_driving_force` | Concentrations, voltage conventions, gradients and reversal? | gradient, holding voltage, reversal potential |
| `transport_specificity` | Substrate or ion controls and attribution; charge flow kept apart from identified-ion flow? | competitor, ion substitution, inhibitor, label identity |
| `transport_response_model` | Concentrations and apparent Km on one supported curve (required for Km and a saturation response)? | concentration series, fit, saturation reached |

**Readers that supply it (all types):** text paragraphs (Methods and Results) and tables. Uptake time courses, Michaelis-Menten
plots, current traces and I-V curves are figures and are **unavailable** today (SOP Known gaps).

---

## 3. The draft experiment list (10 types)

Type ids start with `transport_`, are snake_case and none is a reserved id. All ten are in class `transport_response`, predicate
`transports`.

| # | Type id | Experiment | Family |
| --- | --- | --- | --- |
| 1 | `transport_cell_tracer_uptake` | Whole-cell uptake or efflux of a labelled substrate, stopped and separated | Cells, isotope or tagged tracer, discontinuous |
| 2 | `transport_medium_analysis` | Unlabelled substrate measured in the medium or in the cells by chemical analysis | Cells, analytical, discontinuous |
| 3 | `transport_fluorescent_reporter` | Fluorescent substrate analogue, indicator dye or sensor in cells | Cells, optical, continuous |
| 4 | `transport_proteoliposome_tracer` | Purified protein in liposomes, labelled substrate uptake or efflux | Reconstituted, isotope, discontinuous |
| 5 | `transport_vesicle_probe_flux` | Vesicle flux read continuously by an ion electrode or an entrapped dye | Reconstituted or native vesicles, continuous |
| 6 | `transport_counterflow` | Counterflow and exchange: trans-stimulation of a labelled substrate | Cells or vesicles, discontinuous |
| 7 | `transport_patch_clamp` | Patch clamp of cells (whole-cell, inside-out, outside-out) | Electrophysiology, continuous |
| 8 | `transport_oocyte_two_electrode` | Two-electrode voltage clamp in Xenopus oocytes | Electrophysiology, continuous |
| 9 | `transport_planar_bilayer` | Single-channel or macroscopic current in a planar lipid bilayer | Electrophysiology, reconstituted |
| 10 | `transport_ssm_electrophysiology` | Solid-supported membrane electrophysiology (transient currents of proteoliposomes) | Electrophysiology, reconstituted |

**Considered and not listed as types** (with the reason):

- *Growth complementation, deletion and restoration of uptake-dependent growth, survival, resuscitation*: perturbation of a cell, A106
  (the old review also kept it there). A transport measurement made in such a strain is type 1, 2 or 3.
- *Transcript or protein level of a transporter, localization, accessibility labelling of a flippase (MurJ with a reporter)*:
  `protein_signal`, `protein_amount` or A106; the MurJ lipid-II flipping case reads lipid II by a ColM-cleavage reporter and is a boundary note, not a
  transport rate in the sense of the class (`06_murj_2014_accessibility_components.md`). Whether a flippase assay belongs here is an open question.
- *Substrate binding to the transporter (ITC, thermal shift, SPR of a substrate), the PxPT/PxPR binding boundary*: `ligand_binding`.
- *ATPase or other enzyme activity of a pump or transporter (substrate-stimulated ATP hydrolysis)*: `activity_rate`, not movement.
- *Inhibition (IC50, Ki) of transport*: a different claim ("inhibits"); not in this class's quantity kinds.
- *Isothermal or thermal readouts of transport, structure-based inferences (cryo-EM with substrate), molecular dynamics*: not experiments of this class.
- *Radiotracer uptake in oocytes or in cultured mammalian cells*: protocol 1 with another preparation (a fact on the record).
- *Calcium imaging of channel activation, thallium flux (FluxOR) and similar plate assays*: protocol 3 (cell fluorescence).
- *86Rb+ or 22Na+ efflux and influx in cells*: protocol 1 (an ion tracer).

Mapping used in every entry below: native quantities as in section 2; criteria are written as "grader criterion -> sheet criterion";
unit conversions to the anchor unit are exact (`FIXED_BY_DEFINITION`) and the grader holds no threshold (SOP step 2).

### 3.1 `transport_cell_tracer_uptake`

```text
experiment:            whole-cell tracer uptake or efflux                 (type id transport_cell_tracer_uptake)
family:                cells, isotope or tagged tracer (14C, 3H, 32P, 35S, 86Rb+, 22Na+, 45Ca2+), stopped by rapid filtration and wash,
                       by centrifugation through oil, or by dilution in ice-cold stop buffer; counted by scintillation
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  retained label (cpm, dpm) converted with the stated specific activity to amount (pmol, nmol) per mg protein, per mg
                       dry weight or per 10^9 CFU; initial velocity over a linear interval (pmol/min/mg); accumulation at a time; Km and Vmax
                       from a concentration series (uM, nmol/min/mg); fold over the empty-vector or parent strain
controls required:     empty vector or deleted parent strain beside the test; zero-time (stopped at once) or cold control for surface binding;
                       blank filter without cells; specific activity stated; label identity (substrate or its metabolite) at least stated;
                       energy-state control (inhibitor or uncoupler, cold) when the transport is energy dependent
noise expectations:    the stated spread and its kind; background counts beside the test counts; the linear interval named (30 s to 2 min is
                       usual); the cell quantity (OD, protein, CFU) stated; counting efficiency stated or not
replicates needed:     count plus kind (technical filters, independent cultures); no cut-off here, the converter decides (SOP step 3)
certainty:             quantitative: a rate or Km over its own background; qualitative: "uptake above the empty vector" or "no uptake"
readers that supply it:text, tables; time courses figures-only (unavailable)
past work (where):     BioY biotin (`01_bioy_2007.md`, PMC1815280); FucP fucose (`04_fucp_2011_pnas.md`, PMC3084102: 40 mCi/mmol = 88.8 dpm/pmol,
                       0.22 um filter, LiCl wash, initial velocity from 120 s); BtsT pyruvate whole cells (`02_btst_2018_components.md`,
                       PMC5738728: 6x empty vector in the first 30 s, Km 16.5 +/- 6.4 uM); VBNC pyruvate (`04_vbnc_pyruvate_2019_components.md`,
                       PMC6349089); old sheet 7 `transport_response_cells_schema`
```

Record and criteria (a builder's draft; grader criterion -> sheet criterion):

- Record quantities: `km`, `vmax`, `turnover` (when the transporter count is stated), `normalized_rate` with `rate_basis`, `fold_over_control` with
  `control_value`, `accumulated_amount` with `time_window`, `substrate_concentration`, `specific_activity` (context), `replicate_count`, spread and `spread_kind`.
- Yes/no facts: `empty_vector_control_done`, `zero_time_control_done`, `linear_interval_shown`, `saturation_shown`, `competitor_control_done`, `energy_control_done`,
  `label_identity_shown`, `expression_confirmed`, `viability_checked`, `independent_replicates`, `native_substrate`, `uptake_detected_above_control`.
- Criteria: empty vector and zero-time -> `background_alternatives`, `membrane_system`; linear interval and time window -> `transport_endpoint`; concentration
  series and Km fit -> `transport_response_model`; competitor, energy control and label identity -> `transport_specificity`; temperature, pH, buffer, ion
  composition -> `transport_driving_force`, `condition_scope`; expression confirmed -> `attribution_supported`; specific activity and counting -> `calibration_applicability`;
  replicates -> `sampling_basis`; spread of the chosen quantity -> `variance_correspondence`.
- Preparations: the cell culture -> `analyte_preparation_ref`; others None (section 6).
- Weak points the paper often leaves open (so the sheet gives unknown): metabolism or trapping of the label, surface binding, residual host uptake, the active transporter amount.

### 3.2 `transport_medium_analysis`

```text
experiment:            medium or cell-content analysis of an unlabelled substrate   (type id transport_medium_analysis)
family:                cells, analytical, discontinuous (substrate disappearance or product appearance in the supernatant, or content of
                       cells separated through silicone oil; HPLC with derivatization, LC-MS, enzymatic analyzer, ICP-MS or ion chromatography for ions)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  concentration in the medium at times (uM), amount moved over an interval (umol), rate over the interval or from a slope
                       (nmol/min/mg dry weight, uM/min), intracellular concentration (mM) by volume conversion; fold over the control strain
controls required:     cell-free medium control (chemical loss, adsorption); parent or empty-vector strain; zero-time sample; stop and separation
                       time stated (a delayed centrifugation is an unknown extra interval); calibration standards in the same medium; internal standard
                       for MS; cell mass or number stated
noise expectations:    spread and kind; the number of time points that define the slope (two time points give an interval average, not an
                       initial rate); analyzer calibration range against the concentrations measured; metabolism and consumption of the substrate in the cells
replicates needed:     count plus kind
certainty:             quantitative, but an INTERVAL or appearance measure: it balances export, re-uptake, lysis and metabolism (the YjeH note);
                       a ten-minute disappearance is not an initial rate (the CstA/YbdD note)
readers that supply it:text, tables
past work (where):     YjeH methionine export (`03_yjeh_2015.md`: 105.6, 127.6 and 173.0 nmol/min/mg dry weight, SD); CstA/YbdD pyruvate 10 min (`03_csta_ybdd_2018_endpoint.md`,
                       PMC5847655); old sheet 7
```

- Record quantities: `normalized_rate` (dry weight, protein), `concentration_series` (medium concentrations at the time points), `accumulated_amount`, `fold_over_control`,
  `interval` (s or min), `cell_mass`, spread and kind, `replicate_count`.
- Facts: `cell_free_control_done`, `empty_vector_control_done`, `multiple_time_points`, `stop_time_stated`, `calibration_in_medium`, `internal_standard_used`,
  `export_and_reuptake_separated` (no: stated), `independent_replicates`, `transport_detected_above_control`.
- Criteria: cell-free and empty vector -> `background_alternatives`; interval and number of time points -> `transport_endpoint`; calibration in the same medium, internal standard
  -> `calibration_applicability`, `matrix_interference`; strain contrast and expression -> `attribution_supported`; export against reuptake and consumption -> `transport_specificity`.

### 3.3 `transport_fluorescent_reporter`

```text
experiment:            fluorescent substrate, indicator dye or sensor in cells     (type id transport_fluorescent_reporter)
family:                cells, optical, continuous or plate (fluorescent substrate analogues such as 2-NBDG or ethidium efflux; ion indicators
                       Ca2+, Tl+ (FluxOR), pH dyes; genetically encoded sensors for fluoride, glucose, ATP; flow cytometry of dye content)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  fluorescence signal (RFU, arbitrary) and its slope (RFU/min); fold over the control cells or over the baseline before the substrate;
                       concentration only when a calibration curve is stated (uM); half-time of the change (s)
controls required:     untransfected or empty-vector cells; cells without substrate or dye; analogue shown to be a substrate (the analogue is not the
                       natural substrate); dye leakage, bleaching and autofluorescence controls; calibration of the indicator in the same buffer (high and low standards)
noise expectations:    spread; background fluorescence beside the test; signal range of the detector; sensor dynamic range against the change measured
replicates needed:     count plus kind (wells, coverslips, independent cultures)
certainty:             quantitative only after calibration; otherwise a relative signal (a fold over its own control); the analogue differs from the native
                       substrate, so assertion relevance is lowered (the weight, not the direction)
readers that supply it:text, tables; trace figures unavailable
past work (where):     none found in the places searched (the Fluc case used electrodes, not dyes); the old sheet 7 lists no dye case
```

- Record quantities: `fold_over_control`, `signal_slope` (arbitrary, context), `half_time`, `km` (when a series is stated), `calibration_slope` (RFU per uM, context), spread and kind, `replicate_count`.
- Facts: `untransfected_control_done`, `no_substrate_control_done`, `analogue_is_native_substrate`, `indicator_calibrated`, `bleaching_leak_control_done`, `competitor_control_done`, `independent_replicates`,
  `transport_detected_above_control`.
- Criteria: untransfected and no-substrate -> `background_alternatives`; calibrated indicator -> `calibration_applicability`; dye and autofluorescence interference -> `matrix_interference`; analogue against native
  -> `assertion_relevance`, `transport_specificity`; indicator specificity (Tl+ for K+, a pH dye for protons) -> `transport_specificity`.

### 3.4 `transport_proteoliposome_tracer`

```text
experiment:            proteoliposome tracer transport                    (type id transport_proteoliposome_tracer)
family:                reconstituted, isotope, discontinuous (purified protein reconstituted in liposomes; imposed delta-pH, delta-psi (valinomycin), or
                       Na+ or other ion gradient; labelled substrate uptake or efflux; stopped on a filter, a cation-exchange column or by dilution)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  retained label per time (pmol, nmol) per mg protein in the proteoliposomes; initial rate (nmol/min/mg of reconstituted protein);
                       turnover per transporter (s^-1) when the active amount is stated; fold over empty (protein-free) liposomes; Km (uM) from a series;
                       lipid to protein ratio (w/w), vesicle size (nm)
controls required:     protein-free (empty) liposomes through the same protocol; no-gradient control (the driving force is the intended variable);
                       uncoupler or ionophore control of the imposed gradient; heat-inactivated or mutant protein; protein quantified as reconstituted
                       (not input); vesicle integrity or leak
noise expectations:    spread and kind; empty-liposome counts beside the test; the linear interval; orientation and active fraction of the reconstituted
                       protein stated or not (they decide whether a per-molecule turnover is meaningful)
replicates needed:     count plus kind (technical, independent reconstitutions, independent protein preparations)
certainty:             quantitative, the cleanest system for "this protein, this substrate": only the protein, the lipid and the gradient define the flux
readers that supply it:text, tables
past work (where):     BtsT proteoliposomes (`02_btst_2018_components.md`: 40 uM 14C pyruvate, 25 C, delta-pH or delta-psi, empty liposomes, PMC5738728); FucP/BioY
                       whole-cell cases are type 1; old sheet 7
```

- Record quantities: `normalized_rate` (`rate_basis` purified protein), `turnover`, `km`, `vmax`, `fold_over_control`, `accumulated_amount`, `reconstituted_protein_amount`, `lipid_protein_ratio`, spread and kind.
- Facts: `empty_liposome_control_done`, `no_gradient_control_done`, `gradient_verified`, `protein_quantified_after_reconstitution`, `leak_checked`, `inactive_protein_control_done`, `competitor_control_done`,
  `substrate_identity_shown`, `independent_replicates`, `purified_protein`, `transport_detected_above_control`.
- Criteria: empty liposome -> `background_alternatives`, `membrane_system`; the gradient and its verification -> `transport_driving_force`; competitor and ion substitution -> `transport_specificity`;
  protein amount -> `attribution_supported`, `calibration_applicability`; linear interval -> `transport_endpoint`; series and fit -> `transport_response_model`.

### 3.5 `transport_vesicle_probe_flux`

```text
experiment:            continuous vesicle flux by electrode or entrapped probe   (type id transport_vesicle_probe_flux)
family:                reconstituted or native vesicles, continuous (ion-selective electrode in the bath, as for Fluc F- and Cl-; entrapped fluorescent
                       probes: pyranine or fluorescein for pH, ACMA quench for protons, Cl- or K+ sensitive dyes; valinomycin and CCCP as counter-ion and
                       proton carriers; the pool left in the vesicles released by detergent at the end)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  fraction of the trapped pool released over time (dimensionless, per cent), a rate constant (s^-1) or a half-time (s), the initial
                       efflux rate (umol/s or mM/s in the bath), a rate per mg protein (nmol/min/mg), a lower bound when the release is faster than the
                       apparatus dead time (a bound, not a rate); fold over protein-free vesicles; per-channel ion rate when the number of channels is derived
controls required:     protein-free vesicles; a second ion or substrate (chloride against fluoride in the Fluc case); detergent release as the 100 percent
                       reference; ionophore control of the gradient; electrode calibration; protein-free vesicles for the Poisson fraction of empty vesicles
noise expectations:    spread; the electrode response time against the flux (dead time about 1 s for Fluc; a faster flux is only bounded); Poisson dilution of the protein
                       (30 to 50 percent empty vesicles are expected and are not leak)
replicates needed:     count plus kind
certainty:             quantitative (a rate constant or a fraction over time) or a bound; strong for ion selectivity because two ions can be compared in one vesicle
readers that supply it:text, tables
past work (where):     Fluc (`02_fluc_2013.md`, eLife 01084 xml in `a105_transport_channel_case_174`: more than 30,000 ions/s per functional unit estimated from a release
                       faster than 1 s; F- against Cl-); old sheet 7
```

- Record quantities: `release_fraction` (dimensionless), `rate_constant` (s^-1), `half_time` (s), `normalized_rate`, `turnover` (stated by the paper), `fold_over_control`, `detection_bound` (a bounded operand), spread and kind.
- Facts: `protein_free_vesicle_control_done`, `second_ion_control_done`, `detergent_reference_done`, `electrode_calibrated`, `ionophore_control_done`, `released_faster_than_dead_time`, `independent_replicates`,
  `transport_detected_above_control`.
- Criteria: protein-free vesicles -> `background_alternatives`, `membrane_system`; second ion or counter-ion control -> `transport_specificity`; time resolution and dead time -> `transport_endpoint`;
  gradient and counter-ion -> `transport_driving_force`; electrode calibration -> `calibration_applicability`.

### 3.6 `transport_counterflow`

```text
experiment:            counterflow, exchange and trans-stimulation            (type id transport_counterflow)
family:                cells or vesicles, discontinuous (vesicles or cells preloaded with unlabelled substrate; labelled substrate added outside; uptake of label
                       above its equilibrium (overshoot) shows exchange; equilibrium exchange at equal inside and outside concentrations; a second unlabelled
                       molecule tested as the inside substrate)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  retained label per time (pmol/mg) with and without the preload; the overshoot ratio (peak over equilibrium, dimensionless); the
                       exchange rate (nmol/min/mg) or the fold of preloaded over non-preloaded uptake (dimensionless); Km of the external substrate
controls required:     same vesicles or cells without the preload (the baseline of the trans-effect); protein-free or empty-vector control; preload of a non-substrate
                       (a negative internal molecule); verified preload (the inside concentration)
noise expectations:    spread; the time of the peak; label equilibrium reached or not; internal pool dilution
replicates needed:     count plus kind
certainty:             quantitative (a fold of trans-stimulated uptake over its own baseline); the result is evidence of recognition of the preloaded molecule as a
                       substrate, so the partner of the claim is the preloaded or the labelled molecule and the record must say which
readers that supply it:text, tables
past work (where):     none found as a separate case in the places searched (counterflow appears inside the old transport papers' controls)
```

- Record quantities: `fold_over_control` (preloaded over non-preloaded), `overshoot_ratio` (kind `substrate_response_ratio`), `normalized_rate`, `km`, `accumulated_amount`, `time_of_peak`, spread and kind.
- Facts: `non_preloaded_baseline_done`, `empty_control_done`, `non_substrate_preload_control_done`, `preload_verified`, `equilibrium_reached`, `labelled_molecule_named`, `preloaded_molecule_named`, `independent_replicates`,
  `transport_detected_above_control`.
- Criteria: baseline and empty control -> `background_alternatives`; non-substrate preload -> `transport_specificity`; preload and gradient -> `transport_driving_force`; peak and equilibrium -> `transport_endpoint`.

### 3.7 `transport_patch_clamp`

```text
experiment:            patch-clamp recording of cells                       (type id transport_patch_clamp)
family:                electrophysiology, continuous (whole-cell, inside-out, outside-out and cell-attached patches of HEK, CHO or native cells; voltage steps and
                       ramps; substrate-induced or voltage-gated currents; reversal potential under a salt gradient; single-channel events in a patch)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  current (pA, nA) at a holding voltage (mV); current density (pA/pF); reversal potential (mV) and the permeability ratio from it; unitary
                       conductance (pS) from single-channel events or an I-V slope; open probability; fold of substrate-evoked over baseline or over untransfected cells
controls required:     untransfected or empty-vector cells recorded the same way; the current with and without the substrate (or the blocker); ion substitution
                       (the reversal potential shifts with the ion); series resistance and leak subtraction stated; seal resistance
noise expectations:    spread across cells (cells are the sampling unit, not sweeps); the recording noise against the unitary amplitude; the endogenous current of the host cell
replicates needed:     number of cells plus number of independent transfections or preparations (separately)
certainty:             quantitative; identification of the ion needs ion substitution or a reversal potential, charge flow is not ion flow
readers that supply it:text, tables; traces and I-V curves are figures (unavailable)
past work (where):     old sheet 33 `channel_cells_schema` (`read_channel_inputs`); Fluc planar-bilayer values are type 9
```

- Record quantities: `current`, `holding_voltage`, `reversal_potential`, `unitary_conductance`, `charge_rate`, `fold_over_control`, `current_density` (context), `cell_count`, spread and kind.
- Facts: `untransfected_control_done`, `substrate_free_control_done`, `ion_substitution_done`, `blocker_control_done`, `series_resistance_compensated`, `leak_subtracted`, `single_channel_resolved`,
  `independent_cells`, `transport_detected_above_control`.
- Criteria: untransfected cell -> `background_alternatives`, `membrane_system`; ion substitution, reversal potential and blocker -> `transport_specificity`; holding voltage, bath and pipette solutions -> `transport_driving_force`;
  conductance already corrected for driving force -> `transport_endpoint`; seal and series resistance -> `calibration_applicability`.

### 3.8 `transport_oocyte_two_electrode`

```text
experiment:            two-electrode voltage clamp in Xenopus oocytes       (type id transport_oocyte_two_electrode)
family:                electrophysiology, continuous (cRNA injected oocytes, current at a clamped potential on perfusion of the substrate; I-V curves;
                       reversal shifts under ion substitution)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  substrate-induced current (nA, uA) at a holding voltage (mV); fold over water-injected or uninjected oocytes; apparent Km from a
                       series of substrate concentrations (uM, mM); reversal potential (mV); charge per substrate from simultaneous radiotracer uptake (a ratio)
controls required:     water-injected or uninjected oocytes from the same batch; the same oocyte before and after the substrate; endogenous oocyte currents; a
                       non-substrate analogue; ion substitution
noise expectations:    spread across oocytes (oocyte batches are the independent unit); leak current; the endogenous conductance
replicates needed:     oocytes per batch and batches (separately)
certainty:             quantitative; the current is evidence of charge movement coupled to the substrate, which an electroneutral transporter does not give (an absent current is
                       not absence of transport)
readers that supply it:text, tables
past work (where):     none found in the places searched; the structure follows old sheet 33
```

- Record quantities: `current`, `holding_voltage`, `reversal_potential`, `km`, `fold_over_control`, `charge_rate` (rare), `oocyte_count`, `batch_count`, spread and kind.
- Facts: `uninjected_control_done`, `same_oocyte_baseline_done`, `analogue_control_done`, `ion_substitution_done`, `leak_subtracted`, `independent_batches`, `transport_detected_above_control`.
- Criteria: water-injected -> `background_alternatives`, `membrane_system`; analogue and ion substitution -> `transport_specificity`; holding voltage and concentrations -> `transport_driving_force`; series and Km fit -> `transport_response_model`.

### 3.9 `transport_planar_bilayer`

```text
experiment:            planar lipid bilayer recording                        (type id transport_planar_bilayer)
family:                electrophysiology, reconstituted (purified protein or proteoliposomes fused into a painted or folded bilayer; single-channel
                       insertion events; macroscopic current; salt gradient reversal potentials)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  unitary current (pA) at a holding voltage (mV); unitary conductance (pS) = |I| / |V - Vrev|; reversal potential (mV) and
                       permeability ratio between two ions (dimensionless); number of insertion events and of bilayers; open probability; ions per second (charge/e)
controls required:     bilayer without protein (no events); protein-free proteoliposomes; two ions in a bi-ionic gradient; the driving force subtracted (the Fluc
                       case: dividing by 0.200 V instead of 0.253 V gives a misleading 9 pS); blocker; bilayer stability
noise expectations:    spread across bilayers (a bilayer is the independent unit, events within one trace are not); the recording noise against the unitary amplitude
replicates needed:     bilayers and independent protein preparations (separately)
certainty:             quantitative per molecule; the cleanest identification of the ion by the reversal potential
readers that supply it:text, tables
past work (where):     Fluc (`02_fluc_2013.md`: 1.8 pA at -200 mV, reversal about +53 mV, 7.1 pS, 1.12e7 ions/s; bi-ionic 119 +/- 3 mV, P_F/P_Cl above about 100);
                       old sheet 33
```

- Record quantities: `unitary_current`, `holding_voltage`, `reversal_potential`, `unitary_conductance`, `charge_rate`, `permeability_ratio` (kind `substrate_response_ratio`), `event_count`, `bilayer_count`, spread and kind.
- Facts: `protein_free_bilayer_control_done`, `bi_ionic_gradient_done`, `driving_force_corrected`, `blocker_control_done`, `independent_bilayers`, `purified_protein`, `transport_detected_above_control`.
- Criteria: protein-free bilayer -> `background_alternatives`, `membrane_system`; reversal potential and bi-ionic ratio -> `transport_specificity`; driving-force correction -> `transport_driving_force`, `transport_endpoint`;
  bilayers against events -> `sampling_basis`.

### 3.10 `transport_ssm_electrophysiology`

```text
experiment:            solid-supported membrane electrophysiology            (type id transport_ssm_electrophysiology)
family:                electrophysiology, reconstituted (proteoliposomes or membrane fragments adsorbed on a gold sensor under a lipid layer; a substrate
                       concentration jump gives a transient current that reports charge translocation of electrogenic carriers and pumps)
evidences (sheet):     transport_response                                (predicate: transports)
native outputs/units:  peak current (nA) of the transient after a concentration jump; charge translocated (nC, by integration); Km (uM, mM) from the peak current against
                       the concentration; fold over the empty-vesicle sensor or over the non-substrate jump; decay time constant (ms)
controls required:     empty liposomes on the same type of sensor; a jump with a non-substrate or with buffer only; sensor capacitance and conductance stated; a blocker or inhibitor
                       when known; reproducibility between sensors (sensors are the sampling unit)
noise expectations:    spread across sensors; the baseline noise and the buffer-jump artefact; the dependence on the amount of protein adsorbed
replicates needed:     sensors plus independent preparations (separately)
certainty:             quantitative and relative: the amplitude depends on the amount of protein on the sensor, so the Km and the fold are the usable effects; a transient current
                       shows electrogenic translocation, not the net transport of every substrate
readers that supply it:text, tables
past work (where):     none found in the places searched
ROLE mapping note:     proteoliposome batch -> immobilized_preparation_ref; the gold sensor -> surface_ref (section 6)
```

- Record quantities: `peak_current`, `charge`, `km`, `fold_over_control`, `decay_time`, `sensor_count`, spread and kind.
- Facts: `empty_liposome_sensor_done`, `non_substrate_jump_done`, `buffer_jump_artefact_subtracted`, `sensor_capacitance_stated`, `blocker_control_done`, `independent_sensors`, `transport_detected_above_control`.
- Criteria: empty liposome sensor and buffer jump -> `background_alternatives`, `membrane_system`; non-substrate jump and blocker -> `transport_specificity`; jump concentrations and ion composition -> `transport_driving_force`; series and Km -> `transport_response_model`.

---

## 4. Direction and strength for the class (class-scoped; code in `G/literature_transport_response_direction.py`, constants in `CLASS_transport_response.md`)

**All numbers below are EXPERT_REVIEW, owner to confirm. Literature figures are "from memory, not verified".** The paradigm is the activity
and binding paradigm, with the same output shape:

```text
p = clip( (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), 0, 1 )      (noise_end > strong_end for Km: smaller is stronger)
s = (3 p^2 - 2 p^3) / (1 + r^2),    r = sd / e    (0 when no spread is stated)
log_ratio = QUALITATIVE_LOG_RATIO[type] * s
```

A stated measured effect SUPPORTS by its graded strength `s`; `s == 0` (at or beyond the noise end) is neutral; a quantitative result never opposes. Controls, the
initial-rate regime, the gradient and the other sheet criteria lower the WEIGHT only, never the direction. A paper stating that the protein shows
no transport above its own control or detection limit is the qualitative path ("transport not detected", opposes).

### 4.1 The stated quantities, anchors and direction

The anchors are per quantity, not per type (the physics of a Km or a conductance is the same in every assay). Larger is stronger except for the Km.

| Quantity (record kind) | Anchor unit | noise_end | strong_end | Larger or smaller | Reason, one line (all EXPERT_REVIEW, owner to confirm) |
| --- | --- | --- | --- | --- | --- |
| Km or K0.5 (`transport_parameter`) | uM | 1e4 (10 mM) | 1 | smaller is stronger | At 10 mM saturation is hardly reachable and a Km this large is not told from non-mediated uptake; 1 uM is a high-affinity carrier (BioY about 0.25 uM, BtsT 16.5 uM; from memory, not verified). |
| turnover per molecule (`transport_rate`, unit s^-1) | s^-1 | 1e-2 | 1e2 | larger | The same ends as the activity turnover: one turnover per two minutes is the slow end of carriers and pumps; typical carriers are 1 to 100 s^-1 (from memory, not verified); a channel is above and caps at 1. |
| unitary conductance (`electrical_conductance`) | pS | 1 | 1e2 | larger | 1 pS is about 0.1 pA at 100 mV, the least a single-channel record resolves above its noise; most ion channels are 10 to 100 pS, Fluc about 7 pS (from memory, not verified). |
| charge rate per channel (`charge_equivalent_rate`) | charges/s | 6e5 | 6e7 | larger | The conductance ends read at 100 mV (1 pS = 6.2e5, 100 pS = 6.2e7 charges/s), rounded, so the two channel scales agree. |
| rate over the paper's own control (`transport_rate_ratio`, `substrate_response_ratio`) | dimensionless | 1 | 30 | larger | No better than the control is the noise end; at 30-fold the control holds about 3 percent of the signal and no longer limits it (empty-vector backgrounds are 3 to 30 percent of a good uptake signal; from memory, not verified). A ratio at or under 1 is neutral, never opposition. |
| rate per mass (`transport_rate`, unit nmol/min/mg) | nmol/min/mg | 1e-3 (1 pmol/min/mg) | 1e1 | larger | 1 pmol/min/mg is about 90 counts per minute at 40 mCi/mmol (88.8 dpm per pmol, the FucP figure), the floor of a filter assay over its blank; 10 nmol/min/mg is a well expressed carrier in whole cells (from memory, not verified). Weak: depends on expression, substrate level and the normalizer. |

Worked values with these ends (no spread): BtsT Km 16.5 uM gives p 0.70, s 0.78 (with the stated relative spread 0.39, s 0.68); BioY Km 0.25 uM gives s 1; a 6-fold uptake over the empty vector gives s 0.54;
a turnover of 10 s^-1 gives s 0.84; Fluc 7.1 pS gives s 0.39; BioY 60 pmol/min/mg gives s 0.42. The curve is smooth between the ends: never a pass or fail step, and never one generic formula for all the quantities.

### 4.2 Which quantity is the effect when a record states several

Order (`TRANSPORT_EFFECT_ORDER`): Km, turnover, unitary conductance, charge rate, fold over control, rate per mass. Why: the Km is intensive (it needs neither the transporter amount nor a
normalizer) and a fitted saturable curve already shows signal over background; turnover and unitary conductance are per molecule but need the active amount or a single-channel record; the charge rate is
the conductance without the driving force removed, so it follows the conductance; a fold over the paper's own control shows that the protein transports at all but depends on that control's own
background; a rate per mg depends on expression, the substrate concentration and the normalizer, so it is last. An accumulated amount, a stated current and a log ratio are not effects here (reasons in the registration note).

### 4.3 What a result stated in words alone means here

The existing vocabulary is kept and READ for this class: `interaction_detected` reads "transport detected" (movement of the claimed substrate or ion above the paper's own
control), `interaction_not_detected` reads "transport not detected" (none above the control or the detection limit; the missing value is never 0), `interaction_not_stated` reads
"transport not stated". `literature_direction` handles the three; with no effect a transport result counts `QUALITATIVE_LOG_RATIO[type] * STATED_ONLY_STRENGTH` (0.25), so one edit of
`stated_strength` is needed (registration note 1c). Example: "pyruvate uptake was only observed in cells producing BtsT" -> "transport detected". A bare statement that the protein "is a pyruvate
transporter" without a measurement is not a result of this class.

### 4.4 Proposed per-type maximum (`QUALITATIVE_LOG_RATIO`), added by each builder

Rule: a weaker assay carries less evidence. Proposals (EXPERT_REVIEW): `transport_proteoliposome_tracer` 1.5 (only protein, lipid and gradient define the flux); `transport_planar_bilayer` 1.4 (single
molecules, ion identified by the reversal potential); `transport_ssm_electrophysiology` 1.3 (defined system, amplitude relative); `transport_counterflow` 1.2 and `transport_vesicle_probe_flux` 1.2 (defined or
native vesicles; counterflow infers a substrate from trans-stimulation); `transport_patch_clamp` and `transport_oocyte_two_electrode` 1.2 (a cell with endogenous channels and a host background);
`transport_cell_tracer_uptake` 1.0 (other transporters, metabolism, trapping and surface binding contribute); `transport_medium_analysis` 0.9 and `transport_fluorescent_reporter` 0.9 (an interval balance of
export, uptake and metabolism; an analogue and a dye are not the substrate).

### 4.5 Pooling

**Not pooled** (as for `activity_rate`): the effect of a result is one of six quantities in different units, chosen per experiment, so no two results need share a unit and no mean of them has one. The
row's pooled effect, variance and precision are null for the class; the direction, strength and weight are unaffected. Edit: `NOT_POOLED_CLASSES` in `G/literature_row.py` (registration note 2).

---

## 5. Claim predicate (proposal, owner to confirm)

- **Predicate:** `transports`. Spelling already used by `domain.py` `PREDICATES` and the SOP's proposal. Added to `CLAIM_PREDICATES_BY_CLASS['transport_response']` (the entry is in the registration note).
- **Not symmetric.** "P transports S" is not "S transports P". It is not added to `SYMMETRIC_PREDICATES`, so a record whose target is the substrate and whose partner is the protein is not the claim (the
  `partner_route` rule applies only to symmetric predicates).
- **Subject:** the transporter, channel or pump (the record's `target_id`, the assayed protein as written). **Partner:** the transported molecule or ion (the record's `partner_id`, with `partner_role`
  the transported substrate). A claim names molecules only (predicate, subject, partner); it carries no threshold, no direction of flow and no stoichiometry.
- **How the record's stated partner must agree:** the claim names a partner (the substrate or the ion) -> the record's stated partner must be the same name after normalization (`normalize_identity_ref`), else
  the result is `irrelevant` (reason `other_partner`) and stays off the row. A record naming no partner but measuring transport (an effect or a statement) is `unresolved` (`partner_not_stated`) and may enter the
  row. A claim without a partner (a claim about the protein alone) does not compare the partner.
- **The hypothesis value:** a `transports` hypothesis carries a reference or a term for the transported molecule (a chemical, not a reaction). Therefore `transports` must NOT be added to
  `TERM_PARTNER_IS_NOT_A_MOLECULE` in `literature_claim.py`: the label of the value is the claim's partner. The page's `hypothesis_claim` needs no term types here.
- **Risk to report:** an ion or a substrate has several spellings (fluoride, F-, F−; D-glucose, glucose); the claim name comes from a looked-up list and the leaf states the name "as written", so equality can fail
  and a true result becomes `irrelevant`. Open question 4 in section 7.
- **Direction of flow** (import or export), and coupling (symport, antiport, uniport) are not part of the claim and not graded; the record keeps them as a vocabulary fact only if the owner wants
  `assertion_relevance` to use them.

---

## 6. The class decisions of SOP step 0c, as read from the code (DRAFT, owner to confirm)

| Item | Finding | Draft decision |
| --- | --- | --- |
| `QUANTITY_KINDS['transport_response']`, `CRITERIA_BY_TYPE` | 11 kinds and `COMMON_CRITERIA` plus 5 transport criteria; `_required_criteria` makes `transport_response_model` required only for `transport_parameter`, `substrate_saturation`, `substrate_response_ratio` and `log_substrate_response`. | Used as they are. Each converter fills the sheet criteria listed in section 3. Gaps in the unit sets are in the registration note, section 4. |
| `QUALITATIVE_STATEMENT` | Binding wording. | No new values; read as "transport detected / not detected / not stated" (section 4.3). Comment added beside the vocabulary. |
| `ROLE`, `IMMOBILIZATION_SIDES`, `ROW_DEPENDENCE_KEYS` | Binding-flavoured (`analyte`, `immobilized`, `surface`). | `analyte_preparation_ref` = the preparation that carries the protein: the cell culture or transfection (types 1, 2, 3, 7), the oocyte batch (type 8), the purified protein preparation (types 4, 5, 6 when reconstituted, 9). `immobilized_preparation_ref` = the reconstituted vesicle batch (types 4, 5, 6, 9 when proteoliposomes are fused, and type 10), None for whole cells and oocytes. `surface_ref` = the electrode surface that holds the membrane: the gold sensor of type 10, None for every other type (a patch pipette or a bilayer cup is not a sample preparation shared between results). `dataset_ref` as always. Each converter documents its mapping. A cell and an oocyte batch are samples the same way a purified protein stock is: results from the same culture, batch or protein stock are dependent through `analyte_preparation_ref`. |
| Direction | `literature_direction` is nM-binding only. | A separate class-scoped function `transport_direction_and_ratio` (section 4), same paradigm as activity. |
| Hypothesis value type | A `transports` hypothesis names a molecule. | `claim_of_hypothesis` accepts it (`term_ref` or `reference`) and keeps it as the partner. |
| Stated-only strength | `stated_strength` names `activity_rate` only. | One edit in the contract so the transport class is included. |
| Pooling | `POOLED_UNIT_BY_CLASS` knows binding only. | `NOT_POOLED_CLASSES` includes `transport_response`. |
| One value, one method | A paper often states one number for several preparations (whole cells and proteoliposomes) or a Km from one and a rate from another. | A leaf records a transport value under a type only when the passage ties it to that protocol; otherwise no type can be named (SOP: a leaf that cannot name its type has no experiment). |
| Endpoint against rate | The old review keeps accumulation, interval average and initial rate apart (BioY: a 3.5 h accumulation is not an initial rate; CstA/YbdD: a ten-minute disappearance). | The record keeps `time_window` and the linear-interval fact; the `transport_endpoint` criterion reads them. An accumulated amount is not an effect. |

---

## 7. What is still open (questions for the owner, in plain words)

1. Is the list of ten protocols right? In particular: should whole-cell tracer uptake (1) and whole-cell analysis of the medium (2) stay apart, and should counterflow (6) be its own type or a design run
   with 1 or 4? Should patch clamp (7) and oocyte voltage clamp (8) be one type?
2. Should a flippase or a lipid transporter read by a reporter (the MurJ lipid-II case) be in this class, or left out until a real paper needs it?
3. Does a Km that is small count as stronger evidence that a protein transports a substrate? (The draft says yes: a small Km shows a specific, saturable carrier. A large Km is less specific.) And is a rate per mg
   too weak and too dependent on the amount of protein to count at all, or should whole-cell rates and purified-protein rates have separate scales?
4. Names of ions and substrates: the claim name comes from a looked-up list, the paper's name is "as written" (fluoride, F-, F−). Should the leaf be asked for the name the list uses, or is there a synonym list
   that I should know about?
5. Should the direction of flow (into the cell or out) or the coupling ion (proton, sodium) be part of what is checked, or is the claim only "this protein moves this molecule"?
6. Is 0.25 (the stated-only strength) right for transport, where "uptake was observed" often carries a control in the same sentence ("above the empty vector")?
7. May an accumulated amount (nmol/mg at a time) or a stated current ever be the effect? The draft says no, because of time, cell number and expression; the alternative is the unit sets of the sheet extended
   (registration note 4) and anchors for them.
8. The unit "fold": use `dimensionless` for the ratio kinds (the draft, no change in the sheet code) or add `fold` as for `rate_ratio`?
9. Researched values: all anchors, the order of the quantities and the per-type maxima are mine, from memory. Which should I verify first against the transport literature (the Km range, the 30-fold, the turnover range)?
10. No real published paragraph has been chosen for any type; the papers in section 1 are candidates (BtsT PMC5738728 and BioY PMC1815280 for tracer uptake and Km; Fluc for vesicle and bilayer). Should a real paragraph be
    found per type before the second wave starts, or by each builder as for binding?
