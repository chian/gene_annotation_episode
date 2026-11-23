"""Ph_stat criteria: the ONE place where the grader's criteria of a pH-stat titration enzyme assay are declared.

DRAFT of 2026-11-22 (owner to confirm). This file is the single source for what the ph_stat grader asks. The grader reports FACTS and holds NO
threshold that judges goodness: where a criterion needs a number to be compared with a limit (the share of the substrate consumed, the enzyme over
the substrate plus Km, the substrate series against the Km, the gap between the product pKa and the set pH, the buffer concentration, the replicate
count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and
its EXPERT_REVIEW constants are on the sheet side, in literature_ph_stat_converter.py. The logic that answers each question is in
literature_ph_stat_grader.py (one short function per criterion, same order). There is no constant here: a concentration unit is turned into nM by the
reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

What is particular to a pH-stat. The readout is the base added to hold the pH, so it counts EVERY proton the mixture releases: the reaction's own,
the spontaneous hydrolysis of the substrate, the carbon dioxide that dissolves at a pH above 7, an acid-producing contaminant. The three controls and the
carbon dioxide exclusion therefore answer different questions. The base added is the reaction's rate only for the share of the released protons that
are titrated at the set pH (the proton yield), and only if the titrant keeps up (the buffer in the vessel sets how far the added base lags the reaction).
The titrant concentration, finally, is the only calibration of the rate: no extinction coefficient stands between the base added and the rate.

How to read an entry in PH_STAT_CRITERIA
----------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_ph_stat_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_ph_stat_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

PH_STAT_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) consumption of base by the substrate measured and set aside, by a no-enzyme blank or an inactive-enzyme control?',
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
        'question': 'Was the base consumed by the enzyme preparation without the substrate (an acid-producing contaminant, a deamidating protein) measured with a no-substrate control?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'carbon_dioxide_excluded',
        'question': 'Was carbon dioxide kept out of the reaction, so that the carbon dioxide that dissolves at the set pH did not consume the titrant?',
        'reads': ('facts.carbon_dioxide_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the rate of base addition shown to be proportional to the amount of enzyme?',
        'reads': ('facts.rate_proportional_to_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the base consumed shown to be the claimed reaction (the acid or the alcohol identified by another measurement)?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'titrant_standardized',
        'question': 'Was the concentration of the titrant determined (standardized), since it is the only calibration of the rate?',
        'reads': ('facts.titrant_standardized',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'proton_yield',
        'question': 'Is the share of the released protons that the titrant counts at the set pH stated or corrected, so that the base added is the rate of the reaction?',
        'reads': ('facts.ionization_corrected', 'quantities.ph_set_point', 'quantities.product_pka'),
        'rule': 'The correction (or a determination of the proton yield per product) stated as done is supported. Otherwise, when the set pH and the pKa of the product are both given the grader records the pKa minus the pH (product_pka_minus_ph, pH units) with their refs (proton_yield_refs) and leaves the judgement to the sheet. Otherwise unknown: a yield stated nowhere, or a correction stated as not made with no pKa and pH to show it unneeded, is not shown wrong. The criterion covers a reaction that releases protons and is titrated with a base.',
        'thresholds': (),
        'returns': (
            ('supported', 'ionization_correction_stated', 'the correction fact is yes'),
            ('unknown', 'proton_yield_recorded_for_the_sheet', 'the correction fact is not yes and the pH and the pKa are given: the gap is recorded and the sheet judges it'),
            ('unknown', 'proton_yield_not_stated', 'the correction fact is not yes and the pH or the pKa is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'buffer_capacity',
        'question': 'Was the reaction run with little or no buffer, so that the titrant follows the release of protons without a lag?',
        'reads': ('facts.reaction_unbuffered', 'quantities.buffer_concentration'),
        'rule': 'A reaction stated as unbuffered is supported. Otherwise, when the buffer concentration is given the grader records it in nM (buffer_nM) with its ref (buffer_refs) and leaves the judgement to the sheet. Otherwise unknown (the buffer is not stated, or the reaction is buffered at a level not stated).',
        'thresholds': (),
        'returns': (
            ('supported', 'reaction_unbuffered_stated', 'the unbuffered fact is yes'),
            ('unknown', 'buffer_recorded_for_the_sheet', 'the unbuffered fact is not yes and the buffer concentration is given: it is recorded and the sheet judges it'),
            ('unknown', 'buffer_not_stated', 'the unbuffered fact is not yes and no buffer concentration is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the titration curve where little substrate has been consumed?',
        'reads': ('quantities.substrate_consumed_percent', 'facts.linear_progress_curve'),
        'rule': 'A linear-progress-curve fact stated as no fails. When the share of the substrate consumed is given the grader records it (consumed_percent, consumed_refs) and leaves the judgement to the sheet. Otherwise the linear-progress-curve fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-progress-curve fact is no'),
            ('unknown', 'consumed_recorded_for_the_sheet', 'the share consumed is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_progress_curve_stated', 'no share consumed is given and the fact is yes'),
            ('unknown', 'rate_regime_not_stated', 'no share consumed is given and the fact is not stated'),
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
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated titrations of one reaction mixture are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate (a short-chain ester, an emulsion of a triglyceride)?',
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
