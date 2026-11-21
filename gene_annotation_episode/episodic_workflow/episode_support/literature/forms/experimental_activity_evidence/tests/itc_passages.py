"""Chunks of text for the ITC extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the ITC form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (micro sign, degree sign,
Delta) so byte offsets differ from character offsets.

``HSP90_HOP`` is real: the legend of Figure 1 (parts a and b) of the Hsp90/Hop paper, 'Molecular basis of the
interaction of Hsp90 with its co-chaperone Hop', Protein Science 29(11), 2020, doi 10.1002/pro.3969, PMC7679967 (open
access, CC BY-NC-ND). The text is the legend as the publisher's XML gives it (italics removed; the subscript of KD
written inline; the thin spaces (U+2009) and the hyphen U+2010 before TdS kept as published). It states the ITC KD with its error, the
fitted stoichiometry n, that the model was a single binding site, that the errors are standard deviations of three
independent experiments, and the signs of the enthalpy and entropy terms (no values)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_extraction import (
    FIT_MODEL, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_record import UNITS

PAPER_ID = 'PMC7679967'
HSP90_HOP = (
    '(a) Isothermal titration calorimetry (ITC) affinity measurement fitted to a single binding site model '
    '(KD =\u20090.578\u2009±\u20090.073\u2009μM). The stoichiometry of n =\u20090.544\u2009±\u20090.052 indicates an Hsp90 dimer bound by only one Hop '
    'molecule. (b) The interaction of Hsp90 and Hop is characterized by negative ΔH and positive ‐TΔS. Errors '
    'represent the SD out of three independent experiments.')

SYNTHETIC = (
    'Isothermal titration calorimetry was performed on a MicroCal PEAQ-ITC at 25 °C, with the temperature held '
    'constant by the instrument. The assay measured the binding of the protein ParB to its partner PopZ. The cell contained 10 µM ParB and the syringe 100 µM PopZ; both proteins were '
    'dialysed together against the same buffer. Their concentrations were determined by absorbance at 280 nm, and the '
    'active fraction of each protein was determined by a binding-activity assay. A single titration consisted of 20 '
    'injections. Control titrations of PopZ into buffer measured the heat of dilution, and this heat was subtracted '
    'from the binding heats; the baseline of each thermogram was corrected before integration. The isotherm was '
    'fitted with a one-set-of-sites model, in which n was a free fitting parameter, and the binding sites were not '
    'heterogeneous; residuals of the fit are shown in Figure 2B. The fit gave n = 1.0 (1:1 expected from the crystal '
    'structure), KD = 20 nM (standard deviation 3 nM), ΔH = -50 kJ/mol and ΔS = -20.3 J/mol/K. Three independent '
    'titrations were done on separate protein preparations.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'kd_spread': (3, 'nM', 'standard deviation 3 nM'),
    'stoichiometry': (1.0, 'dimensionless', 'n = 1.0'),
    'expected_stoichiometry': (1.0, 'dimensionless', '1:1 expected from the crystal structure'),
    'enthalpy': (-50, 'kJ/mol', 'ΔH = -50 kJ/mol'),
    'entropy': (-20.3, 'J/mol/K', 'ΔS = -20.3 J/mol/K'),
    'temperature': (25, 'C', 'at 25 °C'),
    'cell_concentration': (10, 'uM', 'The cell contained 10 µM ParB'),
    'syringe_concentration': (100, 'uM', 'the syringe 100 µM PopZ'),
    'injection_count': (20, 'count', 'consisted of 20 injections'),
    'replicate_count': (3, 'count', 'Three independent titrations'),
    SPREAD_KIND: ('standard_deviation', None, 'standard deviation 3 nM'),
    FIT_MODEL: ('one_set_of_sites', None, 'a one-set-of-sites model'),
    'dilution_control_performed': ('yes', None, 'Control titrations of PopZ into buffer measured the heat of dilution'),
    'dilution_control_subtracted': ('yes', None, 'this heat was subtracted from the binding heats'),
    'baseline_corrected': ('yes', None, 'the baseline of each thermogram was corrected'),
    'concentrations_determined': ('yes', None, 'Their concentrations were determined by absorbance at 280 nm'),
    'active_fraction_determined': ('yes', None, 'the active fraction of each protein was determined'),
    'binding_sites_heterogeneous': ('no', None, 'the binding sites were not heterogeneous'),
    'residuals_reported': ('yes', None, 'residuals of the fit are shown in Figure 2B'),
    'n_fitted_freely': ('yes', None, 'n was a free fitting parameter'),
    'buffer_matching': ('dialysed_together', None, 'dialysed together against the same buffer'),
    'temperature_controlled': ('yes', None, 'with the temperature held constant by the instrument'),
    'independent_titrations': ('yes', None, 'Three independent titrations were done on separate protein preparations'),
}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'parb'
SYNTHETIC_PARTNER = 'popz'
# The real paragraph names Hsp90 and its co-chaperone Hop as two interacting proteins; which of the two is the molecule
# assayed is genuinely ambiguous, so no single target is expected.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None
REAL_EXPECTED_PAIR = (('hsp90',), ('hop',))     # symmetric pair named by the paragraph; either orientation accepted

# field -> (value, unit, quote) for the real passage: only what it states.
HSP90_HOP_STATED = {
    'kd': (0.578, 'uM', 'KD =\u20090.578\u2009±\u20090.073\u2009μM'),
    'kd_spread': (0.073, 'uM', '±\u20090.073\u2009μM'),
    'stoichiometry': (0.544, 'dimensionless', 'n =\u20090.544\u2009±\u20090.052'),
    'replicate_count': (3, 'count', 'three independent experiments'),
    SPREAD_KIND: ('standard_deviation', None, 'Errors represent the SD'),
    FIT_MODEL: ('one_set_of_sites', None, 'a single binding site model'),
    'independent_titrations': ('yes', None, 'three independent experiments'),
}


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


def hsp90_hop_answer():
    return answer_from(HSP90_HOP, HSP90_HOP_STATED)
