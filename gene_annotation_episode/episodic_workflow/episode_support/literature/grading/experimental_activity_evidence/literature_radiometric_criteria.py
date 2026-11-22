"""Radiometric criteria: the ONE place where the grader's criteria of a radiometric enzyme assay are declared.

This file is the single source for what the radiometric grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the share of the substrate converted, the counts over the blank, the
enzyme over the substrate plus Km, the substrate series against the Km, the replicate count), the grader records the number
with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_radiometric_converter.py. The logic that answers each question is in
literature_radiometric_grader.py (one short function per criterion, same order). There is no constant here: a concentration unit is
turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

What is particular to a radiometric assay (and so is asked here and not for an optical assay): the signal is the label of the substrate
carried into the product, so (a) the blank is not a chromophore drift but substrate carried through the separation and label impurities
(a zero-time sample or the substrate alone through the separation), (b) the product is known only through the separation (identity by
co-migration or by another method), (c) counts become an amount only through the specific radioactivity and the counting efficiency, and (d)
the product can be lost on the way (recovery of the separation).

How to read an entry in RADIOMETRIC_CRITERIA
--------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_radiometric_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_radiometric_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

RADIOMETRIC_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) conversion of the labelled substrate measured and set aside, by a no-enzyme blank or an inactive-enzyme control?',
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
        'id': 'carryover_control',
        'question': 'Was the label that reaches the product fraction without any reaction (unconverted substrate carried through the separation, label impurity of the substrate) measured, by a zero-time sample or by the substrate alone taken through the separation?',
        'reads': ('facts.zero_time_control', 'facts.separation_blank_control'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'carryover_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'counts_over_background',
        'question': 'How large are the counts of the reaction over the counts of its own blank?',
        'reads': ('quantities.counts_over_background',),
        'rule': 'When the fold over the blank is given the grader records it (counts_over_background) with its ref (background_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'background_ratio_recorded_for_the_sheet', 'the fold over the blank is given: it is recorded and the sheet judges it'),
            ('unknown', 'background_ratio_not_stated', 'the fold over the blank is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the rate shown to be proportional to the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the counted label shown to be the product of the claimed reaction (identified by co-migration with an authentic standard or by another measurement), and not only label found in a fraction?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'specific_radioactivity_stated',
        'question': 'Is the specific radioactivity of the labelled substrate, as used in the reaction, stated?',
        'reads': ('quantities.specific_radioactivity',),
        'rule': 'Stated is supported; not stated is unknown (a rate whose conversion constant is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'specific_radioactivity_stated', 'the specific radioactivity is given'),
            ('unknown', 'specific_radioactivity_missing', 'it is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'counting_calibration',
        'question': 'Were the counts converted into an amount of product with the counting efficiency (dpm, quench correction or an internal standard) and the specific radioactivity?',
        'reads': ('facts.counts_converted_to_amount',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'separation_recovery',
        'question': 'Was the recovery of the product through the separation and counting steps determined or corrected for?',
        'reads': ('facts.separation_recovery_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the time course where little substrate has been converted?',
        'reads': ('quantities.substrate_converted_percent', 'facts.linear_time_course'),
        'rule': 'A linear-time-course fact stated as no fails. When the share of the substrate converted is given the grader records it (converted_percent, converted_refs) and leaves the judgement to the sheet. Otherwise the linear-time-course fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-time-course fact is no'),
            ('unknown', 'converted_recorded_for_the_sheet', 'the share converted is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_time_course_stated', 'no share converted is given and the fact is yes'),
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
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated counts of one reaction mixture are not replicates.',
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
        'question': 'Is the labelled substrate the enzyme\'s native substrate rather than an analogue or a surrogate?',
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
