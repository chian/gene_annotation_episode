"""ELISA criteria: the ONE place where the ELISA-style binding grader's criteria and thresholds are declared (plate-based solid-phase binding: direct, indirect or sandwich ELISA, or a competition ELISA).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the ELISA grader asks. The grader reports FACTS and holds NO threshold that
judges goodness: where a criterion needs a number to be compared with a limit (the signal over the background, the plateau absorbance, the
incubation, the concentration count and span, the agreement of the KD and the Ki, the replicate count), the grader records the number with its
support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the
sheet side, in literature_elisa_converter.py. The logic that answers each question is in literature_elisa_grader.py (one short function per
criterion, same order). The only constants left here are unit conversions (FIXED_BY_DEFINITION).

Support rule (from the ELISA work, designed in from the start): a criterion returns 'supported' or 'conflicting' only with support refs, the
quoted source spans of the stated fields it rests on. A decision that rests on a fact or a choice that holds no span (the fit model with no
reported constant) is 'unknown' with a declared reason, never 'supported' and never 'conflicting'.

How to read an entry in ELISA_CRITERIA
--------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_elisa_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Constants: each is defined once, below, and marked FIXED_BY_DEFINITION (a unit conversion, not a judgment).

Terms. The reported constant of a series: the apparent KD of a saturation
titration, else the Ki, else the EC50 or the IC50 (native 'constant_name' says
which). Apparent KD: the KD read from a heterogeneous assay with wash steps; a
complex that dissociates during the washes is lost from the signal, so the number
is an upper bound of the equilibrium KD, not the equilibrium KD in solution. EC50
and IC50: half-maximal concentrations of a curve; they are not dissociation
constants (an EC50 depends on the coating and on the detection; an IC50 on the
concentration of the ligand it competes with) and are never carried as a binding
constant. Avidity: the multivalent binding of a multivalent coating or ligand (a
dimer, an antibody, an oligomer), which gives an apparent KD far below the
monovalent one. Signal window: the absorbance of the plateau over that of the
background wells (the blank, no-coat or no-ligand wells).

What this method does not ask (items of the other binding experiments left out
because a plate assay has no such thing): a sensorgram baseline, mass transport,
a regeneration, the kinetic rate constants, a labelled partner held below the KD,
the particle number of a confocal volume and the donor and the acceptor of FRET.
The coating concentration, the number of washes, the number of technical wells,
the temperature, the readout, the enzyme, the blocking agent, the detection
format, the spread and the statement that only this method was used are kept in
the record for the reviewer; no criterion judges them.
"""

VERSION = 'a105_elisa_criteria'

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
ELISA_CRITERIA = (
    {
        'id': 'signal_window',
        'question': 'Is the plateau absorbance high enough over the background wells to define the binding curve?',
        'reads': ('quantities.signal_maximum', 'quantities.signal_background'),
        'rule': 'The grader records the plateau absorbance over the background absorbance (signal_over_background) and the refs of the two (signal_window_refs) and leaves the judgement to the sheet. Either number not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'signal_window_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'signal_or_background_not_given', 'the plateau or the background absorbance is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'detector_range',
        'question': 'Was the signal within the linear range of the plate reader?',
        'reads': ('facts.signal_in_linear_range', 'quantities.signal_maximum', 'quantities.detector_linear_limit'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and a plateau absorbance is given, the grader records it (plateau_absorbance and plateau_refs) together with the reader linear limit the paper states, if any (detector_linear_limit and linear_limit_refs), and leaves the judgement to the sheet; no plateau given is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'plateau_recorded_for_the_sheet', 'not stated and a plateau absorbance is given: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no plateau absorbance'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('saturation', 'Did the binding curve reach a plateau within the concentrations used?', 'saturation_reached'),
    _one_fact('blank_subtraction', 'Was the signal of the blank wells (no coat, no ligand) subtracted?', 'blank_subtracted'),
    _one_fact('specificity_control', 'Was the specificity shown by a control with a non-binding protein, an uncoated well or a mutant?', 'nonspecific_binding_checked'),
    {
        'id': 'wash_dissociation',
        'question': 'Was dissociation of the complex during the washes considered, so that the number can be read as an apparent KD?',
        'reads': ('facts.wash_dissociation_considered', 'quantities.koff', 'quantities.wash_duration'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and both the dissociation rate constant and the total wash duration are given, the grader records them (koff_per_s, wash_min and wash_loss_refs) and leaves the judgement to the sheet; otherwise it is unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'wash_loss_recorded_for_the_sheet', 'not stated and koff and the wash duration are given: they are recorded and the sheet judges them'),
            ('unknown', 'fact_unknown', 'not stated and koff or the wash duration is not given'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when the plate was washed?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an incubation time is given, the grader records it (incubation_min, in minutes, and incubation_refs, with constant_refs of the reported constant it is read against) and leaves the judgement to the sheet; otherwise it is unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'not stated and an incubation time is given: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no incubation time'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('avidity', 'Was multivalent binding (avidity) of the coating or of the ligand excluded or controlled?', 'avidity_excluded'),
    _one_fact('coated_protein_activity', 'Was the coated protein shown to be active and correctly oriented on the plate?', 'coated_protein_active'),
    _one_fact('detection_interference', 'Was it shown that the detection reagent does not interfere with the binding?', 'detection_does_not_interfere'),
    {
        'id': 'concentration_series',
        'question': 'Did the concentrations bracket the reported constant well enough to define the binding curve?',
        'reads': ('quantities.kd', 'quantities.ki', 'quantities.ec50', 'quantities.ic50', 'quantities.titration_point_count', 'concentration_series'),
        'rule': 'The grader records the number of concentrations (concentration_count: the listed series, or else the stated number of points) with its refs (concentration_count_refs) and, when the reported constant and the list are both given, the lowest and the highest concentration over the constant (concentration_low_over_constant, concentration_high_over_constant) with their refs (concentration_span_refs); the judgement is left to the sheet. The span can only be recorded from the list.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_series_recorded_for_the_sheet', 'a count is known (listed or stated): it, and the span when the constant and the list are given, are recorded and the sheet judges them'),
            ('unknown', 'constant_or_series_missing', 'no count is known'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the model of the binding curve stated, and does it fit the assay format?',
        'reads': ('fit_model', 'assay_format'),
        'rule': 'The model must be stated. A competitive-binding model for a saturation titration fails, and a one-site or Hill model for a competition fails; a four-parameter logistic model fits both formats. Not stated is unknown. A model stated when no KD, Ki, EC50 or IC50 is reported is unknown whatever the format (the model and the format hold no span; the quoted span of a reported constant is the support of the decision, and there is none).',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a model stated that fits the format (or no format stated) and a constant reported'),
            ('unknown', 'model_stated_without_a_reported_constant', 'a model stated and no constant reported (whether or not it fits the format)'),
            ('conflicting', 'competition_model_for_saturation_titration', 'competitive binding model and saturation titration, and a constant reported'),
            ('conflicting', 'direct_model_for_competition', 'one-site or Hill model and competition, and a constant reported'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'direct_vs_competition',
        'question': 'Do the saturation-titration KD and the competition Ki, when both are reported, agree?',
        'reads': ('quantities.kd', 'quantities.ki', 'quantities.ic50', 'quantities.tracer_concentration', 'quantities.tracer_kd', 'facts.single_estimate_method'),
        'rule': 'With a competition IC50, the concentration of the ligand it displaces and that ligand\'s KD given, the grader computes the Cheng-Prusoff Ki, IC50 / (1 + tracer concentration / tracer KD) (ki_cheng_prusoff_nM; arithmetic of stated numbers, not a judgement). The Ki compared is the reported Ki, else this one. With both a KD and that Ki given, the grader records the larger over the smaller (estimate_fold, at least 1) and the refs (estimate_refs); with both a reported Ki and the Cheng-Prusoff Ki, it records their fold (conversion_fold, conversion_refs); the judgement is left to the sheet. With no fold to record, only this method used (single estimate stated yes) is not applicable and otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'estimates_recorded_for_the_sheet', 'a fold gap (KD against the Ki, or the reported Ki against the Cheng-Prusoff Ki) is recorded and the sheet judges it'),
            ('unknown', 'kd_or_ki_missing', 'the KD or the Ki is missing and only one method is not stated'),
            ('not_applicable', 'single_estimate_method', 'the KD or the Ki is missing and only one method is stated'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Technical wells of one plate are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
