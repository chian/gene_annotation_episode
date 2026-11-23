"""Stopped_colorimetric criteria: the ONE place where the grader's criteria of a stopped colorimetric enzyme assay are declared.

This file is the single source for what the stopped_colorimetric grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the share of the substrate consumed, the enzyme over the
substrate plus Km, the substrate series against the Km, the highest product over the top of the standard curve, the number of standards, the
number of time points, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_stopped_colorimetric_converter.py.
The logic that answers each question is in literature_stopped_colorimetric_grader.py (one short function per criterion, same order). There is
no constant here: a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in STOPPED_COLORIMETRIC_CRITERIA
-----------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_stopped_colorimetric_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
No criterion reads a plain choice (spread_kind, reagent_class): a choice carries no span after the leaf records are merged.
"""

VERSION = 'a105_stopped_colorimetric_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

STOPPED_COLORIMETRIC_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the change that happens without the enzyme (the substrate breaking down or reacting with the colour reagent during the incubation) measured and set aside, by a no-enzyme control or an inactive-enzyme control?',
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
        'id': 'reagent_background_blank',
        'question': 'Was the colour the reagent gives at time zero (with the substrate, the buffer and the enzyme preparation present) measured with a zero-time blank and subtracted?',
        'reads': ('facts.zero_time_blank',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_borne_signal',
        'question': 'Was the colour that comes from the enzyme preparation and its buffer (free phosphate, reducing sugar, thiol or ammonia carried with the enzyme) measured with an enzyme-without-substrate control?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the rate (or the product formed) shown to be proportional to the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the colour shown to be the claimed product (identified by another measurement) rather than inferred from the colour reagent, which reacts with a whole class of compounds?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_curve_matrix',
        'question': 'Was the product standard curve made in the reaction buffer (or the buffer shown not to interfere with the colour reagent), so that the colour of a standard and of a sample mean the same amount?',
        'reads': ('facts.standard_curve_in_reaction_buffer',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_curve_range',
        'question': 'Did the product amounts measured stay within the range of the standard curve?',
        'reads': ('quantities.product_concentration_max', 'quantities.standard_curve_high'),
        'rule': 'When the highest product concentration and the top of the standard curve are both given the grader records the first over the second (product_over_standard_high, dimensionless) with their refs (standard_range_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'standard_range_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'product_or_standard_range_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'standard_curve_points',
        'question': 'How many standards define the product standard curve?',
        'reads': ('quantities.standard_curve_points',),
        'rule': 'When the number of standards is given the grader records it (standard_points, standard_points_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'standard_points_recorded_for_the_sheet', 'the number of standards is given: it is recorded and the sheet judges it'),
            ('unknown', 'standard_points_not_stated', 'the number of standards is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the time course where little substrate has been consumed and the product still grows in a straight line?',
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
        'id': 'time_course_points',
        'question': 'At how many time points was the product measured, so that a straight line (and its bending) can be seen, rather than one end-point read as a rate?',
        'reads': ('quantities.time_points_count',),
        'rule': 'When the number of time points is given the grader records it (time_points, time_points_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'time_points_recorded_for_the_sheet', 'the number of time points is given: it is recorded and the sheet judges it'),
            ('unknown', 'time_points_not_stated', 'the number of time points is not given'),
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate?',
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
