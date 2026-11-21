"""SPA criteria: the ONE place where the scintillation proximity assay (SPA) binding grader's criteria and thresholds are declared (a radioligand binding to a target captured on scintillant beads, no separation or wash; saturation binding for KD and Bmax, competition binding for IC50 and Ki by the Cheng-Prusoff equation).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the SPA grader asks. The grader reports FACTS and holds NO threshold
that judges goodness: where a criterion needs a number to be compared with a limit (the percent bound, the non-specific fraction, the
non-specific excess, the bead-only fraction, the incubation time, the concentration count and the span of the series over the KD, the
radioligand concentration over the KD, the Hill slope, the Cheng-Prusoff gap, the replicate count), the grader records the number with its
support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on
the sheet side, in literature_spa_converter.py. The logic that answers each question is in literature_spa_grader.py (one short function
per criterion, same order). The only constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in SPA_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_spa_record.py)
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

Terms. The binding constant of a record: the KD of the radioligand from a saturation experiment, else the Ki of a competition
(native 'constant_name' says which). The IC50 is a half-maximal concentration of a competition curve and depends on the
concentration and the KD of the radioligand it competes with; it is not a dissociation constant and is never carried as a binding
constant. Bound fraction (percent_bound): the percent of the added radioligand that is bound; the free concentration is taken to
be the added concentration, which holds only when little is bound (ligand depletion). Non-specific binding: the binding that
remains in the presence of an excess of an unlabelled ligand; specific binding is the total minus the non-specific binding.
Bead-only (non-proximity) control: the signal of radioligand and beads without the captured target; a radioligand can bind to the
bead itself and give a signal that no unlabelled ligand removes in the way it removes specific binding. Non-proximity signal: the
small signal of free radioligand in solution that excites a bead it is not bound to; it rises with the radioligand concentration.
Cheng-Prusoff equation: Ki = IC50 / (1 + [radioligand] / KD), with the KD of the same radioligand on the same target.
Hill slope: the steepness of the curve; 1 is one site obeying the law of mass action.

What this method does not ask (items of other binding experiments left out because an SPA has no such thing): filter binding and
the dissociation in a wash (an SPA has no filter and no wash: the homogeneous no-wash format is itself a criterion), a sensorgram
baseline, a signal window of a label signal, the hook effect, the particle number of a confocal volume, the coating of a plate. The
specific activity, the isotope, the kind of bead, the way the target is captured, the kind of target, the amount of beads and of
target per well, the counting efficiency, the settling time, the counter, the Bmax, the temperature, the number of technical wells,
the spread and the statement that only this method was used are kept in the record for the reviewer; no criterion judges them.
"""

VERSION = 'a105_spa_criteria_v1'

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
SPA_CRITERIA = (
    {
        'id': 'ligand_depletion',
        'question': 'Was the radioligand bound in so small a fraction that the free concentration is the added concentration?',
        'reads': ('quantities.percent_bound', 'facts.ligand_depletion_checked'),
        'rule': 'A reported percent of the added radioligand that was bound is recorded (percent_bound, percent_bound_refs) and the judgement is left to the sheet. When no percent is reported, the fact decides: yes supported, no fails, unknown unknown.',
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
        'rule': 'The reported non-specific binding, as a percent of the total binding, is recorded (nonspecific_fraction_percent, nonspecific_fraction_refs) and the judgement is left to the sheet. Not given is unknown.',
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
        'reads': ('quantities.nonspecific_excess', 'quantities.nonspecific_ligand_concentration', 'quantities.nonspecific_ligand_affinity', 'facts.nonspecific_ligand_is_radioligand', 'quantities.kd'),
        'rule': 'The stated fold excess of the unlabelled ligand over its Kd is recorded. Else the concentration of the unlabelled ligand over its own KD or Ki (nonspecific_ligand_affinity) is recorded; else, only when the fact says the unlabelled ligand is the unlabelled radioligand itself, over the KD of the radioligand. A concentration whose ligand has neither its own affinity nor that fact is not divided by the radioligand KD (another ligand has another affinity). The result is recorded (nonspecific_excess_ratio, nonspecific_excess_refs) and the judgement is left to the sheet.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'excess_recorded_for_the_sheet', 'the excess is stated or computable against the right constant: it is recorded and the sheet judges it'),
            ('unknown', 'excess_reference_not_given', 'a concentration of the unlabelled ligand is given, but neither its own affinity nor that it is the unlabelled radioligand (with a KD)'),
            ('unknown', 'excess_not_given', 'no fold excess is stated and no concentration of the unlabelled ligand is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _one_fact('nonproximity_signal', 'Was the non-proximity signal of the free radioligand (light from radioligand that is not bound to the captured target) checked?', 'nonproximity_signal_checked'),
    {
        'id': 'bead_only_control',
        'question': 'Was a control without the captured target (the radioligand binding to the bead itself) measured, and was its signal a small part of the total signal?',
        'reads': ('quantities.bead_only_fraction', 'facts.bead_only_control_done'),
        'rule': 'A reported signal of the control without the captured target, as a percent of the total signal, is recorded (bead_only_percent, bead_only_refs) and the judgement is left to the sheet. When no percent is reported, the fact decides: yes supported, no fails, unknown unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'bead_only_percent_recorded_for_the_sheet', 'a bead-only percent is reported: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'no percent reported and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'no percent reported and the fact is no'),
            ('unknown', 'fact_unknown', 'no percent reported and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no percent reported and the fact is not_applicable'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when the plate was counted?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time', 'quantities.association_half_time'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an incubation time is given, the grader records it (incubation_min, in minutes, and incubation_refs; with no half-time also the KD in the native record, kd_nM and kd_refs); when the half-time of an association time course is also given it records the incubation over that half-time (incubation_over_half_time, half_time_refs). The judgement is left to the sheet; otherwise it is unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_over_half_time_recorded_for_the_sheet', 'not stated, and an incubation time and an association half-time are given: the quotient is recorded and the sheet judges it'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'not stated, an incubation time is given and no association half-time: it is recorded with the KD and its refs, and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no incubation time'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'radioligand_range',
        'question': 'Did the radioligand concentrations of the saturation series bracket the KD well enough to define KD and Bmax?',
        'reads': ('quantities.kd', 'quantities.titration_point_count', 'quantities.radioligand_range_lowest', 'quantities.radioligand_range_highest', 'concentration_series'),
        'rule': 'The grader records the number of concentrations (the listed series, else the stated number of points: concentration_count, concentration_count_refs) and, from the KD and a list or a lowest and a highest concentration, the lowest and the highest over the KD (concentration_low_over_kd, concentration_high_over_kd, concentration_span_refs); the judgement of the count and of the span is left to the sheet. The assay format does not switch it off: a record whose source reports a competition beside a saturation experiment is one experiment, and a record with no saturation data is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_series_recorded_for_the_sheet', 'a count or a span is recorded: the sheet judges them'),
            ('unknown', 'kd_or_series_missing', 'no count is stated or listed and no KD, or no list and no lowest and highest concentration is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'competition_radioligand_level',
        'question': 'Was the single radioligand concentration of the competition at or below the KD of the radioligand?',
        'reads': ('quantities.radioligand_concentration', 'quantities.kd'),
        'rule': 'The radioligand concentration over the KD is recorded (radioligand_over_kd, radioligand_over_kd_refs) and the judgement is left to the sheet. Either not given is unknown (the assay format does not switch the criterion off: no competition concentration given is unknown).',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'radioligand_over_kd_recorded_for_the_sheet', 'both are given: the quotient is recorded and the sheet judges it'),
            ('unknown', 'radioligand_concentration_or_kd_not_given', 'the radioligand concentration or the KD is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _one_fact('homogeneous_format', 'Was the bound radioligand measured without a separation or wash step (a no-wash format that holds the binding at equilibrium in the presence of the free radioligand)?', 'homogeneous_no_wash_format'),
    _one_fact('radioligand_quality', 'Was the purity of the radioligand (and its freedom from radiolysis degradation) checked?', 'radioligand_purity_checked'),
    _one_fact('quench_interference', 'Was the lowering of the counts by coloured or quenching compounds or buffer (colour quench) checked or corrected for?', 'quench_interference_checked'),
    _one_fact('bead_settling', 'Was the settling of the beads controlled (a fixed settling time, or a check that the signal is stable)?', 'bead_settling_controlled'),
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
        'rule': 'The reported Hill slope is recorded (hill_slope, hill_slope_refs) and the judgement is left to the sheet. Not given is unknown.',
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
        'rule': 'A fact answered no fails. Otherwise, when a Ki, an IC50, the radioligand concentration and the KD are all reported, the grader records the reported Ki, the Ki calculated as IC50 / (1 + radioligand concentration / KD), their quotient and the refs of the four (ki_nM, calculated_ki_nM, ki_over_calculated, cheng_prusoff_refs) and leaves the judgement of the gap to the sheet, whatever the fact says. Otherwise the fact decides: yes supported, unknown unknown. When the fact is not stated, the format is a saturation experiment and neither a Ki nor an IC50 is reported, the criterion does not apply.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'cheng_prusoff_gap_recorded_for_the_sheet', 'the fact is not no and the four values are reported: the gap is recorded and the sheet judges it'),
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
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Wells of one experiment are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
