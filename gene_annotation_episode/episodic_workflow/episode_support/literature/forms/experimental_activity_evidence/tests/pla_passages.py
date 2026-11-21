"""Chunks of text for the PLA (proximity ligation assay: in situ PLA, Duolink) extraction real-model runs.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form (``SYNTHETIC_STATED`` is the tuple of the field names). It contains
multi-byte characters (micro sign, degree sign, plus-minus) so byte offsets differ from character offsets.

``REAL`` is real: the Methods paragraph of section 2.10 'Proximity Ligation Assay (PLA)' of 'An N-Terminal Acidic Patch Underlies Differential Inhibition of mRNA Nuclear Export by
Human Coronavirus Nsp1 Proteins' (Viruses 2026, PMC13709700, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0)), as the publisher's XML (Europe PMC full text)
gives the paragraph's own text with the markup removed (including the typographic apostrophe of 'manufacturer's'). It describes the Duolink In Situ Red kit, the fixation of cells on
coverslips with 4% paraformaldehyde, the primary antibodies (anti-Flag and anti-NXF1), the PLA probes, ligation and amplification by the manufacturer's protocol and the confocal imaging.
It gives no species of the antibodies, no control, no puncta, no count of cells, no software and no replicate.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pla_extraction import field_names

PAPER_ID = 'PMC13709700'
REAL = (
    'PLA was performed using the Duolink In Situ Red Starter Kit (Sigma-Aldrich) according to the manufacturer’s instructions. Cells on coverslips were fixed with 4% paraformaldehyde '
    'for 15 min and permeabilized with 0.5% Triton X-100 for 15 min. After blocking with Duolink blocking solution at 37 °C for 60 min, cells were incubated with primary antibodies '
    '(anti-Flag and anti-NXF1) diluted in Duolink antibody diluent at 37 °C for 60 min. PLA probes (PLUS and MINUS) were added and incubated at 37 °C for 60 min. Ligation and '
    'amplification were performed according to the manufacturer’s protocol. Subsequently, cells were incubated with primary antibodies (anti-Flag and anti-NXF1) at 4 °C overnight, '
    'followed by incubation with Alexa Fluor-conjugated secondary antibodies for 1 h. Nuclei were stained with Hoechst 33258. Coverslips were mounted and images acquired using '
    'confocal microscopy.')

# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it (a choice has no unit: None). Not allowed, because the paragraph does not state them:
# the species of the antibodies, any control, any puncta number, the number of cells, the software, the amplification time (only 'according to the manufacturer's protocol'), the replicates, the statistics.
REAL_ALLOWED = {
    'fixation': {('paraformaldehyde', None)},
    'cell_system': {('cultured_cells', None)},
}

SYNTHETIC = (
    'The association of QX-7 with its partner PZ-2 was tested by an in situ proximity ligation assay (Duolink) on cultured HeLa cells grown on coverslips and fixed with 4% paraformaldehyde. '
    'The two primary antibodies, a mouse anti-QX-7 antibody and a rabbit anti-PZ-2 antibody, were raised in different species, and both antibodies had been validated for immunofluorescence on knockout cells. '
    'After the ligation, the rolling-circle amplification was run for 100 min at 37 °C. Cells with both primary antibodies showed 24.5 puncta per cell, so the assay detected the two proteins in close proximity. '
    'The reaction with no primary antibody gave 1.2 puncta per cell and was negative, and the reactions with only the anti-QX-7 antibody or only the anti-PZ-2 antibody gave almost no puncta, so the single-antibody controls were negative. '
    'After siRNA knockdown of PZ-2 the cells showed 3.1 puncta per cell, and the knockdown lowered the signal. A pair of proteins known to interact was run as a positive control pair in the same assay and gave puncta. '
    'The puncta lay in the nucleus, where both proteins are expected to meet. The puncta were counted in 120 cells with ImageJ, and the counting was blind to the condition. '
    'The puncta of the test and of the control were compared by a Mann-Whitney test. The assay was repeated in three independent experiments on separate days with separate cultures, and the mean puncta per cell are given as the mean ± the standard deviation of the experiments.')

SYNTHETIC_STATED = field_names()

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Synthetic: 'The association of QX-7 with its partner PZ-2': QX-7 is the target, PZ-2 the partner.
SYNTHETIC_TARGET = 'qx-7'
SYNTHETIC_PARTNER = 'pz-2'
# Real: a Methods paragraph that names only antibodies (anti-Flag, anti-NXF1) and a kit, no molecule the assay is about as a target: None.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
