"""Chunks of text for the split-reporter (protein-fragment complementation: split luciferase such as NanoBiT, split GFP or BiFC, split beta-lactamase, split TEV) extraction real-model runs.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``SYNTHETIC_STATED`` lists the field, value, unit and quote of each. The leaf world puts text before it, so the byte offsets differ from zero.

``REAL`` is real: two consecutive Results paragraphs of 'Split NanoLuc technology allows quantitation of interactions between PII protein and its receptors with unprecedented sensitivity'
(PMC8206089, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0), as the licence statement of the publisher's XML (Europe PMC full text) says), the paragraphs on the titration of PipX-SmBiT to PII-LgBiT
that begin 'To quantitatively determine the dissociation constant of PII-PipX interaction' and 'At the concentration of PipX-SmBiT at which half maximal luminescence is observed', as the XML gives the text of each paragraph with the markup (italics, subscripts, the figure and table links) removed, joined by a blank line.
The text is exactly as the XML gives it, including its non-breaking spaces (``\\xa0``) and thin spaces (``\\u2009``). The paragraphs report an apparent KD of the PII-PipX complex from a titration of PipX-SmBiT to PII-LgBiT, with two values (in the presence of ADP and in the presence of ATP);
they give no negative control, no signal-to-background ratio, no replicate, no list of concentrations, and do not say where the assay was run.
"""
PAPER_ID = 'PMC8206089'
REAL = (
    'To quantitatively determine the dissociation constant of PII-PipX interaction in presence of 2\xa0mM ATP or ADP, increasing concentrations of PipX were titrated to a fixed concentration of PII-LgBiT (10\xa0pM trimer). '
    'Then, the RLUs were plotted against the PipX-SmBiT concentrations (Fig.\xa02c). From these curves, KD values were calculated assuming that in equilibrium the dissociation constant follows the Eq.\xa0(1):\n\n'
    'At the concentration of PipX-SmBiT at which half maximal luminescence is observed, 50% of PII should be in the PipX complex. This concentration should therefore correspond to the KD of the complex '
    '(provided that PipX is in large excess over PII so that the free PipX concentrations approximately equal the total PipX concentration). We estimated the half-maximal RLU value by hyperbolic fitting, resulting in a KD of '
    '5.7 ± 0.78\xa0nM for the PII-PipX complex in presence of ADP and of 52.4 ± 0.92\xa0nM in presence of ATP (Table 1).')

SYNTHETIC = (
    'The binding of QX-7 to its partner protein PZ-2 was measured with the split NanoLuc reporter NanoBiT, in a lysate of HEK293 cells, as a titration. QX-7 was fused to LgBiT and PZ-2 to SmBiT, and four orientation combinations '
    'of the fusions were tested. The signal of the pair was seen in more than one of these orientations. The expression of all fusion proteins was verified by immunoblot. The QX-7 and PZ-2 pair gave a reconstituted luminescence signal '
    'above the background and the controls, with a signal-to-background ratio of 85 and a signal 40 times that of the negative control pair. Each fusion protein alone, or with the free partner fragment, gave only background signal. '
    'A pair of unrelated proteins fused to the same fragments gave only background signal. A non-binding mutant of QX-7 in place of QX-7 gave only background signal. A known interacting pair, the leucine zipper pair, gave a signal '
    'in the same assay. The background signal of untransfected lysate was measured and subtracted. PZ-2 was titrated at eight concentrations, from 1 nM to 1000 nM. The signal rose with the concentration of PZ-2 and reached a plateau. '
    'The reconstitution of NanoBiT is reversible, so the signal follows the equilibrium of the partners. Fitting the titration gave an apparent KD of 40 nM with a standard error of 4 nM. Three independent experiments were done on '
    'separate days, and the KD was determined by the split reporter only.')

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Synthetic: 'The binding of QX-7 to its partner protein PZ-2': QX-7 is the target, PZ-2 the partner (the titrated protein).
SYNTHETIC_TARGET = 'qx-7'
SYNTHETIC_PARTNER = 'pz-2'
# Real: the paragraphs measure the PII-PipX interaction (PipX titrated to a fixed PII); which of the two is the molecule the assay is about is genuinely ambiguous, so None.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('pii',), ('pipx',))     # symmetric pair named by the paragraph; either orientation accepted

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (40, 'nM', 'an apparent KD of 40 nM'),
    'kd_spread': (4, 'nM', 'a standard error of 4 nM'),
    'signal_to_background': (85, 'ratio', 'a signal-to-background ratio of 85'),
    'signal_over_negative_control': (40, 'ratio', 'a signal 40 times that of the negative control pair'),
    'orientation_pairs_tested': (4, 'count', 'four orientation combinations of the fusions were tested'),
    'loaded_concentration_lowest': (1, 'nM', 'from 1 nM'),
    'loaded_concentration_highest': (1000, 'nM', 'to 1000 nM'),
    'concentration_count': (8, 'count', 'at eight concentrations'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    'reporter_system': ('split_nanoluc', None, 'the split NanoLuc reporter NanoBiT'),
    'assay_system': ('cell_lysate', None, 'in a lysate of HEK293 cells'),
    'readout_mode': ('titration', None, 'as a titration'),
    'spread_kind': ('standard_error', None, 'a standard error of 4 nM'),
    'interaction_detected': ('yes', None, 'gave a reconstituted luminescence signal above the background and the controls'),
    'fragment_alone_control_negative': ('yes', None, 'Each fusion protein alone, or with the free partner fragment, gave only background signal'),
    'unrelated_pair_control_negative': ('yes', None, 'A pair of unrelated proteins fused to the same fragments gave only background signal'),
    'binding_mutant_control_negative': ('yes', None, 'A non-binding mutant of QX-7 in place of QX-7 gave only background signal'),
    'positive_control_done': ('yes', None, 'A known interacting pair, the leucine zipper pair, gave a signal in the same assay'),
    'signal_in_several_orientations': ('yes', None, 'was seen in more than one of these orientations'),
    'expression_verified': ('yes', None, 'The expression of all fusion proteins was verified by immunoblot'),
    'saturable_titration_shown': ('yes', None, 'The signal rose with the concentration of PZ-2 and reached a plateau'),
    'complementation_reversible': ('yes', None, 'The reconstitution of NanoBiT is reversible, so the signal follows the equilibrium of the partners'),
    'background_subtracted': ('yes', None, 'The background signal of untransfected lysate was measured and subtracted'),
    'independent_experiments': ('yes', None, 'Three independent experiments were done on separate days'),
    'single_estimate_method': ('yes', None, 'the KD was determined by the split reporter only'),
}

# The allowed set of the real model run: field -> every (value, unit) the paragraphs clearly state for it. Not allowed, because the paragraphs do not
# state them: the KD (two values, for ADP and for ATP, with no statement of which is the result) and its spread and kind, any signal ratio, the number of orientations, the concentrations of the series and their number, the assay system (cells, lysate or purified proteins),
# replicates, every control, expression, a reversible complementation, the background and a statement that only this method was used.
REAL_ALLOWED = {
    'reporter_system': {('split_nanoluc', None)},
    'readout_mode': {('titration', None)},
    'interaction_detected': {('yes', None)},
    'saturable_titration_shown': {('yes', None)},
}
