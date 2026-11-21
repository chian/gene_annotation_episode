"""Chunks of text for the AlphaScreen extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree and micro signs) so byte
offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the optimal assay concentrations (the matrix cross-titration and the hook effect) of
'Identification of a small-molecule ligand of the epigenetic reader protein Spindlin1 via a versatile screening platform' (Nucleic Acids
Research 2016, doi 10.1093/nar/gkw089, PMC4872087, PMID 26893353, open access, CC BY), as the publisher's XML gives the paragraph's own
text (a Greek mu U+03BC in 'μg/ml', not the micro sign, and an en dash U+2013 in 'biotin-H3(1–23)K4me3'). The paragraph is whole (one line
in the XML, no sentence was removed). It describes an AlphaLISA pretest of the bead concentrations with a biotin-6xHis peptide (the
manufacturer's 25 μg/ml and 17 μg/ml 'for both, acceptor- and donor beads'), a matrix cross-titration of His-Spindlin1 and
biotin-H3(1–23)K4me3 with Ni-NTA acceptor beads and streptavidin donor beads, the hook effect that was found for the streptavidin
donor beads above 50 nM of the biotinylated peptide and not for the Ni-NTA acceptor beads up to 500 nM of the protein, and the choice of
15 nM His-Spindlin1 and 30 nM biotin-H3(1–23)K4me3 'for subsequent experiments' as 'a compromise between an appropriate assay window and
a reliable prevention of the hook-effect'. It gives no KD, EC50, IC50 or Ki value, no signal, background, signal-to-background or Z'
value, no incubation time, temperature, plate format, replicate count or list of concentrations, no fit model, and no statement of a
counter-screen, a linear range, equilibrium, a non-binding control, avidity, an effect of the tag or protection from light.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_extraction import (
    ACCEPTOR_BEAD, ASSAY_FORMAT, DONOR_BEAD, FIT_MODEL, SERIES, SPREAD_KIND, TITRATION_DESIGN, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_record import UNITS

PAPER_ID = 'PMC4872087'
REAL = (
    "In a pretest we evaluated the optimal acceptor- and donor bead concentrations for the Alpha assay using a biotin-6xHis peptide which interacts with both bead species bringing them into proximity to generate an Alpha signal. "
    "Besides the manufacturer's recommendation of 25 μg/ml (final concentration) of both bead types, we tested several dilutions of a 1:1 acceptor- and donor bead mixture (data not shown). "
    "We observed an appropriate assay window at a concentration of 17 μg/ml for both, acceptor- and donor beads (1/300 dilution of a 5 mg/ml stock-suspension), in the final assay volume. "
    "Next, we were scouting for the optimal assay concentrations of both, His-Spindlin1 and its ligand biotin-H3(1–23)K4me3. "
    "Therefore, we conducted a matrix cross-titration of His-Spindlin1 and biotin-H3(1–23)K4me3 on a microplate. "
    "After incubation of the plate and addition of Ni-NTA acceptor beads and streptavidin donor beads the Alpha signals were collected and plotted against the concentrations of His-Spindlin1 and biotin-H3K4me3 concentrations, respectively. "
    "The resulting titration curves showed the so-called hook-effect which is typically observed when the concentration of analytes exceeds the binding capacity of the respective bead-type leading to dilution effects and non-statistical distribution of bead-bound and unbound Spindlin1/biotin-H3K4me3 complexes. "
    "The characteristic shape of such a curve shows an initial increase of the Alpha signal as the concentration of one binding partner increases followed by a decrease of the signal after the concentration of the binding partner surpasses the binding capacity of the respective Alpha bead. "
    "In our experiment we observed a significant saturation and dilution effect for the streptavidin coated donor beads at concentrations of the biotinylated peptide exceeding 50 nM (final concentration). "
    "For the acceptor beads no hook-effect could be observed with His-Spindlin1 up to concentrations equal to 500 nM of the protein (see Figure 1B). "
    "According to the manufacturer this apparent discrepancy in binding capacity of the streptavidin donor beads and the Ni-NTA acceptor beads is due to the fact that the 6xHis-Ni-NTA interaction is weaker compared to the biotin-streptavidin interaction. "
    "Thus, more 6xHis-tagged protein dissociates from the acceptor beads at equilibrium which is why the hook-point is typically reached at higher protein concentrations for the Ni-NTA acceptor beads compared to the streptavidin donor beads. "
    "As a result of this experiment we chose a His-Spindlin1 concentration of 15 nM for subsequent experiments and a biotin-H3(1–23)K4me3 concentration of 30 nM, respectively. "
    "These concentrations display a compromise between an appropriate assay window and a reliable prevention of the hook-effect.")

SYNTHETIC = (
    'Binding of ParB to ParA was measured by AlphaScreen at 25 °C in 384-well plates. The assay was about the protein ParA and its partner ParB. ParA carried a biotin and was captured on streptavidin donor beads, '
    'and ParB carried a His tag and was captured on nickel chelate acceptor beads, each bead kind at a final concentration of 20 µg/mL. Biotinylated ParA was '
    'held at 5 nM while His-ParB was titrated at 12 concentrations of 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM. The partners were incubated for '
    '60 min, and after the beads were added the plate was incubated for another 45 min before it was read. All steps with donor beads were done under subdued '
    'light. The signal at the top of the curve was 450000 cps over a background of 900 cps, a signal-to-background ratio of 500, and the Z\' factor was 0.8; '
    'the signal stayed within the linear range of the reader. A counter-screen with a biotinylated His-tagged control peptide showed no interference with the '
    'signal. The hook effect was avoided by fitting only the rising part of the curve with a four-parameter logistic model, and the biotinylated ParA at 5 nM '
    'was below the KD, so it did not deplete His-ParB. The binding was at equilibrium because a longer incubation of 3 h gave the same signal. A non-binding '
    'mutant of ParA gave no signal, the capture on the beads did not alter the binding because capture through an anti-tag antibody gave the same result, and '
    'multivalent binding on the beads was excluded by a low capture density. The fit gave an apparent KD = 20 nM (standard error 2 nM) and an EC50 of 28 nM. '
    'In a competition format 5 nM biotinylated ParA and 10 nM His-tagged ParB were mixed with an unlabelled competitor, which gave an IC50 of 45 nM and '
    'Ki = 30 nM (standard error 3 nM). Each concentration was measured in 3 wells, and 3 independent experiments were done on separate plates with fresh '
    'dilutions. The affinity was also measured by isothermal titration calorimetry.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'apparent KD = 20 nM'),
    'ki': (30, 'nM', 'Ki = 30 nM'),
    'ec50': (28, 'nM', 'an EC50 of 28 nM'),
    'ic50': (45, 'nM', 'an IC50 of 45 nM'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'ki_spread': (3, 'nM', 'standard error 3 nM'),
    'signal_maximum': (450000, 'cps', 'The signal at the top of the curve was 450000 cps'),
    'signal_background': (900, 'cps', 'a background of 900 cps'),
    'signal_to_background': (500, 'ratio', 'a signal-to-background ratio of 500'),
    'z_prime': (0.8, 'ratio', "the Z' factor was 0.8"),
    'bead_concentration': (20, 'ug/mL', 'each bead kind at a final concentration of 20 µg/mL'),
    'labelled_partner_concentration': (5, 'nM', 'Biotinylated ParA was held at 5 nM'),
    'tagged_partner_concentration': (10, 'nM', '10 nM His-tagged ParB'),
    'plate_well_count': (384, 'count', '384-well plates'),
    'titration_point_count': (12, 'count', '12 concentrations'),
    'technical_replicate_count': (3, 'count', 'measured in 3 wells'),
    'incubation_time': (60, 'min', 'The partners were incubated for 60 min'),
    'bead_incubation_time': (45, 'min', 'the plate was incubated for another 45 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'replicate_count': (3, 'count', '3 independent experiments'),
    SERIES: ([1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048], 'nM', '1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM'),
    ASSAY_FORMAT: ('saturation_titration', None, 'His-ParB was titrated at 12 concentrations'),
    TITRATION_DESIGN: ('fixed_partner_titration', None, 'Biotinylated ParA was held at 5 nM while His-ParB was titrated'),
    DONOR_BEAD: ('streptavidin', None, 'captured on streptavidin donor beads'),
    ACCEPTOR_BEAD: ('nickel_chelate', None, 'captured on nickel chelate acceptor beads'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('four_parameter_logistic', None, 'with a four-parameter logistic model'),
    'counter_screen_done': ('yes', None, 'A counter-screen with a biotinylated His-tagged control peptide showed no interference with the signal'),
    'hook_effect_handled': ('yes', None, 'The hook effect was avoided by fitting only the rising part of the curve'),
    'partner_concentration_below_kd': ('yes', None, 'the biotinylated ParA at 5 nM was below the KD'),
    'signal_in_linear_range': ('yes', None, 'the signal stayed within the linear range of the reader'),
    'equilibrium_reached': ('yes', None, 'The binding was at equilibrium because a longer incubation of 3 h gave the same signal'),
    'nonspecific_binding_checked': ('yes', None, 'A non-binding mutant of ParA gave no signal'),
    'capture_does_not_alter_binding': ('yes', None, 'the capture on the beads did not alter the binding'),
    'light_protected': ('yes', None, 'under subdued light'),
    'avidity_excluded': ('yes', None, 'multivalent binding on the beads was excluded by a low capture density'),
    'independent_experiments': ('yes', None, '3 independent experiments were done on separate plates'),
    'single_estimate_method': ('no', None, 'also measured by isothermal titration calorimetry'),
}

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about.
REAL_STATED = {
    'bead_concentration': (17, 'ug/mL', '17 μg/ml for both, acceptor- and donor beads'),
    DONOR_BEAD: ('streptavidin', None, 'Ni-NTA acceptor beads and streptavidin donor beads'),
    ACCEPTOR_BEAD: ('nickel_chelate', None, 'Ni-NTA acceptor beads and streptavidin donor beads'),
    TITRATION_DESIGN: ('cross_titration', None, 'we conducted a matrix cross-titration of His-Spindlin1 and biotin-H3(1–23)K4me3'),
    'hook_effect_handled': ('yes', None, 'a reliable prevention of the hook-effect'),
}
# What else a careful reader may also state from the real passage: nothing. The 15 nM and 30 nM partner concentrations are
# concentrations chosen 'for subsequent experiments' from the cross-titration, not those of the cross-titration itself, so they are
# not in the allowed set (a model that states them is reported, not allowed).
REAL_MAY_ALSO_STATE = set()

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'para'
SYNTHETIC_PARTNER = 'parb'
# The passage names His-Spindlin1 and 'its ligand biotin-H3(1–23)K4me3' (en dash U+2013). The biotin-6xHis peptide of the bead pretest
# is a reagent, not a partner.
REAL_EXPECTED_TARGET = 'his-spindlin1'
REAL_EXPECTED_PARTNER = 'biotin-h3(1-23)k4me3'
REAL_EXPECTED_PAIR = (('spindlin1', 'his-spindlin1'), ('biotin-h3(1-23)k4me3',))     # symmetric pair named by the paragraph; either orientation accepted


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
