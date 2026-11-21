"""FP criteria: the ONE place where the FP/FA grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the FP grader asks.
The grader reports FACTS and holds NO threshold that judges goodness: where a criterion
needs a number to be compared with a limit (the window, the tracer over the KD, the
concentration series, the incubation, the intensity change, the replicate count, the
direct-versus-competition fold gap), the grader records the number with its support refs
and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement
and its EXPERT_REVIEW constants are on the sheet side, in literature_fp_converter.py.
The logic that answers each question is in literature_fp_grader.py (one short function
per criterion, same order). The only constants left here are unit conversions
(FIXED_BY_DEFINITION).

How to read an entry in FP_CRITERIA
-----------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_fp_record.py)
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

Terms. The reported constant: the KD of a direct titration, or, when the
record has no KD, the Ki of a competition (displacement) experiment. Tracer:
the fluorescently labelled partner at a fixed concentration. Titrant: what is
added in a series. Window: the polarization span between free tracer
(signal_minimum) and bound tracer (signal_maximum), in mP; an anisotropy r is
read as the polarization P = 3 r / (2 + r) (times 1000 for mP), which is the
definition linking the two. Tight binding: the tracer concentration is not
well below the KD, so binding depletes the free titrant and the 1:1 hyperbola
no longer gives the KD; a quadratic fit (or an explicit consideration of the
depletion) is needed.

What FP does not ask (items of the other binding experiments left out because
FP has no such thing): a surface and its regeneration, mass transport, a
sensorgram baseline drift, the immobilized partner's activity, the kinetic
rate constants and their consistency with the KD (FP at equilibrium has none),
a dissociation window and a steady-state versus kinetic comparison (the
counterpart here is the direct versus competition comparison).
"""

VERSION = 'a105_fp_criteria_v1'

# ---- Threshold constants -------------------------------------------------
MP_PER_POLARIZATION = 1000.0  # FIXED_BY_DEFINITION: one polarization unit is 1000 millipolarization units (mP).
ANISOTROPY_FACTOR = 3.0  # FIXED_BY_DEFINITION: P = ANISOTROPY_FACTOR r / (ANISOTROPY_OFFSET + r), the definition linking polarization P and anisotropy r.
ANISOTROPY_OFFSET = 2.0  # FIXED_BY_DEFINITION: see ANISOTROPY_FACTOR.
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.

# ---- The criteria --------------------------------------------------------
FP_CRITERIA = (
    {
        'id': 'assay_window',
        'question': 'Is the polarization window between free and bound tracer large enough to resolve the titration?',
        'reads': ('quantities.signal_minimum', 'quantities.signal_maximum', 'quantities.signal_noise'),
        'rule': 'The grader records the window (window_mP = maximum minus minimum, in mP; an anisotropy r is converted to polarization first) and its refs (window_refs), and, when the paper states the noise of the polarization reads in mP, that noise (window_noise_mP, window_noise_refs), and leaves the judgement to the sheet. Either end not given is unknown.',
        'thresholds': ('MP_PER_POLARIZATION', 'ANISOTROPY_FACTOR', 'ANISOTROPY_OFFSET'),
        'returns': (
            ('unknown', 'window_recorded_for_the_sheet', 'both signal ends are given: the window is recorded and the sheet judges it'),
            ('unknown', 'minimum_or_maximum_missing', 'a signal end is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'free_probe_baseline',
        'question': 'Was the polarization of the free tracer (buffer and tracer without the partner) measured as the baseline?',
        'reads': ('facts.free_probe_baseline_measured',),
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
        'id': 'tracer_concentration',
        'question': 'Was the tracer concentration at or below the KD, or was tracer depletion handled by a tight-binding analysis?',
        'reads': ('quantities.tracer_concentration', 'quantities.kd', 'fit_model', 'facts.tracer_at_or_below_kd', 'facts.tight_binding_considered'),
        'rule': 'With the tracer concentration and the KD (the tracer own KD, from a direct titration) both given, the grader records their quotient (tracer_over_kd), the refs (tracer_refs) and whether the analysis handles tight binding (tight_binding_handled: a quadratic fit, or tight binding stated as considered) and leaves the judgement to the sheet. With either number missing (a competition Ki is not the tracer KD), the fact that the tracer is at or below KD decides: yes supported; no is supported when tight binding was handled and fails otherwise; not stated is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'tracer_over_kd_recorded_for_the_sheet', 'both numbers are given: the quotient is recorded and the sheet judges it'),
            ('supported', 'tracer_at_or_below_kd', 'no quotient and the fact is yes'),
            ('supported', 'tracer_above_kd_with_tight_binding_analysis', 'no quotient, the fact is no and the fit is quadratic or tight binding is stated considered'),
            ('conflicting', 'tracer_above_kd_without_tight_binding_analysis', 'no quotient, the fact is no and neither'),
            ('unknown', 'tracer_or_kd_missing', 'no quotient and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Did the titrant concentrations bracket the reported constant well enough to define the binding curve?',
        'reads': ('quantities.kd', 'quantities.ki', 'quantities.ic50', 'concentration_series', 'series_kind'),
        'rule': 'The grader records the number of concentrations (concentration_count), the lowest and the highest over the reference constant (concentration_low_over_constant, concentration_high_over_constant) and their refs (series_refs) and leaves the judgement to the sheet. The reference is the IC50 when the series is stated to be the competitor series and the IC50 is given (series_reference ic50), otherwise the reported constant. The reference or the series not given is unknown.',
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
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an incubation time is given, the grader records it (incubation_min, in minutes, and incubation_refs) and leaves the judgement to the sheet; otherwise it is unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'not stated and an incubation time is given: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no incubation time'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'intensity_change',
        'question': 'Was a change of the tracer fluorescence intensity on binding checked or corrected?',
        'reads': ('facts.intensity_change_checked', 'quantities.total_intensity_change', 'intensity_change_direction'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an intensity change is reported, the grader records it (intensity_change_percent and intensity_change_refs, and the stated direction intensity_change_direction, increase or decrease or None) and leaves the judgement to the sheet; with neither it is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'intensity_change_recorded_for_the_sheet', 'not stated and a change is reported: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no change reported'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'specificity_control',
        'question': 'Was the specificity of the signal shown by a nonspecific-binding control or displacement of the tracer by an unlabelled competitor?',
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
        'id': 'surface_adsorption',
        'question': 'Was adsorption of the tracer or titrant to the plate or tubes prevented (detergent, carrier protein or a non-binding plate)?',
        'reads': ('facts.surface_adsorption_prevented',),
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
