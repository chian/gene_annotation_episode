"""Coupled_enzyme criteria: the ONE place where the grader's criteria of a continuous coupled-enzyme assay are declared.

This file is the single source for what the coupled_enzyme grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the share of the substrate consumed, the lag against the time the
rate was read, the coupling capacity over the measured rate, the substrate series against the Km, the highest absorbance, the replicate
count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_coupled_enzyme_converter.py. The logic that answers each
question is in literature_coupled_enzyme_grader.py (one short function per criterion, same order).

The only constants here are unit conversions, FIXED_BY_DEFINITION: UM_PER_MIN_PER_UNIT turns a rate of the record's vocabulary into uM/min
(1 U/mL is 1 umol/min/mL, which is 1000 uM/min; 1 mU/mL is 1 uM/min; 1 mM is 1000 uM; 1 nM is 0.001 uM) and SECONDS_PER_UNIT turns a time into
seconds.

How to read an entry in COUPLED_ENZYME_CRITERIA
-----------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupled_enzyme_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_coupled_enzyme_criteria_v1'

UM_PER_MIN_PER_UNIT = {'uM/min': 1.0, 'mM/min': 1000.0, 'nM/min': 0.001, 'U/mL': 1000.0, 'mU/mL': 1.0}   # FIXED_BY_DEFINITION: exact unit conversions to uM/min.
SECONDS_PER_UNIT = {'s': 1.0, 'min': 60.0}   # FIXED_BY_DEFINITION: a minute is 60 seconds.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

COUPLED_ENZYME_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the signal of the reporter without the primary enzyme (reporter background, spontaneous change, contaminating activity of the coupling enzymes) measured and set aside, by a no-primary-enzyme blank or an inactive-enzyme control?',
        'reads': ('facts.no_primary_enzyme_control', 'facts.inactive_enzyme_control'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_reaction_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'substrate_independent_signal',
        'question': 'Was the enzyme-dependent signal that does not need the primary substrate (reporter oxidase or reductase activity of the preparation, a substrate-independent turnover of the coupling system) measured with a no-substrate control?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the rate shown to be proportional to the amount of the primary enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product of the primary reaction identified by another measurement, not only through the coupling reaction?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'extinction_coefficient_stated',
        'question': 'Is the extinction coefficient of the reporter that turns the signal slope into a rate stated, with the wavelength it belongs to?',
        'reads': ('quantities.extinction_coefficient', 'quantities.wavelength'),
        'rule': 'Both stated is supported; either missing is unknown (a rate whose conversion constant is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'extinction_coefficient_and_wavelength_stated', 'both are given'),
            ('unknown', 'extinction_coefficient_or_wavelength_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reporter_stoichiometry',
        'question': 'Is it stated how many reporter molecules are consumed or formed per molecule of product, as used to turn the reporter slope into the primary rate?',
        'reads': ('facts.reporter_stoichiometry_stated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'absorbance_range',
        'question': 'Did the absorbance stay in the range where the detector is linear with the concentration?',
        'reads': ('quantities.absorbance_max',),
        'rule': 'When the highest absorbance is given the grader records it (absorbance_max) with its ref (absorbance_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'absorbance_recorded_for_the_sheet', 'the highest absorbance is given: it is recorded and the sheet judges it'),
            ('unknown', 'absorbance_not_stated', 'the highest absorbance is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the progress curve where little of the primary substrate has been consumed?',
        'reads': ('quantities.substrate_consumed_percent', 'facts.linear_progress_curve'),
        'rule': 'A linear-progress-curve fact stated as no fails. When the share of the substrate consumed is given the grader records it (consumed_percent, consumed_refs) and leaves the judgement to the sheet. Otherwise the linear-progress-curve fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-progress-curve fact is no'),
            ('unknown', 'consumed_recorded_for_the_sheet', 'the share consumed is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_progress_curve_stated', 'no share consumed is given and the fact is yes'),
            ('unknown', 'rate_regime_not_stated', 'no share consumed is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'lag_phase',
        'question': 'Was the rate read after the lag in which the coupling enzymes catch up with the primary reaction, so that the reporter slope is the primary rate?',
        'reads': ('quantities.lag_time', 'quantities.rate_start_time', 'facts.lag_phase_excluded'),
        'rule': 'A lag-phase-excluded fact stated as no fails. When both the lag and the time the rate was read from are given the grader records their ratio (lag_start_over_lag, the start time over the lag, both in seconds) with their refs (lag_refs) and leaves the judgement to the sheet. Otherwise the lag-phase-excluded fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the lag-phase-excluded fact is no'),
            ('unknown', 'lag_recorded_for_the_sheet', 'the lag and the start time are both given and the fact is not no: their ratio is recorded and the sheet judges it'),
            ('supported', 'lag_phase_excluded_stated', 'the lag and the start time are not both given and the fact is yes'),
            ('unknown', 'lag_not_stated', 'the lag and the start time are not both given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'coupling_capacity',
        'question': 'Is the activity of the coupling enzymes well above the rate they have to follow, so that the reporter slope is set by the primary enzyme and not by the coupling system?',
        'reads': ('quantities.coupling_excess', 'quantities.coupling_enzyme_activity', 'quantities.primary_rate'),
        'rule': 'When the paper states the excess of the coupling activity over the primary rate (coupling_excess) the grader records it; otherwise, when the coupling activity and the primary rate are both given, it records their ratio, both in uM/min (coupling_excess). The ref is coupling_refs. The judgement is left to the sheet. Otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'coupling_excess_recorded_for_the_sheet', 'the excess is stated, or the coupling activity and the primary rate are both given: the excess is recorded and the sheet judges it'),
            ('unknown', 'coupling_excess_or_activity_and_rate_missing', 'neither the excess nor both of the coupling activity and the primary rate are given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'coupling_system_check',
        'question': 'Was the coupling system checked to respond at once and fully to the product of the primary reaction (product added, or more coupling enzyme added without a change)?',
        'reads': ('facts.coupling_system_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'coupling_enzymes_unaffected',
        'question': 'Were the coupling enzymes shown not to be affected by what was added or changed in the experiment (effector, inhibitor, partner, test compound, buffer)?',
        'reads': ('facts.coupling_enzymes_unaffected',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
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
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated reads of one reaction mixture are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the activity measured with the purified primary enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
