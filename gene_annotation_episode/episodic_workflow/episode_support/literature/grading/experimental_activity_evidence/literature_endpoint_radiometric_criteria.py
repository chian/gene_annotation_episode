"""Endpoint_radiometric criteria: the ONE place where the grader's criteria of a radiometric end-point conversion experiment are declared.

This file is the single source for what the endpoint_radiometric grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the counts of the test over the counts of the blank, the replicate
count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_endpoint_radiometric_converter.py. The logic that answers each
question is in literature_endpoint_radiometric_grader.py (one short function per criterion, same order). There is no constant here and nothing
is compared.

How to read an entry in ENDPOINT_RADIOMETRIC_CRITERIA
-----------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_radiometric_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_radiometric_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_RADIOMETRIC_CRITERIA = (
    {
        'id': 'spontaneous_conversion_control',
        'question': 'Was the label\'s own conversion without the enzyme (spontaneous breakdown of the substrate, label carried into the product fraction by the enzyme-free reaction) measured with a no-enzyme control or an inactive-enzyme control?',
        'reads': ('facts.no_enzyme_control_done', 'facts.inactive_enzyme_control_done'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_conversion_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'separation_background_control',
        'question': 'Was the carry-over of the labelled substrate into the product fraction measured: the substrate alone, or a sample stopped at time zero, taken through the separation and counted?',
        'reads': ('facts.separation_control_done', 'facts.zero_time_sample_done'),
        'rule': 'Either fact stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'separation_background_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'counts_over_background',
        'question': 'Is the counted signal of the test reaction well above the counts of the paper\'s own blank?',
        'reads': ('quantities.counts_test', 'quantities.counts_background', 'quantities.signal_over_background'),
        'rule': 'When both counts are given in the same unit the grader records their ratio (signal_over_background) with the refs of both (counts_refs) and leaves the judgement to the sheet. Otherwise, when the ratio itself is stated, the grader records it. Counts in different units, or nothing stated, are unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'counts_recorded_for_the_sheet', 'the ratio is given or both counts are given in one unit: it is recorded and the sheet judges it'),
            ('unknown', 'counts_in_different_units', 'both counts are given but in different units, and no ratio is stated'),
            ('unknown', 'counts_not_stated', 'no ratio and no pair of counts is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'specific_radioactivity_stated',
        'question': 'When an amount of product is stated, is the specific radioactivity that turns counts into that amount stated?',
        'reads': ('quantities.product_amount', 'quantities.specific_radioactivity'),
        'rule': 'No amount of product stated: not applicable (a share converted is a ratio of counts and needs no specific radioactivity). An amount stated with the specific radioactivity is supported; an amount stated without it is unknown (an amount whose conversion constant is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'specific_radioactivity_stated', 'an amount and the specific radioactivity are given'),
            ('unknown', 'specific_radioactivity_not_stated', 'an amount is given and the specific radioactivity is not'),
            ('not_applicable', 'no_product_amount_stated', 'no amount of product is given'),
        ),
    },
    {
        'id': 'counting_efficiency',
        'question': 'Were the counts corrected for counting efficiency or quenching, so that colour or sample material does not change the counted fraction?',
        'reads': ('facts.counting_efficiency_corrected',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the conversion shown to depend on the enzyme (it rises with the amount of enzyme or time, or it is absent with the inactive enzyme, the mutant or an inhibitor)?',
        'reads': ('facts.conversion_depends_on_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the counted product identified by an authentic standard or by an independent identification, rather than only by where the label ran in the separation?',
        'reads': ('facts.product_identified_by_standard',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'label_in_product_position',
        'question': 'Is the radioactive label on the part of the substrate that ends up in the counted product?',
        'reads': ('facts.label_in_product_position',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'endpoint_time_and_stop',
        'question': 'Is the time of the end point stated, and was the reaction stopped before the product was separated, so that the stated time is the real end of the reaction?',
        'reads': ('quantities.endpoint_time', 'facts.reaction_stopped_before_analysis'),
        'rule': 'The stop stated as not done fails. The time stated and the stop stated as done is supported. Either one missing is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the reaction is stated as not stopped before the analysis'),
            ('supported', 'time_and_stop_stated', 'the time is given and the stop is yes'),
            ('unknown', 'time_or_stop_not_stated', 'the time is not given or the stop is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'same_time_in_compared_arms',
        'question': 'Were the test and the control (or the compared enzymes and conditions) incubated for the same time?',
        'reads': ('facts.same_time_for_compared_arms',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'fraction_over_total_label',
        'question': 'Is the share converted taken over the total radioactivity of the same sample (substrate plus product), so that the denominator is measured and not nominal?',
        'reads': ('facts.fraction_over_total_label',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'native_reaction',
        'question': 'Is the labelled substrate the enzyme\'s native substrate rather than a surrogate or an analogue?',
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
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated counts of one reaction are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
