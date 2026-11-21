"""Chunks of text for the ELISA extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree and micro signs) so byte
offsets differ from character offsets.

``REAL`` is real: the Methods paragraph 'Solid-phase binding assay' of 'Structural analyses define the molecular basis of clusterin
chaperone function' (Nature Structural & Molecular Biology 2025, doi 10.1038/s41594-025-01631-4, PMC12527946, PMID 40781479, open
access, CC BY 4.0), as the publisher's XML gives the paragraph's own text (a thin space U+2009 between every number and its unit, '100 µl', '10 µg ml−1',
'4 °C', '1 h', '450 nm'; a micro sign U+00B5 in 'µl' and 'µg', a minus sign U+2212 in 'ml−1' and a degree sign U+00B0 in '4 °C'; the reference numbers and the subscript stay glued to the words as the XML has them,
'described41', 'CaCl2', 'KD' and 'v1)86.'). The paragraph is whole (one line in the XML, no sentence was removed). It describes an
ELISA-type solid-phase binding of the ligands Clu or RAP to a plate coated with the VLDLR ectodomain (10 µg ml−1, overnight at
4 °C), blocked with 2% BSA, the ligands in 'different concentrations' for 1 h at room temperature (and, 'for the competition assay',
100 nM of Clu with increasing concentrations of RAP), three washes with blocking solution after the ligand, an anti-Clu or anti-RAP
antibody, an HRP-conjugated goat anti-mouse IgG, a TMB substrate, absorbance at 450 nm, background from wells coated with BSA, the
no-ligand well signal subtracted, and KD values fitted with 'binding, saturation, one-site-specific binding'. It gives no KD, EC50,
IC50 or Ki value (they are in the Results), no list or number of the concentrations, no plateau or background absorbance, no
temperature as a number ('room temperature'), no replicate count, and no statement of equilibrium, of dissociation during the
washes, of avidity, of the activity of the coated protein or of the interference of the detection reagent. It describes a titration
and a competition together, and it has an earlier 'washed once' (before blocking) and three washes after the ligand, the antibody and
the conjugate.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_extraction import (
    ASSAY_FORMAT, BLOCKING_AGENT, DETECTION_FORMAT, ENZYME_CONJUGATE, FIT_MODEL, READOUT_SIGNAL, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_record import UNITS

PAPER_ID = 'PMC12527946'
REAL = (
    'The assay was performed as previously described41. The 96-well plate (Nunc-immuno MicroWell 96-well solid plate; Merck) was coated with 100 µl of TBS-C '
    '(Tris-buffered saline pH 7.4 and 2 mM CaCl2) containing 10 µg ml−1 VLDLR-ed overnight at 4 °C. The plate was washed once with TBS-C and incubated for '
    '2 h at room temperature with TBS-C blocking buffer (2% BSA and 0.05% Tween-20). The plate was then incubated with different concentrations of the '
    'ligands Clu or RAP in blocking solution for 1 h at room temperature. For the competition assay, the plate was incubated with 100 nM of Clu in the '
    'presence of increasing concentrations of RAP. The plate was washed three times with blocking solution. Anti-Clu (sc-5289, Santa Cruz Biotechnologies; '
    'dilution 1:100) or anti-RAP (sc-515625, Santa Cruz Biotechnologies; dilution 1:100) antibodies were added in TBS-C blocking solution and incubated for '
    '1 h at room temperature. The plate was washed three times with TBS-C blocking solution and incubated with horseradish peroxidase (HRP)-conjugated goat '
    'anti-mouse IgG (A4416, Merck; dilution 1:10,000) added in TBS-C blocking solution and incubated for 1 h at room temperature. The plate was washed three '
    'times with TBS-C blocking solution and developed by adding 100 µl per well of the HRP substrate one-step Ultra TMB ELISA substrate solution (Thermo '
    'Fisher Scientific) and the reaction was quenched with 100 µl per well of 2 M sulfuric acid. Absorbance at 450 nm was measured in a Spark multimode '
    'microplate reader (Tecan). Binding to wells coated with BSA was used to estimate the background signal for each sample and the no-ligand well signal '
    'was subtracted from the rest of the samples. The KD values were obtained by fitting the data using GraphPad Prism 10 software (www.graphpad.com) '
    '(binding, saturation, one-site-specific binding). A detailed protocol is available from protocols.io (10.17504/protocols.io.yxmvm36kol3p/v1)86.')

SYNTHETIC = (
    'Binding of ParB to coated ParA was measured by an indirect ELISA at 25 °C. The assay was about the coated protein ParA and its ligand ParB. Plates were coated with ParA at a concentration of 2 µg/mL and blocked with '
    'bovine serum albumin. ParB was added in 12 concentrations of 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM. The binding step lasted 90 min, '
    'and the binding was at equilibrium because a longer binding step of 3 h gave the same signal. Plates were washed 3 times after the binding step, and the '
    'dissociation of the complex during the washes was shown to be negligible by a rapid wash that gave the same signal. Bound ParB was detected with a '
    'horseradish peroxidase conjugated anti-His antibody, and the plates were read as absorbance at 450 nm, which gave a plateau of 1.2 OD over a background '
    'of 0.06 OD; the signal stayed within the linear range of the plate reader. The signal of blank wells without ParA was subtracted, and an uncoated well '
    'and an irrelevant protein gave no signal. ParA was coated through its tag by an anti-tag antibody and was shown to be active, multivalent binding was '
    'excluded by use of monomeric ParB, and the detection antibody did not interfere with the binding. The curve reached saturation and was fitted with a '
    'four-parameter logistic model, giving an apparent KD = 20 nM (standard error 2 nM) and an EC50 of 28 nM. In a competition ELISA an unlabelled competitor '
    'displaced 10 nM ParB, whose own KD was 15 nM, and gave an IC50 of 45 nM and Ki = 30 nM (standard error 3 nM). The reader was linear up to 2.5 OD. '
    'The dissociation rate constant of the complex was koff = 0.0001 s^-1, and the washes took 10 min in total. Each concentration was measured in 3 wells, and 3 independent experiments were done on '
    'separate plates with fresh dilutions. The affinity was also measured by surface plasmon resonance.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'apparent KD = 20 nM'),
    'ki': (30, 'nM', 'Ki = 30 nM'),
    'ec50': (28, 'nM', 'an EC50 of 28 nM'),
    'ic50': (45, 'nM', 'an IC50 of 45 nM'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'ki_spread': (3, 'nM', 'standard error 3 nM'),
    'coating_concentration': (2, 'ug/mL', 'at a concentration of 2 µg/mL'),
    'signal_maximum': (1.2, 'OD', 'a plateau of 1.2 OD'),
    'signal_background': (0.06, 'OD', 'a background of 0.06 OD'),
    'wash_count': (3, 'count', 'washed 3 times after the binding step'),
    'titration_point_count': (12, 'count', '12 concentrations'),
    'technical_replicate_count': (3, 'count', 'measured in 3 wells'),
    'incubation_time': (90, 'min', 'The binding step lasted 90 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'replicate_count': (3, 'count', '3 independent experiments'),
    SERIES: ([1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048], 'nM', '1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM'),
    ASSAY_FORMAT: ('saturation_titration', None, 'ParB was added in 12 concentrations'),
    DETECTION_FORMAT: ('indirect', None, 'an indirect ELISA'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('four_parameter_logistic', None, 'fitted with a four-parameter logistic model'),
    READOUT_SIGNAL: ('absorbance', None, 'read as absorbance at 450 nm'),
    ENZYME_CONJUGATE: ('horseradish_peroxidase', None, 'horseradish peroxidase conjugated anti-His antibody'),
    BLOCKING_AGENT: ('bsa', None, 'blocked with bovine serum albumin'),
    'blank_subtracted': ('yes', None, 'The signal of blank wells without ParA was subtracted'),
    'nonspecific_binding_checked': ('yes', None, 'an uncoated well and an irrelevant protein gave no signal'),
    'saturation_reached': ('yes', None, 'The curve reached saturation'),
    'signal_in_linear_range': ('yes', None, 'the signal stayed within the linear range of the plate reader'),
    'wash_dissociation_considered': ('yes', None, 'the dissociation of the complex during the washes was shown to be negligible'),
    'equilibrium_reached': ('yes', None, 'the binding was at equilibrium because a longer binding step of 3 h gave the same signal'),
    'avidity_excluded': ('yes', None, 'multivalent binding was excluded by use of monomeric ParB'),
    'coated_protein_active': ('yes', None, 'was shown to be active'),
    'detection_does_not_interfere': ('yes', None, 'the detection antibody did not interfere with the binding'),
    'independent_experiments': ('yes', None, '3 independent experiments were done on separate plates'),
    'single_estimate_method': ('no', None, 'also measured by surface plasmon resonance'),
    'tracer_concentration': (10, 'nM', 'displaced 10 nM ParB'),
    'tracer_kd': (15, 'nM', 'whose own KD was 15 nM'),
    'detector_linear_limit': (2.5, 'OD', 'The reader was linear up to 2.5 OD'),
    'koff': (0.0001, 's^-1', 'koff = 0.0001 s^-1'),
    'wash_duration': (10, 'min', 'the washes took 10 min in total'),
}

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about.
REAL_STATED = {
    'coating_concentration': (10, 'ug/mL', '10 µg ml−1 VLDLR-ed'),
    'incubation_time': (1, 'h', 'ligands Clu or RAP in blocking solution for 1 h'),
    'wash_count': (3, 'count', 'The plate was washed three times with blocking solution'),
    ENZYME_CONJUGATE: ('horseradish_peroxidase', None, 'horseradish peroxidase (HRP)-conjugated'),
    BLOCKING_AGENT: ('bsa', None, '2% BSA and 0.05% Tween-20'),
    READOUT_SIGNAL: ('absorbance', None, 'Absorbance at 450 nm was measured'),
    FIT_MODEL: ('1:1', None, 'binding, saturation, one-site-specific binding'),
    'blank_subtracted': ('yes', None, 'the no-ligand well signal was subtracted'),
}
# What else a careful reader may also state from the real passage: the detection by a primary and an enzyme-conjugated secondary
# antibody (indirect), the BSA-coated wells as a control (a specificity control), and, because the paragraph describes ligand
# titrations and, 'for the competition assay', a competition, a format. Nothing else: no KD, EC50, IC50 or Ki value, no list or
# number of concentrations, no plateau or background absorbance, no temperature as a number ('room temperature'), no replicate
# count, and no statement of equilibrium, wash dissociation, avidity, coated-protein activity or detection interference.
# Also (after the grader-gap pass): the tracer concentration, because 'for the competition assay, the plate was incubated with 100 nM of Clu in the
# presence of increasing concentrations of RAP' gives the constant concentration of the ligand RAP displaces (the quote '100 nM of Clu'). The
# paragraph gives no KD of that ligand (tracer_kd), no koff, no duration of the washes (only 'washed three times') and no stated reader linear
# range, so those four stay unavailable.
REAL_MAY_ALSO_STATE = {DETECTION_FORMAT, 'nonspecific_binding_checked', ASSAY_FORMAT, 'tracer_concentration'}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'para'
SYNTHETIC_PARTNER = 'parb'
# The plate is coated with the VLDLR ectodomain (VLDLR-ed), the protein whose ligand binding is assayed; the ligands are two (Clu or
# RAP), so no single partner is named.
REAL_EXPECTED_TARGET = 'vldlr-ed'
REAL_EXPECTED_PARTNER = None


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
