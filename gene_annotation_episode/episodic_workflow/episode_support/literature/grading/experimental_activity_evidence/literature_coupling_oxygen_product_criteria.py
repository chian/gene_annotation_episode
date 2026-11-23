"""Coupling_oxygen_product criteria: the ONE place where the grader's criteria of an oxygen-uptake-with-product coupling experiment are declared (class
reaction_coupling; DRAFT 2026-11-22 for the owner to correct, nothing was run).

The experiment: one enzyme reaction in one vessel; the dissolved oxygen is read with an electrode or optode and the claimed product is identified and counted by
another measurement over the same interval; the result is the product made per oxygen consumed (one per O2 for CsiD/LhgO), with the oxygen that went to
hydrogen peroxide accounted for. Oxygen uptake alone can be uncoupled chemistry, so the identified product and the match of the two sides are what the criteria ask.

This file is the single source for what the coupling_oxygen_product grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a
criterion needs a number to be compared with a limit (the air-saturated oxygen value of the calibration, the drift, the oxygen uptake without the substrate, the
productive fraction against the stoichiometric bound, the lengths of the two windows, the replicate count), the grader records the number with its support refs
and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_coupling_oxygen_product_converter.py. The logic that answers each question is in literature_coupling_oxygen_product_grader.py (one short function per
criterion, same order). There is no constant here: a unit is turned into the common unit by the grader's fixed unit table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in COUPLING_OXYGEN_PRODUCT_CRITERIA
---------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_oxygen_product_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.

A supported or conflicting result always cites the quoted spans of the stated fields it rests on. No criterion rests on a plain choice (the spread kind is recorded only).
"""

VERSION = 'a105_coupling_oxygen_product_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)


def _fact_with_number(recorded_reason, number):
    """The returns of a criterion that reads one fact and one number: the fact stated as no fails; a stated number is recorded for the sheet; otherwise the fact decides."""
    return (
        ('conflicting', 'fact_answered_no', 'the fact is no'),
        ('unknown', recorded_reason, 'the ' + number + ' is given and the fact is not no: it is recorded and the sheet judges it'),
        ('supported', 'facts_answered_yes', 'no ' + number + ' is given and the fact is yes'),
        ('unknown', 'fact_unknown', 'no ' + number + ' is given and the fact is unknown'),
        ('not_applicable', 'fact_not_applicable', 'no ' + number + ' is given and the fact is not_applicable'),
    )


COUPLING_OXYGEN_PRODUCT_CRITERIA = (
    {
        'id': 'electrode_calibration',
        'question': 'Was the oxygen electrode or optode calibrated (air-saturated buffer and a zero-oxygen point), and is the air-saturated oxygen value used for it stated?',
        'reads': ('facts.electrode_calibrated', 'quantities.air_saturated_oxygen'),
        'rule': 'The calibration fact stated as no fails. When the air-saturated oxygen concentration is given the grader records it (air_saturated_uM, air_saturated_refs) and leaves the judgement to the sheet. Otherwise the fact decides: yes supported, silence unknown.',
        'thresholds': (),
        'returns': _fact_with_number('air_saturated_recorded_for_the_sheet', 'air-saturated oxygen concentration'),
    },
    {
        'id': 'oxygen_drift',
        'question': 'Was the drift of the oxygen signal measured and subtracted, and is it small against the oxygen uptake of the reaction?',
        'reads': ('facts.drift_subtracted', 'quantities.drift_percent'),
        'rule': 'The drift fact stated as no fails. When the drift is given as a percent of the uptake rate the grader records it (drift_percent, drift_refs) and leaves the judgement to the sheet. Otherwise the fact decides: yes supported, silence unknown.',
        'thresholds': (),
        'returns': _fact_with_number('drift_recorded_for_the_sheet', 'drift percent'),
    },
    {
        'id': 'no_enzyme_oxygen_control',
        'question': 'Was the spontaneous oxygen consumption or product formation (without the enzyme) measured with a no-enzyme control?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the oxygen consumption and product formation shown to depend on the active enzyme (an inactive or heat-denatured enzyme or a catalytic mutant gives neither)?',
        'reads': ('facts.inactive_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_independent_oxygen',
        'question': 'Was the oxygen that the enzyme takes up without the substrate (uncoupled or substrate-independent uptake, for example by the co-substrate or the enzyme itself) measured with a no-substrate control, and is it small against the uptake with the substrate?',
        'reads': ('facts.no_substrate_control', 'quantities.no_substrate_oxygen_percent'),
        'rule': 'The no-substrate control stated as no fails. When the uptake without the substrate is given as a percent of the uptake with it the grader records it (no_substrate_percent, no_substrate_refs) and leaves the judgement to the sheet. Otherwise the fact decides: yes supported, silence unknown.',
        'thresholds': (),
        'returns': _fact_with_number('no_substrate_recorded_for_the_sheet', 'no-substrate percent'),
    },
    {
        'id': 'peroxide_accounting',
        'question': 'Was the oxygen that went to hydrogen peroxide accounted for (a catalase test, a peroxide measurement, or a statement that none formed)?',
        'reads': ('facts.peroxide_accounted', 'quantities.peroxide_percent_of_oxygen'),
        'rule': 'The fact stated as no fails. The fact stated as yes, or a stated peroxide share of the oxygen consumed, is supported (a number that is stated shows the accounting was done; the grader also records it, peroxide_percent). Silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('supported', 'peroxide_accounting_stated', 'the fact is yes or a peroxide percent is given'),
            ('unknown', 'fact_unknown', 'the fact is unknown and no peroxide percent is given'),
            ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable and no peroxide percent is given'),
        ),
    },
    {
        'id': 'product_identity',
        'question': 'Was the product identified chemically (an authentic standard, mass spectrometry, NMR or co-elution) rather than inferred from the oxygen consumption?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_calibration',
        'question': 'Was the product quantified against a calibration (a standard series of the authentic compound)?',
        'reads': ('facts.product_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'stoichiometry',
        'question': 'Is the reaction coefficient (oxygen per product) stated, so the product per oxygen can be read as a productive fraction, and does the fraction stay within what the stoichiometry allows?',
        'reads': ('quantities.stoichiometric_coefficient', 'quantities.productive_fraction', 'quantities.stoichiometric_ratio', 'quantities.oxygen_per_product',
                  'quantities.product_formed', 'quantities.oxygen_consumed', 'quantities.product_rate', 'quantities.oxygen_rate'),
        'rule': 'No coefficient stated is unknown. When the coefficient is stated and the passage gives the coupling (stated, or exact arithmetic on stated numbers, see the grader) the grader records the productive fraction (coupling_fraction, coupling_fraction_refs) and leaves its comparison with the stoichiometric bound to the sheet. A coefficient stated with no coupling number is supported.',
        'thresholds': (),
        'returns': (
            ('unknown', 'coefficient_not_stated', 'no coefficient is given'),
            ('unknown', 'stoichiometry_recorded_for_the_sheet', 'the coefficient and a coupling number are given: the productive fraction is recorded and the sheet judges it'),
            ('supported', 'coefficient_stated', 'the coefficient is given and no coupling number is available'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'same_vessel',
        'question': 'Were the oxygen consumption and the product measured in the same reaction vessel or mixture (the product taken from the electrode chamber)?',
        'reads': ('facts.same_vessel',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'window_overlap',
        'question': 'Were the oxygen consumption and the product measured over compatible time intervals of the reaction?',
        'reads': ('facts.same_window', 'quantities.oxygen_window', 'quantities.product_window'),
        'rule': 'The same-window fact stated as no fails. When both window lengths are given the grader records the shorter over the longer (window_ratio, window_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the same-window fact is no'),
            ('unknown', 'windows_recorded_for_the_sheet', 'both window lengths are given and the fact is not no: the ratio is recorded and the sheet judges it'),
            ('supported', 'same_window_stated', 'a window length is missing and the fact is yes'),
            ('unknown', 'window_not_stated', 'a window length is missing and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'a window length is missing and the fact is not_applicable'),
        ),
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the coupling measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
