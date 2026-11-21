"""Chunks of text for the DSF (thermal shift: differential scanning fluorimetry and nanoDSF) extraction tests.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form; ``SYNTHETIC_STATED`` lists, per field, the value, unit and
a quote that says it. It contains multi-byte characters (micro and degree signs) so byte offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the nanoDSF screening of small molecule mimics of an Adhiron against the nucleoprotein (NP) of Crimean-Congo haemorrhagic fever virus (CCHFV) of
'Adhirons are efficient tools to guide antiviral ligand discovery' (Communications Biology 2025, doi 10.1038/s42003-025-09137-x, PMC12686443, open access under the Creative Commons Attribution 4.0
licence (CC BY 4.0)), the paragraph that begins 'When the selected compounds were screened for binding to NP by nanoDSF', as the publisher's XML (Europe PMC full text) gives the paragraph's own text with the markup removed.
The text is exactly as the XML gives it, including its thin spaces (``\\u2009``) between a number and its unit and the non-breaking space after 'Fig.' (``\\xa0``). It reports the intrinsic fluorescence readout (nanoDSF), the shift of each compound against the DMSO control,
and a positive thermal shift of 0.98 and 0.57 degrees Celsius for two compounds (AF1-02 and AF1-05). It gives no Tm, no scatter, no concentration, no heating rate and no replicate number.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dsf_extraction import (
    READOUT, SPREAD_KIND, TM_METHOD)

PAPER_ID = 'PMC12686443'
REAL = (
    'When the selected compounds were screened for binding to NP by nanoDSF, fluorescence at 330 nm and 350 nm was measured, and the derivative of the ratio (F330/F350) was plotted against the temperature, '
    'generating melting peaks. Finally, the inflection point of each curve was measured as the Tm and the shift for each compound was calculated relative to the DMSO control (Fig.\xa02C). '
    'Both AF1-02 and AF1-05 generated a positive thermal shift for CCHFV NP of 0.98 °C and 0.57 °C, respectively, indicating that they bind to CCHFV NP. '
    'Combined with the results from the mini-genome system assay, it suggests that AF1-05 binds CCHFV NP but is not biologically active, whereas AF1-02 both binds and inhibits CCHFV NP. '
    'Although AF1-02 possesses weak activity, this could be improved by rounds of structural optimisation. These results demonstrate that Adhirons can be used as scaffolds to direct the identification of small molecule modulators.')

# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. The paragraph states that the readout is the intrinsic fluorescence (nanoDSF), that a
# positive thermal shift was seen (a rise of the Tm), that the shift was taken against a DMSO control (the protein with the vehicle and no ligand) and the shifts of the two compounds (0.98 and 0.57 degrees Celsius; it gives each for a
# different compound, so a call may state either or leave the shift unavailable). Not allowed, because the paragraph does not state them: any Tm, a scatter, a Tagg, any concentration or their number, a heating rate, replicates, the KD,
# the ligand concentration at which a shift was read, whether a scatter is over independent experiments or wells (no scatter is given), the way the Tm was read (it says the inflection point of a derivative, not a fit or a maximum), a ligand-alone control, the shape of the curves, a series of concentrations, a dose dependence and independent experiments.
REAL_ALLOWED = {
    'delta_tm': {(0.98, 'C'), (0.57, 'C')},
    READOUT: {('label_free_intrinsic_fluorescence', None)},
    'thermal_shift_observed': {('yes', None)},
    'protein_alone_control_done': {('yes', None)},
}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Real paragraph: the protein screened is CCHFV NP (written 'NP' and 'CCHFV NP'); two different compounds are tested, so no single partner: None.
SYNTHETIC_TARGET = 'pz-2'
SYNTHETIC_PARTNER = 'qx-7'
REAL_EXPECTED_TARGET = 'cchfv np'
REAL_EXPECTED_PARTNER = None

SYNTHETIC = (
    'The thermal shift of the binding of the ligand QX-7 to the protein PZ-2 was measured by nanoDSF in a Prometheus instrument, label free by the intrinsic tryptophan fluorescence, with the protein at 5 µM in 25 mM Hepes pH 7.5 and 150 mM NaCl. '
    'The samples were heated at 1 °C/min from 20 °C to 95 °C, and the Tm was read as the maximum of the first derivative of the fluorescence ratio. '
    'The protein alone, without the ligand, was measured in the same buffer with the same 1% DMSO vehicle, and its Tm was 52.3 °C. '
    'The ligand alone, with the buffer and no protein, was also scanned and gave no signal of its own. The melt curves were clean sigmoids with one unfolding transition. '
    'QX-7 was added at eight concentrations, from 1 µM to 200 µM, as a ligand titration. With 200 µM QX-7 the Tm was 57.1 °C, a thermal shift of 4.8 °C, with a standard deviation of the Tm of 0.3 °C, taken over the independent experiments. '
    'The Tagg of the protein alone was 61.0 °C and with the ligand 66.2 °C. The shift grew with the ligand concentration, as a dose dependent stabilisation. '
    'A fit of the shifts against the ligand concentration gave an apparent KD of 12 µM with a standard error of 1.5 µM. '
    'Three independent experiments were done on separate days.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (12, 'uM', 'an apparent KD of 12 µM'),
    'kd_spread': (1.5, 'uM', 'a standard error of 1.5 µM'),
    'tm_apo': (52.3, 'C', 'its Tm was 52.3 °C'),
    'tm_ligand': (57.1, 'C', 'With 200 µM QX-7 the Tm was 57.1 °C'),
    'delta_tm': (4.8, 'C', 'a thermal shift of 4.8 °C'),
    'tm_spread': (0.3, 'C', 'a standard deviation of the Tm of 0.3 °C'),
    'tagg_apo': (61.0, 'C', 'The Tagg of the protein alone was 61.0 °C'),
    'tagg_ligand': (66.2, 'C', 'with the ligand 66.2 °C'),
    'protein_concentration': (5, 'uM', 'with the protein at 5 µM'),
    'ligand_concentration_lowest': (1, 'uM', 'from 1 µM'),
    'ligand_concentration_highest': (200, 'uM', 'to 200 µM'),
    'ligand_concentration_count': (8, 'count', 'added at eight concentrations'),
    'shift_ligand_concentration': (200, 'uM', 'With 200 µM QX-7'),
    'heating_rate': (1, 'C_per_min', 'heated at 1 °C/min'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    READOUT: ('label_free_intrinsic_fluorescence', None, 'label free by the intrinsic tryptophan fluorescence'),
    TM_METHOD: ('first_derivative', None, 'the maximum of the first derivative of the fluorescence ratio'),
    SPREAD_KIND: ('standard_error', None, 'a standard error of 1.5 µM'),
    'thermal_shift_observed': ('yes', None, 'a thermal shift of 4.8 °C'),
    'protein_alone_control_done': ('yes', None, 'The protein alone, without the ligand, was measured in the same buffer with the same 1% DMSO vehicle'),
    'ligand_alone_control_done': ('yes', None, 'gave no signal of its own'),
    'melt_curve_sigmoidal': ('yes', None, 'The melt curves were clean sigmoids with one unfolding transition'),
    'ligand_titration_measured': ('yes', None, 'as a ligand titration'),
    'shift_dose_dependent': ('yes', None, 'The shift grew with the ligand concentration'),
    'tm_spread_over_independent_experiments': ('yes', None, 'taken over the independent experiments'),
    'independent_experiments': ('yes', None, 'Three independent experiments were done on separate days'),
}
