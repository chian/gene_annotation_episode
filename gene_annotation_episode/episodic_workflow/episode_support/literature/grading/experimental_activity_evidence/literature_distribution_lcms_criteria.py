"""Distribution_lcms criteria: the ONE place where the grader's criteria of an LC-MS or LC-MS/MS product-profile experiment are declared.

DRAFT 2026-11-22 (owner to confirm). This file is the single source for what the distribution_lcms grader asks. The grader reports FACTS and holds NO threshold that
judges goodness: where a criterion needs a number to be compared with a limit (the product concentration over the limit of quantification, the replicate count), the
grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are
on the sheet side, in literature_distribution_lcms_converter.py. The logic that answers each question is in literature_distribution_lcms_grader.py (one short function per
criterion, same order). There is no constant here: a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

What the method is, so the questions read right. An ion signal is not a molar amount: the share of a product among the products is quantitative only when each species is
calibrated on its own (an authentic standard with its own curve, or an isotope-labelled internal standard of the species), and ion suppression by the matrix changes the signal
again. The criteria therefore ask: are the species assigned with standards, is the response calibrated per species, do the shares share one denominator, is the matrix effect
and the sample handling addressed, do the signals lie in the calibrated range, and are there the controls (no enzyme, inactive enzyme) and the replicates.

How to read an entry in DISTRIBUTION_LCMS_CRITERIA
--------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_lcms_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_lcms_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_LCMS_CRITERIA = (
    {
        'id': 'species_assigned_with_standards',
        'question': 'Were the species whose shares are given identified (and quantified) against authentic standards, matched by retention time and by mass or fragment ions?',
        'reads': ('facts.authentic_standard_for_each_species',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'calibration_per_species',
        'question': 'Is the response of each species calibrated on its own (a calibration curve or response factor per species, or an isotope-labelled internal standard), so that an ion-signal share is an amount share?',
        'reads': ('facts.calibrated_per_species', 'facts.isotope_labelled_internal_standard'),
        'rule': 'Either fact stated as yes is enough (they are two ways to the same end). If neither is yes and one is no, it fails. A calibration stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'response_calibration_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'shared_denominator_and_closure',
        'question': 'Do the shares share one stated denominator, with every product identified so that no unassigned peak is left out of the total?',
        'reads': ('facts.fractions_share_one_denominator', 'facts.all_products_identified'),
        'rule': 'Both facts decide: any no fails; else any unknown is unknown; else both not_applicable is not applicable; else supported. The total recovery, when stated, is recorded (it is the sheet\'s recovery role) and is not judged: a share normalised to 100 percent can sum to 100 while the recovery is unknown, and a closure is not an independent mass balance.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'matrix_effect_addressed',
        'question': 'Was the matrix effect (ion suppression or enhancement) addressed: evaluated, or avoided by calibrating in the same matrix as the samples?',
        'reads': ('facts.ion_suppression_checked', 'facts.matrix_matched_calibration'),
        'rule': 'Either fact stated as yes is enough (two ways to the same end). If neither is yes and one is no, it fails. A matrix effect stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'matrix_effect_addressed_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'sample_handling',
        'question': 'Was the reaction stopped before the analysis, and were the products stable through the reaction, the work-up and the wait in the autosampler, so that the profile read is the profile of the stated time?',
        'reads': ('facts.enzyme_removed_or_quenched_before_analysis', 'facts.products_stable_under_assay_and_workup'),
        'rule': 'The two are independent safeguards: any fact stated as no fails; else any fact stated as yes is supported; else unknown (or not applicable when both are not_applicable).',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('supported', 'facts_answered_yes', 'no fact is no and a fact is yes'),
            ('unknown', 'fact_unknown', 'no fact is yes or no and a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'calibration_range_covers_signals',
        'question': 'Do the measured signals lie within the calibrated range, with the product well above the limit of quantification?',
        'reads': ('facts.signals_within_calibration_range', 'quantities.product_concentration', 'quantities.limit_of_quantification'),
        'rule': 'The fact stated as no fails. When the product concentration and the limit of quantification are both given and the fact is not no, the grader records the concentration over the limit (product_over_loq, dimensionless) with their refs (loq_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the calibration-range fact is no'),
            ('unknown', 'concentration_over_limit_recorded_for_the_sheet', 'both numbers are given and the fact is not no: the ratio is recorded and the sheet judges it'),
            ('supported', 'signals_within_calibration_range_stated', 'the numbers are not both given and the fact is yes'),
            ('unknown', 'calibration_range_not_stated', 'the numbers are not both given and the fact is not stated'),
            ('not_applicable', 'fact_not_applicable', 'the numbers are not both given and the fact is not_applicable'),
        ),
    },
    {
        'id': 'no_enzyme_reaction',
        'question': 'Was a reaction without the enzyme run and analysed by the same method, so that spontaneous products and contaminant ions are set aside?',
        'reads': ('facts.no_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_reaction',
        'question': 'Was a reaction with an inactive enzyme (heat-denatured or a catalytic mutant) run and analysed by the same method, so that the products are shown to come from this enzyme?',
        'reads': ('facts.inactive_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent reactions?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated injections of one sample are not replicates.',
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
        'question': 'Was the product profile made by the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
