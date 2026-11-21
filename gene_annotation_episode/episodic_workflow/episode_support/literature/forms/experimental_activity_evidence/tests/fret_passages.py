"""Chunks of text for the FRET extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the FRET form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (micro and degree signs) so
byte offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the TR-FRET assay validation of CoraFluor-1 (terbium) labelled KLHL11 and
AF488-labelled CUL3 N-terminal domain in 'Structural and biochemical characterization establishes a detailed understanding
of KEAP1-CUL3 complex assembly' (Free Radical Biology & Medicine 2023, doi 10.1016/j.freeradbiomed.2023.04.021,
PMC10564622, PMID 37156295, open access, CC BY 4.0), exactly as the publisher's XML gives the paragraph's own text
(non-breaking spaces U+00A0 inside '20 nM', an en dash U+2013 in the confidence interval, a minus sign U+2212 in the
exponents and a tilde operator U+223C). It states that the donor and the acceptor were attached directly by acylation (not through
tag antibodies or streptavidin), that a saturation binding experiment gave a KD of 20 nM (95% CI 19-22 nM), that the
dissociation rate constant gave an assay equilibration time of about 15 min, that displacement by unlabelled competitors
gave similar KD values and that the dye labelling did not alter the affinity. It says nothing of the concentrations, the
delay and window, the ratio ends, the plate, the volume, the incubation, the number of replicates or the fit model; those
are in the paper's Methods, which are not in this chunk. The paragraph is whole (no sentence was removed); the figure
legend that follows it in the publisher's XML (it repeats 'KD value of 20 nM') is a separate figure element and is not part of
the paragraph's own text."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_extraction import (
    ASSAY_FORMAT, FIT_MODEL, PAIR, PLATE_TYPE, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_record import UNITS

PAPER_ID = 'PMC10564622'
REAL = (
    'We rationalized that pairwise labeling of BTB-containing proteins and CUL3NTD would provide a straightforward and '
    'target-agnostic strategy for the characterization of binding affinities (Fig. 6A–D). TR-FRET donor and acceptor '
    'functionalization was accomplished through direct acylation using CoraFluor-1-Pfp and AF488-Tfp, respectively '
    '[[54], [55], [56]]. We selected direct chemical labeling over the use of labeled anti-epitope tag antibodies or '
    'streptavidin, which can complicate data interpretation due to the formation of higher-order complexes. To validate '
    'our approach, we first performed a saturation binding experiment with CoraFluor-1-labeled KLHL11BTB-BACK and '
    'AF488-CUL3NTD, which yielded a KD value of 20\xa0nM (95% CI 19–22\xa0nM), consistent with our previous ITC data '
    '(Fig. 6B) [29]. Direct measurement of the dissociation rate constant (koff\xa0=\xa03.81\xa0×\xa010−3 s−1) was determined '
    'by the addition of an excess of the respective unlabeled competitor to preequilibrated TR-FRET donor and acceptor '
    'functionalized protein complexes, establishing an assay equilibration time of ∼15\xa0min (5\xa0×\xa0t1/2) '
    '(Fig. 6C) [57,58]. Dose-response titration of unlabeled CUL3NTD or KLHL11BTB-BACK as competitors yielded similar KD '
    'values (Fig. 6D) and provided evidence that dye functionalization was well tolerated and did not alter the binding '
    'affinity (Table S2).')

SYNTHETIC = (
    'TR-FRET binding assays were carried out in white 384-well plates in a volume of 20 µL at 25 °C. The assay measured the binding of the protein ParB to its partner PopZ. The read was '
    'time-resolved, with a delay of 100 µs and an integration window of 400 µs, using a terbium cryptate donor on ParB '
    'and a d2 acceptor on its partner peptide. The proteins were labelled directly with the dyes, not through antibodies '
    'or streptavidin, and labelled and unlabelled ParB gave the same affinity, so the labels did not alter binding. In '
    'the direct titration, the donor-labelled ParB was held at 5 nM, below the KD, and samples were incubated for 60 min; '
    'the ratio was stable over a further hour, so binding was at equilibrium. The peptide was titrated in ten '
    'concentrations of 2, 4, 10, 20, 40, 100, 200, 400, 1000 and 2000 nM. The signal was calculated for each well as '
    'the ratio of the 665 nm acceptor emission to the 620 nm donor emission; the emission ratio was 0.4 at the bottom '
    'of the curve and rose to 1.6 at the plateau. Wells with the donor alone and wells with the acceptor alone were '
    'measured, and the bleed-through was subtracted. Interference of the peptide with the signal by absorbance or '
    'fluorescence was checked. Depletion was considered, and the data were fitted with a quadratic (tight-binding) '
    'model, giving KD = 20 nM (standard error 2 nM) and EC50 = 31 nM. Non-specific signal was checked with a '
    'non-binding mutant, and an excess of unlabelled peptide displaced the labelled partner. The same ParB-peptide '
    'interaction was also measured in the same assay by competition: the acceptor-labelled peptide was held at 30 nM '
    'and an unlabelled ligand gave Ki = 40 nM (standard error 4 nM) and IC50 = 85 nM; the affinity was thus estimated '
    'both by direct titration and by competition. Three '
    'independent titrations were done on separate days with fresh dilution series.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'ki': (40, 'nM', 'Ki = 40 nM'),
    'ec50': (31, 'nM', 'EC50 = 31 nM'),
    'ic50': (85, 'nM', 'IC50 = 85 nM'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'ki_spread': (4, 'nM', '(standard error 4 nM)'),
    'donor_concentration': (5, 'nM', 'donor-labelled ParB was held at 5 nM'),
    'acceptor_concentration': (30, 'nM', 'acceptor-labelled peptide was held at 30 nM'),
    'ratio_minimum': (0.4, 'ratio', 'emission ratio was 0.4'),
    'ratio_maximum': (1.6, 'ratio', 'rose to 1.6'),
    'delay_time': (100, 'us', 'a delay of 100 µs'),
    'integration_time': (400, 'us', 'an integration window of 400 µs'),
    'assay_volume': (20, 'uL', 'a volume of 20 µL'),
    'incubation_time': (60, 'min', 'incubated for 60 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'replicate_count': (3, 'count', 'Three independent titrations'),
    SERIES: ([2, 4, 10, 20, 40, 100, 200, 400, 1000, 2000], 'nM', 'ten concentrations of 2, 4, 10, 20, 40, 100, 200, 400, 1000 and 2000 nM'),
    ASSAY_FORMAT: ('direct_titration', None, 'In the direct titration'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('quadratic', None, 'a quadratic (tight-binding) model'),
    PLATE_TYPE: ('white', None, 'white 384-well plates'),
    PAIR: ('lanthanide_with_organic_acceptor', None, 'a terbium cryptate donor on ParB and a d2 acceptor'),
    'time_resolved_read': ('yes', None, 'The read was time-resolved'),
    'ratiometric_readout_used': ('yes', None, 'the ratio of the 665 nm acceptor emission to the 620 nm donor emission'),
    'donor_only_control_measured': ('yes', None, 'Wells with the donor alone'),
    'acceptor_only_control_measured': ('yes', None, 'wells with the acceptor alone'),
    'crosstalk_corrected': ('yes', None, 'the bleed-through was subtracted'),
    'labelled_partner_at_or_below_kd': ('yes', None, 'was held at 5 nM, below the KD'),
    'tight_binding_considered': ('yes', None, 'Depletion was considered'),
    'equilibrium_reached': ('yes', None, 'so binding was at equilibrium'),
    'indirect_labelling_used': ('no', None, 'labelled directly with the dyes, not through antibodies or streptavidin'),
    'labelling_does_not_alter_binding': ('yes', None, 'so the labels did not alter binding'),
    'compound_interference_checked': ('yes', None, 'Interference of the peptide with the signal by absorbance or fluorescence was checked'),
    'nonspecific_binding_checked': ('yes', None, 'Non-specific signal was checked with a non-binding mutant'),
    'unlabelled_competitor_displaces': ('yes', None, 'an excess of unlabelled peptide displaced the labelled partner'),
    'independent_titrations': ('yes', None, 'Three independent titrations were done on separate days'),
    'single_estimate_method': ('no', None, 'estimated both by direct titration and by competition'),
}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'popz'
# The real paragraph labels both KLHL11BTB-BACK and CUL3NTD and titrates either against the other (saturation binding,
# competition by either unlabelled protein): the two are symmetric, so no single target is expected.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('klhl11btb-back',), ('cul3ntd',))     # symmetric pair named by the paragraph; either orientation accepted

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about.
REAL_STATED = {
    'kd': (20, 'nM', 'KD value of 20\xa0nM'),
    SPREAD_KIND: ('confidence_interval', None, '95% CI 19–22\xa0nM'),
    ASSAY_FORMAT: ('direct_titration', None, 'saturation binding experiment'),
    'time_resolved_read': ('yes', None, 'TR-FRET donor and acceptor functionalization'),
    'indirect_labelling_used': ('no', None, 'We selected direct chemical labeling over the use of labeled anti-epitope tag antibodies or streptavidin'),
    'labelling_does_not_alter_binding': ('yes', None, 'dye functionalization was well tolerated and did not alter the binding affinity'),
}
# What else a careful reader may also state from the real passage (a judgement the passage supports, not a number): that an
# excess of unlabelled competitor displaced the labelled partner and that both the saturation and the displacement format
# were used. The paragraph does not name the kind of donor, does not give the incubation time, and does not say the read
# was made after the equilibration time: none of those may be stated.
REAL_MAY_ALSO_STATE = {'unlabelled_competitor_displaces', 'single_estimate_method'}


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
