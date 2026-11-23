"""ITC criteria: the ONE place where the ITC grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the ITC
grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (n over
the expected n, the c value, the injection count, the temperature, the replicate
count, the fitted n, the gap of the two free energies), the grader records the
number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on
the sheet side, in literature_itc_converter.py. The logic that answers each
question is in literature_itc_grader.py (one short function per criterion, same
order). The only constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in ITC_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_itc_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Constants: each is defined once, below. FIXED_BY_DEFINITION marks a physical
constant or unit conversion, not a judgment. Every judgment value
(EXPERT_REVIEW) is in literature_itc_converter.py.

Terms. KD: dissociation constant. n: the fitted stoichiometry (ligand per
partner). c value: c = n x [cell concentration] / KD, the dimensionless number
that says whether the titration curve has a measurable shape. dG: Gibbs
free energy; dH enthalpy; dS entropy; dG = dH - T x dS.
"""

VERSION = 'a105_itc_criteria'

# ---- Constants -----------------------------------------------------------
GAS_CONSTANT_J_PER_MOL_K = 8.314462618  # FIXED_BY_DEFINITION: R, used in dG = R T ln(KD / 1 M).
KCAL_TO_KJ = 4.184  # FIXED_BY_DEFINITION: unit conversion.
KELVIN_OFFSET = 273.15  # FIXED_BY_DEFINITION: 0 C in kelvin.
NM_PER_M = 1e9  # FIXED_BY_DEFINITION: unit conversion, KD is kept in nM and used in molar for dG.
J_PER_KJ = 1000.0  # FIXED_BY_DEFINITION: unit conversion.

# ---- The criteria --------------------------------------------------------
ITC_CRITERIA = (
    {
        'id': 'heat_of_dilution_control',
        'question': 'Was the heat of diluting the ligand into buffer measured and removed, and the baseline treated?',
        'reads': ('facts.dilution_control_performed', 'facts.dilution_control_subtracted', 'facts.baseline_corrected'),
        'rule': 'All three facts must be yes. Any no fails; otherwise any unknown is unknown; all not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'all three facts yes (or yes and not_applicable)'),
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'fact_unknown', 'no fact is no and one is unknown'),
            ('not_applicable', 'fact_not_applicable', 'all facts are not_applicable'),
        ),
    },
    {
        'id': 'concentration_accuracy_and_active_fraction',
        'question': 'Were the concentrations determined and the active fraction considered, so that n is near the expected stoichiometry?',
        'reads': ('quantities.stoichiometry', 'quantities.expected_stoichiometry', 'facts.concentrations_determined', 'facts.active_fraction_determined'),
        'rule': 'Both facts (concentrations determined, active fraction determined) must be yes; a fact answered no fails. When n and the expected n are both given and no fact is no, the grader records the ratio fitted n / expected n (n_over_expected), its refs (n_over_expected_refs) and whether a fact is unknown (concentration_facts_unknown) and leaves the judgement of the ratio to the sheet.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'n_over_expected_recorded_for_the_sheet', 'no fact is no and n and the expected n are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'n_or_expected_stoichiometry_missing', 'no fact is no and n or expected n not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'c_value_window',
        'question': 'Is the c value in the window where the curve has a measurable shape, so KD is well determined?',
        'reads': ('quantities.stoichiometry', 'quantities.cell_concentration', 'quantities.kd', 'quantities.final_molar_ratio'),
        'rule': 'c = n x [cell] / KD. The grader records it (c_value) with the refs of the three quantities (c_value_refs) and leaves the judgement of the window to the sheet. When the final ligand : partner molar ratio r is also stated it records the final total ligand over KD, r x c / n (final_ligand_over_kd, with final_ratio_refs): how far the titration went past KD, which decides whether a low-c titration still reached its plateau.',
        'thresholds': (),
        'returns': (
            ('unknown', 'c_value_recorded_for_the_sheet', 'n, cell concentration and KD are given: c is recorded and the sheet judges it'),
            ('unknown', 'n_cell_concentration_or_kd_missing', 'n, cell concentration or KD not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'fit_model_appropriate',
        'question': 'Is the fitting model appropriate for the binding sites, and is there residual evidence that the fit describes the data?',
        'reads': ('fit_model', 'facts.binding_sites_heterogeneous', 'facts.residuals_reported'),
        'rule': 'The model must be stated and residuals reported. A one-set-of-sites model when the sites are stated to be heterogeneous or interacting fails; a one-set-of-sites model with that question unanswered is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated_with_residual_evidence', 'model stated, residuals reported, no shortfall'),
            ('conflicting', 'one_set_model_for_heterogeneous_sites', 'model is one_set_of_sites and sites are heterogeneous'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('unknown', 'no_residual_evidence', 'residuals not reported'),
            ('unknown', 'site_heterogeneity_unknown_for_one_set_model', 'one_set_of_sites and heterogeneity not answered no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'injections_sufficient',
        'question': 'Were there enough injections to define the binding isotherm?',
        'reads': ('quantities.injection_count', 'titration_mode'),
        'rule': 'The grader records the titration mode (titration_mode). When the mode is stated as single_injection or continuous the injection count does not describe how well the curve is sampled: the grader records the mode with its refs (injection_refs) and leaves the judgement to the sheet. Otherwise it records the stated injection count (injection_count) with its refs (injection_refs) and leaves the judgement to the sheet.',
        'thresholds': (),
        'returns': (
            ('unknown', 'titration_mode_recorded_for_the_sheet', 'the mode is single_injection or continuous: it is recorded and the sheet judges it'),
            ('unknown', 'injection_count_recorded_for_the_sheet', 'a count is stated and the mode is not single_injection or continuous: it is recorded and the sheet judges it'),
            ('unknown', 'injection_count_missing', 'count not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'buffer_matching',
        'question': 'Were the cell and syringe solutions in the same buffer, so mixing heats do not mimic binding?',
        'reads': ('facts.buffer_matching',),
        'rule': 'Dialysed together, or matched by a stated procedure, is supported. Stated as not matched fails. Not stated is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'buffers_matched', 'answer is dialysed_together or matched_by_stated_procedure'),
            ('conflicting', 'buffers_not_matched', 'answer is not_matched'),
            ('unknown', 'buffer_matching_unknown', 'answer is unknown'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'temperature_stated_and_controlled',
        'question': 'Is the temperature stated, plausible, and controlled?',
        'reads': ('quantities.temperature', 'facts.temperature_controlled'),
        'rule': 'Control stated as no fails (a fact). The temperature must be given; the grader records it in kelvin (temperature_K) with its refs and the answer on control (temperature_refs, temperature_control) and leaves the judgement of the range and of the control answer to the sheet.',
        'thresholds': ('KELVIN_OFFSET',),
        'returns': (
            ('conflicting', 'fact_answered_no', 'control stated as no'),
            ('unknown', 'temperature_not_stated', 'temperature not given and control not no'),
            ('unknown', 'temperature_recorded_for_the_sheet', 'temperature given and control not no: they are recorded and the sheet judges them'),
        ),
    },
    {
        'id': 'replicate_titrations_independent',
        'question': 'Were there enough replicate titrations, and were they independent (separate preparations or days)?',
        'reads': ('quantities.replicate_count', 'facts.independent_titrations'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'stoichiometry_consistency',
        'question': 'Is the fitted n a freely fitted, meaningful, simple-ratio stoichiometry?',
        'reads': ('quantities.stoichiometry', 'facts.n_fitted_freely'),
        'rule': 'n must be given and fitted freely (not fixed by the analyst); a fixed n fails (a fact). The grader records the stated n (stoichiometry_n), the answer on the free fit (stoichiometry_free) and the refs (stoichiometry_refs) and leaves the judgement of its size and of its distance from a simple ratio to the sheet.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'stoichiometry_was_fixed', 'n is given and n_fitted_freely is no'),
            ('unknown', 'stoichiometry_recorded_for_the_sheet', 'n is given and was not fixed: it is recorded and the sheet judges it'),
            ('unknown', 'stoichiometry_not_given', 'n not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'thermodynamic_consistency',
        'question': 'Do the free energy from KD and the free energy from enthalpy minus temperature times entropy agree?',
        'reads': ('quantities.kd', 'quantities.enthalpy', 'quantities.entropy', 'quantities.temperature', 'facts.enthalpy_buffer_ionization_corrected'),
        'rule': 'dG from KD = R T ln(KD in molar). dG from parts = dH - T dS. The grader records both and their absolute gap (dg_from_kd_kJ_per_mol, dg_from_parts_kJ_per_mol, dg_gap_kJ_per_mol) with the refs (dg_refs) and the answer on whether the reported dH was corrected for buffer ionization (enthalpy_ionization_corrected) and leaves the judgement of the gap, and of whether the identity applies to a corrected dH, to the sheet. If only the entropy is not given the check cannot be made and does not apply.',
        'thresholds': ('GAS_CONSTANT_J_PER_MOL_K', 'KCAL_TO_KJ', 'KELVIN_OFFSET', 'NM_PER_M', 'J_PER_KJ'),
        'returns': (
            ('unknown', 'free_energy_gap_recorded_for_the_sheet', 'KD, enthalpy, entropy and temperature are given: the gap is recorded and the sheet judges it'),
            ('unknown', 'kd_enthalpy_or_temperature_missing', 'KD, enthalpy or temperature not given'),
            ('not_applicable', 'entropy_not_given_check_not_possible', 'KD, enthalpy and temperature given, entropy not given'),
        ),
    },
)
