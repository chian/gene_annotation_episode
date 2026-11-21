# A105 grader criteria index (for expert review)

Written 2026-11-19. This page is an index, not the source. **The code is the single source**: each grader's
criteria, rules and threshold numbers are declared in one Python file per grader (listed below). This page only
points to those declarations and summarizes them in plain words. If this page and the code disagree, the code is
right and this page is stale. A test (`test_literature_criteria_declarations.py`) fails when a criterion id or a
constant value in the code is missing from the tables below, so the two cannot drift silently.

Folder for all files named here:
`gene_annotation_episode/episodic_workflow/episode_support/literature/grading/experimental_activity_evidence/`

Words used. A **criterion** is one question the grader asks of one experiment's record. Each answer is one of four
statuses: **supported** (the record shows the standard is met), **conflicting** (the record shows the standard is NOT
met), **unknown** (the record does not say; this is never counted as met and never as unmet), **not_applicable** (the
question does not apply to this record). A **threshold constant** is a named number a rule uses. **EXPERT_REVIEW**
marks a number that is a judgment an expert should confirm or change. **FIXED_BY_DEFINITION** marks a physical
constant or unit conversion that is not a judgment.

## SPR (surface plasmon resonance)

Declared in `literature_spr_criteria.py` (criteria in `SPR_CRITERIA`, numbers as named constants at the top).
Evaluated in `literature_spr_grader.py` (one short function per criterion). Mapped to the binding sheet in
`literature_spr_converter.py`.

| Criterion id | Question | Rule in words | Constants used |
| --- | --- | --- | --- |
| `reference_subtraction` | Was the signal corrected using a reference surface? | Reference surface or double referencing stated as done is enough; otherwise a stated "no" fails. | none |
| `concentration_series` | Did the concentrations bracket KD? | At least the minimum number of concentrations, lowest at most 0.2 x KD, highest at least 5 x KD. | `MIN_CONCENTRATIONS`, `LOW_FACTOR`, `HIGH_FACTOR` |
| `fit_model` | Is the fit model right and is there evidence the fit is good? | Model stated, residual evidence present; a 1:1 model for a multivalent analyte fails; chi-squared above the limit fraction of Rmax fails. | `CHI2_OVER_RMAX_MAX` |
| `rmax_consistency` | Is the maximum response what the immobilized amount and masses predict? | Observed / theoretical Rmax must be between the two limits. | `RMAX_RATIO_MIN`, `RMAX_RATIO_MAX` |
| `mass_transport` | Was mass-transport limitation checked and absent? | Checked-not-limited supported; checked-limited fails; not checked is unknown. | none |
| `baseline_regeneration` | Stable baseline and clean regeneration? | Both facts yes; any no fails; otherwise unknown if either unknown. | none |
| `replicates` | Enough independent replicates? | At least the minimum, on independent surfaces or chips; "not independent" or a count below the minimum fails. | `MIN_REPLICATES` |
| `immobilized_activity` | Was the immobilized partner shown active? | The one fact decides. | none |
| `kinetic_consistency` | Does KD equal koff / kon? | koff / kon (in nM) within the relative tolerance of the reported KD. | `KINETIC_TOLERANCE`, `NM_PER_M` |
| `steady_state_vs_kinetic` | Do steady-state and kinetic KD agree? | Within a fold factor; not applicable if only one estimate method was used. | `AGREEMENT_FACTOR` |

| Constant | Value | Judgment? | Why it exists |
| --- | --- | --- | --- |
| `MIN_CONCENTRATIONS` | 5 | EXPERT_REVIEW | Fewest analyte concentrations for a usable series. |
| `LOW_FACTOR` | 0.2 | EXPERT_REVIEW | Lowest concentration at most this multiple of KD. |
| `HIGH_FACTOR` | 5.0 | EXPERT_REVIEW | Highest concentration at least this multiple of KD. |
| `CHI2_OVER_RMAX_MAX` | 0.1 | EXPERT_REVIEW | Fit chi-squared above this fraction of Rmax marks a poor fit. |
| `RMAX_RATIO_MIN` | 0.3 | EXPERT_REVIEW | Observed / theoretical Rmax below this: inactive surface or wrong stoichiometry. |
| `RMAX_RATIO_MAX` | 1.2 | EXPERT_REVIEW | Observed / theoretical Rmax above this: non-specific binding or aggregation. |
| `MIN_REPLICATES` | 3 | EXPERT_REVIEW | Fewest independent replicates. |
| `KINETIC_TOLERANCE` | 0.2 | EXPERT_REVIEW | Allowed relative gap between KD and koff / kon. |
| `AGREEMENT_FACTOR` | 2.0 | EXPERT_REVIEW | Allowed fold gap between steady-state and kinetic KD. |
| `NM_PER_M` | 1000000000.0 | FIXED_BY_DEFINITION | Unit conversion, molar to nM. |

## ITC (isothermal titration calorimetry), draft

Declared in `literature_itc_criteria.py` (criteria in `ITC_CRITERIA`, numbers as named constants at the top).
Evaluated in `literature_itc_grader.py`. Record form in `forms/experimental_activity_evidence/literature_itc_record.py`
(one level up from the folder above). Mapped to the binding sheet in `literature_itc_converter.py`. The grader records
facts only; the converter judges them gradually (a degree in (0, 1] on `supported`), scaled only by numbers of the same
record, with no threshold constant (owner rule of 2026-11-21); nothing to compare against is unknown. The forms are
illustrative drafts for the owner and experts.

| Criterion id | Question | Rule in words | Constants used |
| --- | --- | --- | --- |
| `heat_of_dilution_control` | Was the heat of diluting the ligand into buffer measured and removed, and the baseline treated? | All three facts (control performed, control subtracted, baseline corrected) yes; any no fails; otherwise unknown if any unknown. | none |
| `concentration_accuracy_and_active_fraction` | Were concentrations determined and the active fraction considered, so n is near expected? | A fact "no" fails. Otherwise r = fitted n / expected n gives degree min(r, 1/r); a fact unknown is unknown. | none |
| `c_value_window` | Is the curve shape measurable (c = n x [cell] / KD)? | With N stated injections: degree (c / (c + 1)) x (N / (N + sqrt(c))), the saturation of the cell sites times the share of injections on the curved part; N not stated is unknown. | none |
| `fit_model_appropriate` | Is the model right for the sites, with residual evidence? | Model stated and residuals reported; a one-set-of-sites model for heterogeneous sites fails; that question unanswered is unknown. | none |
| `injections_sufficient` | Enough injections to define the isotherm? | N injections give degree N / (N + 1); no minimum. | none |
| `buffer_matching` | Same buffer in cell and syringe? | Dialysed together or matched by a stated procedure supported; stated not matched fails; not stated unknown. | none |
| `temperature_stated_and_controlled` | Is the temperature stated and controlled? | Temperature given and control stated yes; control "no" fails. No range is judged (nothing in the record to compare against). | `KELVIN_OFFSET` |
| `replicate_titrations_independent` | Enough independent replicate titrations? | "Not independent" fails; m titrations stated independent give degree m / (m + 1); independence unknown is unknown. | none |
| `stoichiometry_consistency` | Is the fitted n a freely fitted stoichiometry close to the stoichiometry the source expects? | A fixed n fails. A freely fitted n against the stated expected n e gives degree 1 / (1 + abs(n - e) / e); free fit unknown or no expected n is unknown. | none |
| `thermodynamic_consistency` | Does dG from KD match dH - T dS? | The gap g gives degree abs(dG_KD) / (abs(dG_KD) + g); if only the entropy is not given the check does not apply; KD, enthalpy or temperature missing is unknown. | `GAS_CONSTANT_J_PER_MOL_K`, `KCAL_TO_KJ`, `KELVIN_OFFSET`, `NM_PER_M`, `J_PER_KJ` |

| Constant | Value | Judgment? | Why it exists |
| --- | --- | --- | --- |
| `GAS_CONSTANT_J_PER_MOL_K` | 8.314462618 | FIXED_BY_DEFINITION | The gas constant R. |
| `KCAL_TO_KJ` | 4.184 | FIXED_BY_DEFINITION | Unit conversion. |
| `KELVIN_OFFSET` | 273.15 | FIXED_BY_DEFINITION | 0 C in kelvin. |
| `NM_PER_M` | 1000000000.0 | FIXED_BY_DEFINITION | Unit conversion, molar to nM. |
| `J_PER_KJ` | 1000.0 | FIXED_BY_DEFINITION | Unit conversion. |

## How an expert reviews or changes a criterion

1. Open the grader's criteria file (`literature_spr_criteria.py` or `literature_itc_criteria.py`). The criterion's
   entry says the question, what it reads, the rule in words, which constants it uses, and each status it can
   return with the reason code.
2. To change a number: edit the named constant in that same file (each is defined once, with a one-line reason).
   Keep the marker: EXPERT_REVIEW for a judgment. Then update the value in the table above (the declarations test
   fails until you do) and the explicit-number cases in the grader's test file
   (`tests/test_literature_spr_grader.py` or `tests/test_literature_itc_grader.py`), which state the hand-worked
   arithmetic next to each threshold.
3. To change a rule (not only a number): edit the criterion's `rule` and `returns` text in the criteria file and the
   matching short function in the grader file (`literature_spr_grader.py` or `literature_itc_grader.py`); the
   declarations test checks that every status and reason the grader returns is a declared case. A few reason codes
   spell a number in words (for example `fewer_than_five_concentrations`); rename those too if the number changes.
4. To change how a criterion feeds the binding sheet: edit `CRITERIA_MAP` in the converter
   (`literature_spr_converter.py` or `literature_itc_converter.py`) and its converter test.
5. Run the tests in `tests/` for that grader; the declarations test
   (`tests/test_literature_criteria_declarations.py`) confirms the declaration, grader and this index still agree.
