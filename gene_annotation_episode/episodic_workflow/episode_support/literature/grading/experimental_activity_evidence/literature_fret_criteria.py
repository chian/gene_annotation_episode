"""FRET criteria: the ONE place where the FRET / TR-FRET grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the FRET grader asks.
The grader reports FACTS and holds NO threshold that judges goodness: where a criterion
needs a number to be compared with a limit (the window, the gating delay and integration
window, the labelled partner over the KD, the concentration series, the incubation, the
replicate count, the direct-versus-competition fold gap), the grader records the number
with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet
side, in literature_fret_converter.py. The logic that answers each question is in
literature_fret_grader.py (one short function per criterion, same order). The only
constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in FRET_CRITERIA
-------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_fret_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Constants: each is defined once, below. FIXED_BY_DEFINITION marks a physical
constant or unit conversion, not a judgment; no judgment value is declared here.

Terms. The reported constant of a series: the KD of a direct titration, else
the Ki of a competition, else the EC50, else the IC50 (the native value
'constant_name' says which); the effect handed to the sheet is only a KD or a
Ki, because an EC50 or IC50 depends on the labelled concentrations and is not
a binding constant. Labelled partner: a partner carrying the donor or the
acceptor that is held at a fixed concentration (donor_concentration and
acceptor_concentration); the limiting one is the smaller of the two stated.
Titrant: what is added in a series. Window: the fold between the highest and
the lowest acceptor over donor emission ratio (ratio_maximum over
ratio_minimum), the signal over background of the titration. Tight binding:
the labelled partner is not well below the KD, so binding depletes the free
titrant and the 1:1 hyperbola no longer gives the KD; a quadratic fit (or an
explicit consideration of the depletion) is needed. Time-resolved: the read
waits a delay after the excitation flash (TR-FRET, HTRF, LanthaScreen); it
needs a donor with a long lifetime (a lanthanide), so gating with a
fluorescent-protein or organic-dye donor is a contradiction.

What FRET does not ask (items of the other binding experiments left out because
FRET in solution has no such thing): a surface and its regeneration, mass
transport, a sensorgram baseline drift, the immobilized partner's activity,
the kinetic rate constants and their consistency with the KD (an equilibrium
FRET titration has none), a steady-state versus kinetic comparison (the
counterpart here is the direct versus competition comparison), and the
adsorption to plates (not part of the FRET form).
"""

VERSION = 'a105_fret_criteria'

# ---- Threshold constants -------------------------------------------------
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.
US_PER_UNIT = {'us': 1.0, 'ms': 1000.0}  # FIXED_BY_DEFINITION: microseconds per gate time unit.
PER_S_PER_UNIT = {'per_s': 1.0, 'per_min': 1 / 60}  # FIXED_BY_DEFINITION: per second per rate unit (a rate constant per minute is 1/60 of the same per second).

# ---- The criteria --------------------------------------------------------
FRET_CRITERIA = (
    {
        'id': 'assay_window',
        'question': 'Is the fold between the highest and the lowest emission ratio large enough to resolve the titration?',
        'reads': ('quantities.ratio_minimum', 'quantities.ratio_maximum', 'quantities.z_prime'),
        'rule': 'The grader records the fold (ratio_fold = maximum over minimum, when both ends are given), the stated Z prime factor (z_prime, when given) and their refs (window_refs) and leaves the judgement to the sheet. Neither a complete pair of ends nor a Z prime given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'window_recorded_for_the_sheet', 'both ratio ends or a Z prime factor are given: the fold and the Z prime are recorded and the sheet judges them'),
            ('unknown', 'minimum_or_maximum_missing', 'a ratio end is not given and no Z prime factor is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'ratiometric_readout',
        'question': 'Was the signal the ratio of the acceptor emission to the donor emission (not the acceptor intensity alone)?',
        'reads': ('facts.ratiometric_readout_used',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'spectral_crosstalk',
        'question': 'Were donor emission leaking into the acceptor channel and direct acceptor excitation measured (donor-only and acceptor-only controls) and corrected?',
        'reads': ('facts.crosstalk_corrected', 'facts.donor_only_control_measured', 'facts.acceptor_only_control_measured'),
        'rule': 'A stated correction of the crosstalk (bleed-through) is enough; a stated absence of correction fails. When the correction is not stated, both controls stated as done are enough; otherwise any control stated as not done fails and any not stated is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'crosstalk_corrected', 'the correction fact is yes'),
            ('supported', 'facts_answered_yes', 'the correction is not stated and both controls are yes'),
            ('conflicting', 'fact_answered_no', 'the correction is no, or it is not stated and a control is no'),
            ('unknown', 'fact_unknown', 'the correction is not stated, no control is no and one is unknown'),
            ('not_applicable', 'fact_not_applicable', 'all three facts are not_applicable'),
        ),
    },
    {
        'id': 'time_gating',
        'question': 'If the read was time-resolved, was it gated with a long-lived donor, a long enough delay and a long enough integration window?',
        'reads': ('facts.time_resolved_read', 'donor_acceptor_pair', 'donor_lanthanide', 'quantities.delay_time', 'quantities.integration_time'),
        'rule': 'A read stated as not time-resolved does not apply. A time-resolved read (stated, or a delay given) with a fluorescent-protein or organic-dye pair fails (those donors live nanoseconds and cannot be gated). Otherwise the delay must be given: the grader records the delay (delay_us), the integration window if given (integration_us), the lanthanide of the donor if named (donor_lanthanide) and their refs (gating_refs) and leaves the judgement to the sheet. A time-resolved read whose delay is not given is unknown.',
        'thresholds': ('US_PER_UNIT',),
        'returns': (
            ('unknown', 'gating_recorded_for_the_sheet', 'time-resolved with a long-lived donor and a delay is given: the delay and the window are recorded and the sheet judges them'),
            ('conflicting', 'time_gating_with_short_lived_donor', 'time-resolved with a fluorescent-protein or organic-dye pair'),
            ('unknown', 'delay_not_stated', 'time-resolved and the delay is not given'),
            ('unknown', 'time_resolved_read_not_stated', 'the fact is unknown and no delay is given'),
            ('not_applicable', 'not_time_resolved', 'answer no'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'labelled_concentration',
        'question': 'Was the limiting labelled partner at or below the KD, or was depletion handled by a tight-binding analysis?',
        'reads': ('quantities.donor_concentration', 'quantities.acceptor_concentration', 'quantities.kd', 'fit_model', 'facts.labelled_partner_at_or_below_kd', 'facts.tight_binding_considered'),
        'rule': 'With a labelled concentration (the smaller of the donor and acceptor concentrations stated) and the KD both given, the grader records their quotient (labelled_over_kd), the refs (labelled_refs) and whether the analysis handles tight binding (tight_binding_handled: a quadratic fit, or tight binding stated as considered) and leaves the judgement to the sheet. With either number missing (a competition Ki is not a KD), the fact that the labelled partner is at or below the KD decides: yes supported; no is supported when tight binding was handled and fails otherwise; not stated is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'labelled_over_kd_recorded_for_the_sheet', 'both numbers are given: the quotient is recorded and the sheet judges it'),
            ('supported', 'labelled_at_or_below_kd', 'no quotient and the fact is yes'),
            ('supported', 'labelled_above_kd_with_tight_binding_analysis', 'no quotient, the fact is no and the fit is quadratic or tight binding is stated considered'),
            ('conflicting', 'labelled_above_kd_without_tight_binding_analysis', 'no quotient, the fact is no and neither'),
            ('unknown', 'labelled_or_kd_missing', 'no quotient and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Did the titrant concentrations bracket the reported constant well enough to define the binding curve?',
        'reads': ('quantities.kd', 'quantities.ki', 'quantities.ec50', 'quantities.ic50', 'concentration_series', 'series_format'),
        'rule': 'The grader records the number of concentrations (concentration_count), the lowest and the highest over the reported constant (concentration_low_over_constant, concentration_high_over_constant), which titration the series belongs to if stated (series_format) and their refs (series_refs) and leaves the judgement to the sheet. The constant or the series not given is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'series_recorded_for_the_sheet', 'the constant and the series are given: count and span are recorded and the sheet judges them'),
            ('unknown', 'constant_or_series_missing', 'the reported constant or the series is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when read?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time', 'quantities.koff', 'quantities.kd', 'quantities.ki', 'quantities.ec50', 'quantities.ic50'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an incubation time is given, the grader records it (incubation_min, in minutes, the stated dissociation rate constant koff_per_s if given, and incubation_refs, which include the refs of the koff or, without one, of the reported constant) and leaves the judgement to the sheet; otherwise it is unknown.',
        'thresholds': ('MIN_PER_UNIT', 'PER_S_PER_UNIT'),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'not stated and an incubation time is given: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no incubation time'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'labelling_scheme',
        'question': 'Is the labelling direct, or, if indirect through an antibody, tag or streptavidin, was the labelling shown not to alter the binding?',
        'reads': ('facts.indirect_labelling_used', 'facts.labelling_does_not_alter_binding'),
        'rule': 'Labelling stated as altering the binding fails; labelling stated as not altering it is supported. Otherwise direct labelling (indirect labelling stated as not used) is supported, indirect labelling without that control is unknown (the extra tag and antibody equilibria and higher-order complexes are not excluded), and nothing stated is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'labelling_shown_not_to_alter_binding', 'the second fact is yes'),
            ('supported', 'direct_labelling', 'the second fact is not stated and indirect labelling is no'),
            ('conflicting', 'labelling_alters_binding', 'the second fact is no'),
            ('unknown', 'indirect_labelling_not_shown_harmless', 'the second fact is not stated and indirect labelling is yes'),
            ('unknown', 'labelling_not_stated', 'neither fact is stated'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'compound_interference',
        'question': 'Was interference of the titrant or test compound with the ratio (absorbance, inner filter, fluorescence, quenching) checked?',
        'reads': ('facts.compound_interference_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'specificity_control',
        'question': 'Was the specificity of the signal shown by a nonspecific-binding control (a non-binding mutant or unrelated protein) or displacement of the labelled partner by an unlabelled competitor?',
        'reads': ('facts.nonspecific_binding_checked', 'facts.unlabelled_competitor_displaces'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'specificity_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the fitting model stated and suited to the assay format?',
        'reads': ('fit_model', 'assay_format'),
        'rule': 'The model must be stated. A competitive-binding model for a direct titration fails; a 1:1 or Hill model for a competition experiment fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a model stated that does not clash with the format'),
            ('conflicting', 'competition_model_for_direct_titration', 'competitive_binding model and the format is a direct titration'),
            ('conflicting', 'direct_model_for_competition', '1:1 or hill model and the format is competition'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent titrations?',
        'reads': ('quantities.replicate_count', 'facts.independent_titrations'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'direct_vs_competition',
        'question': 'Do the direct-titration KD and the competition Ki agree?',
        'reads': ('quantities.kd', 'quantities.ki', 'facts.single_estimate_method'),
        'rule': 'The grader records the fold gap of the two constants (estimate_fold = larger over smaller) and the refs of the two (estimate_refs) and leaves the judgement to the sheet. If only one estimate was made the question does not apply.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'estimates_recorded_for_the_sheet', 'both estimates are given: the fold gap is recorded and the sheet judges it'),
            ('unknown', 'kd_or_ki_missing', 'an estimate is missing and single_estimate_method is not yes'),
            ('not_applicable', 'single_estimate_method', 'an estimate is missing and single_estimate_method is yes'),
        ),
    },
)
