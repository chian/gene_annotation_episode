"""Itc_kinetics criteria: the ONE place where the grader's criteria of an isothermal titration calorimetry enzyme-kinetics experiment are declared.

This file is the single source for what the itc_kinetics grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the control heat over the reaction heat, the baseline noise over the
reaction heat, the share of the substrate consumed, the enzyme over the substrate plus Km, the substrate series against the Km, the replicate
count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_itc_kinetics_converter.py. The logic that answers each question is
in literature_itc_kinetics_grader.py (one short function per criterion, same order). The only constant here is a unit conversion marked
FIXED_BY_DEFINITION; a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in ITC_KINETICS_CRITERIA
---------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_itc_kinetics_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_itc_kinetics_criteria_v1'
# FIXED_BY_DEFINITION: the thermal powers of the record in microwatts (1 nW is 0.001 uW; 1 ucal/s is 4.184 uW, the thermochemical calorie being exactly 4.184 J).
POWER_UW_PER_UNIT = {'nW': 0.001, 'uW': 1.0, 'ucal/s': 4.184}

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ITC_KINETICS_CRITERIA = (
    {
        'id': 'substrate_dilution_control',
        'question': 'Was the heat of diluting and mixing the substrate (a substrate injection into buffer without the enzyme) measured and set aside?',
        'reads': ('facts.substrate_into_buffer_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dilution_control',
        'question': 'Was the heat of diluting the enzyme (an enzyme injection into buffer without the substrate) measured and set aside?',
        'reads': ('facts.enzyme_into_buffer_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'signal_over_blank',
        'question': 'Is the control heat (the dilution heat) small beside the heat of the enzyme reaction?',
        'reads': ('quantities.thermal_power', 'quantities.dilution_power'),
        'rule': 'When the reaction power and the control power are both given the grader records the control power over the reaction power (dilution_over_signal, dimensionless) with their refs (blank_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'blank_share_recorded_for_the_sheet', 'both powers are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'power_or_blank_missing', 'either power is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'signal_over_noise',
        'question': 'Is the baseline noise of the calorimeter small beside the heat of the enzyme reaction?',
        'reads': ('quantities.thermal_power', 'quantities.baseline_noise'),
        'rule': 'When the reaction power and the baseline noise are both given the grader records the noise over the reaction power (noise_over_signal, dimensionless) with their refs (noise_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'noise_share_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'power_or_noise_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'enthalpy_stated',
        'question': 'Is the reaction enthalpy that turns the thermal power into a rate stated?',
        'reads': ('quantities.reaction_enthalpy',),
        'rule': 'Stated is supported; missing is unknown (a rate whose conversion constant is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'reaction_enthalpy_stated', 'the enthalpy is given'),
            ('unknown', 'reaction_enthalpy_missing', 'the enthalpy is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'enthalpy_determined',
        'question': 'Was the reaction enthalpy measured on its own, by complete conversion of a known amount of substrate in the buffer, pH and temperature of the rate measurement?',
        'reads': ('facts.enthalpy_determined_in_assay_buffer',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the heat rate shown to be proportional to the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the heat shown to be the claimed reaction (the product identified by another measurement)?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Was the rate read at a point where little substrate had been consumed, from a steady level of the power?',
        'reads': ('quantities.substrate_consumed_percent', 'facts.steady_power_plateau'),
        'rule': 'A steady-power fact stated as no fails. When the share of the substrate consumed is given the grader records it (consumed_percent, consumed_refs) and leaves the judgement to the sheet. Otherwise the steady-power fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the steady-power fact is no'),
            ('unknown', 'consumed_recorded_for_the_sheet', 'the share consumed is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'steady_power_plateau_stated', 'no share consumed is given and the fact is yes'),
            ('unknown', 'rate_regime_not_stated', 'no share consumed is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'response_time_accounted',
        'question': 'Was the response time of the calorimeter (the lag of the measured power behind the reaction heat) taken into account?',
        'reads': ('facts.response_time_accounted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_substrate_ratio',
        'question': 'Is the enzyme concentration small against the substrate concentration plus the Km, so that the steady-state rate law applies?',
        'reads': ('quantities.enzyme_concentration', 'quantities.substrate_concentration', 'quantities.km'),
        'rule': 'When the three are given the grader records the enzyme over the substrate plus the Km (enzyme_over_substrate_plus_km, dimensionless) with their refs (enzyme_ratio_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'enzyme_ratio_recorded_for_the_sheet', 'the three are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'enzyme_substrate_or_km_missing', 'any of the three is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the substrate concentrations of the saturation curve bracket the Km well enough to define it?',
        'reads': ('quantities.km', 'concentration_series'),
        'rule': 'When the Km and the series are both given the grader records the number of concentrations (concentration_count), the lowest and the highest over the Km (concentration_low_over_km, concentration_high_over_km) and their refs (concentration_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'substrate_series_recorded_for_the_sheet', 'the Km and the series are given: the count and the two ratios are recorded and the sheet judges them'),
            ('unknown', 'km_or_series_missing', 'the Km or the series is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'active_enzyme_amount',
        'question': 'Was the amount of active enzyme determined (an active-site titration or an equivalent), so that a rate per enzyme is not a rate per total protein?',
        'reads': ('facts.active_site_concentration_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated injections of one reaction mixture are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate (an analogue)?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the activity measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
