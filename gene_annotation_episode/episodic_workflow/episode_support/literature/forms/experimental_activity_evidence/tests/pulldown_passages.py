"""Chunks of text for the pull-down / co-IP extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree and micro signs) so byte
offsets differ from character offsets.

``REAL`` is real: the Results paragraph 'RECQ1 Exists in Complex with Ku70/80 Heterodimer' of 'Human RECQ1 interacts with Ku70/80 and modulates DNA
end-joining of double-strand breaks' (Parvathaneni et al., PLoS ONE 2013, doi 10.1371/journal.pone.0062481, PMC3641083, PMID 23650516, open access, CC0
public domain dedication), as the publisher's XML gives the paragraph's own text with the markup (the figure links) removed: the paragraph is whole (one
paragraph in the XML, nothing removed), plain ASCII. It says how the interaction was tested: a reciprocal immunoprecipitation with specific antibodies
from HeLa cell nuclear extracts, western blots showing that the RECQ1 antibody co-precipitated Ku70 and Ku80 and the Ku70/80 immunoprecipitation
co-precipitated RECQ1, normal IgG failing to pull down any of the three, and the interaction surviving benzonase treatment of the extract. It gives no
wash, incubation, input lane, number of experiments, endogenous level, competition or specificity control, and no number at all.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_extraction import (
    CAPTURE, CROSSLINKER, DETECTION, NUCLEASE, SOURCE, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import UNITS

PAPER_ID = 'PMC3641083'
REAL = (
    'To determine if RECQ1 interacts with Ku70/80, we performed reciprocal immunoprecipitation using specific antibodies from HeLa cell nuclear extracts (Fig. 1A). '
    'Western blot analyses showed RECQ1 antibody specifically co-precipitated Ku70 and Ku80 and immunoprecipitation of Ku70/80 resulted in co-precipitation of RECQ1 (Fig. 1A). '
    'Similar immunoprecipitation using normal IgG failed to pull down RECQ1, Ku70 or Ku80 (Fig. 1A). '
    'The presence of EtBr (data not shown) or the use of benzonase-treated extract in immunoprecipitation reaction did not abolish co-precipitation of Ku70/80 and RECQ1, suggesting that the interaction is not mediated by DNA (Fig. 1B).')

SYNTHETIC = (
    'Pull-down of DX-9 by GST-DX-3 was done from a lysate of HEK293 cells. This pull-down tested the binding of the prey protein DX-9 to its partner, the bait protein DX-3. 50 µl of glutathione beads carried the bait. GST-DX-3 was bound to glutathione beads and incubated '
    'with the cell lysate for 2 h at 4 °C. No crosslinker was used. The beads were washed 4 times with a buffer of 300 mM NaCl and 0.1% Triton X-100, and the bound proteins '
    'were eluted with sample buffer. 5% of the lysate was loaded as the input lane. DX-9 was detected in the eluate by western blot, and the DX-9 band in the GST-DX-3 eluate '
    'was 12-fold stronger than in the control. 4% of the input DX-9 was recovered in the eluate. Over the experiments the fold enrichment had a standard deviation of 2.6 and a standard error of the mean of 1.5. A control with GST alone on glutathione beads was done, and DX-9 was absent '
    'from the GST-alone eluate. A positive control with the known interacting pair DX-5 and DX-6, taken through the same wash, gave the expected band. A control in which the lysate was incubated with the beads without GST-DX-3 showed that DX-9 does not bind the beads alone. The pull-down was '
    'also done the other way round with GST-DX-9, and DX-3 was found, so the interaction was reciprocal. Competition with excess untagged DX-3 abolished the capture of DX-9. '
    'The interaction survived treatment of the lysate with benzonase, so it was not bridged by nucleic acid. Purified recombinant GST-DX-3 and purified DX-9 also interacted, '
    'so the interaction is direct. The DX-3 and DX-9 in the lysate were at their endogenous levels, not overexpressed. The band intensities were quantified and normalized to '
    'the input. The anti-DX-9 antibody was validated with a DX-9 knockdown control. 3 independent experiments were done on separate days.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'fold_enrichment': (12, 'ratio', '12-fold stronger than in the control'),
    'fold_enrichment_sd': (2.6, 'ratio', 'a standard deviation of 2.6'),
    'fold_enrichment_sem': (1.5, 'ratio', 'a standard error of the mean of 1.5'),
    'percent_input_recovered': (4, 'percent', '4% of the input DX-9 was recovered'),
    'input_fraction': (5, 'percent', '5% of the lysate was loaded as the input lane'),
    'nacl_wash': (300, 'mM', 'a buffer of 300 mM NaCl'),
    'detergent_wash': (0.1, 'percent', '0.1% Triton X-100'),
    'wash_count': (4, 'count', 'washed 4 times'),
    'incubation_time': (2, 'h', 'incubated with the cell lysate for 2 h'),
    'incubation_temperature': (4, 'C', 'for 2 h at 4 °C'),
    'replicate_count': (3, 'count', '3 independent experiments'),
    DETECTION: ('western_blot', None, 'detected in the eluate by western blot'),
    CAPTURE: ('gst', None, 'GST-DX-3 was bound to glutathione beads'),
    SOURCE: ('cell_lysate', None, 'from a lysate of HEK293 cells'),
    NUCLEASE: ('benzonase', None, 'treatment of the lysate with benzonase'),
    CROSSLINKER: ('none', None, 'No crosslinker was used'),
    'prey_detected_in_eluate': ('yes', None, 'DX-9 was detected in the eluate by western blot'),
    'negative_control_done': ('yes', None, 'A control with GST alone on glutathione beads was done'),
    'prey_absent_in_negative_control': ('yes', None, 'DX-9 was absent from the GST-alone eluate'),
    'positive_control_detected': ('yes', None, 'A positive control with the known interacting pair DX-5 and DX-6, taken through the same wash, gave the expected band'),
    'bait_minus_control_done': ('yes', None, 'DX-9 does not bind the beads alone'),
    'input_lane_shown': ('yes', None, 'was loaded as the input lane'),
    'reciprocal_done': ('yes', None, 'the interaction was reciprocal'),
    'competition_disrupts_interaction': ('yes', None, 'Competition with excess untagged DX-3 abolished the capture of DX-9'),
    'interaction_survives_nuclease': ('yes', None, 'The interaction survived treatment of the lysate with benzonase'),
    'direct_interaction_shown': ('yes', None, 'so the interaction is direct'),
    'endogenous_expression_levels': ('yes', None, 'were at their endogenous levels'),
    'quantification_with_normalization': ('yes', None, 'quantified and normalized to the input'),
    'specificity_validated': ('yes', None, 'was validated with a DX-9 knockdown control'),
    'independent_experiments': ('yes', None, '3 independent experiments were done on separate days'),
}

# field -> (value, unit, quote) for the real passage: what a careful reader may state from it about the experiment it describes, with the
# quote that says it.
REAL_STATED = {
    DETECTION: ('western_blot', None, 'Western blot analyses showed'),
    CAPTURE: ('antibody', None, 'using specific antibodies from HeLa cell nuclear extracts'),
    SOURCE: ('cell_lysate', None, 'HeLa cell nuclear extracts'),
    NUCLEASE: ('benzonase', None, 'benzonase-treated extract'),
    'prey_detected_in_eluate': ('yes', None, 'RECQ1 antibody specifically co-precipitated Ku70 and Ku80'),
    'reciprocal_done': ('yes', None, 'immunoprecipitation of Ku70/80 resulted in co-precipitation of RECQ1'),
    'negative_control_done': ('yes', None, 'Similar immunoprecipitation using normal IgG'),
    'prey_absent_in_negative_control': ('yes', None, 'normal IgG failed to pull down RECQ1, Ku70 or Ku80'),
    'interaction_survives_nuclease': ('yes', None, 'the use of benzonase-treated extract in immunoprecipitation reaction did not abolish co-precipitation of Ku70/80 and RECQ1'),
}
# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Not allowed, because the paragraph does
# not state them: every number (it has none), a direct interaction (the paragraph describes a co-immunoprecipitation from extracts, which does not state
# it), endogenous levels, the input lane, the control without the bait, competition, specificity validation, quantification, independent experiments,
# the crosslinker, and the wash.
REAL_ALLOWED = {name: {(value, unit)} for name, (value, unit, _) in REAL_STATED.items()}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Real paragraph: the test is whether RECQ1 interacts with Ku70/80, so RECQ1 is the target and the Ku70/80 heterodimer its partner (the antibodies and IgG are reagents).
SYNTHETIC_TARGET = 'dx-9'
SYNTHETIC_PARTNER = 'dx-3'
REAL_EXPECTED_TARGET = 'recq1'
REAL_EXPECTED_PARTNER = 'ku70/80'


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


REAL_FOLD = (3, 'ratio', '(Fig. 1A)')       # not a fold enrichment: used only to test quote refusals ('(Fig. 1A)' occurs three times)


# The normal-IgG capture is only implied to be the negative control: the quote says it was done with normal IgG, not that it was a control.
REAL_SUPPORT = {'negative_control_done': 'implied'}


def real_answer():
    return answer_from(REAL, REAL_STATED, REAL_SUPPORT)
