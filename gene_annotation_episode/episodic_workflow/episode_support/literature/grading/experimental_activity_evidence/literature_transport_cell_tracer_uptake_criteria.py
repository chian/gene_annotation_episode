"""Transport_cell_tracer_uptake criteria: the ONE place where the grader's criteria of a whole-cell tracer uptake (or efflux) experiment are declared.

This file is the single source for what the transport_cell_tracer_uptake grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the uptake interval, the substrate series against the Km, the replicate count),
the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its
EXPERT_REVIEW constants are on the sheet side, in literature_transport_cell_tracer_uptake_converter.py. The logic that answers each question is in
literature_transport_cell_tracer_uptake_grader.py (one short function per criterion, same order). There is no constant here: a concentration unit is
turned into nM by the reader's fixed scale table and a time into seconds by the fixed minute (both FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in TRANSPORT_CELL_TRACER_UPTAKE_CRITERIA
-------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_cell_tracer_uptake_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
No criterion rests on a plain choice field (spread_kind, rate_basis): a choice holds no span in the merged record.
"""

VERSION = 'a105_transport_cell_tracer_uptake_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

TRANSPORT_CELL_TRACER_UPTAKE_CRITERIA = (
    {
        'id': 'background_controls',
        'question': 'Was the uptake that does not belong to the protein (other transporters and metabolism of the host, label that sticks to the cells and the filter) measured and set aside, by control cells without the protein or by a zero-time or cold sample?',
        'reads': ('facts.empty_vector_control_done', 'facts.zero_time_control_done'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'background_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'expression_confirmed',
        'question': 'Was the production of the protein in the cells confirmed, so that the uptake can be tied to it?',
        'reads': ('facts.expression_confirmed',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'cell_integrity',
        'question': 'Were the viability or the membrane integrity of the cells checked, so that the label kept by the cells is inside intact cells?',
        'reads': ('facts.viability_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the linear part of the time course, over an interval short enough that the uptake has not bent towards a steady state?',
        'reads': ('quantities.time_window', 'facts.linear_interval_shown'),
        'rule': 'A linear-interval fact stated as no fails. The fact stated as yes is supported. Otherwise, when the length of the uptake interval is given, the grader records it (time_window_s, time_window_refs) and leaves the judgement to the sheet; with neither it is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-interval fact is no'),
            ('supported', 'linear_interval_stated', 'the linear-interval fact is yes'),
            ('unknown', 'time_window_recorded_for_the_sheet', 'the fact is not stated and the interval is given: it is recorded and the sheet judges it'),
            ('unknown', 'rate_regime_not_stated', 'the fact is not stated and no interval is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the substrate concentrations of the saturation series bracket the Km well enough to define it?',
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
        'id': 'competitor_control',
        'question': 'Was the uptake shown to be specific to the substrate, by a reduction with an excess of the unlabelled substrate or with a competitor?',
        'reads': ('facts.competitor_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'label_identity',
        'question': 'Was the label kept by the cells shown to be the unchanged substrate and not a metabolite of it?',
        'reads': ('facts.label_identity_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'energy_dependence',
        'question': 'Was the dependence of the uptake on its energy source or gradient tested (an uncoupler, an inhibitor, energy-depleted or cold cells), so that the driving force of the transport is shown?',
        'reads': ('facts.energy_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'specific_activity_stated',
        'question': 'Is the specific activity of the label stated, so that the counts can be turned into an amount?',
        'reads': ('quantities.specific_activity',),
        'rule': 'Stated is supported; not stated is unknown (an amount whose conversion constant is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'specific_activity_stated', 'the specific activity is given'),
            ('unknown', 'specific_activity_not_stated', 'the specific activity is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'native_substrate',
        'question': 'Is the labelled compound the natural substrate itself rather than an analogue or a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated filters of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
