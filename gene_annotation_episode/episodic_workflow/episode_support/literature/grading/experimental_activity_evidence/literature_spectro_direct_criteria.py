"""Spectro_direct criteria: the ONE place where the grader's criteria of a continuous direct spectrophotometric enzyme assay are declared.

This file is the single source for what the spectro_direct grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the share of the substrate consumed, the enzyme over the
substrate plus Km, the substrate series against the Km, the highest absorbance, the replicate count), the grader records the number
with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_spectro_direct_converter.py. The logic that answers each question is in
literature_spectro_direct_grader.py (one short function per criterion, same order). There is no constant here: a concentration unit is
turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in SPECTRO_DIRECT_CRITERIA
-----------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_spectro_direct_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_spectro_direct_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

SPECTRO_DIRECT_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) change of the substrate or cofactor measured and set aside, by a no-enzyme blank or an inactive-enzyme control?',
        'reads': ('facts.no_enzyme_control', 'facts.inactive_enzyme_control'),
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
        'question': 'Was the enzyme-dependent signal that does not need the substrate (cofactor oxidase or reductase activity, an enzyme-borne chromophore) measured with a no-substrate control?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the rate shown to be proportional to the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the absorbance change shown to be the claimed reaction (the product or the substrate loss identified by another measurement)?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'extinction_coefficient_stated',
        'question': 'Is the extinction coefficient that turns the absorbance slope into a rate stated, with the wavelength it belongs to?',
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
        'question': 'Is the rate an initial rate: taken from the part of the progress curve where little substrate has been consumed?',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate (a chromogenic analogue)?',
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
