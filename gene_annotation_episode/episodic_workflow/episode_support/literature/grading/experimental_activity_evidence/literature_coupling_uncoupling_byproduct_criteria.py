"""Coupling_uncoupling_byproduct criteria: the ONE place where the grader's criteria of a by-product (uncoupling) assay of a coupled reaction are declared.
DRAFT 2026-11-22 (class reaction_coupling), copied from the shape of literature_spectro_direct_criteria.py; every criterion is for the owner and an expert to correct.

This file is the single source for what the coupling_uncoupling_byproduct grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the blank as a share of the signal, the recovery of a known amount of
by-product, the share of the cofactor that went to the by-product, the replicate count), the grader records the number with its support refs and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_coupling_uncoupling_byproduct_converter.py. The logic that answers each question is in literature_coupling_uncoupling_byproduct_grader.py (one short
function per criterion, same order). The only constant here is a unit conversion marked FIXED_BY_DEFINITION; nothing else is compared.

The by-product assay is itself the reporter of this method: the criteria that guard the reporter (a catalase or superoxide-dismutase control, a check
against reductants that give a signal, the by-product not being lost in the mixture, a standard series and a recovery) ask whether the by-product
signal means what it is said to mean. The uncoupled share is judged against what the chemistry allows (one hydrogen peroxide per NAD(P)H at most), and
the productive share by difference is licensed only when the paper says the by-product accounts for all the cofactor that did not go to the product.

How to read an entry in COUPLING_UNCOUPLING_BYPRODUCT_CRITERIA
---------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_uncoupling_byproduct_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_coupling_uncoupling_byproduct_criteria'
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)
_facts_returns = (
    ('supported', 'facts_answered_yes', 'every fact is yes (a not_applicable one is set aside)'),
    ('conflicting', 'fact_answered_no', 'a fact is no'),
    ('unknown', 'fact_unknown', 'no fact is no and a fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'every fact is not_applicable'),
)

COUPLING_UNCOUPLING_BYPRODUCT_CRITERIA = (
    {
        'id': 'no_enzyme_blank',
        'question': 'Was the by-product (and the cofactor loss) measured in a blank without the enzyme, so that spontaneous reduction of oxygen by the cofactor or by the reagents is set aside?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'blank_signal_share',
        'question': 'How large is the by-product signal of the blank without the enzyme, as a share of the signal of the complete reaction?',
        'reads': ('quantities.blank_percent_of_signal',),
        'rule': 'When the share is given the grader records it (blank_percent) with its ref (blank_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'blank_share_recorded_for_the_sheet', 'the blank share is given: it is recorded and the sheet judges it'),
            ('unknown', 'blank_share_not_stated', 'the blank share is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'inactive_enzyme_control',
        'question': 'Was a control with an inactive enzyme (heat-denatured or a catalytically dead mutant) measured, so that the by-product is shown to come from the enzyme and not from free metal, free heme or a contaminant?',
        'reads': ('facts.inactive_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_dependent_turnover',
        'question': 'Were the by-product and the cofactor use also measured with the enzyme and without the substrate, so that the substrate-stimulated turnover is told from the basal turnover of the enzyme?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'byproduct_identity_control',
        'question': 'Was the by-product signal shown to be the by-product, by a catalase control (hydrogen peroxide) or a superoxide dismutase control (superoxide)?',
        'reads': ('facts.catalase_control', 'facts.sod_control'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'byproduct_identity_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'reductant_interference_excluded',
        'question': 'Was the by-product reagent checked against reaction components that give a signal by themselves (a reducing agent, the cofactor, the substrate, the test compound)?',
        'reads': ('facts.reductant_interference_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'byproduct_not_consumed',
        'question': 'Was the by-product shown not to be lost in the reaction mixture during the measurement (a peroxide degraded by the enzyme, the buffer or a contaminating catalase would be under-counted)?',
        'reads': ('facts.byproduct_not_consumed',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_series',
        'question': 'Was the by-product signal calibrated with a standard series of known amounts, made in the reaction buffer?',
        'reads': ('facts.standard_series',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_recovery',
        'question': 'Was a known amount of by-product added to the complete reaction mixture recovered?',
        'reads': ('quantities.standard_recovery',),
        'rule': 'When the recovery is given the grader records it as a fraction (recovery_fraction, percent turned into a fraction by the fixed factor) with its ref (recovery_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('PERCENT_PER_FRACTION',),
        'returns': (
            ('unknown', 'recovery_recorded_for_the_sheet', 'the recovery is given: it is recorded and the sheet judges it'),
            ('unknown', 'recovery_not_stated', 'the recovery is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'uncoupled_share',
        'question': 'What share of the consumed cofactor went to the by-product, and does the passage give it in a form that can be set against the chemistry?',
        'reads': ('quantities.uncoupled_fraction', 'quantities.byproduct_per_cofactor', 'quantities.byproduct_coefficient'),
        'rule': 'A stated uncoupled fraction is the share (percent turned into a fraction by the fixed factor). Otherwise a stated by-product per cofactor over a stated coefficient is the share (the ratio divided by the coefficient). The grader records the share (uncoupled_share, with its source, refs and supports) and leaves the judgement against what the chemistry allows to the sheet. A ratio with no coefficient and no stated fraction is unknown: a ratio is not a share without the coefficient.',
        'thresholds': ('PERCENT_PER_FRACTION',),
        'returns': (
            ('unknown', 'uncoupled_share_recorded_for_the_sheet', 'a share is stated, or a ratio and its coefficient are stated: it is recorded and the sheet judges it'),
            ('unknown', 'byproduct_coefficient_not_stated', 'only a ratio is stated, with no coefficient and no stated fraction'),
            ('unknown', 'uncoupled_share_not_stated', 'no fraction and no ratio is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'productive_share_bound',
        'question': 'Does a stated productive share of the cofactor stay within what the chemistry allows (not more product than the cofactor can give)?',
        'reads': ('quantities.productive_fraction',),
        'rule': 'When a productive fraction is stated the grader records it as a fraction (productive_share, percent turned into a fraction by the fixed factor) with its ref (productive_share_refs) and leaves the judgement against the bound to the sheet; otherwise unknown.',
        'thresholds': ('PERCENT_PER_FRACTION',),
        'returns': (
            ('unknown', 'productive_share_recorded_for_the_sheet', 'a productive fraction is stated: it is recorded and the sheet judges it'),
            ('unknown', 'productive_share_not_stated', 'no productive fraction is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'uncoupling_routes_accounted',
        'question': 'Does the passage say the by-product accounts for all the cofactor that did not go to the product, so that the productive share is the rest (by difference)?',
        'reads': ('facts.uncoupling_routes_accounted',),
        'rule': 'The one fact decides: yes supported, no fails (another loss route, such as a water-forming oxidase route, is stated), unknown unknown, not_applicable not applicable. The fact is also recorded (routes_accounted) because the sheet side derives the productive share by difference only on yes.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product of the claimed reaction identified and measured in the same experiment, so that the cofactor use is shown to be the claimed reaction and not only an uncoupled turnover?',
        'reads': ('facts.product_measured_too',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_mixture_and_window',
        'question': 'Were the cofactor use and the by-product measured in the same reaction mixture over the same time window?',
        'reads': ('facts.same_mixture', 'facts.same_window'),
        'rule': 'Both facts decide together: any no fails, else any unknown is unknown, else yes supported.',
        'thresholds': (),
        'returns': _facts_returns,
    },
    {
        'id': 'same_preparation',
        'question': 'Were the cofactor use and the by-product measured with the same enzyme preparation?',
        'reads': ('facts.same_preparation',),
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate or a non-native substrate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the coupling measured with the purified enzyme rather than a cell extract, lysate or membrane fraction?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
