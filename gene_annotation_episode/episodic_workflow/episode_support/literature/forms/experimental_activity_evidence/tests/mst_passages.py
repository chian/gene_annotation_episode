"""Chunks of text for the MST extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the MST form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (a micro sign, a degree sign and
a per-mille sign) so byte offsets differ from character offsets.

``REAL`` is real: the Methods paragraph on the MicroScale Thermophoresis measurement in 'Structural basis for selective thymidine
binding by the Borrelia burgdorferi substrate-binding protein BmpA' (Journal of Biological Chemistry 2026, doi
10.1016/j.jbc.2026.113206, PMC13325309, PMID 42208901, open access, CC BY 4.0), exactly as the publisher's XML gives the paragraph's
own text (a right single quotation mark U+2019 in 'manufacturer's' and a Greek mu U+03BC in '100 uM'). The paragraph is whole (no
sentence was removed). It states that BmpA was labelled with NHS-RED dye, diluted to a final concentration of 10 nM in a buffer with
0.05% Tween-20, titrated with a series of ligand dilutions given as a range from 100 uM to 3.05 nM (not as a list of
concentrations), mixed in equal volumes and incubated for 10 min at room temperature 'to ensure binding equilibrium', loaded into
'standard MST premium capillaries', measured on a 'Monolith LabelFree/pico RED' instrument at 100% excitation power and 'medium MST
power', in triplicate, with the Kd from a fit of the normalized fluorescence against the logarithm of the ligand concentration using a
1:1 binding model. It gives no Kd (the Kd values are in the Results paragraph, not in this chunk), no spread, no signal size, no
F-hot time, no readout kind, no check of the initial fluorescence, of aggregation or of a control, and says nothing of the
independence of the triplicates."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_extraction import (
    ASSAY_FORMAT, CAPILLARY_TYPE, FIT_MODEL, LABEL_TYPE, READOUT_SIGNAL, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_record import UNITS

PAPER_ID = 'PMC13325309'
REAL = (
    'Binding interactions between BmpA and select ligands were assessed using MicroScale Thermophoresis. Purified BmpA was '
    'fluorescently labeled with NHS-RED dye following the manufacturer’s protocol (NanoTemper Technologies). The labeled '
    'BmpA was diluted to a final concentration of 10 nM in PBST buffer (phosphate-buffered saline, 0.05% Tween-20, pH 7.4). A '
    'series of ligand dilutions was prepared to achieve a concentration range from 100 μM to 3.05 nM. Each MST reaction '
    'consisted of mixing equal volumes of NHS-RED-labeled BmpA and nucleoside solution, followed by a 10-min incubation at room '
    'temperature to ensure binding equilibrium. Prepared samples were loaded into standard MST premium capillaries (NanoTemper '
    'Technologies). Measurements were taken using a Monolith LabelFree/pico RED instrument set to 100% excitation power and '
    'medium MST power. All experiments were performed in triplicate. Data analysis was performed using MO.Affinity Analysis '
    'software (NanoTemper Technologies). Binding affinities (Kd) were determined by fitting the normalized fluorescence '
    'responses against the logarithm of ligand concentration using a 1:1 binding model.')

SYNTHETIC = (
    'MST binding assays were done on a Monolith instrument. The assay measured the binding of the protein ParB to its '
    'partner PopZ. ParB was labelled covalently with an NHS-ester red dye, and '
    'labelled and unlabelled ParB gave the same affinity, so the label did not alter binding. Samples of 10 µL in a '
    'buffer with 0.05% Tween-20 were drawn into hydrophilic capillaries and incubated for 15 min at 25 °C; the signal '
    'did not change with a further hour, so binding was at equilibrium. The excitation LED power was 40% and the MST '
    '(infrared laser) power was 60%. Fnorm was read as thermophoresis, with F-hot taken 1.5 s after the infrared laser was '
    'switched on. In the direct titration, the labelled ParB was held at 5 nM, below the KD, and its peptide partner was '
    'titrated in 12 titrant concentrations of 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM. The initial '
    'fluorescence was checked with the SD-test and did not change with the titrant concentration, and the fluorescence '
    'intensity was within the range of the instrument. The capillary scans were overlaid and the peak shapes were checked '
    'for aggregation and adsorption. The change of Fnorm was 12 ‰ with a signal-to-noise of 18, and the noise of Fnorm was 0.7 ‰. Depletion was '
    'considered, and the data were fitted with a quadratic (tight-binding) model, giving KD = 20 nM (standard error 2 nM) and '
    'EC50 = 31 nM. Non-specific signal was checked with a non-binding mutant peptide. The same interaction was also '
    'measured by competition, in which an unlabelled ligand displaced the labelled peptide and gave Ki = 40 nM (standard '
    'error 4 nM); the affinity was thus estimated both by direct titration and by competition. Three independent titrations '
    'were done on separate days with fresh dilution series.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'ki': (40, 'nM', 'Ki = 40 nM'),
    'ec50': (31, 'nM', 'EC50 = 31 nM'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'ki_spread': (4, 'nM', 'standard error 4 nM'),
    'labelled_concentration': (5, 'nM', 'the labelled ParB was held at 5 nM'),
    'fnorm_amplitude': (12, 'permille', 'The change of Fnorm was 12 ‰'),
    'fnorm_noise': (0.7, 'permille', 'the noise of Fnorm was 0.7 ‰'),
    'signal_to_noise': (18, 'ratio', 'a signal-to-noise of 18'),
    'led_power': (40, 'percent', 'The excitation LED power was 40%'),
    'ir_laser_power': (60, 'percent', 'the MST (infrared laser) power was 60%'),
    'fhot_time': (1.5, 's', 'F-hot taken 1.5 s after'),
    'titration_point_count': (12, 'count', '12 titrant concentrations'),
    'incubation_time': (15, 'min', 'incubated for 15 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'replicate_count': (3, 'count', 'Three independent titrations'),
    SERIES: ([1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048], 'nM', '12 titrant concentrations of 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM'),
    ASSAY_FORMAT: ('direct_titration', None, 'In the direct titration'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('quadratic', None, 'a quadratic (tight-binding) model'),
    READOUT_SIGNAL: ('thermophoresis', None, 'Fnorm was read as thermophoresis'),
    CAPILLARY_TYPE: ('hydrophilic', None, 'hydrophilic capillaries'),
    LABEL_TYPE: ('covalent_nhs_dye', None, 'labelled covalently with an NHS-ester red dye'),
    'initial_fluorescence_checked': ('yes', None, 'The initial fluorescence was checked with the SD-test'),
    'initial_fluorescence_consistent': ('yes', None, 'did not change with the titrant concentration'),
    'fluorescence_intensity_in_range': ('yes', None, 'the fluorescence intensity was within the range of the instrument'),
    'aggregation_or_adsorption_checked': ('yes', None, 'the peak shapes were checked for aggregation and adsorption'),
    'detergent_or_carrier_in_buffer': ('yes', None, '0.05% Tween-20'),
    'labelled_partner_at_or_below_kd': ('yes', None, 'was held at 5 nM, below the KD'),
    'tight_binding_considered': ('yes', None, 'Depletion was considered'),
    'equilibrium_reached': ('yes', None, 'so binding was at equilibrium'),
    'labelling_does_not_alter_binding': ('yes', None, 'so the label did not alter binding'),
    'nonspecific_binding_checked': ('yes', None, 'Non-specific signal was checked with a non-binding mutant peptide'),
    'independent_titrations': ('yes', None, 'Three independent titrations were done on separate days'),
    'single_estimate_method': ('no', None, 'estimated both by direct titration and by competition'),
}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'popz'
# The real paragraph assesses binding of BmpA (the labelled protein) to 'select ligands' (nucleosides, none named), so the
# target is BmpA and no single partner is named.
REAL_EXPECTED_TARGET = 'bmpa'
REAL_EXPECTED_PARTNER = None

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about.
REAL_STATED = {
    'labelled_concentration': (10, 'nM', 'diluted to a final concentration of 10 nM'),
    'incubation_time': (10, 'min', 'a 10-min incubation'),
    'led_power': (100, 'percent', '100% excitation power'),
    'replicate_count': (3, 'count', 'All experiments were performed in triplicate'),
    FIT_MODEL: ('1:1', None, 'using a 1:1 binding model'),
    LABEL_TYPE: ('covalent_nhs_dye', None, 'fluorescently labeled with NHS-RED dye'),
    'detergent_or_carrier_in_buffer': ('yes', None, '0.05% Tween-20'),
}
# What else a careful reader may also state from the real passage (a judgement the passage supports, not a number): that the
# ligand series was titrated against the labelled BmpA (a direct titration). The paragraph gives no list of concentrations (a
# range), no number for the MST power ('medium'), no temperature value ('room temperature'), no readout kind, no signal size, no
# check of the initial fluorescence, of aggregation or of a control, and does not say the triplicates were independent; the
# incubation 'to ensure binding equilibrium' states an intention and not that equilibrium was shown; 'standard MST premium
# capillaries' names two kinds; and the instrument's name 'LabelFree/pico RED' is not a statement that the detection was label-free:
# none of those may be stated.
REAL_MAY_ALSO_STATE = {ASSAY_FORMAT}


def answer_from(chunk, stated, supports=None):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable. A stated field's
    support is ``supports[name]`` or 'direct'; an unavailable field has none."""
    supports = supports or {}
    answer = {}
    for name in field_names():
        carries_unit = name in UNITS
        if name in stated:
            value, unit, quote = stated[name]
            answer[name] = {'status': 'stated', 'value': value, 'quote': quote, 'support': supports.get(name, 'direct'), 'reason': None,
                            **({'unit': unit} if carries_unit else {})}
        else:
            answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None,
                            'reason': 'not_stated_in_passage', **({'unit': None} if carries_unit else {})}
    return answer


def synthetic_answer():
    return answer_from(SYNTHETIC, SYNTHETIC_STATED)


def real_answer():
    return answer_from(REAL, REAL_STATED)
