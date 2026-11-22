"""Endpoint_colorimetric criteria: the ONE place where the grader's criteria of a stopped colorimetric end-point experiment are declared.

This file is the single source for what the endpoint_colorimetric grader asks. The grader reports FACTS and holds NO threshold that judges goodness:
where a criterion needs a number to be compared with a limit (the product read against the ends of the standard curve, the number of standards, the
replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_endpoint_colorimetric_converter.py. The logic that answers each question
is in literature_endpoint_colorimetric_grader.py (one short function per criterion, same order). The only constants here are two unit tables, exact by
definition (FIXED_BY_DEFINITION), that turn a concentration unit into nM and an amount unit into pmol so that the product read and the ends of the
standard curve can be compared when the passage states them in the same kind of unit.

How to read an entry in ENDPOINT_COLORIMETRIC_CRITERIA
------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_colorimetric_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_colorimetric_criteria_v1'
NM_PER_UNIT = {'nM': 1.0, 'uM': 1.0e3, 'mM': 1.0e6}   # FIXED_BY_DEFINITION: the factor of each concentration unit to nM
PMOL_PER_UNIT = {'pmol': 1.0, 'nmol': 1.0e3, 'umol': 1.0e6}   # FIXED_BY_DEFINITION: the factor of each amount unit to pmol

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)


def _either_returns(supported_reason):
    return (
        ('supported', supported_reason, 'either fact is yes'),
        ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
        ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
        ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
    )


ENDPOINT_COLORIMETRIC_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the colour that the substrate and the buffer give without the enzyme (spontaneous chemistry, reagent reacting with the substrate) measured and set aside, by a no-enzyme blank or an inactive-enzyme control?',
        'reads': ('facts.no_enzyme_control', 'facts.inactive_enzyme_control'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': _either_returns('spontaneous_reaction_control_stated'),
    },
    {
        'id': 'enzyme_borne_signal',
        'question': 'Was the colour that comes from the enzyme preparation or its buffer (phosphate, ammonium, reducing ends or thiols carried over with the protein) measured and set aside, by a control without the substrate or a zero-time sample?',
        'reads': ('facts.no_substrate_control', 'facts.zero_time_sample'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': _either_returns('enzyme_borne_signal_control_stated'),
    },
    {
        'id': 'standard_curve_in_buffer',
        'question': 'Was the product standard curve made in the reaction buffer (or taken through the same steps as the samples), so that the colour per amount of product is the colour in the reactions?',
        'reads': ('facts.standard_curve_in_buffer',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_curve_range',
        'question': 'Did the amount of product read lie inside the range of the standard curve, so that it was read by interpolation and not by extrapolation?',
        'reads': ('quantities.product_read_on_curve', 'quantities.standard_curve_low', 'quantities.standard_curve_high'),
        'rule': 'When the product read and at least one end of the curve are given in the same kind of unit (concentrations, or amounts) the grader records the product over the highest standard (product_over_standard_high) and over the lowest standard (product_over_standard_low) that are given, with their refs (standard_range_refs), and leaves the judgement to the sheet. A product read in a concentration unit with an end of the curve in an amount unit (or the reverse) is unknown. Otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'standard_range_recorded_for_the_sheet', 'the product read and an end of the curve are given in the same kind of unit: the ratios are recorded and the sheet judges them'),
            ('unknown', 'standard_range_units_differ', 'the product read and an end of the curve are given in different kinds of unit (a concentration and an amount)'),
            ('unknown', 'standard_range_not_stated', 'the product read is not given, or no end of the curve is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'standard_curve_points',
        'question': 'Did the standard curve have enough standards to show that the colour is a straight line of the amount of product?',
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
        'id': 'reagent_interference_checked',
        'question': 'Was it checked that a component of the reaction (buffer, salt, reducing agent, detergent, substrate, enzyme preparation) does not give colour with the reagent or change the colour of the product?',
        'reads': ('facts.reagent_interference_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the product shown to rise with the amount of enzyme or with the incubation time?',
        'reads': ('facts.product_rises_with_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product identified by another measurement than the colour reagent (which names only a product class such as phosphate, reducing ends, a thiol or ammonia)?',
        'reads': ('facts.product_identified_independently',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'endpoint_time_stated',
        'question': 'Is the time the reaction ran before it was stopped or read stated, so that the end point is a defined time point?',
        'reads': ('quantities.endpoint_time',),
        'rule': 'A stated time is supported; a time not given is unknown (an end point whose time is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'endpoint_time_stated', 'the time is given'),
            ('unknown', 'endpoint_time_not_stated', 'the time is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reaction_stopped',
        'question': 'Was the reaction stopped at a stated moment before the colour was read (by the reagent, an acid, heat or another quench), so that the time read is the real end point?',
        'reads': ('facts.reaction_stopped',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_time_for_arms',
        'question': 'Were the test reaction and the reactions it is compared with (controls, other enzymes, other conditions) incubated and read for the same time?',
        'reads': ('facts.same_time_for_compared_arms',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'denominator_stated',
        'question': 'Is the amount of substrate at the start stated, so that a share converted has a defined denominator?',
        'reads': ('quantities.substrate_initial',),
        'rule': 'A stated initial substrate concentration is supported; one not given is unknown (a share whose denominator is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'initial_substrate_stated', 'the initial substrate concentration is given'),
            ('unknown', 'initial_substrate_not_stated', 'the initial substrate concentration is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'denominator_measured',
        'question': 'Was the amount of substrate at the start measured, rather than only weighed out or taken from a nominal stock?',
        'reads': ('facts.initial_substrate_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Wells or tubes read from one reaction mixture are not replicates.',
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
        'question': 'Was the conversion measured with the purified enzyme rather than a cell extract, lysate or whole cells?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
