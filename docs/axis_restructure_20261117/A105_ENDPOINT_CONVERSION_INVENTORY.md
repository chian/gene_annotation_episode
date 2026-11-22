# A105 `endpoint_conversion` experiment inventory (SOP step 0, DRAFT for the owner to correct)

Written 2026-11-22 under `A105_EXPERIMENT_SOP.md` step 0, modelled on `A105_ACTIVITY_RATE_INVENTORY.md`. Read-only search. Nothing was run (no
Python, no test, no script); every statement about the code comes from reading it. Files written: this document,
`G/literature_endpoint_conversion_direction.py` and `runs/a105_class_drafts/registration/CLASS_endpoint_conversion.md`.

**Status: DRAFT.** The owner has not supplied an `endpoint_conversion` list. Following SOP 0a item 2 the list below is drafted from the sources found
and from domain knowledge. **Nothing here is owner-confirmed.** It is one entry per reapplicable protocol (a way of measuring), not per paper or per
case. Every number is `EXPERT_REVIEW`, owner to confirm, and every literature statement is "from memory, not verified" unless a source file is named.

**What the class is about.** How much of the substrate was converted, or how much product there was, at an end point, and how long completion took:
a conversion fraction, an endpoint amount, a completion time. One time point or a yield, not a rate. Rates and kinetic constants (kcat, Km, a slope,
U/mg) belong to `activity_rate`. The same paper and the same assay can give both: a time course read for its slope is `activity_rate`; the same
chromatogram read for "what share was converted after 24 h" is `endpoint_conversion`. A result is placed in a class by the quantity it states, one
quantity per result.

---

## 1. Sources searched and what was found

| Place | Found | Used for |
| --- | --- | --- |
| `docs/axis_restructure_20261117/A105_EXPERIMENT_SOP.md` | The protocol (step 0), the class decisions (0c), the template (0d), the build steps, the rules that apply everywhere. | Method of this document. |
| `docs/axis_restructure_20261117/A105_ACTIVITY_RATE_INVENTORY.md` | The only class inventory that exists; 19 types; direction and judgement section; class decisions. | Model of the sections. |
| `G/literature_assay_grading.py` | `QUANTITY_KINDS['endpoint_conversion']` = conversion_fraction, conversion_difference, endpoint_amount, completion_time, completion_time_ratio. `CRITERIA_BY_TYPE['endpoint_conversion']` = `COMMON_CRITERIA` (measurement_identity, calibration_applicability, matrix_interference, background_alternatives, attribution_supported, assertion_relevance, condition_scope, variance_correspondence, sampling_basis) + endpoint_alignment, conversion_denominator, product_identity. `_required_criteria`: product_identity optional (but explicit for endpoint_amount); conversion_denominator optional for endpoint_amount, completion_time and completion_time_ratio. `_quantity_unit_supported` units in section 2. | Class core, criteria mapping, units. |
| `G/literature_activity_direction.py`, section (5c) of `G/literature_row_contract.py`, `G/literature_direction.py`, section (5b2) | The class-scoped direction paradigm: log-scale position between a noise end and a strong end, smooth step `3p^2 - 2p^3`, lowered by the relative spread, never opposing, qualitative and unstated cases handed to `literature_direction`. `STATED_ONLY_STRENGTH` 0.25. `stated_strength` counts only `QUANTITATIVE_STRENGTH_ANCHORS` types and `activity_rate` as measuring. | Section 4 and the direction file. |
| `G/literature_page_update.py`, `G/literature_row.py`, `G/literature_claim.py`, `G/literature_relevance.py` | The activity branch of the direction call; `NOT_POOLED_CLASSES = ('activity_rate',)`; claims read only `term_ref` and `reference` values and `catalyzes` with a `term_ref` gives a null partner; relevance by partner equality. **`class_of_predicate` raises for a predicate in two classes and the page uses it (`internal_summary.py` line 151).** | Sections 5, 6 and the registration note. |
| `verification/biochemical_fourteen_graders_319/REPORT.md` | Old readers that were really endpoint-conversion calculations: entry 5 `read_completion_time_inputs` (HFP Ru5P/R5P isomerisation, `>18 h` after further cleanup versus `<10 min` earlier, ratio `>108`, not an activity ratio); entry 13 `read_parent_depletion_inputs` (purified P205, capecitabine removal at 24 h, active minus inactive S146A and minus abiotic control, shared active observation kept); entry 12 `read_concentration_window_inputs` (PARP1 HPLC NAD+ consumed, nicotinamide formed, depletion fraction over a window); entry 11 `read_endpoint_signal_inputs` (MvhADG/HdrABC MTZ reduction at 320 nm, baseline-corrected amplitude and fraction). | Past work and the quantities. |
| `verification/biochemical_assay_guides_318/REPORT.md` | "An endpoint experiment can answer an end..." (line 11): fraction converted and regime; no-enzyme, inactive-enzyme and reporter-only controls answer different questions; "there was a control" is weaker than its composition, timing, result and uncertainty. | Controls and noise fields. |
| `research/experimental_scoring_review_2026-10-23/` (`molecular_measurement/summary.md`, `EMERGING_LANES.md`, `SYNTHESIS.md`) | HFP isomerisation present but assigned to a contaminating RpiA (attribution); YihS NMR fractions (product-distribution case, not this class); CysQ colour assay versus AMP mass spectrometry; "a different endpoint or time window is not a contradictory repetition" (ES03). | Attribution and alignment notes. |
| `verification/a105_sheet_reader_inventory_315/SHEETS.tsv` | Sheet 1 "Corrected preparation endpoint activity", sheet 29 "Finite endpoint signal correction". Calculations, not types. | Past-work fields only. |
| `docs/axis_restructure_20261117/EXPERIMENT_INVENTORY_SEARCH.md`, `..._SEARCH_2.md` | No per-technique list for endpoint conversion; `completion_time` and `endpoint_signal` appear only as module names; the owner's biochemical questions (sensitivity, kinetic parameters, heating, in vitro or in vivo, realism of the chemistry, expected signal in messy samples, a control for spontaneous reaction). | Questions mapped to the class core. |
| Activity inventory cases (`QueF` NMR PMC555470, `CysQ` PMC2711008, `RidA` PMC3270999, HFP PMC12051542, BbPK, CsiD) | Cited there for activity; the same papers also give end points (QueF NMR product after incubation, CysQ AMP by mass spectrometry, HFP NMR fractions). Their text was not re-read here. | Past work, marked "from the activity inventory". |
| Codex session files, git history | Not searched (SOP: grep only; the task forbids opening a session file). | Nothing. |

**Conclusion:** as for binding and activity, no prior per-technique list for this class exists in the places searched. The prior work is organised by
calculation (completion-time ratio, parent depletion, concentration window, endpoint signal). The list below is new.

---

## 2. What all `endpoint_conversion` types share (the class core)

**Evidences:** sheet `endpoint_conversion` (predicate `catalyzes`, section 5; blocker noted there).

**What is measured:** at one stated time (or at completion), the share of the substrate that was converted, or the amount of product present, or the
time the reaction took to reach a stated completion or equilibrium. The enzyme is the target; the substrate is the partner.

**Stated quantities of the sheet** (`QUANTITY_KINDS['endpoint_conversion']`) and their units the sheet accepts (`_quantity_unit_supported`):

| Quantity kind | Meaning | Units the sheet accepts | Anchor unit used by the direction rule |
| --- | --- | --- | --- |
| `conversion_fraction` | share of the initial substrate converted at the end point, as stated | `fraction`, `dimensionless` | `fraction` |
| `conversion_difference` | the share converted minus the paper's own control (no-enzyme, inactive enzyme, zero-time) | `fraction`, `dimensionless` | `fraction` |
| `endpoint_amount` | product (or substrate left) at the end point | `M, mM, uM, nM, mol, mmol, umol, nmol, pmol, molecules, count, mg, ug, ng, mg/ml` | `uM` |
| `completion_time` | time to reach the stated completion or equilibrium | `s, sec, min, h, hour` | `min` |
| `completion_time_ratio` | reference completion time over test completion time (more than 1: the test completes sooner) | `fraction`, `dimensionless` | `dimensionless` |

A paper states percent; the sheet has no percent. The converter turns percent into a fraction (factor 0.01), `h`/`s` into minutes, and an amount in
mol into a concentration only when the passage also states the reaction volume (`reaction_volume` below). All are exact conversions
(FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes.

**Record quantities common to every type** (each a record operand, `point` or `unavailable` with a reason, never 0, never omitted):

- `conversion_percent` (unit `percent`, `fraction`) and `conversion_spread`; `spread_kind` (SD, SEM, CI, range; an unstated "±" stays unstated).
- `control_conversion` (same units) beside the test value; `net_conversion_percent` when the paper states the control-corrected value itself.
- `substrate_initial` (concentration `uM, mM, M`, or amount with `reaction_volume` in `uL, mL`): the denominator of the fraction.
- `product_amount` (`uM, mM, nM` or `nmol, umol, pmol`) and `substrate_remaining`.
- `endpoint_time` (`s, min, h`) the time at which the end point was read; `completion_time` (`s, min, h`) with an optional bound (`>`, `<`) when stated;
  `reference_completion_time` (same units).
- `enzyme_concentration` (`uM, nM, mg/mL`) and `enzyme_loading_basis` (molar, mass, active sites).
- `detection_limit` (same units as the quantified species) for non-detection results.
- `replicate_count` and the fact `independent_replicates`; the count is recorded, no cut-off.
- Identity block (automatic, `F/literature_identity_extraction.py`): `target_id` (the enzyme as written), optional `partner_id` (the substrate converted),
  `temperature_c`, pH.

**Facts common to every type** (`yes`, `no`, `unknown`, `not_applicable`; silence is `unknown`, never `no`):
no_enzyme_control_done; inactive_enzyme_control_done; zero_time_sample_done; time_point_stated; same_time_for_compared_arms; reaction_stopped_before_analysis
(quench or inactivation, so the read time is the real end point); initial_substrate_determined (denominator measured, not nominal); product_identified_by_standard
(an authentic standard or an independent identification); substrate_loss_matches_product_gain (mass balance stated); purified_enzyme; native_substrate;
substrate_fully_dissolved; conversion_detected_above_control (the qualitative statement, section 4).

**Class criteria that every type's grader decides, and the sheet criterion each maps to** (a type adds its own method criteria in section 3; the
mapping rule is the SOP's: any `conflicting` makes the sheet criterion `conflicting`, else any `unknown`, else `supported`; degree the minimum):

| Core criterion (grader, facts only) | Sheet criterion of `CRITERIA_BY_TYPE['endpoint_conversion']` |
| --- | --- |
| substrate, product, units and denominator stated for this estimate | measurement_identity |
| standard curve or response factor stated and the read amount inside it; recovery of a known standard | calibration_applicability |
| extract, buffer or matrix effect addressed (matrix-matched standard, internal standard) | matrix_interference |
| no_enzyme_control_done, inactive_enzyme_control_done, zero_time_sample_done | background_alternatives |
| enzyme dependence shown (rises with enzyme, falls with the inactive mutant or an inhibitor); no contaminating activity | attribution_supported |
| time_point_stated, same_time_for_compared_arms, reaction_stopped_before_analysis | endpoint_alignment |
| initial_substrate_determined; the fraction's denominator is the measured initial amount | conversion_denominator |
| product_identified_by_standard, substrate_loss_matches_product_gain | product_identity |
| native_substrate; the end point addresses the claimed conversion | assertion_relevance |
| purified_enzyme; temperature and pH inside the claim's conditions | condition_scope |
| the stated spread belongs to this estimate (kind stated, same correction) | variance_correspondence |
| replicate_count; independent_replicates | sampling_basis |

Each judgement of a number (a calibration range, a replicate count, a time that is long against the half-time) is made on the SHEET side by the
converter, researched per assay and made gradual (SOP step 3). The grader records the facts and hands numbers over with a reason ending in
`_recorded_for_the_sheet`.

**Owner biochemical questions mapped to the core:** sensitivity -> `detection_limit` and the net conversion over the control; kinetic parameters ->
none (activity_rate); heating -> `temperature_c` and a pretreatment fact; in vitro / in vivo -> `purified_enzyme`; realism of the chemistry ->
`native_substrate`, pH; expected signal in messy samples -> matrix-matched calibration and internal standard; spontaneous reaction -> the no-enzyme
control and `control_conversion`.

**Certainty:** quantitative: the net conversion (or the time, or the amount) against its own control and spread; or qualitative: "conversion detected" /
"not detected" as a sentence (no number), which counts less than a measured value (section 4).

**Readers that supply it (all types):** text paragraphs (Methods and Results) and tables. Chromatograms, spectra, gel images and progress plots are
figures and unavailable today (SOP Known gaps).

---

## 3. The draft experiment list (10 types)

Ids start with `endpoint_`, are snake_case and are none of the reserved ids. The family column names the way the end point is read.

| # | Type id | Experiment | Family |
| --- | --- | --- | --- |
| 1 | `endpoint_hplc_uv` | Fixed-time reaction, quenched, substrate and product quantified by HPLC with optical detection or refractive index | Separation, discontinuous |
| 2 | `endpoint_ms_quant` | Fixed-time reaction, product quantified by LC-MS or GC-MS against an internal standard | Mass spectrometry, discontinuous |
| 3 | `endpoint_nmr` | Reaction followed by NMR; conversion read from integrals at a stated time or at completion | NMR |
| 4 | `endpoint_colorimetric` | Fixed-time reaction stopped with a colour reagent, product read from a standard curve | Optical, discontinuous |
| 5 | `endpoint_radiometric` | Radiolabelled substrate, product separated and counted at a fixed time | Isotope, discontinuous |
| 6 | `endpoint_gel_band` | Substrate and product separated on a gel or TLC plate, share converted by densitometry | Separation, discontinuous |
| 7 | `endpoint_optical_plateau` | Reaction run to a final optical signal (absorbance or fluorescence), conversion from the signal change and a calibration | Optical, continuous to a plateau |
| 8 | `endpoint_enzymatic_assay` | Substrate left or product formed measured at the end by a second, specific enzyme | Enzymatic end-point determination |
| 9 | `endpoint_time_course_completion` | Reaction sampled over time until it reaches a stated completion or equilibrium; the time is the result | Sampled progress, any detector |
| 10 | `endpoint_gas_evolution` | Gas product (H2, CO2, CH4, N2O, O2) accumulated in a closed vessel, measured by GC or manometry at a fixed time | Gas, discontinuous |

**Considered and not listed as types** (with the reason):

- *Initial-rate and steady-state kinetics, Km, kcat*: `activity_rate`.
- *Product spectrum, equilibrium composition (NMR fractions of R5P and Ru5P)*: `product_distribution`. The HFP paper gives both; the completion time is this class.
- *Cofactor-to-product coupling (P450cam NADH versus product)*: `reaction_coupling`.
- *Whole-cell biotransformation and growth*: a context fact (`purified_enzyme` no) on any type; growth belongs to A106 (not touched).
- *Titration end points, polarimetry, conductometry, isothermal calorimetry to completion*: rare; add if a real paper needs them.
- *Partner omission and addback at one time point*: a design, not a protocol; a fact on the record (activity inventory's open question).

Each entry below follows SOP 0d and then adds what a builder needs: record quantities with unit vocabularies, yes/no facts, the method's own criteria and the
sheet criterion each maps to. "Core" means everything in section 2. Researched values are named only where a builder can start from them; each is
`EXPERT_REVIEW` and "from memory, not verified".

### 3.1 `endpoint_hplc_uv`

```text
experiment:            fixed-time reaction with HPLC quantification        (type id endpoint_hplc_uv)
family:                separation, discontinuous (HPLC-UV, HPLC-diode array, HPLC-RI, ion chromatography)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  peak area or height (arbitrary); substrate and product amount (uM, mM, nmol) from a standard curve; percent
                       conversion; retention time (min); time point (min, h); detection or quantification limit
controls required:     authentic product standard (identity and calibration); no-enzyme and inactive-enzyme sample at the same time;
                       zero-time sample; quench stated; internal standard or injection-volume control when stated
noise expectations:    stated spread and kind; replicate injections versus independent reactions; calibration range holds the read amounts;
                       substrate and product both quantified (so loss matches gain); detection limit for a non-detection
replicates needed:     count + independence fact; no cut-off
certainty:             quantitative net conversion; identity by retention time against a standard (weaker than mass); a non-detection is
                       bounded by the stated limit
readers that supply it:text, tables; chromatograms unavailable
past work (where):     P205 capecitabine parent removal at 24 h versus S146A and abiotic controls (verification 319 entry 13, tests/test_literature_p205_parent_depletion_308.py);
                       PARP1 NAD+ and nicotinamide at a window (319 entry 12); BbPK direct HPLC acetate (activity inventory, case 164)
```

Record quantities: core, plus `peak_area_ratio` (`dimensionless`), `standard_curve_low` and `standard_curve_high` (`uM, mM`), `injection_replicates`
(count), `detection_limit` (`uM, nM`). Facts: authentic_standard_used, internal_standard_used, calibration_in_matrix, both_species_quantified.

Method criteria (grader) to sheet criteria: standard_curve_covers_read_amount -> calibration_applicability (the converter judges the position of the read
amount inside the stated range, gradual, full inside, falling towards the edge and beyond); both_species_quantified and substrate_loss_matches_product_gain ->
product_identity; calibration_in_matrix -> matrix_interference; injection_replicates versus independent_replicates -> sampling_basis.

### 3.2 `endpoint_ms_quant`

```text
experiment:            fixed-time reaction with mass-spectrometric quantification   (type id endpoint_ms_quant)
family:                mass spectrometry, discontinuous (LC-MS, LC-MS/MS, GC-MS, direct-infusion ESI with an internal standard)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  ion counts or area ratio to the internal standard; product amount (uM, nM, nmol) from a calibration; m/z and
                       retention time; percent conversion; time point; limit of detection or quantification
controls required:     authentic product standard; stable-isotope or structural-analogue internal standard; matrix-matched calibration for
                       extracts; no-enzyme and inactive-enzyme samples; zero-time sample
noise expectations:    spread and kind; matrix effect (ion suppression) addressed; calibration range; limit of detection for a
                       non-detection; mass accuracy or MS/MS match stated
replicates needed:     count + independence fact
certainty:             quantitative with identity by mass; the product named, not a product class
readers that supply it:text, tables; spectra unavailable
past work (where):     CysQ AMP by mass spectrometry with an internal standard (PMC2711008, from the activity inventory); CsiD LC-MS product identity
                       (PMC6265302); Bcd/Etf H2 formation (PMC2223550) is the gas type
```

Record quantities: core, plus `area_ratio_to_internal_standard`, `calibration_low` and `calibration_high` (`uM, nM`), `mass_accuracy` (`ppm`), `detection_limit`.
Facts: internal_standard_used, isotope_labelled_standard, matrix_matched_calibration, ms_ms_confirmation, authentic_standard_used.

Method criteria: internal_standard_used and matrix_matched_calibration -> matrix_interference; calibration range -> calibration_applicability;
authentic_standard_used and ms_ms_confirmation -> product_identity.

### 3.3 `endpoint_nmr`

```text
experiment:            NMR end point or progress to completion              (type id endpoint_nmr)
family:                NMR (1H, 13C, 31P, 19F), quantitative integrals
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  integral of substrate and product signals (relative); percent conversion (integral ratio); concentration against an
                       internal standard (uM, mM); chemical shift assignments (ppm); time point; completion time if followed
controls required:     no-enzyme spectrum at the same time; inactive-enzyme spectrum; authentic product spectrum or assignment; internal
                       concentration standard when an amount is stated; relaxation delay long enough for quantitative integrals
noise expectations:    signal-to-noise of the integrals when stated; the spread of repeated reactions (rarely given); sensitivity is low so the
                       enzyme and substrate amounts are high (condition_scope)
replicates needed:     count + independence fact (NMR reactions are rarely repeated)
certainty:             quantitative with identity by spectrum; a non-detection limited by the signal-to-noise
readers that supply it:text, tables; spectra unavailable
past work (where):     HFP isomerisation by NMR (PMC12051542; fractions belong to product_distribution, the completion time to endpoint_time_course_completion);
                       QueF (PMC555470) and sulfoglycolysis NMR (molecular_measurement) from the activity inventory
```

Record quantities: core, plus `integral_ratio`, `internal_standard_concentration`, `relaxation_delay` (`s`), `signal_to_noise` (`dimensionless`), `nuclei` choice (1H, 13C,
31P, 19F, other). Facts: internal_standard_used, quantitative_relaxation_delay, product_assigned_by_reference_spectrum.
A relaxation delay of at least five times the longest T1 is the usual condition for quantitative integrals (from memory, not verified); the converter judges
it gradually if the paper states both numbers.

Method criteria: quantitative_relaxation_delay and internal_standard_used -> calibration_applicability; signal_to_noise recorded -> variance_correspondence
(an integral without a stated noise has no variance); product_assigned_by_reference_spectrum -> product_identity.

### 3.4 `endpoint_colorimetric`

```text
experiment:            stopped assay with colorimetric detection of the product   (type id endpoint_colorimetric)
family:                optical, discontinuous (malachite green or molybdate phosphate, DNS or BCA reducing sugar, DTNB thiol, Nessler or
                       Berthelot ammonia, hydroxamate, chromogenic derivatisation)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  absorbance at the reagent wavelength (nm); product amount from a standard curve (nmol, uM); percent conversion; time
                       point; detection limit
controls required:     product standard curve in the reaction buffer; no-enzyme and zero-time blank; substrate-only blank (substrate reacting
                       with the reagent, for example free phosphate in ATP); stop and colour development time stated
noise expectations:    spread and kind; blank beside the test; absorbance inside the standard curve range; reagent interference by buffer
                       components (phosphate, reducing agents)
replicates needed:     count + independence fact
certainty:             quantitative; a product class (phosphate, reducing end, thiol), not a named product
readers that supply it:text, tables
past work (where):     CysQ colour assay that cannot resolve low-uM amounts (molecular_measurement spec_cysq_pap_not_imp, activity inventory);
                       BbPK chromogenic acetyl phosphate (case 164)
```

Record quantities: core, plus `absorbance_test`, `absorbance_blank`, `wavelength` (`nm`), `standard_curve_low` and `standard_curve_high`, `color_development_time`
(`min`). Facts: standard_curve_in_buffer, substrate_blank_done, reagent_interference_checked.

Method criteria: standard_curve_in_buffer and the curve range -> calibration_applicability; substrate_blank_done -> background_alternatives;
reagent_interference_checked -> matrix_interference; product class only -> product_identity unknown unless an independent identification is stated.

### 3.5 `endpoint_radiometric`

```text
experiment:            radiolabelled substrate, product counted at a fixed time    (type id endpoint_radiometric)
family:                isotope, discontinuous (14C, 3H, 32P, 35S; product separated by TLC, filter binding, ion exchange or as 14CO2; scintillation
                       counting or phosphorimager)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  counts (cpm, dpm) or phosphorimager units; fraction of the label in the product; percent conversion; product amount
                       (nmol, pmol) from the specific radioactivity (Ci/mol or cpm/nmol); time point
controls required:     no-enzyme and boiled-enzyme sample; zero-time sample; substrate alone through the separation step (carry-over background);
                       stated specific radioactivity
noise expectations:    spread and kind; background counts beside the test counts; counting efficiency stated or not; label purity of the substrate
replicates needed:     count + independence fact
certainty:             quantitative and very sensitive; the identity of the product rests on the separation
readers that supply it:text, tables; autoradiographs unavailable
past work (where):     none found in the places searched
```

Record quantities: core, plus `counts_test`, `counts_background`, `specific_radioactivity` (`Ci/mol`, `cpm/nmol`), `label_purity_percent`. Facts:
separation_control_done, boiled_enzyme_control_done, label_in_product_position.

Method criteria: separation_control_done -> background_alternatives; counts over background recorded for the sheet -> calibration_applicability;
label_in_product_position (the label is on the part of the substrate that ends up in the product) -> product_identity.

### 3.6 `endpoint_gel_band`

```text
experiment:            gel or TLC separation with densitometry              (type id endpoint_gel_band)
family:                separation, discontinuous (nuclease and ligase products on a denaturing gel, protease cleavage by SDS-PAGE, kinase
                       mobility shift, TLC of nucleotides or lipids; stained or labelled bands)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  band intensity of substrate and product (arbitrary); fraction of substrate converted (fraction or percent); time point;
                       the sentence "product band present or absent"
controls required:     no-enzyme lane; catalytic-mutant lane; size markers or product marker; metal-free (EDTA) lane for metal-dependent enzymes;
                       zero-time lane
noise expectations:    spread across gels; densitometry inside its linear range (stated or not); the fraction defined over substrate plus product
replicates needed:     count + independence fact (separate gels)
certainty:             quantitative semi-quantitative fraction, or a yes/no band; identity by mobility against a marker only
readers that supply it:text, tables; gel images unavailable (today only the sentence and the table)
past work (where):     none found for conversion (the old gel sheet, SHEETS 17, is protein bands: protein_signal)
```

Record quantities: core, plus `intensity_substrate`, `intensity_product` (`arbitrary`), `fraction_defined_over` choice (substrate_only, substrate_plus_product, total_lane).
Facts: marker_lane_done, mutant_lane_done, densitometry_linear_range_stated, band_identified_by_marker.

Method criteria: mutant_lane_done and no_enzyme_lane_done -> background_alternatives; fraction_defined_over -> conversion_denominator;
band_identified_by_marker -> product_identity; densitometry_linear_range_stated -> calibration_applicability.

### 3.7 `endpoint_optical_plateau`

```text
experiment:            reaction run to a final optical signal                (type id endpoint_optical_plateau)
family:                optical, continuous to a plateau (absorbance of a chromophoric substrate or product, fluorescence of a fluorogenic
                       substrate, NADH consumption to completion)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  final absorbance or fluorescence change; the extinction coefficient or the fluorophore calibration; product amount
                       (uM) from the change; percent of the substrate converted; time to the plateau (min); wavelength (nm)
controls required:     no-enzyme baseline over the same time; the full-conversion reference (complete conversion of the same substrate amount, or
                       free fluorophore standard); inner-filter and quenching check at the substrate used
noise expectations:    spread and kind; baseline drift beside the signal change; signal inside the detector's linear range
replicates needed:     count + independence fact
certainty:             quantitative when calibrated against a full-conversion reference; otherwise relative to the paper's own control
readers that supply it:text, tables; traces unavailable
past work (where):     MvhADG/HdrABC MTZ reduction at 320 nm, endpoint amplitude and fraction (verification 319 entry 11; a figure of the old tooling);
                       NADH 340 nm cases of the activity inventory (Bcd/EtfAB PMC2223550)
```

Record quantities: core, plus `signal_change_total`, `signal_change_baseline`, `extinction_coefficient` (`M^-1cm^-1`, `mM^-1cm^-1`), `path_length` (`cm`), `wavelength`
(`nm`), `time_to_plateau` (`s, min, h`). Facts: baseline_control_done, full_conversion_reference_done, plateau_stable, product_identified_by_standard.

Method criteria: full_conversion_reference_done and extinction coefficient stated -> calibration_applicability; baseline_control_done -> background_alternatives;
plateau_stable -> endpoint_alignment (the end point is a plateau, not a point on a slope); product_identified_by_standard -> product_identity (a chromophore change
names a reaction only when the product is identified).

### 3.8 `endpoint_enzymatic_assay`

```text
experiment:            end-point determination with a second enzyme          (type id endpoint_enzymatic_assay)
family:                enzymatic end-point determination (formate by formate dehydrogenase, glucose by glucose oxidase and peroxidase, ammonia
                       by glutamate dehydrogenase, ethanol, lactate, a ketoacid trapped by ferricyanide or a hydrazone)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  absorbance or fluorescence of the reporter at the end; amount of substrate left or product formed (uM, nmol) from a
                       standard series; percent conversion; time point; detection limit
controls required:     standard series of the analyte through the same second enzyme; reaction mixture without the first enzyme; check that the
                       second enzyme does not act on the original substrate or the test compound; complete reporter conversion (enough second enzyme
                       and cofactor)
noise expectations:    spread and kind; reporter in excess; standard series range against the signal; side reactivity of the second enzyme
replicates needed:     count + independence fact
certainty:             quantitative; identity rests on the specificity of the second enzyme
readers that supply it:text, tables
past work (where):     FDH-coupled formate end point (moral_2011_review.md, activity inventory); RidA ketoacid and ferricyanide trapping (PMC3270999)
```

Record quantities: core, plus `reporter_signal_test`, `reporter_signal_blank`, `standard_series_low`, `standard_series_high`, `second_enzyme_amount` (`U/mL`),
`second_enzyme_incubation` (`min`). Facts: standard_series_through_second_enzyme, second_enzyme_specificity_checked, reporter_conversion_complete.

Method criteria: standard_series_through_second_enzyme -> calibration_applicability; second_enzyme_specificity_checked -> product_identity;
reporter_conversion_complete -> endpoint_alignment (the read end point is the end of the second reaction); first-enzyme-omitted mixture ->
background_alternatives.

### 3.9 `endpoint_time_course_completion`

```text
experiment:            sampled progress to a stated completion or equilibrium     (type id endpoint_time_course_completion)
family:                sampled progress, any detector (NMR, HPLC, optical); the result is the TIME to reach the stated state
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  time to completion or equilibrium (s, min, h), possibly bounded (">18 h", "<10 min"); the stated criterion of completion (for
                       example no substrate signal left, or a constant ratio over later samples); the reference time of a control or an earlier preparation;
                       the ratio of the two
controls required:     the same completion criterion for the compared arms; no-enzyme time course (does it complete alone at all); a sampling interval
                       finer than the reported time; the same temperature and loading in the compared arms
noise expectations:    the sampling grid (a completion time is only known to the interval between two samples); spread when several runs; a bounded
                       time is a limit, not a value
replicates needed:     count + independence fact
certainty:             quantitative time (or a bounded time); the comparison with a reference only if the endpoint definition is the same
readers that supply it:text, tables
past work (where):     HFP Ru5P/R5P isomerisation: more than 18 h versus less than 10 min after cleanup, a ratio above 108 that is not an activity ratio
                       (verification 319 entry 5; research molecular_measurement: isomerisation present, assignment to HFP challenged by a contaminating RpiA)
```

Record quantities: core, plus `sampling_interval` (`s, min, h`), `completion_criterion` choice (substrate_gone, product_plateau, ratio_constant, equilibrium_reached,
other_stated), `enzyme_loading_test` and `enzyme_loading_reference` (same units). Facts: same_completion_criterion_in_arms, same_loading_in_arms, no_enzyme_course_done.

Method criteria: same_completion_criterion_in_arms -> endpoint_alignment (the central one for a time ratio: different endpoint definitions are not comparable);
no_enzyme_course_done -> background_alternatives; same_loading_in_arms -> condition_scope; contaminating activity examined -> attribution_supported (the HFP lesson).

### 3.10 `endpoint_gas_evolution`

```text
experiment:            gas product accumulated in a closed vessel             (type id endpoint_gas_evolution)
family:                gas, discontinuous (GC with thermal-conductivity or flame detection, headspace GC-MS, manometry, gas-pressure transducer)
evidences (sheet):     endpoint_conversion                                 (predicate: catalyzes)
native outputs/units:  gas amount (umol, nmol) or percent of the theoretical yield; headspace partial pressure (kPa, bar); time point; detection limit
controls required:     no-enzyme vial; inactive-enzyme vial; calibration with known gas amounts in the same vessel; headspace and liquid volumes stated
                       (the dissolved part of the gas); anaerobic technique where oxygen interferes
noise expectations:    spread and kind; leak control (a sealed blank held for the same time); calibration range; temperature at the reading
replicates needed:     count + independence fact
certainty:             quantitative; the gas is identified by the detector; the yield depends on the stated stoichiometry
readers that supply it:text, tables
past work (where):     Bcd/EtfAB H2 formation (PMC2223550, activity inventory); H2 formation of Clostridium kluyveri (verification 319 entry 2, as a rate)
```

Record quantities: core, plus `headspace_volume` (`mL`), `liquid_volume` (`mL`), `gas_partial_pressure` (`kPa`, `bar`), `theoretical_yield` (`umol, nmol`), `gas_species` choice (H2, CO2, CH4,
N2O, O2, other). Facts: calibration_gas_in_same_vessel, leak_control_done, dissolved_gas_accounted_for, gas_identified_by_detector.

Method criteria: calibration_gas_in_same_vessel -> calibration_applicability; leak_control_done and the no-enzyme vial -> background_alternatives;
dissolved_gas_accounted_for -> conversion_denominator (the amount the fraction is taken from); gas_identified_by_detector -> product_identity.

---

## 4. Direction and strength for the class (DRAFT, owner to confirm)

Code: `G/literature_endpoint_conversion_direction.py` (new); constants to be added to `G/literature_row_contract.py` section (5d) by the coordinator, from
`runs/a105_class_drafts/registration/CLASS_endpoint_conversion.md`. The paradigm is the activity class's: no generic formula for every quantity; one researched
pair of ends per quantity, gradual between them, never a pass or fail.

```text
p = clip( (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), 0, 1 )
s = (3 p^2 - 2 p^3) / (1 + r^2),    r = sd / e  (0 when no spread is stated)
log_ratio = QUALITATIVE_LOG_RATIO[type] * s
```

- A stated effect SUPPORTS by its graded strength `s`; `s == 0` (at or under the noise end) is neutral. A quantitative result never opposes. Controls,
  blanks, endpoint alignment and every other sheet criterion lower the WEIGHT only, never the direction.
- The paper stating that no conversion was seen above its own control or limit is the not-detected case: the qualitative path (`interaction_not_detected`,
  read "conversion not detected"), which opposes.
- Larger is stronger for the conversion quantities and the amount; SMALLER is stronger for the completion time. The same formula serves: the completion
  time's noise end is the larger number.

| Quantity | Effect operand unit (anchor) | Larger or smaller is stronger | noise_end | strong_end | Reason (all EXPERT_REVIEW, owner to confirm; from memory, not verified) |
| --- | --- | --- | --- | --- | --- |
| conversion_difference (net of the paper's own control) | fraction | larger | 0.02 | 0.9 | Integration, pipetting and control-subtraction noise of HPLC, NMR and gel readouts is a few percent (quantitation limits near 1 to 5 percent of the substrate). Near-complete conversion is the strongest an end point can show; above 0.9 the product is limited by what the method can tell from residual substrate. |
| conversion_fraction (as stated) | fraction | larger | 0.05 | 0.9 | The raw value still holds spontaneous conversion and background (autohydrolysis commonly gives a few percent over hours), so its noise end is higher than the net one. |
| completion_time_ratio (reference time over test time) | dimensionless | larger | 1 | 1e3 | No faster than the reference is the noise end; three orders of speed-up is the practical range of a time comparison. The HFP case in the old inventory was a ratio above 108 (a bound). |
| completion_time | min | smaller | 1440 | 1 | A reaction needing a day (24 h) is hard to tell from slow background chemistry and enzyme decay; completion inside one minute is the fastest an ordinary sampled assay resolves. |
| endpoint_amount | uM | larger | 1 | 1e3 | 1 uM is about the quantitation floor of UV-HPLC and colorimetric product assays; 1 mM product is a substantial conversion of a usual 1 to 10 mM substrate. The weakest scale: it depends on the loading the paper chose. |

- **Order of preference when a record states several** (`ENDPOINT_EFFECT_ORDER`): conversion_difference, conversion_fraction, completion_time_ratio,
  completion_time, endpoint_amount. Why: a fraction net of the paper's own control isolates the enzyme from spontaneous conversion and has no unit
  problem; the raw fraction is relative to the loaded substrate but holds background; a time ratio is relative to the paper's own reference but needs the same
  endpoint definition on both sides; a bare time depends on the enzyme and substrate loaded; an absolute amount depends on the loading and has no natural scale.
- **A result stated in words alone** ("conversion was observed", "no conversion was detected"): the existing vocabulary is kept and READ for this class:
  `interaction_detected` = "conversion detected", `interaction_not_detected` = "conversion not detected", `interaction_not_stated` = "conversion not stated". It counts
  `STATED_ONLY_STRENGTH` (0.25) of the type's value, for a detection and a non-detection alike. This needs `stated_strength` in the contract to count this
  class as measuring (registration note, 1c); today it would return 1.0 for these types.
- **`direction_field_support`:** the support class of the field that fixes the direction (the chosen effect), or of `conversion_detected_above_control` for a
  qualitative result; required whenever the direction is known.
- **A non-positive net conversion** (the test no better than the control) is not an effect: the converter fills no effect; if the paper says so in words it goes through
  the qualitative path. **A bounded time** ("> 18 h") cannot be the effect (the function requires a point and raises); see section 7.
- **Pooling:** NOT pooled. The effect of a result is one of five quantities in different units chosen per experiment, so the row's pooled effect, variance and
  precision stay null for the class (`NOT_POOLED_CLASSES`), as for `activity_rate`. The direction, strength and weight are unaffected.
- `QUALITATIVE_LOG_RATIO[type]` (the per-type maximum, also the magnitude of "conversion not detected") is a per-type proposal in the registration note; the builder of each type confirms it.

---

## 5. Claim predicate (DRAFT; BLOCKER for the owner)

- **Proposed predicate:** `catalyzes` (SOP 0b), the claim `E catalyzes S` with the enzyme as subject and the substrate as partner.
- **Not symmetric.** "E catalyzes S" is not "S catalyzes E"; it stays out of `SYMMETRIC_PREDICATES`.
- **Subject:** the enzyme, the record's `target_id` (who was measured; target match `same` when the normalized names are equal).
- **Partner:** the substrate that was converted (the record's `partner_id`, as written in the passage). When the hypothesis value is a `reference` to a molecule
  record, that molecule is the claim's partner, and the record's stated substrate must agree: equal after normalisation is `relevant` (`partner_agrees`), a different
  one is `irrelevant` (`other_partner`) and stays off the row, none stated is `unresolved` (`partner_not_stated`) when the experiment measured a conversion, else `irrelevant`.
  When the value is a `term_ref` (the existing A105 hypotheses carry a reaction term) the claim's partner is null and the target alone decides (`TERM_PARTNER_IS_NOT_A_MOLECULE`).
  The product is never the partner: a claim names molecules only, one partner.
- **BLOCKER:** `catalyzes` already belongs to `activity_rate` (`CLAIM_PREDICATES_BY_CLASS`). `class_of_predicate` raises for a predicate in two classes, and the
  page uses it to choose the claim's sheet class (`internal_summary.py` line 151; `test_binding.py` line 155 asserts `catalyzes` is `activity_rate`). With both classes
  listing it the page would raise. The owner must choose one predicate per class (for example `converts` for this class) or let one predicate span several classes.
  The registration note says exactly what each choice changes. Nothing was changed.

---

## 6. Class decisions of SOP 0c, as read from the code (DRAFT, owner to confirm)

| Item | Finding | Draft decision |
| --- | --- | --- |
| `QUANTITY_KINDS['endpoint_conversion']`, `CRITERIA_BY_TYPE` | Five kinds; criteria `COMMON_CRITERIA` + endpoint_alignment, conversion_denominator, product_identity. `product_identity` optional except for `endpoint_amount`; `conversion_denominator` optional for `endpoint_amount`, `completion_time`, `completion_time_ratio`. | Use as is. Every converter fills the effect kind it states and selects every criterion section 2 maps. |
| `QUALITATIVE_STATEMENT` | Binding wording. | No new values: `interaction_detected` reads "conversion detected", `interaction_not_detected` "conversion not detected", `interaction_not_stated` "conversion not stated". |
| `ROLE`, `IMMOBILIZATION_SIDES`, `ROW_DEPENDENCE_KEYS` | `analyte`, `immobilized`, `surface`. | Dependence keys: enzyme preparation -> `analyte_preparation_ref`; `immobilized_preparation_ref` None; `surface_ref` None; `dataset_ref` as extracted. Reasoning: no type here immobilises the enzyme or uses a surface; the substrate and the second enzyme or reagent are not enzyme preparations. Two results from one enzyme preparation or one dataset are dependent. |
| Direction | `literature_direction` is nM binding only. | A separate class-scoped function (section 4), written. |
| Pooling | `NOT_POOLED_CLASSES = ('activity_rate',)`. | Add this class (reason in section 4). |
| Stated-in-words strength | `stated_strength` counts only anchored types and `activity_rate`. | Add this class (registration note 1c). |
| Hypothesis value type | `catalyzes` hypotheses carry a reaction `term_ref`; `claim_of_hypothesis` accepts `term_ref` and `reference`. | Partner null for a reaction term (as built for activity). No patch. |
| Units of the sheet | No percent; `fold` only for `rate_ratio`; time units not all aliased for variances. | The converter converts to the anchor unit by an exact factor (section 2). |
| Which result belongs to this class | One paper can give a rate and an end point from the same data. | One quantity per result; a result states the end point quantity or it is activity_rate (opening paragraph). |

---

## 7. What is still open (questions for the owner)

1. **Predicate.** `catalyzes` is already the activity class's, and the page needs one class per predicate. Do you want a second word for this class (for example `converts`), or one predicate for several classes?
2. **The list.** Are these ten protocols right? Should `endpoint_time_course_completion` be a type or only a way of stating a time inside the other nine types? Is `endpoint_gas_evolution` wanted, or does gas belong with the detector types (GC) of the others?
3. **Substrate disappearance.** A conversion measured only as substrate loss (no product seen) is weaker evidence than product seen. As built the sheet makes `product_identity` optional for fractions. Should it be required for every kind of this class?
4. **Bounded times.** "More than 18 hours" and "less than 10 minutes" are bounds. The direction function raises on a bound as the effect. Should a bound be read at its limit (a lower bound on the time ratio supports at least that much)?
5. **The numbers.** Every end in section 4 is from memory and not verified. In particular: is 2 percent a fair noise end for a net conversion, and is 24 hours the right noise end for a completion time? Is an absolute product amount worth keeping as an effect at all, given that it depends on the loading?
6. **Fractions on a log scale.** A conversion from 5 to 10 percent counts as much as from 45 to 90 percent. Is that what you want, or should the scale be linear for fractions?
7. **Where the line to `activity_rate` falls.** A time course read for a slope is activity; the same data read for "share converted after 24 h" is this class. Is one-quantity-per-result the rule you want when one paper gives both?
8. **Unknown weights.** Per-type and per-criterion unknown weights (`WEIGHT_UNKNOWN_BY_TYPE`, `WEIGHT_UNKNOWN_BY_CRITERION`) are not drafted here; the builder of each type decides them with the SOP questions. Fine to leave to the second wave?
9. **Real paragraphs.** None found yet for any type. HFP (PMC12051542), CysQ (PMC2711008) and QueF (PMC555470) are the candidates from older material; their text and licences were not checked here.
10. **Whole-cell and extract conversions** ("resting cells converted 80 percent of the substrate in 24 h"): kept out as a context fact on the ten types. Is that right, or is it a type?
11. **Cell-free versus bound.** Immobilised enzymes (an enzyme on beads or a column) would change the dependence keys. None of the ten types does this today; say if you want one.
