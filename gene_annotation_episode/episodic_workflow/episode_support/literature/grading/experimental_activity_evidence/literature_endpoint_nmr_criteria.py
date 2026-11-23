"""Endpoint_nmr criteria: the ONE place where the grader's criteria of an NMR end-point conversion experiment are declared. DRAFT, owner to correct.

This file is the single source for what the endpoint_nmr grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the relaxation delay against T1, the signal-to-noise ratio, the acquisition time against the
end-point time, the detection limit of a non-detection, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_endpoint_nmr_converter.py. The logic that answers
each question is in literature_endpoint_nmr_grader.py (one short function per criterion, same order). The only constants here are unit conversions, FIXED_BY_DEFINITION.

What the experiment is: one enzyme reaction read by NMR at one stated time or at completion; the integrals of an assigned substrate and product signal give the
share of the substrate converted. What can go wrong, and so what the criteria ask: a background reaction that is not the enzyme's (controls, enzyme dependence); a
product signal that is not the product (assignment, mass balance); integrals that are not proportional to the amount (the nuclei did not relax between scans, the
signal is too small against the noise, signals overlap); an end point that is not a time point (the reaction ran on during a long acquisition); a share with no
fixed denominator; a negative result whose spectrum could not have shown a small conversion; and the common conditions (native substrate, purified enzyme,
independent replicates).

How to read an entry in ENDPOINT_NMR_CRITERIA
----------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_nmr_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_nmr_criteria'

PERCENT_PER_FRACTION = 100.0                              # FIXED_BY_DEFINITION: a percent is a hundredth.
SECONDS_PER_UNIT = {'ms': 0.001, 's': 1.0}                # FIXED_BY_DEFINITION: the unit spellings of a relaxation time.
MINUTES_PER_UNIT = {'s': 1.0 / 60.0, 'min': 1.0, 'h': 60.0}   # FIXED_BY_DEFINITION: the unit spellings of a time.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_NMR_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) conversion of the substrate measured and set aside, by a no-enzyme spectrum or an inactive-enzyme spectrum?',
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
        'id': 'enzyme_dependence',
        'question': 'Was the conversion shown to depend on the enzyme (it rises with the enzyme amount, or is lost when the enzyme is inactivated, inhibited or removed)?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_assignment',
        'question': 'Was the product signal assigned to the claimed product (the spectrum of an authentic standard, spiking, or a stated further assignment) rather than inferred from the loss of the substrate signal?',
        'reads': ('facts.product_signal_assigned',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'mass_balance',
        'question': 'Does the loss of the substrate signal match the gain of the product signal (the sum of the integrals stays constant, no other signal appears)?',
        'reads': ('facts.substrate_loss_matches_product_gain',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'relaxation_delay',
        'question': 'Were the nuclei given time to relax between scans, so that the integrals are proportional to the amounts?',
        'reads': ('quantities.relaxation_delay', 'quantities.longest_t1', 'facts.quantitative_acquisition'),
        'rule': 'A quantitative-acquisition fact stated as no fails. When the relaxation delay is given the grader records it in seconds (relaxation_delay_s) and the longest T1 in seconds when it is given (longest_t1_s, otherwise None) with their refs (relaxation_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the quantitative-acquisition fact is no'),
            ('unknown', 'relaxation_delay_recorded_for_the_sheet', 'the delay is given and the fact is not no: the delay (and the T1 when given) is recorded and the sheet judges it'),
            ('supported', 'quantitative_acquisition_stated', 'no delay is given and the fact is yes'),
            ('unknown', 'relaxation_not_stated', 'no delay is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'signal_to_noise',
        'question': 'Is the signal the conversion rests on large enough against the noise to be integrated?',
        'reads': ('quantities.signal_to_noise',),
        'rule': 'When the signal-to-noise ratio is given the grader records it (signal_to_noise, signal_to_noise_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'signal_to_noise_recorded_for_the_sheet', 'the ratio is given: it is recorded and the sheet judges it'),
            ('unknown', 'signal_to_noise_not_stated', 'the ratio is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'signals_resolved',
        'question': 'Are the integrated substrate and product signals separate from each other and from the buffer, protein and other signals?',
        'reads': ('facts.signals_resolved',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'time_alignment',
        'question': 'Is the conversion the conversion at the stated time: the reaction was stopped before the spectrum, or the spectrum took short against the time, and the compared arms were read at the same time?',
        'reads': ('quantities.endpoint_time', 'quantities.acquisition_duration', 'facts.reaction_stopped_before_analysis', 'facts.same_time_for_compared_arms'),
        'rule': 'The same-time fact stated as no fails. The end-point time not given is unknown. With the time given and the reaction stopped before the spectrum stated as yes it is supported. With the time given, the stop not stated as yes and the acquisition time given, the grader records the acquisition time over the end-point time (acquisition_over_endpoint_time, window_refs) and leaves the judgement to the sheet; with no acquisition time given it is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the same-time fact is no'),
            ('unknown', 'endpoint_time_not_stated', 'the end-point time is not given'),
            ('supported', 'reaction_stopped_at_the_stated_time', 'the time is given and the reaction was stopped before the spectrum'),
            ('unknown', 'acquisition_window_recorded_for_the_sheet', 'the time and the acquisition time are given and the stop is not yes: the ratio is recorded and the sheet judges it'),
            ('unknown', 'acquisition_window_not_stated', 'the time is given, the stop is not yes and no acquisition time is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'integral_denominator',
        'question': 'Is the denominator of the conversion fixed by the spectra: both substrate and product integrals of one spectrum, a spectrum before the enzyme, or an internal standard of known concentration?',
        'reads': ('facts.both_species_integrated', 'facts.initial_substrate_determined', 'facts.internal_standard_used'),
        'rule': 'Any of the three stated as yes is enough. All three stated as no fails. Otherwise unknown (a denominator stated nowhere is unknown, never no).',
        'thresholds': (),
        'returns': (
            ('supported', 'denominator_fixed_by_the_spectra', 'any of the three facts is yes'),
            ('conflicting', 'no_denominator_reference', 'all three facts are no'),
            ('unknown', 'denominator_not_stated', 'none is yes and not all three are no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'non_detection_limit',
        'question': 'For a result stated as not detected: could the spectrum have shown a small conversion (is the detection limit stated and low)?',
        'reads': ('facts.conversion_detected_above_control', 'quantities.detection_limit'),
        'rule': 'Applies only when the not-detected fact is no. Then, when the detection limit is given, the grader records it as a fraction (detection_limit_fraction, detection_refs) and leaves the judgement to the sheet; when it is not given it is unknown. When the fact is yes or not stated the criterion is not applicable.',
        'thresholds': (),
        'returns': (
            ('not_applicable', 'not_a_stated_non_detection', 'the fact is not no'),
            ('unknown', 'detection_limit_recorded_for_the_sheet', 'the fact is no and the limit is given: it is recorded and the sheet judges it'),
            ('unknown', 'detection_limit_not_stated', 'the fact is no and no limit is given'),
        ),
    },
    {
        'id': 'native_reaction',
        'question': 'Is the substrate the enzyme\'s native substrate rather than an analogue or surrogate?',
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
        'question': 'Were there enough replicates, run as independent reactions?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated spectra of one reaction are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
