"""Chunks of text for the AUC (analytical ultracentrifugation: sedimentation velocity and sedimentation equilibrium) extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (micro and degree signs) so byte
offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the sedimentation velocity of PPAR-gamma-DL, SIRT1 and their mixture of 'The SIRT1 N-Terminal Domain as a Common Binding Interface for PPARgamma Anchoring'
(Proteins 2025, PMC12594183, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0)), the paragraph that begins 'After mapping the primary SIRT1:PPARgamma binding
interfaces', as the publisher's XML (Europe PMC full text) gives the paragraph's own text with the markup (italics, subscripts, the figure and table links) removed; the figure and the table that follow the
paragraph in the XML are not part of it. The text is exactly as the XML gives it, including its non-breaking spaces after 'Figure' and 'Table' (written as ``\\xa0`` below), the thin spaces around the plus-minus sign and
before 'kDa' (``\\u2009``) and the Unicode hyphen of 'AUC-SV' and 'PPARgamma-DL' (``\\u2010``); the line break between the K and the subscript D of 'KD' is removed. It reports the sedimentation
velocity of PPARgamma-DL alone (1.69 S, 35.6 kDa), of SIRT1 alone (two species, 2.12 S and 3.41 S, 51.4 and 97.4 kDa: a monomer and a dimer) and of their mixture (two peaks, 1.74 S for the unbound state and
2.89 S, 73.6 kDa, for a heterodimeric complex, 1:1, about 77 kDa) by a c(s) distribution. It gives no loading concentration (they are in the Methods), no KD (it says the concentrations were above the determined KD),
no fit statistics, no temperature, no speed, no buffer and no replicate.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_auc_extraction import (
    ANALYSIS_MODEL, DETECTION, RUN_MODE, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_auc_record import UNITS

PAPER_ID = 'PMC12594183'
REAL = (
    'After mapping the primary SIRT1:PPARγ binding interfaces, we sought to determine the stoichiometry of the proteins for modeling the complex. The stoichiometry was '
    'assessed using sedimentation velocity assay, through the method of analytical ultracentrifugation (AUC‐SV), which provides the sedimentation coefficient (S) and '
    'allows for the calculation of the protein size distribution in solution. To ensure all binding interfaces between SIRT1 and PPARγ were saturated, we used concentrations '
    'above the determined KD. The sedimentation coefficient distribution (c(s) vs. S) values of the samples are shown in Figure\xa02A. The raw data scans and the '
    'representative fits to a continuous c(s) distribution model are depicted in Figure\xa02B. PPARγ‐DL exhibited a singular S value of 1.69S ± 0.04, '
    'corresponding to a sedimentation particle mass of 35.6 ± 3.3 kDa, while SIRT1 showed two S values of 2.12S ± 0.12 and 3.41S ± 0.12, '
    'corresponding to sedimentation particle masses of 51.4 ± 5.7 kDa and 97.4 ± 11.3 kDa, respectively (Table\xa01). Thus, while the '
    'PPARγ‐DL sample consisted of monomeric forms, the SIRT1 sample contained both monomeric and dimeric forms. In the SIRT1:PPARγ‐DL sample, two peaks were '
    'observed: one at 1.74S ± 0.12 and another at 2.89S ± 0.21, corresponding to sedimentation particle masses of 38.06 ± 4.6 kDa and '
    '73.6 ± 6.6 kDa, respectively (Table\xa01). The 1.74S peak corresponded to the unbound state, likely driven by high PPARγ concentration. The '
    '2.89S ± 0.21 peak matched the combined masses of the monomeric SIRT1 (51.4 ± 5.7 kDa) and PPARγ‐DL (35.6 ± 3.3 kDa) in a 1:1 '
    'ratio (~77 kDa), indicating the formation of a heterodimeric complex. Additionally, the absence of the SIRT1 dimer peak in the complex sample suggested that PPARγ '
    'promotes the dissociation of the SIRT1 dimer, which may indicate a structural mechanism of SIRT1:PPARγ assembly.')

SYNTHETIC = (
    'Analytical ultracentrifugation of the binding of QX-7 to its partner protein PZ-2 was done as sedimentation velocity and sedimentation equilibrium runs in a Beckman Coulter XL-I at 20 °C and '
    'a rotor speed of 42000 rpm for the velocity runs, with the sedimentation read by absorbance at 280 nm. The buffer density and viscosity were calculated with SEDNTERP and used in the analysis. '
    'Each component was also run alone under the same conditions, and each component alone sedimented as a single species with no aggregate. The data were analysed with a continuous distribution '
    'c(s). QX-7 and PZ-2 were loaded at five concentrations, from 0.5 µM to 50 µM, as a concentration series. The mixture showed a complex peak at 4.1 S, larger than either component alone: '
    'the larger component alone sedimented at 3.2 S and the smaller one at 2.1 S. The frictional ratio of the complex was 1.3. The molar mass of the complex from the fit was 52 kDa, in agreement '
    'with the calculated mass of 54 kDa for the complex, which has a 1:1 stoichiometry. The weight-average s increased with the loading concentration as for a reversible association. '
    'Sedimentation equilibrium was done at several speeds, which were fitted together in a global fit, and successive scans overlaid, so equilibrium was reached. The global fit gave a KD of 4 µM '
    'with a standard error of 0.5 µM. The rmsd of the fit was 0.004 AU and the residuals were random. A non-binding mutant of QX-7 in place of QX-7 did not form the complex with PZ-2. Three '
    'independent experiments were done on separate days, and the KD was determined by analytical ultracentrifugation only.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (4, 'uM', 'a KD of 4 µM'),
    'kd_spread': (0.5, 'uM', 'a standard error of 0.5 µM'),
    'complex_sedimentation_coefficient': (4.1, 'S', 'a complex peak at 4.1 S'),
    'component_sedimentation_coefficient_larger': (3.2, 'S', 'the larger component alone sedimented at 3.2 S'),
    'component_sedimentation_coefficient_smaller': (2.1, 'S', 'the smaller one at 2.1 S'),
    'frictional_ratio': (1.3, 'ratio', 'The frictional ratio of the complex was 1.3'),
    'complex_mass_measured': (52, 'kDa', 'The molar mass of the complex from the fit was 52 kDa'),
    'complex_mass_theoretical': (54, 'kDa', 'the calculated mass of 54 kDa for the complex'),
    'stoichiometry_ratio': (1, 'ratio', 'which has a 1:1 stoichiometry'),
    'loaded_concentration_lowest': (0.5, 'uM', 'from 0.5 µM'),
    'loaded_concentration_highest': (50, 'uM', 'to 50 µM'),
    'concentration_count': (5, 'count', 'were loaded at five concentrations'),
    'fit_rmsd': (0.004, 'AU', 'The rmsd of the fit was 0.004 AU'),
    'rotor_speed': (42000, 'rpm', 'a rotor speed of 42000 rpm'),
    'run_temperature': (20, 'C', 'at 20 °C'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    RUN_MODE: ('velocity_and_equilibrium', None, 'as sedimentation velocity and sedimentation equilibrium runs'),
    ANALYSIS_MODEL: ('c_of_s', None, 'analysed with a continuous distribution c(s)'),
    DETECTION: ('absorbance', None, 'read by absorbance at 280 nm'),
    SPREAD_KIND: ('standard_error', None, 'a standard error of 0.5 µM'),
    'complex_detected': ('yes', None, 'The mixture showed a complex peak at 4.1 S, larger than either component alone'),
    'components_run_alone': ('yes', None, 'Each component was also run alone under the same conditions'),
    'components_monodisperse': ('yes', None, 'each component alone sedimented as a single species with no aggregate'),
    'concentration_series_measured': ('yes', None, 'as a concentration series'),
    'reversible_association_shown': ('yes', None, 'increased with the loading concentration as for a reversible association'),
    'mass_matches_complex': ('yes', None, 'in agreement with the calculated mass of 54 kDa for the complex'),
    'fit_residuals_random': ('yes', None, 'the residuals were random'),
    'buffer_density_viscosity_corrected': ('yes', None, 'The buffer density and viscosity were calculated with SEDNTERP and used in the analysis'),
    'equilibrium_reached_shown': ('yes', None, 'successive scans overlaid, so equilibrium was reached'),
    'multiple_speeds_used': ('yes', None, 'Sedimentation equilibrium was done at several speeds, which were fitted together'),
    'non_binding_control_done': ('yes', None, 'A non-binding mutant of QX-7 in place of QX-7 did not form the complex with PZ-2'),
    'independent_experiments': ('yes', None, 'Three independent experiments were done on separate days'),
    'single_estimate_method': ('yes', None, 'the KD was determined by analytical ultracentrifugation only'),
}

# field -> (value, unit, quote) for the real passage: what a careful reader may state from it about the experiment it describes, with the
# quote that says it.
REAL_STATED = {
    'complex_sedimentation_coefficient': (2.89, 'S', 'The 2.89S ± 0.21 peak matched the combined masses of the monomeric SIRT1'),
    'component_sedimentation_coefficient_smaller': (1.69, 'S', 'PPARγ‐DL exhibited a singular S value of 1.69S'),
    'complex_mass_measured': (73.6, 'kDa', 'another at 2.89S ± 0.21, corresponding to sedimentation particle masses of 38.06 ± 4.6 kDa and 73.6 ± 6.6 kDa, respectively'),
    'complex_mass_theoretical': (77, 'kDa', 'in a 1:1 ratio (~77 kDa)'),
    'stoichiometry_ratio': (1, 'ratio', 'in a 1:1 ratio (~77 kDa), indicating the formation of a heterodimeric complex'),
    RUN_MODE: ('sedimentation_velocity', None, 'using sedimentation velocity assay'),
    ANALYSIS_MODEL: ('c_of_s', None, 'representative fits to a continuous c(s) distribution model'),
    'complex_detected': ('yes', None, 'indicating the formation of a heterodimeric complex'),
    'components_run_alone': ('yes', None, 'while SIRT1 showed two S values of 2.12S ± 0.12 and 3.41S ± 0.12'),
    'components_monodisperse': ('no', None, 'the SIRT1 sample contained both monomeric and dimeric forms'),
    'mass_matches_complex': ('yes', None, 'peak matched the combined masses of the monomeric SIRT1'),
}
# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Not allowed, because the paragraph does not
# state them: the KD (it says only that the concentrations were above the determined KD) and its spread, the sedimentation coefficient of the larger component (SIRT1 has two species, a monomer and
# a dimer, with no statement of which one is the result), the frictional ratio, any loading concentration or their number, the rmsd, the speed, the temperature (all in the Methods), replicates, the detection (not named in this
# paragraph), a concentration series, a reversible association, random residuals, a corrected buffer, equilibrium and several speeds (a velocity run), the non-binding control, and a statement that only this method was used.
REAL_ALLOWED = {name: {(value, unit)} for name, (value, unit, _) in REAL_STATED.items()}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Real paragraph: SIRT1 and PPARgamma are assayed symmetrically as a complex (SIRT1:PPARgamma), so neither is singled out as the target: None as ambiguous.
SYNTHETIC_TARGET = 'qx-7'
SYNTHETIC_PARTNER = 'pz-2'
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('sirt1',), ('pparγ-dl',))     # symmetric pair named by the paragraph; either orientation accepted


def answer_from(chunk, stated, support=None):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable. A stated field
    carries support 'direct' unless ``support`` (field -> support) says otherwise; an unavailable one carries none."""
    answer = {}
    for name in field_names():
        carries_unit = name in UNITS
        if name in stated:
            value, unit, quote = stated[name]
            answer[name] = {'status': 'stated', 'value': value, 'quote': quote, 'support': (support or {}).get(name, 'direct'), 'reason': None,
                            **({'unit': unit} if carries_unit else {})}
        else:
            answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None,
                            'reason': 'not_stated_in_passage', **({'unit': None} if carries_unit else {})}
    return answer


def synthetic_answer():
    return answer_from(SYNTHETIC, SYNTHETIC_STATED)


REAL_COUNT = (2, 'count', 'Figure')       # not a replicate count: used only to test quote refusals ('Figure' occurs twice)


# The smaller component, the 1:1 ratio, the stated mass of a 1:1 complex and the monomer-dimer statement are only implied by their quotes.
REAL_SUPPORT = {'component_sedimentation_coefficient_smaller': 'implied', 'complex_mass_theoretical': 'implied', 'stoichiometry_ratio': 'implied', 'components_run_alone': 'implied', 'components_monodisperse': 'implied'}


def real_answer():
    return answer_from(REAL, REAL_STATED, REAL_SUPPORT)
