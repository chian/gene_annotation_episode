"""Chunks of text for the EMSA (electrophoretic mobility shift assay, gel shift) extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (micro and degree signs) so byte
offsets differ from character offsets.

``REAL`` is real: a Results paragraph of 'Insights into the regulation of small RNA expression: SarA represses the expression of two sRNAs in Staphylococcus aureus'
(Nucleic Acids Research 2016, doi 10.1093/nar/gkw777, PMC5137438, PMID 27596601, open access under the Creative Commons Attribution-NonCommercial 4.0 licence,
(c) The Author(s) 2016, Oxford University Press), the paragraph that begins 'We used EMSA for binding assays of purified SarA on the srn_9340 promoter region', as the
publisher's XML gives the paragraph's own text with the markup (italics, subscripts and the figure links) removed: the paragraph is whole (one paragraph in the XML,
nothing removed). The text is exactly as the XML gives it, including its typographic characters (the minus sign, the quotation marks, the plus-minus sign) and the
missing space in 'srn_9340P225effectively' where a subscript meets the next word. It reports a titration of the purified protein SarA against a PCR-fragment probe, an apparent
Kd of 11 +/- 0.2 nM, a second (upper) shifted band, competition with a 10-fold excess of the unlabelled probe, and no displacement by a 100-fold excess of an unlabelled non-specific
fragment. It gives no probe length or label that belongs to this probe alone, no buffer, incubation, gel or run, no protein concentrations, no fit model and no replicates.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_extraction import (
    COMPETITOR_TYPE, FIT_MODEL, GEL_TYPE, PROBE_LABEL, PROBE_TYPE, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import UNITS

PAPER_ID = 'PMC5137438'
REAL = (
    'We used EMSA for binding assays of purified SarA on the srn_9340 promoter region (Figure 5C). We synthesized a PCR fragment of srn_9340 nucleotides −165 to +60 '
    '(with the coding sequence starting at +1), and named this ‘srn_9340P225.’ We observed a distinct SarA/srn_9340P225 complex with an apparent Kd of 11 ± 0.2 nM '
    '(Figure 5C, middle arrow). The complex has an abundance that is positively linked to SarA quantities. A second band shift then appeared which probably correspond to '
    'protein aggregation onto the DNA probe (Figure 5C, upper band). A 10-fold excess of srn_9340P225effectively competed with the labeled promoter fragment for SarA binding, '
    'whereas a 100-fold excess of 16S225, an unlabeled non-specific 225 pb 16S DNA fragment, did not displace the labeled one from the complex (Figure 5D). Together, these '
    'results indicate that SarA directly and specifically binds the srn_9340 promoter in vitro.')

SYNTHETIC = (
    'EMSA of the binding of DX-5 to the DX-5 site was done with a 28 bp double-stranded DNA probe labelled with 32P. The EMSA tested the protein DX-5 against its DNA probe PZ-2, a fragment carrying the DX-5 site. The probe was at 0.5 nM in the binding reaction, and purified DX-5 '
    'was added at 11 concentrations from 1 nM to 640 nM. The binding buffer held 100 mM KCl, 5 mM MgCl2 and 10% glycerol, with 50 ng of poly(dI-dC) in each 20 µl reaction. '
    'The reactions were incubated for 30 min at 25 °C, and a time course showed that binding had reached equilibrium by 20 min. They were run on a 6% native polyacrylamide '
    'gel at 10 V/cm for 90 min at 4 °C. A lane with the probe alone was run beside the reactions. DX-5 gave a shifted band with the probe. A 100-fold excess of the unlabelled '
    'specific probe abolished the shifted band, whereas a 200-fold excess of an unlabelled unrelated DNA did not abolish it. A probe with the DX-5 site mutated did not shift. '
    'Bovine serum albumin in place of DX-5 did not shift the probe. An anti-DX-5 antibody gave a supershift, which confirms that the protein in the complex is DX-5. '
    'The complex was stable in the gel run, with no smear between the shifted band and the free probe. The free and shifted probe were quantified by phosphorimager, and 92% of '
    'the probe was shifted at 640 nM DX-5. The shifted fraction against the protein concentration was fitted with a one-site binding model, which gave an apparent KD of 20 nM with '
    'a standard deviation of 2 nM. The probe concentration was below the KD, and the protein concentrations spanned the KD, from well below it to saturation. Only one shifted band '
    'was seen. Three independent experiments were done on separate days, and the KD was determined by this gel shift method only.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'an apparent KD of 20 nM'),
    'kd_spread': (2, 'nM', 'a standard deviation of 2 nM'),
    'fraction_shifted_highest': (92, 'percent', '92% of the probe was shifted'),
    'protein_concentration_lowest': (1, 'nM', 'from 1 nM'),
    'protein_concentration_highest': (640, 'nM', 'to 640 nM'),
    'probe_concentration': (0.5, 'nM', 'The probe was at 0.5 nM'),
    'probe_length': (28, 'bp', 'a 28 bp'),
    'salt_concentration': (100, 'mM', '100 mM KCl'),
    'magnesium_concentration': (5, 'mM', '5 mM MgCl2'),
    'glycerol_percent': (10, 'percent', '10% glycerol'),
    'nonspecific_competitor_amount': (50, 'ng', '50 ng of poly(dI-dC)'),
    'specific_competitor_excess': (100, 'ratio', 'A 100-fold excess of the unlabelled specific probe'),
    'incubation_time': (30, 'min', 'incubated for 30 min'),
    'incubation_temperature': (25, 'C', 'at 25 °C'),
    'gel_percent': (6, 'percent', 'a 6% native polyacrylamide gel'),
    'run_time': (90, 'min', 'for 90 min'),
    'run_voltage': (10, 'V/cm', 'at 10 V/cm'),
    'run_temperature': (4, 'C', '90 min at 4 °C'),
    'titration_point_count': (11, 'count', 'at 11 concentrations'),
    'shifted_species_count': (1, 'count', 'Only one shifted band was seen'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    PROBE_TYPE: ('dsdna', None, 'double-stranded DNA probe'),
    PROBE_LABEL: ('p32', None, 'labelled with 32P'),
    GEL_TYPE: ('native_polyacrylamide', None, 'native polyacrylamide gel'),
    COMPETITOR_TYPE: ('poly_dI_dC', None, 'poly(dI-dC)'),
    SPREAD_KIND: ('standard_deviation', None, 'a standard deviation of 2 nM'),
    FIT_MODEL: ('one_site', None, 'fitted with a one-site binding model'),
    'shift_detected': ('yes', None, 'DX-5 gave a shifted band'),
    'shift_abolished_by_specific_competitor': ('yes', None, 'abolished the shifted band'),
    'shift_not_abolished_by_nonspecific_competitor': ('yes', None, 'did not abolish it'),
    'mutant_probe_does_not_shift': ('yes', None, 'A probe with the DX-5 site mutated did not shift'),
    'probe_alone_lane_shown': ('yes', None, 'A lane with the probe alone was run'),
    'nonspecific_protein_control_done': ('yes', None, 'Bovine serum albumin in place of DX-5 did not shift the probe'),
    'free_probe_quantified': ('yes', None, 'The free and shifted probe were quantified by phosphorimager'),
    'probe_at_or_below_kd': ('yes', None, 'The probe concentration was below the KD'),
    'equilibrium_reached': ('yes', None, 'binding had reached equilibrium by 20 min'),
    'supershift_confirms_protein_identity': ('yes', None, 'An anti-DX-5 antibody gave a supershift'),
    'protein_purified': ('yes', None, 'purified DX-5'),
    'complex_survives_gel_run': ('yes', None, 'The complex was stable in the gel run'),
    'protein_range_brackets_kd': ('yes', None, 'the protein concentrations spanned the KD'),
    'independent_experiments': ('yes', None, 'Three independent experiments were done on separate days'),
    'single_estimate_method': ('yes', None, 'determined by this gel shift method only'),
}

# field -> (value, unit, quote) for the real passage: what a careful reader may state from it about the experiment it describes, with the
# quote that says it.
REAL_STATED = {
    'kd': (11, 'nM', 'apparent Kd of 11 ± 0.2 nM'),
    'kd_spread': (0.2, 'nM', 'apparent Kd of 11 ± 0.2 nM'),
    'specific_competitor_excess': (10, 'ratio', 'A 10-fold excess of srn_9340P225effectively competed'),
    'shift_detected': ('yes', None, 'We observed a distinct SarA/srn_9340P225 complex'),
    'shift_abolished_by_specific_competitor': ('yes', None, 'effectively competed with the labeled promoter fragment for SarA binding'),
    'shift_not_abolished_by_nonspecific_competitor': ('yes', None, 'did not displace the labeled one from the complex'),
    'protein_purified': ('yes', None, 'purified SarA'),
}
# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. The number of shifted species is allowed
# with the value 2 ('A second band shift then appeared' after 'a distinct complex': two shifted bands). Not allowed, because the paragraph does not
# state them: the probe length and type of this probe (the '225' names the fragment and the only stated length, '225 pb', is of the non-specific
# fragment), the label, any concentration of the probe or the protein, the buffer, incubation, gel, run, the number of titration points, replicates,
# the fit model, the spread kind, the supershift, the mutant probe, the probe-alone lane, quantification, equilibrium and the stability of the complex.
REAL_ALLOWED = {**{name: {(value, unit)} for name, (value, unit, _) in REAL_STATED.items()}, 'shifted_species_count': {(2, 'count')}}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
# Real paragraph: SarA is the target. The DNA is named twice (the 'srn_9340 promoter region' and the fragment 'srn_9340P225'), so the partner is left None as ambiguous.
SYNTHETIC_TARGET = 'dx-5'
SYNTHETIC_PARTNER = 'pz-2'
REAL_EXPECTED_TARGET = 'sara'
REAL_EXPECTED_PARTNER = None


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


REAL_PERCENT = (5, 'percent', '(Figure 5')       # not a shifted fraction: used only to test quote refusals ('(Figure 5' occurs four times)


def real_answer():
    return answer_from(REAL, REAL_STATED)
