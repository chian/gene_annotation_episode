"""AUC criteria: the ONE place where the analytical ultracentrifugation (AUC: sedimentation velocity and sedimentation equilibrium) grader's criteria and thresholds are declared (a protein, or a mixture of two proteins, is spun in an analytical ultracentrifuge; in velocity runs the sedimentation coefficient s of each species is read from c(s) or a Lamm fit and a complex sediments faster than either component alone, with a molar mass from the fit; in equilibrium runs a global fit of several concentrations and speeds gives the mass, the stoichiometry and, for a reversible association, the KD; mostly qualitative or semi-quantitative, occasionally a KD from a concentration series).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the AUC grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the s shift of the complex, the mass deviation, the stoichiometry, the number of
loading concentrations, the loading range relative to the KD, the fit residual, the replicate count), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_auc_converter.py.
The logic that answers each question is in literature_auc_grader.py (one short function per criterion, same order). The only constants left
here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in AUC_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_auc_record.py)
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
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' or 'not_applicable' with a
declared reason, never 'supported' and never 'conflicting'. The choices of the record (run mode, analysis model, detection, spread kind) hold no span, so no
criterion rests on a choice alone; the one use of a choice is that a velocity-only run is 'not_applicable' for the two equilibrium criteria when their fact is not stated
('velocity_run_has_no_equilibrium_criterion'), a declared reason that decides nothing about the experiment's quality.

What the claim is. The experiment is judged by how well it supports "these two proteins form a complex in solution" (a complex peak at a larger s, a mass
of the complex, a stoichiometry, a KD from a concentration series). The controls (each component alone under the same conditions, each component homogeneous, a
non-binding mutant, a concentration series that shows a reversible association, equilibrium reached, several speeds, a corrected buffer density and viscosity, a fit with random
small residuals) decide how much that means. The criteria that need a KD (the stoichiometry and the loading range relative to the KD) are 'not_applicable' for a record that
reports no KD ('no_apparent_kd_reported').

Terms. Sedimentation coefficient s (Svedberg, S): the sedimentation velocity per unit centrifugal field. Shift: how much larger, in percent, the s of the complex peak is than the s of the
larger component alone ((complex - larger) / larger * 100, signed). Mass deviation: (measured - theoretical) / theoretical * 100, signed. Loading range over the KD: the
lowest and the highest loading concentration divided by the KD. Fit rmsd: the root mean square deviation of the fit (absorbance units or fringes).

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the s of the smaller component alone, the frictional ratio, the rotor speed, the temperature,
the run mode, the analysis model, the detection, the spread of the KD and its kind, and the statement that only this method was used.
"""

VERSION = 'a105_auc_criteria'

# ---- Threshold constants -------------------------------------------------
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: percent per unit fraction (the shift and the mass deviation are recorded in percent).
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


def _equilibrium_fact(criterion_id, question, fact_name):
    return {'id': criterion_id, 'question': question, 'reads': ('facts.' + fact_name,),
            'rule': 'The one fact decides: yes supported, no fails, not_applicable not applicable. An unknown fact is unknown, or not applicable when the run mode is stated as sedimentation velocity only (a velocity run has no equilibrium to reach and no speeds to compare).',
            'thresholds': (),
            'returns': (
                ('supported', 'facts_answered_yes', 'answer yes'),
                ('conflicting', 'fact_answered_no', 'answer no'),
                ('unknown', 'fact_unknown', 'answer unknown and the run mode is not stated as sedimentation velocity'),
                ('not_applicable', 'velocity_run_has_no_equilibrium_criterion', 'answer unknown and the run mode is sedimentation velocity'),
                ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
            )}


# ---- The criteria --------------------------------------------------------
AUC_CRITERIA = (
    _one_fact('complex_observed', 'Did the mixture show a complex (a peak or a species at a larger sedimentation coefficient than either component alone)?', 'complex_detected'),
    {
        'id': 'sedimentation_shift',
        'question': 'Did the complex sediment faster than the larger component alone by at least the minimum shift?',
        'reads': ('quantities.complex_sedimentation_coefficient', 'quantities.component_sedimentation_coefficient_larger', 'quantities.component_mass_larger', 'quantities.component_mass_smaller'),
        'rule': 'When the s of the complex and the s of the larger component alone are both stated, the grader records the shift in percent (shift_percent, signed) and the refs of the two (shift_refs) and leaves the judgement to the sheet; when the masses of both components are also stated it records them (component_mass_larger, component_mass_smaller) and adds their refs, so that the sheet can read the shift against the partner size; otherwise unknown.',
        'thresholds': ('PERCENT_PER_FRACTION',),
        'returns': (
            ('unknown', 'sedimentation_shift_recorded_for_the_sheet', 'both s values are stated: the shift is recorded and the sheet judges it'),
            ('unknown', 'sedimentation_shift_not_given', 'the two s values are not both stated'),
        ),
    },
    _one_fact('components_alone', 'Was each component also run alone under the same conditions?', 'components_run_alone'),
    _one_fact('component_homogeneity', 'Was each component homogeneous alone (a single species, no aggregate or self-association that could be taken for a complex)?', 'components_monodisperse'),
    {
        'id': 'mass',
        'question': 'Does the molar mass of the complex from the AUC fit agree with the mass the complex should have?',
        'reads': ('quantities.complex_mass_measured', 'quantities.complex_mass_theoretical', 'quantities.component_mass_smaller', 'facts.mass_matches_complex'),
        'rule': 'The grader holds no threshold for the mass. When the measured and the theoretical mass of the complex are both stated, it records them as facts (mass_measured, mass_theoretical, mass_deviation_percent = (measured - theoretical) / theoretical * 100, signed, and the refs of the two spans in mass_support_refs; with the mass of the smaller component, when stated, as mass_smaller_component and its ref added) and leaves the judgement to the sheet side (the AUC converter). Otherwise the fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': ('PERCENT_PER_FRACTION',),
        'returns': (
            ('unknown', 'mass_deviation_recorded_for_the_sheet', 'both masses are stated: the deviation is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'not both stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'not both stated and the fact is no'),
            ('unknown', 'fact_unknown', 'not both stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'not both stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'stoichiometry',
        'question': 'Is the complex 1:1, so that a KD is the constant of one binding step?',
        'reads': ('quantities.stoichiometry_ratio', 'quantities.kd'),
        'rule': 'With no KD reported the criterion does not apply. Otherwise the grader records the stated stoichiometry (stoichiometry_ratio) and its refs (stoichiometry_refs) and leaves the judgement to the sheet; none stated is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'stoichiometry_recorded_for_the_sheet', 'a KD is reported and a stoichiometry is stated: it is recorded and the sheet judges it'),
            ('unknown', 'stoichiometry_not_given', 'a KD is reported and no stoichiometry is stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Was the experiment run at enough loading concentrations to show the concentration dependence of a reversible association?',
        'reads': ('quantities.concentration_count', 'facts.concentration_series_measured'),
        'rule': 'A stated number of loading concentrations is recorded (concentration_count, concentration_count_refs) and the judgement is left to the sheet. With no number, the fact stated as no is a series of one (count 1, the fact\'s refs), recorded the same way: a short series is less evidence, not evidence against. Otherwise the fact decides: yes supported, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('unknown', 'concentration_count_recorded_for_the_sheet', 'a count is stated, or the fact is no (a series of one): it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'no count is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no count is stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no count is stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'concentration_range',
        'question': 'Did the loading concentrations span the KD (some well below it, some well above it)?',
        'reads': ('quantities.loaded_concentration_lowest', 'quantities.loaded_concentration_highest', 'quantities.kd'),
        'rule': 'With no KD reported the criterion does not apply. When the lowest loading concentration, the highest one and the KD are all stated, the grader records the two quotients (low_over_kd, high_over_kd) and the refs of the three (range_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_range_recorded_for_the_sheet', 'a KD is reported and both ends of the range are stated: the quotients are recorded and the sheet judges them'),
            ('unknown', 'concentration_range_not_given', 'a KD is reported and the two ends of the range are not both stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    _one_fact('reversibility', 'Did the sedimentation (the weight-average s or the mass) change with the loading concentration, or did a global fit hold, as for a reversible association?', 'reversible_association_shown'),
    _equilibrium_fact('equilibrium_reached', 'In a sedimentation equilibrium run, was equilibrium reached (successive scans overlay)?', 'equilibrium_reached_shown'),
    _equilibrium_fact('multiple_speeds', 'In a sedimentation equilibrium run, were several rotor speeds fitted together?', 'multiple_speeds_used'),
    {
        'id': 'fit_quality',
        'question': 'Does the fit describe the data (random residuals and a small rmsd)?',
        'reads': ('quantities.fit_rmsd', 'facts.fit_residuals_random'),
        'rule': 'Residuals stated as not random fail (a fact). Otherwise a stated rmsd is recorded (fit_rmsd, fit_rmsd_unit, fit_refs) and the judgement is left to the sheet; with no rmsd the fact decides: yes supported, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the residuals are stated as not random'),
            ('unknown', 'fit_rmsd_recorded_for_the_sheet', 'the fact is not no and an rmsd is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, no rmsd is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no rmsd is stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no rmsd is stated and the fact is not_applicable'),
        ),
    },
    _one_fact('buffer_correction', 'Were the buffer density and viscosity (and the partial specific volume) used for the standard s and the mass?', 'buffer_density_viscosity_corrected'),
    _one_fact('non_binding_control', 'Did a control with a non-binding mutant or an unrelated protein in place of one partner fail to form the complex?', 'non_binding_control_done'),
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Scans of one cell are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
