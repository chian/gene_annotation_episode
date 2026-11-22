"""Transport_fluorescent_reporter criteria: the ONE place where the grader's criteria of a fluorescent-reporter transport experiment in cells are declared.

DRAFT of 2026-11-22 (owner to correct). This file is the single source for what the transport_fluorescent_reporter grader asks. The grader reports
FACTS and holds NO threshold that judges goodness: where a criterion needs a number to be compared with a limit (the Z' factor of the assay window, the
substrate series against the Km, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_transport_fluorescent_reporter_converter.py.
The logic that answers each question is in literature_transport_fluorescent_reporter_grader.py (one short function per criterion, same order). There is
no constant here: a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in TRANSPORT_FLUORESCENT_REPORTER_CRITERIA
---------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_fluorescent_reporter_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_transport_fluorescent_reporter_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

_one_fact_rule = 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.'

TRANSPORT_FLUORESCENT_REPORTER_CRITERIA = (
    {
        'id': 'control_cells',
        'question': 'Were control cells without the studied transporter (untransfected, empty vector, parent strain or knockout) measured in the same way, so that endogenous uptake and dye binding are set aside?',
        'reads': ('facts.untransfected_control_done',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'no_substrate_baseline',
        'question': 'Was a control without the substrate or fluorescent molecule (a buffer-only or vehicle addition) measured in the same way?',
        'reads': ('facts.no_substrate_control_done',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'background_fluorescence',
        'question': 'Were the background and the autofluorescence of the cells and the medium measured and subtracted?',
        'reads': ('facts.background_fluorescence_subtracted',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'signal_drift',
        'question': 'Was the drift of the signal from photobleaching or from leakage of the dye out of the cells measured or corrected?',
        'reads': ('facts.signal_drift_controlled',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'indicator_calibration',
        'question': 'Was the indicator or sensor calibrated (a standard curve, or high and low standards) so that the signal can be read as a concentration?',
        'reads': ('facts.indicator_calibrated',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'assay_window',
        'question': 'Is the signal of the cells with the transporter well separated from that of the control cells (the Z\' factor of the assay)?',
        'reads': ('quantities.z_prime_factor',),
        'rule': 'When the Z\' factor is given the grader records it (z_prime) with its ref (z_prime_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'z_prime_recorded_for_the_sheet', 'the Z\' factor is given: it is recorded and the sheet judges it'),
            ('unknown', 'z_prime_not_stated', 'the Z\' factor is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_identity',
        'question': 'Is what is read the native substrate or ion itself rather than a fluorescent analogue, a labelled derivative or a surrogate ion?',
        'reads': ('facts.analogue_is_native_substrate',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'analogue_competition',
        'question': 'Was the signal reduced by an excess of the unlabelled natural substrate, by a competitor or by a specific inhibitor, so that it is shown to go through the transporter?',
        'reads': ('facts.competitor_control_done',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'indicator_specificity',
        'question': 'Was the indicator or sensor shown to respond to the transported substrate or ion and not to others?',
        'reads': ('facts.indicator_specificity_shown',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'expression_confirmed',
        'question': 'Was the expression or the membrane insertion of the studied transporter in the cells confirmed?',
        'reads': ('facts.expression_confirmed',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'membrane_integrity',
        'question': 'Were the viability or the membrane integrity of the cells checked, so that the dye does not enter through damaged membranes?',
        'reads': ('facts.cells_intact_checked',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'linear_interval',
        'question': 'Is the signal taken from the linear or early part of its time course (an initial rate) and not from the approach to a plateau?',
        'reads': ('facts.linear_interval_shown',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_concentration_stated',
        'question': 'Is the concentration of the substrate or fluorescent molecule at which the signal was measured stated, so that the driving force is known?',
        'reads': ('quantities.substrate_concentration',),
        'rule': 'Stated is supported; not stated is unknown (a signal whose substrate concentration is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'substrate_concentration_stated', 'the concentration is given'),
            ('unknown', 'substrate_concentration_not_stated', 'the concentration is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_series',
        'question': 'Did the substrate concentrations of the concentration-response bracket the Km well enough to define it?',
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
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated wells of one preparation are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
