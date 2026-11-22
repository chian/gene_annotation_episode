"""Product_immunodetection criteria: the ONE place where the grader's criteria of an antibody-detected enzyme reaction are declared.

This file is the single source for what the product_immunodetection grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the share of the substrate converted, the enzyme over the
substrate plus Km, the substrate series against the Km, the number of standards, the Z' factor or the signal-to-background, the replicate count),
the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its
EXPERT_REVIEW constants are on the sheet side, in literature_product_immunodetection_converter.py. The logic that answers each question is in
literature_product_immunodetection_grader.py (one short function per criterion, same order). There is no constant here: a concentration unit is
turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in PRODUCT_IMMUNODETECTION_CRITERIA
--------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_product_immunodetection_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_product_immunodetection_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

PRODUCT_IMMUNODETECTION_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the signal that appears without the enzyme (non-enzymatic modification, antibody binding to the substrate or the plate) measured and set aside, by a no-enzyme blank or an inactive-enzyme control?',
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
        'id': 'cofactor_dependence',
        'question': 'Was the signal shown to need the donor of the modification (ATP, S-adenosylmethionine, acetyl-CoA, ubiquitin or the other co-substrate), by a reaction without it?',
        'reads': ('facts.no_cofactor_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_independent_signal',
        'question': 'Was the signal that does not need the substrate (self-modification of the enzyme, an antibody that sees the enzyme itself) measured with a no-substrate control?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'antibody_product_specificity',
        'question': 'Was the antibody shown to recognise the modified product and not the unmodified substrate (or other modified species)?',
        'reads': ('facts.antibody_specific_for_product',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the product shown to be proportional to the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the modified product (or the site of the modification) shown to be the claimed one by another measurement than the antibody?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_calibration',
        'question': 'Was the antibody signal turned into an amount of product by a standard series of the modified product, when an amount-based rate is claimed?',
        'reads': ('facts.product_standard_curve', 'standard_series', 'quantities.catalytic_efficiency', 'quantities.turnover', 'quantities.specific_activity'),
        'rule': 'A standard curve stated as not used fails when an amount-based quantity (kcat/Km, kcat or specific activity) is stated, and is not applicable when only a fold over the control is stated (a fold needs no calibration). When the standard series is given the grader records the number of standards (standard_point_count, standard_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'standard_curve_not_used_for_an_amount_based_quantity', 'the fact is no and an amount-based quantity is stated'),
            ('not_applicable', 'relative_readout_needs_no_standard_curve', 'the fact is no and no amount-based quantity is stated'),
            ('unknown', 'standard_series_recorded_for_the_sheet', 'the standard series is given and the fact is not no: the number of standards is recorded and the sheet judges it'),
            ('supported', 'product_standard_curve_stated', 'no standard series is given and the fact is yes'),
            ('not_applicable', 'fact_not_applicable', 'no standard series is given and the fact is not_applicable'),
            ('unknown', 'product_standard_curve_not_stated', 'no standard series is given and the fact is not stated'),
        ),
    },
    {
        'id': 'assay_window',
        'question': 'Is the separation of the signal of the reaction from the background (the Z\' factor, or the signal-to-background) large enough to read a rate?',
        'reads': ('quantities.z_prime', 'quantities.signal_to_background'),
        'rule': 'When the Z\' factor or the signal-to-background is given the grader records them (z_prime, signal_to_background, window_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'assay_window_recorded_for_the_sheet', 'a Z\' factor or a signal-to-background is given: it is recorded and the sheet judges it'),
            ('unknown', 'assay_window_not_stated', 'neither is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'signal_range',
        'question': 'Did the measured signals stay in the working range of the detection (inside the standard curve, not saturated, not in the hook region)?',
        'reads': ('facts.signal_within_standard_range',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: product formed in a time over which little substrate has been converted and the product grows linearly with time?',
        'reads': ('quantities.substrate_converted_percent', 'facts.linear_in_time'),
        'rule': 'A linear-in-time fact stated as no fails. When the share of the substrate converted is given the grader records it (converted_percent, converted_refs) and leaves the judgement to the sheet. Otherwise the linear-in-time fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-in-time fact is no'),
            ('unknown', 'converted_recorded_for_the_sheet', 'the share converted is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_in_time_stated', 'no share converted is given and the fact is yes'),
            ('unknown', 'rate_regime_not_stated', 'no share converted is given and the fact is not stated'),
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
        'question': 'Is the substrate the enzyme\'s native substrate (for example the full-length protein) rather than a surrogate (a short synthetic peptide)?',
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
