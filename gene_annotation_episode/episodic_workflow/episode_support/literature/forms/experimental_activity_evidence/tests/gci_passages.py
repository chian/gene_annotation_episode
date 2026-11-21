"""Chunks of text for the GCI extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the GCI form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree, superscript two
and times signs) so byte offsets differ from character offsets.

``REAL`` is real: the first six sentences of the Results paragraph on the grating-coupled interferometry (GCI) measurement of 'CrcA' binding to
'Crc' in 'Catabolite repression control protein antagonist, a novel player in Pseudomonas aeruginosa carbon catabolite
repression control' (Frontiers in Microbiology 2023, doi 10.3389/fmicb.2023.1195558, PMC10213629, open access, CC BY), exactly as the
publisher's XML gives it (thin spaces U+2009 before the units, the Greek mu U+03BC, the degree sign and the plus-minus
sign). It states that Crc was immobilized at 15 pg/mm2 on a 4-PCP WAVE chip, that CrcA was applied in serial dilutions
from 20 uM to 156.25 nM (a range, no list), that the analysis gave a 1:1 kinetic with KD 10.99 uM at 25 degrees, and a
steady-state ('equilibration curve') KD of 11.99 +- 0.00 uM, and then reports a different experiment (a positive control
with the Hfq/amiE6ARN complex, KD2 112.310 nM). The chunk ends before the paragraph's seventh sentence, which repeats the
words '1:1 kinetic' (for that other complex): with it a natural quote of the fit model occurs twice and is refused (a
real model run met this), so the chunk is the paragraph up to there. It says nothing of kon, koff, the response, the
replicates, referencing, regeneration or mass transport, and states no molecular mass, stoichiometry or dissociation
time (so the real paragraph's expected sets are unchanged by the four fields analyte_mass, ligand_mass, stoichiometry
and dissociation_time; the name of its '1:1 kinetic' fit is not a stoichiometry statement, and the form says so)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_gci_extraction import (
    CHIP_TYPE, FIT_MODEL, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_gci_record import UNITS

PAPER_ID = 'PMC10213629'
REAL = (
    'Next, grating coupled interferometry (GCI), a surface plasmon resonance (SPR) related approach, was used to '
    'confirm the interaction between CrcA and Crc. Crc was immobilized at a low concentration (15 pg/mm2) to the '
    'surface of the 4-PCP-WAVE-chip (see Materials and Methods), and then serial dilutions of CrcA protein (from '
    '20 μM to 156.25 nM) were added. The corresponding sensorgram is shown in Figure 4A. The analysis '
    'revealed a 1:1 kinetic with an equilibration constant KD of 10.99 μM at 25°C with high dissociation '
    'and association rates. The equilibration curve analysis resulted in a similar KD of 11.99 ± 0.00 '
    'μM (Supplementary Figure S7A), suggesting a low affinity of CrcA for Crc. As a positive control, we used '
    'different concentrations of the Hfq/amiE6ARN protein/RNA complex (Figure 4B) that interacts with Crc '
    '(Sonnleitner et al., 2018; Pei et al., 2019). The determined KD2 value (112.310 nM; Figure 4B) is comparable '
    'with the dissociation constant revealed in solution by microscale thermophoresis (134.6\u2009nM) (Sonnleitner et '
    'al., 2018).')

SYNTHETIC = (
    'Grating-coupled interferometry was performed on a Creoptix WAVEdelta at 25 °C. The assay measured the binding of the protein ParB to its partner PopZ. Biotinylated ParB was captured '
    'on a streptavidin-coated WAVEchip to an immobilization level of 500 pg/mm² on one channel; a reference '
    'channel carried no ParB, and its signal was subtracted from the signal of the measuring channel. The data were '
    'also double referenced against blank buffer injections, and DMSO solvent-correction injections were used to '
    'correct the bulk effect of the 1% DMSO in the running buffer. The baseline was stable, with no significant '
    'drift. Non-specific binding of PopZ to a blank streptavidin surface was checked. The ParB on the chip was '
    'active: it bound its known partner. The analyte PopZ is not bivalent or oligomeric under these conditions. '
    'Mass-transport limitation was checked by repeating the injections at two flow rates. Kinetics were measured '
    'with the waveRAPID method, using repeated short pulses of a single concentration of 200 nM. The sensorgrams '
    'were globally fitted with a 1:1 model, which gave kon = 1.0 × 10^5 M^-1 s^-1 and koff = 2.0 × 10^-3 '
    's^-1, giving KD = 20 nM (standard deviation 3 nM). The maximum response was 40 pg/mm². '
    'The molecular mass of ParB is 100 kDa and that of PopZ is 20 kDa, and the stoichiometry is one PopZ molecule '
    'bound per ParB molecule. Dissociation was followed for 600 s after each pulse. A steady-state fit '
    'of the equilibrium responses gave KD = 30 nM, so both a kinetic and a steady-state estimate were made. The '
    'surface was regenerated with 10 mM glycine pH 1.7 without loss of binding capacity. Three independent '
    'experiments were done on separate channels of separate chips.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'kd_steady_state': (30, 'nM', 'steady-state fit of the equilibrium responses gave KD = 30 nM'),
    'kon': (100000, 'M^-1 s^-1', 'kon = 1.0 × 10^5 M^-1 s^-1'),
    'koff': (0.002, 's^-1', 'koff = 2.0 × 10^-3 s^-1'),
    'response_max': (40, 'pg/mm2', 'The maximum response was 40 pg/mm²'),
    'kd_spread': (3, 'nM', 'standard deviation 3 nM'),
    'immobilization_level': (500, 'pg/mm2', 'an immobilization level of 500 pg/mm²'),
    'analyte_mass': (20, 'kDa', 'that of PopZ is 20 kDa'),
    'ligand_mass': (100, 'kDa', 'mass of ParB is 100 kDa'),
    'stoichiometry': (1, 'dimensionless', 'one PopZ molecule bound per ParB molecule'),
    'dissociation_time': (600, 's', 'Dissociation was followed for 600 s'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    SERIES: ([200], 'nM', 'a single concentration of 200 nM'),
    SPREAD_KIND: ('standard_deviation', None, 'standard deviation 3 nM'),
    FIT_MODEL: ('1:1', None, 'globally fitted with a 1:1 model'),
    CHIP_TYPE: ('streptavidin', None, 'streptavidin-coated WAVEchip'),
    'reference_channel_subtracted': ('yes', None, 'a reference channel carried no ParB, and its signal was subtracted'),
    'double_referenced': ('yes', None, 'The data were also double referenced against blank buffer injections'),
    'bulk_solvent_corrected': ('yes', None, 'DMSO solvent-correction injections were used to correct the bulk effect'),
    'baseline_stable': ('yes', None, 'The baseline was stable'),
    'regeneration': ('yes', None, 'The surface was regenerated with 10 mM glycine pH 1.7'),
    'independent_channels_or_chips': ('yes', None, 'Three independent experiments were done on separate channels of separate chips'),
    'immobilized_partner_active': ('yes', None, 'The ParB on the chip was active'),
    'analyte_bivalent_or_oligomeric': ('no', None, 'PopZ is not bivalent or oligomeric'),
    'mass_transport_checked': ('yes', None, 'Mass-transport limitation was checked'),
    'nonspecific_binding_checked': ('yes', None, 'Non-specific binding of PopZ to a blank streptavidin surface was checked'),
    'single_estimate_method': ('no', None, 'both a kinetic and a steady-state estimate were made'),
    'repeated_pulse_kinetics_used': ('yes', None, 'Kinetics were measured with the waveRAPID method, using repeated short pulses'),
}

# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about (CrcA on Crc).
REAL_STATED = {
    'kd': (10.99, 'uM', 'KD of 10.99 μM'),
    'kd_steady_state': (11.99, 'uM', 'KD of 11.99 ± 0.00 μM'),
    'immobilization_level': (15, 'pg/mm2', '15 pg/mm2'),
    'fit_model': ('1:1', None, 'a 1:1 kinetic'),
}
# What else a careful reader may also state from the real passage (a judgement the passage supports, not a number):
# the chip chemistry (a 4-PCP chip), that two estimates of the KD were made, that the immobilized Crc is active (the
# positive control shows it binding a known partner) and that non-specific binding was checked.
REAL_MAY_ALSO_STATE = {'chip_type', 'single_estimate_method', 'nonspecific_binding_checked'}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'popz'
# The real paragraph is about the interaction between CrcA and Crc (Crc immobilized, CrcA the analyte, and the paragraph
# also reports a positive control); which of the two is the molecule assayed is ambiguous, so no single target is expected.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('crca',), ('crc',))     # symmetric pair named by the paragraph; either orientation accepted


def answer_from(chunk, stated):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable."""
    answer = {}
    for name in field_names():
        carries_unit = name in UNITS
        if name in stated:
            value, unit, quote = stated[name]
            answer[name] = {'status': 'stated', 'value': value, 'quote': quote, 'support': 'direct', 'reason': None,
                            **({'unit': unit} if carries_unit else {})}
        else:
            answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None,
                            'reason': 'not_stated_in_passage', **({'unit': None} if carries_unit else {})}
    return answer


def synthetic_answer():
    return answer_from(SYNTHETIC, SYNTHETIC_STATED)


def real_answer():
    return answer_from(REAL, REAL_STATED)
