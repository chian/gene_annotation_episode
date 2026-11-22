"""Luminescent criteria: the ONE place where the grader's criteria of a luminescent enzyme assay are declared.

The assay (ADP-Glo, Kinase-Glo, NAD(P)H-Glo, luciferase-coupled pyrophosphate or ATP detection) turns the product, or the substrate left, into
light through a luciferase reaction; the light (RLU) means an amount of product only through a standard series read in the same plate.

This file is the single source for what the luminescent grader asks. The grader reports FACTS and holds NO threshold that judges goodness:
where a criterion needs a number to be compared with a limit (the share of the substrate converted, the enzyme over the substrate plus Km,
the substrate series against the Km, the highest product over the highest standard, the Z' factor, the replicate count), the grader records
the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_luminescent_converter.py. The logic that answers each question is in
literature_luminescent_grader.py (one short function per criterion, same order). There is no constant here: a concentration unit is turned into
nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in LUMINESCENT_CRITERIA
--------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_luminescent_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_luminescent_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

LUMINESCENT_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the light of the reaction without enzyme (reagent background, ATP carried over, spontaneous substrate breakdown) measured and set aside, by a no-enzyme blank or an inactive-enzyme control?',
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
        'id': 'substrate_independent_signal',
        'question': 'Was the enzyme-dependent light that does not need the substrate (a kinase\'s autophosphorylation, an ATPase activity of the preparation) measured with a no-substrate control?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'assay_window',
        'question': 'Is the signal of the assay separated from its control by a usable margin (the Z\' factor)?',
        'reads': ('quantities.z_prime',),
        'rule': 'When the Z\' factor is given the grader records it (z_prime) with its ref (z_prime_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'z_prime_recorded_for_the_sheet', 'the Z\' factor is given: it is recorded and the sheet judges it'),
            ('unknown', 'z_prime_not_stated', 'the Z\' factor is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'detection_interference_control',
        'question': 'Was it checked that the luciferase detection step is not disturbed by the reaction mixture (a known ATP or ADP amount added to the mixture without enzyme, or a luciferase counter-screen)?',
        'reads': ('facts.detection_interference_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the signal or rate shown to be proportional to the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the reaction behind the light shown to be the claimed reaction (the modified substrate or the product identified by another measurement, not only the ADP or ATP the luciferase reads)?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_curve_used',
        'question': 'Was the light turned into an amount of product with a standard series of known ATP or ADP amounts read in the same assay?',
        'reads': ('facts.standard_curve_used',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_range',
        'question': 'Did the product read in the reaction stay within the range of the standard series?',
        'reads': ('quantities.standard_curve_highest', 'quantities.product_concentration_highest', 'facts.signal_in_standard_range'),
        'rule': 'The range fact stated as no fails. When the highest standard and the highest product are both given the grader records the highest product over the highest standard (product_over_standard_top, dimensionless) with their refs (standard_range_refs) and leaves the judgement to the sheet. Otherwise the range fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the range fact is no'),
            ('unknown', 'product_over_standard_recorded_for_the_sheet', 'both numbers are given and the fact is not no: the ratio is recorded and the sheet judges it'),
            ('supported', 'signal_in_standard_range_stated', 'the numbers are not both given and the fact is yes'),
            ('unknown', 'standard_range_not_stated', 'the numbers are not both given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the time course where little substrate has been converted?',
        'reads': ('quantities.substrate_consumed_percent', 'facts.linear_progress_curve'),
        'rule': 'A linear-time-course fact stated as no fails. When the share of the substrate converted is given the grader records it (consumed_percent, consumed_refs) and leaves the judgement to the sheet. Otherwise the linear-time-course fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-time-course fact is no'),
            ('unknown', 'consumed_recorded_for_the_sheet', 'the share converted is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_progress_curve_stated', 'no share converted is given and the fact is yes'),
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
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated wells of one reaction mixture are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate (a generic protein or peptide, or ATP alone)?',
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
