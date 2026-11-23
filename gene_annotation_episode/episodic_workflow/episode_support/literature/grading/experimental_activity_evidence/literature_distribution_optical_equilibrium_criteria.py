"""Distribution_optical_equilibrium criteria: the ONE place where the grader's criteria of an optical equilibrium measurement of a reaction mixture are declared.

This file is the single source for what the distribution_optical_equilibrium grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the highest absorbance, how much the signal still changed at the plateau, the
replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_distribution_optical_equilibrium_converter.py. The logic that answers each
question is in literature_distribution_optical_equilibrium_grader.py (one short function per criterion, same order). There is no constant here and no unit
conversion: nothing is compared.

How to read an entry in DISTRIBUTION_OPTICAL_EQUILIBRIUM_CRITERIA
-----------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_distribution_optical_equilibrium_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_distribution_optical_equilibrium_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

DISTRIBUTION_OPTICAL_EQUILIBRIUM_CRITERIA = (
    {
        'id': 'pure_species_spectra',
        'question': 'Was the spectrum of each pure species measured under the conditions of the assay, so that the plateau signal can be assigned to the species (the species are told apart by their spectra only)?',
        'reads': ('facts.pure_species_spectra_measured',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'extinction_coefficient_stated',
        'question': 'Is the extinction coefficient that turns the plateau absorbance into a concentration stated, with the wavelength it belongs to?',
        'reads': ('quantities.extinction_coefficient', 'quantities.wavelength'),
        'rule': 'Both stated is supported; either missing is unknown (a composition whose conversion constant is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'extinction_coefficient_and_wavelength_stated', 'both are given'),
            ('unknown', 'extinction_coefficient_or_wavelength_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'denominator_and_coverage',
        'question': 'Is every species that absorbs at the wavelength read accounted for in the composition, and is the composition (or constant) that of the single reaction step tested rather than a composite of coupled equilibria?',
        'reads': ('facts.all_absorbing_species_accounted', 'facts.constant_refers_to_one_step'),
        'rule': 'Both facts together: any no fails; otherwise any unknown is unknown; otherwise all not_applicable is not applicable; otherwise supported. The shares of the species of one mixture share one denominator, so they are one measurement, not several.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'absorbance_range',
        'question': 'Did the absorbance stay in the range where the detector is linear with the concentration?',
        'reads': ('quantities.absorbance_max',),
        'rule': 'When the highest absorbance is given the grader records it (absorbance_max) with its ref (absorbance_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'absorbance_recorded_for_the_sheet', 'the highest absorbance is given: it is recorded and the sheet judges it'),
            ('unknown', 'absorbance_not_stated', 'the highest absorbance is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'no_enzyme_sample',
        'question': 'Was a mixture without the enzyme followed in the same way, to see whether the signal moves without it (the equilibrium itself does not depend on the enzyme, so this shows whether the approach needs it)?',
        'reads': ('facts.no_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_enzyme_sample',
        'question': 'Was a control with an inactive enzyme followed in the same way, so that the approach to equilibrium is shown to come from the studied enzyme and not from a contaminating activity?',
        'reads': ('facts.inactive_enzyme_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'plateau_stability',
        'question': 'Did the signal reach a stable plateau, with no drift left, so that the composition read from it is the end state and not a point on the way?',
        'reads': ('facts.plateau_stable', 'quantities.plateau_change_percent'),
        'rule': 'The fact stated as no fails. When the change of the signal over the plateau window is given the grader records it (plateau_change_percent, plateau_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'plateau_change_recorded_for_the_sheet', 'the change is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'plateau_stable_stated', 'no change is given and the fact is yes'),
            ('unknown', 'plateau_not_stated', 'no change is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'equilibrium_from_both_sides',
        'question': 'Is the composition shown to be an equilibrium by reaching it from both sides (from the substrate and from the product) or the same value at several initial concentrations?',
        'reads': ('facts.approached_from_both_sides', 'facts.same_value_at_several_initial_concentrations'),
        'rule': 'Either fact stated as yes is supported. A reverse approach or a concentration series stated as not done is no evidence either way (the plateau criterion carries the stability), so neither stated is unknown; both not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'equilibrium_evidence_stated', 'either fact is yes'),
            ('unknown', 'equilibrium_evidence_not_stated', 'neither fact is yes and the two are not both not_applicable'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
            ('conflicting', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated reads of one mixture are not replicates.',
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
        'question': 'Was the mixture brought to equilibrium by the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
