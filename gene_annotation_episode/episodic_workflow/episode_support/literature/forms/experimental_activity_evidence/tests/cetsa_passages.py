"""Chunks of text for the CETSA (cellular thermal shift assay: melt curve and isothermal dose-response ITDR-CETSA) extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``SYNTHETIC_STATED`` lists each field with its value, unit and quote. It contains multi-byte characters (micro and degree signs) so byte
offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the isothermal dose-response CETSA of the androgen receptor ('CETSA HT', the paragraph that begins 'Using this newly established CETSA HT assay')
of 'Determining direct binders of the Androgen Receptor using a high-throughput Cellular Thermal Shift Assay' (Sci Rep 2018, PMC5760633, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0)),
as the publisher's XML (Europe PMC full text) gives the paragraph's own text with the markup (italics, subscripts, superscript reference numbers, figure links) removed (so the reference numbers stand against the word before them, as in 'LNCaP30');
the figure that follows the paragraph in the XML is not part of it. The text is exactly as the XML gives it, including its non-breaking spaces after 'Fig.' (written as ``\\xa0`` below) and the thin spaces between a number and its unit (``\\u2009``).
It reports an ITDR-CETSA at a heat shock of 46 degrees C chosen in the window between the unbound and the agonist-bound androgen receptor, in cells, with EC50 values for several compounds (testosterone 1.7 nM, R1881 1.2 nM, andrenosterone 50.6 nM: no one of them is
the result of the paragraph), inactive metabolites that gave no or only partial engagement, and a time-course. It gives no readout (it is in the paragraph before), no Tm, no vehicle or loading control, no replicate and no number of concentrations.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_cetsa_extraction import (
    EXPERIMENT_FORMAT, READOUT, SAMPLE_FORMAT, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_cetsa_record import UNITS

PAPER_ID = 'PMC5760633'
REAL = (
    'Using this newly established CETSA HT assay, we looked at the effect of DHT or Enzalutamide on AR thermal stability in CWR22-Pc-R1-AD1 cells. Similar to the observations made by CETSA Classics shown in Fig.\xa01, '
    'we observed AR thermal stabilisation upon the addition of DHT agonist, while the addition of Enzalutamide antagonist did not induce any thermal stabilisation (Fig.\xa02a). To confirm these observations, the assay format was '
    'switched to isothermal dose response fingerprints (ITDRFCETSA)7, whereby ligand concentration was varied in the presence of a heat shock at 46 °C. This temperature provided a suitable window between unbound and '
    'agonist-bound AR where the majority of cellular AR was thermally destabilised in the absence of agonist target engagement (Fig.\xa02a). In this format, we determined the relative potency of target engagement for a range of AR '
    'agonists (Fig.\xa02b), while a range of AR antagonists all failed to induce any thermal stabilisation at 46 °C (Fig.\xa02b, Supplementary Fig.\xa0S3). This data demonstrates that CETSA HT can be applied to determine the relative '
    'potency of target engagement, with the AR agonist testosterone, and a synthetic stable analogue R1881, demonstrating 50% effective concentrations (EC50) for in-cell AR target engagement of 1.7 and 1.2 nM respectively. The partial AR '
    'agonist Andrenosterone showed reduced potency of target engagement, with an EC50 of 50.6 nM. The inactive metabolic products of testosterone, dehydroisoandrosterone 3-sulphate and trans-dehydroandrosterone, showed only partial or '
    'no target engagement respectively (Fig.\xa02b). These observations were consistent in an alternative AR-positive prostate cancer cell line, LNCaP30, demonstrating the thermal behaviour of AR described herein is not only specific to '
    'CWR22Pc-R1-AD1 cells (Supplementary Fig.\xa0S3). Furthermore, a time-course of compound treatment revealed that thermal stabilisation of AR was apparent following 10 min incubation with testosterone or R1881, but complete thermal '
    'stabilisation required 30 min treatment with andrenosterone, suggesting a requirement for intracellular conversion into the active AR agonist. In contrast, no thermal stabilisation was observed at any point following up to 6 h '
    'treatment with a range of antagonists, confirming AR antagonists do not thermally stabilise AR upon target engagement (Supplementary Fig.\xa0S4).')

SYNTHETIC = (
    'Cellular thermal shift assays of the binding of the compound QX-7 to the kinase PZ-2 were done in intact HEK293 cells that were incubated with QX-7 for 1 h at 37 °C. '
    'For the melt curve, the cells were heated for 3 min at ten temperatures from 40 °C to 67 °C, and for the isothermal dose-response at 52 °C, and the soluble PZ-2 was read by western blot. '
    'DMSO vehicle controls were heated in the same way, and GAPDH was used as a loading control. The melting temperature of PZ-2 was 48.5 °C with the vehicle and 54.0 °C with 10 µM QX-7, '
    'a thermal shift of 5.5 °C, so QX-7 stabilised PZ-2 and engaged it in the cells. The standard deviation of the Tm was 0.4 °C, taken over the independent experiments. The temperature of 52 °C was in the melting transition of PZ-2 and gave a window between the unbound and the bound protein. '
    'The stabilisation increased with the concentration of QX-7 in a dose-response of eleven concentrations from 0.01 µM to 30 µM, with an EC50 of 0.8 µM and a standard error of 0.1 µM. '
    'The total amount of PZ-2 in unheated samples was not changed by QX-7. An inactive analogue of QX-7 did not stabilise PZ-2, and PZ-2 with a mutation of the binding site was not stabilised by QX-7. '
    'Cell viability was checked with a viability assay and was not changed by QX-7. Three independent experiments were done on separate days.')

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Synthetic: the compound QX-7 is tested against the kinase PZ-2 whose thermal stability is measured, so PZ-2 is the target and QX-7 the partner.
SYNTHETIC_TARGET = 'pz-2'
SYNTHETIC_PARTNER = 'qx-7'
# Real: the paragraph is about the thermal stability of AR (written 'AR'); it names several compounds (DHT, enzalutamide, testosterone, R1881, andrenosterone), so no single partner.
REAL_EXPECTED_TARGET = 'ar'
REAL_EXPECTED_PARTNER = None

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'engagement_ec50': (0.8, 'uM', 'an EC50 of 0.8 µM'),
    'engagement_ec50_spread': (0.1, 'uM', 'a standard error of 0.1 µM'),
    'tm_vehicle': (48.5, 'C', '48.5 °C with the vehicle'),
    'tm_ligand': (54.0, 'C', '54.0 °C with 10 µM QX-7'),
    'tm_shift': (5.5, 'C', 'a thermal shift of 5.5 °C'),
    'tm_spread': (0.4, 'C', 'standard deviation of the Tm was 0.4 °C'),
    'isothermal_temperature': (52, 'C', 'isothermal dose-response at 52 °C'),
    'heating_time': (3, 'min', 'heated for 3 min'),
    'temperature_lowest': (40, 'C', 'from 40 °C'),
    'temperature_highest': (67, 'C', 'to 67 °C'),
    'temperature_count': (10, 'count', 'at ten temperatures'),
    'compound_concentration_lowest': (0.01, 'uM', 'from 0.01 µM'),
    'compound_concentration_highest': (30, 'uM', 'to 30 µM'),
    'concentration_count': (11, 'count', 'eleven concentrations'),
    'compound_incubation_time': (1, 'h', 'incubated with QX-7 for 1 h'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    SAMPLE_FORMAT: ('intact_cells', None, 'in intact HEK293 cells'),
    EXPERIMENT_FORMAT: ('melt_curve_and_itdr', None, 'For the melt curve, the cells were heated for 3 min at ten temperatures from 40 °C to 67 °C, and for the isothermal dose-response at 52 °C'),
    READOUT: ('western_blot', None, 'the soluble PZ-2 was read by western blot'),
    SPREAD_KIND: ('standard_error', None, 'a standard error of 0.1 µM'),
    'target_engagement_shown': ('yes', None, 'so QX-7 stabilised PZ-2 and engaged it in the cells'),
    'vehicle_control_done': ('yes', None, 'DMSO vehicle controls were heated in the same way'),
    'loading_control_used': ('yes', None, 'GAPDH was used as a loading control'),
    'melt_curve_measured': ('yes', None, 'For the melt curve, the cells were heated for 3 min at ten temperatures'),
    'isothermal_temperature_in_window': ('yes', None, 'The temperature of 52 °C was in the melting transition of PZ-2 and gave a window between the unbound and the bound protein'),
    'dose_dependent_shown': ('yes', None, 'The stabilisation increased with the concentration of QX-7'),
    'negative_control_done': ('yes', None, 'An inactive analogue of QX-7 did not stabilise PZ-2'),
    'specificity_control_done': ('yes', None, 'PZ-2 with a mutation of the binding site was not stabilised by QX-7'),
    'cell_integrity_checked': ('yes', None, 'Cell viability was checked with a viability assay and was not changed by QX-7'),
    'total_target_level_controlled': ('yes', None, 'The total amount of PZ-2 in unheated samples was not changed by QX-7'),
    'independent_experiments': ('yes', None, 'Three independent experiments were done on separate days'),
    'tm_spread_over_independent_experiments': ('yes', None, 'taken over the independent experiments'),
}

# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Not allowed, because the paragraph does not
# state them or gives no single result: the EC50 (three compounds, none the result) and its spread, a melting temperature, its standard deviation (and whether it is over independent experiments) or a shift (none given), the heating time, a temperature range or count, the compound concentrations and their number,
# the incubation time (only a separate time-course), the readout (it is in the paragraph before), the vehicle, loading, specificity, viability and total-target controls, replicates.
REAL_ALLOWED = {
    'target_engagement_shown': {('yes', None)},
    'isothermal_temperature': {(46, 'C')},
    'isothermal_temperature_in_window': {('yes', None)},
    'dose_dependent_shown': {('yes', None)},
    'negative_control_done': {('yes', None)},
    SAMPLE_FORMAT: {('intact_cells', None)},
    EXPERIMENT_FORMAT: {('itdr', None), ('melt_curve_and_itdr', None)},
}


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
