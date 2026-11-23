"""Distribution_radio_tlc criteria: the ONE place where the grader's criteria of a radiolabelled product-distribution experiment (TLC, radio-HPLC or gel with
counting or phosphor imaging) are declared. DRAFT 2026-11-22 (class product_distribution), built from the shape of literature_spectro_direct_criteria.py.

This file is the single source for what the distribution_radio_tlc grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the recovery of the applied radioactivity, the background over the smallest
species, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_distribution_radio_tlc_converter.py. The
logic that answers each question is in literature_distribution_radio_tlc_grader.py (one short function per criterion, same order).

The only constant here is a unit conversion marked FIXED_BY_DEFINITION: a share stated as a percent is a hundredth of a fraction. Nothing else is compared.

How to read an entry in DISTRIBUTION_RADIO_TLC_CRITERIA
-------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_radio_tlc_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_radio_tlc_criteria'
FRACTION_PER_UNIT = {'fraction': 1.0, 'percent': 0.01}   # FIXED_BY_DEFINITION: a percent is a hundredth of a fraction.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_RADIO_TLC_CRITERIA = (
    {
        'id': 'species_assigned_with_standards',
        'question': 'Were the labelled spots, bands or peaks assigned to species by authentic unlabelled standards run beside them?',
        'reads': ('facts.cold_standards_co_run',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'label_retained_by_all_products',
        'question': 'Does every counted product keep the label, so that no product of the reaction is missing from the lane?',
        'reads': ('facts.label_retained_by_all_products',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'shares_of_one_lane_total',
        'question': 'Are the shares shares of the total counts of the same lane, one whole for all species?',
        'reads': ('facts.fractions_share_one_denominator',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'lane_recovery_stated',
        'question': 'How much of the applied radioactivity was found in the spots, bands or fractions of the lane (closure)?',
        'reads': ('quantities.lane_recovery',),
        'rule': 'When the recovery is given the grader records it as a fraction (lane_recovery_fraction) with its ref (lane_recovery_refs) and leaves the judgement to the sheet; otherwise unknown. A recovery is a closure, not an independent mass balance.',
        'thresholds': ('FRACTION_PER_UNIT',),
        'returns': (
            ('unknown', 'lane_recovery_recorded_for_the_sheet', 'the recovery is given: it is recorded and the sheet judges it'),
            ('unknown', 'lane_recovery_not_stated', 'the recovery is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'equal_label_per_molecule',
        'question': 'Does every counted species carry the same number of labelled atoms per molecule, so that equal counts are equal amounts?',
        'reads': ('facts.equal_label_per_molecule',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'detection_efficiency_matched',
        'question': 'Were the counts of the species corrected for differences in detection (quenching, self-absorption, imager response), or shown not to differ?',
        'reads': ('facts.detection_efficiency_matched',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'spots_resolved',
        'question': 'Were the spots, bands or peaks of neighbouring species separated from each other, so the counts of one are not counts of another?',
        'reads': ('facts.spots_resolved',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'background_beside_smallest_band',
        'question': 'Is the background of the plate or lane small against the smallest species that is quantified?',
        'reads': ('quantities.counts_background', 'quantities.smallest_species_counts', 'facts.background_subtracted'),
        'rule': 'When the background and the counts of the smallest species are both given in the same unit the grader records the background over the smallest species (background_over_smallest_species, dimensionless) with their refs (background_refs) and leaves the judgement to the sheet. Otherwise the background-subtracted fact decides: yes supported, no fails, silence unknown. The numbers come first because they say how much a missing subtraction would matter.',
        'thresholds': (),
        'returns': (
            ('unknown', 'background_recorded_for_the_sheet', 'both numbers are given in one unit: the ratio is recorded and the sheet judges it'),
            ('supported', 'background_subtracted_stated', 'the numbers are not both given in one unit and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'the numbers are not both given in one unit and the fact is no'),
            ('unknown', 'background_not_stated', 'the numbers are not both given in one unit and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'within_linear_range_of_imager',
        'question': 'Was the signal within the linear range of the detector (the imaging plate or counter not saturated)?',
        'reads': ('facts.within_linear_range_of_imager',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_blank_lane',
        'question': 'Was a lane without the enzyme, incubated like the others, run, so that impurities of the labelled substrate and its spontaneous conversion are not counted as the enzyme\'s product?',
        'reads': ('facts.no_enzyme_lane_run', 'facts.zero_time_lane_run'),
        'rule': 'A no-enzyme lane stated as run is supported (it shows both the impurities of the labelled substrate and its spontaneous change). A no-enzyme lane stated as not run, with no zero-time lane stated as run, fails. A zero-time lane alone shows only the impurities, so it never makes the criterion supported or failed: it is unknown. Silence is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'no_enzyme_lane_stated', 'the no-enzyme lane is yes'),
            ('conflicting', 'fact_answered_no', 'the no-enzyme lane is no and the zero-time lane is not yes'),
            ('unknown', 'only_zero_time_lane_stated', 'the no-enzyme lane is not yes and the zero-time lane is yes'),
            ('unknown', 'fact_unknown', 'neither lane is stated as run'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'inactive_enzyme_lane',
        'question': 'Was a lane with an inactive enzyme (heat-denatured or a catalytically dead mutant) run, so that the product is shown to need the active enzyme?',
        'reads': ('facts.inactive_enzyme_lane_run',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated lanes of one reaction are not replicates.',
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
        'question': 'Is the labelled substrate the enzyme\'s native substrate rather than a surrogate or an analogue?',
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
