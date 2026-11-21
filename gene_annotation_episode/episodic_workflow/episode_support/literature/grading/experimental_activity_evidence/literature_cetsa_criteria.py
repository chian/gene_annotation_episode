"""CETSA criteria: the ONE place where the cellular thermal shift assay (CETSA: melt curve and isothermal dose-response ITDR-CETSA) grader's criteria and thresholds are declared (a compound is added to intact cells, a lysate or a tissue, the sample is heated and the target protein that stays soluble is read by western blot, AlphaScreen or mass spectrometry; a ligand that binds the target stabilises it, so the melt curve shifts to a higher melting temperature Tm, or at one temperature the soluble fraction rises with the compound concentration, giving an EC50 that is an apparent engagement constant derived from the thermal shift; mostly a qualitative statement of target engagement).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the CETSA grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the thermal shift, the number of temperatures, the number of compound concentrations, the concentration range relative to the EC50,
the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_cetsa_converter.py.
The logic that answers each question is in literature_cetsa_grader.py (one short function per criterion, same order). The only constants left
here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in CETSA_CRITERIA
--------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_cetsa_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Support rule: a criterion returns 'supported' or 'conflicting' only with
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' or 'not_applicable' with a
declared reason, never 'supported' and never 'conflicting'. The choices of the record (sample format, experiment format, readout, spread kind) hold no span, so no
criterion rests on a choice alone; the uses of a choice are that an isothermal-only experiment is 'not_applicable' for the melt-curve criterion, a melt-curve-only experiment is 'not_applicable' for the two
isothermal criteria and a lysate is 'not_applicable' for the cell-integrity criterion, in each case only when their own fact is not stated (declared reasons that decide nothing about the experiment's quality).

What the claim is. The experiment is judged by how well it supports "this compound binds this target protein in the cell or lysate" (a thermal stabilisation of the target, with its size, or an EC50).
The controls (a vehicle control, a loading control, a control of the total target, a negative compound, a specificity control such as a binding-site mutant or a competition, a melt curve of enough temperatures,
an isothermal temperature in the transition, a dose-response of enough concentrations on both sides of the EC50, viable cells, independent experiments) decide how much that means. The EC50 is an apparent constant
derived from the thermal shift at one temperature and one heating time, not an equilibrium dissociation constant; the criterion that needs it (the concentration range relative to the EC50) is 'not_applicable' for a record that
reports no EC50 ('no_apparent_engagement_constant_reported').

Terms. Thermal shift: the melting temperature with the compound minus the melting temperature without it, in degrees Celsius (the stated shift, or the difference of the two stated melting temperatures). Concentration range over the EC50: the lowest and
the highest compound concentration divided by the EC50.

Added after the range review (grader gaps, 2026-11-21): thermal_shift also reads the stated standard deviation of the Tm (tm_spread) and whether it is over independent experiments; temperature_series also reads the ends of the temperature range and the stated Tm values (is the Tm inside the sampled range); isothermal_window also reads the isothermal temperature and the Tm without the compound. The grader only records these numbers; the sheet judges them.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the heating time, the compound incubation time, the sample format, the readout,
the spread of the EC50 and its kind.
"""

VERSION = 'a105_cetsa_criteria_v1'

# ---- Threshold constants -------------------------------------------------
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.


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


def _format_fact(criterion_id, question, fact_name, format_reason, format_name):
    return {'id': criterion_id, 'question': question, 'reads': ('facts.' + fact_name,),
            'rule': 'The one fact decides: yes supported, no fails, not_applicable not applicable. An unknown fact is unknown, or not applicable when ' + format_name + ' (the criterion belongs to the other format).',
            'thresholds': (),
            'returns': (
                ('supported', 'facts_answered_yes', 'answer yes'),
                ('conflicting', 'fact_answered_no', 'answer no'),
                ('unknown', 'fact_unknown', 'answer unknown and ' + format_name + ' is not the case'),
                ('not_applicable', format_reason, 'answer unknown and ' + format_name),
                ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
            )}


# ---- The criteria --------------------------------------------------------
CETSA_CRITERIA = (
    _one_fact('engagement_observed', 'Did the compound stabilise the target against heat (a thermal stabilisation that shows target engagement)?', 'target_engagement_shown'),
    {
        'id': 'thermal_shift',
        'question': 'Did the melt curve of the target shift to a higher temperature with the compound, and by more than the scatter of the melting temperature?',
        'reads': ('quantities.tm_shift', 'quantities.tm_ligand', 'quantities.tm_vehicle', 'quantities.tm_spread', 'facts.tm_spread_over_independent_experiments'),
        'rule': 'When the shift is stated, or the two melting temperatures (with and without the compound) are both stated, the grader records the shift in degrees Celsius (shift_celsius) and the refs of the values it comes from (shift_refs; a stated shift wins over a difference) and leaves the judgement to the sheet; when a standard deviation of the Tm is also stated it records that too (tm_spread_c), the answer of the fact that says whether it is over independent experiments (tm_spread_independent) and the refs of all of them (shift_spread_refs); otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'thermal_shift_recorded_for_the_sheet', 'a shift, or both melting temperatures, are stated: the shift is recorded and the sheet judges it'),
            ('unknown', 'thermal_shift_not_given', 'neither a shift nor both melting temperatures are stated'),
        ),
    },
    _one_fact('vehicle_control', 'Was a control sample without the compound (vehicle) heated and read in the same way?', 'vehicle_control_done'),
    _one_fact('loading_control', 'Was a loading control used (the same amount of sample was read)?', 'loading_control_used'),
    {
        'id': 'temperature_series',
        'question': 'Was the melt curve measured at enough temperatures to define the transition?',
        'reads': ('quantities.temperature_count', 'facts.melt_curve_measured', 'quantities.temperature_lowest', 'quantities.temperature_highest', 'quantities.tm_vehicle', 'quantities.tm_ligand'),
        'rule': 'The fact stated as no fails. Otherwise a stated number of temperatures is recorded (temperature_count, temperature_count_refs) and the judgement is left to the sheet; when both ends of the sampled range and at least one melting temperature are stated, the distances of the lowest and the highest stated Tm from the two ends are recorded too (temperature_margin_low_c, temperature_margin_high_c, temperature_bracket_refs); with no number the fact decides: yes supported, not_applicable not applicable, unknown unknown, or not applicable when the experiment format is stated as an isothermal dose-response only (it has no melt curve).',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'temperature_count_recorded_for_the_sheet', 'the fact is not no and a count is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, no count is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no count is stated, the fact is unknown and the format is not stated as isothermal only'),
            ('not_applicable', 'isothermal_format_has_no_melt_curve', 'no count is stated, the fact is unknown and the format is stated as an isothermal dose-response only'),
            ('not_applicable', 'fact_not_applicable', 'no count is stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'isothermal_window',
        'question': 'Was the isothermal temperature chosen in the transition of the unbound target (a window between the unbound and the bound target)?',
        'reads': ('facts.isothermal_temperature_in_window', 'quantities.isothermal_temperature', 'quantities.tm_vehicle'),
        'rule': 'The fact stated as no fails. Otherwise, when the isothermal temperature and the melting temperature without the compound are both stated, the grader records their difference (isothermal_over_tm_c, isothermal_window_refs) and leaves the judgement to the sheet; with no such numbers the fact decides: yes supported, unknown unknown, not_applicable not applicable, or not applicable when the fact is unknown and the experiment format is stated as a melt curve only (it has no isothermal temperature).',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'isothermal_window_recorded_for_the_sheet', 'the fact is not no and both temperatures are stated: their difference is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is yes and the numbers are not both stated'),
            ('unknown', 'fact_unknown', 'the fact is unknown, the numbers are not both stated and the format is not stated as a melt curve only'),
            ('not_applicable', 'melt_curve_format_has_no_isothermal_temperature', 'the fact is unknown, the numbers are not both stated and the format is stated as a melt curve only'),
            ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
        ),
    },
    {
        'id': 'dose_response',
        'question': 'Was the stabilisation followed over enough compound concentrations to show a dose dependence?',
        'reads': ('quantities.concentration_count', 'facts.dose_dependent_shown'),
        'rule': 'The fact stated as no fails. Otherwise a stated number of compound concentrations is recorded (concentration_count, concentration_count_refs) and the judgement is left to the sheet; with no number the fact decides: yes supported, not_applicable not applicable, unknown unknown, or not applicable when the experiment format is stated as a melt curve only (it has no dose-response).',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'concentration_count_recorded_for_the_sheet', 'the fact is not no and a count is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, no count is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no count is stated, the fact is unknown and the format is not stated as a melt curve only'),
            ('not_applicable', 'melt_curve_format_has_no_dose_response', 'no count is stated, the fact is unknown and the format is stated as a melt curve only'),
            ('not_applicable', 'fact_not_applicable', 'no count is stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'concentration_range',
        'question': 'Did the compound concentrations span the EC50 (some well below it, some well above it)?',
        'reads': ('quantities.compound_concentration_lowest', 'quantities.compound_concentration_highest', 'quantities.engagement_ec50'),
        'rule': 'With no EC50 reported the criterion does not apply. When the lowest concentration, the highest one and the EC50 are all stated, the grader records the two quotients (low_over_ec50, high_over_ec50) and the refs of the three (range_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_range_recorded_for_the_sheet', 'an EC50 is reported and both ends of the range are stated: the quotients are recorded and the sheet judges them'),
            ('unknown', 'concentration_range_not_given', 'an EC50 is reported and the two ends of the range are not both stated'),
            ('not_applicable', 'no_apparent_engagement_constant_reported', 'no EC50 is reported'),
        ),
    },
    _one_fact('negative_control', 'Did a negative compound (an inactive analogue or a non-binder) fail to stabilise the target?', 'negative_control_done'),
    _one_fact('specificity_control', 'Did a specificity control (a binding-site mutant, a competition, a knockdown of the target) show that the stabilisation depends on binding to the target?', 'specificity_control_done'),
    _format_fact('cell_integrity', 'Were the viability or integrity of the cells, or the uptake of the compound, checked?', 'cell_integrity_checked', 'lysate_has_no_living_cells', 'the sample is stated as a cell lysate'),
    _one_fact('total_level_control', 'Was the total amount of the target shown not to be changed by the compound (the stabilisation is not a change of the expression)?', 'total_target_level_controlled'),
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Wells or tubes of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
