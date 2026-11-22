"""Distribution_gc criteria: the ONE place where the grader's criteria of a gas-chromatography product distribution are declared.

This file is the single source for what the distribution_gc grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the retention-index difference of a library match, the share of the area that
was identified, the share over the smallest integrated share, the extraction recovery, the replicate count) or a state to be weighed (raw area
percentages read from a flame-ionization detector or from a mass spectrometer), the grader records the number or the state with its support refs
and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_distribution_gc_converter.py. The logic that answers each question is in literature_distribution_gc_grader.py (one short function per
criterion, same order). The only constant here is PERCENT_PER_FRACTION, a unit conversion FIXED_BY_DEFINITION; nothing else is compared.

How to read an entry in DISTRIBUTION_GC_CRITERIA
-------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_gc_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_gc_criteria_v1'
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth; a share given in percent is turned into a fraction by this exact factor.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_GC_CRITERIA = (
    {
        'id': 'species_identification',
        'question': 'Is the product (the species whose share is stated) identified by an authentic standard, or by a library match whose retention index agrees with the published one?',
        'reads': ('facts.identified_by_standard', 'facts.identified_by_library_match', 'quantities.retention_index_observed', 'quantities.retention_index_reference'),
        'rule': 'Identified by an authentic standard stated as yes is supported. Otherwise, when a library match is stated as yes and both the observed and the reference retention index are given, the grader records the difference between them (retention_index_difference, identification_refs) and leaves the judgement to the sheet. Anything else is unknown: a missing identification is never read as no.',
        'thresholds': (),
        'returns': (
            ('supported', 'identified_by_standard', 'the authentic-standard fact is yes'),
            ('unknown', 'library_identification_recorded_for_the_sheet', 'no standard is stated as used, a library match is yes and both retention indices are given: the difference is recorded and the sheet judges it'),
            ('unknown', 'library_match_without_retention_index', 'no standard is stated as used, a library match is yes and a retention index is missing'),
            ('unknown', 'identification_not_stated', 'neither a standard nor a library match is stated as yes'),
            ('conflicting', 'never', 'never returned by the grader (the sheet judges the retention-index difference)'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'response_factors_applied',
        'question': 'Were the peak areas corrected for the response of each compound, so that the share is a share of the amount of product and not only of the detector signal?',
        'reads': ('facts.response_factors_calibrated', 'facts.quantified_by_flame_ionization', 'facts.quantified_by_mass_spectrometry'),
        'rule': 'Response factors, calibration curves or internal standards stated as yes is supported. When the paper states the shares are raw, uncorrected areas (no) and says exactly one of the two detectors gave the areas, the grader records which (uncorrected_detector, uncorrected_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'response_factors_calibrated', 'the calibration fact is yes'),
            ('unknown', 'uncorrected_areas_recorded_for_the_sheet', 'the calibration fact is no and exactly one detector fact is yes: the detector is recorded and the sheet judges it'),
            ('unknown', 'uncorrected_detector_not_stated_or_ambiguous', 'the calibration fact is no and no detector, or both, are stated as the source of the areas'),
            ('unknown', 'response_factors_not_stated', 'the calibration fact is not stated'),
            ('conflicting', 'never', 'never returned (a share from raw areas is weaker evidence, not evidence against)'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'denominator_coverage',
        'question': 'Do the shares cover all the product peaks, with no unidentified product peak left out of the total?',
        'reads': ('facts.all_peaks_in_denominator', 'quantities.identified_area_fraction'),
        'rule': 'The all-peaks fact stated as no fails. When the identified part of the total area is given the grader records it as a fraction (identified_fraction, identified_refs) and leaves the judgement to the sheet. Otherwise the all-peaks fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the all-peaks fact is no'),
            ('unknown', 'coverage_recorded_for_the_sheet', 'the identified part of the area is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'all_peaks_in_denominator_stated', 'no identified part is given and the fact is yes'),
            ('unknown', 'denominator_not_stated', 'no identified part is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'detection_limit_ratio',
        'question': 'Is the share of the product well above the smallest share the method integrated or could detect?',
        'reads': ('quantities.minimum_integrated_share', 'quantities.product_fraction'),
        'rule': 'When the smallest integrated share and the share of the product are both given the grader records the share over the limit (share_over_limit, limit_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'share_over_limit_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'limit_or_share_not_stated', 'the limit or the share is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'injector_stability',
        'question': 'Was it checked that the product is not rearranged or broken in the hot injector or on the column?',
        'reads': ('facts.injector_stability_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'extraction_recovery',
        'question': 'Was the product recovered in the extraction or sampling step, so that no product is lost more than another?',
        'reads': ('quantities.extraction_recovery',),
        'rule': 'When the recovery is given the grader records it as a fraction (recovery, recovery_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'recovery_recorded_for_the_sheet', 'the recovery is given: it is recorded and the sheet judges it'),
            ('unknown', 'recovery_not_stated', 'the recovery is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'no_enzyme_control',
        'question': 'Was a control extract without the enzyme analysed, to set aside peaks of the solvent, the plastic and the spontaneous chemistry of the substrate?',
        'reads': ('facts.no_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_stability',
        'question': 'Were the products shown to stay unchanged during the reaction, the quenching and the extraction?',
        'reads': ('facts.products_stable_under_assay_and_workup',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_control',
        'question': 'Was a control with an inactive enzyme (heat-treated, a dead mutant, or an empty-vector extract) analysed, so that the products are the enzyme\'s?',
        'reads': ('facts.inactive_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
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
        'question': 'Were the products made by the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent reactions?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated injections of one extract are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
