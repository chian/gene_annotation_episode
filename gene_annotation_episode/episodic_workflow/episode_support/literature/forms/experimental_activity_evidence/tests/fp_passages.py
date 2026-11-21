"""Chunks of text for the FP extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the FP form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (micro, degree and plus-minus
signs) so byte offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the fluorescence polarization assay of FAM-labelled LANA1-22 peptide binding to
nucleosomes in 'Interactions of Nucleosomes with Acidic Patch-Binding Peptides: A Combined Structural Bioinformatics,
Molecular Dynamics, and Fluorescence Polarization, and Single-Molecule FRET Study' (International Journal of Molecular
Sciences 2023, doi 10.3390/ijms242015194, PMC10606924, open access, CC BY), exactly as the publisher's XML gives it (an en
dash U+2013, the plus-minus sign U+00B1 and the micro sign U+00B5). It states that the tracer was at 100 nM, that
nucleosomes were varied, that the measured polarization anisotropy was fitted with 'a corresponding binding model' (no model
named), that Kd was 0.4 +- 0.09 uM (the kind of the +- is not stated) and that nonspecific adsorption of nucleosomes on the wells
may lower the effective concentration. It says nothing of the window, the series values, the incubation, the replicate count, the
fit model's name, the controls or the equilibrium; those are in the paper's Methods and figure legend, which are not in this
chunk. The paragraph is whole (no sentence was removed)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fp_extraction import (
    ASSAY_FORMAT, FIT_MODEL, PLATE_TYPE, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fp_record import UNITS

PAPER_ID = 'PMC10606924'
REAL = (
    'Hence, to quantitatively estimate the dissociation constant for the LANA1-22–nucleosome complex, we have '
    'resorted to a fluorescence polarization assay. The schematic diagram of the experiment is shown in Figure 6c. '
    'FAM-labeled LANA1-22 peptides at a concentration of 100 nM were mixed with varying concentration of unlabeled '
    'nucleosomes. The FAM label was excited with polarized light; the binding of the peptide to the nucleosome was '
    'measured by the increase of the polarized component of the emitted light (see Methods, Section 4.9). The measured '
    'polarization anisotropy values correspond to the fraction of the bound peptide and were fitted using a '
    'corresponding binding model (see Methods, Section 4.9). The estimated value of Kd was 0.4 ± 0.09 µM '
    '(see Figure 6d). We consider it as the upper bound for the Kd value, since the effective concentration of '
    'nucleosomes during the measurement may be somewhat smaller due to the nonspecific adsorption of nucleosomes on the '
    'wells of the plate containing the samples during FP measurements.')

SYNTHETIC = (
    'Fluorescence polarization assays were carried out in black non-binding 384-well plates in a volume of 20 µL '
    'at 25 °C. The assay measured the binding of the protein ParB to its peptide partner PopZ. In the direct titration, the labelled peptide (tracer) was held at 5 nM, below the KD, and 0.01% '
    'Tween-20 and 0.1 mg/mL BSA were included to prevent adsorption to the plate. Samples were incubated for 30 min, '
    'and the polarization was stable over a further hour, so binding was at equilibrium. ParB was titrated in ten '
    'concentrations of 2, 4, 10, 20, 40, 100, 200, 400, 1000 and 2000 nM. The polarization of the free tracer, '
    'measured as the baseline, was 50 mP and rose to a plateau of 250 mP when the tracer was fully bound. The total '
    'fluorescence intensity changed by 10% on binding, and this change was checked and corrected for. Tracer '
    'depletion was considered, and the data were fitted with a quadratic (tight-binding) model, giving KD = 20 nM '
    '(standard error 2 nM). Non-specific binding was checked with an unrelated protein, which gave no signal, and an '
    'excess of unlabelled peptide displaced the bound tracer. In a competition experiment with an unlabelled ligand, '
    'Ki = 40 nM (standard error 4 nM); the affinity was thus estimated both by direct titration and by competition. '
    'Three independent titrations were done on separate days with fresh dilution series.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'ki': (40, 'nM', 'Ki = 40 nM'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'ki_spread': (4, 'nM', 'standard error 4 nM'),
    'tracer_concentration': (5, 'nM', 'held at 5 nM'),
    'signal_minimum': (50, 'mP', 'was 50 mP'),
    'signal_maximum': (250, 'mP', 'plateau of 250 mP'),
    'total_intensity_change': (10, 'percent', 'changed by 10%'),
    'assay_volume': (20, 'uL', 'a volume of 20 µL'),
    'incubation_time': (30, 'min', 'incubated for 30 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'replicate_count': (3, 'count', 'Three independent titrations'),
    SERIES: ([2, 4, 10, 20, 40, 100, 200, 400, 1000, 2000], 'nM', 'ten concentrations of 2, 4, 10, 20, 40, 100, 200, 400, 1000 and 2000 nM'),
    ASSAY_FORMAT: ('direct_titration', None, 'In the direct titration'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('quadratic', None, 'a quadratic (tight-binding) model'),
    PLATE_TYPE: ('black_non_binding', None, 'black non-binding 384-well plates'),
    'tracer_at_or_below_kd': ('yes', None, 'held at 5 nM, below the KD'),
    'equilibrium_reached': ('yes', None, 'so binding was at equilibrium'),
    'tight_binding_considered': ('yes', None, 'Tracer depletion was considered'),
    'intensity_change_checked': ('yes', None, 'this change was checked and corrected for'),
    'free_probe_baseline_measured': ('yes', None, 'The polarization of the free tracer, measured as the baseline'),
    'nonspecific_binding_checked': ('yes', None, 'Non-specific binding was checked with an unrelated protein'),
    'unlabelled_competitor_displaces': ('yes', None, 'an excess of unlabelled peptide displaced the bound tracer'),
    'surface_adsorption_prevented': ('yes', None, 'to prevent adsorption to the plate'),
    'independent_titrations': ('yes', None, 'Three independent titrations were done on separate days'),
    'single_estimate_method': ('no', None, 'estimated both by direct titration and by competition'),
}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'popz'
# The real paragraph is about the LANA1-22 peptide (the FAM-labelled tracer) binding nucleosomes; whether the peptide or the
# nucleosome is the molecule assayed is ambiguous, so no single target is expected.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('lana1-22',), ('nucleosome',))     # symmetric pair named by the paragraph; either orientation accepted

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about.
REAL_STATED = {
    'kd': (0.4, 'uM', 'Kd was 0.4 ± 0.09 µM'),
    'kd_spread': (0.09, 'uM', '0.09 µM'),
    'tracer_concentration': (100, 'nM', 'at a concentration of 100 nM'),
}
# What else a careful reader may also state from the real passage (a judgement the passage supports, not a number):
# that the experiment is a direct titration of the tracer with nucleosomes.
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
