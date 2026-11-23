"""AlphaScreen criteria: the ONE place where the AlphaScreen / AlphaLISA binding grader's criteria and thresholds are declared (bead-based amplified luminescent proximity binding assay: direct titration, cross-titration or competition).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the AlphaScreen grader asks. The grader reports FACTS and holds NO threshold that
judges goodness: where a criterion needs a number to be compared with a limit (the signal-to-background ratio, the Z-prime factor, the incubation,
the concentration count and span, the agreement of the KD and the Ki, the replicate count), the grader records the number with its support refs and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_alpha_converter.py. The logic that answers each question is in literature_alpha_grader.py (one short function per criterion, same order).
The only constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in ALPHA_CRITERIA
--------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_alpha_record.py)
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

Terms. The reported constant of a series: the apparent KD of a saturation
titration, else the Ki, else the EC50 or the IC50 (native 'constant_name' says
which). Apparent KD: the KD read from a bead-based proximity assay; the signal is amplified and the
partners are presented on beads that carry many capture molecules, so the number is an apparent constant of
bead-presented complexes (avidity), not the monovalent solution KD. EC50 and IC50: half-maximal concentrations of a curve; they are not
dissociation constants (an EC50 depends on the concentrations of the partners and of the beads; an IC50 on the concentration of the
pair it competes with) and are never carried as a binding constant. Hook effect: the fall of the signal at a high concentration of a
partner, because the free partner saturates the capture sites of its beads and donor and acceptor beads no longer bind the same
complex; a constant must be fitted to the rising part or with a bell-shaped model. Signal window: the signal at the top of the curve
over the signal of the background wells (S/B). Z': the screening-window factor of the positive and negative controls.

What this method does not ask (items of the other binding experiments left out because a bead assay has no such thing): a sensorgram
baseline, mass transport, a regeneration, the kinetic rate constants, the particle number of a confocal volume, the donor and the
acceptor of FRET, the washes of a plate assay and the coating of a plate. The bead concentration, the bead coatings,
the plate format, the temperature, the number of technical wells,
the spread and the statement that only this method was used are kept in the record for the reviewer; no criterion judges them.
"""

VERSION = 'a105_alphascreen_criteria'

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
ALPHA_CRITERIA = (
    {
        'id': 'signal_window',
        'question': 'Is the signal at the top of the curve high enough over the background to define the binding curve?',
        'reads': ('quantities.signal_to_background', 'quantities.signal_maximum', 'quantities.signal_background'),
        'rule': 'The grader records the signal-to-background ratio (signal_over_background: the ratio the source reports, else the top signal over the background signal) and the refs of what it rests on (signal_window_refs) and leaves the judgement to the sheet. Neither given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'signal_window_recorded_for_the_sheet', 'a ratio is reported, or the top and the background signal are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'signal_window_not_given', 'no ratio is reported and the top signal or the background signal is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'assay_quality',
        'question': 'Is the Z-prime factor of the assay high enough?',
        'reads': ('quantities.z_prime',),
        'rule': 'The reported Z-prime factor is recorded (z_prime and z_prime_refs) and the judgement is left to the sheet. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'z_prime_recorded_for_the_sheet', 'a Z-prime is given: it is recorded and the sheet judges it'),
            ('unknown', 'z_prime_not_given', 'no Z-prime is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _one_fact('detector_range', 'Was the signal within the linear range of the reader?', 'signal_in_linear_range'),
    _one_fact('interference_counter_screen', 'Was signal interference (colour or singlet oxygen quenchers, biotin mimetics, metal chelators, light) excluded by a counter-screen with a control linker?', 'counter_screen_done'),
    _one_fact('hook_effect', 'Was the hook effect (the fall of the signal at a high partner concentration) looked for and dealt with, so that the constant is not read from the falling part?', 'hook_effect_handled'),
    {
        'id': 'partner_depletion',
        'question': 'Was the partner held at a constant concentration at or below the KD, so that it does not deplete the titrated partner?',
        'reads': ('facts.partner_concentration_below_kd', 'quantities.labelled_partner_concentration', 'quantities.tagged_partner_concentration', 'quantities.kd', 'quantities.ki', 'quantities.ec50', 'quantities.ic50', 'titration_design'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated, the design is not a cross-titration, the reported constant is given and at least one partner concentration is given, the grader records the largest stated partner concentration over the reported constant (partner_over_constant, partner_name, partner_refs) and leaves the judgement to the sheet; otherwise it is unknown. In a cross-titration both partners are titrated, so no partner is held constant and no number is recorded.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'partner_concentration_recorded_for_the_sheet', 'not stated, not a cross-titration, a constant and a partner concentration are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no ratio can be recorded'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when the beads were added or the plate was read?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time', 'quantities.bead_incubation_time'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an incubation time of the partners is given, the grader records the time the partners were together (incubation_min, in minutes: that incubation plus the step after the beads were added when that is stated too, because the partners go on binding in that step) and its refs (incubation_refs) and leaves the judgement to the sheet; otherwise it is unknown. The step after the beads alone is not recorded: the time before the beads is then not known.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'not stated and an incubation time is given: the total time with the bead step is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no incubation time'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('specificity_control', 'Was the specificity shown by a control with a non-binding protein, a mutant or an untagged partner?', 'nonspecific_binding_checked'),
    _one_fact('capture_artifacts', 'Was it shown that the tag, the label or the capture on the beads does not alter the binding?', 'capture_does_not_alter_binding'),
    _one_fact('light_protection', 'Were the light-sensitive beads protected from ambient light?', 'light_protected'),
    _one_fact('avidity', 'Was multivalent binding (avidity) of the bead-presented partners excluded or controlled?', 'avidity_excluded'),
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
        'reads': ('fit_model', 'assay_format', 'quantities.kd', 'quantities.ki', 'quantities.ec50', 'quantities.ic50'),
        'rule': 'The model must be stated and a KD, Ki, EC50 or IC50 must be reported, because the quoted spans of the reported constants are the only support of the model. A competitive-binding model for a saturation titration fails, and a one-site, quadratic or bell-shaped model for a competition fails; a four-parameter logistic model and another named model fit both formats. Not stated is unknown. A model stated with no reported constant is unknown, whatever the format (no span supports it, so neither supported nor conflicting can be returned).',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a model stated that fits the format (or no format stated) and a constant reported'),
            ('conflicting', 'competition_model_for_saturation_titration', 'competitive binding model and saturation titration, and a constant reported'),
            ('conflicting', 'direct_model_for_competition', 'one-site, quadratic or bell-shaped model and competition, and a constant reported'),
            ('unknown', 'model_stated_without_a_reported_constant', 'a model stated and no constant reported'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'direct_vs_competition',
        'question': 'Do the titration KD and the competition Ki, when both are reported, agree?',
        'reads': ('quantities.kd', 'quantities.ki', 'facts.single_estimate_method'),
        'rule': 'With both a KD and a Ki given, the grader records the larger over the smaller (estimate_fold, at least 1) and the refs of the two (estimate_refs) and leaves the judgement to the sheet. With one missing, only this method used (single estimate stated yes) is not applicable and otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'estimates_recorded_for_the_sheet', 'both are given: the fold gap is recorded and the sheet judges it'),
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
