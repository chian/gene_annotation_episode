"""Distribution_chiral criteria: the ONE place where the grader's criteria of a chiral product-distribution experiment are declared (DRAFT 2026-11-22, owner to confirm).

The experiment: an enzyme makes a product with stereo-isomers (enantiomers, or diastereomers), the isomers are separated by chiral-phase chromatography or electrophoresis (or, for
diastereomers, on an ordinary column), and the enantiomeric excess (ee), the enantiomer ratio (er) or the diastereomer ratio (dr) of the product is stated. ee, er and dr are one fact in
three spellings. A racemic standard of the product, run on the same column, shows that the column separates both isomers.

This file is the single source for what the distribution_chiral grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a criterion needs a number to be
compared with a limit (the resolution between the isomer peaks, the share of the minor isomer against the detection limit, the replicate count), the grader records the number with its
support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_distribution_chiral_converter.py. The logic that answers each question is in literature_distribution_chiral_grader.py (one short function per criterion, same order).

The constants of this file are unit conversions and identities only, each FIXED_BY_DEFINITION; nothing here judges.

How to read an entry in DISTRIBUTION_CHIRAL_CRITERIA
-----------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_chiral_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.

Support rule: a criterion returns 'supported' or 'conflicting' only with support refs, the quoted source spans of the stated fields it rests on. No criterion rests on a choice
(a choice holds no span in the merged record): the configuration and the technique are kept in the record for the reviewer and judge nothing.

What the class asks of this method. The class is product_distribution: which products a reaction gives and in what proportions. For two stereo-isomers the proportion is the share of the major
isomer, f = (1 + ee) / 2, or the ratio major over minor (er, dr). For two enantiomers the detector responds equally by symmetry (an achiral detector, such as UV, cannot tell them apart), so
the response-factor question of the class is not applicable; for diastereomers the responses can differ and the passage must say they were checked. The controls decide how far the result
means that the ENZYME made it: the racemic standard (identity of both peaks), the no-enzyme control (a chemical background gives a racemate), the inactive-enzyme control and the
configurational stability of the product (a product that racemizes or epimerizes on the bench or in the buffer hides the enzyme's selectivity).
"""

VERSION = 'a105_distribution_chiral_criteria'

PERCENT_PER_FRACTION = 100.0   # FIXED_BY_DEFINITION: a percent is a hundredth.
ISOMERS_IN_A_PAIR = 2.0        # FIXED_BY_DEFINITION: ee = (major - minor) / (major + minor) for two isomers, so the major share is (1 + ee) / 2 and the minor share (1 - ee) / 2.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_CHIRAL_CRITERIA = (
    {
        'id': 'racemic_standard_run',
        'question': 'Was a racemic (or diastereomeric) standard of the product run on the same column, showing that both isomers are separated?',
        'reads': ('facts.racemic_standard_run',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'configuration_assigned_by_standard',
        'question': 'Was the configuration of the major isomer assigned by comparison with an authentic standard of known configuration?',
        'reads': ('facts.configuration_assigned_by_standard',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'isomer_response_factors',
        'question': 'Are the detector responses of the two isomers equal or calibrated, so that equal peak areas mean equal amounts?',
        'reads': ('quantities.diastereomer_ratio', 'quantities.enantiomeric_excess', 'quantities.enantiomer_ratio', 'facts.response_factors_calibrated'),
        'rule': 'A stated diastereomer ratio makes the question apply (diastereomers can respond differently): the one fact response_factors_calibrated decides (yes supported, no fails, unknown unknown). A stated enantiomeric excess or enantiomer ratio without a diastereomer ratio is not applicable (two enantiomers respond equally on an achiral detector, by symmetry). With none of the three stated the kind of isomers is not known: unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'a diastereomer ratio is stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'a diastereomer ratio is stated and the fact is no'),
            ('unknown', 'fact_unknown', 'a diastereomer ratio is stated and the fact is unknown'),
            ('not_applicable', 'isomers_are_enantiomers', 'no diastereomer ratio is stated and an enantiomeric excess or an enantiomer ratio is'),
            ('unknown', 'isomer_kind_not_stated', 'none of the three is stated'),
        ),
    },
    {
        'id': 'isomer_pair_one_measurement',
        'question': 'Is the result stated as a comparison of the two isomers measured in one analysis (an excess or a ratio of the major over the minor isomer), so that the shares have one denominator?',
        'reads': ('quantities.enantiomeric_excess', 'quantities.enantiomer_ratio', 'quantities.diastereomer_ratio'),
        'rule': 'An excess or a ratio is by its definition a comparison of two isomers over their own sum, so a stated one is supported (its spans are the support); none stated is unknown. The three spellings are one measurement and are never counted as separate results.',
        'thresholds': (),
        'returns': (
            ('supported', 'isomer_pair_stated_as_one_measurement', 'an excess or a ratio is stated'),
            ('unknown', 'no_isomer_measure_stated', 'none of the three is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'no_enzyme_control',
        'question': 'Was a reaction without the enzyme run and analysed, so that a chemical (racemic) background is shown or excluded?',
        'reads': ('facts.no_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_configurational_stability',
        'question': 'Was the product shown not to racemize or epimerize under the assay conditions and the work-up?',
        'reads': ('facts.product_configurationally_stable',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_control',
        'question': 'Was a reaction with an inactive enzyme (heat-denatured or a catalytically dead mutant) run and analysed, so that the result is the enzyme\'s?',
        'reads': ('facts.inactive_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'peak_resolution',
        'question': 'Were the peaks of the two isomers resolved well enough to read their areas apart?',
        'reads': ('quantities.peak_resolution', 'facts.isomer_peaks_baseline_resolved'),
        'rule': 'The baseline-resolved fact stated as no fails. When the resolution Rs is given the grader records it (peak_resolution, peak_resolution_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the baseline-resolved fact is no'),
            ('unknown', 'peak_resolution_recorded_for_the_sheet', 'Rs is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'isomer_peaks_baseline_resolved_stated', 'no Rs is given and the fact is yes'),
            ('unknown', 'peak_resolution_not_stated', 'no Rs is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'minor_isomer_detection',
        'question': 'Can the method see the minor isomer at the share the result claims (the minor share against the detection limit)?',
        'reads': ('quantities.minor_isomer_detection_limit', 'quantities.enantiomeric_excess', 'quantities.enantiomer_ratio', 'quantities.diastereomer_ratio'),
        'rule': 'When the detection limit and a result are given the grader records the minor isomer\'s share of the total (minor_share: (1 - ee) / 2 for an excess, 1 / (1 + ratio) for a ratio; 0 for an excess of 100 percent, where no minor isomer is seen) and the limit (detection_limit, both as fractions) with their refs (detection_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('ISOMERS_IN_A_PAIR', 'PERCENT_PER_FRACTION'),
        'returns': (
            ('unknown', 'detection_limit_recorded_for_the_sheet', 'a detection limit and a result are given: the minor share and the limit are recorded and the sheet judges them'),
            ('unknown', 'detection_limit_or_result_missing', 'the detection limit or the result is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
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
        'id': 'native_substrate',
        'question': 'Is the substrate the enzyme\'s native substrate rather than a synthetic surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the stereochemical result obtained with the purified enzyme rather than a cell extract, lysate or whole cells?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
