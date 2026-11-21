"""Chunks of text for the SEC (size-exclusion chromatography, with or without multi-angle light scattering, SEC-MALS) extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (micro and degree signs) so byte
offsets differ from character offsets.

``REAL`` is real: a Results paragraph of 'The MCU and MCUb amino-terminal domains tightly interact: mechanisms for low conductance assembly of the mitochondrial calcium uniporter complex'
(iScience 2024, doi 10.1016/j.isci.2024.109699, PMC11068563, PMID 38706857, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0), (c) 2024 The Author(s)),
the paragraph that begins 'Given the self-association observed here for the MCUb-NTD', as the publisher's XML gives the paragraph's own text with the markup (the figure links) removed. The
paragraph is whole, with ONE exception: in the XML the legend of Figure 4 is nested inside the paragraph element (a figure element, with its own caption), and its text is not part of
the paragraph's own text, so it is left out; nothing else is removed. The text is exactly as the XML gives it, including its non-breaking spaces (written as ``\\xa0`` below), the minus sign of
'mg mL−1', the tilde operator of '∼20×' and the plus-minus sign. It reports SEC-MALS of the MCUb-NTD alone (at three injection concentrations in mg/mL), the MCU-NTD alone, and their
~1:1 mixture: a heterodimer with a MALS molar mass of 21.7 +/- 0.4 kDa that elutes as a single peak at an earlier elution volume than either protein alone, SDS-PAGE of the earlier elution
fractions of the mixture showing two bands, the same with 5 mM CaCl2 or MgCl2 (22.2 and 20.8 kDa). It gives no elution volume, no theoretical mass of the complex, no injected molar
concentration, no column, buffer, flow rate or temperature (those are in the left-out legend and in the Methods), no KD and no replicates.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_extraction import (
    COLUMN_TYPE, DETECTION, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import UNITS

PAPER_ID = 'PMC11068563'
REAL = (
    'Given the self-association observed here for the MCUb-NTD, the self-association previously observed for the MCU-NTD33 and the homology between the domains (Figure\xa01B), we next used '
    'size exclusion chromatography with in-line multi-angle light scattering (SEC-MALS) to assess if these paralogous NTDs interact. First, SEC-MALS was performed on MCUb-NTD, which has a '
    'theoretical monomer mass of 12.0098\xa0kDa. At injection concentrations of 2\xa0mg mL−1, 3\xa0mg mL−1, and 4\xa0mg mL−1, MCUb-NTD consistently eluted in a single major peak with '
    'MALS-determined molecular weights of 11.4\xa0± 0.1\xa0kDa, 11.6\xa0± 0.3\xa0kDa, and 12.2\xa0± 0.1\xa0kDa, respectively (Figure\xa04A; Table\xa0S2). These data contrast the DLS observations '
    'showing higher order oligomerization likely due to the ∼20× dilution that occurs on the SEC column. The presence of 5\xa0mM CaCl2 or 5\xa0mM MgCl2 in the SEC-MALS experiments did not '
    'appreciably alter the elution volume or molecular weights (Figure\xa04B; Table\xa0S2). The theoretical monomeric mass of the MCU-NTD is 13.8637\xa0kDa; SEC-MALS showed that an injection '
    'concentration of 3\xa0mg mL−1 and after the column dilution, MCU-NTD also exists as a monomer with a measured molecular weight of 13.6\xa0± 0.2\xa0kDa (Figure\xa04C; Table\xa0S2). Excitingly, '
    'when mixed in a ∼1:1\xa0M ratio, the domains formed a heterodimer with a MALS-determined molecular weight of 21.7\xa0± 0.4\xa0kDa (Figure\xa04D; Table\xa0S2). Further, the mixed sample '
    'eluted in a single peak and at an earlier elution volume compared to either of the proteins in isolation. Interestingly, the MCU-NTD:MCUb-NTD interaction was stable in the presence of both '
    '5\xa0mM CaCl2 and 5\xa0mM MgCl2, as the molecular weight and co-elution volume were minimally affected by the divalent cations (i.e., 22.2\xa0± 0.1\xa0kDa and 20.8\xa0± 0.1\xa0kDa in the '
    'presence of 5\xa0mM CaCl2 and 5\xa0mM MgCl2, respectively) (Figures\xa04E and 4F; Table\xa0S2). SDS-PAGE gels of the elution fractions revealed single bands for the individual MCU-NTD and '
    'MCUb-NTD injections but two bands in the earlier elution fractions for the mixed samples, confirming co-elution (Figures\xa04G–4I). Since the proteins elute with a bell-shaped concentration '
    'profile in the SEC-MALS experiments, fractions taken from the center of the peak will have higher protein concentration and higher SDS-PAGE band intensities than the flanking fractions. '
    'Altogether, SEC-MALS shows that under dilute conditions, MCUb-NTD and MCU-NTD primarily exist as monomers; however, these NTDs interact when mixed, forming stable heterodimers that '
    'co-elute in gel filtration experiments.')

SYNTHETIC = (
    'SEC-MALS of the binding of QX-7 to its partner protein PZ-2 was done on a Superdex 200 Increase 10/300 GL column (bed volume 24 mL) at a flow rate of 0.5 mL/min and 4 °C in a running buffer of 20 mM Tris '
    'pH 8.0 with 150 mM NaCl, which was high enough to rule out interaction with the resin. The column was calibrated with protein standards of known size. A 500 µL sample of QX-7 and PZ-2 at '
    '5 µM each was injected after 30 min of incubation, and the elution was followed by light scattering. Each component was also run alone on the same column. The mixture eluted as a complex '
    'peak, earlier than either component alone: the complex peak at 11.2 mL, the larger component alone at 12.5 mL and the smaller component alone at 14.1 mL, a shift of 1.3 mL. SDS-PAGE of '
    'the fractions of the complex peak showed both proteins. The molar mass of the complex peak by MALS was 52 kDa, against a calculated mass of 54 kDa for the complex, in agreement with the '
    'calculated mass of the complex, with a polydispersity of 1.02 and no aggregation. The larger component alone had a MALS molar mass of 36.8 kDa and the smaller one 17.6 kDa. The complex has '
    'a 1:1 stoichiometry. When QX-7 was titrated into PZ-2, the peak of free PZ-2 decreased as the complex peak grew, and the areas of the peaks gave an apparent KD of 200 nM with a standard '
    'error of 20 nM. The complex was stable on the column at this concentration, which was above the KD. A non-binding mutant of QX-7 in place of QX-7 did not co-elute with PZ-2. Three '
    'independent experiments were done on separate days, and the KD was determined by size-exclusion chromatography only.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (200, 'nM', 'an apparent KD of 200 nM'),
    'kd_spread': (20, 'nM', 'a standard error of 20 nM'),
    'complex_elution_volume': (11.2, 'mL', 'the complex peak at 11.2 mL'),
    'component_elution_volume_earlier': (12.5, 'mL', 'the larger component alone at 12.5 mL'),
    'component_elution_volume_later': (14.1, 'mL', 'the smaller component alone at 14.1 mL'),
    'elution_volume_shift': (1.3, 'mL', 'a shift of 1.3 mL'),
    'complex_mass_measured': (52, 'kDa', 'The molar mass of the complex peak by MALS was 52 kDa'),
    'complex_mass_theoretical': (54, 'kDa', 'a calculated mass of 54 kDa for the complex'),
    'component_mass_measured_larger': (36.8, 'kDa', 'The larger component alone had a MALS molar mass of 36.8 kDa'),
    'component_mass_measured_smaller': (17.6, 'kDa', 'the smaller one 17.6 kDa'),
    'stoichiometry_ratio': (1, 'ratio', 'The complex has a 1:1 stoichiometry'),
    'polydispersity': (1.02, 'ratio', 'a polydispersity of 1.02'),
    'flow_rate': (0.5, 'mL/min', 'a flow rate of 0.5 mL/min'),
    'column_volume': (24, 'mL', 'bed volume 24 mL'),
    'run_temperature': (4, 'C', 'and 4 °C'),
    'loaded_concentration': (5, 'uM', '5 µM each'),
    'loaded_volume': (500, 'uL', 'A 500 µL sample'),
    'salt_concentration': (150, 'mM', '150 mM NaCl'),
    'incubation_time': (30, 'min', 'after 30 min of incubation'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    COLUMN_TYPE: ('superdex', None, 'a Superdex 200 Increase 10/300 GL column'),
    DETECTION: ('light_scattering', None, 'the elution was followed by light scattering'),
    SPREAD_KIND: ('standard_error', None, 'a standard error of 20 nM'),
    'complex_peak_detected': ('yes', None, 'The mixture eluted as a complex peak, earlier than either component alone'),
    'components_run_alone': ('yes', None, 'Each component was also run alone on the same column'),
    'complex_peak_analysed_by_sds_page': ('yes', None, 'SDS-PAGE of the fractions of the complex peak showed both proteins'),
    'free_peak_decreases_with_titration': ('yes', None, 'the peak of free PZ-2 decreased as the complex peak grew'),
    'mals_mass_matches_complex': ('yes', None, 'in agreement with the calculated mass of the complex'),
    'column_calibrated_with_standards': ('yes', None, 'The column was calibrated with protein standards of known size'),
    'buffer_rules_out_resin_interaction': ('yes', None, 'high enough to rule out interaction with the resin'),
    'complex_stable_on_column': ('yes', None, 'The complex was stable on the column at this concentration'),
    'aggregation_absent': ('yes', None, 'no aggregation'),
    'single_component_control_done': ('yes', None, 'A non-binding mutant of QX-7 in place of QX-7 did not co-elute with PZ-2'),
    'independent_experiments': ('yes', None, 'Three independent experiments were done on separate days'),
    'single_estimate_method': ('yes', None, 'determined by size-exclusion chromatography only'),
}

# field -> (value, unit, quote) for the real passage: what a careful reader may state from it about the experiment it describes, with the
# quote that says it.
REAL_STATED = {
    'complex_mass_measured': (21.7, 'kDa', 'the domains formed a heterodimer with a MALS-determined molecular weight of 21.7\xa0± 0.4\xa0kDa'),
    'component_mass_measured_larger': (13.6, 'kDa', 'a measured molecular weight of 13.6\xa0± 0.2\xa0kDa'),
    'stoichiometry_ratio': (1, 'ratio', 'the domains formed a heterodimer'),
    DETECTION: ('light_scattering', None, 'size exclusion chromatography with in-line multi-angle light scattering (SEC-MALS)'),
    'complex_peak_detected': ('yes', None, 'the mixed sample eluted in a single peak and at an earlier elution volume compared to either of the proteins in isolation'),
    'components_run_alone': ('yes', None, 'compared to either of the proteins in isolation'),
    'complex_peak_analysed_by_sds_page': ('yes', None, 'but two bands in the earlier elution fractions for the mixed samples, confirming co-elution'),
    'complex_stable_on_column': ('yes', None, 'forming stable heterodimers that co-elute in gel filtration experiments'),
}
# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Not allowed, because the paragraph does not
# state them: any elution volume or shift (none is given as a number), the theoretical mass of the complex (only the monomer masses are given), the smaller component's mass (three
# values at three injection concentrations, none given as the result), the injected concentration (given in mg/mL, a unit the form does not offer), the polydispersity, the column (and its volume: none is given), flow rate,
# temperature, salt of the running buffer (the 5 mM CaCl2 and MgCl2 are divalent cations added to test an effect), incubation, the KD, replicates, calibration, resin interaction, aggregation
# (a single peak is not a statement of it), the titration, the single-component control (running each protein alone is not that), and a statement that the MALS mass matches the complex.
REAL_ALLOWED = {name: {(value, unit)} for name, (value, unit, _) in REAL_STATED.items()}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Real paragraph: the interaction of two paralogous domains (MCUb-NTD and MCU-NTD) is tested with neither one the target of the other, so both are None as ambiguous.
SYNTHETIC_TARGET = 'qx-7'
SYNTHETIC_PARTNER = 'pz-2'
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('mcub-ntd',), ('mcu-ntd',))     # symmetric pair named by the paragraph; either orientation accepted


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


REAL_COUNT = (2, 'count', 'Figure')       # not a replicate count: used only to test quote refusals ('Figure' occurs many times)


# The stoichiometry is only implied by the quote: it says the domains formed a heterodimer, not that the ratio is 1 to 1 by a measurement.
REAL_SUPPORT = {'stoichiometry_ratio': 'implied'}


def real_answer():
    return answer_from(REAL, REAL_STATED, REAL_SUPPORT)
