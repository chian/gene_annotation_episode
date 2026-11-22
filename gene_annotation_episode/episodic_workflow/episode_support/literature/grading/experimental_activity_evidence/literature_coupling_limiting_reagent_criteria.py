"""Coupling_limiting_reagent criteria: the ONE place where the grader's criteria of a limiting-reagent endpoint experiment (a reaction run to completion with one
cofactor or co-substrate limiting; equivalents of it per product from the endpoint or a titration) are declared. DRAFT 2026-11-22, owner to correct.

This file is the single source for what the coupling_limiting_reagent grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a
criterion needs a number to be compared with a limit (the share of the limiting reagent left, the excess of the other reagent, the measured equivalents against the
paper's own coefficient, the number of titration points, the replicate count), the grader records the number with its support refs and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_coupling_limiting_reagent_converter.py.
The logic that answers each question is in literature_coupling_limiting_reagent_grader.py (one short function per criterion, same order). There is no constant here.

How to read an entry in COUPLING_LIMITING_REAGENT_CRITERIA
----------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_limiting_reagent_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_coupling_limiting_reagent_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

_facts_returns = (
    ('supported', 'facts_answered_yes', 'every fact is yes (or not_applicable)'),
    ('conflicting', 'fact_answered_no', 'a fact is no'),
    ('unknown', 'fact_unknown', 'no fact is no and a fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'every fact is not_applicable'),
)

COUPLING_LIMITING_REAGENT_CRITERIA = (
    {
        'id': 'completion_shown',
        'question': 'Was the reaction shown to run to completion, so that the limiting reagent was used up and the product at the end is the full yield from it, and how much of the limiting reagent was left?',
        'reads': ('facts.completion_shown', 'facts.limiting_reagent_consumed_fully', 'quantities.limiting_reagent_remaining'),
        'rule': 'A fact stated as no fails. When the share of the limiting reagent left is given and no fact is no, the grader records it (remaining_percent, remaining_refs) and leaves the judgement to the sheet. Otherwise either fact stated as yes is supported, and silence is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'remaining_recorded_for_the_sheet', 'the share left is given and no fact is no: it is recorded and the sheet judges it'),
            ('supported', 'completion_stated', 'no share left is given, no fact is no and a fact is yes'),
            ('unknown', 'fact_unknown', 'no share left is given, no fact is no and none is yes'),
            ('not_applicable', 'fact_not_applicable', 'no share left is given and both facts are not_applicable'),
        ),
    },
    {
        'id': 'excess_of_other_reagents',
        'question': 'Were the other reagents in excess over the limiting reagent, so that the limiting reagent really limits and the rate does not change during the run?',
        'reads': ('facts.other_reagents_in_excess', 'quantities.excess_over_limiting'),
        'rule': 'The fact stated as no fails. When the fold of excess is given and the fact is not no, the grader records it (excess_fold, excess_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'excess_recorded_for_the_sheet', 'the fold is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'excess_stated', 'no fold is given and the fact is yes'),
            ('unknown', 'excess_not_stated', 'no fold is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'no_regeneration',
        'question': 'Was the limiting reagent kept from being regenerated during the reaction (no regeneration system), so that its amount is the amount added?',
        'reads': ('facts.no_regeneration',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'limiting_amount_verified',
        'question': 'Was the amount of limiting reagent that was added checked by a measurement rather than taken from the weighed amount?',
        'reads': ('facts.limiting_amount_verified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'reaction_coefficient',
        'question': 'Does the paper state the reaction\'s own coefficient (equivalents of the limiting reagent per product), and does the measured number agree with it?',
        'reads': ('quantities.stoichiometric_coefficient', 'quantities.limiting_reagent_per_product'),
        'rule': 'No coefficient stated is unknown. A coefficient and a measured equivalents per product both stated: the grader records the measured over the stated (equivalents_over_coefficient) with its refs (equivalents_refs) and leaves the judgement to the sheet. A coefficient stated and no measured number is supported (the paper gives its reaction account).',
        'thresholds': (),
        'returns': (
            ('unknown', 'equivalents_recorded_for_the_sheet', 'the coefficient and the measured equivalents per product are given: the ratio is recorded and the sheet judges it'),
            ('supported', 'coefficient_stated', 'the coefficient is given and no measured number is'),
            ('unknown', 'coefficient_not_stated', 'the coefficient is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'product_identity',
        'question': 'Was the product chemically identified (against an authentic standard, by mass or NMR) rather than inferred from the loss of the substrate or the cofactor?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_calibration',
        'question': 'Was the product measured against a standard of known amounts?',
        'reads': ('facts.product_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_reaction',
        'question': 'Were the product and the limiting reagent taken from the same reaction mixture at the same end of the reaction?',
        'reads': ('facts.same_mixture', 'facts.same_endpoint'),
        'rule': 'Any fact no fails; else any fact unknown is unknown; else all not_applicable is not applicable; else supported.',
        'thresholds': (),
        'returns': _facts_returns,
    },
    {
        'id': 'no_enzyme_control',
        'question': 'Was a reaction without the enzyme measured, so that loss of the limiting reagent or formation of the product without the enzyme is shown to be absent or small?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'no_substrate_control',
        'question': 'Was a reaction with the enzyme and the limiting reagent but without the substrate measured, so that use of the limiting reagent by something other than the claimed reaction (an oxidase side activity) is shown to be absent or small?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_control',
        'question': 'Was a reaction with an inactive enzyme (heat-denatured or a catalytically dead mutant) measured, so that the product is attributed to the enzyme?',
        'reads': ('facts.inactive_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'titration_points',
        'question': 'If the limiting reagent was titrated in steps, were there enough points to show the rise to the break and the plateau?',
        'reads': ('quantities.titration_points',),
        'rule': 'When the number of points is given the grader records it (titration_points, titration_refs) and leaves the judgement to the sheet; otherwise unknown (a single dose is not a titration and is not penalised).',
        'thresholds': (),
        'returns': (
            ('unknown', 'titration_points_recorded_for_the_sheet', 'the number of points is given: it is recorded and the sheet judges it'),
            ('unknown', 'titration_points_not_stated', 'the number of points is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated measurements of one reaction mixture are not replicates.',
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
        'question': 'Are the substrate and the cofactor the enzyme\'s native ones rather than surrogates?',
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
