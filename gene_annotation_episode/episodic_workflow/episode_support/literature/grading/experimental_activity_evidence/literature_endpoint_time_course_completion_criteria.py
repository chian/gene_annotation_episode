"""Endpoint_time_course_completion criteria: the ONE place where the grader's criteria of a sampled reaction followed to a stated completion or equilibrium are declared.

This file is the single source for what the endpoint_time_course_completion grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a
criterion needs a number to be compared with a limit (the sampling interval against the completion time, the enzyme loading of the two arms, the replicate count), the
grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on
the sheet side, in literature_endpoint_time_course_completion_converter.py. The logic that answers each question is in literature_endpoint_time_course_completion_grader.py (one
short function per criterion, same order). The only constants here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in ENDPOINT_TIME_COURSE_COMPLETION_CRITERIA
----------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_time_course_completion_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.

Fields the grader keeps without a criterion of their own (native only, read by the converter): the three exactness facts (completion_time_is_exact, reference_time_is_exact,
completion_time_ratio_is_exact: whether each stated time or ratio is a value or only a bound), the fact conversion_detected_above_control (the qualitative statement), the
spread and its kind, the two choices completion_criterion and detection_method.
"""

VERSION = 'a105_endpoint_time_course_completion_criteria_v1'
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.
LOADING_SCALE = {'nM': ('molar', 1.0), 'uM': ('molar', 1000.0), 'mg/mL': ('mass', 1.0)}  # FIXED_BY_DEFINITION: (kind, factor to nM or to mg/mL); two loadings are compared only within one kind.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_TIME_COURSE_COMPLETION_CRITERIA = (
    {
        'id': 'completion_criterion',
        'question': 'Does the passage say what state counted as complete or as equilibrium, so that the time identifies a defined end point?',
        'reads': ('facts.completion_criterion_stated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'matched_endpoint',
        'question': 'Was the same completion or equilibrium state used to read the time of the test arm and of the reference arm?',
        'reads': ('facts.same_completion_criterion_in_arms',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable. Times read against different end points are not comparable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'samples_stopped',
        'question': 'Was each sample stopped (quenched, inactivated or the enzyme removed) before it was analysed, so that it shows the time it was taken?',
        'reads': ('facts.samples_stopped_before_analysis',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'sampling_resolution',
        'question': 'Was the sampling fine enough for the completion time to be known: a completion is only known to the gap between two samples?',
        'reads': ('quantities.completion_time', 'quantities.sampling_interval'),
        'rule': 'When the completion time and the sampling interval are both given the grader records the interval over the time (sampling_interval_over_time, dimensionless) with their refs (sampling_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('unknown', 'sampling_recorded_for_the_sheet', 'both are given: the interval over the time is recorded and the sheet judges it'),
            ('unknown', 'sampling_interval_or_time_missing', 'the completion time or the sampling interval is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'spontaneous_course_control',
        'question': 'Was the spontaneous (non-enzymatic) course of the substrate measured and set aside, by a time course without the enzyme or with an inactive enzyme?',
        'reads': ('facts.no_enzyme_course_done', 'facts.inactive_enzyme_course_done'),
        'rule': 'Either course stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_course_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the time to completion shown to depend on the enzyme (shorter with more enzyme, not completing with the inactive enzyme or an inhibitor)?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'contaminating_activity',
        'question': 'Was it examined whether the activity belongs to the enzyme and not to a contaminating enzyme of the preparation?',
        'reads': ('facts.contaminating_activity_examined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product identified by an authentic standard or an independent identification?',
        'reads': ('facts.product_identified_by_standard',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'mass_balance',
        'question': 'Does the loss of the substrate match the gain of the product?',
        'reads': ('facts.substrate_loss_matches_product_gain',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_substrate',
        'question': 'Was the starting amount of the substrate measured, so that the state called complete refers to a known amount?',
        'reads': ('facts.initial_substrate_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'matched_loading',
        'question': 'Did the test arm and the reference arm have the same amount of enzyme, so that a ratio of times is a difference of the enzyme and not of its loading?',
        'reads': ('facts.same_loading_in_arms', 'quantities.enzyme_loading_test', 'quantities.enzyme_loading_reference'),
        'rule': 'A fact stated as no fails. When both loadings are given in the same kind of unit (both molar or both mass) the grader records the fold difference of the two loadings (loading_fold, never below 1) with their refs (loading_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': ('LOADING_SCALE',),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'loading_recorded_for_the_sheet', 'both loadings are given in one kind of unit and the fact is not no: the fold difference is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'no comparable loadings are given and the fact is yes'),
            ('unknown', 'fact_unknown', 'no comparable loadings are given and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no comparable loadings are given and the fact is not_applicable'),
        ),
    },
    {
        'id': 'matched_temperature',
        'question': 'Were the test arm and the reference arm run at the same temperature?',
        'reads': ('facts.same_temperature_in_arms',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the time course run with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
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
        'id': 'replicates',
        'question': 'Were there enough replicate time courses, run as independent experiments?',
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
)
