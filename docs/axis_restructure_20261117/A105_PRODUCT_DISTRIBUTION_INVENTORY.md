# A105 `product_distribution` experiment inventory (SOP step 0, DRAFT for the owner to correct)

Written 2026-11-22 under `A105_EXPERIMENT_SOP.md` step 0, modelled on `A105_ACTIVITY_RATE_INVENTORY.md`. Read-only search; nothing was run (no Python,
no test, no script), nothing was committed. Files written for this class: this one, `G/literature_product_distribution_direction.py`, and
`runs/a105_class_drafts/registration/CLASS_product_distribution.md` (the source the coordinator adds to the contract).

**Status: DRAFT, nothing here is owner-confirmed.** The owner has not supplied a list for this class. Following SOP 0a item 2, the list is drafted from
the sources found plus domain knowledge: one entry per reapplicable protocol (a way of measuring), not per paper or case. Every number is
`EXPERT_REVIEW`; literature figures marked "from memory, not verified" are not verified. Per the owner's rule the values are researched per quantity and
gradual between two ends, never a pass/fail step and never one formula for all.

**Class boundary.** Which products a reaction gives and in what proportions, and where its equilibrium lies: product fractions, regio- and
stereo-selectivity, product ratios, equilibrium fraction or ratio. Not how fast (`activity_rate`), not how much in total or how complete
(`endpoint_conversion`), not stoichiometric balance with a cofactor (`reaction_coupling`).

---

## 1. Sources searched and what was found

| Place | Found | Used for |
| --- | --- | --- |
| `A105_EXPERIMENT_SOP.md` (Step 0 and the rules), `A105_ACTIVITY_RATE_INVENTORY.md` | The protocol, the template, the model document. | Structure of this file. |
| `G/literature_assay_grading.py` | `QUANTITY_KINDS['product_distribution']` = `product_fraction`, `product_fraction_ratio`, `equilibrium_fraction`, `equilibrium_ratio`. `CRITERIA_BY_TYPE['product_distribution']` = the nine `COMMON_CRITERIA` + `species_identity`, `response_factors`, `common_denominator`, `equilibrium_state`. `_quantity_unit_supported`: all four kinds accept only the units `fraction` and `dimensionless`. `_required_criteria`: `equilibrium_state` is optional unless the kind starts with `equilibrium_`. The questions are quoted in section 3.10. | Quantities, units, criteria (sections 2, 3, 4). |
| `G/literature_activity_direction.py`, `G/literature_direction.py`, `G/literature_row_contract.py` (5b2, 5c, `CLAIM_PREDICATES_BY_CLASS`, `stated_strength`) | The class-scoped direction paradigm: anchors per quantity, log position, smooth step, lowered by the stated spread, quantitative never opposes, words alone go to `literature_direction`. `stated_strength` knows only anchored binding types and `activity_rate` (must grow by this class, see the registration note). | Section 4 and the direction module. |
| `G/literature_row.py`, `G/literature_page_update.py` | `POOLED_UNIT_BY_CLASS`, `NOT_POOLED_CLASSES` live in `literature_row.py`, not the contract. `page_update` branches on the class for the direction call. | Registration note. |
| `docs/axis_restructure_20261117/INVESTIGATION_FINDING_FEATURES_a105.md` | The old reader `literature_product_partition_cells` fed `product_distribution` only (flags `approximate`, `outside_reported_fraction_range`, a `threshold`); the class sheet is "Product distribution and equilibrium". | Past work. |
| `docs/axis_restructure_20261117/A105_FIGURE_EXTRACTION_FINDINGS.md` | Only the partition and coupling namespaces route to `product_distribution`; no figure namespace does. | Readers (section 3, "text and tables only"). |
| `docs/axis_restructure_20261117/LOST_CONTENT_a104.md` | A104 characterization maps `catalyzes` to {activity_rate, endpoint_conversion, product_distribution, reaction_coupling}. | Predicate (section 5). |
| `research/experimental_scoring_review_2026-10-23/a105_assay_validity_case_145/PROPOSAL.md`, `template_a105_reactions_001/02_aquifex_hfp_001.md`, `11_component_synthesis_001.md` | The one real product-distribution case: HFP (PMC12051542, JBC 2025), 31P and 13C NMR with chemical standards: 39.7 percent Ru5P and 60.3 percent R5P at equilibrium from either substrate (R5P/Ru5P 1.519). Notes: an equilibrium composition belongs to the preparation and does not say how much of the catalysis is the studied enzyme (a contaminating isomerase, RpiA, was found); the two fractions share one denominator and sum to 1, so they are one measurement, not two; a normalized partition can sum to 100 percent while the total recovery is unknown; no relaxation or response correction or standard recovery was reported; a source unit inconsistency (0.67 mM versus 0.67 M) prevents molar yields; 31P and 13C NMR of the same preparation are not independent. | Controls, noise, the "shared denominator" and "not independent" rules, the attribution caveat on equilibrium quantities. |
| `research/.../molecular_measurement/summary.md`, `template_a105_reactions_001/05_f420_partner_2022_001.md` | F420 precursor partner (PMC8764529): with equal 0.5 mM candidate substrates the product-rate proportions were 65, 26.5 and 8.5 percent (3-PG, 2-PL, PEP), n = 3 biological replicates with SD displayed. A coupling partner can change the product spectrum. | Product-fraction record fields; the "partner can set the observed spectrum" note. |
| `research/.../template_a105_reactions_001/06_tria_atza_2001_001.md`, `03_cysq_2008_001.md`, `a105_matched_estimator_source_260/SOURCE_REVIEW_001.md` | Product fate fractions that share data with the cleavage estimates (PARP1: nicotinamide versus free ADP-ribose; not independent views); HPLC and MS product identification with standards. | Product identity and shared-denominator facts; HPLC and LC-MS entries. |
| `verification/biochemical_assay_guides_318`, `biochemical_fourteen_graders_319`, `a105_sheet_reader_inventory_315/SHEETS.tsv` | Searched for the class's words (product distribution, product fraction, equilibrium fraction, regioselectivity, enantiomeric, product ratio): no hit in these three places. SHEETS.tsv has no product-distribution sheet row by that name. The enzyme-assay guides give the general controls (no-enzyme, inactive enzyme, mass purity is not activity purity). | Nothing specific; general controls only. |
| `docs/axis_restructure_20261117/EXPERIMENT_INVENTORY_SEARCH.md`, `_2.md` | No product-distribution technique list; no hit for the class's words beyond the class name. | Nothing. |
| Codex session files | Not opened (instructed). | Nothing. |

**Conclusion.** As for binding and activity, no per-technique list or per-technique criteria exist for this class. The only prior case is one NMR
equilibrium partition (HFP) and one product-spectrum case by competition (F420). The list below is new, drafted from the class's quantity kinds and
criteria and from how product mixtures are actually measured in papers. Methods and figures marked "from memory" come from general knowledge of the
field, not from a document in this repository.

---

## 2. What all `product_distribution` types share (the class core)

**Evidences:** sheet `product_distribution` (predicate `catalyzes`, section 5).

**What is measured.** After a reaction (or at equilibrium) the amount of each species is measured by a method that separates or resolves them,
and the share of one of them is stated: the claimed product's fraction of all products, a ratio of two products (regio-isomers, stereo-isomers,
chain lengths, cleavage sites), or the composition at equilibrium. One experiment gives one set of shares that share a denominator.

**Native quantities common to every type** (each a record operand: `point` or `unavailable` with a reason, never 0, never omitted; every stated
value carries `support`):

| Quantity (record field) | Unit vocabulary | Sheet kind it fills | Note |
| --- | --- | --- | --- |
| `product_fraction` | `fraction`, `percent` | `product_fraction` | The share of ONE named product among the products formed (not of the substrate). The product is the record's partner. Converter: percent times 0.01 (exact). |
| `product_fraction_ratio` | `dimensionless` | `product_fraction_ratio` | Ratio of two products' shares within one reaction (regio-isomer ratio, diastereomer ratio, enantiomer ratio, chain-length ratio). The numerator species is the record's partner. A ratio written "a:b" is read as a/b. |
| `enantiomeric_excess` | `percent`, `fraction` | `product_fraction` of the major enantiomer, f = (1 + ee) / 2 (exact, two species only) | Only for `distribution_chiral`. The major enantiomer (a named species) is the partner; ee with its sign convention unstated is `unavailable`. |
| `equilibrium_fraction` | `fraction`, `percent` | `equilibrium_fraction` | Share of one named species in the equilibrium mixture. |
| `equilibrium_ratio` | `dimensionless` | `equilibrium_ratio` | Product-side over other-side concentration ratio at equilibrium; `K` when both sides have one species and equal molecularity. A K with a unit is NOT in the sheet's vocabulary (reported, registration note section 4, item 2). |
| each of the four above, a spread | same unit | `effect_variance` | Spread kinds (`spread_kind`): `standard_deviation`, `standard_error`, `confidence_interval`, `range`, `unstated`. An unstated "+/-" stays unstated, never read as SD. |
| `replicate_count` | count | `sampling_basis` | Count and the fact below; no cut-off. |
| `total_recovery` | `fraction`, `percent` | role `recovery` | Sum of the measured species over the starting amount (closure). Not an independent mass balance when the fractions were normalized to 100 percent. |
| `substrate_conversion` | `fraction`, `percent` | context | Conversion at the sampling time. A distribution read at high conversion can have drifted (secondary products). |
| `sampling_time` | `s`, `min`, `h` | context | Time at which the distribution was read. |
| `minor_species_detection_limit` | `fraction`, `percent` | `calibration_applicability` | Smallest fraction the method resolves, when stated. |
| `species_count` | count | `common_denominator` | Number of species the denominator covers. |
| Identity block (automatic) | | | `target_id` (the enzyme as written), `partner_id` (the species whose share is stated), `temperature_c`, pH. |

**Choices** (plain vocabularies): `fraction_basis` = `mole`, `mass`, `peak_area`, `ion_signal`, `band_intensity`, `integral` (what the share is a share of:
only `mole` is a molar share by itself; the others need response factors, see criterion `response_factors`); `spread_kind` (above).

**Yes/no facts common to every type** (`yes`, `no`, `unknown`, `not_applicable`; silence is `unknown`, never `no`):
`authentic_standard_for_each_species`; `response_factors_calibrated`; `fractions_share_one_denominator`; `all_products_identified` (no unassigned peaks or
bands left out of the denominator); `no_enzyme_control_done`; `inactive_enzyme_control_done` (heat-treated or catalytic mutant); `products_stable_under_assay_and_workup`
(no interconversion, degradation or loss after the reaction); `enzyme_removed_or_quenched_before_analysis`; `distribution_stable_over_time` (the same share at
two or more times); `approached_from_both_sides` (equilibrium reached from substrate and from product); `independent_replicates`; `purified_enzyme`;
`native_substrate`; `claimed_product_detected` (the fact that carries the qualitative statement).

**Certainty, all types.** A measured share or ratio read against the paper's own spread; or a stated result in words alone ("X was the only
product", "no Y was detected"), which is the weakest form (section 4). A quantitative share never opposes; "the claimed product was not found"
opposes.

**Owner biochemical questions mapped to the core.** Sensitivity: `minor_species_detection_limit`, `total_recovery`. Kinetic parameters: not in this class.
Conditions (temperature, in vitro or in vivo, realism of the chemistry): `temperature_c`, pH, `purified_enzyme`, `native_substrate`, `substrate_conversion`.
Expected signal in messy samples: `authentic_standard_for_each_species`, matrix criterion, `total_recovery`. A control for spontaneous reaction:
`no_enzyme_control_done` (non-enzymatic isomerization, hydrolysis or racemization gives its own distribution).

**Readers that supply it (all types):** text paragraphs (Methods and Results) and tables (the `table` and `report` leaves). Chromatograms, spectra,
gels and plots are figures and are unavailable today (SOP Known gaps); a share written only in a figure is `unavailable`.

---

## 3. The draft experiment list (9 types)

All ids start with `distribution_`, are snake_case and are not among the reserved ids. Each is one way of measuring that can be reapplied to any
enzyme; none is a paper or a case.

| # | Type id | Experiment | Family |
| --- | --- | --- | --- |
| 1 | `distribution_nmr` | Quantitative NMR of the product mixture | NMR, spectroscopy, no separation |
| 2 | `distribution_hplc` | HPLC peak areas (UV, fluorescence, refractive index, ELSD, CAD) | Liquid chromatography |
| 3 | `distribution_gc` | GC-FID or GC-MS peak areas of volatile or derivatized products | Gas chromatography |
| 4 | `distribution_lcms` | LC-MS or LC-MS/MS product profile by ion signal | Liquid chromatography, mass spectrometry |
| 5 | `distribution_chiral` | Chiral-phase chromatography or electrophoresis (ee, er, dr) | Chromatography, stereochemistry |
| 6 | `distribution_radio_tlc` | Radiolabelled products separated by TLC or radio-HPLC and counted or imaged | Isotope, separation |
| 7 | `distribution_gel_bands` | Electrophoretic size or cleavage-site pattern with densitometry or fragment analysis | Electrophoresis |
| 8 | `distribution_enzymatic_endpoint` | Each species determined by its own specific enzymatic assay after the reaction | Enzymatic end-point analysis |
| 9 | `distribution_optical_equilibrium` | Equilibrium composition from an absorbance or fluorescence change of the mixture | Optical, equilibrium |

**Considered and not listed as types** (with the reason):

- *Competition between several substrates* (several substrates at once, product proportions as in the F420 case): a design; the shares are read by types 1 to 6.
  Recorded as a fact on the record if the owner wants it (open question 5). *Equilibrium from both sides* is likewise a design (`approached_from_both_sides`), read by any
  detector; only the two detectors that exist for equilibrium work alone (types 8 and 9) are types of their own.
- *Isotope tracing of metabolic flux (13C, 14C fractions of pathway products in cells)*: whole-cell, belongs with growth and flux evidence (A106, not touched here).
- *Mass spectrometry imaging, ion mobility, capillary electrophoresis of small molecules*: rare for this claim; CE of nucleic acids is in type 7, CE of chiral small molecules in type 5.
- *Product spectrum by sequencing (deep-sequencing of edited or modified nucleic acid)*: no paper of this class found; add if a real one is needed.
- *Computed distributions (docking, QM/MM selectivity)*: not an experiment.

Fields named in each entry below are in addition to the class core (section 2). "Own criteria" are the method's own grader criteria (facts only; the
sheet judges) with the sheet criterion each maps to (`->`). Researched values are pointers for the type's builder, "from memory, not verified".

### 3.1 `distribution_nmr`

```text
experiment:            quantitative NMR of the product mixture              (type id distribution_nmr)
family:                NMR, spectroscopy, no separation (1H, 13C, 31P, 19F; time-resolved or end-point)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  integral per species (relative, or uM against an internal standard); product share as fraction or percent;
                       species ratio; equilibrium share; relaxation delay (s); number of scans; field (MHz); chemical shift (ppm)
controls required:     authentic standards or reference spectra for each species (chemical shift assignment); no-enzyme spectrum (spontaneous
                       interconversion); internal concentration standard; relaxation delay long enough for full relaxation of every integrated nucleus
noise expectations:    signal-to-noise of the minor integral; spread over replicate spectra; number of scans; baseline and phasing statement
replicates needed:     independent reactions (count + independence fact); several spectra of one sample are technical, not independent
certainty:             quantitative share with structural identity; low sensitivity (about 1 to 5 percent minor species, from memory, not verified);
                       equilibrium shares need the equilibrium evidence
readers that supply it:text, tables; spectra are figures (unavailable)
past work (where):     HFP 31P and 13C NMR, Ru5P 39.7 percent and R5P 60.3 percent (PMC12051542; a105_assay_validity_case_145 PROPOSAL); QueF NMR (PMC555470, used under
                       activity_rate); no existing code for this class
```

Record extras: `relaxation_delay` (`s`, `ms`), `number_of_scans` (count), `signal_to_noise_minor` (dimensionless), `spectrometer_frequency` (`MHz`), `nucleus` (choice: `1H`, `13C`, `31P`, `19F`, `15N`),
facts `relaxation_delay_adequate` (stated as at least five times the longest T1, or inversion-recovery checked), `internal_standard_used`, `integrals_from_resolved_signals`.
Own criteria: `shares_from_resolved_signals` -> `species_identity`; `species_assigned_with_standards` -> `species_identity`; `relaxation_delay_recorded` -> `response_factors` (NMR is response-factor free only when
the nuclei relax fully; the delay is recorded for the sheet to judge against the researched five-T1 rule, from memory, not verified); `denominator_species_stated` -> `common_denominator`;
`no_enzyme_spectrum` -> `background_alternatives`; `inactive_enzyme_spectrum` -> `attribution_supported`; `signal_to_noise_minor` -> `calibration_applicability`; `replicates` -> `sampling_basis`; `stable_composition_over_time` and `approached_from_both_sides` -> `equilibrium_state`; `purified_enzyme` and `native_substrate` -> `condition_scope`.

### 3.2 `distribution_hplc`

```text
experiment:            HPLC peak-area distribution of products              (type id distribution_hplc)
family:                liquid chromatography (UV, diode array, fluorescence, refractive index, ELSD, CAD detection)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  peak area or height (arbitrary); retention time (min); product share as fraction or percent (of peak area or of amount);
                       species ratio; relative response factor per species (dimensionless); standard curve per species; detection limit
controls required:     authentic standard for each species (retention time and spiking); response factors or per-species calibration curves (a UV area
                       percent is not a molar percent unless the extinction coefficients are equal); no-enzyme and heat-inactivated enzyme injections; quench or enzyme removal before injection;
                       stability of each product through the work-up
noise expectations:    spread of areas over replicate injections AND independent reactions; peak resolution between neighbouring species; integration baseline statement
replicates needed:     independent reactions (count + independence fact); repeated injections are technical
certainty:             quantitative share; identity by retention only unless a standard or MS confirms; molar share only with response factors
readers that supply it:text, tables; chromatograms are figures (unavailable)
past work (where):     PARP1 HPLC nicotinamide and ADP-ribose accounting (319 entry 12; matched_estimator_source_260, used under activity_rate); BbPK HPLC acetate (case 164, activity_rate); CysQ AMP (PMC2711008)
```

Record extras: `peak_resolution` (dimensionless), `detection_wavelength` (`nm`), `relative_response_factor` (dimensionless), `injection_count` (count), facts `peaks_resolved`, `spiked_with_standard`, `quenched_before_injection`, `calibration_curves_for_each_species`.
Own criteria: `species_assigned_with_standards` -> `species_identity`; `response_factors_calibrated` -> `response_factors`; `shared_denominator_and_closure` -> `common_denominator`; `peak_resolution_recorded` -> `matrix_interference`; `calibration_range_covers_signals` -> `calibration_applicability`; `no_enzyme_injection` -> `background_alternatives`; `products_stable_through_workup` -> `background_alternatives`; `inactive_enzyme_injection` -> `attribution_supported`; `replicates` -> `sampling_basis`; `equilibrium_evidence` -> `equilibrium_state`; `purified_enzyme`, `native_substrate` -> `condition_scope`.

### 3.3 `distribution_gc`

```text
experiment:            GC-FID or GC-MS distribution of volatile or derivatized products   (type id distribution_gc)
family:                gas chromatography (terpene and other volatile product spectra, fatty acid methyl esters, silylated sugars, headspace gas)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  peak area percent; product share as fraction or percent; species ratio (regio-isomer, chain length); Kovats or retention index;
                       mass spectrum match; internal standard ratio
controls required:     authentic standards or retention-index and mass-spectral library match for each species; no-enzyme and inactive-enzyme extracts (solvent, plastic and spontaneous
                       rearrangement peaks); extraction recovery per species; thermal stability of each product in the injector (some terpenes rearrange in the hot inlet)
noise expectations:    spread over independent reactions; area percent versus response (FID responds roughly to carbon content, so a carbon-number-matched share is close to molar
                       for hydrocarbons, from memory, not verified; MS ion counts do not)
replicates needed:     independent reactions (count + independence fact)
certainty:             quantitative share (FID) or relative ion share (MS); identity by library match is weaker than by standard
readers that supply it:text, tables; chromatograms are figures (unavailable)
past work (where):     no case in the places searched; Bcd/Etf H2 formation by GC (PMC2223550) is activity_rate
```

Record extras: `retention_index` (dimensionless), `internal_standard_ratio` (dimensionless), `extraction_recovery` (`fraction`, `percent`), `detector` (choice: `fid`, `ms`, `tcd`), facts `identified_by_standard`, `identified_by_library_match_only`, `injector_stability_checked`, `extraction_recovery_stated`.
Own criteria: `species_assigned_with_standards` -> `species_identity` (library match only is a fact the sheet judges); `response_factors_calibrated` -> `response_factors`; `shared_denominator_and_closure` -> `common_denominator`; `injector_stability_checked` and `extraction_recovery_stated` -> `matrix_interference`; `no_enzyme_extract` -> `background_alternatives`; `inactive_enzyme_extract` -> `attribution_supported`; `replicates` -> `sampling_basis`; `purified_enzyme`, `native_substrate` -> `condition_scope`; `calibration_range_covers_signals` -> `calibration_applicability`.

### 3.4 `distribution_lcms`

```text
experiment:            LC-MS or LC-MS/MS product profile by ion signal      (type id distribution_lcms)
family:                liquid chromatography with mass spectrometry (extracted ion chromatograms, selected or multiple reaction monitoring)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  ion counts or peak area (arbitrary); share as fraction or percent of summed ion signal; species ratio; m/z and fragment of each species; isotope-labelled
                       internal standard ratio; calibration curve per species; limit of quantification
controls required:     authentic standard per species (identity and calibration); isotope-labelled internal standard where shares are quantified; matrix-matched calibration; no-enzyme and inactive-enzyme
                       reactions; check that ionization response is similar or calibrated (ion signal is not molar)
noise expectations:    spread over independent reactions; ion suppression statement; ratio of qualifier to quantifier ion
replicates needed:     independent reactions (count + independence fact)
certainty:             quantitative only when calibrated per species; otherwise a relative profile whose share is on the ion-signal basis
readers that supply it:text, tables; chromatograms and spectra are figures (unavailable)
past work (where):     CysQ AMP by MS with internal standard (PMC2711008, activity_rate); CsiD LC-MS identity (PMC6265302); no existing code for this class
```

Record extras: `limit_of_quantification` (`fraction`, `percent`), `internal_standard_ratio`, `ionization_mode` (choice: `positive`, `negative`), facts `isotope_labelled_internal_standard`, `matrix_matched_calibration`, `ion_suppression_checked`.
Own criteria: `species_assigned_with_standards` -> `species_identity`; `calibration_per_species` -> `response_factors`; `shared_denominator_and_closure` -> `common_denominator`; `ion_suppression_checked` and `matrix_matched_calibration` -> `matrix_interference`; `calibration_range_covers_signals` -> `calibration_applicability`; `no_enzyme_reaction` -> `background_alternatives`; `inactive_enzyme_reaction` -> `attribution_supported`; `replicates` -> `sampling_basis`; `purified_enzyme`, `native_substrate` -> `condition_scope`.

### 3.5 `distribution_chiral`

```text
experiment:            chiral-phase chromatography or electrophoresis of stereo-isomeric products   (type id distribution_chiral)
family:                chromatography or capillary electrophoresis on a chiral selector (chiral HPLC, chiral GC, SFC, chiral CE); also diastereomer separation on an achiral column
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  enantiomeric excess (percent or fraction); enantiomer ratio er ("a:b"); diastereomer ratio dr; peak areas; absolute configuration of the major isomer (a choice: R, S, E, Z, ...);
                       conversion at the sampling time
controls required:     racemic or diastereomeric standard of the product (shows the column separates both isomers and gives equal areas); authentic standard of known configuration for assignment;
                       no-enzyme control (spontaneous racemization or epimerization of the product or substrate); product configurational stability under assay and work-up
noise expectations:    spread over independent reactions; ee near 100 percent is limited by the minor peak's detection limit; peak resolution of the two isomers
replicates needed:     independent reactions (count + independence fact)
certainty:             quantitative; ee, er and dr are the same fact in three spellings, never three results
readers that supply it:text, tables
past work (where):     no case in the places searched
```

Record extras: `enantiomeric_excess`, `enantiomer_ratio`, `diastereomer_ratio` (all as in section 2; the converter turns ee into the major enantiomer's share and er and dr into a ratio, exactly), `configuration` (choice: `R`, `S`, `E`, `Z`, `cis`, `trans`, `syn`, `anti`), `peak_resolution`, facts `racemic_standard_run`, `configuration_assigned_by_standard`, `product_configurationally_stable`.
Own criteria: `racemic_standard_run` and `configuration_assigned_by_standard` -> `species_identity`; `response_factors_equal_for_isomers` (the two isomers have the same detector response by symmetry on an achiral detector, so this is `not_applicable` unless diastereomers) -> `response_factors`; `shared_denominator_two_isomers` -> `common_denominator`; `product_configurationally_stable` and `no_enzyme_control` -> `background_alternatives`; `inactive_enzyme_control` -> `attribution_supported`; `peak_resolution_recorded` -> `calibration_applicability`; `replicates` -> `sampling_basis`; `purified_enzyme`, `native_substrate` -> `condition_scope`.

### 3.6 `distribution_radio_tlc`

```text
experiment:            radiolabelled product distribution by TLC, radio-HPLC or gel with counting or phosphorimaging   (type id distribution_radio_tlc)
family:                isotope with separation (14C, 3H, 32P, 35S labelled substrate; products separated, bands or fractions counted)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  counts (cpm, dpm) or PSL per spot, band or fraction; share as fraction or percent of total counts in the lane; species ratio; Rf or retention of each species;
                       specific radioactivity of the substrate
controls required:     authentic cold standards co-run and visualized (identity by position); no-enzyme lane (spontaneous products and impurities in the labelled substrate); zero-time lane (impurity of the labelled substrate);
                       whole-lane recovery (counts in all spots over counts applied); background counts beside the test counts
noise expectations:    spread over independent reactions; background beside lowest band; linear range of the imager; spot or band overlap
replicates needed:     independent reactions (count + independence fact)
certainty:             quantitative and very sensitive for labelled species; a label on one atom reports only products that keep it, so shares are of labelled products
readers that supply it:text, tables; autoradiographs are figures (unavailable)
past work (where):     no case in the places searched
```

Record extras: `counts_background` (`cpm`, `dpm`), `lane_recovery` (`fraction`, `percent`), `label` (choice: `14C`, `3H`, `32P`, `35S`, `33P`), facts `cold_standards_co_run`, `zero_time_lane_run`, `label_retained_by_all_products`, `within_linear_range_of_imager`.
Own criteria: `cold_standards_co_run` -> `species_identity`; `label_retained_by_all_products` -> `common_denominator`; `lane_recovery_stated` -> `common_denominator`; `within_linear_range_of_imager` -> `calibration_applicability`; `zero_time_lane_run` and `no_enzyme_lane` -> `background_alternatives`; `inactive_enzyme_lane` -> `attribution_supported`; `response_factors` -> `not_applicable` when the shares are counts of one isotope (equal specific activity per labelled atom) and `unknown` otherwise; `replicates` -> `sampling_basis`; `purified_enzyme`, `native_substrate` -> `condition_scope`.

### 3.7 `distribution_gel_bands`

```text
experiment:            electrophoretic size or cleavage-site distribution with densitometry or fragment analysis   (type id distribution_gel_bands)
family:                electrophoresis (denaturing PAGE of nucleic acids, capillary fragment analysis, SDS-PAGE of cleavage products, sequencing ladder)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  band or peak intensity (arbitrary); share of each product length or site as fraction or percent of the lane; product ratio; fragment size (nt, bp, kDa); cleavage site position (nt)
controls required:     size markers or sequencing ladder (assigns each band to a length or site); no-enzyme lane; catalytic-mutant lane; substrate-only lane; stain or label linear in amount over the amounts loaded
noise expectations:    spread across gels; densitometry linear range; band overlap; per-nucleotide stain or label response (a longer fragment carries more label or stain per molecule when stained, equally when end-labelled)
replicates needed:     independent reactions (count + independence fact); lanes on one gel are not independent of the gel
certainty:             quantitative (share by densitometry) or qualitative (a band is present or absent)
readers that supply it:text, tables; gel images are figures (unavailable)
past work (where):     no case in the places searched (the old gel sheet SHEETS 17 is protein bands, the protein_signal class)
```

Record extras: `fragment_size` (`nt`, `bp`, `kDa`), `cleavage_position` (`nt`), `gel_percent` (percent), `labelling` (choice: `end_labelled`, `uniformly_labelled`, `stained`, `fluorescent_tag`), facts `size_markers_run`, `end_labelled_so_equal_response`, `within_linear_range_of_stain_or_label`.
Own criteria: `size_markers_run` -> `species_identity`; `labelling_gives_equal_response` -> `response_factors`; `all_bands_in_denominator` -> `common_denominator`; `within_linear_range` -> `calibration_applicability`; `no_enzyme_lane` and `substrate_only_lane` -> `background_alternatives`; `catalytic_mutant_lane` -> `attribution_supported`; `replicates` -> `sampling_basis`; `purified_enzyme`, `native_substrate` -> `condition_scope`.

### 3.8 `distribution_enzymatic_endpoint`

```text
experiment:            each species determined by its own specific enzymatic assay after the reaction   (type id distribution_enzymatic_endpoint)
family:                enzymatic end-point analysis (a specific dehydrogenase, oxidase or kinase converts one species stoichiometrically to a measurable reporter; classic for sugars, organic acids, amino acids)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  concentration of each species (uM, mM; converted to a share); reporter absorbance at 340 nm or fluorescence; share as fraction or percent; equilibrium ratio from the concentrations
controls required:     authentic standard curve per species run with the same analysis enzyme; specificity of the analysis enzyme for its species (no cross-reaction with the others, shown with the pure species);
                       blank without the analysis enzyme; reaction run to completion of the analysis step (reporter plateau); no-enzyme sample for spontaneous species; quench of the first enzyme before analysis
noise expectations:    spread over independent reactions; analysis-enzyme completeness; interference of the other species or buffer components with the reporter
replicates needed:     independent reactions (count + independence fact)
certainty:             quantitative share; molar by construction (each species measured in its own units), but a share of species not covered by an assay is missing from the denominator
readers that supply it:text, tables
past work (where):     RidA ketoacid and ferricyanide trapping (PMC3270999) and OxDC FDH-coupled formate endpoint (moral_2011_review.md) are detection steps used under activity_rate; no case for this class
```

Record extras: `analysis_enzyme_cross_reactivity` (`fraction`, `percent`), `reporter_wavelength` (`nm`), facts `analysis_enzyme_specificity_shown`, `analysis_run_to_completion`, `standard_curve_for_each_species`, `first_enzyme_quenched_before_analysis`.
Own criteria: `analysis_enzyme_specificity_shown` -> `species_identity`; `standard_curve_for_each_species` -> `response_factors` (molar by calibration); `species_covered_by_assays` and `closure` -> `common_denominator`; `analysis_run_to_completion` and `standard_curve_range` -> `calibration_applicability`; `cross_reactivity_stated` -> `matrix_interference`; `no_enzyme_sample` -> `background_alternatives`; `inactive_enzyme_sample` -> `attribution_supported`; `replicates` -> `sampling_basis`; `stable_composition_over_time` and `approached_from_both_sides` -> `equilibrium_state`; `purified_enzyme`, `native_substrate` -> `condition_scope`.

### 3.9 `distribution_optical_equilibrium`

```text
experiment:            equilibrium composition from an absorbance or fluorescence change of the mixture   (type id distribution_optical_equilibrium)
family:                optical, equilibrium (a species with its own spectrum, for example NADH, a chromophoric substrate or product; equilibrium ratio from the plateau and the spectrum of each side)
evidences (sheet):     product_distribution                                 (predicate: catalyzes)
native outputs/units:  absorbance (or fluorescence) at the plateau; extinction coefficient or fluorescence yield of each species; equilibrium fraction or ratio (dimensionless); wavelength (nm);
                       initial concentrations
controls required:     the plateau reached from both directions, or the same value at several initial concentrations; spectrum of each pure species at the assay pH; no-enzyme sample (a sample that does not move, so the plateau
                       is catalyst-dependent in time only); a stable plateau (no drift from instability or side reaction)
noise expectations:    spread over independent samples; absorbance range (detector linearity); coupled-equilibrium corrections stated (for a coupled reaction the observable is a composite constant, a Keq of the sum, not of one step)
replicates needed:     independent samples (count + independence fact)
certainty:             quantitative equilibrium share or ratio, no separation; the identity of the absorbing species is by spectrum only
readers that supply it:text, tables; plots of A against time are figures (unavailable)
past work (where):     no case in the places searched; HFP reached its equilibrium by NMR (distribution_nmr), not optically
```

Record extras: `wavelength` (`nm`), `extinction_coefficient` per species (`M^-1 cm^-1`, `mM^-1 cm^-1`), `absorbance_plateau` (dimensionless), `plateau_drift` (dimensionless per `min`), facts `approached_from_both_sides`, `plateau_stable`, `pure_species_spectra_measured`, `composite_constant_stated_as_such`.
Own criteria: `pure_species_spectra_measured` -> `species_identity`; `extinction_coefficient_stated` -> `response_factors`; `all_absorbing_species_accounted` -> `common_denominator`; `absorbance_range` -> `calibration_applicability`; `no_enzyme_sample` -> `background_alternatives`; `plateau_stable`, `approached_from_both_sides` -> `equilibrium_state`; `replicates` -> `sampling_basis`; `purified_enzyme`, `native_substrate` -> `condition_scope`.
`attribution_supported`: the equilibrium does not depend on the enzyme; only `inactive_enzyme_sample` showing no approach to equilibrium in the same time supports that this enzyme is the catalyst.

### 3.10 Sheet questions (from `CRITERION_QUESTIONS`, quoted so the builders map to the sheet's own words)

| Sheet criterion | Question |
| --- | --- |
| `species_identity` | Are the measured product species and their assignment established? |
| `response_factors` | Are species-specific detector responses calibrated to the stated amount-fraction or signal-fraction basis? |
| `common_denominator` | Do selected fractions share a defined denominator and stated species coverage, without treating closure as independent mass balance? |
| `equilibrium_state` | Does time/stability or reverse-approach evidence establish equilibrium rather than a single endpoint? |
| `measurement_identity` | Do source subject, construct, preparation, endpoint, units and denominator identify this estimate? |
| `calibration_applicability` | Do calibration, sensitivity, response range and recovery apply to this detector and selected estimate? |
| `matrix_interference` | Are matrix effects, detector interference and sample handling addressed for this measured quantity? |
| `background_alternatives` | Do matched controls or quantified corrections address spontaneous chemistry and competing contributions? |
| `attribution_supported` | Does the selected quantity and its controls isolate the claimed contribution of the studied molecule, with the same endpoint and denominator for an attributed/total signal fraction? |
| `assertion_relevance` | Does this endpoint at its actual functional resolution address the selected assertion? |
| `condition_scope` | Do substrate, pH, temperature, heating, cofactors and in-vitro/in-vivo preparation support the asserted conditions? |
| `variance_correspondence` | Is this variance for this exact estimate, including its corrections and shared measurements? |
| `sampling_basis` | Are sampling units, technical repeats, independent preparations and dependence correctly represented? |

`measurement_identity`, `assertion_relevance` and `variance_correspondence` map as in the activity types: `assertion_relevance` from `native_substrate` and the match of the stated product to the claim (the relevance check
in the page does the molecular matching); `variance_correspondence` is supported only when a variance was computed; `measurement_identity` is not selected by a method criterion.
`equilibrium_state` is a required criterion for the two `equilibrium_*` kinds in every type and optional for the two `product_*` kinds: a type that reports an equilibrium result and has no equilibrium evidence answers it `unknown`.

---

## 4. Direction and strength for the class (DRAFT; every number EXPERT_REVIEW, owner to confirm)

Code: `G/literature_product_distribution_direction.py`; constants proposed in `runs/a105_class_drafts/registration/CLASS_product_distribution.md` (contract section 5d). Same paradigm as binding and
activity: the position on the quantity's own log scale between two ends, a smooth step, lowered by the stated spread.

```text
p = clip( (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), 0, 1 )      (LARGER is stronger)
s = (3 p^2 - 2 p^3) / (1 + r^2),    r = sd / e    (0 when no spread is stated)
log_ratio = QUALITATIVE_LOG_RATIO[type] * s
```

**Which stated quantity is the effect.** The share of the CLAIMED product (a claim is about whether this enzyme gives this product). The record's partner is that product, so the result bears on the row only when it agrees with the claim
(section 5). A share of another product of the same reaction is a different result (`other_partner`) and stays off the row.

| Quantity | Anchor unit | Larger is stronger? | noise_end | strong_end | Reason (all from memory, not verified; EXPERT_REVIEW) |
| --- | --- | --- | --- | --- | --- |
| `product_fraction` | `fraction` | yes | 0.01 | 0.9 | noise end: about the smallest minor species that HPLC, GC and NMR area or integral percentages resolve and quantify without a trace method (about one percent); below it a "product" is often an impurity, carry-over or spontaneous side product. Strong end: a claimed product that is nine tenths of what the reaction gives is the reaction's product; beyond that more share says more about selectivity than about whether the enzyme makes the product, and the claim names only the product. |
| `product_fraction_ratio` | `dimensionless` | yes (claimed product in the numerator) | 0.01 | 9 | The fraction ends carried through r = f / (1 - f): f = 0.01 is r about 0.01, f = 0.9 is r = 9. The ratio is for two species; with three or more the fraction is the better-defined quantity. |
| `equilibrium_fraction` | `fraction` | yes | 0.01 | 0.9 | The same ends as the product share. Kept separate so the owner can tune it: an equilibrium composition is the same for any catalyst or none, so it shows where the reaction lies and that the product is accessible, not that this enzyme makes it. The sheet's `attribution_supported` (no-enzyme and inactive-enzyme controls) carries the catalyst; it lowers the weight, never the direction. |
| `equilibrium_ratio` | `dimensionless` | yes (the claimed product, or the claimed product side, in the numerator) | 0.01 | 9 | Same ends as the product ratio. A K below 0.01 means the reaction does not run to the claimed product at all (strength 0, neutral). |

Worked values on the fraction scale: 0.01 gives 0; 0.05 gives about 0.29; 0.10 about 0.52; 0.30 about 0.85; 0.50 about 0.95; 0.90 and above 1. On the ratio scale: 1 (equal shares) gives about 0.76 and 9 gives 1. **The two
forms are not one curve between the ends** (a share of 0.5 gives 0.95 as a fraction but the same share written as ratio 1 gives 0.76): a log of a share and a log of a ratio differ in the middle. Open question 3.

**Order of preference when a record states several** (`PRODUCT_DISTRIBUTION_EFFECT_ORDER`): `product_fraction`, `product_fraction_ratio`, `equilibrium_fraction`, `equilibrium_ratio`. Why: the share names its own product and denominator and needs no
choice of numerator; the ratio is the same measurement with one more thing to get right (which product is on top); the equilibrium quantities last because the same composition is reached without the enzyme and only means something
when the equilibrium evidence holds. ee, er and dr are one fact in three spellings: the converter turns them into one share or one ratio and never counts them as separate results.

**What a result stated in words alone means.** The existing vocabulary is kept and READ for this class: `interaction_detected` reads "product detected" (the claimed product is among the products: "X was formed", "the enzyme gives X"),
`interaction_not_detected` reads "product not detected" (the claimed product was not found: "no Y was detected", with its detection limit stated or not), `interaction_not_stated` reads "product not stated". A bare statement counts
`QUALITATIVE_LOG_RATIO[type] * STATED_ONLY_STRENGTH` (0.25, owner-confirmed 2026-11-22) for a detection and a non-detection alike, so it counts less than any measured share above about 0.01. For this to hold the contract's `stated_strength`
must name this class (registration note 1b item 2). "X was the only product" is a stated detection, not a share of 1 (a share is a number the paper states). A stated "not detected" with a stated detection limit still opposes; the limit is recorded and
judged by the sheet (a weak limit lowers the weight). A share of exactly 0 is stated by the converter as "product not detected".

**Pooling.** Results of this class are NOT pooled in one unit (proposal: `NOT_POOLED_CLASSES` gains `product_distribution`): the effect is one of four quantities in two units and four meanings, chosen per experiment, so no mean has one unit. The row's pooled effect, variance and
precision are null; direction, strength and weight are unaffected.

**Weight and the sheet, not the direction.** Response factors, the shared denominator, closure, the equilibrium evidence, controls and replicates lower the weight only. A quantitative share never opposes. Conflicting stays what the paper itself shows
against the standard (a fact answered `no`, such as `no_enzyme_control_done` with the product also in the no-enzyme control, or a peak area percent used as a molar percent when the paper itself says response factors differ).

**Researched values per type (pointers for the builders, each to be researched with its method literature, made gradual, named and commented `EXPERT_REVIEW`).** NMR: relaxation delay against the longest T1 (about five T1, from memory, not verified), signal-to-noise of the
minor signal, number of independent spectra. HPLC and LC-MS: peak resolution of neighbours (about 1.5 for baseline, from memory, not verified), calibration range against the measured signal, response-factor spread across species. GC: injector stability, extraction recovery. Chiral:
resolution of the two isomers, minor-peak detection limit near 100 percent ee. Radio-TLC: lane recovery, background against the smallest band, linear range of the imager. Gel bands: linear range of the stain or label, band overlap. Enzymatic end-point:
analysis completeness and cross-reactivity. Optical equilibrium: plateau stability and the absorbance range. Replicates for all: `sqrt(n / MIN_REPLICATES)` with the method's researched minimum, as in the SOP.

**Proposed per-type `QUALITATIVE_LOG_RATIO` (EXPERT_REVIEW; a weaker method carries less; all below the label-free binding types).** `distribution_nmr` 1.3, `distribution_gc` 1.3, `distribution_chiral` 1.3, `distribution_hplc` 1.2, `distribution_radio_tlc` 1.2, `distribution_lcms` 1.1,
`distribution_enzymatic_endpoint` 1.1, `distribution_gel_bands` 1.0, `distribution_optical_equilibrium` 0.9. Reasons: NMR, GC and chiral chromatography identify species and give shares with little response bias; HPLC area needs response factors; LC-MS ion signal is not molar; gel and optical equilibrium rest on indirect labels or spectra.

---

## 5. Claim predicate (proposed, owner to confirm)

**Predicate `catalyzes`**, added to `CLAIM_PREDICATES_BY_CLASS['product_distribution']`; not symmetric (it stays out of `SYMMETRIC_PREDICATES`). A claim names molecules only: predicate, subject, partner; no threshold, no share.

- **Subject:** the enzyme (the record's `target_id`, the assayed protein as written).
- **Partner:** the claimed product, a molecule (the hypothesis value is a `reference` to the product molecule). The record's `partner_id` is the species whose share is the effect (the product fraction's species, the numerator of the ratio, the
  claimed side of an equilibrium). "E catalyzes P" is not "P catalyzes E".
- **Agreement:** a record whose partner equals the claim's partner (after `normalize_identity_ref`) is `relevant`; a record whose partner differs is `irrelevant` (`other_partner`, off the row); a record with an effect or a statement but no stated partner is `unresolved` (`partner_not_stated`),
  stays on the row and counts less. The complement of a share (1 minus the share, the other species of a two-species mixture) is NOT derived by the converter: the other species is a different partner.
- **A claim without a partner** (the hypothesis value is a reaction `term_ref`): the target alone decides and any product share of the enzyme counts (the page's `claim_of_hypothesis` reads a `term_ref` as target-only). This loses product specificity, which is the point of the class; the hypothesis should name the product molecule.
- **Same predicate in several classes.** `catalyzes` is already the predicate of `activity_rate` (and proposed for `endpoint_conversion` and `reaction_coupling`). `literature_relevance` and `page_update._check_claims` already handle that (they search the class lists and use the record's own class), but `class_of_predicate` raises when a predicate is in more than one list and `internal_summary.py` calls it. Raised in the registration note (section 4, item 1); not patched.

---

## 6. The class decisions of SOP step 0c, as read from the code

| Item | Finding | Proposal (owner to decide) |
| --- | --- | --- |
| `QUANTITY_KINDS['product_distribution']`, `CRITERIA_BY_TYPE` | 4 kinds, 13 criteria (section 1). `_required_criteria`: `equilibrium_state` optional unless the kind starts with `equilibrium_`. | Use as is. A converter fills the effect with the best-determined stated kind; `quantity_kind` names it. |
| Units | Only `fraction` and `dimensionless` for all four kinds. | Converters turn percent into fraction (exact factor 0.01) and ee into the major isomer's share (exact, two species). An equilibrium constant with a unit has no kind: reported, left `unavailable`. |
| `QUALITATIVE_STATEMENT` | Binding wording. | No new values; the reading for this class is "product detected / not detected / not stated" (section 4). Written beside the vocabulary by the coordinator. |
| `stated_strength` | Names only anchored binding types and `activity_rate`. | Must also name `product_distribution` (registration note 1b). |
| `ROLE`, `IMMOBILIZATION_SIDES`, `ROW_DEPENDENCE_KEYS` | Binding-flavoured. | The enzyme preparation maps to `analyte_preparation_ref`; `immobilized_preparation_ref`, `surface_ref` and `dataset_ref` handling as for the activity types (`dataset_ref` is stamped by the page). **No type of this class has an immobilized enzyme, a surface or an electrode, so `immobilized_preparation_ref` and `surface_ref` are None for all nine.** Each converter documents it. |
| Direction | `literature_direction` is binding-only. | A separate class-scoped function, written here; larger is stronger. |
| Pooling | `POOLED_UNIT_BY_CLASS` knows only `nM`. | `NOT_POOLED_CLASSES` gains the class (section 4). |
| Roles of the sheet | `effect`, `effect_variance`, `recovery`, `attributed_signal`, `total_signal`, `condition_test`, `condition_reference`, assertion and alternative predictions. | The share fills `effect`; `total_recovery` fills `recovery`; the other roles stay null with reasons. The two roles `attributed_signal` and `total_signal` could hold the product signal and the total signal, but the quantity kind already is the share; keeping the share in `effect` avoids counting it twice (open question 4). |
| One value, one method | Two methods in one paper (NMR and HPLC) can state different shares of one product. | A leaf records a share under a type only when the passage ties it to that method; otherwise no type can be named. |
| Several products in one reaction | One reaction gives several shares that sum to 1 and share one denominator: one measurement, not several independent ones (the HFP case). | One record states the share of ONE named product (its partner); the other species are other records of the same experiment. Whether they merge or count separately is open question 2. |

---

## 7. What is still open (for the owner, in plain words)

1. Is this list of nine right? In particular: are the two equilibrium-only types (enzymatic end-point, optical equilibrium) wanted, and should competition between several substrates be a type or only a fact on the record?
2. When one reaction gives three products and a paper states all three shares, should that be one result per product (each its own partner and its own row), or one result for the product the hypothesis names? The draft says one result per named product; the shares share one denominator, so
   they must not count as independent evidence for one claim.
3. The fraction and the ratio forms give different strengths for the same share (0.5 gives 0.95, ratio 1 gives 0.76). Do you want the two forms on one curve (the ratio's ends set so that both agree at every share), or is a difference acceptable?
4. Should a product share be the effect (the draft), or the sheet's attributed-over-total signal fraction, or both?
5. Is an equilibrium composition worth the same as an observed product share? It is enzyme-independent; the draft gives it the same ends and puts it last in the order of preference. Should its strong end be lower?
6. The noise end 0.01 (one percent) and strong end 0.9: confirm or give your own. They are the ends of the whole class.
7. Is "X was the only product" a stated detection (0.25 of the type's value, the draft) or should "only product" count more because it states an absence of others?
8. An equilibrium constant with a unit (for example in M^-1) has no place in the sheet's vocabulary. Add a kind, or leave such K unavailable?
9. Should the class use `catalyzes` (shared with `activity_rate`, which breaks `class_of_predicate` and the page's `sheet_class`) or its own predicate, for example `produces`?
10. The Codex sessions were not searched and no list of 150 papers for this class was found. Which real papers (with open full text, SOP step 6) should serve as the real paragraph of each type? Candidates in the repository are only the HFP NMR paper (PMC12051542) for `distribution_nmr` and the F420 partner paper (PMC8764529) for a product spectrum; none was checked for licence or for a usable paragraph.
