"""Endpoint_enzymatic_assay criteria: the ONE place where the grader's criteria of an end-point determination with a second enzyme are declared.
DRAFT (2026-11-22), owner to correct.

This file is the single source for what the endpoint_enzymatic_assay grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (R squared of the standard curve, the number of standards, the read amount against
the ends of the standard series, the incubation with the second enzyme, the detection limit against the initial substrate, the replicate count), the grader
records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_endpoint_enzymatic_assay_converter.py. The logic that answers each question is in
literature_endpoint_enzymatic_assay_grader.py (one short function per criterion, same order). The only constants here are unit conversions
(FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes.

How to read an entry in ENDPOINT_ENZYMATIC_ASSAY_CRITERIA
---------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_enzymatic_assay_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_enzymatic_assay_criteria'

UM_PER_UNIT = {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}      # FIXED_BY_DEFINITION: a concentration unit in micromolar.
NMOL_PER_UNIT = {'pmol': 1.0e-3, 'nmol': 1.0, 'umol': 1.0e3}      # FIXED_BY_DEFINITION: an amount unit in nanomoles.
MIN_PER_UNIT = {'s': 1.0 / 60.0, 'min': 1.0, 'h': 60.0}      # FIXED_BY_DEFINITION: a time unit in minutes.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)


def _any_yes_returns(supported_reason):
    return (
        ('supported', supported_reason, 'either fact is yes'),
        ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
        ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
        ('not_applicable', 'fact_not_applicable', 'every fact is not_applicable'),
    )


ENDPOINT_ENZYMATIC_ASSAY_CRITERIA = (
    {
        'id': 'estimate_identity',
        'question': 'Is the reported end-point quantity (a share converted, a control-corrected share or a product amount) stated together with the time of the end point?',
        'reads': ('quantities.net_conversion_percent', 'quantities.conversion_percent', 'quantities.product_amount', 'quantities.endpoint_time'),
        'rule': 'At least one of the three effect quantities stated together with the end-point time is supported. An effect with no time, or no effect at all, is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'effect_and_endpoint_time_stated', 'an effect quantity and the end-point time are both given'),
            ('unknown', 'endpoint_time_not_stated', 'an effect quantity is given and the end-point time is not'),
            ('unknown', 'no_effect_quantity_stated', 'none of the three effect quantities is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'standard_series_through_second_enzyme',
        'question': 'Was a standard series of the analyte run through the same second-enzyme assay as the samples?',
        'reads': ('facts.standard_series_through_second_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_curve_fit',
        'question': 'How well does the standard curve fit its standards (R squared)?',
        'reads': ('quantities.standard_curve_r_squared',),
        'rule': 'When R squared is given the grader records it (r_squared) with its ref (r_squared_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'r_squared_recorded_for_the_sheet', 'R squared is given: it is recorded and the sheet judges it'),
            ('unknown', 'r_squared_not_stated', 'R squared is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'standard_series_size',
        'question': 'Were there enough different standards to define the standard curve?',
        'reads': ('quantities.standard_series_points',),
        'rule': 'When the number of standards is given the grader records it (standard_points) with its ref (standard_points_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'standard_points_recorded_for_the_sheet', 'the number of standards is given: it is recorded and the sheet judges it'),
            ('unknown', 'standard_points_not_stated', 'the number of standards is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'read_inside_standard_series',
        'question': 'Was the analyte read inside the range of the standard series (not extrapolated beyond its lowest or highest standard)?',
        'reads': ('quantities.read_amount', 'quantities.standard_series_low', 'quantities.standard_series_high', 'facts.read_amount_within_standard_series'),
        'rule': 'The fact stated as no fails. When the read amount and at least one end of the series are given in the same kind of unit (both concentrations or both amounts) the grader records the read amount over the highest standard and over the lowest standard (read_over_standard_high, read_over_standard_low; None for an end not given) with their refs (standard_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'read_position_recorded_for_the_sheet', 'the read amount and an end of the series are comparable and the fact is not no: the ratios are recorded and the sheet judges them'),
            ('supported', 'read_within_series_stated', 'no comparable numbers and the fact is yes'),
            ('unknown', 'read_or_series_missing_or_not_comparable', 'no comparable numbers and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'matrix_effect_addressed',
        'question': 'Was an effect of the reaction mixture on the second enzyme addressed, by standards in the reaction buffer or by a spike that was recovered?',
        'reads': ('facts.matrix_matched_standards', 'facts.spike_recovery_done'),
        'rule': 'Either fact stated as yes is enough. If neither is yes and one is stated as no, it fails. Silence is unknown, never no.',
        'thresholds': (),
        'returns': _any_yes_returns('matrix_control_stated'),
    },
    {
        'id': 'second_enzyme_specificity',
        'question': 'Was it shown that the second enzyme does not act on the original substrate, the test compound or other components of the mixture?',
        'reads': ('facts.second_enzyme_specificity_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product identified or measured by another method, or does the substrate lost match the product gained?',
        'reads': ('facts.product_confirmed_independently', 'facts.substrate_loss_matches_product_gain'),
        'rule': 'Either fact stated as yes is enough. If neither is yes and one is stated as no, it fails. Silence is unknown, never no.',
        'thresholds': (),
        'returns': _any_yes_returns('product_identity_stated'),
    },
    {
        'id': 'first_enzyme_controls',
        'question': 'Was the signal that does not come from the first enzyme measured and set aside, by a no-enzyme blank, an inactive-enzyme control or a zero-time sample?',
        'reads': ('facts.no_enzyme_control', 'facts.inactive_enzyme_control', 'facts.zero_time_sample'),
        'rule': 'Any of the three stated as done is enough. If none is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': _any_yes_returns('enzyme_free_control_stated'),
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the conversion shown to depend on the first enzyme (it rose with the enzyme amount or time, or fell with an inhibitor or an inactive mutant)?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'endpoint_time_alignment',
        'question': 'Is the time of the end point stated, and was the first reaction stopped before the analysis, at the same time in the compared arms?',
        'reads': ('quantities.endpoint_time', 'facts.reaction_stopped_before_analysis', 'facts.same_time_for_compared_arms'),
        'rule': 'Either fact stated as no fails. Otherwise the end-point time stated together with the reaction stopped before the analysis is supported. A missing time, or a stop that is not stated, is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the stop fact or the same-time fact is no'),
            ('unknown', 'endpoint_time_not_stated', 'no fact is no and the end-point time is not given'),
            ('supported', 'time_and_stop_stated', 'the time is given and the stop fact is yes'),
            ('unknown', 'reaction_stop_not_stated', 'the time is given and the stop fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reporter_completion',
        'question': 'Did the second reaction go to completion before the signal was read (the signal reached its plateau, enough enzyme and cofactor)?',
        'reads': ('facts.reporter_conversion_complete', 'quantities.second_enzyme_incubation'),
        'rule': 'The fact stated as no fails and stated as yes is supported. Without the fact, a stated incubation time with the second enzyme is recorded (incubation_minutes, incubation_refs) and the judgement is left to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('supported', 'second_reaction_completion_stated', 'the fact is yes'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'the fact is not stated and the incubation time is given: it is recorded and the sheet judges it'),
            ('unknown', 'second_reaction_completion_not_stated', 'the fact is not stated and no incubation time is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'initial_substrate',
        'question': 'Is the amount of substrate at the start, the denominator of the share converted, stated or measured?',
        'reads': ('facts.initial_substrate_determined', 'quantities.substrate_initial'),
        'rule': 'The fact stated as no (the nominal amount was taken) fails. Otherwise the fact stated as yes, or the initial substrate concentration stated, is supported. Silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('supported', 'initial_substrate_stated', 'the fact is yes, or the concentration is given'),
            ('unknown', 'initial_substrate_not_stated', 'the fact is not stated and no concentration is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'non_detection_limit',
        'question': 'Where the paper states that no conversion was detected, how small a conversion could its assay have seen (the detection limit over the initial substrate)?',
        'reads': ('facts.conversion_detected_above_control', 'quantities.detection_limit', 'quantities.substrate_initial'),
        'rule': 'Applies only when the paper states that no conversion above the control was detected; otherwise not applicable. Then, when the detection limit and the initial substrate are both given, the grader records the limit over the initial substrate (limit_over_initial, limit_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('not_applicable', 'no_non_detection_stated', 'the paper does not state a non-detection'),
            ('unknown', 'detection_limit_recorded_for_the_sheet', 'a non-detection is stated and the limit and the initial substrate are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'detection_limit_or_substrate_not_stated', 'a non-detection is stated and the limit or the initial substrate is not given'),
            ('supported', 'never', 'never returned'),
            ('conflicting', 'never', 'never returned'),
        ),
    },
    {
        'id': 'native_reaction',
        'question': 'Is the substrate the first enzyme\'s native substrate rather than a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the conversion measured with the purified first enzyme rather than a cell extract, lysate or whole cells?',
        'reads': ('facts.purified_enzyme',),
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
)
