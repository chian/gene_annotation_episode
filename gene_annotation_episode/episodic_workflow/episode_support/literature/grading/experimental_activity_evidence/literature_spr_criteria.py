"""SPR criteria: the ONE place where the SPR grader's criteria and thresholds are declared.

This file is the single source for what the SPR grader asks. The grader
reports FACTS and holds NO threshold that judges goodness: where a criterion
needs a number to be compared with a limit (the concentration series against
the KD, the chi-squared over Rmax, the Rmax ratio, the replicate count, the
agreement of the KD with koff/kon, the agreement of the two KD estimates), the
grader records the number with its support refs and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_spr_converter.py. The logic that
answers each question is in literature_spr_grader.py (one short function per
criterion, same order). The only constant left here is a unit conversion
(FIXED_BY_DEFINITION).

How to read an entry in SPR_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_spr_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Threshold constants: the only one left is a unit conversion marked
FIXED_BY_DEFINITION, not a judgment. Every judgment value (EXPERT_REVIEW) is
in literature_spr_converter.py.
"""

VERSION = 'a105_spr_criteria_v1'

# ---- Constants -----------------------------------------------------------
NM_PER_M = 1e9  # FIXED_BY_DEFINITION: koff/kon is in molar; the sheet works in nM.

# ---- The criteria --------------------------------------------------------
SPR_CRITERIA = (
    {
        'id': 'reference_subtraction',
        'question': 'Was the signal corrected for bulk and non-specific binding using a reference surface?',
        'reads': ('facts.reference_surface', 'facts.double_referencing'),
        'rule': 'Reference-surface subtraction or double referencing stated as done is enough. If neither is stated as done and one is stated as not done, it fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'reference_subtraction_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Did the analyte concentrations bracket the KD well enough to define the binding curve?',
        'reads': ('quantities.kd', 'concentration_series'),
        'rule': 'When the KD and the series are both given, the grader records the number of concentrations (concentration_count), the lowest and the highest over the KD (concentration_low_over_kd, concentration_high_over_kd) and their refs (concentration_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'concentration_series_recorded_for_the_sheet', 'the KD and the series are given: the count and the two ratios are recorded and the sheet judges them'),
            ('unknown', 'kd_or_series_missing', 'KD or the series is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the fitting model appropriate for the analyte, and is there evidence the fit describes the data?',
        'reads': ('fit_model', 'facts.analyte_bivalent_or_oligomeric', 'facts.residuals_reported', 'quantities.chi_squared', 'quantities.rmax'),
        'rule': 'The model must be stated, with residual evidence (chi-squared with Rmax, or residuals reported). A 1:1 model for a bivalent or oligomeric analyte fails (a fact). When chi-squared and Rmax are both given, the grader records their quotient (chi2_over_rmax), the answer on bivalence (fit_bivalent_answer) and the refs (fit_refs) and leaves the judgement to the sheet.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated_with_residual_evidence', 'model stated, no chi-squared over Rmax, residuals reported, no shortfall'),
            ('conflicting', 'one_to_one_model_for_bivalent_or_oligomeric_analyte', 'model is 1:1_langmuir and the analyte is bivalent or oligomeric'),
            ('unknown', 'chi_squared_over_rmax_recorded_for_the_sheet', 'model stated, not the bivalent case, chi-squared and Rmax given: the quotient is recorded and the sheet judges it'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('unknown', 'no_residual_evidence', 'neither chi-squared with Rmax nor residuals reported'),
            ('unknown', 'bivalence_or_oligomer_state_unknown_for_one_to_one_model', '1:1 model and bivalence not answered no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'rmax_consistency',
        'question': 'Is the observed maximum response consistent with the amount of immobilized partner and the molecular masses?',
        'reads': ('quantities.rmax', 'quantities.immobilization_level', 'quantities.analyte_mass', 'quantities.ligand_mass', 'quantities.stoichiometry'),
        'rule': 'Theoretical Rmax = analyte mass / ligand mass x immobilization level x stoichiometry. The grader records the theoretical Rmax and the observed / theoretical ratio (rmax_theoretical, rmax_ratio) with their refs (rmax_refs) and leaves the judgement to the sheet.',
        'thresholds': (),
        'returns': (
            ('unknown', 'rmax_ratio_recorded_for_the_sheet', 'all five inputs are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'rmax_operand_missing', 'any of the five inputs is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'mass_transport',
        'question': 'Was mass-transport limitation checked and found absent?',
        'reads': ('facts.mass_transport',),
        'rule': 'Checked and not limited is supported; checked and limited fails. Not checked is unknown, because an unchecked experiment is not shown to be limited.',
        'thresholds': (),
        'returns': (
            ('supported', 'mass_transport_checked_not_limited', 'answer is checked_not_limited'),
            ('conflicting', 'mass_transport_checked_limited', 'answer is checked_limited'),
            ('unknown', 'mass_transport_not_checked', 'answer is not_checked'),
            ('unknown', 'mass_transport_unknown', 'answer is unknown'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'baseline_regeneration',
        'question': 'Was the baseline stable and the surface regenerated cleanly between cycles?',
        'reads': ('facts.baseline_drift', 'facts.regeneration'),
        'rule': 'Both facts must be yes. Any no fails; otherwise any unknown is unknown; both not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'both facts yes (or yes and not_applicable)'),
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'fact_unknown', 'no fact is no and one is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run on independent surfaces or chips?',
        'reads': ('quantities.replicate_count', 'facts.independent_surfaces'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Injections of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'immobilized_activity',
        'question': 'Was the immobilized partner shown to be active (functional) on the surface?',
        'reads': ('facts.immobilized_activity',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'kinetic_consistency',
        'question': 'Does the KD agree with the ratio of the off-rate to the on-rate?',
        'reads': ('quantities.kd', 'quantities.kon', 'quantities.koff'),
        'rule': 'KD from rates = koff / kon (in nM). The grader records it (kd_from_rates_nM) with the refs of the three quantities (kinetic_refs) and leaves the comparison with the reported KD to the sheet.',
        'thresholds': ('NM_PER_M',),
        'returns': (
            ('unknown', 'kd_from_rates_recorded_for_the_sheet', 'KD, kon and koff are given: the KD from the rates is recorded and the sheet judges it'),
            ('unknown', 'kd_kon_or_koff_missing', 'KD, kon or koff not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'steady_state_vs_kinetic',
        'question': 'Do the steady-state and the kinetic KD estimates agree?',
        'reads': ('quantities.kd_steady_state', 'quantities.kd', 'facts.single_estimate_method'),
        'rule': 'The grader records the fold gap between the two estimates (steady_kinetic_fold, at least 1) with the refs of the two (steady_kinetic_refs) and leaves the judgement to the sheet. If only one estimate method was used the question does not apply.',
        'thresholds': (),
        'returns': (
            ('unknown', 'estimate_fold_recorded_for_the_sheet', 'both estimates are given: the fold gap is recorded and the sheet judges it'),
            ('unknown', 'steady_state_or_kinetic_kd_missing', 'an estimate is missing and single_estimate_method is not yes'),
            ('not_applicable', 'single_estimate_method', 'an estimate is missing and single_estimate_method is yes'),
        ),
    },
)
