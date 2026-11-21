# A105 assay calibration details: how much should an unstated criterion still count?

Written 2026-11-21. Read-only research. No code was changed for this page. The weights below are **proposals for the
owner to decide**; each one has its reasoning written out, so the owner can check it.

Sources read: for each of the 25 binding types, `literature_<m>_criteria.py` and `literature_<m>_converter.py` in
`gene_annotation_episode/episodic_workflow/episode_support/literature/grading/experimental_activity_evidence/`.
That means the criterion questions, `CRITERIA_MAP`, and the `EXPERT_REVIEW` constants with their reasons. Also read:
`literature_row_contract.py`, `literature_resolution.py`, `literature_page_update.py` and the SOP
(`A105_EXPERIMENT_SOP.md`, step 4 of the OWNER RULE).

The method citations come from memory and were **not checked on the web**. Check volume and page numbers before
quoting them outside this page.

## 0. Facts about the code that shape the decision (read first)

1. **The unknown weight applies to SHEET criteria, not to native ones.**
   - `row_weight` reads the converter's `interpretations`. These are the pooled sheet criteria: `binding_controls`
     (BC), `binding_regime` (BR), `binding_parameter_definition` (BPD), `binding_species` (BS),
     `calibration_applicability` (CA) and `sampling_basis` (SB), plus `variance_correspondence`, which appears only
     when it is supported.
   - The pooling rule is: any conflicting member makes the sheet criterion conflicting; otherwise any unknown member
     makes it unknown.
   - So an unknown BC means **"at least one member is unstated"**, not "nothing is stated". In Trp quenching, for
     example, BC pools 7 native criteria and is unknown almost always.
   - A per-sheet-criterion weight is therefore coarse. A finer weight would need the converter to pass which members
     are unknown, which it does not do today. The weights below are set for the typical pattern of unstated members
     in each assay.
2. **What the weight scales.**
   - The per-result weight is the mean of r_c over the applicable sheet criteria.
   - A result whose criteria are all unknown gets exactly u. So u is "the reliability of a fully unvetted result of
     this type".
   - Rule 4b, a result with no applicable criterion, uses the same value. It should follow the per-type value too.
3. **Working-tree state (not my edits).**
   - Another session has added `WEIGHT_UNKNOWN_BY_TYPE` to `literature_row_contract.py` and threaded
     `experiment_type` through `literature_resolution.criterion_resolution`, `row_weight` and
     `literature_page_update._weight_input`.
   - That table sets 15 types and holds 10 at 0.9 as "PENDING".
   - The column "WT now" below shows those values for comparison. I did not edit them.
4. **The Trp converter uses `WEIGHT_UNKNOWN` inside a degree curve.** This happens in `_judge_excitation` (line 128)
   and `_judge_incubation` (line 171). The SOP step 4 forbids it ("Never use the unknown weight as part of a degree
   curve"). If the unknown weight becomes per type, those two judges will be tied to whichever constant they import.
   Someone should decouple them. Not done here, because converters are off limits.
5. **The working copies of some converters currently have no `EXPERT_REVIEW` constants.** This applies to AlphaScreen,
   radioligand, SPA, EMSA, SEC, dialysis and DSF; they are being softened right now. For those, the values quoted
   here are from `HEAD`.

## 1. Decision rule used for every assay

**u = the expected r_c of an unstated aspect**, computed as:

u ≈ P(adequate | unstated in the extracted text of a published paper) + P(not adequate) × E[degree | not adequate]

The rule is anchored so that label-free KD (SPR) gives the owner's 0.9:
- a reference surface and in-software referencing are near universal;
- when a detail is wrong, the KD is usually off by a factor, not meaningless.

The five owner questions are answered for each assay:
- **Q1** What does the assay measure; is the readout absolute, relative or semi-quantitative?
- **Q2** Is there a reference range we would trust without the paper?
- **Q3** What does an unstated control or calibration do to the number's meaning?
- **Q4** If we assume "fine" and are wrong, how badly does the score mislead?
- **Q5** Is this consistent with KD?

**The asymmetry behind all of it (Q4).**
- **KD-type assays:** a failed unstated detail mostly distorts the magnitude, for example a KD off by 2 to 10 times
  through depletion, mass transport or a missed plateau. The direction ("binds") usually survives, and the KD
  strength anchors already reduce a doubtful magnitude.
- **Relative or qualitative assays:** a failed unstated control (empty bait, autoactivation, single antibody, bead
  only, a non-interacting pair) turns background into a false "binds". The whole direction is wrong. That is why u
  drops more there.

**Per-sheet-criterion overrides.** Where a sheet criterion is clearly more benign or more critical than the assay
default, it gets its own value. The legend for criterion members:
- **b** = benign when unstated (intrinsic to the readout, an instrument default, or near-universal practice);
- **g** = a real gap (the number or the direction can be wrong and the paper would not show it);
- **p** = partly (usually fine, but it fails often enough to matter).

## 2. Summary: one line per assay

| assay | readout | proposed u (default) | overrides | WT now | one-line reason |
| --- | --- | --- | --- | --- | --- |
| spr | absolute KD (M), rates | **0.90** | none | 0.90 | The KD anchor: referencing is in-software and routine, KD has trusted ranges, and failures are mostly magnitude errors. |
| itc | absolute KD, dH, n | **0.90** | BR 0.85 | 0.85 | Absolute and self-calibrated (electrical calibration, dilution heats routine); the only real unstated gap is the c-window for tight binders. |
| bli | absolute KD (from rates) | **0.85** | BC 0.80 | 0.80 | Same physics as SPR, but the reference sensor and non-specific sticking to tips are not automatic. |
| gci | absolute KD (from rates) | **0.85** | none | 0.90 | SPR-like, but a smaller literature with fewer reporting conventions; the waveRAPID format changes the series check. |
| fp | relative mP; KD from the curve | **0.80** | BC 0.75, BR 0.75 | 0.75 | The curve calibrates itself (free and bound plateaus); tracer depletion and specificity are real gaps; a Ki needs the tracer KD. |
| fret | relative ratio; KD/Ki from the curve | **0.75** | BC 0.70, BPD 0.70, CA 0.85 | 0.70 | The ratio and time gating are instrument defaults; indirect (antibody) labelling and compound interference are real gaps. |
| mst | relative Fnorm; KD from the curve | **0.75** | BC 0.70 | 0.75 | Composite signal; initial-fluorescence and aggregation artefacts are the main failure modes and need in-paper checks. |
| trp_quenching | relative fluorescence change | **0.70** | BC 0.60 | 0.65 | Inner filter and quenching mechanism are often uncorrected (a well-documented problem); protein at uM can deplete. |
| fcs | relative diffusion change; KD from fraction bound | **0.80** | CA 0.75 | 0.90 (pending) | Fraction bound uses its own free-probe reference (volume calibration matters only for absolute D); brightness change and aggregates are gaps. |
| elisa | semi-quantitative OD; apparent KD/EC50 | **0.70** | BC 0.65, BR 0.65 | 0.60 | Not at equilibrium after the washes; coating, activity and avidity are lab-specific; blank subtraction is benign. |
| alphascreen | relative amplified counts; apparent constant | **0.65** | BC 0.60, BR 0.60 | 0.90 (pending) | Bead avidity, the hook effect and frequent-hitter interference make the constant format-specific. |
| radioligand | absolute bound (fmol via specific activity); KD; Ki via Cheng-Prusoff | **0.85** | BC 0.90, BR 0.80, CA 0.80 | 0.90 (pending) | A mature field with universal non-specific-binding practice; depletion and equilibrium are the usual unstated failures. |
| spa | as radioligand, homogeneous | **0.80** | CA 0.75 | 0.90 (pending) | Radioligand logic plus bead background, colour quench and settling, which are less routinely reported. |
| pulldown | qualitative band (presence vs control lane) | **0.70** | BC 0.55, BS 0.60, SB 0.80 | 0.90 (pending) | Meaning comes from the negative-control capture; "direct" vs "in a complex" is a gap for "binds"; washes and inputs are benign. |
| emsa | fraction shifted (relative to free probe in the lane); apparent KD | **0.75** | BC 0.60 | 0.90 (pending) | Self-referenced lanes and the probe usually below KD; specific competition and protein identity carry the meaning. |
| sec | co-elution (qualitative); apparent KD rare | **0.75** | BR 0.60, CA 0.90 | 0.90 (pending) | Co-elution is robust for tight complexes; dilution on the column biases any KD; column calibration is irrelevant to co-elution. |
| dialysis | absolute free and bound concentrations | **0.85** | CA 0.80 | 0.90 (pending) | A direct measurement with a standard protocol; recovery and device adsorption are the gaps (hydrophobic ligands). |
| auc | absolute s and M from first principles; KD from an isotherm | **0.85** | BR 0.75 | 0.90 (pending) | Hydrodynamics are absolute; a KD needs loading concentrations spanning it, which is a real gap if unstated. |
| dsf | absolute dTm (deg C), but affinity only model-derived | **0.70** | BC 0.80, BR 0.65 | 0.90 (pending) | A dTm implies its protein-alone reference; its link to affinity depends on the unfolding thermodynamics and the dose series. |
| cetsa | relative soluble fraction vs vehicle; EC50 is not a KD | **0.65** | BC 0.55 | 0.60 | In-cell stabilisation can be indirect; negative-compound, specificity and total-level controls carry the meaning. |
| bret | relative BRET ratio (net over donor only) | **0.70** | BC 0.60, BR 0.60 | 0.65 | Bystander BRET at high expression; a negative pair and saturation/expression matching define specificity. |
| y2h | qualitative reporter growth / fold | **0.60** | BC 0.50, BS 0.80, SB 0.80 | 0.50 | The direction rests wholly on autoactivation and non-interacting controls; expression is implied by a positive. |
| split_reporter | relative reconstituted signal; apparent KD | **0.65** | BC 0.55, BR 0.60 | 0.60 | Fragment-alone and unrelated-pair controls define the meaning; BiFC is irreversible, so its "KD" is not an equilibrium. |
| pla | semi-quantitative puncta per cell vs control | **0.55** | BC 0.50, CA 0.50, BR 0.70, SB 0.80 | 0.50 | 40 nm proximity is not binding; antibody specificity is the dominant unstated risk. |
| proximity | relative MS enrichment (fold, FDR) | **0.60** | BPD 0.55, CA 0.85, SB 0.80 | 0.55 | Proximity within about 10 nm is not binding; a reported fold or FDR implies a control existed; bait overexpression is a gap. |

**Rule 4b** (a result with no applicable criterion): use the assay default u.

**Q5 for the whole table:**
- Only the label-free KD methods and ITC stay at 0.85 to 0.9. They are the only ones where the number is absolute,
  generally plausible ranges exist, and unstated details are mostly benign.
- Everything else is lower in proportion to how much of its meaning lives in in-paper controls.

---

## 3. Per assay

Each assay below follows the same layout:
- the five answers (Q1 to Q5);
- a table of sheet criterion | members (with b, g or p) | proposed u.

Constants named are the converter's `EXPERT_REVIEW` values; they apply to stated values only.

### SPR, u = 0.90 (the anchor)

- **Q1:** Absolute KD in M, also kon and koff, from a refractive-index response. RU is instrument-specific, but the
  KD is not.
- **Q2:** Yes. KDs of protein-protein and small-molecule pairs have well-known ranges. The converter's ranges
  (concentrations 0.2x to 5x KD, chi2/Rmax at most 0.1, Rmax ratio 0.3 to 1.2) are standard practice.
  Sources: Myszka 1999, J Mol Recognit 12:279 (double referencing); Katsamba et al. 2006, Anal Biochem 352:208
  (multi-user benchmark).
- **Q3:** Reference subtraction is done by the instrument software and is near universal, so it is benign. Mass
  transport and the bracketing of KD are the real unstated failures. The Rich & Myszka annual biosensor literature
  surveys (J Mol Recognit, 2000s) repeatedly found avoidable problems in published data. Those failures shift the
  KD; they do not invent binding.
- **Q4:** A moderate magnitude error. The direction is rarely wrong.
- **Q5:** This is the KD case.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | reference_subtraction b, baseline_regeneration b | 0.90 |
| BR | concentration_series p, mass_transport p, steady_state_vs_kinetic b (n/a if only one) | 0.90 (the most likely real gap; 0.85 would be defensible) |
| BPD | fit_model p, kinetic_consistency b | 0.90 |
| BS | immobilized_activity p | 0.90 |
| CA | rmax_consistency p | 0.90 |
| SB | replicates b | 0.90 |

### ITC, u = 0.90; BR 0.85

- **Q1:** Absolute KD, dH and n. The heat is electrically calibrated in the instrument.
- **Q2:** Yes. Usable c window about 1 to 1000. Sources: Wiseman et al. 1989, Anal Biochem 179:131; Turnbull &
  Daranas 2003, JACS 125:14859.
- **Q3:**
  - Benign: dilution-heat subtraction and buffer matching are routine; the temperature is almost always 15 to 37 C.
  - Real gap: an unstated concentration hides c. Tight binders (KD below about 10 nM) are unidentifiable by direct
    titration (Velazquez-Campoy & Freire 2006, Nat Protoc 1:186).
  - Partial: n consistency depends on the active fraction. It shifts n much more than KD. Inter-lab spread is in
    Myszka et al. 2003, J Biomol Tech 14:247.
- **Q4:** A magnitude error. The heat of a non-binder is not a sigmoid, so a false "binds" is rare.
- **Q5:** Absolute like SPR, so 0.9, with BR at 0.85 for the c-window.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | heat_of_dilution_control b, buffer_matching b | 0.90 |
| BR | c_value_window g (tight KD), injections_sufficient b, temperature_stated_and_controlled b | 0.85 |
| BPD | fit_model_appropriate p, thermodynamic_consistency b | 0.90 |
| BS | concentration_accuracy_and_active_fraction p | 0.90 |
| CA | stoichiometry_consistency p | 0.90 |
| SB | replicate_titrations_independent b | 0.90 |

### BLI, u = 0.85; BC 0.80

- **Q1:** Absolute KD from kon and koff; the wavelength shift in nm is instrument-specific.
- **Q2:** Yes, for the KD. Loading about 2 nm and decay of at least 5 % are vendor guidance. Sources: Abdiche et al.
  2008, Anal Biochem 377:209; Concepcion et al. 2009, Comb Chem HTS 12:791.
- **Q3:**
  - Real gap: the reference sensor and the blank-sensor non-specific check are separate wells the user must set up.
    Non-specific sticking to tips (especially Ni-NTA and streptavidin tips) is common.
  - Partial: avidity and rebinding on crowded tips; a short dissociation step gives an extrapolated koff.
- **Q4:** A non-specific tip shift can create an apparent binder, so it is worse than SPR, but still mainly a
  magnitude problem.
- **Q5:** Slightly below SPR.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | reference_subtraction p, nonspecific_binding_control g, baseline_and_regeneration b | 0.80 |
| BR | concentration_series p, dissociation_window p, avidity_and_mass_transport p, steady_state_vs_kinetic b | 0.85 |
| BPD | fit_model p, kinetic_consistency b | 0.85 |
| BS | immobilized_activity p | 0.85 |
| CA | loading_and_response p | 0.85 |
| SB | replicates b | 0.90 |

### GCI, u = 0.85

- **Q1:** Absolute KD from rates, with a mass-sensitive response (pg/mm2).
- **Q2:** Yes, for the KD. The waveRAPID single-concentration pulsed format is in Kartal et al. 2021, SLAS Discov
  26:995.
- **Q3:**
  - Benign: referencing and DMSO/bulk correction are in-software.
  - Partial: the non-specific check and crowding.
  - The physics is SPR's, but the method has a smaller literature and fewer reporting habits.
- **Q4:** A magnitude error.
- **Q5:** Slightly below SPR. The WT value of 0.9 is defensible too; I propose 0.85 because the reporting conventions
  are less established.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | reference_subtraction b, bulk_solvent_correction b, nonspecific_binding_control p, baseline_and_regeneration b | 0.85 |
| BR | concentration_series p, mass_transport p, steady_state_vs_kinetic b | 0.85 |
| BPD | fit_model p, kinetic_consistency b | 0.85 |
| BS | immobilized_activity p | 0.85 |
| CA | surface_level_and_response p | 0.85 |
| SB | replicates b | 0.90 |

### FP, u = 0.80; BC 0.75, BR 0.75

- **Q1:** A relative signal (mP). The KD or Ki comes from the concentration axis, and the free and bound plateaus
  calibrate the signal within the experiment.
- **Q2:** Yes, for the KD. Window at least 70 to 100 mP; tracer at or below KD. A Ki needs the tracer KD
  (Nikolovska-Coleska et al. 2004, Anal Biochem 332:261; Huang 2003, J Biomol Screen 8:34: resolvable potency is
  limited by the tracer). See also Rossi & Taylor 2011, Nat Protoc 6:365.
- **Q3:**
  - Benign: the free-probe baseline is intrinsic to a fitted curve, and detergent or non-binding plates are routine.
  - Real gap: the tracer concentration relative to KD (tight binders read as "KD = half the tracer"); the
    specificity/displacement control; a change of fluorescence intensity (scaled by the converter's
    INTENSITY_CHANGE_MAX_PERCENT of 30 %).
- **Q4:** Mostly a magnitude error. A sticky or aggregating titrant can raise mP without real binding, which is a
  partial direction risk.
- **Q5:** One step below the label-free methods.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | free_probe_baseline b, specificity_control g, surface_adsorption b | 0.75 |
| BR | tracer_concentration g, concentration_series p, equilibrium p, direct_vs_competition b | 0.75 |
| BPD | fit_model p, intensity_change p | 0.80 |
| CA | assay_window b (a fitted curve implies a window) | 0.85 |
| SB | replicates b | 0.85 |

### FRET / TR-FRET, u = 0.75; BC 0.70, BPD 0.70, CA 0.85

- **Q1:** A relative emission ratio; the KD or Ki comes from the curve.
- **Q2:** Yes, for the KD. Z' of 0.5 or more (Zhang, Chung & Oldenburg 1999, J Biomol Screen 4:67); delay 50 to
  150 us (Degorce et al. 2009, Curr Chem Genomics 3:22); see also Hieb et al. 2012, NAR 40:e33.
- **Q3:**
  - Benign: the ratiometric read and time gating are instrument and kit defaults.
  - Real gap: the crosstalk correction in plain FRET; indirect labelling through an antibody or streptavidin (the
    constant can reflect the detection complex); compound interference (inner filter, quenching); a specificity
    control.
- **Q4:** Magnitude errors, plus an apparent "binding" from a compound that is itself an artefact.
- **Q5:** Below FP, because there are more format-specific failure modes.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | spectral_crosstalk p, specificity_control g, compound_interference g | 0.70 |
| BR | labelled_concentration g, concentration_series p, equilibrium p, direct_vs_competition b | 0.75 |
| BPD | fit_model p, labelling_scheme g, ratiometric_readout b | 0.70 |
| CA | assay_window b, time_gating b | 0.85 |
| SB | replicates b | 0.85 |

### MST, u = 0.75; BC 0.70

- **Q1:** A relative Fnorm (thermophoresis or T-jump); the KD comes from the curve.
- **Q2:** Yes, for the KD. Signal-to-noise of 5 or more is vendor guidance. Sources: Jerabek-Willemsen et al. 2014,
  J Mol Struct 1077:101; the multi-lab benchmark López-Méndez et al. 2021, Eur Biophys J 50:653; Scheuermann et al.
  2016, Biochemistry 55:6309 (artefacts).
- **Q3:**
  - Benign: the fluorescence level and the F-hot window are vendor software defaults.
  - Real gap: a change of the initial fluorescence (it mimics binding unless an SD test is run); aggregation or
    adsorption; a label effect.
- **Q4:** An initial-fluorescence or aggregation artefact can create a fully apparent binder, so there is a real
  direction risk.
- **Q5:** Below FP.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | initial_fluorescence g, aggregation_adsorption g, specificity_control g, fluorescence_level b | 0.70 |
| BR | labelled_concentration p, concentration_series p, equilibrium p, direct_vs_competition b | 0.75 |
| BPD | fit_model p, labelling_scheme p, readout_window b | 0.75 |
| CA | signal_amplitude b (a fitted curve implies one) | 0.80 |
| SB | replicates b | 0.85 |

### Trp quenching, u = 0.70; BC 0.60

- **Q1:** A relative change of intrinsic fluorescence; the KD comes from the curve. Ksv is excluded from the effect.
- **Q2:** Partly. The physics of the inner filter (correction factor 10^((Aex+Aem)/2)) and of excitation at 295 nm is
  textbook (Lakowicz, Principles of Fluorescence Spectroscopy, 3rd ed. 2006).
  - van de Weert & Stella 2011, J Mol Struct 998:144 document that many published quenching-based binding studies
    skip the inner-filter correction or misuse Stern-Volmer.
- **Q3:**
  - Benign: the buffer blank; dilution (usually under 5 %); photobleaching for short reads.
  - Real gap: the inner filter for absorbing ligands (nucleotides, aromatics, dyes); ligand fluorescence; static vs
    dynamic quenching; the protein (uM) relative to KD.
- **Q4:** An uncorrected inner filter alone produces a saturating-looking "quench" from a non-binder. That is a
  direction risk.
- **Q5:** Clearly below the label-free methods.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | inner_filter g, dilution b, buffer_blank b, ligand_fluorescence g, specificity_control g, photobleaching b, quenching_mechanism p | 0.60 |
| BR | saturation p, concentration_series p, protein_concentration g, equilibrium b | 0.75 |
| BPD | fit_model p, excitation_selectivity p | 0.70 |
| CA | signal_amplitude b | 0.80 |
| SB | replicates b | 0.85 |

### FCS / FCCS, u = 0.80; CA 0.75

- **Q1:**
  - Diffusion times are relative to the free labelled partner measured in the same setup.
  - The fraction bound gives a KD on the concentration axis.
  - An absolute D needs volume calibration; a fraction bound does not.
- **Q2:** Yes, for the KD. Particle number 0.1 to 10. Resolving two species needs a diffusion-time ratio of about 1.6
  or more (Meseth et al. 1999, Biophys J 76:1619). Source: Haustein & Schwille 2007, Annu Rev Biophys Biomol Struct
  36:151.
- **Q3:**
  - Benign: volume calibration, triplet state and background, because standard fit models include them and the
    fraction bound is self-referenced.
  - Real gap: the brightness change on binding; bright aggregates (they dominate the correlation); a label on the
    larger partner, which gives too small a diffusion change.
- **Q4:** Aggregates can mimic a slow "complex", a partial direction risk; otherwise a magnitude error.
- **Q5:** A solution titration with its own reference, near FP.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | volume_calibration b, triplet_state b, brightness p, crosstalk p (FCCS), background b, aggregates g, photobleaching b, surface_adsorption b, labelling p, specificity_control g | 0.80 |
| BR | saturation p, labelled_range b, labelled_over_kd p, concentration_series p, equilibrium b | 0.80 |
| BPD | diffusion_model b, fit_model p | 0.80 |
| CA | diffusion_change g, mass_consistency p, acquisition b | 0.75 |
| SB | replicates b | 0.85 |

### ELISA, u = 0.70; BC 0.65, BR 0.65

- **Q1:** Semi-quantitative OD from a solid phase; an apparent KD or EC50, not a solution KD.
- **Q2:** Only weakly.
  - The solid-phase "KD" depends on coating density, avidity and washes.
  - Friguet et al. 1985, J Immunol Methods 77:305 is the reason a solution-phase ELISA exists.
  - Butler et al. 1992, J Immunol Methods 150:77 found that adsorbed proteins are often partly denatured.
  - See also the Assay Guidance Manual (NCBI), Immunoassay Methods chapter.
- **Q3:**
  - Benign: blank subtraction, and a signal window and reader linearity under 2 OD.
  - Real gap: equilibrium and dissociation during the washes (the readout is not at equilibrium); avidity of a
    bivalent detection reagent or coat; the activity of the coated protein; a specificity control.
- **Q4:** Sticky proteins on polystyrene give "binding" without a non-binder control. That is a direction risk.
- **Q5:** Clearly below the solution titrations.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | blank_subtraction b, specificity_control g, avidity g, coated_protein_activity p, detection_interference p | 0.65 |
| BR | saturation p, concentration_series p, equilibrium p, wash_dissociation g, direct_vs_competition b | 0.65 |
| BPD | fit_model p | 0.75 |
| CA | signal_window b, detector_range b | 0.80 |
| SB | replicates p | 0.80 |

### AlphaScreen / AlphaLISA, u = 0.65; BC 0.60, BR 0.60

- **Q1:** Relative amplified counts from bead proximity; an apparent constant.
- **Q2:** Weak. Z' of 0.5 or more (Zhang 1999); S/B of 10 or more. Sources: Eglen et al. 2008, Curr Chem Genomics
  1:2; Yasgar et al. 2016, Methods Mol Biol 1439:77.
  - Frequent-hitter interference: PAINS were defined from AlphaScreen data (Baell & Holloway 2010, J Med Chem
    53:2719).
- **Q3:**
  - Benign: light protection and the reader range.
  - Real gap: the hook effect; partner depletion and bead capacity; avidity of bead-presented partners; the
    interference counter-screen (TruHits) for a compound Ki; capture or tag artefacts.
- **Q4:** Interference compounds read as inhibitors and a hook effect reads as a "constant". That is a direction and
  magnitude risk.
- **Q5:** Below ELISA for compounds; about equal for protein-protein pairs.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | specificity_control g, capture_artifacts p, avidity g, interference_counter_screen g, light_protection b | 0.60 |
| BR | partner_depletion g, hook_effect g, concentration_series p, equilibrium p, direct_vs_competition b | 0.60 |
| BPD | fit_model p | 0.70 |
| CA | signal_window b, assay_quality b, detector_range b | 0.80 |
| SB | replicates p | 0.80 |

### Radioligand (filtration), u = 0.85; BC 0.90, BR 0.80, CA 0.80

- **Q1:** Absolute bound in fmol, via specific activity. KD and Bmax are absolute. A Ki is relative to the
  radioligand KD (Cheng & Prusoff 1973, Biochem Pharmacol 22:3099).
- **Q2:** Yes. Rules such as under 10 % bound, NSB under 50 % and an excess of at least 100x KD are long-standing
  receptor-pharmacology rules. Sources: Hulme & Trevethick 2010, Br J Pharmacol 161:1219; Motulsky & Neubig, Curr
  Protoc Neurosci 7.5; Assay Guidance Manual, Receptor Binding Assays chapter.
- **Q3:**
  - Benign: defining and subtracting NSB is universal; PEI-soaked filters are routine; vendor radioligand purity.
  - Real gap: ligand depletion and equilibrium, which Hulme & Trevethick name as the common published failures; a
    fast off-rate during the wash.
  - Partial: an unstated radioligand KD for Cheng-Prusoff, which is usually from the same lab or cited.
- **Q4:** A magnitude error. A specific-binding signal from an excess-displaceable site rarely fakes direction.
- **Q5:** Near the label-free KD methods.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | nonspecific_binding b, nonspecific_excess b, radioligand_quality b, filter_binding b | 0.90 |
| BR | equilibrium g, radioligand_range p, competition_radioligand_level p, wash_dissociation p | 0.80 |
| BPD | fit_model b, nonlinear_fit b, hill_slope p, cheng_prusoff p | 0.85 |
| CA | ligand_depletion g, nonspecific_fraction p | 0.80 |
| SB | replicates b | 0.90 |

### SPA, u = 0.80; CA 0.75

- **Q1:** As for radioligand, but homogeneous: counts from proximity to the bead.
- **Q2:** As for radioligand. Sources: Bosworth & Towers 1989, Nature 341:167; Wu & Liu 2005, BioDrugs 19:383.
- **Q3:**
  - Benign: the no-wash format means it is at equilibrium when read.
  - Real gap: the bead-only and non-proximity background; colour quench from compounds; bead settling. These are
    reported less routinely than NSB in filtration assays.
- **Q4:** Mostly a magnitude error; quench can fake inhibition.
- **Q5:** Slightly below radioligand.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | nonspecific_binding b, nonspecific_excess b, nonproximity_signal p, bead_only_control p, radioligand_quality b | 0.80 |
| BR | equilibrium b, radioligand_range p, competition_radioligand_level p, homogeneous_format b | 0.85 |
| BPD | fit_model b, nonlinear_fit b, hill_slope p, cheng_prusoff p | 0.85 |
| CA | ligand_depletion p, nonspecific_fraction p, quench_interference g, bead_settling p | 0.75 |
| SB | replicates b | 0.85 |

### Pull-down / co-IP, u = 0.70; BC 0.55, BS 0.60, SB 0.80

- **Q1:** Qualitative: presence of the prey in the eluate relative to a control capture. No constant.
- **Q2:** No reference value. The meaning exists only against the in-paper control.
  - The CRAPome lists the proteins that are routinely captured non-specifically (Mellacheruvu et al. 2013, Nat
    Methods 10:730).
  - Nucleic-acid bridging is a known false-positive source (Nguyen & Goodrich 2006, Nat Methods 3:135).
  - See also Phizicky & Fields 1995, Microbiol Rev 59:94.
- **Q3:**
  - Benign: wash stringency (150 to 500 mM NaCl with detergent is typical); incubation; the input lane (it matters
    only for negatives); quantification.
  - Real gap: the bead-only, IgG or empty-bait capture; the nuclease treatment; direct vs in-complex (a co-IP from
    lysate shows association, not direct binding).
  - Mitigation: published co-IP figures nearly always show an IgG or empty-bait lane, and extraction from text
    misses it. This is why BC is 0.55 and not lower.
- **Q4:** Without the control, a sticky prey is a full false "binds". The severity is total.
- **Q5:** Well below KD. It is a relative assay whose controls define the readout.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | negative_control g, bait_minus_control g, input_lane b, reciprocal p, competition p, nuclease g, specificity p | 0.55 |
| BR | wash_stringency b, wash_count b, incubation b | 0.85 |
| BS | expression_level p, direct_interaction g | 0.60 |
| BPD | prey_in_eluate b (a statement implies it), enrichment p | 0.75 |
| CA | quantification b | 0.85 |
| SB | replicates p | 0.80 |

### EMSA, u = 0.75; BC 0.60

- **Q1:** The fraction shifted, relative to the free probe in the same lane. It gives an apparent KD in concentration
  units when the probe is at or below KD. In qualitative mode it is a shift / no shift.
- **Q2:** Partly. The probe is usually radiolabelled or fluorescent at pM to low nM, so below most KDs. The caveats
  are the cage effect and dissociation during the run. Sources: Hellman & Fried 2007, Nat Protoc 2:1849; Fried &
  Crothers 1981, NAR 9:6505; Ryder, Recht & Williamson 2008, Methods Mol Biol 488:99.
- **Q3:**
  - Benign: the probe-alone lane (near universal); a 15 to 30 min incubation.
  - Real gap: specific vs non-specific competition, a mutant probe, and protein identity in crude extracts
    (supershift). These decide whether the band is the protein under study binding this site.
- **Q4:** A non-specific DNA-binding protein in an extract gives a false "binds" of the claimed protein. That is a
  direction risk.
- **Q5:** In quantitative mode, near the solution titrations, except for the controls.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | specific_competition g, nonspecific_competition p, mutant_probe p, probe_alone_lane b, nonspecific_protein_control p, protein_identity g | 0.60 |
| BR | equilibrium b, complex_stability p, probe_concentration p, protein_range p, titration_points p | 0.75 |
| BPD | shift_observed b, single_complex p, fit_model p | 0.80 |
| CA | free_probe_quantified p, saturation p | 0.80 |
| SB | replicates b | 0.85 |

### SEC (and SEC-MALS), u = 0.75; BR 0.60, CA 0.90

- **Q1:** Mostly qualitative co-elution; MALS gives an absolute mass; an apparent KD is rare and biased.
- **Q2:** For mass, yes (MALS is within 5 to 10 %; Folta-Stogniew & Williams 1999, J Biomol Tech 10:51). For a KD, no:
  the 10 to 20-fold dilution on the column means weak complexes dissociate.
- **Q3:**
  - Benign: column calibration (it matters only for size estimates, not co-elution); resin interaction at
    100 to 150 mM salt; running the components alone (standard).
  - Real gap: stability on the column relative to KD; a single-component (non-binding mutant) control.
  - Partial: aggregation that co-elutes.
- **Q4:** An aggregate peak can be mistaken for a complex (a partial direction risk). A weak complex is missed
  (a false negative, not a false "binds").
- **Q5:** Below KD methods in quantitative mode; robust in qualitative mode for tight complexes.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | components_alone b, complex_composition p, single_component_control p, resin_interaction b, monodispersity p | 0.75 |
| BR | complex_stable_on_column g, titration_depletion p | 0.60 |
| BPD | complex_peak_observed b, elution_shift p, mals_mass p, stoichiometry p | 0.75 |
| CA | column_calibration b | 0.90 |
| SB | replicates b | 0.85 |

### Equilibrium dialysis, u = 0.85; CA 0.80

- **Q1:** Absolute free and total ligand concentrations (a detector with a standard curve); an absolute KD or Ki.
- **Q2:** Yes. Rapid equilibrium dialysis runs 4 to 6 h; recovery 80 to 120 % (Waters et al. 2008, J Pharm Sci
  97:4586); Klotz 1982, Science 217:1247 on fitting.
- **Q3:**
  - Benign: the buffer-only control and membrane retention (standard MWCO); the Donnan effect at about 150 mM salt.
  - Real gap: recovery and device adsorption for hydrophobic ligands; time to equilibrium for large ligands.
- **Q4:** Adsorption inflates "bound", so apparent binding can come from the device. That is a partial direction
  risk, mostly for small hydrophobic molecules.
- **Q5:** Absolute like ITC; 0.85 because of the adsorption gap.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | buffer_only_control b, protein_retained b, device_adsorption p, ligand_stability b | 0.85 |
| BR | equilibrium p, ligand_depletion p, protein_level p, concentration_series p, volume_shift b | 0.85 |
| BPD | binding_observed b, fit_model b | 0.90 |
| CA | recovery g, free_measured_directly p, free_fraction_measurable p | 0.80 |
| SB | replicates b | 0.90 |

### AUC (SV / SE), u = 0.85; BR 0.75

- **Q1:** Absolute s and M from first principles; a KD from an isotherm over loading concentrations.
- **Q2:** Yes, for s and M. Sources: Schuck 2000, Biophys J 78:1606 (c(s)); Cole et al. 2008, Methods Cell Biol
  84:143.
  - Instrument calibration errors (temperature, radius, time) shift s by a few percent without external references
    (Zhao et al. 2015, PLoS One 10:e0126420). This matters for exact s, not for detecting a complex.
- **Q3:**
  - Benign: buffer density and viscosity (SEDNTERP is routine); the components run alone (standard).
  - Real gap: loading concentrations spanning the KD and the evidence of reversibility (a single concentration gives
    presence, not a KD).
- **Q4:** Aggregation or self-association can be read as a complex; homogeneity checks address it. Mostly a
  magnitude error.
- **Q5:** Absolute, near ITC.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | components_alone b, component_homogeneity p, non_binding_control p | 0.85 |
| BR | concentration_series g, concentration_range g, reversibility p, equilibrium_reached b, multiple_speeds b | 0.75 |
| BPD | complex_observed b, sedimentation_shift p, mass p, stoichiometry p | 0.85 |
| CA | fit_quality p, buffer_correction b | 0.90 |
| SB | replicates b | 0.85 |

### DSF / thermal shift, u = 0.70; BC 0.80, BR 0.65

- **Q1:** dTm is absolute in deg C. An affinity from it is model-derived: it depends on the unfolding enthalpy, the
  ligand concentration and the heating rate.
- **Q2:** For "is there a shift", yes: 2 C or more is a common hit call (Niesen, Berglund & Vedadi 2007, Nat Protoc
  2:2212). For affinity, no general mapping. dTm does not rank affinity across ligands (Matulis et al. 2005,
  Biochemistry 44:5258; Bai et al. 2019, Sci Rep 9:2650; Vivoli et al. 2014, JoVE 91:51809).
- **Q3:**
  - Benign: the protein-alone reference (a reported dTm implies it); a heating rate of 1 to 2 C/min (instrument
    default).
  - Real gap: the ligand-alone and dye interference (hydrophobic or fluorescent compounds); a dose series for any
    KD; multi-transition curves.
- **Q4:** Dye-compound artefacts give false shifts (a partial direction risk). The apparent KD can be off by orders
  of magnitude without its model.
- **Q5:** Below the solution titrations.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | protein_alone_control b, ligand_alone_control p | 0.80 |
| BR | dose_dependence g (for a KD), concentration_series p, concentration_range g | 0.65 |
| BPD | shift_observed b, shift_size p, shift_over_spread p | 0.70 |
| CA | curve_quality p, heating_rate b | 0.80 |
| SB | replicates b | 0.85 |

### CETSA, u = 0.65; BC 0.55

- **Q1:** The soluble fraction relative to vehicle (a western blot or MS). An ITDR EC50 is an apparent engagement
  value, not a KD: it depends on the heating temperature and time and on cell permeability.
- **Q2:** For a shift, partly: true binders mostly give 2 to 10 C. Sources: Martinez Molina et al. 2013, Science
  341:84; Jafari et al. 2014, Nat Protoc 9:2100. For EC50, no general mapping.
- **Q3:**
  - Benign: the vehicle control (a shift implies it); a loading control (routine).
  - Real gap: a negative compound; a specificity control (mutant, knockdown, competition); the total-level control.
    In intact cells, stabilisation can be indirect, through pathway or complex changes. Proteome-wide TPP shows
    downstream shifts (Savitski et al. 2014, Science 346:1255784).
- **Q4:** An indirect shift is a false "binds". The direction risk is real.
- **Q5:** Below DSF (in-cell), with relative controls.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | vehicle_control b, loading_control b, negative_control g, specificity_control g, total_level_control g | 0.55 |
| BR | temperature_series p, isothermal_window p, dose_response p, concentration_range p | 0.65 |
| BPD | engagement_observed b, thermal_shift p | 0.70 |
| CA | cell_integrity p | 0.70 |
| SB | replicates p | 0.80 |

### BRET (saturation / NanoBRET), u = 0.70; BC 0.60, BR 0.60

- **Q1:** A relative net BRET ratio over donor-only. BRET50 is a relative acceptor:donor quantity. A NanoBRET
  target-engagement Ki is an in-cell apparent constant that needs the tracer KD (Robers et al. 2015, Nat Commun
  6:10091).
- **Q2:** Weak, because the values depend on expression. Sources: Pfleger & Eidne 2006, Nat Methods 3:165; James et
  al. 2006, Nat Methods 3:1001.
  - Saturation curves alone may not separate specific from bystander BRET (Felce et al. 2017, Cell Rep 20:2654).
- **Q3:**
  - Benign: the donor-only background subtraction (routine).
  - Real gap: the negative-control pair; expression matching and the acceptor:donor ratio; showing saturation.
- **Q4:** Overexpressed membrane proteins give bystander BRET, a full false "binds".
- **Q5:** Below the in-vitro titrations. The tracer mode is closer to FP.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | donor_only_control b, acceptor_only_control b, negative_control g, orientation p | 0.60 |
| BR | saturation_shown g, titration_points p, ratio_range p, expression_matching g, competition p | 0.60 |
| BPD | interaction_observed b, bret50_specificity p, signal_over_control p | 0.70 |
| CA | fit_quality p, background_correction b | 0.80 |
| SB | replicates p | 0.80 |

### Yeast two-hybrid, u = 0.60; BC 0.50, BS 0.80, SB 0.80

- **Q1:** Qualitative reporter growth or beta-gal fold over an empty-vector control.
- **Q2:** No physical reference. Sources: Fields & Song 1989, Nature 340:245.
  - Historical large-scale Y2H had high false-positive rates (von Mering et al. 2002, Nature 417:399).
  - Controlled modern pipelines are far better (Braun et al. 2009, Nat Methods 6:91; Dreze et al. 2010, Methods
    Enzymol 470:281, on autoactivator removal).
- **Q3:**
  - Benign: the positive control; non-selective growth; expression verified (a positive implies expression); a
    reciprocal orientation that is missing (many true pairs work one way only).
  - Real gap: bait and prey autoactivation; a non-interacting control. These are the whole meaning of a positive.
- **Q4:** An autoactivating bait is a full false "binds". The severity is total.
- **Q5:** Far below KD. Kept at 0.60 and not 0.50 because autoactivation testing is standard and often omitted only
  from the text.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | bait_autoactivation g, prey_autoactivation g, non_interacting_control g, positive_control b, nonselective_growth b, reciprocal_orientation b | 0.50 |
| BS | expression_verified b | 0.80 |
| BPD | interaction_observed b, reporter_concordance p, reporter_fold p | 0.60 |
| SB | replicates p | 0.80 |

### Split reporter (BiFC, split luciferase / NanoBiT), u = 0.65; BC 0.55, BR 0.60

- **Q1:** A relative reconstituted signal over background; an apparent in-cell KD.
- **Q2:** No physical reference. BiFC is irreversible: it traps transient or random encounters, and its "KD" is not
  an equilibrium (Kerppola 2006, Nat Rev Mol Cell Biol 7:449; Hu, Chinenov & Kerppola 2002, Mol Cell 9:789).
  NanoBiT was designed to be reversible with a weak fragment affinity (Dixon et al. 2016, ACS Chem Biol 11:400).
- **Q3:**
  - Benign: background correction; the positive control.
  - Real gap: fragment-alone and unrelated-pair controls (fragment self-assembly at high expression); a
    binding-mutant control; reversibility for any KD.
- **Q4:** Self-assembly is a full false "binds".
- **Q5:** Below BRET for BiFC, near BRET for NanoBiT.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | fragment_alone_control g, unrelated_pair_control g, binding_mutant_control p, positive_control b | 0.55 |
| BR | fusion_orientations p, saturable_titration p, titration_series p, titration_range p, reversible_reporter g | 0.60 |
| BPD | interaction_observed b, signal_to_background p, negative_control_ratio p | 0.65 |
| CA | expression_verified p, background_correction b | 0.75 |
| SB | replicates p | 0.80 |

### PLA, u = 0.55; BC 0.50, CA 0.50, BR 0.70, SB 0.80

- **Q1:** Semi-quantitative puncta per cell relative to a control. It shows proximity within about 40 nm, not
  binding.
- **Q2:** No physical reference. Sources: Söderberg et al. 2006, Nat Methods 3:995; Alam 2018, Curr Protoc Immunol
  123:e58. Antibody validation is the dominant uncertainty (Uhlen et al. 2016, Nat Methods 13:823).
- **Q3:**
  - Benign: the single-antibody and no-primary controls (kit standard); antibody species (the kit requires it).
  - Real gap: antibody validation; a knockdown or knockout specificity control; blinded quantification.
- **Q4:** A cross-reactive antibody gives a full false "binds". Proximity is also not binding, but that already lowers
  the qualitative strength.
- **Q5:** Far below KD.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | single_antibody_control p, no_primary_control b, specificity_control g, positive_control b | 0.50 |
| BR | compartment p | 0.70 |
| BPD | proximity_observed b, puncta_enrichment p, antibody_species b | 0.55 |
| CA | antibody_validation g, blinded_quantification p, statistical_test p | 0.50 |
| SB | cells_counted b, replicates p | 0.80 |

### Proximity labelling (BioID / TurboID / APEX), u = 0.60; BPD 0.55, CA 0.85, SB 0.80

- **Q1:** Relative MS enrichment (fold, FDR) over a control. It shows proximity within about 10 nm, not binding.
- **Q2:** No physical reference.
  - Typical cut-offs: 2 to 4 fold; FDR of 1 to 5 % in SAINT (Teo et al. 2014, J Proteomics 100:37).
  - Methods: Roux et al. 2012, J Cell Biol 196:801; Branon et al. 2018, Nat Biotechnol 36:880; Hung et al. 2016,
    Nat Protoc 11:456.
- **Q3:**
  - Benign: streptavidin capture and biotin dependence (intrinsic to the method). A reported fold or FDR implies
    that a control existed.
  - Real gap: an unrelated-bait or compartment control (it separates the bait's neighbourhood from the compartment);
    bait overexpression and mislocalisation; orthogonal validation for "binds".
- **Q4:** A compartment bystander is a false "binds".
- **Q5:** Far below KD.

| sheet criterion | members | u |
| --- | --- | --- |
| BC | ligase_only_control p, unlabeled_control b, unrelated_bait_control g | 0.60 |
| BR | expression_level g, localization p | 0.60 |
| BPD | proximity_observed b, enrichment_magnitude p, enrichment_significance p, orthogonal_validation g | 0.55 |
| CA | biotinylation_dependence b, streptavidin_capture b | 0.85 |
| SB | replicates p | 0.80 |

---

## 4. Notes for the owner's decision

- **Per type or per type and sheet criterion.**
  - The default column alone captures most of the effect.
  - The overrides matter most where one sheet criterion carries the meaning: BC for pulldown, Y2H, PLA, split
    reporter, CETSA, BRET and Trp; BR for SEC, AUC and DSF.
  - Either form needs only `experiment_type`, which `literature_page_update._weight_input` already passes in the
    working tree.
- **A finer option, not proposed now.** The converter could pass which members of a pooled sheet criterion were
  unknown, and the weight could use member-level b/g/p values. That would stop a benign unstated member, such as a
  Y2H reciprocal orientation, from pulling the whole BC to the assay's critical value.
- **Trp converter coupling (section 0, item 4).** If u becomes per type, the two Trp judges that use
  `WEIGHT_UNKNOWN` inside a degree should be decoupled, as SOP step 4 requires.
- **Mistakes and limits, stated plainly.**
  - The citations are from memory and not web-verified.
  - The P(adequate) values behind each u are expert judgment, not measured reporting rates.
  - Constants for seven converters were read from `HEAD`, because the working copies are mid-edit.
  - I briefly began reading `literature_resolution.py` and `literature_page_update.py` for an "apply" instruction
    that was then cancelled. No file other than this page was written or changed.
