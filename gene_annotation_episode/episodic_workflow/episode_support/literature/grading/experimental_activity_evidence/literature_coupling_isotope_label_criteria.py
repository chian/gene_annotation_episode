"""Coupling_isotope_label criteria: the ONE place where the grader's criteria of an isotope-label flow experiment are declared.

This file is the single source for what the coupling_isotope_label grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the isotopic purity of the label, the label atoms found against the label atoms the
reaction account expects, the label in the control against the label in the test, the replicate count), the grader records the number
with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW
constants are on the sheet side, in literature_coupling_isotope_label_converter.py. The logic that answers each question is in
literature_coupling_isotope_label_grader.py (one short function per criterion, same order). The only constant here is the exact unit scale of a
share (FRACTION_PER_UNIT, FIXED_BY_DEFINITION: a percent is a hundredth); nothing is compared.

How to read an entry in COUPLING_ISOTOPE_LABEL_CRITERIA
-------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_isotope_label_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_coupling_isotope_label_criteria'
FRACTION_PER_UNIT = {'fraction': 1.0, 'percent': 0.01}   # FIXED_BY_DEFINITION: a percent is a hundredth of a fraction.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

COUPLING_ISOTOPE_LABEL_CRITERIA = (
    {
        'id': 'unlabelled_control',
        'question': 'Was the reaction also run with the unlabelled source and its product read the same way, so that the mass shift (or the count) is shown to come from the label?',
        'reads': ('facts.unlabelled_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'back_exchange_control',
        'question': 'Was exchange of the label that does not go through the claimed reaction (the product or the substrate exchanging with the labelled water or gas by itself) tested and set aside?',
        'reads': ('facts.back_exchange_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'label_position',
        'question': 'Was the position of the label in the product determined, so that the label is shown to sit where the claimed reaction puts it?',
        'reads': ('facts.label_position_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'spontaneous_labelling_control',
        'question': 'Was the label that reaches the product without the enzyme (spontaneous exchange or chemistry) measured by a no-enzyme or an inactive-enzyme control?',
        'reads': ('facts.no_enzyme_control', 'facts.inactive_enzyme_control'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_labelling_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'control_label_level',
        'question': 'How large is the label found in the control without the enzyme (or with an inactive enzyme) against the label found in the test?',
        'reads': ('quantities.label_in_control', 'quantities.label_incorporation'),
        'rule': 'When the label in the control and the label incorporation of the test are both given the grader records the control over the test (control_over_test, dimensionless) with their refs (control_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'control_label_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'control_or_test_label_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'product_identity',
        'question': 'Was the product identified by its mass and the mass shift of the label, against an unlabelled product or standard?',
        'reads': ('facts.product_identified_by_mass_shift',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'label_purity',
        'question': 'Is the isotopic purity of the labelled source stated?',
        'reads': ('quantities.label_purity',),
        'rule': 'When the purity is given the grader records it as a fraction (label_purity_fraction) with its ref (label_purity_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'label_purity_recorded_for_the_sheet', 'the purity is given: it is recorded and the sheet judges it'),
            ('unknown', 'label_purity_not_stated', 'the purity is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'natural_abundance_correction',
        'question': 'Was the label share corrected for the natural abundance of the heavy isotope (and for the impurity of the label)?',
        'reads': ('facts.natural_abundance_corrected',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'label_stoichiometry',
        'question': 'Does the number of label atoms in a labelled product molecule agree with the number the paper\'s own reaction account puts into the product?',
        'reads': ('quantities.label_atoms_per_product', 'quantities.label_atoms_expected'),
        'rule': 'When both numbers are given the grader records the atoms found over the atoms expected (atoms_found_over_expected, dimensionless) with their refs (atoms_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'label_atoms_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'label_atoms_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'matched_runs',
        'question': 'Were the labelled and the unlabelled run made with the same enzyme preparation and over the same incubation and work-up?',
        'reads': ('facts.same_preparation', 'facts.same_window'),
        'rule': 'Both facts stated as yes is supported. Either stated as no fails. Otherwise a fact stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'both facts are yes (a not_applicable one is dropped)'),
            ('conflicting', 'fact_answered_no', 'either fact is no'),
            ('unknown', 'fact_unknown', 'none is no and a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
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
        'question': 'Was the label flow measured with the purified enzyme rather than a cell extract or lysate (where other enzymes can move the label by another route)?',
        'reads': ('facts.purified_enzyme',),
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
)
