"""FCS criteria: the ONE place where the fluorescence correlation spectroscopy (FCS, and dual-colour FCCS) binding grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the FCS grader asks. The grader reports FACTS and holds NO threshold that
judges goodness: where a criterion needs a number to be compared with a limit (the diffusion ratio, its agreement with the mass, the maximum
fraction bound, the labelled range, the labelled partner over the KD, the concentration count and span, the incubation, the acquisition, the
replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet';
the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_fcs_converter.py. The logic that answers each question is in
literature_fcs_grader.py (one short function per criterion, same order). The only constants left here are the cube-root exponent and unit
conversions (FIXED_BY_DEFINITION).

Support rule (from the ELISA work, designed in from the start): a criterion returns 'supported' or 'conflicting' only with support refs, the
quoted source spans of the stated fields it rests on. A decision that rests on a fact or a choice that holds no span (the fit model with no
reported KD) is 'unknown' with a declared reason, never 'supported' and never 'conflicting'.

How to read an entry in FCS_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_fcs_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Constants: each is defined once, below, and marked FIXED_BY_DEFINITION (a physical law or a unit conversion, not a judgment).

Terms. The reported constant of a series: the KD. Labelled partner: the partner
carrying the fluorophore, held at a low constant concentration; it is the only
one the correlation curve reports. Titrant: the partner added in a series.
Diffusion ratio: how much slower the fully bound complex diffuses than the free
labelled partner, the bound diffusion time over the free one (or the free
diffusion coefficient over the bound one); it is the size of the signal. Cube-root
law: the hydrodynamic radius of a compact particle grows with the cube root of its
mass, so does the diffusion time; a complex of twice the mass diffuses only about
26 percent more slowly. Confocal volume calibration: the structure parameter and
the lateral radius of the detection volume are found from a reference dye of known
diffusion coefficient (for example Rhodamine 6G or Alexa 488). One-component fit
of a mixture: gives an apparent time between the free and the bound one, from
which the fraction bound is read only against reference times of the fully free
and the fully bound partner. Two-component fit: gives the two times and their
fractions, and is stable only when the free time is fixed from a measurement of
the free partner. Tight binding: the labelled partner is not well below the KD, so
binding depletes the free titrant and the 1:1 hyperbola no longer gives the KD; a
quadratic fit (or an explicit consideration of the depletion) is needed.

What this method does not ask (items of the other binding experiments left out
because an FCS titration in solution has no such thing): a surface and its
regeneration, mass transport, a sensorgram baseline, the kinetic rate constants,
a competition format and the donor and the acceptor of FRET. The laser power, the
brightness, the structure parameter, the temperature, the spread and the
statement that only this method was used are kept in the record for the
reviewer; no criterion judges them.
"""

VERSION = 'a105_fcs_criteria_v1'

# ---- Threshold constants -------------------------------------------------
CUBE_ROOT_EXPONENT = 1 / 3  # FIXED_BY_DEFINITION: the diffusion time of a compact particle grows with the cube root of its mass (the Stokes-Einstein relation with a radius that grows with the cube root of the mass).
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.
S_PER_UNIT = {'s': 1.0, 'min': 60.0}  # FIXED_BY_DEFINITION: seconds per time unit.
US_PER_UNIT = {'us': 1.0, 'ms': 1000.0}  # FIXED_BY_DEFINITION: microseconds per time unit.
PARTICLES_PER_NM_PER_FL = 0.6022  # FIXED_BY_DEFINITION: molecules in one femtolitre at one nanomolar (Avogadro's constant 6.022e23 per mole, times 1e-9 mol per litre, times 1e-15 litre).


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
FCS_CRITERIA = (
    {
        'id': 'diffusion_change',
        'question': 'Is the diffusion of the complex slow enough, against the free labelled partner, to read a fraction bound?',
        'reads': ('quantities.free_diffusion_time', 'quantities.bound_diffusion_time', 'quantities.free_diffusion_coefficient', 'quantities.bound_diffusion_coefficient', 'quantities.free_diffusion_time_spread', 'readout_signal'),
        'rule': 'The diffusion ratio is bound over free diffusion time when both are given, else free over bound diffusion coefficient. The grader records it (diffusion_ratio) and its refs (diffusion_refs) and, when the spread of the free diffusion time and the free diffusion time are both given, the scatter of the free time relative to it (diffusion_time_scatter, with the refs of both added to diffusion_refs); it leaves the judgement to the sheet. Nothing given is unknown, except that a brightness or cross-correlation readout, which does not read the diffusion, is not applicable.',
        'thresholds': ('US_PER_UNIT',),
        'returns': (
            ('unknown', 'diffusion_ratio_recorded_for_the_sheet', 'a pair of free and bound values is given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'diffusion_values_not_given', 'no pair of free and bound values is given'),
            ('not_applicable', 'readout_is_not_the_diffusion', 'no pair is given and the readout is brightness or cross-correlation'),
        ),
    },
    {
        'id': 'mass_consistency',
        'question': 'Does the change of the diffusion agree with the size of the change of mass of the cube-root law?',
        'reads': ('quantities.mass_ratio', 'quantities.free_diffusion_time', 'quantities.bound_diffusion_time', 'quantities.free_diffusion_coefficient', 'quantities.bound_diffusion_coefficient', 'readout_signal'),
        'rule': 'The expected diffusion ratio is the mass ratio to the power CUBE_ROOT_EXPONENT. When the mass ratio and the diffusion ratio are both given, the grader records them with the expected ratio (mass_ratio, diffusion_ratio, expected_diffusion_ratio) and their refs (mass_consistency_refs) and leaves the judgement to the sheet. The mass ratio or the diffusion ratio not given is unknown, except that a brightness or cross-correlation readout is not applicable.',
        'thresholds': ('CUBE_ROOT_EXPONENT', 'US_PER_UNIT'),
        'returns': (
            ('unknown', 'mass_consistency_recorded_for_the_sheet', 'both are given: the expected ratio is recorded and the sheet judges the agreement'),
            ('unknown', 'mass_ratio_or_diffusion_not_given', 'the mass ratio or the diffusion ratio is not given'),
            ('not_applicable', 'readout_is_not_the_diffusion', 'a value is missing and the readout is brightness or cross-correlation'),
        ),
    },
    {
        'id': 'saturation',
        'question': 'Did the fraction bound reach a plateau at the highest titrant concentration?',
        'reads': ('quantities.fraction_bound_maximum',),
        'rule': 'The largest fraction bound reached is recorded (fraction_bound_maximum, in percent, and fraction_bound_maximum_refs) and the judgement is left to the sheet. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'fraction_bound_maximum_recorded_for_the_sheet', 'the maximum is given: it is recorded and the sheet judges it'),
            ('unknown', 'fraction_bound_maximum_not_given', 'the maximum is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'diffusion_model',
        'question': 'Were the correlation curves fitted with a model that gives the fraction bound?',
        'reads': ('diffusion_model', 'facts.free_diffusion_time_fixed', 'quantities.free_diffusion_time', 'quantities.bound_diffusion_time', 'quantities.free_diffusion_coefficient', 'quantities.bound_diffusion_coefficient', 'readout_signal'),
        'rule': 'A two-component fit is supported when the free time was fixed from the free partner (stated yes), fails when it was not (stated no) and is unknown when not stated. A one-component fit is supported when the free and the bound reference values (both times or both coefficients) are given, otherwise unknown. An anomalous or other model is unknown. No model stated is unknown, except that a brightness or cross-correlation readout is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'two_component_with_free_time_fixed', 'two-component and the free time fixed is yes'),
            ('supported', 'one_component_with_reference_values', 'one-component and both reference values are given'),
            ('conflicting', 'two_component_with_free_time_not_fixed', 'two-component and the free time fixed is no'),
            ('unknown', 'free_time_fixing_not_stated', 'two-component and the free time fixing is not stated'),
            ('unknown', 'one_component_needs_free_and_bound_reference_values', 'one-component and a reference value is missing'),
            ('unknown', 'diffusion_model_anomalous_or_other', 'the model is anomalous or other'),
            ('unknown', 'diffusion_model_not_stated', 'no model stated'),
            ('not_applicable', 'readout_is_not_the_diffusion', 'no model stated and the readout is brightness or cross-correlation'),
        ),
    },
    _one_fact('triplet_state', 'Was the triplet state of the dye included in the fit?', 'triplet_state_modelled'),
    _one_fact('volume_calibration', 'Was the confocal volume calibrated with a reference dye of known diffusion coefficient?', 'confocal_volume_calibrated'),
    _one_fact('brightness', 'Was the difference of the brightness of the complex and the free partner accounted for?', 'brightness_change_accounted'),
    {
        'id': 'crosstalk',
        'question': 'Was the spectral cross-talk between the two colour channels corrected (dual-colour cross-correlation)?',
        'reads': ('facts.crosstalk_corrected', 'readout_signal'),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable; except that an unstated fact is not applicable for a single-colour readout (diffusion time, diffusion coefficient or brightness).',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown and the readout is cross-correlation or not stated'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
            ('not_applicable', 'single_colour_readout', 'answer unknown and the readout is a single-colour one'),
        ),
    },
    _one_fact('background', 'Was the background (dark counts, buffer or uncorrelated light) corrected?', 'background_corrected'),
    _one_fact('aggregates', 'Were aggregates and bright outliers excluded or checked?', 'aggregates_checked'),
    _one_fact('photobleaching', 'Were photobleaching and saturation of the dye checked, for example with a series of laser powers?', 'photobleaching_or_saturation_checked'),
    _one_fact('surface_adsorption', 'Was adsorption of the partners to the chamber surface prevented (passivated chamber, carrier protein or detergent)?', 'surface_adsorption_prevented'),
    _one_fact('labelling', 'Was it shown that the fluorescent label does not alter the binding?', 'labelling_does_not_alter_binding'),
    _one_fact('specificity_control', 'Was the specificity shown by a control with a partner that does not bind?', 'nonbinding_control_done'),
    {
        'id': 'labelled_range',
        'question': 'Was the labelled partner at a concentration that puts a few molecules in the confocal volume?',
        'reads': ('quantities.particle_number', 'quantities.labelled_concentration', 'quantities.detection_volume', 'quantities.brightness'),
        'rule': 'A given particle number is recorded (particle_number and labelled_range_refs). Without it, a given labelled concentration with a given detection volume is turned into a particle number (particle_number_used, derived: concentration times volume times PARTICLES_PER_NM_PER_FL). Without either, a given labelled concentration is recorded (labelled_nM, in nM). When a particle number (stated or derived) and the molecular brightness are given, the total count rate (count_rate_kHz, the particle number times the brightness) is recorded, with the brightness ref added to labelled_range_refs. The judgement is left to the sheet. Nothing given is unknown.',
        'thresholds': ('NM_PER_UNIT', 'PARTICLES_PER_NM_PER_FL'),
        'returns': (
            ('unknown', 'particle_number_recorded_for_the_sheet', 'the particle number is given: it is recorded and the sheet judges it'),
            ('unknown', 'particle_number_derived_from_volume_recorded_for_the_sheet', 'no particle number, and the concentration and the detection volume are given: the derived particle number is recorded and the sheet judges it'),
            ('unknown', 'labelled_concentration_recorded_for_the_sheet', 'no particle number and no detection volume and the concentration is given: it is recorded and the sheet judges it'),
            ('unknown', 'labelled_concentration_not_given', 'neither is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'labelled_over_kd',
        'question': 'Was the labelled partner at or below the KD, or was depletion handled by a tight-binding analysis?',
        'reads': ('quantities.labelled_concentration', 'quantities.kd', 'fit_model', 'facts.labelled_partner_at_or_below_kd', 'facts.tight_binding_considered'),
        'rule': 'With the labelled concentration and the KD both given, the grader records their quotient (labelled_over_kd), whether the analysis is tight-binding (tight_binding_analysis: a quadratic fit, or tight binding stated as considered) and the refs of these (labelled_over_kd_refs), and leaves the judgement to the sheet. With either number missing, the fact that the labelled partner is at or below the KD decides: yes supported; no is supported when the analysis is tight-binding and fails otherwise; not stated is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'labelled_over_kd_recorded_for_the_sheet', 'both are given: the quotient is recorded and the sheet judges it'),
            ('supported', 'labelled_at_or_below_kd', 'not both given and the fact is yes'),
            ('supported', 'labelled_above_kd_with_tight_binding_analysis', 'not both given, the fact is no and the fit is quadratic or tight binding is stated considered'),
            ('conflicting', 'labelled_above_kd_without_tight_binding_analysis', 'not both given, the fact is no and neither'),
            ('unknown', 'labelled_or_kd_missing', 'no ratio and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Did the titrant concentrations bracket the KD well enough to define the binding curve?',
        'reads': ('quantities.kd', 'quantities.titration_point_count', 'concentration_series'),
        'rule': 'The grader records the number of concentrations (concentration_count: the listed series, or else the stated number of points) with its refs (concentration_count_refs) and, when the KD and the list are both given, the lowest and the highest concentration over the KD (concentration_low_over_constant, concentration_high_over_constant) with their refs (concentration_span_refs); the judgement is left to the sheet. The span can only be recorded from the list.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'concentration_series_recorded_for_the_sheet', 'a count is known (listed or stated): it, and the span when the KD and the list are given, are recorded and the sheet judges them'),
            ('unknown', 'kd_or_series_missing', 'no count is known'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when read?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time', 'quantities.kd'),
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
        'id': 'acquisition',
        'question': 'Was each sample measured long enough for a stable correlation curve?',
        'reads': ('quantities.measurement_time', 'quantities.measurement_repeat_count', 'quantities.brightness', 'quantities.free_diffusion_time'),
        'rule': 'The total acquisition time is the time of one measurement times its number of repeats (one repeat when the number is not given). The grader records it (acquisition_total_s), whether the repeat count is given (measurement_repeats_given), the molecular brightness (brightness_kHz) and the free diffusion time (free_diffusion_time_us) when given, and the refs of all of these (acquisition_refs) and leaves the judgement to the sheet. No time is unknown.',
        'thresholds': ('S_PER_UNIT',),
        'returns': (
            ('unknown', 'acquisition_recorded_for_the_sheet', 'a measurement time is given: the total is recorded and the sheet judges it'),
            ('unknown', 'measurement_time_not_given', 'no measurement time'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the model of the binding curve stated?',
        'reads': ('fit_model',),
        'rule': 'The model must be stated (1:1, hill, quadratic or other); its support is the quoted span of the reported KD it was fitted to. Not stated is unknown; stated with no reported KD (no span supports it) is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a binding model stated and a KD is reported'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('unknown', 'model_stated_without_a_reported_kd', 'a binding model stated and no KD reported: no span supports it'),
            ('conflicting', 'never', 'never returned'),
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
)
