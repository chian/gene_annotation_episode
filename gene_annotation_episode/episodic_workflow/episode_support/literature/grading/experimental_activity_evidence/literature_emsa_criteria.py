"""EMSA criteria: the ONE place where the electrophoretic mobility shift assay (EMSA, gel shift) grader's criteria and thresholds are declared (a labelled nucleic acid probe incubated with a protein and run on a native gel; the complex migrates more slowly; qualitative, or a titration giving an apparent KD).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the EMSA grader asks. The grader reports FACTS and holds NO threshold
that judges goodness: where a criterion needs a number to be compared with a limit (the competitor excess, the incubation time, the probe over
the KD, the protein range over the KD, the number of titration points, the shifted fraction at the highest protein concentration, the number of
shifted species, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_emsa_converter.py. The logic that
answers each question is in literature_emsa_grader.py (one short function per criterion, same order). The only constants left here are unit
conversions (FIXED_BY_DEFINITION).

How to read an entry in EMSA_CRITERIA
-------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_emsa_record.py)
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
no constant is reported (the model has no span of its own: the span of the reported constant is its support), is 'unknown' or
'not_applicable' with a declared reason, never 'supported' and never 'conflicting'. The choices of the record (probe type, label, gel
type, competitor type, spread kind, fit model) hold no span, so no criterion rests on a choice alone.

What the claim is. The experiment is judged by how well it supports "this protein binds this nucleic acid sequence". An EMSA is often
QUALITATIVE: it says that a shifted band is seen, and the controls (competition by the specific and the non-specific competitor, a
mutant probe, the probe alone, a non-specific protein, the identity of the protein) decide how much that means. When the protein is
titrated, it also gives an APPARENT KD, with the caveats of the method: the gel is not at equilibrium during the run (a complex that
dissociates while it migrates is lost, and the cage effect of the gel holds a complex together that would fall apart in solution), the
probe concentration must be at or below the KD (above it the titration is stoichiometric and a quadratic model applies), and the
protein concentrations must span the KD. The criteria that need a KD (the probe concentration, the protein range, the number of
titration points, the plateau of the shifted fraction, the fit model) are 'not_applicable' for a record that reports no apparent KD
('no_apparent_kd_reported'): a qualitative shift has no constant that they could bias. A fact stated for the probe concentration or the
protein range is still judged.

Terms. Apparent KD: the protein concentration at which half of the probe is shifted, from the fraction of the probe in the shifted band
against the protein concentration (read by densitometry or phosphorimager). Specific competitor: the unlabelled (cold) probe of the same
sequence; non-specific competitor: an unrelated nucleic acid (for the non-specific competition control), distinct from the non-specific
nucleic acid poly(dI-dC) or salmon sperm DNA that is put in the reaction to absorb non-specific binding. Supershift: a further retarded band
or the loss of the shifted band when an antibody against the protein is added; it shows which protein is in the complex.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the probe type, length and label, the binding buffer (salt,
magnesium, glycerol), the type and the amount of the non-specific nucleic acid in the reaction, the temperature of the incubation, the gel type and
percent, the run (time, voltage, temperature), the spread of the KD and its kind, and the statement that only this method was used.
"""

VERSION = 'a105_emsa_criteria_v1'

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
EMSA_CRITERIA = (
    _one_fact('shift_observed', 'Was a shifted band seen with the protein and the probe?', 'shift_detected'),
    {
        'id': 'specific_competition',
        'question': 'Did an excess of the unlabelled specific probe abolish the shifted band?',
        'reads': ('facts.shift_abolished_by_specific_competitor', 'quantities.specific_competitor_excess'),
        'rule': 'The fact decides: yes supported, unknown unknown, not_applicable not applicable. A fact answered no fails when no fold excess is stated; when one is stated, the grader records it (specific_competitor_excess) with the refs of the fact (specific_competition_refs) and leaves the judgement to the sheet: a competitor in too small an excess is not a test of specificity.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no and no fold excess is stated'),
            ('unknown', 'competition_excess_recorded_for_the_sheet', 'answer no and a fold excess is stated: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('nonspecific_competition', 'Was the shifted band left in place by an excess of a non-specific (unrelated) competitor?', 'shift_not_abolished_by_nonspecific_competitor'),
    _one_fact('mutant_probe', 'Did a probe with the binding site mutated (or scrambled) fail to shift?', 'mutant_probe_does_not_shift'),
    _one_fact('probe_alone_lane', 'Was a lane of the labelled probe alone (without protein) shown?', 'probe_alone_lane_shown'),
    _one_fact('nonspecific_protein_control', 'Did a control with a non-specific protein (bovine serum albumin, or the tag alone) fail to shift the probe?', 'nonspecific_protein_control_done'),
    {
        'id': 'protein_identity',
        'question': 'Is the protein in the shifted complex known to be the protein under study (a purified protein, or a supershift with an antibody)?',
        'reads': ('facts.supershift_confirms_protein_identity', 'facts.protein_purified'),
        'rule': 'Either fact answered yes supported. Otherwise any unknown is unknown; otherwise either answered no fails (a crude extract and no confirming supershift); both not applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'protein_identity_confirmed', 'either fact answered yes'),
            ('conflicting', 'protein_identity_not_confirmed', 'no fact is yes or unknown and at least one is no'),
            ('unknown', 'protein_identity_unknown', 'no fact is yes and at least one is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts not_applicable'),
        ),
    },
    _one_fact('free_probe_quantified', 'Were the free and the shifted probe quantified (densitometry, phosphorimager) to give the shifted fraction?', 'free_probe_quantified'),
    {
        'id': 'equilibrium',
        'question': 'Had the binding reached equilibrium before the gel was loaded?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time'),
        'rule': 'The fact decides: yes supported, no fails, not_applicable not applicable. When the fact is unknown and an incubation time is stated, the grader records it (incubation_min, in minutes, and incubation_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'the fact is unknown and an incubation time is stated: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'the fact is unknown and no incubation time is stated'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('complex_stability', 'Was the complex stable during the gel run (no smear between the shifted band and the free probe)?', 'complex_survives_gel_run'),
    {
        'id': 'probe_concentration',
        'question': 'Was the probe concentration at or below the KD, so that the titration is not stoichiometric?',
        'reads': ('quantities.probe_concentration', 'quantities.kd', 'facts.probe_at_or_below_kd'),
        'rule': 'When both the probe concentration and the KD are stated, the grader records their quotient (probe_over_kd) and the refs of the two (probe_over_kd_refs) and leaves the judgement to the sheet. Otherwise the fact decides: yes supported, no fails, not_applicable not applicable; an unknown fact is unknown, or not applicable when no apparent KD is reported.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'probe_over_kd_recorded_for_the_sheet', 'both are stated: the quotient is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'not both stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'not both stated and the fact is no'),
            ('unknown', 'fact_unknown', 'not both stated, the fact is unknown and a KD is reported'),
            ('not_applicable', 'no_apparent_kd_reported', 'not both stated, the fact is unknown and no KD is reported'),
            ('not_applicable', 'fact_not_applicable', 'not both stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'protein_range',
        'question': 'Did the protein concentrations of the titration span the KD (from well below it to a saturating concentration)?',
        'reads': ('quantities.protein_concentration_lowest', 'quantities.protein_concentration_highest', 'quantities.kd', 'facts.protein_range_brackets_kd'),
        'rule': 'When the lowest and the highest protein concentration and the KD are all stated, the grader records the lowest and the highest over the KD (protein_low_over_kd, protein_high_over_kd) and the refs of the three (protein_range_refs) and leaves the judgement to the sheet. Otherwise the fact decides: yes supported, no fails, not_applicable not applicable; an unknown fact is unknown, or not applicable when no apparent KD is reported.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'protein_range_recorded_for_the_sheet', 'all three are stated: the two quotients are recorded and the sheet judges them'),
            ('supported', 'facts_answered_yes', 'not all three stated and the fact is yes'),
            ('conflicting', 'fact_answered_no', 'not all three stated and the fact is no'),
            ('unknown', 'fact_unknown', 'not all three stated, the fact is unknown and a KD is reported'),
            ('not_applicable', 'no_apparent_kd_reported', 'not all three stated, the fact is unknown and no KD is reported'),
            ('not_applicable', 'fact_not_applicable', 'not all three stated and the fact is not_applicable'),
        ),
    },
    {
        'id': 'titration_points',
        'question': 'Did the titration have enough protein concentrations to define the curve?',
        'reads': ('quantities.titration_point_count', 'quantities.kd'),
        'rule': 'With an apparent KD reported, the stated number of protein concentrations is recorded (titration_point_count, titration_point_refs) and the judgement is left to the sheet. Not given is unknown. With no apparent KD reported the criterion does not apply.',
        'thresholds': (),
        'returns': (
            ('unknown', 'titration_points_recorded_for_the_sheet', 'a KD is reported and a number of points is stated: it is recorded and the sheet judges it'),
            ('unknown', 'titration_point_count_not_given', 'a KD is reported and no number of points is stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    {
        'id': 'saturation',
        'question': 'Did the shifted fraction reach a plateau at the highest protein concentration?',
        'reads': ('quantities.fraction_shifted_highest', 'quantities.kd'),
        'rule': 'With an apparent KD reported, the percent of the probe shifted at the highest protein concentration is recorded (fraction_shifted_percent, fraction_shifted_refs) and the judgement is left to the sheet. Not given is unknown. With no apparent KD reported the criterion does not apply.',
        'thresholds': (),
        'returns': (
            ('unknown', 'fraction_shifted_recorded_for_the_sheet', 'a KD is reported and a shifted fraction is stated: it is recorded and the sheet judges it'),
            ('unknown', 'fraction_shifted_not_given', 'a KD is reported and no shifted fraction is stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    {
        'id': 'single_complex',
        'question': 'Was there one shifted species, or, if several, was a model with more than one site used?',
        'reads': ('quantities.shifted_species_count', 'quantities.kd'),
        'rule': 'A stated number of shifted species is recorded (shifted_species_count, with its refs in shifted_species_refs, and with the refs of the KD added in shifted_species_kd_refs) and the judgement is left to the sheet: one species is supported; with more and an apparent KD reported, a one-site or quadratic fit model fails, a stated Hill, two-site or other model is supported, and no stated model is unknown; with no KD reported it does not apply. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'shifted_species_recorded_for_the_sheet', 'a number of shifted species is stated: it is recorded and the sheet judges it'),
            ('unknown', 'shifted_species_count_not_given', 'no number of shifted species is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the model that gave the apparent KD stated, and suited to the probe concentration (a one-site model only when the probe is at or below the KD)?',
        'reads': ('fit_model', 'quantities.kd', 'quantities.probe_concentration'),
        'rule': 'With no apparent KD reported the criterion does not apply. Otherwise no stated model is unknown; a one-site model with a stated probe concentration is handed to the sheet with the probe over the KD (probe_over_kd, fit_model_probe_refs), which judges it (a quadratic model is needed for tight binding); any other stated model is supported, its support being the span of the KD.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a KD is reported, a fit model is stated, and it is not a one-site model with a stated probe concentration'),
            ('unknown', 'one_site_probe_over_kd_recorded_for_the_sheet', 'a KD is reported, the model is one_site and the probe concentration is stated: the quotient is recorded and the sheet judges it'),
            ('unknown', 'fit_model_not_stated', 'a KD is reported and no fit model is stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Lanes of one gel are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
