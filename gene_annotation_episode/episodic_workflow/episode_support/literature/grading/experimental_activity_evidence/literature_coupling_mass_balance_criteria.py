"""Coupling_mass_balance criteria: the ONE place where the grader's criteria of a mass-balance (closure) experiment are declared.

DRAFT of 2026-11-22 for the owner to correct. This file is the single source for what the coupling_mass_balance grader asks. The grader reports FACTS and holds NO
threshold that judges goodness: where a criterion needs a number to be compared with a limit (the closure, the closure of the method at zero time, the detection limit
over the substrate consumed, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_coupling_mass_balance_converter.py. The logic that
answers each question is in literature_coupling_mass_balance_grader.py (one short function per criterion, same order). There is no constant here: a unit is turned
into nM (concentrations) or nmol (amounts) and a percent into a fraction by the grader's fixed scale tables (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in COUPLING_MASS_BALANCE_CRITERIA
------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_mass_balance_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.

There is no criterion for the sheet's reporter_specificity (a mass balance has no reporter) and none for measurement_identity: those sheet criteria are not selected.
"""

VERSION = 'a105_coupling_mass_balance_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

COUPLING_MASS_BALANCE_CRITERIA = (
    {
        'id': 'product_identity',
        'question': 'Was each product identified (against an authentic standard, by its mass spectrum, or by NMR) rather than inferred?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'species_calibration',
        'question': 'Were the substrate and every quantified product calibrated with their own standards?',
        'reads': ('facts.each_species_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'method_recovery',
        'question': 'Does the method itself recover what is put in: the closure of a sample with no reaction, or an internal standard that corrects the losses of the work-up?',
        'reads': ('quantities.zero_time_closure', 'facts.internal_standard'),
        'rule': 'When the closure of the sample with no reaction is given the grader records it (zero_time_closure, as a fraction, with zero_time_refs) and leaves the judgement to the sheet. Otherwise an internal standard stated as used is supported; any other answer is unknown (external calibration without an internal standard is a usual and valid practice, so a stated no is not a failure of the recovery, it only leaves the recovery unshown).',
        'thresholds': (),
        'returns': (
            ('unknown', 'zero_time_closure_recorded_for_the_sheet', 'the closure with no reaction is given: it is recorded and the sheet judges it'),
            ('supported', 'internal_standard_stated', 'no zero-time closure is given and the internal standard fact is yes'),
            ('unknown', 'recovery_not_shown', 'no zero-time closure is given and the internal standard fact is no, unknown or not_applicable'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'minor_species_detectability',
        'question': 'Is the detection limit of the method small against the substrate consumed, so that an unquantified minor product could not hide a large part of the balance?',
        'reads': ('quantities.detection_limit', 'quantities.substrate_consumed'),
        'rule': 'When both are given in units of one kind (both concentrations or both amounts) the grader records the detection limit over the substrate consumed (detection_limit_share, dimensionless) with their refs (detection_limit_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'detection_limit_recorded_for_the_sheet', 'both are given in one kind of unit: the share is recorded and the sheet judges it'),
            ('unknown', 'detection_limit_or_consumed_missing', 'either is not given'),
            ('unknown', 'detection_limit_and_consumed_in_different_kinds_of_unit', 'one is a concentration and the other an amount, so they cannot be compared'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'blank_controls',
        'question': 'Was the spontaneous change of the substrate and the baseline of the method measured, by a sample at time zero or a control without the enzyme?',
        'reads': ('facts.zero_time_sample', 'facts.no_enzyme_control'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'blank_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'inactive_enzyme',
        'question': 'Was a control with an inactive enzyme (heat-denatured or a catalytically dead mutant) measured, so that the consumption and the products are the enzyme\'s?',
        'reads': ('facts.inactive_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_coverage',
        'question': 'Were all the products expected from the reaction quantified, so that what is not accounted for is not an unmeasured product?',
        'reads': ('facts.all_products_quantified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'volatile_loss',
        'question': 'Was the loss of a volatile or insoluble species (to the headspace, to a precipitate) excluded or checked?',
        'reads': ('facts.volatile_loss_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'reaction_equation',
        'question': 'Is the balanced reaction (the coefficients or the atom counts) on which the closure is calculated stated?',
        'reads': ('facts.reaction_equation_stated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'closure_bound',
        'question': 'Is the closure within what the stoichiometry allows: not more product than the substrate consumed can give?',
        'reads': ('quantities.closure', 'quantities.products_total', 'quantities.substrate_consumed', 'quantities.balance_residual'),
        'rule': 'The closure is the stated closure (as a fraction); when none is stated, the stated sum of the products over the substrate consumed (both in units of one kind); when that is missing too, one minus the stated residual over the substrate consumed (the residual below the substrate consumed, both in units of one kind). The grader records the closure it has (closure, closure_origin, closure_refs) and leaves the judgement to the sheet; otherwise unknown. A closure below 1 is the result of the experiment and is not judged here.',
        'thresholds': (),
        'returns': (
            ('unknown', 'closure_recorded_for_the_sheet', 'a closure is stated or can be worked out from the stated amounts: it is recorded and the sheet judges it'),
            ('unknown', 'closure_not_available', 'no closure is stated and none can be worked out'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'matched_windows',
        'question': 'Were the substrate and the products measured in the same reaction mixture and at the same time points?',
        'reads': ('facts.same_mixture', 'facts.same_window'),
        'rule': 'Any fact no fails; else any unknown is unknown; else all not_applicable is not applicable; else both yes supported.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated injections of one reaction mixture are not replicates.',
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
        'question': 'Was the reaction run with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
