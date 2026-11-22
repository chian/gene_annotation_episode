"""Coupling_electron_balance criteria: the ONE place where the grader's criteria of an electron balance of a reaction are declared.

This file is the single source for what the coupling_electron_balance grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the background share of the electrons delivered, the electron recovery
against what is physically possible, the recovery of a product standard, the replicate count), the grader records the number with its support
refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet
side, in literature_coupling_electron_balance_converter.py. The logic that answers each question is in
literature_coupling_electron_balance_grader.py (one short function per criterion, same order).

The only constants here are unit conversions marked FIXED_BY_DEFINITION: a percent is a hundredth, and an amount of electrons is turned into umol
(a charge by the Faraday constant, which is exact since the 2019 redefinition of the SI, to the digits given), so that the two sides can be set
beside each other. Nothing here is compared with a limit.

How to read an entry in COUPLING_ELECTRON_BALANCE_CRITERIA
----------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_electron_balance_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_coupling_electron_balance_criteria_v1'

PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
FARADAY_C_PER_MOL = 96485.33212  # FIXED_BY_DEFINITION: the Faraday constant (elementary charge times the Avogadro constant, both exact since 2019), coulomb per mole of electrons.
UMOL_PER_UNIT = {'mol': 1.0e6, 'mmol': 1.0e3, 'umol': 1.0, 'nmol': 1.0e-3, 'pmol': 1.0e-6,   # FIXED_BY_DEFINITION: the SI prefixes
                 'C': 1.0e6 / FARADAY_C_PER_MOL, 'mC': 1.0e3 / FARADAY_C_PER_MOL}            # FIXED_BY_DEFINITION: a charge in coulomb is Q / F mol of electrons

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

COUPLING_ELECTRON_BALANCE_CRITERIA = (
    {
        'id': 'no_enzyme_control',
        'question': 'Was a control without the enzyme or catalyst run, so that electrons going to the product by chemistry or by the electrode alone can be seen?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'background_electrons',
        'question': 'Was the background (the charge or donor oxidation without the enzyme) measured and set against the electrons delivered, and subtracted?',
        'reads': ('quantities.background_electrons', 'quantities.electrons_delivered', 'facts.background_charge_subtracted'),
        'rule': 'The background-subtracted fact stated as no fails. When the background and the electrons delivered are both given the grader records the background over the electrons delivered (background_share, dimensionless, both in umol) with their refs (background_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the background-subtracted fact is no'),
            ('unknown', 'background_recorded_for_the_sheet', 'both amounts are given and the fact is not no: the share is recorded and the sheet judges it'),
            ('supported', 'background_charge_subtracted_stated', 'the amounts are not both given and the fact is yes'),
            ('unknown', 'background_not_stated', 'the amounts are not both given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'inactive_enzyme_control',
        'question': 'Was a control with an inactive enzyme run, so that the electron flow into the product is shown to need the active enzyme?',
        'reads': ('facts.inactive_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product chemically identified against an authentic standard rather than inferred from the loss of the donor?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'electrons_per_product_stated',
        'question': 'Is the number of electrons one product molecule takes stated for the reaction?',
        'reads': ('quantities.electrons_per_product',),
        'rule': 'Stated is supported; not stated is unknown (an electron count that is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'electrons_per_product_stated', 'the number is given'),
            ('unknown', 'electrons_per_product_not_stated', 'the number is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'electron_closure',
        'question': 'Does the share of the delivered electrons recovered in the product stay within what is physically possible?',
        'reads': ('quantities.productive_fraction', 'quantities.electrons_delivered', 'quantities.product_formed', 'quantities.electrons_per_product'),
        'rule': 'The share is the stated productive fraction (percent turned into a fraction), or else the electrons per product times the product formed over the electrons delivered (both in umol), when those three are stated. The grader records the share (recovery_fraction), whether it was stated or worked out (recovery_origin), its weakest support (recovery_support) and its refs (recovery_refs) and leaves the judgement to the sheet; with no share it is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'closure_recorded_for_the_sheet', 'a share is stated or can be worked out: it is recorded and the sheet judges it'),
            ('unknown', 'closure_not_stated', 'no share is stated and the three amounts are not all given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'both_sides_stated',
        'question': 'Are the electrons delivered and the product formed both stated as amounts with their units, so the two sides of the balance can be read?',
        'reads': ('quantities.electrons_delivered', 'quantities.product_formed'),
        'rule': 'Both stated is supported; either missing is unknown (a balance stated only as a percent is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'both_amounts_stated', 'both amounts are given'),
            ('unknown', 'an_amount_not_stated', 'either amount is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'delivery_calibration',
        'question': 'Was the counting of the electrons delivered calibrated (standardised titrant, calibrated coulometer, determined donor concentration)?',
        'reads': ('facts.delivery_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_calibration',
        'question': 'Was the measurement of the product calibrated with a standard (a gas standard series, a standard curve)?',
        'reads': ('facts.product_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_recovery',
        'question': 'Did a known standard of the product put through the measurement give back what was put in?',
        'reads': ('quantities.standard_recovery',),
        'rule': 'When the recovery is given the grader records it (standard_recovery_fraction, percent turned into a fraction) with its ref (standard_recovery_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'standard_recovery_recorded_for_the_sheet', 'the recovery is given: it is recorded and the sheet judges it'),
            ('unknown', 'standard_recovery_not_stated', 'the recovery is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'headspace_accounting',
        'question': 'Were the product in the gas phase and the dissolved product both accounted for (the loss on sampling the headspace corrected)?',
        'reads': ('facts.headspace_accounted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'oxygen_excluded',
        'question': 'Was the reaction kept free of oxygen or another electron acceptor that could take the electrons instead of the product?',
        'reads': ('facts.anaerobic_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'mediator_bypass',
        'question': 'Was a path excluded that moves electrons to the product without the enzyme (the mediator dye alone, the electrode alone)?',
        'reads': ('facts.mediator_bypass_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'matched_windows',
        'question': 'Were the electrons delivered and the product measured over the same interval, in the same vessel and from the same preparation?',
        'reads': ('facts.same_window', 'facts.same_reaction_mixture'),
        'rule': 'Both facts yes is supported; any fact no fails; otherwise any fact unknown is unknown.',
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
        'id': 'native_electron_carrier',
        'question': 'Is the electron donor or carrier the natural one of the enzyme rather than an artificial dye, chemical reductant or electrode?',
        'reads': ('facts.native_electron_carrier',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the balance measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
