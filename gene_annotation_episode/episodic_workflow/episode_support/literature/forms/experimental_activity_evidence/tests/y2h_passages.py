"""Chunks of text for the Y2H (yeast two-hybrid) extraction model runs.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form (``literature_y2h_record.py``). It contains a multi-byte character (the degree sign) so byte offsets differ from character offsets.

``REAL`` is real: the Methods paragraph 'Transcriptional Activity Detection and Yeast Two-Hybrid Assay' of 'Identification of STOP1-Like Proteins Associated With Aluminum Tolerance in Sweet Sorghum'
(Front. Plant Sci. 2018, 9:258, doi 10.3389/fpls.2018.00258, PMC5835670, open access under the Creative Commons Attribution licence (CC BY)), as the publisher's XML (Europe PMC full text) gives the paragraph's own text
with the markup removed. It describes the bait (pBridge, GAL4 DNA-binding domain) and the prey (pGADT7, GAL4 activation domain) vectors, the yeast strain Y2HGold (and Y190 for the beta-galactosidase assay), the selective medium
SD/-Trp-Leu-His, the incubation (3 days at 30 degrees C), the Miller units of the beta-galactosidase assay and three biological replicates. It gives no 3-AT concentration (it says 'with or without 3-AT' for the autoactivation test of the bait),
no result of any pair, no Miller value and no spread of one, no dilution series, no control result, no reciprocal orientation, no expression of the fusions.
"""
PAPER_ID = 'PMC5835670'
REAL = (
    'To detect the transcriptional activity of SbSTOP1s, the bait vector pBridge expressing SbSTOP1a, SbSTOP1b, SbSTOP1c, SbSTOP1d, SbSTOP1d-NT (1–275 aa) or SbSTOP1d-CT (276–519 aa) fused to the GAL4 DNA-binding domain (BD) was used to transform the yeast strain Y2HGold. '
    'Colonies were selected on SD/-Trp-His medium (with or without 3-AT) and cultured for 3 days at 30°C. For the yeast two-hybrid assay, the prey vector pGADT7 expressing SbSTOP1b or SbSTOP1d fused to the GAL4 activation domain (AD) and the bait vector pBridge expressing SbSTOP1d-NT (1–275 aa) fused to the BD were used to co-transform the yeast strain Y2HGold (or the Y190 yeast strain for the β-galactosidase assay). '
    'Colonies were selected on SD/-Trp-Leu-His medium and cultured for 3 days at 30°C. The β-galactosidase assay was performed using chlorophenol red-β-D-galactopyranoside (CPRG) as substrate, and Miller units were calculated according to the Yeast Protocols Handbook (Clontech, PT3024-1). '
    'The experiment was conducted using three biological replicates.')

# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Not allowed, because the paragraph does not state them: a 3-AT concentration, any
# beta-galactosidase value, any result or control result (autoactivation, interaction, positive and unrelated controls, reciprocal orientation, non-selective growth, expression, more than one reporter), the strain Y190 as the strain of the test (the
# paragraph names two strains for two assays), and a selective medium for the autoactivation test (SD/-Trp-His, with or without 3-AT).
REAL_ALLOWED = {
    'system_kind': {('y2h', None)},
    'bait_fusion_domain': {('gal4_dbd', None)},
    'prey_fusion_domain': {('gal4_ad', None)},
    'yeast_strain': {('y2hgold', None)},
    'selective_medium_scored': {('minus_histidine', None)},
    'incubation_temperature': {(30, 'C')},
    'incubation_time': {(3, 'days')},
    'replicate_count': {(3, 'count')},
    'independent_experiments': {('yes', None)},
}

# The expected identity of the model run (normalized: casefold, whitespace collapsed). Synthetic: the bait QX-7 and its partner (prey) PZ-2. Real: the bait of the
# two-hybrid assay is SbSTOP1d-NT; the prey is SbSTOP1b or SbSTOP1d (two proteins), so the partner is ambiguous and not expected.
SYNTHETIC_TARGET = 'qx-7'
SYNTHETIC_PARTNER = 'pz-2'
REAL_EXPECTED_TARGET = 'sbstop1d-nt'
REAL_EXPECTED_PARTNER = None

SYNTHETIC = (
    'Yeast two-hybrid assays of the binding of the protein QX-7 to its partner protein PZ-2 were done in the yeast strain AH109. QX-7 was fused to the GAL4 DNA-binding domain (pGBKT7) as the bait and PZ-2 to the GAL4 activation domain (pGADT7) as the prey, '
    'and the pairs were scored on medium lacking histidine and adenine with 5 mM 3-AT after incubation at 30 °C for 4 days. The bait QX-7 with the empty prey vector, tested on medium with 2.5 mM 3-AT, did not activate the reporter, and the prey PZ-2 with the empty bait vector did not activate it either. '
    'An unrelated protein, lamin C, in place of PZ-2 did not activate the reporter. The positive control pair, p53 and large T antigen, activated the reporter. All transformants grew on non-selective medium lacking leucine and tryptophan, '
    'and immunoblots showed that both fusion proteins were expressed in yeast. The pair QX-7 and PZ-2 grew on the selective medium, so the two proteins interact, and the interaction was also seen when the bait and the prey were swapped. '
    'The pair activated two reporters, growth on selective medium and beta-galactosidase activity. In a spot assay of ten-fold serial dilutions the pair grew down to the 1:1000 dilution, whereas the negative control grew only down to the 1:10 dilution. '
    'The beta-galactosidase activity of the pair was 142 Miller units (standard deviation 12 Miller units, standard error of the mean 6.9 Miller units), that of the negative control was 3.1 Miller units (standard deviation 0.4 Miller units, standard error of the mean 0.23 Miller units) and that of the positive control was 160 Miller units. '
    'Three independent experiments were done on separate days.')
