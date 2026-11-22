"""Distribution_enzymatic_endpoint criteria: the ONE place where the grader's criteria of an enzymatic end-point determination of a product mixture are declared.

This file is the single source for what the distribution_enzymatic_endpoint grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the cross-reactivity of an analysis enzyme, the highest absorbance of the reporter,
the recovery of the analyses, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_distribution_enzymatic_endpoint_converter.py.
The logic that answers each question is in literature_distribution_enzymatic_endpoint_grader.py (one short function per criterion, same order). There is
no constant here: a percent is turned into a fraction or the reverse by a fixed definition in the grader, and nothing else is compared.

How to read an entry in DISTRIBUTION_ENZYMATIC_ENDPOINT_CRITERIA
-----------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_enzymatic_endpoint_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_enzymatic_endpoint_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_ENZYMATIC_ENDPOINT_CRITERIA = (
    {
        'id': 'analysis_enzyme_specificity',
        'question': 'Was the analysis enzyme of each species shown to read that species only, by testing it with the other pure species of the mixture?',
        'reads': ('facts.analysis_enzyme_specificity_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'standard_curve_per_species',
        'question': 'Was each species determined against its own standards, run with the same analysis enzyme, so that its amount is in molar units?',
        'reads': ('facts.standard_curve_for_each_species',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'denominator_and_coverage',
        'question': 'Do the shares share one defined total, and does every species of the mixture have its own analysis, so that none is missing from that total?',
        'reads': ('facts.fractions_share_one_denominator', 'facts.all_species_assayed'),
        'rule': 'Shared rule over the two facts: any no fails, else any unknown is unknown, else all not_applicable is not applicable, else supported.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'closure',
        'question': 'Do the amounts found by the analyses add up to the amount the reaction started with (the closure of the analyses)?',
        'reads': ('quantities.total_recovery',),
        'rule': 'When the recovery is given the grader records it as a percent (total_recovery_percent) with its ref (recovery_refs) and leaves the judgement to the sheet; otherwise unknown. A closure is not an independent mass balance.',
        'thresholds': (),
        'returns': (
            ('unknown', 'recovery_recorded_for_the_sheet', 'the recovery is given: it is recorded and the sheet judges it'),
            ('unknown', 'recovery_not_stated', 'the recovery is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'analysis_run_to_completion',
        'question': 'Did the analysis step of each species run to completion before it was read (the reporter reached its plateau)?',
        'reads': ('facts.analysis_run_to_completion',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'signals_inside_standard_curve',
        'question': 'Did the readings of the samples lie inside the range of the standards?',
        'reads': ('facts.signals_inside_standard_curve',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'reporter_absorbance_range',
        'question': 'Did the absorbance of the reporter stay in the range where the detector is linear with the concentration?',
        'reads': ('quantities.reporter_absorbance_max',),
        'rule': 'When the highest absorbance is given the grader records it (absorbance_max) with its ref (absorbance_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'absorbance_recorded_for_the_sheet', 'the highest absorbance is given: it is recorded and the sheet judges it'),
            ('unknown', 'absorbance_not_stated', 'the highest absorbance is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'cross_reactivity',
        'question': 'Does the analysis enzyme of one species also read another species of the mixture, and how strongly?',
        'reads': ('quantities.analysis_enzyme_cross_reactivity', 'facts.analysis_enzyme_specificity_shown'),
        'rule': 'When the cross-reactivity is given the grader records it as a percent of the response to the analysis enzyme\'s own species (cross_reactivity_percent) with its ref (cross_reactivity_refs) and leaves the judgement to the sheet. Otherwise the specificity fact decides (the same sentence that shows specificity also says no other species was read): yes supported, no fails, unknown unknown, not_applicable not applicable. Silence is not specificity, and not cross-reaction.',
        'thresholds': (),
        'returns': (
            ('unknown', 'cross_reactivity_recorded_for_the_sheet', 'the cross-reactivity is given: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'no cross-reactivity is given and the specificity fact is yes'),
            ('conflicting', 'fact_answered_no', 'no cross-reactivity is given and the specificity fact is no'),
            ('unknown', 'fact_unknown', 'no cross-reactivity is given and the specificity fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no cross-reactivity is given and the specificity fact is not_applicable'),
        ),
    },
    {
        'id': 'first_enzyme_quenched',
        'question': 'Was the reaction of the studied enzyme stopped before the analyses, so that the mixture could not change further or disturb the analysis enzymes?',
        'reads': ('facts.first_enzyme_quenched_before_analysis',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'reagent_blank',
        'question': 'Was a blank run for the analyses (the analysis enzyme or the sample left out), so that the signal of the reagents and of the sample alone is set aside?',
        'reads': ('facts.reagent_blank_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'no_enzyme_sample',
        'question': 'Was a sample without the studied enzyme run and analysed in the same way, to see the species that appear or interconvert without the enzyme?',
        'reads': ('facts.no_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'products_stable_until_analysis',
        'question': 'Did the species stay unchanged between the end of the reaction and the analysis (no interconversion, degradation or loss on standing)?',
        'reads': ('facts.products_stable_until_analysis',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_sample',
        'question': 'Was a sample with an inactive enzyme (heat-denatured or a catalytically dead mutant) run and analysed in the same way, so that the species can be attributed to the enzyme\'s catalysis?',
        'reads': ('facts.inactive_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'stable_composition',
        'question': 'Does the composition stay the same over time, or come out the same from both sides, so that it is an equilibrium and not a single end point?',
        'reads': ('facts.distribution_stable_over_time', 'facts.approached_from_both_sides'),
        'rule': 'Stability stated as no fails. Either fact stated as yes is supported. Both not_applicable is not applicable. Otherwise unknown (silence is not an equilibrium, and not a non-equilibrium).',
        'thresholds': (),
        'returns': (
            ('conflicting', 'composition_still_changing', 'the stability fact is no'),
            ('supported', 'equilibrium_evidence_stated', 'either fact is yes (and the stability fact is not no)'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
            ('unknown', 'equilibrium_evidence_not_stated', 'neither is yes, the stability fact is not no, and they are not both not_applicable'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated analyses of one sample are not replicates.',
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
