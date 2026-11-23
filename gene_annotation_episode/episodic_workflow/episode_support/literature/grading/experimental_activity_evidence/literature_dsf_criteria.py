"""DSF criteria: the ONE place where the thermal shift (differential scanning fluorimetry, DSF, and nanoDSF) grader's criteria and thresholds are declared (a protein is heated while its unfolding is followed with a dye or by its intrinsic fluorescence; the melting temperature Tm is read alone and with a ligand; the ligand-induced shift delta Tm shows binding only indirectly; mostly qualitative, occasionally an apparent KD from a series of ligand concentrations).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the DSF grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the size of the shift, the shift over the scatter of the Tm, the number of ligand concentrations, the ligand range
relative to the apparent KD, the heating rate, the replicate count), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_dsf_converter.py.
The logic that answers each question is in literature_dsf_grader.py (one short function per criterion, same order). The only constants left
here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in DSF_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_dsf_record.py)
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
declared reason, never 'supported' and never 'conflicting'. The choices of the record (readout, Tm method, spread kind) hold no span, so no criterion rests on a choice.

What the claim is. The experiment is judged by how well it supports "this ligand binds this protein", knowing that a thermal shift shows binding only INDIRECTLY (a ligand can raise the Tm without
binding the site of interest, a ligand that binds the folded and the unfolded protein equally shifts nothing, and the shift of a destabilising ligand is not a stabilisation). The criteria are the shift itself (a rise of the Tm: its size and its size over the scatter of the Tm),
the controls (the protein alone in the same buffer and vehicle, the ligand with the dye and no protein), the quality of the melt curve and the heating rate, the concentration dependence of the shift (a series of ligand concentrations, a shift that grows with the concentration and,
for an apparent KD, concentrations on both sides of it) and the number of independent experiments. The criterion that needs a KD (the ligand range relative to the KD) is 'not_applicable' for a record that reports no KD ('no_apparent_kd_reported').

Terms. Melting temperature Tm: the midpoint of the unfolding transition. Thermal shift delta Tm: Tm with the ligand minus Tm without the ligand, in degrees Celsius, SIGNED (a rise is positive); the grader takes the stated shift, or, when the
passage states no shift but states both Tm values, their difference. Shift over spread: the signed shift divided by the stated standard deviation of the Tm. Ligand range over the KD: the lowest and the highest ligand concentration divided by the apparent KD.
Heating rate: degrees Celsius per minute.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the Tagg of nanoDSF, the readout, the way the Tm was read, the spread of the KD and its kind.
"""

VERSION = 'a105_dsf_criteria'

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


# ---- The criteria --------------------------------------------------------
DSF_CRITERIA = (
    _one_fact('shift_observed', 'Did the ligand raise the melting temperature of the protein?', 'thermal_shift_observed'),
    {
        'id': 'shift_size',
        'question': 'Is the thermal shift (delta Tm, signed) at least the minimum shift?',
        'reads': ('quantities.delta_tm', 'quantities.tm_apo', 'quantities.tm_ligand', 'quantities.shift_ligand_concentration', 'quantities.kd'),
        'rule': 'When the passage states the shift, or states the Tm alone and the Tm with the ligand (their difference is the shift), the grader records the signed shift in degrees Celsius (thermal_shift_c) and its refs (thermal_shift_refs) and leaves the judgement to the sheet; otherwise unknown. When the ligand concentration at which the shift was read and an apparent KD are both stated, it also records their quotient (shift_concentration_over_kd) and the refs of the two (shift_concentration_refs): the shift grows with the occupancy, so the sheet reads the size of the shift against it.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'thermal_shift_recorded_for_the_sheet', 'a shift is stated, or both Tm values are: the signed shift is recorded and the sheet judges it'),
            ('unknown', 'thermal_shift_not_given', 'no shift is stated and the two Tm values are not both stated'),
        ),
    },
    {
        'id': 'shift_over_spread',
        'question': 'Is the thermal shift larger than the scatter of the Tm?',
        'reads': ('quantities.delta_tm', 'quantities.tm_apo', 'quantities.tm_ligand', 'quantities.tm_spread', 'facts.tm_spread_over_independent_experiments'),
        'rule': 'When the signed shift is known (as for shift_size) and a standard deviation of the Tm is stated, the grader records the quotient (shift_over_spread), the standard deviation itself (tm_spread_c), the answer of the fact that says whether that standard deviation is over independent experiments or only over wells of one plate (tm_spread_independent) and the refs of all of them (shift_spread_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'shift_over_spread_recorded_for_the_sheet', 'the shift and the spread are known: the quotient is recorded and the sheet judges it'),
            ('unknown', 'shift_over_spread_not_given', 'the shift or the spread is not known'),
        ),
    },
    _one_fact('protein_alone_control', 'Was the protein also measured without the ligand in the same buffer and vehicle, as the reference of the shift?', 'protein_alone_control_done'),
    _one_fact('ligand_alone_control', 'Was the ligand also measured with the dye and without the protein, and gave no signal of its own?', 'ligand_alone_control_done'),
    _one_fact('curve_quality', 'Were the melt curves clean sigmoids with one unfolding transition?', 'melt_curve_sigmoidal'),
    _one_fact('dose_dependence', 'Did the shift grow with the ligand concentration?', 'shift_dose_dependent'),
    {
        'id': 'concentration_series',
        'question': 'Was the shift measured at enough ligand concentrations to show its concentration dependence?',
        'reads': ('quantities.ligand_concentration_count', 'facts.ligand_titration_measured'),
        'rule': 'The fact stated as no (no titration: a single-concentration screen) is a weakness, not opposition: the grader records the stated count, or one concentration when none is stated (concentration_count, concentration_count_refs: the fact) and leaves the judgement to the sheet. Otherwise a stated number of ligand concentrations is recorded the same way; with no number the fact decides: yes supported, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('unknown', 'single_concentration_recorded_for_the_sheet', 'the fact is no: a single concentration (or the stated count) is recorded and the sheet judges it'),
            ('unknown', 'concentration_count_recorded_for_the_sheet', 'the fact is not no and a count is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, no count is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no count is stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no count is stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'concentration_range',
        'question': 'Did the ligand concentrations span the apparent KD (some well below it, some well above it)?',
        'reads': ('quantities.ligand_concentration_lowest', 'quantities.ligand_concentration_highest', 'quantities.kd', 'quantities.protein_concentration'),
        'rule': 'With no KD reported the criterion does not apply. When the lowest ligand concentration, the highest one and the KD are all stated, the grader records the two quotients (low_over_kd, high_over_kd) and the refs of the three (range_refs) and leaves the judgement to the sheet; otherwise unknown. When the protein concentration is also stated, it records the KD over the protein concentration (kd_over_protein, refs added to range_refs): a KD far below the protein concentration is limited by the titration.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_range_recorded_for_the_sheet', 'a KD is reported and both ends of the range are stated: the quotients are recorded and the sheet judges them'),
            ('unknown', 'concentration_range_not_given', 'a KD is reported and the two ends of the range are not both stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    {
        'id': 'heating_rate',
        'question': 'Was the sample heated slowly enough for the Tm to be near the equilibrium unfolding?',
        'reads': ('quantities.heating_rate',),
        'rule': 'A stated heating rate is recorded (heating_rate_c_per_min, heating_rate_refs) and the judgement is left to the sheet; none stated is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'heating_rate_recorded_for_the_sheet', 'a heating rate is stated: it is recorded and the sheet judges it'),
            ('unknown', 'heating_rate_not_given', 'no heating rate is stated'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Wells of one plate are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
