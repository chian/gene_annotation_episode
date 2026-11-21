"""MST criteria: the ONE place where the MST (microscale thermophoresis) grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the MST grader asks.
The grader reports FACTS and holds NO threshold that judges goodness: where a criterion
needs a number to be compared with a limit (the signal-to-noise and the Fnorm change, the
detected partner over the KD, the concentration series, the incubation, the F-hot time,
the replicate count, the direct-versus-competition fold gap), the grader records the
number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet
side, in literature_mst_converter.py. The logic that answers each question is in
literature_mst_grader.py (one short function per criterion, same order). The only
constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in MST_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_mst_record.py)
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
the Ki of a competition, else the EC50 (the native value 'constant_name'
says which); the effect handed to the sheet is only a KD or a Ki, because an
EC50 depends on the detected partner's concentration and is not a binding
constant. Detected (labelled) partner: the partner held at a fixed
concentration (labelled_concentration). Titrant: what is added in a series.
Signal: the change of the normalized fluorescence Fnorm between the unbound and
the bound state (fnorm_amplitude, per mille) and its signal-to-noise. Initial
fluorescence: the fluorescence before the infrared laser heats the spot; it must
not depend on the titrant, or the change of Fnorm may be a quenching or an
enhancement and not a binding. Tight binding: the detected partner is not well
below the KD, so binding depletes the free titrant and the 1:1 hyperbola no
longer gives the KD; a quadratic fit (or an explicit consideration of the
depletion) is needed. Thermophoresis readout: Fnorm read at an F-hot time after
the fast temperature jump of the dye has ended; read earlier, the signal is the
temperature jump and not the thermophoresis.

What MST does not ask (items of the other binding experiments left out because
MST in solution has no such thing): a surface and its regeneration, mass
transport, a sensorgram baseline, an immobilized partner's activity, the kinetic
rate constants (an equilibrium titration has none), the donor and the acceptor of
FRET and the polarization ends of FP.
"""

VERSION = 'a105_mst_criteria_v1'

# ---- Threshold constants -------------------------------------------------
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.
S_PER_UNIT = {'s': 1.0, 'ms': 0.001}  # FIXED_BY_DEFINITION: seconds per F-hot time unit.

# ---- The criteria --------------------------------------------------------
MST_CRITERIA = (
    {
        'id': 'signal_amplitude',
        'question': 'Is the change of the normalized fluorescence large enough, against the noise, to fit a KD?',
        'reads': ('quantities.signal_to_noise', 'quantities.fnorm_amplitude'),
        'rule': 'The grader records the two numbers that are given (signal_to_noise, fnorm_amplitude in per mille; None for one not given) and their refs (signal_refs) and leaves the judgement to the sheet. Neither given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'signal_recorded_for_the_sheet', 'at least one number is given: it is recorded and the sheet judges it'),
            ('unknown', 'signal_not_given', 'neither number is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'initial_fluorescence',
        'question': 'Was the initial fluorescence shown not to change with the titrant (no quenching or enhancement mimicking binding)?',
        'reads': ('facts.initial_fluorescence_consistent', 'facts.initial_fluorescence_checked'),
        'rule': 'A stated consistency decides: yes supported, no fails. When the consistency is not stated, a check stated as not made fails; a check stated as made without a stated result, and nothing stated, are unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'initial_fluorescence_consistent', 'the consistency is yes'),
            ('conflicting', 'initial_fluorescence_changes_with_titrant', 'the consistency is no'),
            ('conflicting', 'initial_fluorescence_not_checked', 'the consistency is not stated and the check is no'),
            ('unknown', 'initial_fluorescence_result_not_stated', 'the consistency is not stated and the check is not no'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'fluorescence_level',
        'question': 'Was the fluorescence intensity within the range the instrument reads reliably?',
        'reads': ('facts.fluorescence_intensity_in_range',),
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
        'id': 'aggregation_adsorption',
        'question': 'Was aggregation of a partner, or its adsorption to the capillary wall, checked (capillary scan, peak shape)?',
        'reads': ('facts.aggregation_or_adsorption_checked',),
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
        'id': 'labelled_concentration',
        'question': 'Was the detected partner at or below the KD, or was depletion handled by a tight-binding analysis?',
        'reads': ('quantities.labelled_concentration', 'quantities.kd', 'fit_model', 'facts.labelled_partner_at_or_below_kd', 'facts.tight_binding_considered'),
        'rule': 'With the labelled concentration and the KD both given, the grader records their quotient (labelled_over_kd), the refs (labelled_refs) and whether the analysis handles tight binding (tight_binding_handled: a quadratic fit, or tight binding stated as considered) and leaves the judgement to the sheet. With either number missing (a competition Ki is not a KD), the fact that the detected partner is at or below the KD decides: yes supported; no is supported when tight binding was handled and fails otherwise; not stated is unknown.',
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
        'reads': ('quantities.kd', 'quantities.ki', 'quantities.ec50', 'quantities.titration_point_count', 'concentration_series'),
        'rule': 'The grader records the number of concentrations (concentration_count: the listed series, or else the stated number of points) with its refs (count_refs) and, when the list and the reported constant are both given, the lowest and the highest over the constant (concentration_low_over_constant, concentration_high_over_constant) with their refs (series_refs), and leaves the judgement to the sheet; the span can only be judged from the list. Neither a list nor a count is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'series_recorded_for_the_sheet', 'a list or a count is given: the count (and the span, when it can be formed) is recorded and the sheet judges it'),
            ('unknown', 'constant_or_series_missing', 'neither a list nor a count is given'),
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
        'id': 'labelling_scheme',
        'question': 'Is the detection label-free, or, if a label (dye, His-tag dye, fluorescent protein) is used, was it shown not to alter the binding?',
        'reads': ('label_type', 'facts.labelling_does_not_alter_binding'),
        'rule': 'Labelling stated as altering the binding fails; labelling stated as not altering it is supported (both rest on the fact\'s span). Otherwise label-free detection (intrinsic fluorescence) is unknown, because the label type is a choice that holds no span and a decision needs one; a stated label without that control is unknown (the label may change size, charge or the binding site), and nothing stated is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'labelling_shown_not_to_alter_binding', 'the fact is yes'),
            ('unknown', 'label_free_stated_without_a_span', 'the fact is not stated and the label type is label-free: the label type holds no span'),
            ('conflicting', 'labelling_alters_binding', 'the fact is no'),
            ('unknown', 'label_not_shown_harmless', 'the fact is not stated and a label type other than label-free is stated'),
            ('unknown', 'labelling_not_stated', 'neither the fact nor a label type is stated'),
            ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable and no label type is stated'),
        ),
    },
    {
        'id': 'specificity_control',
        'question': 'Was the specificity of the signal shown by a nonspecific-binding control (a non-binding mutant or an unrelated protein)?',
        'reads': ('facts.nonspecific_binding_checked',),
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
        'id': 'readout_window',
        'question': 'Is the readout (thermophoresis, temperature jump or initial fluorescence) stated, and for thermophoresis was F-hot read after the temperature jump?',
        'reads': ('readout_signal', 'quantities.fhot_time'),
        'rule': 'A readout of the initial fluorescence has no F-hot window and does not apply; a temperature-jump readout stated is unknown (the readout is a choice that holds no span and a decision needs one). A thermophoresis readout needs its F-hot time given: the grader records it (fhot_s, in seconds, and fhot_refs) and leaves the judgement to the sheet. The readout not stated is unknown.',
        'thresholds': ('S_PER_UNIT',),
        'returns': (
            ('unknown', 'fhot_time_recorded_for_the_sheet', 'thermophoresis and the F-hot time is given: it is recorded and the sheet judges it'),
            ('unknown', 'temperature_jump_readout_stated_without_a_span', 'the readout is the temperature jump: the readout holds no span'),
            ('unknown', 'fhot_time_not_stated', 'thermophoresis and the F-hot time is not given'),
            ('unknown', 'readout_signal_not_stated', 'no readout stated'),
            ('not_applicable', 'initial_fluorescence_readout', 'the readout is the initial fluorescence'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the fitting model stated and suited to the assay format?',
        'reads': ('fit_model', 'assay_format'),
        'rule': 'The model must be stated. The model and the format are choices that hold no span, so a decision on them rests on the quoted spans of the reported constants (KD, Ki, EC50) the model was fitted to; with no reported constant it is unknown. A competitive-binding model for a direct titration fails; a 1:1 or Hill model for a competition experiment fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a model stated that does not clash with the format, and a reported constant gives the support'),
            ('conflicting', 'competition_model_for_direct_titration', 'competitive_binding model and the format is a direct titration, and a reported constant gives the support'),
            ('conflicting', 'direct_model_for_competition', '1:1 or hill model and the format is competition, and a reported constant gives the support'),
            ('unknown', 'model_stated_without_a_reported_constant', 'a model is stated and no constant (KD, Ki, EC50) is reported: there is no span to support it'),
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
