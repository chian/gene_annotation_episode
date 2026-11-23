"""Distribution_nmr criteria: the ONE place where the grader's criteria of a quantitative NMR measurement of a product mixture are declared.

This file is the single source for what the distribution_nmr grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a
criterion needs a number to be compared with a limit (the delay between scans against the longest T1, the signal-to-noise ratio of the minor signal, the
replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_distribution_nmr_converter.py. The logic that answers each question is in
literature_distribution_nmr_grader.py (one short function per criterion, same order). There is no constant here: a time unit is turned into seconds by the
grader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in DISTRIBUTION_NMR_CRITERIA
-------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_nmr_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_nmr_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_NMR_CRITERIA = (
    {
        'id': 'shares_from_resolved_signals',
        'question': 'Was each species quantified from its own resolved NMR signal, not from a signal overlapping with another species?',
        'reads': ('facts.integrals_from_resolved_signals',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'species_assigned_with_standards',
        'question': 'Were the species assigned by authentic standards, reference spectra or spiking, and not only by an expected chemical shift?',
        'reads': ('facts.species_assigned_with_standards',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'relaxation_delay',
        'question': 'Was the delay between scans long enough for the integrated nuclei to relax fully, so that the integrals are in proportion to the amounts?',
        'reads': ('facts.relaxation_delay_adequate', 'quantities.relaxation_delay', 'quantities.longest_t1'),
        'rule': 'The fact stated as no fails. The fact stated as yes is supported (the paper says the relaxation was adequate). Otherwise, when the delay is given, the grader records it (relaxation_delay_s) with the longest T1 when that is given (longest_t1_s) and their refs (relaxation_refs) and leaves the judgement to the sheet; with neither the fact nor the delay it is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('supported', 'relaxation_delay_adequate_stated', 'the fact is yes'),
            ('unknown', 'relaxation_recorded_for_the_sheet', 'the fact is not stated and the delay is given: it is recorded (with the T1 when given) and the sheet judges it'),
            ('unknown', 'relaxation_not_stated', 'the fact is not stated and the delay is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'denominator_and_coverage',
        'question': 'Do the shares sit over one common total and does that total cover every species seen in the spectrum?',
        'reads': ('facts.fractions_share_one_denominator', 'facts.all_products_identified'),
        'rule': 'Both facts together: any no fails; otherwise any unknown is unknown; otherwise all not_applicable is not applicable; otherwise supported. The shares of the species of one reaction share one denominator, so they are one measurement, not several.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'no_enzyme_spectrum',
        'question': 'Was a mixture without the enzyme measured, to see what appears or interconverts without it (spontaneous isomerisation, hydrolysis or exchange)?',
        'reads': ('facts.no_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_spectrum',
        'question': 'Was a control with an inactive enzyme measured, so that the species are shown to come from the studied enzyme and not from a contaminating activity?',
        'reads': ('facts.inactive_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'minor_signal_to_noise',
        'question': 'Is the signal-to-noise ratio of the smallest integrated signal stated, so that the integral of a minor species can be trusted?',
        'reads': ('quantities.signal_to_noise_minor',),
        'rule': 'When the ratio is given the grader records it (signal_to_noise_minor) with its ref (signal_to_noise_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'signal_to_noise_recorded_for_the_sheet', 'the ratio is given: it is recorded and the sheet judges it'),
            ('unknown', 'signal_to_noise_not_stated', 'the ratio is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'stable_composition',
        'question': 'Is the composition shown to be an equilibrium, by a composition that no longer changes over time or by the same composition reached from both sides?',
        'reads': ('facts.distribution_stable_over_time', 'facts.approached_from_both_sides'),
        'rule': 'The composition stated as still changing (stable over time stated as no) fails. Otherwise either fact stated as yes is supported. A reverse approach stated as not done is no evidence either way. Neither stated is unknown; both not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'composition_still_changing', 'the stable-over-time fact is no'),
            ('supported', 'equilibrium_evidence_stated', 'the stable-over-time fact is not no and either fact is yes'),
            ('unknown', 'equilibrium_evidence_not_stated', 'neither fact is yes, the stable-over-time fact is not no, and the two are not both not_applicable'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Several spectra of one sample are not replicates.',
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
        'question': 'Was the mixture produced by the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
