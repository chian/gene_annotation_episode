"""Chunks of text for the intrinsic fluorescence quenching extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (a degree sign, a multiplication
sign and a minus sign) so byte offsets differ from character offsets.

``REAL`` is real: the Methods paragraph 4.14 'Tryptophan Fluorescence Quenching Assay' of 'Neuroprotective Action of Coumarin
Derivatives through Activation of TRKB-CREB-BDNF Pathway and Reduction of Caspase Activity in Neuronal Cells Expressing
Pro-Aggregated Tau Protein' (International Journal of Molecular Sciences 2022, 23, 12734, doi 10.3390/ijms232112734, PMC9654711,
PMID 36361524, open access, CC BY 4.0), exactly as the publisher's XML gives the paragraph's own text (en dashes U+2013 in the two
ranges, minus signs U+2212 in the equation and one line break before 'where'). The paragraph is whole (no sentence was removed). It
states that the interaction of TRKB-ECD-His with three test compounds was determined by tryptophan fluorescence titration, with
7,8-DHF as a positive control, that the protein was at 50 nM in PBS, that the compounds were used at 0-1000 nM (a range, not a
list), the instrument, 'room temperature' (no value), excitation at 295 nm, an emission range of 300-400 nm, and that the KD was
determined by fitting the normalized fluorescence intensity at 330 nm with an equation of the fractional change f and the total
protein and compound concentrations. It gives no KD (the KD values are in the Results paragraph, not in this chunk), no spread,
no size of the change, no direction, no name of the fit model, no replicate count, no incubation time and no control, and says
nothing of inner-filter or dilution corrections.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_extraction import (
    CHANGE_DIRECTION, FIT_MODEL, SERIES, SHIFT_DIRECTION, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_record import UNITS

PAPER_ID = 'PMC9654711'
REAL = (
    'The interaction between TRKB-ECD-His and LM-031, LMDS-1 or LMDS-2 was determined by tryptophan fluorescence titration. '
    '7,8-DHF (Sigma-Aldrich) was included as a positive control [39]. Tryptophan fluorescence spectra of TRKB-ECD-His (50 nM in '
    'PBS) were obtained before and after titration with different concentrations of test compounds (0–1000 nM). The fluorescent '
    'quenching was conducted in a cuvette with a 1 cm path length cell by an F-7000 fluorescence spectrophotometer (Hitachi, '
    'Tokyo, Japan) at room temperature. The intrinsic fluorescence spectra of TRKB were recorded with excitation wavelength set '
    'at 295 nm and emission wavelength in the range 300–400 nm. The dissociation constant (KD) of 7,8-DHF, LM-031, LMDS-1 and '
    'LMDS-2 to TRKB was determined by fitting the normalized fluorescence intensity at 330 nm under different concentrations of '
    'test compounds using the equation derived from Liu et al. [39]:KD = [P]T (f − 1) + [D]T (1/f − 1),\n'
    'where f is the fractional change, and [P]Tand [D]Tare the total concentration of TRKB-ECD-His protein and test compound, '
    'respectively.')

SYNTHETIC = (
    'Binding of the peptide ligand to ParB was measured by intrinsic tryptophan fluorescence titration at 25 °C. The assay was about the quenching of the protein ParB by its partner, the peptide PZ-2. ParB was held at a '
    'constant 5 nM, below the KD, and the samples were excited at 295 nm; the emission was read at 340 nm. The ligand was added in '
    '12 ligand concentrations of 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM, and each sample was left for 5 min after '
    'each addition before the read; the signal was stable over a further hour, so binding was at equilibrium. The total added '
    'volume was 3% of the starting volume, and the fluorescence was corrected for dilution. The fluorescence of the buffer was '
    'subtracted, and the fluorescence of the ligand alone was measured under the same conditions. The ligand did not absorb at the '
    'excitation and emission wavelengths, with an absorbance of 0.02 AU at the highest concentration, and the inner-filter effect '
    'was corrected with a titration of a free N-acetyl-tryptophanamide (NATA) solution; a free NATA solution was titrated with the '
    'ligand as a control. The ligand quenched the fluorescence by 40% at saturation, and the emission maximum showed a blue shift '
    'of 4 nm; the fluorescence change saturated at high ligand concentration. The quenching was static, the result of complex '
    'formation. Photobleaching was checked with a time scan of the protein alone. A non-binding variant of ParB was also titrated '
    'with the ligand and gave no signal change, and replacing the tryptophan W45 at the binding site by phenylalanine abolished the '
    'change, so the signal came from a tryptophan at the binding site. Depletion of free ligand by tight binding was considered, and '
    'the data were fitted with a quadratic (tight-binding) model, giving KD = 20 nM (standard error 2 nM). A Stern-Volmer analysis '
    'of the first points gave Ksv = 2.0 × 10^4 M−1, a quenching constant that is not the KD. The same interaction was also '
    'measured by isothermal titration calorimetry. Three independent titrations were done on separate days with fresh dilution series.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'ksv': (20000, 'M^-1', 'Ksv = 2.0 × 10^4 M−1'),
    'protein_concentration': (5, 'nM', 'ParB was held at a constant 5 nM'),
    'excitation_wavelength': (295, 'nm', 'excited at 295 nm'),
    'emission_wavelength': (340, 'nm', 'the emission was read at 340 nm'),
    'emission_shift': (4, 'nm', 'blue shift of 4 nm'),
    'fluorescence_change': (40, 'percent', 'quenched the fluorescence by 40% at saturation'),
    'ligand_absorbance': (0.02, 'AU', 'an absorbance of 0.02 AU'),
    'added_volume_fraction': (3, 'percent', 'The total added volume was 3% of the starting volume'),
    'titration_point_count': (12, 'count', '12 ligand concentrations'),
    'incubation_time': (5, 'min', 'left for 5 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'replicate_count': (3, 'count', 'Three independent titrations'),
    SERIES: ([1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048], 'nM', '1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024 and 2048 nM'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('quadratic', None, 'a quadratic (tight-binding) model'),
    CHANGE_DIRECTION: ('quenching', None, 'quenched the fluorescence'),
    SHIFT_DIRECTION: ('blue', None, 'a blue shift'),
    'inner_filter_corrected': ('yes', None, 'the inner-filter effect was corrected'),
    'ligand_absorbance_negligible': ('yes', None, 'The ligand did not absorb at the excitation and emission wavelengths'),
    'dilution_corrected': ('yes', None, 'the fluorescence was corrected for dilution'),
    'buffer_blank_subtracted': ('yes', None, 'The fluorescence of the buffer was subtracted'),
    'ligand_only_control_measured': ('yes', None, 'the fluorescence of the ligand alone was measured'),
    'nonbinding_control_done': ('yes', None, 'A non-binding variant of ParB was also titrated with the ligand and gave no signal change'),
    'trp_analogue_control_done': ('yes', None, 'a free NATA solution was titrated with the ligand as a control'),
    'signal_localised_to_binding_site': ('yes', None, 'so the signal came from a tryptophan at the binding site'),
    'signal_saturates': ('yes', None, 'the fluorescence change saturated at high ligand concentration'),
    'quenching_is_static': ('yes', None, 'The quenching was static'),
    'photobleaching_checked': ('yes', None, 'Photobleaching was checked with a time scan'),
    'protein_at_or_below_kd': ('yes', None, 'below the KD'),
    'tight_binding_considered': ('yes', None, 'Depletion of free ligand by tight binding was considered'),
    'equilibrium_reached': ('yes', None, 'so binding was at equilibrium'),
    'independent_titrations': ('yes', None, 'Three independent titrations were done on separate days'),
    'single_estimate_method': ('no', None, 'also measured by isothermal titration calorimetry'),
}

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about.
REAL_STATED = {
    'protein_concentration': (50, 'nM', 'TRKB-ECD-His (50 nM in PBS)'),
    'excitation_wavelength': (295, 'nm', 'excitation wavelength set at 295 nm'),
    'emission_wavelength': (330, 'nm', 'fluorescence intensity at 330 nm'),
}
# What else a careful reader may also state from the real passage: nothing. The compounds are used over a range (0-1000 nM), not a
# list; the temperature is 'room temperature' (no number); the emission range 300-400 nm is not a single wavelength; 'The
# fluorescent quenching was conducted' names the assay and does not say the compounds quenched or by how much; the equation of f,
# [P]T and [D]T is not named a model; 7,8-DHF is a positive-control compound, not a non-binding control; and no replicate count,
# incubation, correction, blank or control is stated. None of those may be stated.
REAL_MAY_ALSO_STATE = set()

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'pz-2'
# The assayed protein is TRKB-ECD-His (the passage writes 'TRKB' later in the same sense); the three test compounds are several
# partners, so no single partner is named.
REAL_EXPECTED_TARGET = 'trkb-ecd-his'
REAL_EXPECTED_PARTNER = None


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
