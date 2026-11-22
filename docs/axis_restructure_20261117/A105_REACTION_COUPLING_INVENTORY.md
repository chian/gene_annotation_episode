# A105 `reaction_coupling` experiment inventory (SOP step 0, DRAFT for the owner to correct)

Written 2026-11-22 under `A105_EXPERIMENT_SOP.md` step 0, by reading only. Nothing was run, nothing was committed, and no existing file was edited. The files written are this one,
`G/literature_reaction_coupling_direction.py` and `runs/a105_class_drafts/registration/CLASS_reaction_coupling.md` (G = `gene_annotation_episode/episodic_workflow/episode_support/literature/grading/experimental_activity_evidence`,
F = `.../literature/forms/experimental_activity_evidence`).

**Status: DRAFT for the owner to correct.** The owner has not supplied a `reaction_coupling` list. Following SOP 0a item 2, the list below is drafted from the sources found plus domain knowledge. **Nothing here is owner-confirmed.**
It is one entry per protocol that can be reapplied to anything (a way of measuring), not per paper. Every number in sections 3 and 4 is `EXPERT_REVIEW`, owner to confirm, and every literature figure is "from memory, not verified".
No generic judgement formula is proposed: the per-criterion curves are researched per type by its builder (SOP step 3); section 4 gives only the class's direction and strength scale ends.

---

## 1. Sources searched and what was found

| Place | Found | Used for |
| --- | --- | --- |
| `docs/axis_restructure_20261117/A105_EXPERIMENT_SOP.md`, `A105_ACTIVITY_RATE_INVENTORY.md` | The protocol, the template and the model inventory. | Structure. |
| `G/literature_assay_grading.py` | `QUANTITY_KINDS['reaction_coupling']` = `productive_fraction`, `stoichiometric_ratio`, `balance_residual`. `CRITERIA_BY_TYPE['reaction_coupling']` = the nine `COMMON_CRITERIA` + `product_identity`, `stoichiometry`, `matched_windows`, `reporter_specificity`. Questions: product_identity "Is the claimed product chemically identified rather than inferred from substrate or reporter disappearance?"; stoichiometry "Are reaction coefficients and productive-use normalization supported for the claimed reaction?"; matched_windows "Do product and reporter measurements refer to compatible reaction windows, preparations and normalization?"; reporter_specificity "Are reporter chemistry, coupling capacity and side consumption compatible with the claimed productive flux?". Units: `productive_fraction` and `stoichiometric_ratio` take `fraction` or `dimensionless` only; `balance_residual` takes amounts only (M, mM, uM, nM, mol, mmol, umol, nmol, pmol, molecules, count, mg, ug, ng). `_required_criteria` has no optional criterion for this class. | The class core (section 2), the criteria maps (section 3), the misfits (registration note section 3). |
| `G/literature_row_contract.py`, `literature_page_update.py`, `literature_relevance.py`, `literature_row.py` | `CLAIM_PREDICATES_BY_CLASS` holds `ligand_binding` and `activity_rate` only. `class_of_predicate` needs exactly one class per predicate. `stated_strength` counts only `activity_rate` and the anchored binding types as "can report a measured effect". `NOT_POOLED_CLASSES = ('activity_rate',)`. | Predicate, direction, pooling (sections 4 to 6). |
| `research/experimental_scoring_review_2026-10-23/template_a105_reactions_001/01_csid_lhgo_001.md` (CsiD/LhgO, PMC6265302) | Defines productive coupling q = (net moles of chemically identified L2HG) / (net moles of O2 consumed), both over the same interval, expected 1:1; values beyond stoichiometric bounds are diagnostics, not clipped; O2 uptake can include uncoupled co-substrate oxidation; neither q nor a number was populated by the paper text. | `coupling_oxygen_product`; the "do not clip" note. |
| `.../template_a105_reactions_001/07_quef_2005_001.md` (QueF, PMC555470) | NADPH absorbance loss at 334/340/365 nm or HPLC; product preQ1 by HPLC co-elution, UV and NMR; four-electron nitrile-to-amine reaction, accounting predicts 2 NADPH per product; synthetic q = 2 x 45 / 100 = 0.90; cofactor-limited attainable yield Y = product / min(initial substrate, initial NADPH / 2) (50 percent at equal 0.5 mM substrate and NADPH). | `coupling_cofactor_product`, `coupling_limiting_reagent`; the coefficient in the productive fraction. |
| `verification/biochemical_fourteen_graders_319/REPORT.md`, entry 9; `episode_support/literature/inputs/.../literature_product_coupling_inputs.py`, `.../calculations/.../literature_product_coupling_calculations.py` (headers and schemas only); `verification/a105_sheet_reader_inventory_315/SHEETS.tsv` row 26 "Product and reporter coupling" | The old coupling reader/calculator: P450cam camphor hydroxylation against NADH oxidation, WT and mutants; product by chromatography and MS against authentic 5-exo-hydroxycamphor, NADH loss at 340 nm. Roles `product`, `cofactor`, `reported_coupling`; components `product_per_cofactor` (P/H), `productive_fraction` (nu x P/H, nu = cofactor per product), `calculated_coupling_percent` (100 x nu x P/H), `reported_coupling_percent`, `displayed_coupling_difference_pp`, variance by first-order propagation. Physical interpretation needs the same molecule, preparation, normalization and conditions and a chemically identified product; unknown links give conditional arithmetic only. | The record quantities, the productive-fraction definition, the matched-window facts. |
| `G/tests/test_literature_assay_grading_primary.py` (lines 125 to 150, `coupling_example`) | An existing reaction_coupling assessment: kind `stoichiometric_ratio`, reported product per NADH of a T252N mutant; `product_identity` supported, `matched_windows` unknown because product conditions (10 to 30 min) and cofactor conditions (steady-state kinetic experiments) differ. | A concrete case of the matched-windows criterion. |
| `.../molecular_measurement/summary.md` | Cases: CsiD uncoupled O2 uptake; HFP one-pot assay (staged terminal output cannot isolate every step); cofactor conversion without the proposed productive reaction (EUBREC2651, QueF-L, YadB: missing glutamate vs phosphate release, a covalent adduct instead of product); reductant carry-over or artificial mediator bypass in HydABC, MvhHdr, Bcd/Etf, NfnAB with "limiting-substrate stoichiometry". | Controls and the `reporter_specificity` side-consumption facts. |
| `.../a105_optical_case_031/FINDINGS.md` (Bcd/EtfAB, PMC2223550) | NADH 340 nm rate and H2 formation in one experiment; methyl viologen drops the H2 rate from 5 to 0.02 and the NADH rate from 7 to 5 umol/min/mg. | `coupling_electron_balance`, `coupling_cofactor_product` past work. |
| `.../template_a105_reactions_001/` FrsA (ADH/NADH coupled assay, coupling enzyme checked by adding acetaldehyde), CysQ (AMP by MS with internal standard) | Reporter-capacity check; product by MS. | `reporter_specificity` facts. |
| `docs/axis_restructure_20261117/INVESTIGATION_FINDING_FEATURES_a105.md` (lines 29, 110, 127) | Confirms the class's sheet name, kinds and criteria; 13 criteria, none optional. | Consistency. |
| `docs/axis_restructure_20261117/EXPERIMENT_INVENTORY_SEARCH.md`, `..._SEARCH_2.md`, `A105_SCORING_DESIGN.md` (grep for coupling) | No per-technique coupling list. "Product coupling" is one of about 35 per-measurement-kind code modules. | Nothing more. |
| `episode_support/grading/evolutionary_history_evidence/characterization.py` | A104 maps `catalyzes` to {activity_rate, endpoint_conversion, product_distribution, reaction_coupling}. | The predicate (section 5). |
| Codex sessions | **Not opened** (task rule). The October 150-paper inventory remains unfound. | Nothing. |
| Public literature (nitrogenase ATP/2e- ratios, P/O ratios, H2O2 uncoupling of P450s, 18O2 labelling) | Not searched; only recalled. | Everything marked "from memory, not verified". |

**Conclusion:** no per-technique list for this class exists in the places searched. The prior work is organised by calculation (product per cofactor, productive fraction, reported coupling percent). Only one cofactor-product case (P450cam) and the
QueF and CsiD proposals describe the measurement; the other protocols below are from domain knowledge.

---

## 2. What all `reaction_coupling` types share (the class core)

**What is measured:** two things in the same reaction, and the link between them: how much of one is consumed or formed per unit of the other. The "consumed" side is a cofactor (NAD(P)H, ATP, O2, electrons from a donor) or a substrate, the "formed" side is the claimed product, or a
by-product (H2O2, water). The link is a productive fraction (share of the consumed partner that ends in the claimed product, with the reaction's coefficient applied), a stoichiometric ratio (product per partner consumed, no coefficient applied), or a balance residual (what is left unaccounted for).

**Evidences (sheet):** `reaction_coupling` (predicate `catalyzes`, section 5).

**Native quantities common to every type** (each a record operand, `point` or `unavailable` with a reason, never 0, never omitted):

| Quantity | Unit vocabulary | Meaning |
| --- | --- | --- |
| `productive_fraction` | fraction, percent | Share of the consumed partner that ends in the claimed product, as stated. Percent is converted exactly (divide by 100). |
| `stoichiometric_ratio` | mol_per_mol, fraction | Moles of product per mole of consumed partner, as stated (or the reverse if the paper states cofactor per product; then `ratio_direction` says so). |
| `stoichiometric_coefficient` | mol_per_mol | The paper's own reaction account: moles of consumed partner per mole of product (for example 1 for a P450 monooxygenase and NADPH, 2 for QueF). Without it a ratio is not a fraction. |
| `product_formed` and `partner_consumed` (amounts) | uM, mM, nM, umol, nmol, pmol, mol | Net amounts over the same window (net of the control). |
| `product_rate` and `partner_rate` (rates) | umol/min, nmol/min, pmol/min, nmol/s, uM/min, uM/s, nmol/min/mg, umol/min/mg, pmol/min/mg | Net rates of each side, in the class rate vocabulary of `activity_rate`. |
| `balance_residual` | the amount units above | Amount not accounted for (consumed minus accounted). |
| `window` | s, min, h | Start and end (or length) of the interval each side was measured over. |
| `effect_spread` and `spread_kind` | of the ratio, in its unit | SD, SEM, CI, fit SE, unstated "±" (an unstated "±" stays unstated). The spread of the RATIO, not of the parts. |
| `replicate_count`, `replicate_kind` | count; technical repeats, independent reactions, independent preparations | No cut-off. |
| `detection_limit` | the amount units | For a product not detected. |
| Identity block (automatic) | | `target_id` (the enzyme as written), `partner_id` (the substrate as written), `temperature_c`, pH. |

**Facts common to every type** (`yes`, `no`, `unknown`, `not_applicable`; silence is `unknown`, never `no`): product chemically identified against an authentic standard; product calibrated with a standard series; consumed side calibrated; both sides measured in the same reaction mixture;
both sides measured over the same time window; both sides from the same enzyme preparation; no-enzyme control done; no-substrate (substrate-independent partner consumption) control done and subtracted; inactive-enzyme (heat or catalytic mutant) control done; the stoichiometric coefficient stated; purified enzyme
(versus extract); native substrate and cofactor (versus surrogate); independent replicates.

**Class-wide mapping of what the sheet criteria read** (a type adds its own members, section 3):

| Sheet criterion | Core members (the types add more) |
| --- | --- |
| `measurement_identity` | same enzyme preparation, same reaction mixture, units and denominator stated for both sides. |
| `calibration_applicability` | product standard series, consumed-side calibration (extinction coefficient and path, electrode calibration, standard curve), stated recovery. |
| `matrix_interference` | detector interference by the other reaction components or by the test compound (cofactor and product absorbing together, reductants in a peroxide assay). |
| `background_alternatives` | no-enzyme and no-substrate controls (substrate-independent partner consumption, spontaneous product). |
| `attribution_supported` | inactive-enzyme control; contaminating activity excluded. |
| `product_identity` | authentic standard and a second identification (mass, NMR, co-elution plus spectrum). |
| `stoichiometry` | the coefficient stated; the productive-use normalization of the ratio. |
| `matched_windows` | same vessel, same interval, same preparation, same normalization of the two sides. |
| `reporter_specificity` | reporter chemistry, coupling capacity, side consumption (the partner used by something other than the claimed reaction). `not_applicable` for a type with no reporter. |
| `assertion_relevance` | native substrate and cofactor, the claimed reaction. |
| `condition_scope` | pH, temperature, cofactor, purified enzyme or extract. |
| `variance_correspondence` | the spread is the ratio's own (propagated from both sides), not one side's. |
| `sampling_basis` | replicates independent (count only). |

**Certainty:** quantitative types: a measured link (productive fraction or ratio) read against its own spread. A result stated in words alone ("the reaction was coupled", "no product formed") is the qualitative path (section 4).

**Readers that supply it (all types):** text paragraphs (Methods and Results) and tables. Time courses, gels and chromatograms are figures and are unavailable today (SOP Known gaps).

**Owner biochemical questions mapped to the core:** sensitivity (`detection_limit`, signal over the control), kinetic parameters (not an output of this class), heating (`temperature_c`), in vitro or in vivo (purified-enzyme fact), realism of the chemistry (native-substrate fact, pH), expected signal in messy samples (matrix fact,
recovery), spontaneous reaction (no-enzyme control).

---

## 3. The draft experiment list (8 types)

Type ids start with `coupling_`, are snake_case and are none of the reserved ids.

| # | Type id | Experiment | Family |
| --- | --- | --- | --- |
| 1 | `coupling_cofactor_product` | Cofactor consumption paired with identified product (NAD(P)H loss against product by HPLC, GC or MS) | Optical or separation, paired rates |
| 2 | `coupling_oxygen_product` | Oxygen uptake paired with identified product | Electrode plus separation, paired rates |
| 3 | `coupling_uncoupling_byproduct` | Uncoupling by by-product: peroxide or superoxide formed per cofactor consumed | Optical, by-product |
| 4 | `coupling_atp_product` | Nucleotide hydrolysis paired with the product it drives | Optical or isotope, paired rates |
| 5 | `coupling_electron_balance` | Electrons delivered against electrons recovered in product (reductant titration, charge, faradaic efficiency) | Electron accounting |
| 6 | `coupling_mass_balance` | Substrate consumed against the sum of identified products (carbon, nitrogen, mass or molar closure) | Separation or NMR, closure |
| 7 | `coupling_limiting_reagent` | Reaction taken to completion with one limiting reagent: product (or equivalents consumed) per equivalent of limiting reagent | Endpoint stoichiometry |
| 8 | `coupling_isotope_label` | Isotope-label flow (18O2, H2 18O, 13C or 15N or double radiolabel): share of the product that carries the label of the claimed source | Isotope, mass spectrometry or counting |

**Considered and not listed** (with the reason):

- *Single-sided measurements* (only product, or only cofactor consumption): these are `activity_rate` or `endpoint_conversion`; this class needs both sides in the same reaction.
- *Reporter-capacity checks of a coupled-enzyme rate assay* (FrsA adding the intermediate): a control of `activity_rate`/`coupled_enzyme`, recorded there; here it is the `reporter_specificity` criterion of each type.
- *Proton or ion per electron stoichiometry* (H+/e-, P/O with a membrane): the second quantity is a transported amount, so it belongs to `transport_response`. Ask the owner whether the P/O ratio (ATP made per O consumed) goes here (type 4 or 2) or there.
- *Product ratios of a branched reaction* (product spectrum, equilibrium fractions): `product_distribution`.
- *Calorimetric enthalpy balance*: rare; add if a real paper needs it.
- *Quantum or photon yield* (photoconversion per photon absorbed): a coupling of product to light; not drafted, ask the owner if wanted.

### 3.1 `coupling_cofactor_product`

```text
experiment:            cofactor consumption paired with identified product      (type id coupling_cofactor_product)
family:                paired rates: optical or chromatographic consumed side, separation or MS product side
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  cofactor loss: absorbance slope or change at 340 nm (dA/min, A) or NAD(P)H amount (nmol, uM) or rate
                       (nmol/min, nmol/min/mg); product amount (uM, nmol) and rate; stated coupling (percent or fraction);
                       product per cofactor (mol/mol); cofactor per product coefficient (mol/mol); extinction coefficient
                       (mM^-1 cm^-1) and path length (cm); wavelength (nm)
controls required:     no-substrate NAD(P)H oxidation (uncoupled turnover of the enzyme without substrate) and no-enzyme
                       oxidation, both subtracted; authentic product standard with a standard series; product and cofactor
                       taken from the same reaction mixture and interval; catalytic-mutant control; by-product (H2O2) accounted
                       or stated unmeasured
noise expectations:    spread of the ratio, not of one side; blank slope beside the test slope; calibration recovery of a known
                       product amount; absorbance in the linear range of the detector; product and cofactor each with its own
                       spread (the ratio's spread is propagated from both)
replicates needed:     count + kind (technical repeats, independent reactions, independent preparations), no cut-off
certainty:             quantitative: productive fraction (coefficient x product / cofactor) or the bare ratio; qualitative only
                       "coupled" or "uncoupled" in words
readers that supply it:text (Methods: wavelength, coefficient, conditions; Results: coupling), tables (coupling tables per variant);
                       traces are figures
past work (where):     P450cam camphor hydroxylation vs NADH oxidation, WT and mutants (verification 319 entry 9; the old
                       product-coupling reader and calculator); T252N product per NADH assessment in
                       test_literature_assay_grading_primary.py; QueF 2 NADPH per product (PMC555470, template_a105_reactions_001/07);
                       Bcd/Etf NADH vs H2 (PMC2223550, a105_optical_case_031)
record fields:         productive_fraction, stoichiometric_ratio, stoichiometric_coefficient, cofactor_consumed, product_formed,
                       cofactor_rate, product_rate, window (cofactor and product), extinction_coefficient, wavelength, spread, spread_kind,
                       replicate_count, detection_limit; facts: product_identified, product_calibrated, same_mixture, same_window,
                       same_preparation, no_substrate_control, no_enzyme_control, mutant_control, background_subtracted,
                       byproduct_accounted, independent_replicates, purified_enzyme, native_substrate
criteria -> sheet:     product_identity <- product_identified, product_calibrated;
                       stoichiometry <- stoichiometric_coefficient (stated, and agrees with product/cofactor chemistry);
                       matched_windows <- same_mixture, same_window, same_preparation (+ the overlap of the two windows as a number);
                       reporter_specificity <- no_substrate_control (uncoupled cofactor oxidation), byproduct_accounted, absorbance range;
                       calibration_applicability <- extinction_coefficient stated, absorbance range, calibration recovery;
                       background_alternatives <- no_enzyme_control, background_subtracted;
                       attribution_supported <- mutant_control; measurement_identity <- same_preparation, units;
                       assertion_relevance <- native_substrate; condition_scope <- purified_enzyme; sampling_basis <- replicates
```

### 3.2 `coupling_oxygen_product`

```text
experiment:            oxygen uptake paired with identified product             (type id coupling_oxygen_product)
family:                electrode (Clark, optode, Oroboros) plus separation or NMR for the product
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  O2 consumed (nmol, umol, uM) and rate (nmol/min, umol/min/mg, uM/min); product amount and rate; product per
                       O2 (mol/mol); expected O2 per product (1 for a monooxygenase, 2 for a dioxygenase; mol/mol); air-saturated
                       O2 concentration at the temperature (uM) used for calibration
controls required:     electrode calibration (air-saturated and zero O2); no-enzyme and no-substrate O2 drift; catalase or peroxide
                       accounting (O2 returned by catalase, H2O2 formed); same vessel and interval for the product sample;
                       authentic product standard
noise expectations:    spread of the ratio; drift beside the test rate; O2 consumption large enough to be measured against the
                       drift; calibration stated or not
replicates needed:     count + kind
certainty:             quantitative productive fraction or product per O2; CsiD: O2 uptake alone can be uncoupled chemistry, so
                       a ratio without product identity is weak
readers that supply it:text, tables
past work (where):     CsiD/LhgO Clark electrode and NMR/LC-MS (PMC6265302; 01_csid_lhgo_001.md defines q = product / O2; the
                       paper's text does not populate q; 53 +/- 3 umol/min/mg O2 rate, the ± kind unstated)
record fields:         productive_fraction, stoichiometric_ratio, stoichiometric_coefficient (O2 per product), oxygen_consumed, product_formed,
                       oxygen_rate, product_rate, window, air_saturated_oxygen (uM), spread, spread_kind, replicate_count;
                       facts: electrode_calibrated, drift_subtracted, no_substrate_control, no_enzyme_control, peroxide_accounted,
                       product_identified, product_calibrated, same_vessel, same_window, independent_replicates, purified_enzyme
criteria -> sheet:     calibration_applicability <- electrode_calibrated, air_saturated_oxygen stated;
                       background_alternatives <- drift_subtracted, no_enzyme_control, no_substrate_control;
                       reporter_specificity <- peroxide_accounted (O2 used by something else), no_substrate_control;
                       product_identity <- product_identified, product_calibrated; stoichiometry <- stoichiometric_coefficient;
                       matched_windows <- same_vessel, same_window; other criteria as the core
```

### 3.3 `coupling_uncoupling_byproduct`

```text
experiment:            by-product (peroxide or superoxide) formed per cofactor consumed     (type id coupling_uncoupling_byproduct)
family:                optical by-product assay (Amplex Red with HRP, ferrous oxidation with xylenol orange, catalase-O2 return,
                       cytochrome c reduction inhibited by SOD) alongside cofactor consumption
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  H2O2 (or O2-) formed (uM, nmol) and rate; cofactor consumed (uM, nmol) and rate; uncoupled fraction (fraction,
                       percent: by-product over cofactor); productive fraction by difference (1 minus uncoupled) when the paper
                       states it; stoichiometric coefficient of the by-product (mol per mol cofactor)
controls required:     no-enzyme and no-substrate by-product formation; catalase (peroxide signal removed) and SOD (superoxide
                       signal removed) controls; reporter control with no peroxidase; test for reductants that give a signal (DTT,
                       ascorbate, thiols); standard series of H2O2 in the reaction buffer; cofactor measured in the same mixture
noise expectations:    spread of the fraction; signal over the no-enzyme blank; standard range; peroxide not consumed by the
                       enzyme or the buffer during the window
replicates needed:     count + kind
certainty:             quantitative, but a productive fraction obtained by difference does not identify the product: it is lower
                       evidence unless the product is also measured (the type then reads as type 1 with a by-product measure)
readers that supply it:text, tables
past work (where):     none found in the places searched; the CsiD uncoupled O2 uptake note and the P450 uncoupling literature
                       (H2O2, superoxide and water as the three uncoupled outcomes; Denisov et al. 2005 Chem Rev, from memory)
record fields:         uncoupled_fraction, productive_fraction, stoichiometric_ratio (by-product per cofactor), byproduct_formed,
                       cofactor_consumed, window, spread, spread_kind, replicate_count; facts: catalase_control, sod_control,
                       reductant_interference_excluded, standard_series, no_enzyme_control, no_substrate_control, same_mixture,
                       same_window, product_measured_too, independent_replicates
criteria -> sheet:     reporter_specificity <- catalase_control, sod_control, reductant_interference_excluded (the by-product assay is the
                       reporter here); calibration_applicability <- standard_series; matrix_interference <- reductant_interference_excluded;
                       product_identity <- product_measured_too (without it the criterion is unknown or conflicting);
                       background_alternatives <- no_enzyme_control, no_substrate_control; matched_windows <- same_mixture, same_window;
                       stoichiometry <- the by-product coefficient stated
```

### 3.4 `coupling_atp_product`

```text
experiment:            nucleotide hydrolysis paired with the product it drives      (type id coupling_atp_product)
family:                paired rates: ATP or GTP hydrolysis (malachite green phosphate, pyruvate kinase/LDH NADH loss, [gamma-32P]
                       release, HPLC of ADP) against product (phosphorylated or ligated product, ammonia, translocated
                       substrate counted as product only if the paper states it so)
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  nucleotide hydrolyzed (nmol, umol, uM) and rate; product formed and rate; nucleotides per product (mol/mol); the
                       basal ATPase rate with no substrate or partner (rate unit); stated coupling (percent or fraction)
controls required:     basal (partner-free or substrate-free) ATPase rate measured and subtracted or reported; free phosphate
                       contamination of the nucleotide stock (blank); no-enzyme hydrolysis; regenerating system stated (it hides
                       ADP); product identified and calibrated; both sides from the same mixture and interval
noise expectations:    spread of the ratio; blank phosphate beside the test phosphate; the hydrolysis not exceeding the linear range
                       of the phosphate or NADH reporter
replicates needed:     count + kind
certainty:             quantitative nucleotides per product (a ratio above 1 is a normal result here: it is the cost, not the
                       fraction); the converter turns it to a productive fraction with the stated coefficient or leaves it a bare
                       ratio
readers that supply it:text, tables
past work (where):     none found in the places searched; nitrogenase ATP per 2 electrons and per H2 (about 4 to 5 ATP per 2 e- under
                       turnover, Hageman and Burris 1978, from memory, not verified); AAA+ and helicase ATP-per-step numbers
                       (from memory)
record fields:         productive_fraction, stoichiometric_ratio, stoichiometric_coefficient (nucleotides per product), nucleotide_hydrolyzed,
                       product_formed, nucleotide_rate, product_rate, basal_rate, window, spread, spread_kind, replicate_count;
                       facts: basal_rate_subtracted, phosphate_blank_done, no_enzyme_control, regeneration_system_stated, product_identified,
                       product_calibrated, same_mixture, same_window, independent_replicates
criteria -> sheet:     reporter_specificity <- basal_rate_subtracted (nucleotide use by something else), regeneration_system_stated, phosphate range;
                       background_alternatives <- phosphate_blank_done, no_enzyme_control; matched_windows <- same_mixture, same_window;
                       stoichiometry <- stoichiometric_coefficient; product_identity <- product_identified, product_calibrated
boundary note:         ATP use that drives transport across a membrane is transport_response; the owner should rule where the P/O ratio goes
```

### 3.5 `coupling_electron_balance`

```text
experiment:            electrons delivered against electrons recovered in product        (type id coupling_electron_balance)
family:                electron accounting (reductant or oxidant titration, coulometry or bulk electrolysis charge, faradaic
                       efficiency, equivalents of reduced donor consumed against H2 or reduced product formed)
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  electrons delivered (umol of electron equivalents; coulomb or mC converted by the Faraday constant, an exact
                       definition) ; product amount (umol, nmol; H2 by gas chromatography); electrons per product (mol/mol);
                       faradaic or electron-recovery efficiency (percent, fraction)
controls required:     background charge or donor oxidation with no enzyme and with no substrate; product calibrated (gas standard
                       series for H2); electrons per product stated; gas-tight vessel or headspace accounting; donor oxidation not
                       by oxygen or another acceptor (anaerobic control)
noise expectations:    spread of the efficiency; background charge beside the test charge; headspace sampling loss
replicates needed:     count + kind
certainty:             quantitative productive fraction (electrons in product over electrons delivered)
readers that supply it:text, tables
past work (where):     Bcd/EtfAB NADH oxidation against H2 formation and the methyl viologen bypass (PMC2223550); HydABC, MvhHdr and
                       NfnAB electron bifurcation and carry-over cases (molecular_measurement summary: reductant carry-over or
                       mediator bypass); protein-film voltammetry activity itself is `activity_rate`
record fields:         productive_fraction, stoichiometric_ratio, stoichiometric_coefficient (electrons per product), electrons_delivered,
                       product_formed, charge (C, mC), window, spread, spread_kind, replicate_count; facts: background_charge_subtracted,
                       gas_standard_series, headspace_accounted, anaerobic_control, mediator_bypass_excluded, no_enzyme_control,
                       product_identified, same_window, independent_replicates
criteria -> sheet:     stoichiometry <- stoichiometric_coefficient (electrons per product stated); background_alternatives <-
                       background_charge_subtracted, no_enzyme_control; reporter_specificity <- mediator_bypass_excluded, anaerobic_control
                       (side consumption of electrons); calibration_applicability <- gas_standard_series; matched_windows <- same_window;
                       product_identity <- product_identified
```

### 3.6 `coupling_mass_balance`

```text
experiment:            substrate consumed against the sum of identified products     (type id coupling_mass_balance)
family:                closure: HPLC, GC, MS or NMR of the substrate and every expected product at matched time points (carbon,
                       nitrogen, mass or molar balance)
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  substrate consumed (uM, nmol); each identified product (uM, nmol); recovery or closure (percent, fraction);
                       balance residual (the amount units); atoms per molecule (count) when the balance is carbon or nitrogen
controls required:     internal standard and calibration for each species; zero-time sample; no-enzyme sample; all expected products
                       quantified (or the unquantified remainder named as residual); volatile or insoluble loss excluded
noise expectations:    spread of the closure; recovery of the total at zero time (the method's own closure with no reaction); detection
                       limits of the minor species
replicates needed:     count + kind
certainty:             quantitative; closure above the stoichiometric bound (above 1) is a diagnostic, not a clipped value
readers that supply it:text, tables
past work (where):     HFP riboflavin assay: one-pot staged output cannot isolate every step and an input is destroyed (PMC12051542,
                       molecular_measurement spec_aquifex_hfp_coupling_contamination); QueF cofactor-limited attainable yield
                       (PMC555470); CysQ AMP by MS with internal standard (PMC2711008)
boundary note:         the fractions among products alone (a product spectrum) are product_distribution; closure needs the consumed
                       substrate beside the products
record fields:         productive_fraction (accounted for over consumed), balance_residual, substrate_consumed, product_formed (per species),
                       atoms_per_molecule, window, spread, spread_kind, replicate_count, detection_limit; facts: internal_standard,
                       each_species_calibrated, zero_time_sample, no_enzyme_control, all_products_quantified, volatile_loss_excluded,
                       same_mixture, same_window, independent_replicates
criteria -> sheet:     calibration_applicability <- internal_standard, each_species_calibrated; product_identity <- each product identified;
                       stoichiometry <- atoms_per_molecule, the reaction equation stated; matched_windows <- same_mixture, same_window;
                       attribution_supported <- all_products_quantified (an unmeasured remainder is the residual); reporter_specificity <-
                       not_applicable (no reporter); background_alternatives <- no_enzyme_control, zero_time_sample
```

### 3.7 `coupling_limiting_reagent`

```text
experiment:            reaction taken to completion with one limiting reagent        (type id coupling_limiting_reagent)
family:                endpoint stoichiometry (limiting cofactor or co-substrate, stepwise titration or one limiting dose)
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  limiting reagent added (uM, nmol); product formed at completion (uM, nmol); equivalents of limiting reagent per
                       product (mol/mol); yield over the limiting reagent (percent, fraction)
controls required:     completion shown (no further change with more enzyme or more time, or the limiting reagent measured as fully
                       consumed, for example NADPH absorbance at zero); the other reagents in excess; no regeneration of the limiting
                       reagent; product calibrated and identified; limiting reagent concentration verified (absorbance for NADPH)
noise expectations:    spread of the equivalents; error of the pipetted limiting amount; product calibration recovery
replicates needed:     count + kind; a titration shows several points
certainty:             quantitative equivalents per product, from which the productive fraction is the coefficient times the yield
readers that supply it:text, tables
past work (where):     QueF cofactor-limited yield Y = product / min(substrate, NADPH / 2) with 0.5 mM each giving at most 50 percent
                       (PMC555470); anaerobic reductive titration of flavoproteins (from memory, not verified)
record fields:         productive_fraction, stoichiometric_ratio, stoichiometric_coefficient, limiting_amount, product_formed, completion_time,
                       titration_points (count), spread, spread_kind, replicate_count; facts: completion_shown, limiting_verified_consumed,
                       others_in_excess, no_regeneration, product_identified, product_calibrated, independent_replicates
criteria -> sheet:     stoichiometry <- stoichiometric_coefficient, others_in_excess, no_regeneration; matched_windows <- completion_shown (one
                       endpoint for both sides); calibration_applicability <- limiting_verified_consumed, product_calibrated; product_identity <-
                       product_identified; reporter_specificity <- not_applicable (or the verifying reporter, if one is used);
                       sampling_basis <- replicates, titration_points
```

### 3.8 `coupling_isotope_label`

```text
experiment:            isotope-label flow into the product                           (type id coupling_isotope_label)
family:                isotope with mass spectrometry or counting (18O2 and H2 18O incorporation, 13C or 15N transfer, 14C-substrate and
                       3H-cofactor double-label counting)
evidences (sheet):     reaction_coupling                                        (predicate: catalyzes)
native outputs/units:  label incorporated into the product (percent, fraction of product molecules or atoms); atoms incorporated per
                       product (count); mass shift (Da, number); labelled substrate consumed and product formed (uM, nmol);
                       double-label ratio of counts (number, dimensionless)
controls required:     label purity stated; unlabelled-medium reaction; back-exchange or solvent-exchange control (H2 18O exchange of
                       the product or the substrate); product identified by the mass shift against an unlabelled standard; the same
                       preparation and window for the labelled and the unlabelled run
noise expectations:    spread of the incorporation; natural-abundance correction stated; mass resolution of the shift
replicates needed:     count + kind
certainty:             quantitative share of the product atoms that came from the claimed source (read as a productive fraction of the
                       label); the most indirect of the eight, because the label shows origin and not the amount consumed
readers that supply it:text, tables; mass spectra are figures
past work (where):     none found in the places searched (18O2 labelling tells oxygenase from oxidase chemistry, from memory)
boundary note:         the owner may prefer to move this to product_distribution or endpoint_conversion (a label fraction is a share
                       of a product, not a link between two measured amounts)
record fields:         productive_fraction (label share), stoichiometric_ratio, atoms_incorporated, mass_shift, label_purity, substrate_consumed,
                       product_formed, window, spread, spread_kind, replicate_count; facts: unlabelled_control, back_exchange_control,
                       natural_abundance_corrected, product_identified_by_mass_shift, same_preparation, same_window, independent_replicates
criteria -> sheet:     product_identity <- product_identified_by_mass_shift; attribution_supported <- back_exchange_control, unlabelled_control;
                       calibration_applicability <- label_purity, natural_abundance_corrected; stoichiometry <- atoms_incorporated against the
                       reaction; matched_windows <- same_preparation, same_window; reporter_specificity <- not_applicable
```

---

## 4. Direction and strength for the class (code in `G/literature_reaction_coupling_direction.py`, constants in the registration note; DRAFT, owner to confirm)

Same paradigm as binding and activity (`literature_direction.py`, `literature_activity_direction.py`): a position on a log scale between a noise end and a strong end, a smooth S-curve, lowered by the stated spread.

```text
p = clip( (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), 0, 1 )      (LARGER is stronger)
s = (3 p^2 - 2 p^3) / (1 + r^2),    r = sd / e    (0 when no spread is stated)
log_ratio = QUALITATIVE_LOG_RATIO[type] * s
```

A stated link SUPPORTS by its graded strength `s`; `s == 0` (at or under the noise end) is neutral; a quantitative result never opposes. Controls, windows, the coefficient and the other sheet criteria lower the weight only, never the direction.

**Which stated quantity is the effect, its anchor unit, which way is stronger:**

| Quantity | Anchor unit | Larger or smaller | noise_end | strong_end | Reason (every number EXPERT_REVIEW, owner to confirm; literature "from memory, not verified") |
| --- | --- | --- | --- | --- | --- |
| `productive_fraction` | fraction | larger is stronger | 0.01 | 0.9 | noise_end: 1 percent, the floor of almost wholly uncoupled turnover and of background chemistry that makes some product without the enzyme. strong_end: 90 percent, the well-coupled end (P450cam with camphor near 100 percent; P450 BM3 with fatty acids about 60 to 90 percent; P450s with poor or non-native substrates often 1 to 30 percent: Denisov et al. 2005 Chem Rev 105:2253, from memory). A typical weak coupling of 10 percent sits at p = 0.51 (s about 0.5). |
| `stoichiometric_ratio` | fraction (mol per mol, no coefficient applied) | larger is stronger | 0.01 | 1.0 | noise_end as above. strong_end: one product per partner consumed, the usual coefficient. A reaction with a coefficient of 2 (QueF) reads 0.5 at full coupling and sits at p = 0.85 (s about 0.94), a small loss, which is why this quantity ranks after the productive fraction. A ratio above 1 is read at the strong end; it is a diagnostic for the criteria, not a clipped value. |
| `balance_residual` | amount | smaller is better closure | none | none | An amount has no common scale. A closure is stated as a productive fraction (accounted for over consumed); the residual itself goes to the `attributed_signal` and `total_signal` roles. |

**Order of preference when a record states several:** `productive_fraction` first, then `stoichiometric_ratio` (`COUPLING_EFFECT_ORDER`). Why: the productive fraction already has the reaction's own coefficient applied, so it answers the claimed reaction; the bare ratio does not know the coefficient and is read as one product per partner.

**A result stated in words alone:** the existing vocabulary is kept and READ for this class: `interaction_detected` = "coupled product formation detected", `interaction_not_detected` = "no product formed above the paper's own control or detection limit", `interaction_not_stated` = "not stated" (unknown, never opposition). Under the 2026-11-22 owner ruling
a stated detection or non-detection counts `QUALITATIVE_LOG_RATIO[type] * STATED_ONLY_STRENGTH` (0.25); this needs `stated_strength` to include this class (registration note 1c). A measured link at p above about 0.2 therefore counts more than the sentence.

**Pooling:** NOT pooled (registration note 1d). One result's effect is a productive fraction or a bare ratio, and different protocols measure different links; both carry the unit "fraction", so a pooled unit would pass the check and average numbers that do not mean the same thing. The row's pooled effect, variance and precision are null; direction, strength and weight are unaffected.

**Researched values per quantity for the builders' criteria curves** (starting points only; each builder researches its own method's values and makes each gradual, SOP step 3; none is a cut-off; `EXPERT_REVIEW`, from memory):

| Criterion read | Full agreement at | Falls to zero at | Reason |
| --- | --- | --- | --- |
| Substrate-independent partner consumption (no-substrate rate) as a share of the test partner rate | at or under 10 percent | 100 percent (the whole test rate is background) | a subtraction of a small background is accurate; as the background approaches the signal the net rate (and so the ratio) loses precision as 1 / (1 - share). Not applicable to the uncoupled turnover itself, which is the quantity of type 3. |
| Overlap of the product and partner windows (shared fraction of the shorter window) | complete overlap (the same aliquot and times) | no overlap | the sheet question is whether the windows are compatible; a product taken at 30 min against a rate from the first 2 min is a different window. |
| Reporter or coupling capacity over the rate measured | 10 times or more | 1 time (log scale) | a reporter at its capacity reports its own limit, not the flux; the usual excess for a coupled assay is 5 to 10 times (from memory; ask the activity builders for the same constant). |
| Calibration recovery of a known standard | 0.9 to 1.1 | 0.5 or 2 | over- and under-recovery both mislead the ratio. |
| Detector absorbance (type 1) | 0.1 to 1.5 | 3 | stray-light bias grows with absorbance; the same shape as `spectro_direct`. |
| Replicates | sqrt(n / 3) | not conflicting for a stated count | the cross-assay consistency rule 1 of the SOP. |

**Unknown weights:** per assay, decided by the SOP questions (is the readout absolute, is there a reference range if unstated, what does an unstated control do). A coupling ratio is an absolute (dimensionless) quantity, but each side needs its own calibration, so the draft expectation is a type default near 0.8, lower for `matched_windows` and `product_identity` (a ratio from sides that were not matched or a product that was not identified is uninterpretable); the builders write the chain.

---

## 5. Claim predicate (proposed `catalyzes`, owner to confirm)

- **Predicate:** `catalyzes`, listed for the class in `CLAIM_PREDICATES_BY_CLASS['reaction_coupling']`. A claim names molecules only: predicate, subject, partner. No threshold.
- **Not symmetric:** "E catalyzes S" is not "S catalyzes E". Do not add it to `SYMMETRIC_PREDICATES`.
- **Subject:** the enzyme (the record's `target_id`, the assayed protein as written). The target match needs it equal to the claim's subject.
- **Partner:** the substrate whose conversion is coupled to the consumed partner (the record's `partner_id`, as written, for example the camphor of the P450cam record). The cofactor (NADH, O2, ATP) is not the claim's partner; it is what the record measures against.
- **How a record's stated partner must agree:** the relevance function compares the normalized names. A claim with no partner is `relevant` (reason `claim_names_no_partner`). A record that states a partner equal to the claim's is `relevant`; a different one is `irrelevant` (`other_partner`) and stays off the row; a record that states no partner but has a measured effect is `unresolved` (`partner_not_stated`) and stays on the row.
  A record of another class does not test the predicate (`experiment_type_cannot_test_predicate`).
- **Real conflict, raised not patched:** `catalyzes` is already the predicate of `activity_rate` (and proposed for `endpoint_conversion` and `product_distribution`). `class_of_predicate` (used by the page's `internal_summary.py` to tell its leaves the sheet class) raises when a predicate belongs to more than one class; `_check_claims` and `relevance` already accept several. Either each class gets its own predicate (for this class a candidate such as `couples`, owner's choice), or the page is changed to hand a leaf the set of classes of the predicate. This draft keeps the owner's proposal and states the conflict.
- **Hypothesis value type:** `claim_of_hypothesis` accepts a `term_ref` or `reference` value. For a `term_ref` (a reaction term, as the existing A105 hypotheses carry) the claim's partner is null and the target alone decides, as for `activity_rate`; the substrate-specificity of the coupling is then not read. Same limit as in the activity inventory, section 5.

---

## 6. The class decisions of SOP step 0c, read from the code (decided in this draft, owner to confirm)

| Item | Finding | Draft decision |
| --- | --- | --- |
| `QUANTITY_KINDS['reaction_coupling']` and `CRITERIA_BY_TYPE` | Three kinds; thirteen criteria, none optional (`_required_criteria` has no branch for the class). | Use as they are. Converters fill `productive_fraction` or `stoichiometric_ratio` as the effect; the residual goes to `attributed_signal` / `total_signal`. A type with no reporter (6, 7, 8) gives `reporter_specificity` the status `not_applicable`; whether the sheet accepts that for a required criterion must be checked (registration note 3, item 1). |
| `QUALITATIVE_STATEMENT` | Binding wording. | Kept and read for the class (section 4). No contract change. |
| `ROLE`, `IMMOBILIZATION_SIDES`, `ROW_DEPENDENCE_KEYS` | Binding-flavoured. `ROW_DEPENDENCE_KEYS` = `analyte_preparation_ref`, `immobilized_preparation_ref`, `surface_ref`, `dataset_ref`. | The enzyme preparation to `analyte_preparation_ref`. `immobilized_preparation_ref` None and `surface_ref` None for all eight types (nothing is immobilized or on a surface; the electrode of type 5 is a way of delivering electrons, not a dependence unit; if the owner wants the electrode as a surface, `surface_ref` only for type 5). `dataset_ref` as the other classes. The two sides of one coupling measurement come from one preparation, so they are one dependence unit, not two. |
| Direction | `literature_direction` is nM-binding only. | A separate class-scoped function (section 4, code written). |
| `stated_strength` | Counts only activity_rate and anchored binding types. | Add `reaction_coupling` (registration note 1c). |
| Pooling | `NOT_POOLED_CLASSES` holds `activity_rate` only. | Add `reaction_coupling` (registration note 1d). |
| Hypothesis value type | `term_ref` or `reference` only. | As section 5. |
| One value, one method | In a coupling paper the two sides are often measured by different methods and conditions (P450 coupling: product at 10 to 30 min, NADH in steady-state kinetics). | A leaf records a coupling under a type only when the passage ties both sides to one reaction; the window and mixture facts say whether they match. A passage that gives each side without tying them gives no coupling record. |
| Derived values | The old calculator derived the productive fraction (nu x P / H). The SOP's extraction rule: "facts are stated only when the quote says them, never worked out from other numbers". | Open question 3. Draft: the leaf states the paper's numbers (amounts, rates, the stated coupling, the coefficient); the converter derives the productive fraction by an exact arithmetic (coefficient x product / partner) only when both sides and the coefficient are stated points, and marks it derived. |

## 7. What is still open (questions for the owner, in plain words)

1. Is the list of eight right? Are types 1 and 2 (and 4) one type "paired rates" with the consumed-side detector a fact, or separate as drafted (each detector has its own controls)? Is type 8 (isotope label) a coupling at all, or does it belong to product distribution?
2. Predicate: `catalyzes` is already the activity class's. Do the classes keep sharing it (then the page must hand a leaf several classes) or does this class get its own word?
3. May the converter work out the productive fraction from stated amounts and the coefficient (as the old calculator did), or must the passage state the coupling itself? The first gives many more usable records; the second is stricter to the "never worked out" rule.
4. A productive fraction above 1 (more product than the partner consumed allows) is read here at the strong end and left to the criteria to lower the weight. Should it instead count as a failed measurement (conflicting stoichiometry, direction neutral)? The CsiD note says such values are diagnostics, not silently clipped.
5. Where do the P/O ratio, H+/e- ratios and ATP-driven transport belong: here or in `transport_response`?
6. Is a coupling by difference (type 3: one minus the by-product share, no product measured) acceptable evidence for a claim "E catalyzes S", or only a note on another type's record?
7. Pooling: not pooled (as drafted), or pooled in the unit "fraction" if every converter states the productive fraction only?
8. Do the two scale ends (1 percent and 90 percent; 1 percent and 1 per partner) look right to you? They are from memory of the P450 literature; an expert in oxygenase and nitrogenase work should check them.
9. `reporter_specificity` is required for every quantity kind. Types with no reporter (6, 7, 8) would answer `not_applicable`; confirm the sheet takes that, or make it optional for them (the grading module is not changed by this draft).
10. No real published paragraph has been found for any type (SOP step 6). Candidates with PMC ids: PMC555470 (QueF), PMC6265302 (CsiD/LhgO), PMC2223550 (Bcd/Etf), PMC12051542 (HFP), PMC2711008 (CysQ). Types 3, 4, 5, 7 and 8 have no candidate in the places searched; their licences and whether the passages state both sides were not checked.
11. Codex sessions and the October 150-paper inventory were not searched; ask where the owner's list of coupling experiments lives, if there is one.
