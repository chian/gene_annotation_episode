"""Radioligand criteria: the ONE place where the radioligand binding grader's criteria and thresholds are declared (saturation binding for KD and Bmax, competition binding for IC50 and Ki by the Cheng-Prusoff equation; filtration or scintillation proximity separation of bound from free).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the radioligand grader asks. The grader reports FACTS and holds NO threshold that
judges goodness: where a criterion needs a number to be compared with a limit (the percent bound, the non-specific fraction and excess, the incubation,
the radioligand concentration range and level, the Hill slope, the agreement with Cheng-Prusoff, the replicate count), the grader records the number
with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the
sheet side, in literature_radioligand_converter.py. The logic that answers each question is in literature_radioligand_grader.py (one short function per
criterion, same order). The only constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in RADIOLIGAND_CRITERIA
--------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_radioligand_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Support rule (from the ELISA work, designed in from the start): a criterion returns 'supported' or 'conflicting' only with
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span, or a fit model stated while
no constant is reported (the model has no span of its own: the spans of the reported constants are its support), is 'unknown'
with a declared reason, never 'supported' and never 'conflicting'.

Constants: each is defined once, below, and marked FIXED_BY_DEFINITION (a unit conversion, not a judgment).

Terms. The binding constant of a record: the KD of the radioligand from a saturation experiment, else the Ki of a competition
(native 'constant_name' says which). The IC50 is a half-maximal concentration of a competition curve and depends on the
concentration and the KD of the radioligand it competes with; it is not a dissociation constant and is never carried as a binding
constant. Bound fraction (percent_bound): the percent of the added radioligand that is bound; the free concentration is taken to
be the added concentration, which holds only when little is bound (ligand depletion). Non-specific binding: the binding that
remains in the presence of an excess of an unlabelled ligand; specific binding is the total minus the non-specific binding.
Cheng-Prusoff equation: Ki = IC50 / (1 + [radioligand] / KD), with the KD of the same radioligand on the same preparation.
Hill slope: the steepness of the curve; 1 is one site obeying the law of mass action.

What this method does not ask (items of the other binding experiments left out because a radioligand assay has no such thing): a
sensorgram baseline, a signal window of a label signal, a counter-screen of optical interference, the hook effect, the particle
number of a confocal volume, the coating of a plate. The specific activity, the isotope, the amount of receptor per assay, the
type of preparation (membrane, purified protein, whole cell), the separation method (read only to decide whether a filter and a
wash apply), the Bmax, the temperature, the number of technical wells, the spread and the statement that only this method
was used are kept in the record for the reviewer; no criterion judges them.
"""

VERSION = 'a105_radioligand_criteria_v1'

# ---- Threshold constants -------------------------------------------------
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.


def _fact_returns():
    return (
        ('supported', 'facts_answered_yes', 'answer yes'),
        ('conflicting', 'fact_answered_no', 'answer no'),
        ('unknown', 'fact_unknown', 'answer unknown'),
        ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
    )


def _one_fact(criterion_id, question, fact_name):
    return {'id': criterion_id, 'question': question, 'reads': ('facts.' + fact_name,),
            'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
            'thresholds': (), 'returns': _fact_returns()}


# ---- The criteria --------------------------------------------------------
RADIOLIGAND_CRITERIA = (
    {
        'id': 'ligand_depletion',
        'question': 'Was the radioligand bound in so small a fraction that the free concentration is the added concentration?',
        'reads': ('quantities.percent_bound', 'facts.ligand_depletion_checked'),
        'rule': 'A reported percent of the added radioligand that was bound is recorded (percent_bound and percent_bound_refs) and the judgement is left to the sheet. When no percent is reported, the fact decides: yes supported, no fails, unknown unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'percent_bound_recorded_for_the_sheet', 'a percent bound is reported: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'no percent reported and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'no percent reported and the fact is no'),
            ('unknown', 'fact_unknown', 'no percent reported and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no percent reported and the fact is not_applicable'),
        ),
    },
    {
        'id': 'nonspecific_fraction',
        'question': 'Was the non-specific binding a small enough part of the total binding at the highest radioligand concentration?',
        'reads': ('quantities.nonspecific_fraction',),
        'rule': 'The reported non-specific binding, as a percent of the total binding, is recorded (nonspecific_percent and nonspecific_fraction_refs) and the judgement is left to the sheet. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'nonspecific_fraction_recorded_for_the_sheet', 'a fraction is reported: it is recorded and the sheet judges it'),
            ('unknown', 'nonspecific_fraction_not_given', 'no fraction is reported'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _one_fact('nonspecific_binding', 'Was non-specific binding determined (with an excess of an unlabelled ligand) and subtracted from the total binding to give the specific binding?', 'nonspecific_binding_determined'),
    {
        'id': 'nonspecific_excess',
        'question': 'Was non-specific binding defined with a high enough excess of the unlabelled ligand?',
        'reads': ('quantities.nonspecific_excess', 'quantities.nonspecific_ligand_concentration', 'quantities.kd'),
        'rule': 'The stated fold excess of the unlabelled ligand over the Kd, else the concentration of the unlabelled ligand over the KD of the radioligand, is recorded (nonspecific_excess_ratio and nonspecific_excess_refs) and the judgement is left to the sheet. Neither given is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'excess_recorded_for_the_sheet', 'a fold excess is stated, or the unlabelled ligand concentration and the KD are given: the excess is recorded and the sheet judges it'),
            ('unknown', 'excess_not_given', 'no fold excess is stated and the concentration of the unlabelled ligand or the KD is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when the bound radioligand was separated from the free?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an incubation time is given, the grader records it (incubation_min, in minutes, and incubation_refs) and leaves the judgement to the sheet; otherwise it is unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'not stated and an incubation time is given: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no incubation time'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'radioligand_range',
        'question': 'Did the radioligand concentrations of the saturation series bracket the KD well enough to define KD and Bmax?',
        'reads': ('quantities.kd', 'quantities.titration_point_count', 'quantities.radioligand_range_lowest', 'quantities.radioligand_range_highest', 'concentration_series'),
        'rule': 'The grader records the number of concentrations (concentration_count: the listed series, else the stated number of points) with its refs (concentration_count_refs) and, when the KD and a list (or a lowest and a highest concentration) are given, the lowest and the highest concentration over the KD (concentration_low_over_kd, concentration_high_over_kd) with their refs (concentration_span_refs); the judgement is left to the sheet. The span can only be recorded from the KD and a list or a lowest and a highest concentration. The assay format does not switch it off: a record whose source reports a competition beside a saturation experiment is one experiment, and a record with no saturation data is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'radioligand_range_recorded_for_the_sheet', 'a count is known, or the span can be recorded: what is known is recorded and the sheet judges it'),
            ('unknown', 'kd_or_series_missing', 'no count is known and no span can be recorded'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'competition_radioligand_level',
        'question': 'Was the single radioligand concentration of the competition at or below the KD of the radioligand?',
        'reads': ('quantities.radioligand_concentration', 'quantities.kd'),
        'rule': 'The radioligand concentration over the KD is recorded (radioligand_over_kd and radioligand_level_refs) and the judgement is left to the sheet. Either not given is unknown (the assay format does not switch the criterion off: no competition concentration given is unknown).',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'radioligand_over_kd_recorded_for_the_sheet', 'both are given: the quotient is recorded and the sheet judges it'),
            ('unknown', 'radioligand_concentration_or_kd_not_given', 'the radioligand concentration or the KD is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _one_fact('radioligand_quality', 'Was the purity of the radioligand (and its freedom from radiolysis degradation) checked?', 'radioligand_purity_checked'),
    {
        'id': 'filter_binding',
        'question': 'Was the binding of the radioligand to the filter (or to the beads) checked?',
        'reads': ('facts.filter_binding_checked', 'separation_method'),
        'rule': 'The fact decides: yes supported, no fails, unknown unknown. When it is not stated and the separation method is not filtration (scintillation proximity or centrifugation), the criterion does not apply.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'not stated and the separation is filtration or not stated'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
            ('not_applicable', 'separation_is_not_filtration', 'not stated and the separation method is scintillation proximity or centrifugation'),
        ),
    },
    {
        'id': 'wash_dissociation',
        'question': 'Was the dissociation of the radioligand during the wash considered (a fast off-rate loses bound radioligand in a wash)?',
        'reads': ('facts.wash_dissociation_considered', 'separation_method'),
        'rule': 'The fact decides: yes supported, no fails, unknown unknown. When it is not stated and the separation method is scintillation proximity (no wash), the criterion does not apply.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'not stated and the separation is not scintillation proximity or not stated'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
            ('not_applicable', 'no_wash_in_scintillation_proximity', 'not stated and the separation method is scintillation proximity'),
        ),
    },
    _one_fact('nonlinear_fit', 'Were the constants obtained by a non-linear fit of the binding curve and not from a linearised (Scatchard) plot?', 'nonlinear_fit_used'),
    {
        'id': 'fit_model',
        'question': 'Is the model of the binding curve stated, and does it fit the assay format?',
        'reads': ('fit_model', 'assay_format', 'quantities.kd', 'quantities.bmax', 'quantities.ki', 'quantities.ic50'),
        'rule': 'The model must be stated and a KD, Bmax, Ki or IC50 must be reported, because the quoted spans of the reported constants are the only support of the model. A one-site competition model (competitive_binding) for a saturation experiment fails; every other model fits every format. Not stated is unknown. A model stated with no reported constant is unknown, whatever the format (no span supports it, so neither supported nor conflicting can be returned).',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a model stated that fits the format (or no format stated) and a constant reported'),
            ('conflicting', 'competition_model_for_saturation', 'competitive binding model and saturation experiment, and a constant reported'),
            ('unknown', 'model_stated_without_a_reported_constant', 'a model stated and no constant reported'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'hill_slope',
        'question': 'Is the Hill slope close to 1, so that one site obeying mass action describes the binding?',
        'reads': ('quantities.hill_slope',),
        'rule': 'The reported Hill slope is recorded (hill_slope and hill_slope_refs) and the judgement is left to the sheet. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'hill_slope_recorded_for_the_sheet', 'a Hill slope is given: it is recorded and the sheet judges it'),
            ('unknown', 'hill_slope_not_given', 'no Hill slope is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'cheng_prusoff',
        'question': 'Was a Ki calculated from the IC50 by the Cheng-Prusoff equation with the KD of the same radioligand, and do the numbers agree?',
        'reads': ('facts.cheng_prusoff_applied_with_own_kd', 'quantities.ki', 'quantities.ic50', 'quantities.radioligand_concentration', 'quantities.kd', 'assay_format'),
        'rule': 'A fact answered no fails. Otherwise, when a Ki, an IC50, the radioligand concentration and the KD are all reported, the grader records the Ki calculated as IC50 / (1 + radioligand concentration / KD) (calculated_ki_nM), the reported Ki over it (ki_over_calculated), the larger over the smaller of the two (cheng_prusoff_fold, at least 1) and the refs of the four values (cheng_prusoff_refs) and leaves the judgement to the sheet, whatever the fact says. Otherwise the fact decides: yes supported, unknown unknown. When the fact is not stated, the format is a saturation experiment and neither a Ki nor an IC50 is reported, the criterion does not apply.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'cheng_prusoff_recorded_for_the_sheet', 'the fact is not no and the four values are reported: the fold gap is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'not all four values are reported and the fact is yes'),
            ('unknown', 'fact_unknown', 'not all four values are reported and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
            ('not_applicable', 'no_competition_constant', 'the fact is not stated, the format is a saturation experiment and neither a Ki nor an IC50 is reported'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Wells or tubes of one experiment are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
