"""Endpoint_gel_band criteria: the ONE place where the grader's criteria of a gel or TLC end-point conversion experiment are declared (DRAFT 2026-11-22, owner to correct).

This file is the single source for what the endpoint_gel_band grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the control lane against the test lane, the replicate count), the grader
records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_endpoint_gel_band_converter.py. The logic that answers each question is in
literature_endpoint_gel_band_grader.py (one short function per criterion, same order). The only constant here is a unit conversion, a percent into a
fraction (FIXED_BY_DEFINITION); nothing else is compared.

How to read an entry in ENDPOINT_GEL_BAND_CRITERIA
--------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_gel_band_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_gel_band_criteria_v1'
PERCENT_PER_FRACTION = 100.0   # FIXED_BY_DEFINITION: a percent is a hundredth; a stated share in percent is turned into a fraction by it.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_GEL_BAND_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) change of the substrate measured and set aside, by a lane without the enzyme or with an inactive enzyme?',
        'reads': ('facts.no_enzyme_lane_done', 'facts.inactive_enzyme_lane_done'),
        'rule': 'Either lane stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A lane stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_reaction_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'substrate_purity_control',
        'question': 'Was the substrate shown not to hold the product already (a zero-time or untreated substrate lane)?',
        'reads': ('facts.zero_time_lane_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'control_lane_background',
        'question': 'Is the share converted in the control lane small against the share converted in the test lane?',
        'reads': ('quantities.conversion_percent', 'quantities.control_conversion'),
        'rule': 'When the test share (above 0) and the control share are both given the grader records them as fractions (test_fraction, control_fraction) with their refs (control_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'control_background_recorded_for_the_sheet', 'the test share and the control share are given: they are recorded and the sheet judges them'),
            ('unknown', 'control_or_test_conversion_missing', 'either share is not given'),
            ('unknown', 'test_conversion_is_zero', 'the test share is stated as 0, so there is nothing to compare the control with'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the product band shown to depend on the active enzyme (lost with an inactive enzyme, EDTA, an inhibitor or without a required cofactor)?',
        'reads': ('facts.product_depends_on_active_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product band identified (a size marker, an authentic standard or another method) rather than inferred from the shrinking substrate band?',
        'reads': ('facts.band_identified_by_marker',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'densitometry_linear_range',
        'question': 'Were the band signals measured inside the linear range of the detection (not saturated, with a standard curve or dilution series)?',
        'reads': ('facts.signal_within_linear_range',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_lane_fraction',
        'question': 'Is the converted share calculated from the bands of one lane, so that differences in loading cancel?',
        'reads': ('facts.fraction_from_same_lane_bands',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'endpoint_time_defined',
        'question': 'Is the time of the end point stated and was the reaction stopped before the gel or plate was loaded, so that the time is the time of the stop?',
        'reads': ('quantities.endpoint_time', 'facts.reaction_stopped_before_loading'),
        'rule': 'The stop fact stated as no fails. The stop fact yes with the time stated is supported. Anything else (the time or the stop not stated) is unknown. No limit on the time is applied.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the stop fact is no'),
            ('supported', 'time_and_stop_stated', 'the time is stated and the stop fact is yes'),
            ('unknown', 'time_or_stop_not_stated', 'the time is not stated or the stop fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'the stop fact is not_applicable'),
        ),
    },
    {
        'id': 'lanes_same_time',
        'question': 'Were the lanes that are compared incubated for the same time under the same conditions?',
        'reads': ('facts.same_time_for_compared_lanes',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'native_reaction',
        'question': 'Is the substrate the enzyme\'s native substrate rather than a model substrate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the conversion measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments (separate gels)?',
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
)
