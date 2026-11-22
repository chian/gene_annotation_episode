"""Separation_band criteria: the ONE place where the grader's criteria of a gel or thin-layer separation assay of an enzyme reaction are declared.

DRAFT (2026-11-22). This file is the single source for what the separation_band grader asks. The grader reports FACTS and holds NO threshold that
judges goodness: where a criterion needs a number to be compared with a limit (the share of the substrate converted, the number of time points, the enzyme
over the substrate, the substrate series against the Km, the replicate count), the grader records the number with its support refs and returns 'unknown'
with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_separation_band_converter.py. The logic that answers each question is in literature_separation_band_grader.py (one short function per
criterion, same order). There is no constant here: a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION),
and nothing else is compared.

How to read an entry in SEPARATION_BAND_CRITERIA
------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_separation_band_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_separation_band_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

SEPARATION_BAND_CRITERIA = (
    {
        'id': 'no_enzyme_lane',
        'question': 'Was the spontaneous (non-enzymatic) change of the substrate during the incubation (hydrolysis, breakage, drift of the band) measured and set aside by a lane or reaction without the enzyme?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'catalytic_mutant_lane',
        'question': 'Was a contaminating activity of the preparation (a copurified nuclease, protease or phosphatase) set aside by a lane with an inactive enzyme, a catalytic mutant made and purified in the same way or a heat-denatured enzyme?',
        'reads': ('facts.inactive_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the amount of product shown to rise with the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product band or spot identified as the claimed product by a size marker, a ladder or an authentic standard run on the same gel or plate?',
        'reads': ('facts.product_marker_run',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'signal_linearity',
        'question': 'Were the band or spot intensities measured in the linear range of the detector, so that an intensity ratio is a ratio of amounts?',
        'reads': ('facts.densitometry_in_linear_range',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'lane_total_denominator',
        'question': 'Was the fraction converted taken as the product over the total (substrate plus product) of the same lane, so that loading and recovery differences between lanes cancel?',
        'reads': ('facts.conversion_over_lane_total',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the time course where little substrate has been converted?',
        'reads': ('quantities.substrate_converted_percent', 'facts.linear_time_course'),
        'rule': 'A linear-time-course fact stated as no fails. When the share of the substrate converted is given the grader records it (consumed_percent, consumed_refs) and leaves the judgement to the sheet. Otherwise the linear-time-course fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-time-course fact is no'),
            ('unknown', 'consumed_recorded_for_the_sheet', 'the share converted is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_time_course_stated', 'no share converted is given and the fact is yes'),
            ('unknown', 'rate_regime_not_stated', 'no share converted is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'time_course_points',
        'question': 'Did the time course have enough stopped time points to show a rate?',
        'reads': ('quantities.time_point_count',),
        'rule': 'When the number of time points is given the grader records it (time_point_count, time_point_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'time_points_recorded_for_the_sheet', 'the number of time points is given: it is recorded and the sheet judges it'),
            ('unknown', 'time_points_not_stated', 'the number of time points is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reaction_stopped',
        'question': 'Was the reaction stopped at each time point, so that the time of each lane is the time the reaction ran?',
        'reads': ('facts.reaction_stopped_at_time_points',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_substrate_ratio',
        'question': 'Is the enzyme concentration small against the substrate concentration, so that the enzyme turned over many times (a catalyst) rather than once (a single-turnover reaction)?',
        'reads': ('quantities.enzyme_concentration', 'quantities.substrate_concentration'),
        'rule': 'When both are given the grader records the enzyme over the substrate (enzyme_over_substrate, dimensionless) with their refs (enzyme_ratio_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'enzyme_ratio_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'enzyme_or_substrate_missing', 'either is not given'),
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
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated loadings of one reaction are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a model or artificial substrate?',
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
