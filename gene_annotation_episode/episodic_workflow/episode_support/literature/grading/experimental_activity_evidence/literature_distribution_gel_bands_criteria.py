"""Distribution_gel_bands criteria: the ONE place where the grader's criteria of an electrophoretic product-distribution experiment are declared (DRAFT 2026-11-22, owner to correct).

This file is the single source for what the distribution_gel_bands grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a criterion needs
a number to be compared with a limit (the share of the claimed product over the stated detection limit, the share of the lane the counted bands account for, the share of
the substrate converted, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet';
the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_distribution_gel_bands_converter.py. The logic that answers each question is in
literature_distribution_gel_bands_grader.py (one short function per criterion, same order). The only constant here is the unit conversion of a share, FIXED_BY_DEFINITION.

How to read an entry in DISTRIBUTION_GEL_BANDS_CRITERIA
-------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_gel_bands_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_gel_bands_criteria'
# FIXED_BY_DEFINITION: a percent is a hundredth of a fraction. The only number of this declaration; it only changes the spelling of a stated share.
FRACTION_PER_UNIT = {'fraction': 1.0, 'percent': 0.01}

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_GEL_BANDS_CRITERIA = (
    {
        'id': 'size_markers',
        'question': 'Was a size marker, ladder or sequencing ladder run beside the products, so that each band or peak is assigned to a length or a cleavage site?',
        'reads': ('facts.size_markers_run',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'band_resolution',
        'question': 'Were the bands or peaks of the products resolved from their neighbours, so that each can be read as its own species?',
        'reads': ('facts.bands_resolved',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'equal_response',
        'question': 'Does a molecule of each product give the same signal (one end label per molecule), or were the band signals corrected for the different response of different fragments?',
        'reads': ('facts.end_labelled_so_equal_response', 'facts.response_corrected_for_length'),
        'rule': 'Either fact stated as yes is enough. If neither is stated as yes and one is stated as no, it fails (for example a length-dependent stain that was not corrected). Silence in both is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'equal_response_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'denominator_coverage',
        'question': 'Does the total the shares are taken of cover every product band or peak of the lane?',
        'reads': ('facts.all_bands_in_denominator',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'linear_range',
        'question': 'Were the band signals within the linear range of the stain, the label or the imager?',
        'reads': ('facts.within_linear_range',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'minor_band_limit',
        'question': 'Is the share of the claimed product well above the smallest share the gel is stated to detect?',
        'reads': ('quantities.product_fraction', 'quantities.minor_species_detection_limit'),
        'rule': 'When the share of the claimed product and the stated detection limit are both given, the grader records the share over the limit (share_over_detection_limit, dimensionless) with their refs (limit_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'limit_recorded_for_the_sheet', 'the share and the limit are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'share_or_limit_missing', 'the share or the limit is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'lane_signal_accounted',
        'question': 'Do the counted bands account for the signal of the lane (or of the input), so that signal lost in the well, in a smear or off the gel does not hide products?',
        'reads': ('quantities.total_recovery',),
        'rule': 'When the recovery is given the grader records it as a fraction (recovery_fraction) with its ref (recovery_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'recovery_recorded_for_the_sheet', 'the recovery is given: it is recorded and the sheet judges it'),
            ('unknown', 'recovery_not_stated', 'the recovery is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reaction_quenched',
        'question': 'Was the reaction stopped before the products were loaded, so that the distribution is the one of the stated reaction and not of the wait?',
        'reads': ('facts.reaction_quenched_before_loading',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'background_subtraction',
        'question': 'Was the background of the lane or of the gel subtracted from the band signals?',
        'reads': ('facts.background_subtracted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'background_lane',
        'question': 'Was the substrate incubated without the enzyme, or run alone, so that what the substrate preparation or a spontaneous cleavage contributes is set aside?',
        'reads': ('facts.no_enzyme_lane', 'facts.substrate_only_lane'),
        'rule': 'Either lane stated as run is enough. If neither is stated as run and one is stated as not run, it fails. A lane stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'background_lane_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'inactive_enzyme_lane',
        'question': 'Was a reaction with an inactive enzyme (heat-denatured or a catalytically dead mutant) run beside the reaction, so that the products are attributed to the enzyme\'s catalysis?',
        'reads': ('facts.inactive_enzyme_lane',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'single_hit_regime',
        'question': 'Does the distribution show the primary products of one cut per molecule, not products of a second cut: was little of the substrate converted?',
        'reads': ('quantities.substrate_conversion', 'facts.primary_products_only'),
        'rule': 'A primary-products fact stated as no fails. When the share of the substrate converted is given the grader records it as a fraction (conversion_fraction, conversion_refs) and leaves the judgement to the sheet. Otherwise the primary-products fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the primary-products fact is no'),
            ('unknown', 'conversion_recorded_for_the_sheet', 'the conversion is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'primary_products_stated', 'no conversion is given and the fact is yes'),
            ('unknown', 'single_hit_not_stated', 'no conversion is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent reactions?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Lanes of one gel loaded from one reaction are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a synthetic model substrate?',
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
