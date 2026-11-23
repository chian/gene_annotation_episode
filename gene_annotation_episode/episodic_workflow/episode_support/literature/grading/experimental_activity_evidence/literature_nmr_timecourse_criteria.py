"""Nmr_timecourse criteria: the ONE place where the grader's criteria of a real-time NMR progress-curve enzyme assay are declared.

This file is the single source for what the nmr_timecourse grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the share of the substrate consumed, the enzyme over the
substrate plus Km, the substrate series against the Km, the signal-to-noise ratio, the relaxation delay over the longest T1, the number of
time points, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_nmr_timecourse_converter.py. The
logic that answers each question is in literature_nmr_timecourse_grader.py (one short function per criterion, same order). The only constants
here are unit conversions (FIXED_BY_DEFINITION): a concentration unit is turned into nM by the reader's fixed scale table, and a time unit
into seconds by S_PER_UNIT below; nothing else is compared.

What marks the method, and so these criteria: the species are seen by their chemical shifts (a product that is assigned is identified, not
inferred), and the amounts come from integrals. An integral is quantitative only when the nuclei relaxed between scans, the signal stands
well above the noise and the amount is tied to a reference (an internal standard of known concentration, or the conserved sum of substrate
and product). The method is insensitive, so it uses micromolar enzyme and millimolar substrate, and the enzyme-over-substrate and substrate
range criteria are asked as in every activity_rate type.

How to read an entry in NMR_TIMECOURSE_CRITERIA
-----------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_nmr_timecourse_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_nmr_timecourse_criteria'
S_PER_UNIT = {'s': 1.0, 'ms': 1.0e-3}   # FIXED_BY_DEFINITION: a millisecond is a thousandth of a second.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

NMR_TIMECOURSE_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) change of the substrate measured and set aside, by a no-enzyme spectrum series or an inactive-enzyme control?',
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
        'id': 'pre_reaction_spectrum',
        'question': 'Was a spectrum of the substrate recorded before the enzyme was added, showing the substrate without the product and without an overlapping resonance?',
        'reads': ('facts.pre_reaction_spectrum',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
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
        'id': 'product_assignment',
        'question': 'Was the product resonance assigned to the claimed product (an authentic standard, spiking, or two-dimensional or coupling information)?',
        'reads': ('facts.product_assigned',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'quantitation_reference',
        'question': 'Are the integrals tied to a reference amount: an internal concentration standard, or a conserved sum of substrate and product?',
        'reads': ('facts.internal_standard_used', 'facts.mass_balance_closed'),
        'rule': 'Either fact stated as yes is enough. A mass balance stated as not closed (and no yes) fails. An internal standard stated as not used is not a failure by itself (the integrals can still be read as a share of the sum), so it is unknown. A reference stated nowhere is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'quantitation_reference_stated', 'either fact is yes'),
            ('conflicting', 'mass_balance_not_closed', 'neither is yes and the mass balance is no'),
            ('unknown', 'internal_standard_not_used', 'neither is yes, the mass balance is not no and the internal standard is no'),
            ('unknown', 'fact_unknown', 'neither is yes and none is no and a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'signal_to_noise',
        'question': 'Does the integrated resonance stand far enough above the noise for its integral to be a reliable amount?',
        'reads': ('quantities.signal_to_noise',),
        'rule': 'When the signal-to-noise ratio is given the grader records it (signal_to_noise, signal_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'signal_to_noise_recorded_for_the_sheet', 'the ratio is given: it is recorded and the sheet judges it'),
            ('unknown', 'signal_to_noise_not_stated', 'the ratio is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'relaxation',
        'question': 'Did the nuclei relax between scans, so that the integrals are proportional to the amounts?',
        'reads': ('quantities.relaxation_delay', 'quantities.longest_t1', 'facts.fully_relaxed_acquisition'),
        'rule': 'A fully-relaxed fact stated as no fails. When the relaxation delay and the longest T1 are both given the grader records the delay over the T1 (relaxation_over_t1, in seconds over seconds through S_PER_UNIT) with its refs (relaxation_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': ('S_PER_UNIT',),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fully-relaxed fact is no'),
            ('unknown', 'relaxation_recorded_for_the_sheet', 'the delay and the T1 are given and the fact is not no: the ratio is recorded and the sheet judges it'),
            ('supported', 'fully_relaxed_acquisition_stated', 'the delay and the T1 are not both given and the fact is yes'),
            ('unknown', 'relaxation_not_stated', 'the delay and the T1 are not both given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the progress curve where little substrate has been consumed?',
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
        'id': 'progress_curve_points',
        'question': 'Were there enough spectra (time points) in the progress curve to fix its slope?',
        'reads': ('quantities.time_point_count',),
        'rule': 'When the number of time points is given the grader records it (time_point_count, time_point_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'time_points_recorded_for_the_sheet', 'the count is given: it is recorded and the sheet judges it'),
            ('unknown', 'time_points_not_stated', 'the count is not given'),
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
        'question': 'Were there enough replicate time courses, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated acquisitions of one sample are not replicates.',
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
        'question': 'Was the activity measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
