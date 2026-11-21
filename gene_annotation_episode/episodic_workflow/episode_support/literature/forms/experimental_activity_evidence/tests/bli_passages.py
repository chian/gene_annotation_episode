"""Chunks of text for the BLI extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the BLI form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree, micro, times
and superscript two signs) so byte offsets differ from character offsets.

``REAL`` is real: the Methods paragraph of 'Inhibition of Chikungunya virus nsP2 protease in vitro by scorpion venom
peptide pantinin-1', PLOS ONE, doi 10.1371/journal.pone.0346930, PMC13065029 (open access, CC BY), exactly as the
publisher's XML gives it (it mixes the micro sign U+00B5 and the Greek mu U+03BC, and has thin spaces U+2009 before
the unit s). It states the BLI instrument and sensor, six concentrations from 20 uM to 0 uM (no list), a buffer-only
reference sensor, the 180 s association and 600 s dissociation phases, that all measurements were in triplicate,
a KD of 9.29 uM from a Scatchard plot (no spread), and a control without the protease that showed no binding. It
says nothing of kon, koff, the response, the loading, the fit quality, regeneration, or whether the triplicates
were independent sensors."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_extraction import (
    BIOSENSOR_TYPE, FIT_MODEL, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_record import UNITS

PAPER_ID = 'PMC13065029'
REAL = (
    'To determine the equilibrium dissociation constant (KD) for the interaction between '
    'pantinin-1 and CHIKV nsP2pro, biolayer interferometry (BLI) was used. The experiment was '
    'performed using an Octet RED96 system (Sartorius, Göttingen, Germany) equipped with AR2G '
    'biosensors. Pantinin-1 was tested at six different concentrations, ranging from 20 µM to 0'
    ' µM. A sensor exposed only to the running buffer during the assay served as the reference '
    '(0µM). All experiments were conducted at room temperature. The assay included an '
    'association phase of 180\u2009s followed by a dissociation phase of 600\u2009s. A representative '
    'sensorgram is shown in S4A Fig. All measurements were conducted in triplicate. From the '
    'BLI binding response data obtained across six concentrations of pantinin-1, a Scatchard '
    'plot was constructed using values extracted from ForteBio Data Analysis Software. This '
    'analysis resulted in a dissociation constant (KD) of 9.29 μM (S4B Fig). To confirm that '
    'the observed binding was specifically between the protease and pantinin-1, a control '
    'experiment was performed in the absence of the protease using 20 µM and 6.66 µM '
    'pantinin-1. As shown in S5 Fig, no binding was detected between the sensor and the '
    'peptide, indicating that the interaction occurs exclusively between the protease and '
    'pantinin-1.')

SYNTHETIC = (
    'Bio-layer interferometry was performed on an Octet RED96e at 25 °C. The assay measured the binding of the protein '
    'ParB to its partner PopZ. Streptavidin biosensors were loaded with '
    'biotinylated ParB for 120 s, to a loading level of 1.0 nm; the loading step was recorded for every sensor. The '
    'loaded sensors were dipped into PopZ at 2, 6, 20, 60, 200 and 600 nM for 300 s (association) and then into '
    'buffer for a dissociation step of 600 s. A reference sensor carrying no ParB was run with PopZ and its signal '
    'was subtracted, and a buffer-only reference of the loaded sensor was subtracted as well. The baseline was '
    'stable, with no significant drift. Non-specific binding of PopZ to blank streptavidin sensors was checked. The '
    'ParB on the sensor was active: it bound its known partner. The analyte PopZ is not bivalent or oligomeric under '
    'these conditions. Avidity and rebinding were considered, and a low loading level was used to avoid them; '
    'mass-transport limitation was also considered. The sensorgrams were globally fitted with a 1:1 model '
    '(R² = 0.99), which gave kon = 1.0 × 10^5 M^-1 s^-1 and koff = 2.0 × 10^-3 s^-1, giving KD = 20 nM (standard '
    'deviation 3 nM). The maximum response was 0.8 nm. A steady-state fit of the equilibrium responses gave '
    'KD = 30 nM, so both a kinetic and a steady-state estimate were made. The sensors were regenerated with 10 mM '
    'glycine pH 1.7 without loss of binding capacity. Three independent experiments were done on separate sensors.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'kd_steady_state': (30, 'nM', 'steady-state fit of the equilibrium responses gave KD = 30 nM'),
    'kon': (100000, 'M^-1 s^-1', 'kon = 1.0 × 10^5 M^-1 s^-1'),
    'koff': (0.002, 's^-1', 'koff = 2.0 × 10^-3 s^-1'),
    'response_max': (0.8, 'nm', 'The maximum response was 0.8 nm'),
    'kd_spread': (3, 'nM', 'standard deviation 3 nM'),
    'fit_r_squared': (0.99, 'dimensionless', 'R² = 0.99'),
    'loading_level': (1.0, 'nm', 'a loading level of 1.0 nm'),
    'dissociation_time': (600, 's', 'a dissociation step of 600 s'),
    'replicate_count': (3, 'count', 'Three independent experiments'),
    SERIES: ([2, 6, 20, 60, 200, 600], 'nM', 'PopZ at 2, 6, 20, 60, 200 and 600 nM'),
    SPREAD_KIND: ('standard_deviation', None, 'standard deviation 3 nM'),
    FIT_MODEL: ('1:1', None, 'globally fitted with a 1:1 model'),
    BIOSENSOR_TYPE: ('streptavidin', None, 'Streptavidin biosensors'),
    'reference_sensor_subtracted': ('yes', None, 'A reference sensor carrying no ParB was run with PopZ and its signal was subtracted'),
    'buffer_reference_subtracted': ('yes', None, 'a buffer-only reference of the loaded sensor was subtracted'),
    'baseline_stable': ('yes', None, 'The baseline was stable'),
    'loading_step_documented': ('yes', None, 'the loading step was recorded for every sensor'),
    'regeneration': ('yes', None, 'The sensors were regenerated with 10 mM glycine pH 1.7'),
    'independent_sensors': ('yes', None, 'Three independent experiments were done on separate sensors'),
    'immobilized_partner_active': ('yes', None, 'The ParB on the sensor was active'),
    'analyte_bivalent_or_oligomeric': ('no', None, 'PopZ is not bivalent or oligomeric'),
    'avidity_rebinding_considered': ('yes', None, 'Avidity and rebinding were considered'),
    'mass_transport_considered': ('yes', None, 'mass-transport limitation was also considered'),
    'nonspecific_binding_checked': ('yes', None, 'Non-specific binding of PopZ to blank streptavidin sensors was checked'),
    'single_estimate_method': ('no', None, 'both a kinetic and a steady-state estimate were made'),
}

# field -> (value, unit, quote) for the real passage: only what it states.
REAL_STATED = {
    'kd': (9.29, 'uM', 'KD) of 9.29 \u03bcM'),
    'dissociation_time': (600, 's', 'dissociation phase of 600\u2009s'),
    'replicate_count': (3, 'count', 'All measurements were conducted in triplicate'),
    'nonspecific_binding_checked': ('yes', None, 'a control experiment was performed in the absence of the protease'),
}
# What else a careful reader may also state from the real passage (a judgement the passage supports, not a number):
# the sensor chemistry, the reference sensor, and the model of the Scatchard analysis.
REAL_MAY_ALSO_STATE = {'biosensor_type', 'reference_sensor_subtracted', 'buffer_reference_subtracted', 'fit_model'}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'popz'
# The real paragraph is about the interaction between the peptide pantinin-1 and the protease CHIKV nsP2pro; it does not
# say which one is on the sensor, so which is the molecule assayed is ambiguous and no single target is expected.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('chikv nsp2pro',), ('pantinin-1',))     # symmetric pair named by the paragraph; either orientation accepted


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
