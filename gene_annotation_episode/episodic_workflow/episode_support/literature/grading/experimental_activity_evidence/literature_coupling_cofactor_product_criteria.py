"""Coupling_cofactor_product criteria: the ONE place where the grader's criteria of a cofactor-consumption / identified-product coupling experiment are declared.

This file is the single source for what the coupling_cofactor_product grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the highest absorbance, the recovery of the product standard, the no-substrate cofactor
rate over the test rate, the coupling value against the stoichiometric bound, the replicate count), the grader records the number with its support refs and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_coupling_cofactor_product_converter.py. The logic that answers each question is in literature_coupling_cofactor_product_grader.py (one short
function per criterion, same order). There is no constant here: an amount or rate unit is brought to its family's base unit by the record's fixed scale table
(FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in COUPLING_COFACTOR_PRODUCT_CRITERIA
-----------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_cofactor_product_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_coupling_cofactor_product_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

COUPLING_COFACTOR_PRODUCT_CRITERIA = (
    {
        'id': 'product_identified',
        'question': 'Was the product identified chemically (an authentic standard, mass spectrometry, NMR) rather than assumed from the substrate or the cofactor loss?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_calibrated',
        'question': 'Was the amount of product determined against a calibration with the authentic product (a standard series of known amounts)?',
        'reads': ('facts.product_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'extinction_coefficient_stated',
        'question': 'Is the extinction coefficient that turns the cofactor absorbance loss into an amount stated, with the wavelength it belongs to?',
        'reads': ('quantities.extinction_coefficient', 'quantities.wavelength'),
        'rule': 'Both stated is supported; either missing is unknown (a cofactor amount whose conversion constant is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'extinction_coefficient_and_wavelength_stated', 'both are given'),
            ('unknown', 'extinction_coefficient_or_wavelength_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'absorbance_range',
        'question': 'Did the absorbance of the cofactor stay in the range where the detector is linear with the concentration?',
        'reads': ('quantities.absorbance_max',),
        'rule': 'When the highest absorbance is given the grader records it (absorbance_max) with its ref (absorbance_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'absorbance_recorded_for_the_sheet', 'the highest absorbance is given: it is recorded and the sheet judges it'),
            ('unknown', 'absorbance_not_stated', 'the highest absorbance is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'calibration_recovery',
        'question': 'Does a known amount of the product come back through the product measurement (the recovery of a standard)?',
        'reads': ('quantities.calibration_recovery',),
        'rule': 'When the recovery is given the grader records it (recovery_percent) with its ref (recovery_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'recovery_recorded_for_the_sheet', 'the recovery is given: it is recorded and the sheet judges it'),
            ('unknown', 'recovery_not_stated', 'the recovery is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'coefficient_stated',
        'question': 'Is the reaction\'s own coefficient (the moles of cofactor the reaction takes per mole of product) stated, so that a ratio of product to cofactor can be turned into a productive fraction?',
        'reads': ('quantities.stoichiometric_coefficient',),
        'rule': 'Stated is supported; not stated is unknown (an unstated coefficient is not shown wrong: the ratio is then read as one product per cofactor).',
        'thresholds': (),
        'returns': (
            ('supported', 'coefficient_stated', 'the coefficient is given'),
            ('unknown', 'coefficient_not_stated', 'the coefficient is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'stoichiometric_bound',
        'question': 'Does the coupling value stay inside what the reaction\'s stoichiometry allows (no more product than the cofactor consumed can make)?',
        'reads': ('quantities.productive_fraction', 'quantities.stoichiometric_ratio', 'quantities.cofactor_per_product', 'quantities.stoichiometric_coefficient', 'quantities.cofactor_consumed',
                  'quantities.product_formed', 'quantities.cofactor_rate', 'quantities.product_rate'),
        'rule': 'The coupling value is, in this order, the stated productive fraction; the coefficient times the product per cofactor; the product per cofactor itself. The product per cofactor is, in this order, the stated ratio, the reverse of the stated cofactor per product, the product amount over the cofactor amount, the product rate over the cofactor rate (amounts and rates only inside one unit family). When a value is found the grader records it (link, link_value, link_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'link_recorded_for_the_sheet', 'a coupling value is stated or can be derived exactly: it is recorded and the sheet judges it'),
            ('unknown', 'no_coupling_value_stated', 'no coupling value is stated and none can be derived from what is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'same_enzyme_preparation',
        'question': 'Were both sides measured with the same enzyme preparation?',
        'reads': ('facts.same_preparation',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_reaction_mixture',
        'question': 'Were the cofactor consumption and the product measured in the same reaction mixture?',
        'reads': ('facts.same_mixture',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_window',
        'question': 'Do the cofactor consumption and the product refer to the same period of the reaction?',
        'reads': ('facts.same_window',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'no_substrate_oxidation',
        'question': 'Was the cofactor oxidation of the enzyme with no substrate (the uncoupled turnover) measured, and how large is it against the cofactor rate of the test?',
        'reads': ('facts.no_substrate_control', 'quantities.no_substrate_cofactor_rate', 'quantities.cofactor_rate'),
        'rule': 'The no-substrate control stated as not done fails (a fact). When the no-substrate rate and the test cofactor rate are both given in one unit family the grader records their ratio (background_over_test, background_refs) and leaves the judgement to the sheet. Otherwise the control stated as done is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the no-substrate control is stated as not done'),
            ('unknown', 'background_recorded_for_the_sheet', 'both rates are given in one family and the control is not no: the ratio is recorded and the sheet judges it'),
            ('supported', 'no_substrate_control_stated', 'the rates are not both given and the control is yes'),
            ('unknown', 'no_substrate_control_not_stated', 'the rates are not both given and the control is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'byproduct_accounted',
        'question': 'Is the cofactor that did not end in the product accounted for (a by-product such as hydrogen peroxide measured, or the uncoupled cofactor use measured)?',
        'reads': ('facts.byproduct_accounted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'spontaneous_oxidation_control',
        'question': 'Was a control without the enzyme (cofactor and substrate alone) measured?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'background_subtracted',
        'question': 'Was the background cofactor oxidation subtracted from the cofactor consumption?',
        'reads': ('facts.background_subtracted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_control',
        'question': 'Was the cofactor use and the product shown to depend on the active enzyme (a heat-denatured enzyme or a catalytically dead mutant gives neither)?',
        'reads': ('facts.inactive_enzyme_control',),
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
