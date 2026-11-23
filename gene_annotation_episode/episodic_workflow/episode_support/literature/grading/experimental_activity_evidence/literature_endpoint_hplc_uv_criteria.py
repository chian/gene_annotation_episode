"""Endpoint_hplc_uv criteria: the ONE place where the grader's criteria of a fixed-time enzyme reaction read by HPLC are declared. DRAFT of 2026-11-22,
owner to correct.

This file is the single source for what the endpoint_hplc_uv grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a
criterion needs a number to be compared with a limit (the read product amount against the standard curve, the number of standard-curve points, the
detection limit against the substrate, the control against the test, the replicate count), the grader records the number with its support refs and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_endpoint_hplc_uv_converter.py. The logic that answers each question is in literature_endpoint_hplc_uv_grader.py (one short function per
criterion, same order). There is no constant here: a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and
nothing else is compared.

How to read an entry in ENDPOINT_HPLC_UV_CRITERIA
--------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_hplc_uv_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_hplc_uv_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_HPLC_UV_CRITERIA = (
    {
        'id': 'estimate_defined',
        'question': 'Is the stated result a defined estimate: a product concentration, or a share converted together with the starting amount of substrate it is a share of?',
        'reads': ('quantities.product_amount', 'quantities.net_conversion_percent', 'quantities.conversion_percent', 'quantities.substrate_initial'),
        'rule': 'A stated product concentration is supported. A stated net or raw share converted is supported when the starting substrate concentration is stated too, and unknown when it is not. Nothing stated is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'estimate_stated', 'a product amount is stated, or a share converted with the starting substrate'),
            ('unknown', 'substrate_amount_not_stated', 'a share converted is stated and the starting substrate concentration is not'),
            ('unknown', 'no_estimate_stated', 'no product amount and no share converted is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) conversion of the substrate measured and set aside, by a no-enzyme control or an inactive-enzyme control?',
        'reads': ('facts.no_enzyme_control_done', 'facts.inactive_enzyme_control_done'),
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
        'id': 'zero_time_sample',
        'question': 'Was a sample taken at time zero (or stopped before the enzyme could act) and analysed, so the starting substrate and any product already present are known?',
        'reads': ('facts.zero_time_sample_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the conversion shown to depend on the enzyme (more enzyme gives more conversion, an inhibitor or an inactive mutant gives less)?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'signal_over_control',
        'question': 'Is the conversion with the enzyme larger than the conversion in the paper\'s own control, and by how much?',
        'reads': ('quantities.conversion_percent', 'quantities.control_conversion_percent'),
        'rule': 'When both the test and the control conversion are stated the grader records them (test_percent, control_percent, control_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'control_comparison_recorded_for_the_sheet', 'both are stated: they are recorded and the sheet judges them'),
            ('unknown', 'test_or_control_conversion_not_stated', 'the test or the control conversion is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'product_identified',
        'question': 'Was the product peak identified (by an authentic standard of the product, or confirmed by a second method such as mass spectrometry), not just assumed from a retention time?',
        'reads': ('facts.authentic_standard_used', 'facts.peak_confirmed_by_second_method'),
        'rule': 'Either fact stated as yes is enough. If neither is yes and one is no, it fails. Stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'product_identified_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'mass_balance',
        'question': 'Does the substrate lost equal the product gained (the mass balance closes), so the conversion is the claimed reaction and not a side loss?',
        'reads': ('facts.substrate_loss_matches_product_gain',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'endpoint_time_stated',
        'question': 'Is the time of the end point stated, and were the compared reactions stopped at the same time?',
        'reads': ('quantities.endpoint_time', 'facts.same_time_for_compared_arms'),
        'rule': 'The same-time fact stated as no fails. Otherwise a stated end-point time is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the same-time fact is no'),
            ('supported', 'endpoint_time_stated', 'the same-time fact is not no and the end-point time is stated'),
            ('unknown', 'endpoint_time_not_stated', 'the same-time fact is not no and the end-point time is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reaction_stopped',
        'question': 'Was the reaction stopped (quenched or the enzyme removed) before analysis, so the time read is the real end point and not a time that kept running in the vial?',
        'reads': ('facts.reaction_stopped_before_analysis',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'denominator_established',
        'question': 'Is the denominator of the share converted established: the starting substrate was measured, or both substrate and product were quantified so the share is taken over their sum?',
        'reads': ('facts.initial_substrate_determined', 'facts.both_species_quantified'),
        'rule': 'Either fact stated as yes is enough. If neither is yes and one is no, it fails. Stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'denominator_established_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'standard_curve_range',
        'question': 'Does the read product concentration lie inside the concentration range of the standard curve?',
        'reads': ('quantities.product_amount', 'quantities.standard_curve_low', 'quantities.standard_curve_high'),
        'rule': 'When the product concentration and both ends of the standard curve are given the grader records the read concentration over the lowest standard and over the highest standard (read_over_curve_low, read_over_curve_high) with their refs (curve_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'standard_curve_range_recorded_for_the_sheet', 'the product concentration and the two ends are given: the two ratios are recorded and the sheet judges them'),
            ('unknown', 'product_amount_or_curve_missing', 'the product concentration or an end of the curve is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'standard_curve_points',
        'question': 'Did the standard curve have enough different concentrations to show the response is linear?',
        'reads': ('quantities.standard_curve_points',),
        'rule': 'When the number of points is given the grader records it (calibration_points, calibration_points_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'calibration_points_recorded_for_the_sheet', 'the number of points is given: it is recorded and the sheet judges it'),
            ('unknown', 'calibration_points_not_stated', 'the number of points is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'detection_limit_share',
        'question': 'Is the detection or quantification limit small against the starting substrate, so a small conversion could have been seen?',
        'reads': ('quantities.detection_limit', 'quantities.substrate_initial'),
        'rule': 'When the limit and the starting substrate are both given the grader records the limit over the substrate (detection_limit_over_substrate) with its refs (detection_limit_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'detection_limit_recorded_for_the_sheet', 'the limit and the substrate are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'detection_limit_or_substrate_missing', 'the limit or the starting substrate is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'matrix_matched_calibration',
        'question': 'Were matrix and handling effects addressed: a standard curve made in the reaction buffer or matrix, or an internal standard added to the samples?',
        'reads': ('facts.calibration_in_matrix', 'facts.internal_standard_used'),
        'rule': 'Either fact stated as yes is enough. If neither is yes and one is no, it fails. Stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'matrix_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicate reactions, run as independent reactions (not repeated injections of one reaction)?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated injections of one sample are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate or analogue?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the conversion measured with the purified enzyme rather than a cell extract, lysate or whole cells?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
