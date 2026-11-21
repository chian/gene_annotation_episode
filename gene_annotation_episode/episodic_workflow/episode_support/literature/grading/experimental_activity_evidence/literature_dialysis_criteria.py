"""Dialysis criteria: the ONE place where the equilibrium dialysis / ultrafiltration binding grader's criteria and thresholds are declared (a ligand and a protein are separated from each other's bound form across a semipermeable membrane (equilibrium dialysis, rapid equilibrium dialysis, ultrafiltration, ultracentrifugation); the free and the total ligand concentration are measured by radioactivity, LC-MS/MS, fluorescence or absorbance; the result is a fraction bound or a percent unbound, or a KD and Bmax from a saturation series, or a Ki).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the dialysis grader asks. The grader reports FACTS and holds NO threshold
that judges goodness: where a criterion needs a number to be compared with a limit (the percent bound, the time to equilibrium, the recovery, the
adsorption, the volume shift, the salt, the bound ligand over the protein, the protein over the KD, the percent unbound, the number of concentrations and
the span of the series over the KD, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending
in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_dialysis_converter.py. The logic that
answers each question is in literature_dialysis_grader.py (one short function per criterion, same order). The only constants left here are unit
conversions (FIXED_BY_DEFINITION).

How to read an entry in DIALYSIS_CRITERIA
-----------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_dialysis_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet.

Support rule (from the ELISA work, designed in from the start): a criterion returns 'supported' or 'conflicting' only with
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' or 'not_applicable' with a
declared reason, never 'supported' and never 'conflicting'. The choices of the record (separation method, device, detector, spread kind, fit model) hold no span, so no
criterion rests on a choice alone: the separation method only switches the equilibrium criterion off ('not_applicable') for ultrafiltration and ultracentrifugation, which are not
equilibrium methods, and the fit model is supported by the spans of the constants it was fitted to.

What the claim is. The experiment is judged by how well it supports "this protein binds this ligand (with this affinity)". Dialysis measures the free ligand directly, which is its
strength: no label, no immobilisation and no change of the ligand are needed, and the result is the fraction bound (or the percent unbound) at the concentrations tried, or, from
a series of concentrations, KD and Bmax. What can go wrong is what the criteria ask: the time to equilibrium (slow for a large protein, a tight binder and a low temperature), losses
and nonspecific binding of the ligand to the membrane and the device (which inflate the apparent binding), the Donnan effect and the volume shift, ligand stability, leakage of the protein
through the membrane, a buffer-only control, a fraction bound that is too small or too large to measure, a protein concentration far below the KD, a bound ligand that exceeds the protein
(depletion), a series of concentrations that does not bracket the KD, and independent replicates. A record that reports no KD and no Ki (for example only a percent bound at one
concentration) is a qualitative result: the criteria that need a KD are 'not_applicable' ('no_kd_reported', 'no_binding_constant_reported') and the converter hands its statement to the
merger as the qualitative effect.

Terms. Free ligand: the ligand on the side without protein (the dialysate or the filtrate). Percent bound: the percent of the total ligand that is bound to the protein (100 minus the percent unbound).
Recovery: the percent of the total ligand put in that is found in both chambers together (a mass balance). Membrane adsorption: the percent of the ligand that binds to the membrane and the device.
Volume shift: the percent by which the volume of the protein chamber changes (osmotic flow, Donnan effect).

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the spreads of KD and Ki and their kind, the number of binding sites Bmax (it supports the fit
model but is not itself judged), the membrane cutoff, the device, the detection method, the temperature, the pH, the volumes of the chambers, the number of cells per experiment, the
free and the total ligand concentration of a single reading, and the statement that only this method was used.
"""

VERSION = 'a105_dialysis_criteria_v1'

# ---- Threshold constants -------------------------------------------------
PERCENT_FULL = 100.0  # FIXED_BY_DEFINITION: percent in the whole (percent bound = 100 minus percent unbound; a fraction times 100 is a percent).
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
H_PER_UNIT = {'min': 1 / 60, 'h': 1.0}  # FIXED_BY_DEFINITION: hours per time unit.
MM_PER_SALT_UNIT = {'mM': 1.0, 'M': 1000.0}  # FIXED_BY_DEFINITION: millimolar per salt concentration unit.


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
DIALYSIS_CRITERIA = (
    {
        'id': 'binding_observed',
        'question': 'Was binding of the ligand to the protein observed (a measurable fraction of the ligand bound)?',
        'reads': ('facts.binding_detected', 'quantities.percent_bound', 'quantities.percent_bound_spread', 'quantities.percent_unbound', 'quantities.fraction_bound', 'quantities.fraction_unbound'),
        'rule': 'The fact decides: yes supported, no fails, not_applicable not applicable. When the fact is unknown and a fraction is stated, the grader records the percent bound (percent_bound: the stated percent bound, else 100 minus the percent unbound, else the fraction bound times 100, else 100 minus the fraction unbound times 100; percent_bound_refs), with the stated standard deviation of the percent bound when there is one (percent_bound_spread, percent_bound_spread_refs), and leaves the judgement (whether binding is shown) to the sheet, which also reads the qualitative statement from it; none stated is unknown.',
        'thresholds': ('PERCENT_FULL',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'percent_bound_recorded_for_the_sheet', 'the fact is unknown and a fraction is stated: the percent bound is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'the fact is unknown and no fraction is stated'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when the free and the bound ligand were measured?',
        'reads': ('facts.equilibrium_time_course_shown', 'quantities.equilibration_time', 'separation_method'),
        'rule': 'The fact decides: yes supported, no fails, not_applicable not applicable. When it is not stated, an ultrafiltration or an ultracentrifugation does not apply (they are not equilibrium methods); otherwise a stated time to equilibrium is recorded (equilibration_h, in hours, and equilibration_refs) and the judgement is left to the sheet; no time is unknown.',
        'thresholds': ('H_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('not_applicable', 'method_is_not_equilibrium_dialysis', 'not stated and the separation method is ultrafiltration or ultracentrifugation'),
            ('unknown', 'equilibration_time_recorded_for_the_sheet', 'not stated and a time to equilibrium is stated: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no time is stated'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'recovery',
        'question': 'Was the ligand recovered from both chambers (a mass balance)?',
        'reads': ('quantities.recovery', 'facts.recovery_checked'),
        'rule': 'A stated recovery is recorded (recovery_percent, recovery_refs) and the judgement is left to the sheet. Otherwise the fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('unknown', 'recovery_recorded_for_the_sheet', 'a recovery is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'none stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'none stated and the fact is no'),
            ('unknown', 'fact_unknown', 'none stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'none stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'device_adsorption',
        'question': 'Was the binding of the ligand to the membrane and the device small, or checked and corrected?',
        'reads': ('quantities.membrane_adsorption', 'facts.adsorption_checked_and_corrected'),
        'rule': 'A stated adsorption is recorded (adsorption_percent, adsorption_refs) together with the answer of the fact (adsorption_corrected, adsorption_corrected_refs: whether it was checked and corrected, when the fact is not unknown) and the judgement is left to the sheet. Otherwise the fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('unknown', 'adsorption_recorded_for_the_sheet', 'an adsorption is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'none stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'none stated and the fact is no'),
            ('unknown', 'fact_unknown', 'none stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'none stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'volume_shift',
        'question': 'Was the Donnan effect or the osmotic volume shift corrected, small or ruled out by the salt?',
        'reads': ('facts.volume_shift_corrected', 'quantities.volume_shift', 'quantities.salt_concentration'),
        'rule': 'The fact decides: yes supported, no fails, not_applicable not applicable. When the fact is unknown, a stated volume shift is recorded (volume_shift_percent, volume_shift_refs) and the judgement is left to the sheet; with no volume shift, a stated salt concentration is recorded (salt_mM, in mM, and salt_refs) and the judgement is left to the sheet (a low salt does not show a shift); otherwise unknown.',
        'thresholds': ('MM_PER_SALT_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'volume_shift_recorded_for_the_sheet', 'the fact is unknown and a volume shift is stated: it is recorded and the sheet judges it'),
            ('unknown', 'salt_recorded_for_the_sheet', 'the fact and the volume shift are unknown and a salt is stated: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'the fact, the volume shift and the salt are unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('ligand_stability', 'Was the ligand stable over the incubation (no degradation)?', 'ligand_stable'),
    _one_fact('free_measured_directly', 'Was the free ligand concentration measured directly, not inferred from the total?', 'free_ligand_measured_directly'),
    _one_fact('protein_retained', 'Did the protein stay behind the membrane (no leak through it)?', 'protein_retained'),
    _one_fact('buffer_only_control', 'Did a control with buffer only (no protein) show equal ligand concentrations in both chambers?', 'buffer_only_control_equal'),
    {
        'id': 'ligand_depletion',
        'question': 'Was the bound ligand concentration at most the protein concentration (the sites not used up)?',
        'reads': ('quantities.bound_ligand_concentration', 'quantities.ligand_total_concentration', 'quantities.free_ligand_concentration', 'quantities.protein_concentration'),
        'rule': 'The bound ligand concentration (the stated one, else the total minus the free when both are stated and the total is larger) over the protein concentration is recorded (bound_over_protein, bound_over_protein_refs) and the judgement is left to the sheet. A bound ligand or the protein concentration not stated is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'bound_over_protein_recorded_for_the_sheet', 'both are available: the ratio is recorded and the sheet judges it'),
            ('unknown', 'bound_or_protein_concentration_not_given', 'no bound ligand concentration can be had or no protein concentration is stated'),
        ),
    },
    {
        'id': 'protein_level',
        'question': 'Was the protein concentration high enough relative to the KD for a fraction bound to be measured?',
        'reads': ('quantities.protein_concentration', 'quantities.kd', 'facts.protein_at_or_above_kd'),
        'rule': 'When the protein concentration and the KD are both stated, the protein concentration over the KD is recorded (protein_over_kd, protein_over_kd_refs) and the judgement is left to the sheet. Otherwise the fact decides: yes supported, no fails, not_applicable not applicable; an unknown fact is unknown, or not applicable when no KD is reported.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'protein_over_kd_recorded_for_the_sheet', 'both are stated: the ratio is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'not both stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'not both stated and the fact is no'),
            ('unknown', 'fact_unknown', 'not both stated, the fact is unknown and a KD is reported'),
            ('not_applicable', 'no_kd_reported', 'not both stated, the fact is unknown and no KD is reported'),
            ('not_applicable', 'fact_not_applicable', 'not both stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'free_fraction_measurable',
        'question': 'Was the free fraction large enough to be measured (not below the minimum percent unbound)?',
        'reads': ('quantities.percent_unbound', 'quantities.fraction_unbound', 'quantities.percent_bound', 'quantities.fraction_bound', 'quantities.free_ligand_concentration', 'quantities.ligand_total_concentration', 'quantities.detection_lloq'),
        'rule': 'The percent unbound (the stated one, else the fraction unbound times 100, else 100 minus the percent bound, else 100 minus the fraction bound times 100) is recorded (percent_unbound, percent_unbound_refs) and the judgement is left to the sheet. When the detector\'s lower limit of quantification is stated and the free concentration of the reading is known (the stated free concentration, else the total concentration times the percent unbound over 100), the free concentration over the limit is recorded too (free_over_lloq, free_over_lloq_refs). With no fraction but a free concentration over the limit, that ratio is recorded alone. Neither does not apply.',
        'thresholds': ('PERCENT_FULL',),
        'returns': (
            ('unknown', 'percent_unbound_recorded_for_the_sheet', 'a fraction is stated: the percent unbound is recorded (and the free concentration over the limit of quantification when both are known) and the sheet judges it'),
            ('unknown', 'free_over_lloq_recorded_for_the_sheet', 'no fraction is stated, a free concentration and the limit of quantification are: the ratio is recorded and the sheet judges it'),
            ('not_applicable', 'no_fraction_reported', 'no fraction is stated and no free concentration over the limit can be had'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Did the series of ligand concentrations have enough points and bracket the KD well enough to define KD and the plateau?',
        'reads': ('quantities.kd', 'quantities.ki', 'quantities.titration_point_count', 'quantities.ligand_range_lowest', 'quantities.ligand_range_highest', 'concentration_series'),
        'rule': 'With neither a KD nor a Ki the criterion does not apply. Otherwise the grader records the number of concentrations (the listed series, else the stated number of points: concentration_count, concentration_count_refs) and, from the KD and a list or a lowest and a highest concentration, the lowest and the highest over the KD (concentration_low_over_kd, concentration_high_over_kd, concentration_span_refs); the judgement of the count and of the span is left to the sheet.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_series_recorded_for_the_sheet', 'a count or a span is recorded: the sheet judges them'),
            ('unknown', 'kd_or_series_missing', 'no count is stated or listed and no KD, or no list and no lowest and highest concentration is given'),
            ('not_applicable', 'no_binding_constant_reported', 'neither a KD nor a Ki is reported'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the model of the saturation fit stated?',
        'reads': ('fit_model', 'quantities.kd', 'quantities.bmax', 'quantities.ki'),
        'rule': 'The model must be stated and a KD, Bmax or Ki must be reported, because the quoted spans of the reported constants are the only support of the model. A model stated with no reported constant is unknown (no span supports it). No model stated is unknown when a constant is reported and does not apply when none is (a record with no constant has no fit).',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a model stated and a constant reported'),
            ('unknown', 'model_stated_without_a_reported_constant', 'a model stated and no constant reported'),
            ('unknown', 'fit_model_not_stated', 'no fit model and a constant reported'),
            ('not_applicable', 'no_binding_constant_reported', 'no fit model and no KD, Bmax or Ki reported'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Cells of one experiment are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
        ),
    },
)
