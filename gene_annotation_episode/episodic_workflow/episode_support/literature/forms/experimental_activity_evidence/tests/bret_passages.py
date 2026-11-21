"""Chunks of text for the BRET / NanoBRET (bioluminescence resonance energy transfer in cells) extraction tests, and what an extractor that read them correctly would state.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form; ``SYNTHETIC_STATED`` is the field -> (value, unit, quote) that reads it correctly. It contains a multi-byte character (the micro sign) so byte
offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the BRET saturation assay of TLR1/2-Rluc8 with TIRAP-Venus, MyD88-Venus and V2R-Venus (the paragraph that begins 'BRET between TLR1/2-Rluc8 and TIRAP-Venus showed clear saturation') of
'Investigation of interactions between TLR2, MyD88 and TIRAP by bioluminescence resonance energy transfer is hampered by artefacts of protein overexpression' (Sampaio NG, Kocan M, Schofield L, Pfleger KDG, Eriksson EM; PLoS One 2018,
PMC6107161, doi 10.1371/journal.pone.0202408, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0), licence read from the publisher's XML in Europe PMC), as the XML gives the paragraph's own text with the markup (the subscript of BRET50, the figure and table links) removed. The text is plain ASCII. It reports the
saturation of the BRET of the donor TLR1/2-Rluc8 with the acceptor TIRAP-Venus (a low BRET50 of 0.117), a linear relationship with MyD88-Venus, and V2R-Venus as a negative control that nevertheless gave a saturation curve, with a higher BRET50 of 0.193. It gives no cell
line, no number of points, no BRETmax, no BRET ratio, no fit statistic, no replicate and no KD (those are in the legends, the Methods and the table).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bret_extraction import (
    ACCEPTOR, BRET_FORMAT, DONOR, EXPRESSION, SPREAD_KIND)

PAPER_ID = 'PMC6107161'
REAL = (
    'BRET between TLR1/2-Rluc8 and TIRAP-Venus showed clear saturation, supportive of constitutive proximity between these two proteins (Fig 3A, blue curve). This specificity was further demonstrated by a low BRET50 value of 0.117 (Table 1). '
    'In contrast, BRET between TLR1/2-Rluc8 and MyD88-Venus had a linear relationship indicating a clear lack of proximity (Fig 3A, red line). This was consistent with confocal microscopy experiments (Fig 1F), which demonstrated that in the absence of TIRAP, '
    'overexpressed MyD88 was localized intracellularly away from the plasma membrane. In contrast, when untagged TIRAP was co-expressed with MyD88-Venus, clear saturation was observed, demonstrating again that MyD88 requires TIRAP to interact with TLR1/2 (Fig 3A, black curve). '
    'V2R-Venus was used as a negative control, as this receptor was not expected to specifically interact with TLR1/2. Intriguingly, a saturation curve for TLR1/2-Rluc8 and V2R-Venus was observed, although this was lower than that of TLR1/2 and TIRAP (Fig 3A, green curve). '
    'The BRET50 value was also higher for TLR1/2-Rluc8 and V2R-Venus (0.193), which are not known to have any meaningful biological interactions. This effect with saturation BRET can occur with overexpression of proteins that might co-localize at the cell membrane without any functional consequences [33], '
    'and again illustrates the need for careful interpretation of saturation BRET data. This being said, the clear linear relationship for TLR1/2-Rluc8 + MyD88-Venus with the switch to a clear saturation curve upon co-expression of TIRAP illustrates the utility of this approach under certain circumstances.')

SYNTHETIC = (
    'BRET between the kinase KX-1 and its partner protein PZ-2 was measured in live HEK293 cells that were transiently transfected, with KX-1 fused to NanoLuc as the donor and PZ-2 fused to Venus as the acceptor. '
    'A saturation titration was done: the donor DNA was held constant and the PZ-2-Venus DNA was raised in eight steps, and the acceptor-to-donor ratio, from 0.02 to 4, was read from the Venus fluorescence and the NanoLuc luminescence of the same cells, so that the expression levels were measured. '
    'Cells that expressed the donor alone and cells that expressed the acceptor alone were run as controls, and the donor-only signal was subtracted from all BRET ratios. Both fusion orientations, with the donor on KX-1 or on PZ-2, were tested. '
    'The BRET ratio of the pair rose as a hyperbola that reached a plateau, a saturation curve, with a BRETmax of 380 mBU and a BRET50 of 0.12; the one-site fit had an R squared of 0.98. At an acceptor-to-donor ratio of 1 the BRET ratio of the pair was 0.30, with a standard error of 0.02, and the BRET ratio of the negative control was 0.04, with a standard error of 0.005, so the pair showed a clear BRET signal; the donor alone gave a BRET ratio of 0.02. '
    'An F-test showed that the hyperbola fitted the data of the pair significantly better than a straight line, and at a fixed acceptor-to-donor ratio of 1 the BRET ratio stayed constant when the total expression was raised. '
    'A non-interacting membrane protein, QR-5, fused to Venus was run as a negative control in the same way; it gave only a nearly linear signal with no specific interaction, and an apparent BRET50 of 0.85. The standard error of the BRET50 of the pair was 0.015 and that of the negative control was 0.09. '
    'In a NanoBRET target engagement experiment with the NanoLuc-KX-1 fusion, a cell-permeable fluorescent tracer was titrated and gave an apparent KD of 35 nM with a standard error of 4 nM. The affinity of the tracer for NanoLuc-KX-1, its tracer KD, was 35 nM. The tracer was used at 0.1 µM in the displacement experiment, in which the unlabelled compound CPD-9 lowered the BRET signal of the tracer in a concentration-dependent way and gave a Ki of 120 nM with a standard error of 15 nM. '
    'Three independent experiments were done on separate days, and the interaction of KX-1 and PZ-2 was determined by BRET only.')

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Synthetic: 'BRET between the kinase KX-1 and its partner protein PZ-2': KX-1 is the target (NanoLuc donor fusion of the target engagement experiment), PZ-2 the partner.
SYNTHETIC_TARGET = 'kx-1'
SYNTHETIC_PARTNER = 'pz-2'
# Real: the paragraph compares several pairs (TLR1/2 with TIRAP, MyD88 and V2R) and does not say which protein the assay is about: ambiguous, so None.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('tlr1/2',), ('tirap',))     # symmetric pair named by the paragraph; either orientation accepted

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (35, 'nM', 'an apparent KD of 35 nM'),
    'kd_spread': (4, 'nM', 'a standard error of 4 nM'),
    'ki': (120, 'nM', 'a Ki of 120 nM'),
    'ki_spread': (15, 'nM', 'a standard error of 15 nM'),
    'bret50': (0.12, 'ratio', 'a BRET50 of 0.12'),
    'bret50_negative_control': (0.85, 'ratio', 'an apparent BRET50 of 0.85'),
    'bret_max': (380, 'mBU', 'a BRETmax of 380 mBU'),
    'bret_ratio_pair': (0.30, 'ratio', 'the BRET ratio of the pair was 0.30'),
    'bret_ratio_negative_control': (0.04, 'ratio', 'the BRET ratio of the negative control was 0.04'),
    'ratio_lowest': (0.02, 'ratio', 'from 0.02'),
    'ratio_highest': (4, 'ratio', 'to 4'),
    'titration_point_count': (8, 'count', 'raised in eight steps'),
    'tracer_concentration': (0.1, 'uM', 'The tracer was used at 0.1 µM'),
    'bret50_spread': (0.015, 'ratio', 'standard error of the BRET50 of the pair was 0.015'),
    'bret50_negative_control_spread': (0.09, 'ratio', 'that of the negative control was 0.09'),
    'bret_ratio_pair_spread': (0.02, 'ratio', 'with a standard error of 0.02'),
    'bret_ratio_negative_control_spread': (0.005, 'ratio', 'with a standard error of 0.005'),
    'bret_ratio_donor_only': (0.02, 'ratio', 'the donor alone gave a BRET ratio of 0.02'),
    'tracer_kd': (35, 'nM', 'its tracer KD, was 35 nM'),
    'fit_r_squared': (0.98, 'ratio', 'an R squared of 0.98'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    BRET_FORMAT: ('saturation_and_competition', None, 'A saturation titration was done'),
    DONOR: ('nanoluc', None, 'KX-1 fused to NanoLuc as the donor'),
    ACCEPTOR: ('fluorescent_protein', None, 'PZ-2 fused to Venus as the acceptor'),
    EXPRESSION: ('transient_transfection', None, 'transiently transfected'),
    SPREAD_KIND: ('standard_error', None, 'a standard error of 4 nM'),
    'interaction_detected': ('yes', None, 'so the pair showed a clear BRET signal'),
    'saturation_shown': ('yes', None, 'rose as a hyperbola that reached a plateau, a saturation curve'),
    'negative_control_pair_used': ('yes', None, 'was run as a negative control in the same way'),
    'negative_control_no_specific_signal': ('yes', None, 'it gave only a nearly linear signal with no specific interaction'),
    'donor_only_control_done': ('yes', None, 'Cells that expressed the donor alone'),
    'acceptor_only_control_done': ('yes', None, 'cells that expressed the acceptor alone'),
    'expression_levels_measured': ('yes', None, 'so that the expression levels were measured'),
    'background_subtracted': ('yes', None, 'the donor-only signal was subtracted from all BRET ratios'),
    'fusion_orientation_swapped': ('yes', None, 'Both fusion orientations, with the donor on KX-1 or on PZ-2, were tested'),
    'tracer_displaced_by_competitor': ('yes', None, 'lowered the BRET signal of the tracer in a concentration-dependent way'),
    'independent_experiments': ('yes', None, 'Three independent experiments were done on separate days'),
    'hyperbola_preferred_over_linear': ('yes', None, 'the hyperbola fitted the data of the pair significantly better than a straight line'),
    'bret_constant_across_expression': ('yes', None, 'the BRET ratio stayed constant when the total expression was raised'),
    'single_estimate_method': ('yes', None, 'was determined by BRET only'),
}

# field -> (value, unit, quote) for the real passage: what a careful reader may state from it about the experiment it describes.
REAL_STATED = {
    'bret50': (0.117, 'ratio', 'a low BRET50 value of 0.117'),
    'bret50_negative_control': (0.193, 'ratio', 'The BRET50 value was also higher for TLR1/2-Rluc8 and V2R-Venus (0.193)'),
    BRET_FORMAT: ('saturation_titration', None, 'showed clear saturation'),
    DONOR: ('rluc', None, 'BRET between TLR1/2-Rluc8 and TIRAP-Venus'),
    ACCEPTOR: ('fluorescent_protein', None, 'and TIRAP-Venus showed'),
    'interaction_detected': ('yes', None, 'supportive of constitutive proximity between these two proteins'),
    'saturation_shown': ('yes', None, 'showed clear saturation'),
    'negative_control_pair_used': ('yes', None, 'V2R-Venus was used as a negative control'),
    'negative_control_no_specific_signal': ('no', None, 'a saturation curve for TLR1/2-Rluc8 and V2R-Venus was observed'),
}
# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Not allowed, because the paragraph does not state them: a KD or a Ki, BRETmax, any BRET ratio,
# the ratio range and the number of points, the tracer, the fit, the replicates, the expression system (the cells and the transfection are in the Methods), the donor-only and acceptor-only controls, the
# measured expression levels, the subtracted background, the swap of the fusions, a displaced tracer, independent experiments and a statement that only this method was used, any spread of the BRET50 or of a BRET ratio, the donor-only BRET ratio, the tracer KD, a stated comparison of the hyperbola with a straight line and a test of BRET against the total expression (a plain statement that a curve was linear is not a model comparison).
REAL_ALLOWED = {name: {(value, unit)} for name, (value, unit, _) in REAL_STATED.items()}
