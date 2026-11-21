"""SEC criteria: the ONE place where the size-exclusion chromatography (SEC, gel filtration; with or without multi-angle light scattering, SEC-MALS) complex grader's criteria and thresholds are declared (two proteins are mixed and run on a size-exclusion column; the complex elutes earlier than either component alone, in a co-elution peak that shows both partners on SDS-PAGE; SEC-MALS gives the molar mass of the complex; mostly qualitative or semi-quantitative, occasionally an apparent KD from peak areas).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the SEC grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the elution shift, the stoichiometry, the salt, the load over the KD,
the polydispersity, the replicate count, the mass deviation), the grader records the number with its support refs and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_sec_converter.py.
The logic that answers each question is in literature_sec_grader.py (one short function per criterion, same order). The only constants left
here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in SEC_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_sec_record.py)
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
declared reason, never 'supported' and never 'conflicting'. The choices of the record (column type, detector, spread kind) hold no span, so no
criterion rests on a choice alone.

What the claim is. The experiment is judged by how well it supports "these two proteins form a complex in solution". An SEC is mostly QUALITATIVE
or semi-quantitative: it says that the mixture elutes as a peak earlier than each component alone (the complex peak) and that the peak holds both
partners (SDS-PAGE), and, with MALS, that the molar mass of the peak is that of the complex. The controls (each component alone on the same column, a
single-component control, a buffer that rules out interaction with the resin, a calibrated column, no aggregation) decide how much that means. The
sample is DILUTED on the column (about ten- to twenty-fold), so a complex that is seen survived the dilution (that is evidence for it), while a weak
complex can be missed. When the mixture is titrated, the areas of the complex peak and of the free-component peak give an APPARENT KD. The criteria
that need a KD (the stability of the complex on the column and the stoichiometry) are 'not_applicable' for a record that reports no apparent KD
('no_apparent_kd_reported'): a qualitative complex peak has no constant that they could bias. A fact stated for the stability is still judged.


Terms. Elution volume: the volume that has passed through the column at the top of the peak; it depends on the hydrodynamic radius, not on mass alone.
Complex peak: the peak of the mixture that elutes earlier than each component alone. Shift: how much earlier (in millilitres) the complex peak elutes than the
component that elutes earlier alone. MALS molar mass: the absolute molar mass of the peak from light scattering and refractive index. Polydispersity: the ratio
Mw/Mn of the peak, close to 1 for a monodisperse peak. Stoichiometry: the molar ratio of the two components in the complex.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the elution volume of the later-eluting component alone, the
molar mass of the larger component alone, the flow rate, the temperature, the incubation before the injection, the column type, the detector,
the spread of the KD and its kind, and the statement that only this method was used.
"""

VERSION = 'a105_sec_criteria_v1'

# ---- Threshold constants -------------------------------------------------
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: percent per unit fraction (the mass deviation is recorded in percent).
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
MM_PER_SALT_UNIT = {'mM': 1.0, 'M': 1000.0}  # FIXED_BY_DEFINITION: millimolar per salt concentration unit.
ML_PER_VOLUME_UNIT = {'uL': 0.001, 'mL': 1.0}  # FIXED_BY_DEFINITION: millilitres per injected-volume unit (the column volume is stated in mL).


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
SEC_CRITERIA = (
    _one_fact('complex_peak_observed', 'Did the mixture elute as a complex peak, earlier than each component alone?', 'complex_peak_detected'),
    {
        'id': 'elution_shift',
        'question': 'Did the complex peak elute earlier than the component that elutes earlier alone by at least the minimum shift?',
        'reads': ('quantities.elution_volume_shift', 'quantities.complex_elution_volume', 'quantities.component_elution_volume_earlier', 'quantities.column_volume'),
        'rule': 'The shift is the stated shift, or when none is stated the elution volume of the earlier-eluting component alone minus the elution volume of the complex, when both are stated. The grader records the shift (shift_ml) and its refs (shift_refs) and leaves the judgement to the sheet; no shift stated and not both volumes stated is unknown. When a shift is recorded the stated column volume is recorded beside it (column_mL, column_refs), the scale the sheet reads the shift against when the earlier component\'s elution volume is not stated.',
        'thresholds': (),
        'returns': (
            ('unknown', 'elution_shift_recorded_for_the_sheet', 'a shift is stated or both elution volumes are stated: the shift is recorded and the sheet judges it'),
            ('unknown', 'elution_shift_not_given', 'no shift is stated and the two elution volumes are not both stated'),
        ),
    },
    _one_fact('components_alone', 'Was each component also run alone on the same column?', 'components_run_alone'),
    _one_fact('complex_composition', 'Did SDS-PAGE (or another analysis) of the complex peak show both proteins in it?', 'complex_peak_analysed_by_sds_page'),
    _one_fact('titration_depletion', 'Did the free-component peak get smaller as the complex peak grew when one component was increased?', 'free_peak_decreases_with_titration'),
    {
        'id': 'mals_mass',
        'question': 'Does the molar mass of the complex peak by MALS agree with the mass the complex should have?',
        'reads': ('quantities.complex_mass_measured', 'quantities.complex_mass_theoretical', 'quantities.component_mass_measured_smaller', 'facts.mals_mass_matches_complex'),
        'rule': 'The grader holds no threshold for the mass. When the measured and the theoretical mass of the complex are both stated, it records them as facts (mass_measured, mass_theoretical, mass_deviation_percent = (measured - theoretical) / theoretical * 100, signed, and the refs of the two spans in mass_support_refs) and leaves the judgement to the sheet side (the SEC converter). Otherwise the fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
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
        'question': 'Is the complex 1:1, so that an apparent KD from peak areas is the constant of one binding step?',
        'reads': ('quantities.stoichiometry_ratio', 'quantities.kd'),
        'rule': 'With no apparent KD reported the criterion does not apply. Otherwise the grader records the stated stoichiometry (stoichiometry_ratio) and its refs (stoichiometry_refs) and leaves the judgement to the sheet; none stated is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'stoichiometry_recorded_for_the_sheet', 'a KD is reported and a stoichiometry is stated: it is recorded and the sheet judges it'),
            ('unknown', 'stoichiometry_not_given', 'a KD is reported and no stoichiometry is stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    _one_fact('column_calibration', 'Was the column calibrated with standards of known size?', 'column_calibrated_with_standards'),
    {
        'id': 'resin_interaction',
        'question': 'Does the running buffer rule out interaction of the proteins with the resin?',
        'reads': ('facts.buffer_rules_out_resin_interaction', 'quantities.salt_concentration'),
        'rule': 'The fact decides: yes supported, no fails, not_applicable not applicable. When the fact is unknown and a salt concentration is stated, the grader records it (salt_mM, in mM, and salt_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('MM_PER_SALT_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'salt_recorded_for_the_sheet', 'the fact is unknown and a salt is stated: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'the fact is unknown and no salt is stated'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'complex_stable_on_column',
        'question': 'Was the complex stable on the column despite the dilution (the injected concentration well above the KD)?',
        'reads': ('quantities.loaded_concentration', 'quantities.kd', 'quantities.loaded_volume', 'quantities.column_volume', 'facts.complex_stable_on_column'),
        'rule': 'When the injected concentration and the KD are both stated, the grader records their quotient (load_over_kd) and the refs of the two (load_refs) and leaves the judgement to the sheet; it records beside it the injected volume and the column volume when stated (loaded_mL, loaded_refs, column_mL, column_refs), from which the sheet reads how far the sample is diluted on the column. Otherwise the fact decides: yes supported, no fails, not_applicable not applicable; an unknown fact is unknown, or not applicable when no apparent KD is reported.',
        'thresholds': ('NM_PER_UNIT', 'ML_PER_VOLUME_UNIT'),
        'returns': (
            ('unknown', 'load_over_kd_recorded_for_the_sheet', 'both are stated: the quotient is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'not both stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'not both stated and the fact is no'),
            ('unknown', 'fact_unknown', 'not both stated, the fact is unknown and a KD is reported'),
            ('not_applicable', 'no_apparent_kd_reported', 'not both stated, the fact is unknown and no KD is reported'),
            ('not_applicable', 'fact_not_applicable', 'not both stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'monodispersity',
        'question': 'Is the peak monodisperse (no aggregation that could be taken for a complex)?',
        'reads': ('quantities.polydispersity', 'facts.aggregation_absent'),
        'rule': 'A stated polydispersity is recorded (polydispersity, polydispersity_refs) and the judgement is left to the sheet. Otherwise the fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('unknown', 'polydispersity_recorded_for_the_sheet', 'a polydispersity is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'none stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'none stated and the fact is no'),
            ('unknown', 'fact_unknown', 'none stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'none stated and the fact is not_applicable'),
        ),
    },
    _one_fact('single_component_control', 'Did a control with a non-binding mutant or an unrelated protein in place of one partner fail to co-elute?', 'single_component_control_done'),
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Injections of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
