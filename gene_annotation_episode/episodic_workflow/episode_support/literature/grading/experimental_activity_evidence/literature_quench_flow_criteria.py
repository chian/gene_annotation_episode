"""Quench_flow criteria: the ONE place where the grader's criteria of a rapid chemical quench-flow enzyme experiment are declared.

This file is the single source for what the quench_flow grader asks. The grader reports FACTS and holds NO threshold that judges goodness:
where a criterion needs a number to be compared with a limit (the substrate over the enzyme, the earliest and latest time against the rate
constant, the number of time points, the burst amplitude per enzyme, the replicate count), the grader records the number with its support
refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the
sheet side, in literature_quench_flow_converter.py. The logic that answers each question is in literature_quench_flow_grader.py (one short
function per criterion, same order).

The only constants here are exact unit conversions (FIXED_BY_DEFINITION): a concentration unit is turned into nM by the reader's fixed scale
table, a time into seconds and a rate constant into s^-1 by the two tables below. Nothing else is compared.

How to read an entry in QUENCH_FLOW_CRITERIA
--------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_quench_flow_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_quench_flow_criteria_v1'

SECONDS_PER_TIME_UNIT = {'ms': 1.0e-3, 's': 1.0}                  # FIXED_BY_DEFINITION: one millisecond is a thousandth of a second.
PER_SECOND_PER_RATE_UNIT = {'s^-1': 1.0, 'min^-1': 1.0 / 60.0}    # FIXED_BY_DEFINITION: one per minute is a sixtieth of one per second.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

QUENCH_FLOW_CRITERIA = (
    {
        'id': 'zero_time_control',
        'question': 'Was a zero-time control measured: the enzyme mixed with the quench before the substrate, to give the product present at time zero?',
        'reads': ('facts.zero_time_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'no_enzyme_control',
        'question': 'Was the spontaneous (non-enzymatic) formation of product measured and set aside, by a control without the enzyme taken through the same mixing, quench and analysis?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'quench_efficiency',
        'question': 'Was the quench shown to stop the reaction at once and completely, so that the product counted is the product of the stated time?',
        'reads': ('facts.quench_stops_reaction',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the product made, or the burst amplitude, shown to increase in proportion to the enzyme concentration?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product separated from the substrate and identified as the claimed product (by a standard or by its mass)?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_calibration',
        'question': 'Was the amount of product calculated against a standard (a calibration curve, a known specific radioactivity or a known recovery)?',
        'reads': ('facts.product_quantified_against_standard',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_substrate_ratio',
        'question': 'Does the substrate over the enzyme fit the design the passage states: the enzyme in excess for a single turnover, the substrate in excess for a burst with steady-state turnover?',
        'reads': ('facts.single_turnover_conditions', 'facts.multiple_turnover_conditions', 'quantities.enzyme_concentration', 'quantities.substrate_concentration'),
        'rule': 'When exactly one of the two design facts is yes and both concentrations are given, the grader records the design (turnover_design) and the substrate over the enzyme (substrate_over_enzyme, dimensionless) with their refs (ratio_refs) and leaves the judgement to the sheet. Both designs stated yes, neither stated, or a concentration missing is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'enzyme_ratio_recorded_for_the_sheet', 'one design is stated and both concentrations are given: the design and the ratio are recorded and the sheet judges them'),
            ('unknown', 'both_designs_stated', 'both design facts are yes'),
            ('unknown', 'turnover_design_not_stated', 'neither design fact is yes'),
            ('unknown', 'enzyme_or_substrate_concentration_missing', 'a design is stated and either concentration is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'time_range',
        'question': 'Did the time points of the course reach from early enough to late enough, against the rate constant, to define the phase?',
        'reads': ('quantities.chemical_rate_constant', 'quantities.shortest_time', 'quantities.longest_time'),
        'rule': 'When the rate constant and at least one of the two times are given the grader records the rate constant times the shortest time (first_point_times_rate) and times the longest time (last_point_times_rate), dimensionless, with their refs (time_range_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'time_range_recorded_for_the_sheet', 'the rate constant and a time are given: the products are recorded and the sheet judges them'),
            ('unknown', 'rate_constant_or_time_range_missing', 'the rate constant or both times are not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'time_course_fit',
        'question': 'Was the time course fitted to an equation by regression?',
        'reads': ('facts.time_course_fitted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'time_points',
        'question': 'Were there enough time points to define the parameters of the fitted equation?',
        'reads': ('quantities.time_point_count',),
        'rule': 'When the number of time points is given the grader records it (time_point_count, time_point_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'time_point_count_recorded_for_the_sheet', 'the number of time points is given: it is recorded and the sheet judges it'),
            ('unknown', 'time_point_count_not_stated', 'the number of time points is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'active_enzyme_amount',
        'question': 'Was the amount of active enzyme determined (an active-site titration or the burst itself), so that a rate per enzyme is not a rate per total protein?',
        'reads': ('facts.active_site_concentration_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'burst_stoichiometry',
        'question': 'How much product does the burst make per enzyme (per active site)?',
        'reads': ('quantities.burst_amplitude_per_enzyme', 'quantities.burst_amplitude', 'quantities.enzyme_concentration', 'facts.single_turnover_conditions', 'facts.multiple_turnover_conditions'),
        'rule': 'A single-turnover design (single turnover yes, multiple turnover not yes) has no burst: not applicable. Otherwise, when the passage gives the amplitude per enzyme the grader records it (burst_per_enzyme, burst_refs); else, when multiple turnover is yes and the amplitude and the enzyme concentration are given, it records their ratio; the judgement is left to the sheet. Otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'burst_amplitude_recorded_for_the_sheet', 'the amplitude per enzyme is given or can be formed: it is recorded and the sheet judges it'),
            ('unknown', 'burst_amplitude_not_stated', 'no amplitude per enzyme is given and none can be formed'),
            ('not_applicable', 'single_turnover_has_no_burst', 'the design is a single turnover'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated analyses of one reaction series are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than an analogue or a surrogate?',
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
