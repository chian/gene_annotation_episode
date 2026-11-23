"""Endpoint_ms_quant criteria: the ONE place where the grader's criteria of a fixed-time enzyme reaction with mass-spectrometric product quantification are declared.

DRAFT of 2026-11-22 (owner to correct). This file is the single source for what the endpoint_ms_quant grader asks. The grader reports FACTS and
holds NO threshold that judges goodness: where a criterion needs a number to be compared with a limit (the control against the test, the read
amount against the calibration range, the calibration points, the read amount against the limit of quantification or detection, the
replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet';
the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_endpoint_ms_quant_converter.py. The logic that answers each
question is in literature_endpoint_ms_quant_grader.py (one short function per criterion, same order). The only constants here are unit
conversions (FIXED_BY_DEFINITION): a concentration unit into uM and a percent into a fraction; nothing else is compared.

How to read an entry in ENDPOINT_MS_QUANT_CRITERIA
--------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_ms_quant_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_ms_quant_criteria'
UM_PER_UNIT = {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}      # FIXED_BY_DEFINITION: a concentration unit in micromolar.
FRACTION_PER_UNIT = {'percent': 0.01, 'fraction': 1.0}      # FIXED_BY_DEFINITION: a percent is a hundredth.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_MS_QUANT_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the product that forms or appears without the enzyme (spontaneous chemistry, carry-over, a contaminant at the product\'s mass) measured and set aside, by a no-enzyme control, an inactive-enzyme control or a zero-time sample?',
        'reads': ('facts.no_enzyme_control_done', 'facts.inactive_enzyme_control_done', 'facts.zero_time_sample_done'),
        'rule': 'Any one of the three stated as done is enough. If none is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_reaction_control_stated', 'any of the three facts is yes'),
            ('conflicting', 'fact_answered_no', 'none is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'none is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'all three facts are not_applicable'),
        ),
    },
    {
        'id': 'signal_above_control',
        'question': 'How large is the product of the test against the product of the paper\'s own control: how much of the test signal is background?',
        'reads': ('quantities.conversion_fraction', 'quantities.control_conversion'),
        'rule': 'When the share converted and the share of the control are both given the grader records the control over the test (background_share, a number without unit: the share of the test signal that the control also shows) with their refs (background_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'background_share_recorded_for_the_sheet', 'both shares are given: the control over the test is recorded and the sheet judges it'),
            ('unknown', 'conversion_or_control_not_stated', 'the share converted or the share of the control is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the product shown to depend on the enzyme (more enzyme gives more product, an inactive mutant or an inhibitor gives none)?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'internal_standard',
        'question': 'Was an internal standard added to every sample, so that ion suppression and injection variation are corrected?',
        'reads': ('facts.internal_standard_used',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'matrix_matched_calibration',
        'question': 'Were the calibration standards made in the matrix of the reaction, so that the response of the standards is the response of the samples?',
        'reads': ('facts.matrix_matched_calibration',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'calibration_range',
        'question': 'Did the measured product amount lie inside the range of the calibration standards?',
        'reads': ('quantities.calibration_low', 'quantities.calibration_high', 'quantities.endpoint_amount', 'facts.amounts_within_calibration_range'),
        'rule': 'The fact stated as no fails (the paper itself says the amounts were extrapolated). Otherwise, when the lowest and highest standard and the product amount are all given as concentrations the grader records the amount over the lowest standard and over the highest standard (read_over_calibration_low, read_over_calibration_high) with their refs (range_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'calibration_range_recorded_for_the_sheet', 'the fact is not no, and the two standards and the amount are given as concentrations: the two ratios are recorded and the sheet judges them'),
            ('supported', 'facts_answered_yes', 'no numbers are recorded and the fact is yes'),
            ('unknown', 'fact_unknown', 'no numbers are recorded and the fact is not stated'),
            ('not_applicable', 'fact_not_applicable', 'no numbers are recorded and the fact is not_applicable'),
        ),
    },
    {
        'id': 'calibration_points',
        'question': 'How many concentration levels did the calibration curve have?',
        'reads': ('quantities.calibration_points',),
        'rule': 'When the number of levels is given the grader records it (calibration_points) with its ref (points_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'calibration_points_recorded_for_the_sheet', 'the number of levels is given: it is recorded and the sheet judges it'),
            ('unknown', 'calibration_points_not_stated', 'the number of levels is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'quantification_floor',
        'question': 'Was the measured product amount above the limit of quantification (or, when only that is stated, the limit of detection) of the method?',
        'reads': ('quantities.endpoint_amount', 'quantities.quantification_limit', 'quantities.detection_limit'),
        'rule': 'When the product amount is given as a concentration and a limit of quantification or of detection is given, the grader records the amount over each limit that is given (read_over_quantification_limit, read_over_detection_limit) with their refs (floor_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'quantification_floor_recorded_for_the_sheet', 'the amount and a limit are given: the ratios are recorded and the sheet judges them'),
            ('unknown', 'amount_or_limit_not_stated', 'the amount (as a concentration) or both limits are not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'product_identification',
        'question': 'Was the product identified by mass spectrometry and not inferred: against an authentic standard, by its fragmentation, or by its accurate mass?',
        'reads': ('facts.authentic_standard_used', 'facts.ms_ms_confirmation', 'facts.accurate_mass_match'),
        'rule': 'Any one of the three stated as yes is enough. If none is stated as yes and one is stated as no, it fails. Silence is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'product_identification_stated', 'any of the three facts is yes'),
            ('conflicting', 'fact_answered_no', 'none is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'none is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'all three facts are not_applicable'),
        ),
    },
    {
        'id': 'endpoint_time_stated',
        'question': 'Is the time at which the end point was read stated?',
        'reads': ('quantities.endpoint_time',),
        'rule': 'Stated is supported; not stated is unknown (an end point without its time is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'endpoint_time_stated', 'the time is given'),
            ('unknown', 'endpoint_time_not_stated', 'the time is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reaction_stopped',
        'question': 'Was the reaction stopped at the end point before the sample was analysed, so that the read time is the real end point and not the time the sample waited in the autosampler?',
        'reads': ('facts.reaction_stopped_before_analysis',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_time_across_arms',
        'question': 'Were the compared reactions (test and control, or the compared enzymes) stopped and read at the same time?',
        'reads': ('facts.same_time_for_compared_arms',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_substrate',
        'question': 'Is the amount of substrate the share converted is taken from stated, and was it measured rather than nominal?',
        'reads': ('facts.initial_substrate_determined', 'quantities.substrate_initial'),
        'rule': 'The fact stated as no fails (the paper itself says the denominator is nominal). The fact stated as yes is supported. Otherwise an initial substrate amount that is stated is supported. Silence is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('supported', 'facts_answered_yes', 'the fact is yes'),
            ('supported', 'substrate_initial_stated', 'the fact is not stated and the initial substrate is given'),
            ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable and no initial substrate is given'),
            ('unknown', 'substrate_initial_not_stated', 'the fact is not stated and no initial substrate is given'),
        ),
    },
    {
        'id': 'native_reaction',
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the conversion measured with the purified enzyme rather than a cell extract, lysate or whole cells?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated injections of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
