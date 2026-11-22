"""Distribution_hplc criteria: the ONE place where the grader's criteria of an HPLC product-distribution experiment are declared.

This file is the single source for what the distribution_hplc grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the peak resolution, the total recovery, the detection limit against the
stated share, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_distribution_hplc_converter.py. The
logic that answers each question is in literature_distribution_hplc_grader.py (one short function per criterion, same order). There is no constant
here: a percent is turned into a fraction by the fixed factor 0.01 (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in DISTRIBUTION_HPLC_CRITERIA
---------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_hplc_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_hplc_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_HPLC_CRITERIA = (
    {
        'id': 'species_assigned_with_standards',
        'question': 'Are the species whose shares are given identified (an authentic standard by retention time or spiking, or confirmation of the product peak by mass or NMR) rather than assigned by retention time alone?',
        'reads': ('facts.authentic_standard_for_each_species', 'facts.identity_confirmed_by_mass_or_nmr'),
        'rule': 'Either fact stated as done is enough. If neither is stated as done and one is stated as not done, it fails. Identity stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'species_assignment_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'response_factors_calibrated',
        'question': 'Is the detector response of each species calibrated (response factors or a calibration curve per species), so that a peak-area share is an amount share?',
        'reads': ('facts.response_factors_calibrated', 'facts.calibration_curves_for_each_species'),
        'rule': 'Either fact stated as done is enough. If neither is stated as done and one is stated as not done (areas used uncorrected, or equal response assumed), it fails: a UV area percent is a molar percent only when the species respond equally. Calibration stated nowhere is unknown.',
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
        'question': 'Do the shares given sit over one defined total with every peak accounted for, and does the total recovery show that no material is missing?',
        'reads': ('facts.fractions_share_one_denominator', 'facts.all_products_identified', 'quantities.total_recovery'),
        'rule': 'Either fact stated as no fails. When the total recovery is stated and neither fact is no, the grader records it (total_recovery as a fraction, closure_refs, denominator_status) and leaves the judgement to the sheet. Otherwise the two facts decide: both yes supported, a fact unknown unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'a denominator fact is no'),
            ('unknown', 'closure_recorded_for_the_sheet', 'the total recovery is given and no fact is no: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'no recovery is given and both facts are yes'),
            ('unknown', 'fact_unknown', 'no recovery is given and a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no recovery is given and both facts are not_applicable'),
        ),
    },
    {
        'id': 'peak_resolution_recorded',
        'question': 'Are the product peaks separated from their neighbours well enough that their areas are not shared?',
        'reads': ('quantities.peak_resolution', 'facts.peaks_resolved'),
        'rule': 'The peaks-resolved fact stated as no fails. When the resolution Rs is given the grader records it (peak_resolution, resolution_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the peaks-resolved fact is no'),
            ('unknown', 'resolution_recorded_for_the_sheet', 'the resolution is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'peaks_resolved_stated', 'no resolution is given and the fact is yes'),
            ('unknown', 'resolution_not_stated', 'no resolution is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reaction_stopped_before_injection',
        'question': 'Was the reaction stopped (quenched, or the enzyme removed) before the sample was injected, so that the distribution is the one at the stated time?',
        'reads': ('facts.enzyme_removed_or_quenched_before_injection',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'calibration_range_covers_signals',
        'question': 'Do the calibration and the detection limit apply to the share that was measured (the signal lies inside the calibration range and well above the detection limit; for a product reported as not detected, the detection limit is low)?',
        'reads': ('facts.signals_within_calibration_range', 'quantities.detection_limit', 'quantities.product_fraction', 'quantities.equilibrium_fraction', 'facts.claimed_product_detected'),
        'rule': 'The in-range fact stated as no fails. When the detection limit is given together with a stated share (the product share, else the equilibrium share), or with a product stated as not detected, the grader records the limit and the share (detection_limit, limit_share, limit_refs; limit_share is None for a stated non-detection) and leaves the judgement to the sheet. Otherwise the in-range fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the in-range fact is no'),
            ('unknown', 'detection_limit_recorded_for_the_sheet', 'the limit is given with a stated share or a stated non-detection and the fact is not no: they are recorded and the sheet judges them'),
            ('supported', 'signals_within_range_stated', 'no limit can be compared and the fact is yes'),
            ('unknown', 'calibration_range_not_stated', 'no limit can be compared and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'no_enzyme_injection',
        'question': 'Was a reaction without the enzyme analysed in the same way, so that spontaneous products and impurities of the substrate are known?',
        'reads': ('facts.no_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'products_stable_through_workup',
        'question': 'Were the products shown not to interconvert or degrade under the assay conditions and during the work-up, so that the distribution is the enzyme\'s and not the work-up\'s?',
        'reads': ('facts.products_stable_under_assay_and_workup',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_injection',
        'question': 'Was a reaction with an inactive enzyme (heat-denatured or a catalytic mutant) analysed in the same way, so that the products are the studied enzyme\'s and not a contaminant\'s?',
        'reads': ('facts.inactive_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'equilibrium_evidence',
        'question': 'Does the composition stay the same over time, or is it reached from both the substrate and the product side, so that it is an equilibrium and not a single end point?',
        'reads': ('facts.distribution_stable_over_time', 'facts.approached_from_both_sides', 'quantities.equilibrium_fraction', 'quantities.equilibrium_ratio'),
        'rule': 'Either fact stated as done is enough. If neither is done and one is stated as not done, it fails. With no fact stated, the criterion is unknown when an equilibrium share or ratio is stated and not applicable when none is (a product share of a reaction stopped early has no equilibrium to establish).',
        'thresholds': (),
        'returns': (
            ('supported', 'equilibrium_evidence_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'equilibrium_evidence_not_stated', 'no fact is stated and an equilibrium share or ratio is stated'),
            ('not_applicable', 'no_equilibrium_result_stated', 'no fact is stated and no equilibrium share or ratio is stated'),
        ),
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
        'question': 'Was the distribution measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
