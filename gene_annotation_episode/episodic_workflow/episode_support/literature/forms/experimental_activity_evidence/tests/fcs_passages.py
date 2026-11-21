"""Chunks of text for the FCS extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (a degree sign, micro signs and
superscript twos) so byte offsets differ from character offsets.

``REAL`` is real: the Results paragraph 'Measurement of Binding Affinity' of 'Fluorescence Correlation Spectroscopy as a Versatile
Method to Define Aptamer-Protein Interactions with Single-Molecule Sensitivity' (Analytical Chemistry 2023, doi
10.1021/acs.analchem.3c03341, PMC10782416, PMID 38124657, open access, CC BY 4.0), as the publisher's XML gives the paragraph's own
text (a Greek small letter tau U+03C4 in 'τD' and a plus-minus sign U+00B1 in 'KD = 5 ± 1 nM'; the reference numbers stay glued to
the words as the XML has them, '(eq 4).34Figure 2b' and 'sequences26'), except that the publisher's source line breaks inside
sentences (the XML has a line feed in the middle of most lines) are each one space. The paragraph is whole (no sentence was removed).
It states that 100 pM of fluorescent CLN3 aptamer was exposed to c-Met 'between 0 and 100 nM' (a range, not a list), that the
correlation curves were fitted with 'a model comprising a single effective diffusing species' giving an apparent diffusion time
τD, that the fraction bound was calculated from the apparent τD against reference values of the fully free and the fully bound
aptamer, that the curve was fitted with 'a simple binding model' (not named 1:1) giving 'KD = 5 ± 1 nM' (the kind of the
uncertainty is not stated), and that the KD is in line with dot blot and biolayer interferometry values. It gives no diffusion time
or coefficient (they are in the preceding Results paragraph, not in this chunk), no laser power, measurement time or repeat count
(they are in the Methods), no particle number, no maximum fraction bound, no list of concentrations, no incubation time, no
replicate count and no statement of any control, and does not say whether the aptamer concentration was at or below the KD.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_extraction import (
    DIFFUSION_MODEL, FIT_MODEL, READOUT_SIGNAL, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import UNITS

PAPER_ID = 'PMC10782416'
REAL = (
    'Having demonstrated that FCS readily detects the binding between CLN3 and the target c-Met protein, we performed an '
    'experiment to quantify the KD. To do that, 100 pM of fluorescent CLN3 were exposed to increasing concentrations of c-Met '
    'between 0 and 100 nM. Figure 2a shows the normalized autocorrelation curves, measured by FCS, where it is easily seen that '
    'the correlation shifts to longer lag times at increasing concentrations of c-Met, consistent with an increasing fraction of '
    'CLN3 that binds to the slow-diffusing protein. Even if the solutions contain two fluorescent species having different '
    'diffusion, i.e., the free aptamer and the complex, the autocorrelation curves were well-fitted with a model comprising a '
    'single effective diffusing species (eq 1), yielding an apparent τD value (representative results of the fit are shown in '
    'Figure S5). The fraction of protein-bound aptamer, or simply fraction bound, was then calculated by comparing the apparent '
    'τD obtained by the fit with reference values corresponding to the fully free aptamer and the fully protein-bound aptamer '
    '(eq 4).34Figure 2b shows in black the fraction of CLN3 bound to c-Met at increasing protein concentrations. The fraction '
    'bound grows significantly between 1 and 10 nM of c-Met. This trend was well-fitted with a simple binding model (eq 5, red '
    'line), yielding a KD = 5 ± 1 nM. The obtained KD is in line with the values measured during the selection and optimization '
    'of CLN3 by dot blot analysis of radiolabeled sequences26 and with a value obtained by biolayer interferometry.35')

SYNTHETIC = (
    'Binding of ParB to a fluorescently labelled peptide was measured by fluorescence correlation spectroscopy (FCS) at 25 °C. '
    'The assay was about the binding of the protein ParB to its partner PZ-2, the labelled peptide. '
    'The peptide was labelled with Alexa 488 and held at a constant 2 nM, below the KD, which put an average of 0.8 molecules in '
    'the confocal volume. ParB was added in 10 concentrations of 1, 2, 5, 10, 20, 50, 100, 200, 500 and 1000 nM, and each sample '
    'was incubated for 20 min after mixing; the diffusion time did not change over a further hour, so binding was at '
    'equilibrium. The confocal volume was calibrated with Rhodamine 6G, which gave a structure parameter of 5.2. Each '
    'measurement lasted 30 s and was repeated 5 times, at a laser power of 5 µW at the sample, with a brightness of 12 kHz per '
    'molecule. Photobleaching and saturation were checked with a series of laser powers, bright aggregates in the fluorescence '
    'trace were excluded, and the background was measured with buffer alone and corrected for. The chambers were passivated '
    'with BSA. The diffusion time of the peptide was the binding signal, and the correlation curves were fitted with a '
    'two-component diffusion model that included a triplet state term, with the diffusion time of the free peptide fixed to the '
    'value measured for the free peptide: the free peptide had a diffusion time of 60 µs and a diffusion coefficient D = 280 '
    'µm²/s, and the fully bound complex had a diffusion time of 108 µs and D = 156 µm²/s; the complex is 6-fold heavier than '
    'the free peptide. The difference between the brightness of the complex and of the free peptide was taken into account. A '
    'control cross-correlation measurement in two colours was also done, and the spectral cross-talk between the two channels '
    'was corrected. The fraction bound reached 92% at the highest ParB concentration. Labelled and unlabelled peptide gave the '
    'same affinity, so the label did not alter binding, and a non-binding peptide variant exposed to ParB gave no change of the '
    'diffusion time. Depletion of free ParB by tight binding was considered, and the fraction bound was fitted with a quadratic '
    '(tight-binding) model, giving KD = 20 nM (standard error 2 nM). The same interaction was also measured by isothermal '
    'titration calorimetry. Three independent titrations were done on separate days with fresh dilution series.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'labelled_concentration': (2, 'nM', 'held at a constant 2 nM'),
    'free_diffusion_time': (60, 'us', 'a diffusion time of 60 µs'),
    'bound_diffusion_time': (108, 'us', 'a diffusion time of 108 µs'),
    'free_diffusion_coefficient': (280, 'um2/s', 'D = 280 µm²/s'),
    'bound_diffusion_coefficient': (156, 'um2/s', 'D = 156 µm²/s'),
    'fraction_bound_maximum': (92, 'percent', 'The fraction bound reached 92%'),
    'particle_number': (0.8, 'molecules', 'an average of 0.8 molecules in the confocal volume'),
    'structure_parameter': (5.2, 'ratio', 'a structure parameter of 5.2'),
    'mass_ratio': (6, 'ratio', 'the complex is 6-fold heavier than the free peptide'),
    'brightness': (12, 'kHz', 'a brightness of 12 kHz per molecule'),
    'laser_power': (5, 'uW', 'a laser power of 5 µW at the sample'),
    'measurement_time': (30, 's', 'Each measurement lasted 30 s'),
    'measurement_repeat_count': (5, 'count', 'repeated 5 times'),
    'titration_point_count': (10, 'count', '10 concentrations'),
    'incubation_time': (20, 'min', 'incubated for 20 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'replicate_count': (3, 'count', 'Three independent titrations'),
    SERIES: ([1, 2, 5, 10, 20, 50, 100, 200, 500, 1000], 'nM', '1, 2, 5, 10, 20, 50, 100, 200, 500 and 1000 nM'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('quadratic', None, 'a quadratic (tight-binding) model'),
    DIFFUSION_MODEL: ('two_component', None, 'two-component diffusion model'),
    READOUT_SIGNAL: ('diffusion_time', None, 'The diffusion time of the peptide was the binding signal'),
    'confocal_volume_calibrated': ('yes', None, 'The confocal volume was calibrated with Rhodamine 6G'),
    'triplet_state_modelled': ('yes', None, 'included a triplet state term'),
    'free_diffusion_time_fixed': ('yes', None, 'the diffusion time of the free peptide fixed to the value measured for the free peptide'),
    'brightness_change_accounted': ('yes', None, 'The difference between the brightness of the complex and of the free peptide was taken into account'),
    'crosstalk_corrected': ('yes', None, 'the spectral cross-talk between the two channels was corrected'),
    'background_corrected': ('yes', None, 'the background was measured with buffer alone and corrected for'),
    'aggregates_checked': ('yes', None, 'bright aggregates in the fluorescence trace were excluded'),
    'photobleaching_or_saturation_checked': ('yes', None, 'Photobleaching and saturation were checked with a series of laser powers'),
    'surface_adsorption_prevented': ('yes', None, 'The chambers were passivated with BSA'),
    'labelling_does_not_alter_binding': ('yes', None, 'so the label did not alter binding'),
    'nonbinding_control_done': ('yes', None, 'a non-binding peptide variant exposed to ParB gave no change of the diffusion time'),
    'labelled_partner_at_or_below_kd': ('yes', None, 'below the KD'),
    'tight_binding_considered': ('yes', None, 'Depletion of free ParB by tight binding was considered'),
    'equilibrium_reached': ('yes', None, 'so binding was at equilibrium'),
    'independent_titrations': ('yes', None, 'Three independent titrations were done on separate days'),
    'single_estimate_method': ('no', None, 'also measured by isothermal titration calorimetry'),
}

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about.
REAL_STATED = {
    'kd': (5, 'nM', 'KD = 5 ± 1 nM'),
    'kd_spread': (1, 'nM', 'KD = 5 ± 1 nM'),
    'labelled_concentration': (100, 'pM', '100 pM of fluorescent CLN3'),
    DIFFUSION_MODEL: ('one_component', None, 'a model comprising a single effective diffusing species'),
    READOUT_SIGNAL: ('diffusion_time', None, 'comparing the apparent τD obtained by the fit'),
}
# What else a careful reader may also state from the real passage: that another method was also used for the KD (a value obtained by
# biolayer interferometry, and dot blot values). Nothing else: the concentrations are a range (0 and 100 nM), not a list; 'a simple
# binding model' is not named 1:1; the kind of the uncertainty of 5 ± 1 nM is not stated; no diffusion time or coefficient, particle
# number, maximum fraction bound, incubation, replicate count, calibration, correction or control is stated in the chunk.
REAL_MAY_ALSO_STATE = {'single_estimate_method'}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'pz-2'
# The passage itself calls c-Met 'the target c-Met protein' and the fluorescent CLN3 aptamer is the labelled partner. (A reader could
# argue the labelled molecule is the one assayed; the passage's own wording decides.)
REAL_EXPECTED_TARGET = 'c-met'
REAL_EXPECTED_PARTNER = 'cln3'


def answer_from(chunk, stated, support=None):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable. Every stated
    field has support 'direct' unless ``support`` (field -> support) names a weaker one; an unavailable field has none."""
    support = support or {}
    answer = {}
    for name in field_names():
        carries_unit = name in UNITS
        if name in stated:
            value, unit, quote = stated[name]
            answer[name] = {'status': 'stated', 'value': value, 'quote': quote, 'support': support.get(name, 'direct'), 'reason': None,
                            **({'unit': unit} if carries_unit else {})}
        else:
            answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None,
                            'reason': 'not_stated_in_passage', **({'unit': None} if carries_unit else {})}
    return answer


def synthetic_answer():
    return answer_from(SYNTHETIC, SYNTHETIC_STATED)


def real_answer():
    return answer_from(REAL, REAL_STATED)
