"""Transport_medium_analysis criteria: the ONE place where the grader's criteria of a medium-analysis transport experiment are declared.

DRAFT 2026-11-22 (owner to correct). This file is the single source for what the transport_medium_analysis grader asks. The experiment: cells
take up or release an UNLABELLED substrate and the substrate in the medium (or in cells separated from it) is measured at stated times by HPLC,
LC-MS, an enzymatic analyzer or ion analysis; the result is a rate or an amount over an INTERVAL, the balance of export, re-uptake, lysis and
metabolism, and not an initial rate unless the time course shows it.

The grader reports FACTS and holds NO threshold that judges goodness: where a criterion needs a number to be compared with a limit (the share of
the substrate moved over the interval, the number of sampling times, the separation delay over the interval, the replicate count), the grader
records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its
EXPERT_REVIEW constants are on the sheet side, in literature_transport_medium_analysis_converter.py. The logic that answers each question is in
literature_transport_medium_analysis_grader.py (one short function per criterion, same order). The only constant here is a unit conversion
(FIXED_BY_DEFINITION): a time given in s, min or h is turned into seconds so that the delay can be divided by the interval.

How to read an entry in TRANSPORT_MEDIUM_ANALYSIS_CRITERIA
----------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_medium_analysis_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (only the fixed unit conversion; the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_transport_medium_analysis_criteria_v1'
SECONDS_PER_TIME_UNIT = {'s': 1.0, 'min': 60.0, 'h': 3600.0}   # FIXED_BY_DEFINITION: a minute is 60 s, an hour 3600 s.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

TRANSPORT_MEDIUM_ANALYSIS_CRITERIA = (
    {
        'id': 'cell_free_control',
        'question': 'Was the loss or gain of the substrate by itself (chemical instability, sticking to the tube or filter) measured and set aside by a cell-free blank taken through the same handling?',
        'reads': ('facts.cell_free_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'zero_time_sample',
        'question': 'Was the starting amount of the substrate measured in a sample taken at time zero?',
        'reads': ('facts.zero_time_sample_taken',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'control_strain',
        'question': 'Were cells without the transporter (an empty vector, the parent or a deletion strain) measured beside the cells that carry it, so that the host\'s own transport and metabolism are set aside?',
        'reads': ('facts.empty_vector_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'expression_confirmed',
        'question': 'Was the expression or membrane insertion of the transporter in the cells confirmed?',
        'reads': ('facts.expression_confirmed',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'calibration_in_medium',
        'question': 'Was the analysis calibrated with standards of the substrate prepared in the same medium as the samples?',
        'reads': ('facts.calibration_in_medium',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'internal_standard',
        'question': 'Was an internal standard added to the samples, so that losses in handling and matrix effects on the signal (ion suppression, derivatization yield) are corrected?',
        'reads': ('facts.internal_standard_used',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the time course where little of the substrate has been moved?',
        'reads': ('quantities.substrate_moved_percent', 'facts.linear_time_course'),
        'rule': 'A linear-time-course fact stated as no fails. When the share of the substrate moved is given the grader records it (moved_percent, moved_refs) and leaves the judgement to the sheet. Otherwise the linear-time-course fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-time-course fact is no'),
            ('unknown', 'moved_recorded_for_the_sheet', 'the share moved is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_time_course_stated', 'no share moved is given and the fact is yes'),
            ('unknown', 'rate_regime_not_stated', 'no share moved is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'time_points',
        'question': 'Were there enough sampling times to define a slope (two times give only an interval average, not an initial rate)?',
        'reads': ('sampling_times', 'facts.zero_time_sample_taken'),
        'rule': 'When the sampling times are given the grader records how many distinct times there are (time_point_count) and whether a zero-time sample was taken (zero_time_sample), with their refs (time_points_refs), and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'time_points_recorded_for_the_sheet', 'the sampling times are given: the count is recorded and the sheet judges it'),
            ('unknown', 'sampling_times_not_stated', 'the sampling times are not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'separation_timing',
        'question': 'Were the cells separated from the medium, or the reaction stopped, at the time of sampling, so that the measured interval is the stated one?',
        'reads': ('quantities.separation_delay', 'quantities.interval', 'facts.immediate_separation'),
        'rule': 'An immediate-separation fact stated as no fails. When the delay and the interval are both given the grader records the delay over the interval (separation_delay_over_interval, dimensionless, both turned into seconds) with its refs (separation_refs) and leaves the judgement to the sheet. Otherwise the immediate-separation fact stated as yes is supported, and silence is unknown.',
        'thresholds': ('SECONDS_PER_TIME_UNIT',),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the immediate-separation fact is no'),
            ('unknown', 'separation_recorded_for_the_sheet', 'the delay and the interval are given and the fact is not no: the ratio is recorded and the sheet judges it'),
            ('supported', 'immediate_separation_stated', 'the delay and the interval are not both given and the fact is yes'),
            ('unknown', 'separation_not_stated', 'the delay and the interval are not both given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_identity',
        'question': 'Was the substance that was measured identified as the substrate itself (an authentic standard, retention time and mass, or a substrate-specific enzyme)?',
        'reads': ('facts.substrate_identity_confirmed',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'metabolism_excluded',
        'question': 'Was consumption or conversion of the substrate inside the cells excluded or measured, so that a loss from the medium is not metabolism and a gain in the medium is not a product?',
        'reads': ('facts.substrate_metabolism_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'reuptake_excluded',
        'question': 'Was re-uptake of the released substrate excluded or accounted for (an appearance in the medium is export minus re-uptake)?',
        'reads': ('facts.reuptake_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'lysis_excluded',
        'question': 'Was leakage or lysis of the cells excluded (a lysed cell releases its content into the medium and looks like export)?',
        'reads': ('facts.lysis_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'energy_source',
        'question': 'Were the cells given the energy source or driving gradient the transport needs?',
        'reads': ('facts.energy_source_provided',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'native_substrate',
        'question': 'Is the measured substrate the transporter\'s native substrate rather than an analogue?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated measurements of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
