"""Endpoint_gas_evolution criteria: the ONE place where the grader's criteria of a gas-evolution end-point enzyme experiment are declared. DRAFT of 2026-11-22, owner to correct.

This file is the single source for what the endpoint_gas_evolution grader asks. The method: an enzyme reaction in a closed vessel, a gas product (H2, CO2, CH4,
N2O, O2) that collects in the headspace, read by gas chromatography or by manometry at a stated time and reported as an amount of the gas or as a percent of the
theoretical yield. The grader reports FACTS and holds NO threshold that judges goodness: where a criterion needs a number to be compared with a limit (the control
over the test, the read amount against the calibration range, the read amount against the detection limit, the amount against the theoretical yield, the replicate
count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its
EXPERT_REVIEW constants are on the sheet side, in literature_endpoint_gas_evolution_converter.py. The logic that answers each question is in
literature_endpoint_gas_evolution_grader.py (one short function per criterion, same order). The only constants here are unit conversions, FIXED_BY_DEFINITION.

How to read an entry in ENDPOINT_GAS_EVOLUTION_CRITERIA
-------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_gas_evolution_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (only unit conversions: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_gas_evolution_criteria_v1'
NMOL_PER_UNIT = {'nmol': 1.0, 'umol': 1.0e3, 'mmol': 1.0e6}   # FIXED_BY_DEFINITION: the gas amounts are turned into nmol before they are compared with each other.
PERCENT_PER_FRACTION = 100.0   # FIXED_BY_DEFINITION: a percent is a hundredth.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_GAS_EVOLUTION_CRITERIA = (
    {
        'id': 'spontaneous_gas_control',
        'question': 'Was the gas that forms without the enzyme (non-enzymatic breakdown of the substrate, a reductant or a metal that gives the gas by itself, a gas leaking out of the stopper) measured and set aside by a no-enzyme vessel or an inactive-enzyme vessel?',
        'reads': ('facts.no_enzyme_control_done', 'facts.inactive_enzyme_control_done'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_gas_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'zero_time_gas',
        'question': 'Was the gas of the vessel read at the start of the reaction, so that gas that was there before the reaction (trace H2 in an anaerobic chamber, CO2 from the buffer, air) is not counted as formed?',
        'reads': ('facts.zero_time_sample_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'leak_control',
        'question': 'Was the tightness of the closed vessel checked (a sealed blank or a known amount of the gas held for the same time without change)?',
        'reads': ('facts.leak_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'signal_over_control',
        'question': 'How large is the gas of the control vessel next to the gas of the test vessel?',
        'reads': ('quantities.gas_amount', 'quantities.control_gas_amount', 'quantities.conversion_percent', 'quantities.control_conversion_percent'),
        'rule': 'When the gas amount of the test and of the control are both stated the grader records the control over the test (control_over_test, dimensionless) with their refs (control_refs) and leaves the judgement to the sheet. Otherwise, when the percent of the theoretical yield of the test and of the control are both stated, it records their ratio in the same way. Otherwise unknown. The amounts are compared first because a percent hides the amount it is taken from.',
        'thresholds': ('NMOL_PER_UNIT',),
        'returns': (
            ('unknown', 'control_recorded_for_the_sheet', 'a test and a control value of the same kind are stated: their ratio is recorded and the sheet judges it'),
            ('unknown', 'control_or_test_not_stated', 'no pair of a test and a control value of the same kind is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the gas shown to depend on the enzyme (it rises with the enzyme amount, or it is lost with an inactive enzyme, a mutant or an inhibitor)?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'gas_identity',
        'question': 'Was the gas identified by the detector (the retention time of a gas standard, a mass spectrum or a gas-specific detector) and not only seen as a rise in pressure?',
        'reads': ('facts.gas_identified_by_detector',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'calibration_gas',
        'question': 'Was the gas reading calibrated with known amounts of the gas in the same kind of vessel (the same vial, volume and stopper), read the same way?',
        'reads': ('facts.calibration_gas_in_same_vessel',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'calibration_range',
        'question': 'Does the gas amount that was read lie inside the range of the known amounts of the calibration?',
        'reads': ('quantities.gas_amount', 'quantities.calibration_low', 'quantities.calibration_high'),
        'rule': 'When the gas amount and both ends of the calibration are stated the grader records the amount over the highest standard (amount_over_calibration_high) and over the lowest standard (amount_over_calibration_low), both dimensionless, with their refs (calibration_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('NMOL_PER_UNIT',),
        'returns': (
            ('unknown', 'calibration_range_recorded_for_the_sheet', 'the amount and both ends are stated: the two ratios are recorded and the sheet judges them'),
            ('unknown', 'calibration_range_or_amount_missing', 'the amount or either end of the calibration is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'detection_margin',
        'question': 'Is the gas amount that was read clearly above the detection limit of the gas reading?',
        'reads': ('quantities.gas_amount', 'quantities.detection_limit'),
        'rule': 'When the gas amount and the detection limit are both stated the grader records the amount over the limit (amount_over_detection_limit, dimensionless) with their refs (detection_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('NMOL_PER_UNIT',),
        'returns': (
            ('unknown', 'detection_margin_recorded_for_the_sheet', 'the amount and the limit are stated: their ratio is recorded and the sheet judges it'),
            ('unknown', 'amount_or_detection_limit_missing', 'the amount or the limit is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'dissolved_gas',
        'question': 'Was the part of the gas that stays dissolved in the liquid (for carbon dioxide also as bicarbonate) counted, so that the headspace alone is not taken for the total?',
        'reads': ('facts.dissolved_gas_accounted_for',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'vessel_volumes',
        'question': 'Are the gas volume and the liquid volume of the closed vessel stated, so that a reader can tell what the amount of gas refers to?',
        'reads': ('quantities.headspace_volume', 'quantities.liquid_volume'),
        'rule': 'Both stated is supported; either missing is unknown (a reading whose vessel is not described is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'headspace_and_liquid_volume_stated', 'both are given'),
            ('unknown', 'headspace_or_liquid_volume_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'time_point_stated',
        'question': 'Is the time of the reaction at which the headspace gas was read stated?',
        'reads': ('quantities.endpoint_time',),
        'rule': 'The time stated is supported; not stated is unknown (a gas amount whose time is unstated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'endpoint_time_stated', 'the time is given'),
            ('unknown', 'endpoint_time_not_stated', 'the time is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'same_time_for_compared_arms',
        'question': 'Were the compared vessels (test and control, or the compared enzymes) read at the same time?',
        'reads': ('facts.same_time_for_compared_arms',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'yield_denominator',
        'question': 'Was the substrate amount that the theoretical yield is taken from measured, and not only taken from the recipe?',
        'reads': ('facts.initial_substrate_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'yield_not_above_theoretical',
        'question': 'Is the gas that was found no more than the substrate can give (the amount over the theoretical yield, or the stated percent of it)?',
        'reads': ('quantities.gas_amount', 'quantities.theoretical_yield', 'quantities.conversion_percent'),
        'rule': 'The grader records the largest of the stated ratios (yield_over_theoretical, dimensionless): the gas amount over the theoretical yield when both are stated, and the stated percent of the theoretical yield over one hundred when it is stated, with their refs (yield_refs), and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('NMOL_PER_UNIT', 'PERCENT_PER_FRACTION'),
        'returns': (
            ('unknown', 'yield_recorded_for_the_sheet', 'a ratio to the theoretical yield can be read: it is recorded and the sheet judges it'),
            ('unknown', 'yield_or_theoretical_not_stated', 'neither the amount with the theoretical yield nor the percent is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent vessels or experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated injections from one vessel are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'native_reaction',
        'question': 'Is the substrate the enzyme\'s native substrate rather than an artificial one?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the gas formed with the purified enzyme rather than a cell extract, lysate or whole cells?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
