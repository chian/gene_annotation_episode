"""GCI criteria: the ONE place where the GCI grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the GCI
grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the
surface level and the response, the concentration series against the KD, the
replicate count, the agreement of the KD with koff/kon, the agreement of the two
KD estimates), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and
its EXPERT_REVIEW constants are on the sheet side, in literature_gci_converter.py.
The logic that answers each question is in literature_gci_grader.py (one short
function per criterion, same order). The constants left here are unit
conversions (FIXED_BY_DEFINITION; PG_MM2_PER_RU is the one approximate reading
of a unit and stays marked EXPERT_REVIEW).

How to read an entry in GCI_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_gci_record.py)
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
constant or unit conversion, not a judgment. Every goodness threshold
(EXPERT_REVIEW) is in literature_gci_converter.py.

Terms. KD: dissociation constant. Response and immobilization level: the
surface mass signal of the chip in pg/mm2 (ng/mm2 or RU are converted). The
reference channel: a chip channel without the immobilized partner (or with an
unrelated one) whose signal is subtracted. Double referencing: the reference
channel AND blank (buffer) injections are subtracted. Bulk and solvent
correction: the refractive-index jump of the sample (for example from DMSO) is
corrected with solvent-correction injections. waveRAPID: kinetics from repeated
short pulses of ONE analyte concentration of increasing length; it replaces a
titration series.

What GCI does not ask (items of the other binding experiments left out because
GCI has no such thing or does not report it): a fit chi-squared or R-squared (the
Creoptix software does not report one in the text of a paper; judged not worth
collecting, see the converter's range review) and the avidity-rebinding
question (a bivalent or oligomeric analyte is asked as a fact of the fit-model
criterion).
"""

VERSION = 'a105_gci_criteria'

# ---- Constants -----------------------------------------------------------
PG_MM2_PER_RU = 1.0  # EXPERT_REVIEW: the usual approximation that one response unit is about 1 pg/mm2 of protein; a source reporting RU is read through it (a unit reading, not a goodness threshold).
NM_PER_M = 1e9  # FIXED_BY_DEFINITION: koff/kon is in molar; the sheet works in nM.
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
PG_MM2_PER_UNIT = {'pg/mm2': 1.0, 'ng/mm2': 1000.0}  # FIXED_BY_DEFINITION: pg/mm2 per surface mass unit (RU is read through PG_MM2_PER_RU).
S_PER_UNIT = {'s': 1.0, 'min': 60.0}  # FIXED_BY_DEFINITION: seconds per dissociation time unit.

# ---- The criteria --------------------------------------------------------
GCI_CRITERIA = (
    {
        'id': 'reference_subtraction',
        'question': 'Was the signal corrected for drift and background using a reference channel or double referencing?',
        'reads': ('facts.reference_channel_subtracted', 'facts.double_referenced'),
        'rule': 'Reference-channel subtraction or double referencing stated as done is enough. If neither is stated as done and one is stated as not done, it fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'reference_subtraction_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'bulk_solvent_correction',
        'question': 'Was the bulk refractive-index and solvent (for example DMSO) effect corrected?',
        'reads': ('facts.bulk_solvent_corrected',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable (an analyte in plain running buffer needs no solvent correction).',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'nonspecific_binding_control',
        'question': 'Was non-specific binding of the analyte to the chip surface checked?',
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
        'question': 'Was the baseline stable and the surface regenerated cleanly where it was reused?',
        'reads': ('facts.baseline_stable', 'facts.regeneration'),
        'rule': 'Both facts must be yes. Any no fails; otherwise any unknown is unknown; both not_applicable is not applicable (a surface used once needs no regeneration).',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'both facts yes (or yes and not_applicable)'),
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'fact_unknown', 'no fact is no and one is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'surface_level_and_response',
        'question': 'Was the immobilized amount low enough to avoid crowding, and the maximum response well above the noise?',
        'reads': ('quantities.immobilization_level', 'quantities.response_max'),
        'rule': 'When the immobilization level or the maximum response is given, the grader records them in pg/mm2 (immobilization_level_pg_mm2, response_max_pg_mm2; None when not given; RU is read through PG_MM2_PER_RU) with their refs (surface_refs) and leaves the judgement of the level and of the response to the sheet; neither given is unknown.',
        'thresholds': ('PG_MM2_PER_RU', 'PG_MM2_PER_UNIT'),
        'returns': (
            ('unknown', 'surface_level_and_response_recorded_for_the_sheet', 'the level or the response is given: they are recorded and the sheet judges them'),
            ('unknown', 'level_or_response_missing', 'neither the level nor the response is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'rmax_consistency',
        'question': 'Is the observed maximum response consistent with the amount of immobilized partner and the molecular masses?',
        'reads': ('quantities.response_max', 'quantities.immobilization_level', 'quantities.analyte_mass', 'quantities.ligand_mass', 'quantities.stoichiometry'),
        'rule': 'Theoretical maximum response = analyte mass / ligand mass x immobilization level x stoichiometry (all in pg/mm2; RU is read through PG_MM2_PER_RU). The grader records the theoretical value and the observed / theoretical ratio (rmax_theoretical_pg_mm2, rmax_ratio) with their refs (rmax_refs) and leaves the judgement to the sheet.',
        'thresholds': ('PG_MM2_PER_RU', 'PG_MM2_PER_UNIT'),
        'returns': (
            ('unknown', 'rmax_ratio_recorded_for_the_sheet', 'all five inputs are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'rmax_operand_missing', 'any of the five inputs is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Did the analyte concentrations bracket the KD well enough to define the binding curve (or, for waveRAPID, was the pulsed concentration high enough)?',
        'reads': ('quantities.kd', 'concentration_series', 'facts.repeated_pulse_kinetics_used'),
        'rule': 'When the KD and the series are both given, the grader records the number of concentrations (concentration_count), the lowest and the highest over the KD (concentration_low_over_kd, concentration_high_over_kd), whether repeated-pulse (waveRAPID) kinetics is stated as used (pulse_kinetics) and the refs (concentration_refs) and leaves the judgement to the sheet; otherwise unknown. With waveRAPID one concentration is the design, so the sheet asks for the highest concentration only and not for the count.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_series_recorded_for_the_sheet', 'the KD and the series are given: the count, the two ratios and the waveRAPID statement are recorded and the sheet judges them'),
            ('unknown', 'kd_or_series_missing', 'KD or the series is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'dissociation_window',
        'question': 'Was the dissociation phase long enough for the signal to decay, so that koff is measured and not extrapolated?',
        'reads': ('quantities.koff', 'quantities.dissociation_time', 'quantities.response_max'),
        'rule': 'The fraction decayed in the window is 1 - exp(-koff x time). The grader records it (dissociation_decay) and the maximum response in pg/mm2 when given (dissociation_response_pg_mm2, else None) with the refs of the quantities used (dissociation_refs) and leaves the judgement to the sheet.',
        'thresholds': ('S_PER_UNIT', 'PG_MM2_PER_RU', 'PG_MM2_PER_UNIT'),
        'returns': (
            ('unknown', 'dissociation_decay_recorded_for_the_sheet', 'koff and the dissociation time are given: the decayed fraction is recorded and the sheet judges it'),
            ('unknown', 'koff_or_dissociation_time_missing', 'koff or the dissociation time is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the fitting model stated and appropriate for the analyte?',
        'reads': ('fit_model', 'facts.analyte_bivalent_or_oligomeric'),
        'rule': 'The model must be stated. A 1:1 model for a bivalent or oligomeric analyte fails; a 1:1 model with that question unanswered is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a model other than 1:1 stated, or 1:1 with the analyte stated not bivalent or oligomeric'),
            ('conflicting', 'one_to_one_model_for_bivalent_or_oligomeric_analyte', 'model is 1:1 and the analyte is bivalent or oligomeric'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('unknown', 'bivalence_or_oligomer_state_unknown_for_one_to_one_model', '1:1 model and bivalence not answered no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'mass_transport',
        'question': 'Was mass-transport limitation of the flow-based measurement checked?',
        'reads': ('facts.mass_transport_checked',),
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
        'id': 'replicates',
        'question': 'Were there enough replicates, run on independent channels or chips?',
        'reads': ('quantities.replicate_count', 'facts.independent_channels_or_chips'),
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
        'question': 'Was the partner immobilized on the chip shown to be active (functional)?',
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
