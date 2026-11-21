"""BLI criteria: the ONE place where the BLI grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the BLI
grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the
loading and the response, the concentration series against the KD, the fit
R-squared, the decay in the dissociation window, the replicate count, the
agreement of the KD with koff/kon, the agreement of the two KD estimates), the
grader records the number with its support refs and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_bli_converter.py. The logic that
answers each question is in literature_bli_grader.py (one short function per
criterion, same order). The only constants left here are unit conversions
(FIXED_BY_DEFINITION).

How to read an entry in BLI_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_bli_record.py)
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
(EXPERT_REVIEW) is in literature_bli_converter.py.

Terms. KD: dissociation constant. Response: the wavelength shift of the
sensor in nanometres (nm), the BLI counterpart of SPR's resonance units.
Loading: the amount of the partner immobilized on the sensor, also in nm.
Dissociation window: the length of the step in which the analyte is
removed and the signal decays. Avidity: a bivalent or oligomeric analyte, or
a crowded sensor, re-binds before leaving and the apparent koff is too slow.

What BLI does not ask (SPR items left out because BLI has no such thing): the
Rmax-from-molecular-masses consistency (a BLI response in nm has no mass
calibration that is reported), the chi-squared over Rmax rule (BLI software
reports R-squared), and a flow-cell mass-transport test (BLI has no flow;
mass transport and rebinding are asked as one 'considered' question).
"""

VERSION = 'a105_bli_criteria_v1'

# ---- Constants -----------------------------------------------------------
NM_PER_M = 1e9  # FIXED_BY_DEFINITION: koff/kon is in molar; the sheet works in nM.
SECONDS_PER_MINUTE = 60.0  # FIXED_BY_DEFINITION: unit conversion of the dissociation time.

# ---- The criteria --------------------------------------------------------
BLI_CRITERIA = (
    {
        'id': 'reference_subtraction',
        'question': 'Was the signal corrected for drift and background using a reference sensor or a buffer reference?',
        'reads': ('facts.reference_sensor_subtracted', 'facts.buffer_reference_subtracted'),
        'rule': 'Reference-sensor subtraction or buffer-reference subtraction stated as done is enough. If neither is stated as done and one is stated as not done, it fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'reference_subtraction_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'nonspecific_binding_control',
        'question': 'Was non-specific binding of the analyte to a blank sensor checked?',
        'reads': ('facts.nonspecific_binding_checked',),
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
        'id': 'baseline_and_regeneration',
        'question': 'Was the baseline stable and the sensor regenerated cleanly where it was reused?',
        'reads': ('facts.baseline_stable', 'facts.regeneration'),
        'rule': 'Both facts must be yes. Any no fails; otherwise any unknown is unknown; both not_applicable is not applicable (single-use sensors need no regeneration).',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'both facts yes (or yes and not_applicable)'),
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'fact_unknown', 'no fact is no and one is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'loading_and_response',
        'question': 'Was the loading step documented, with a loading level that is not crowded and a response well above the noise?',
        'reads': ('facts.loading_step_documented', 'quantities.loading_level', 'quantities.response_max'),
        'rule': 'The loading step must be documented (yes); not documented (no) fails (a fact). When the loading level or the maximum response is given, the grader records them (loading_level_nm, response_max_nm; None when not given), the answer on the documentation (loading_documented) and the refs (loading_refs) and leaves the judgement of the loading and of the response to the sheet; neither given is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'loading_step_not_documented', 'the fact is no'),
            ('unknown', 'loading_and_response_recorded_for_the_sheet', 'the fact is not no and the loading level or the response is given: they are recorded and the sheet judges them'),
            ('unknown', 'loading_or_response_missing', 'the fact is not no and neither the loading level nor the response is given'),
            ('not_applicable', 'never', 'never returned'),
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
        'question': 'Is the fitting model appropriate for the analyte, and does the fit describe the data?',
        'reads': ('fit_model', 'facts.analyte_bivalent_or_oligomeric', 'quantities.fit_r_squared'),
        'rule': 'The model must be stated and the fit R-squared given. A 1:1 model for a bivalent or oligomeric analyte fails (a fact). The grader records the R-squared (fit_r_squared), the answer on bivalence (fit_bivalent_answer) and the refs (fit_refs) and leaves the judgement of the R-squared, and of a 1:1 model whose bivalence is not answered no, to the sheet.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'one_to_one_model_for_bivalent_or_oligomeric_analyte', 'model is 1:1 and the analyte is bivalent or oligomeric'),
            ('unknown', 'r_squared_recorded_for_the_sheet', 'model stated, not the bivalent case, R-squared given: it is recorded and the sheet judges it'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('unknown', 'no_fit_quality_evidence', 'R-squared not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'avidity_and_mass_transport',
        'question': 'Were avidity or rebinding, or mass-transport limitation, considered?',
        'reads': ('facts.avidity_rebinding_considered', 'facts.mass_transport_considered'),
        'rule': 'Either consideration stated as done is enough. If neither is stated as done and one is stated as not done, it fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'avidity_or_transport_considered', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'dissociation_window',
        'question': 'Was the dissociation step long enough for the signal to decay so that koff is measured?',
        'reads': ('quantities.koff', 'quantities.dissociation_time'),
        'rule': 'The fraction decayed in the window is 1 - exp(-koff x time). The grader records it (dissociation_decay) with the refs of koff and the time (dissociation_refs) and leaves the judgement to the sheet.',
        'thresholds': ('SECONDS_PER_MINUTE',),
        'returns': (
            ('unknown', 'dissociation_decay_recorded_for_the_sheet', 'koff and the dissociation time are given: the decayed fraction is recorded and the sheet judges it'),
            ('unknown', 'koff_or_dissociation_time_missing', 'koff or the dissociation time is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run on independent sensors?',
        'reads': ('quantities.replicate_count', 'facts.independent_sensors'),
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
        'id': 'immobilized_activity',
        'question': 'Was the partner loaded on the sensor shown to be active (functional)?',
        'reads': ('facts.immobilized_partner_active',),
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
