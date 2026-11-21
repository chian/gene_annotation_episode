"""Chunks of text for the proximity-labeling (BioID, TurboID, miniTurbo, APEX, APEX2 and split versions) extraction real-model tests.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form. It contains multi-byte characters (micro sign) so byte
offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the mass spectrometry of the TurboID fusions with IpgC and MxiE (their SAINT analysis and the classes of likely false positives) of 'The promiscuous biotin ligase TurboID reveals the proxisome of the
T3SS chaperone IpgC in Shigella flexneri' (mSphere 2024, PMC11580435, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0)), the paragraph that begins 'Biotinylated proteins were purified on a streptavidin resin',
as the publisher's XML (Europe PMC full text) gives the paragraph's own text with the markup (italics, the reference link) removed (the text is plain ASCII). It states the capture on streptavidin, the identification by tandem mass spectrometry, the
spectral counts, the SAINT analysis, the comparison with the TurboID and empty vector controls and that the cytoplasm is bacterial. It states no enrichment of a named candidate, no number, no labelling condition, no fusion site and no check of the fusion.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_proximity_extraction import (
    CELL_SYSTEM, LIGASE, QUANTIFICATION, READOUT, field_names)

PAPER_ID = 'PMC11580435'
REAL = (
    'Biotinylated proteins were purified on a streptavidin resin and identified by tandem mass spectrometry. We used spectral counts and the Significance Analysis of INTeractome (SAINT) software (42) '
    'to identify proteins that were significantly enriched in the TurboID fusions with IpgC and MxiE compared to the TurboID and empty vector controls (Tables S1 and S2). Nevertheless, the list of proteins '
    'filtered by the SAINT analyses still contained three major classes of likely false positives. First, proteins involved in translation, such as ribosomal proteins, are common contaminants in mass '
    'spectrometry due to their abundance or their proximity to baits during their biosynthesis. Second, the major naturally biotinylated protein BccP and proteins involved in biotin synthesis BioB and BioD '
    'are contaminants that are expected with promiscuous biotin ligases when used in the uncompartmentalized bacterial cytoplasm. Finally, T3SS substrates, especially those whose expression is regulated by '
    'MxiE and IpgC, are a class of false positives that is specific to this biological system. Indeed, the concentration of T3SS substrates in the cytoplasm may vary as a function of their secretion and '
    'expression. Under our experimental conditions, the expression of MxiE-regulated T3SS substrates is superior in ipgC-complemented strains expressing the TurboID fusion than in the control uncomplemented '
    'strain expressing the TurboID alone. In addition, IpgC and MxiE may also be vicinal to the protein product of their target genes as translation is co-transcriptional in bacteria. Due to the sensitivity of '
    'proximity labeling to the cellular concentration of individual proteins, all of these factors can lead to false-positive identification of T3SS substrates in the vicinity of IpgC or MxiE.')

SYNTHETIC = (
    'Proximity labeling of the candidate partner PZ-2 with the bait BX-4 was done in HEK293 cells stably expressing BX-4 fused at its C terminus to APEX2. The fusion was expressed at 1.5 times the level of '
    'endogenous BX-4, as measured by immunoblot, and immunofluorescence showed that the fusion localised like endogenous BX-4. Cells were incubated with 500 µM biotin-phenol for 30 min, and the labelling '
    'reaction was started with 1 mM H2O2 and lasted 1 min. Biotinylation depended on the fusion and on the labelling: a streptavidin blot showed biotinylated proteins only in cells treated with both '
    'biotin-phenol and H2O2. The controls were cells expressing the fusion but treated without H2O2, cells expressing free APEX2 without the bait, and cells expressing APEX2 fused to an unrelated protein. '
    'The biotinylated proteins were captured on streptavidin beads and identified by western blot and by mass spectrometry. Label-free intensities were compared with a moderated t-test, and PZ-2 was '
    'enriched 8.5-fold over the APEX2 fused to an unrelated protein with a false discovery rate of 0.8%, a control matched to the bait in expression level and compartment, so PZ-2 was found in proximity to BX-4. The proximity of PZ-2 to BX-4 was confirmed by co-immunoprecipitation. '
    'Three independent experiments were done on separate days, in mammalian cells.')

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Synthetic: BX-4 is the bait fused to APEX2 (the target); PZ-2 is the candidate proximal protein (the partner).
SYNTHETIC_TARGET = 'bx-4'
SYNTHETIC_PARTNER = 'pz-2'
# Real: the paragraph has two baits (IpgC and MxiE) and names no single candidate partner: no single target, so None.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None

# The fields the synthetic passage states: every field of the form.
SYNTHETIC_FIELDS = field_names()

# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Not allowed, because the paragraph does not state them: the enrichment of a named candidate
# (the paragraph describes how the SAINT list was filtered, it names no enriched candidate and no number), any labelling condition, the fusion site, the expression or the localisation of a fusion, a false discovery rate,
# biotinylation shown to depend on the fusion, a control without labelling or with an unrelated bait, replicates, an independent validation.
REAL_ALLOWED = {
    LIGASE: {('turboid', None)},
    READOUT: {('mass_spectrometry', None)},
    QUANTIFICATION: {('spectral_counts', None)},
    CELL_SYSTEM: {('bacteria', None)},
    'streptavidin_capture': {('yes', None)},
    'statistical_test_used': {('yes', None)},
    'ligase_only_control': {('yes', None)},
    # The paragraph says the enrichment is over 'the TurboID and empty vector controls', the free enzyme and no enzyme at all: controls that do not match the bait's localisation (field fold_over_matched_control: no).
    # The paragraph does not state a matched control, so yes is not allowed.
    'fold_over_matched_control': {('no', None)},
}
