"""The extracted record of ONE ELISA-style binding experiment (plate-based solid-phase binding: direct, indirect or sandwich ELISA, or a competition ELISA).

What a leaf extraction holds for one ELISA-style solid-phase binding experiment: one partner (the coated protein) is
adsorbed or captured on the wells of a microtitre plate, the wells are blocked, the other partner (the titrant, the ligand)
is added in a dilution series and left to bind for a set time, the unbound material is removed by washing, and what stays on
the plate is detected with an enzyme-linked reagent (a horseradish peroxidase or alkaline phosphatase conjugate of an antibody
against the ligand, against a tag, or of the ligand itself) and a colorimetric (absorbance, OD) or chemiluminescent readout.
The binding curve (the signal against the titrant concentration) is fitted to give an apparent dissociation constant KD or a
half-maximal effective concentration EC50; in the competition format a constant concentration of the labelled or tagged ligand
competes with a series of an unlabelled competitor, and the curve gives a half-maximal inhibitory concentration IC50, from which
a Ki can be calculated. One experiment, or replicate titrations reported as one result, in the same operand shape as the SPR,
ITC, BLI, GCI, FP, FRET, MST, Trp and FCS records and the existing A105 assay grading inputs (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status
'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact
are the SPR record module's; they are shared because they only build operands.

ELISA differs from the other methods in what is measured and what can go wrong: it is a heterogeneous assay with wash steps, so
what stays on the plate is read after the unbound ligand was washed away and the number is an apparent KD (or an EC50), not an
equilibrium KD in solution, because a complex that dissociates during the washes is lost from the signal; the half-maximal
concentration of a curve (EC50, IC50) is not a dissociation constant and depends on the coating and on the detection; a
multivalent coating or a multivalent ligand (dimers, antibodies, oligomers) binds with avidity and gives an apparent KD far
below the monovalent one; the coated protein can lose activity or be oriented badly on the plastic; the detection reagent can
compete with the binding or bind the coating; the absorbance of a plate reader is linear only up to about two optical density
units and a curve read above it flattens; wells without the coated protein and wells without the ligand give the background that
is subtracted, and a non-binding protein (an irrelevant protein, an uncoated well or a mutant) shows the specificity; the binding
step must be long enough to reach the plateau before the wash; and the replicates are of two kinds (technical wells of one plate,
and independent experiments on separate plates and dilutions). The form keeps exactly those things.

Record fields
-------------
version, experiment_type ('elisa'), experiment_ref, source_ref, assertion_ref
preparations   titrant_preparation_ref (the partner added in a series, or in competition the unlabelled competitor),
               fixed_partner_preparation_ref (the coated partner), dataset_ref: each a string or None (unknown). The converter
               hands them to the merger as its dependence keys (titrant as the analyte key, the coated partner as the other
               partner; the plate is not a surface reference).
quantities     kd, ki, ec50, ic50, kd_spread, ki_spread, coating_concentration, signal_maximum, signal_background,
               wash_count, titration_point_count, technical_replicate_count, incubation_time, temperature, replicate_count: one
               operand each.
               Units: kd/ki/ec50/ic50/kd_spread/ki_spread pM, nM, uM or mM (kd is the apparent dissociation constant the source
               calls a KD; ec50 the half-maximal effective concentration of a binding curve; ic50 the half-maximal inhibitory
               concentration of a competition; ki an inhibition constant the source gives); coating_concentration 'ug/mL' or 'ng/mL'
               (the concentration of the coating solution); signal_maximum and signal_background 'OD' (the absorbance of the
               plateau of the curve, and of the background: the blank, no-coat or no-ligand wells); wash_count, titration_point_count,
               technical_replicate_count (wells per concentration) and replicate_count (independent experiments) 'count';
               incubation_time s, min or h (the binding step of the ligand on the plate, before the wash); temperature C or K.
concentration_series
               operand whose 'value' is a list of titrant concentrations (unit pM, nM, uM or mM), or None when not given. In the
               competition format it is the competitor series.
assay_format   'saturation_titration' (the coated partner is titrated with the ligand; KD or EC50) or 'competition' (an unlabelled
               competitor displaces the ligand; IC50 or Ki) or None.
detection_format
               'direct' (the enzyme is on the ligand itself), 'indirect' (the enzyme is on a secondary antibody against the bound
               ligand or its tag) or 'sandwich' (the ligand is held by a capture antibody and detected by a second reagent), or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
fit_model      '1:1' (a one-site binding model), 'hill', 'four_parameter_logistic', 'competitive_binding', 'other' or None.
readout_signal 'absorbance' (a colorimetric substrate), 'chemiluminescence', 'fluorescence' (a fluorogenic substrate) or None.
enzyme_conjugate
               'horseradish_peroxidase', 'alkaline_phosphatase', 'other' or None. The enzyme of the detection reagent, kept in
               the record for the reviewer; no criterion judges it.
blocking_agent 'bsa', 'milk', 'casein', 'serum', 'other' or None. The protein used to block the plate, kept in the record for
               the reviewer; no criterion judges it.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.
choice_support name -> 'direct', 'implied', 'about_something_else' or None, for each choice field (CHOICE_FIELDS): how well the quote of that
               stated choice supports it; None when the choice is not stated.

Support (how well a stated field's quote supports it)
-----------------------------------------------------
Every stated field carries a fixed-vocabulary fact 'support' (SUPPORTS: 'direct', 'implied', 'about_something_else'): in a quantity operand
(and in the concentration series) and in a fact entry, as a 'support' key beside source_refs; for a choice field in choice_support. An
unavailable operand, an 'unknown' fact and a choice that is not stated carry None. The extraction always sets it from the model's answer.
The constructors ``point`` and ``fact`` below default it to 'direct' ONLY so that tests that build a record by hand (not through the
extraction) need not name it; ``unavailable`` and an 'unknown' fact are always None. The grader keeps the support and does not judge it;
the converter (the sheet side) turns it into a degree.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS

VERSION = 'a105_elisa_record_v1'
EXPERIMENT_TYPE = 'elisa'
QUANTITIES = ('kd', 'ki', 'ec50', 'ic50', 'kd_spread', 'ki_spread', 'coating_concentration', 'signal_maximum', 'signal_background', 'wash_count', 'titration_point_count', 'technical_replicate_count', 'incubation_time', 'temperature', 'replicate_count')
PREPARATION_KEYS = ('titrant_preparation_ref', 'fixed_partner_preparation_ref', 'dataset_ref')
CHOICE_FIELDS = ('assay_format', 'detection_format', 'spread_kind', 'fit_model', 'readout_signal', 'enzyme_conjugate', 'blocking_agent')
ASSAY_FORMATS = ('saturation_titration', 'competition')
DETECTION_FORMATS = ('direct', 'indirect', 'sandwich')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', 'hill', 'four_parameter_logistic', 'competitive_binding', 'other')
READOUT_SIGNALS = ('absorbance', 'chemiluminescence', 'fluorescence')
ENZYME_CONJUGATES = ('horseradish_peroxidase', 'alkaline_phosphatase', 'other')
BLOCKING_AGENTS = ('bsa', 'milk', 'casein', 'serum', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'blank_subtracted': YES_NO, 'nonspecific_binding_checked': YES_NO, 'saturation_reached': YES_NO, 'signal_in_linear_range': YES_NO, 'wash_dissociation_considered': YES_NO, 'equilibrium_reached': YES_NO, 'avidity_excluded': YES_NO, 'coated_protein_active': YES_NO, 'detection_does_not_interfere': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO}


def _checked(support):
    if support not in SUPPORTS:
        raise ValueError('support must be one of ' + ', '.join(SUPPORTS) + ': ' + repr(support))
    return support


def point(value, unit, key, refs, native_component=None, support='direct'):
    """A stated operand with its support (default 'direct': see the module docstring)."""
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': _checked(support)}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    """A fact entry: a stated answer carries its support (default 'direct'); 'unknown' carries None (and no support may be given for it)."""
    if answer == 'unknown':
        if support not in ('direct', None):
            raise ValueError('an unknown fact carries no support')
        return {**literature_spr_record.fact(answer, refs), 'support': None}
    return {**literature_spr_record.fact(answer, refs), 'support': _checked(support)}


CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'ki': CONCENTRATION_UNITS, 'ec50': CONCENTRATION_UNITS, 'ic50': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'coating_concentration': ('ng/mL', 'ug/mL'), 'signal_maximum': ('OD',), 'signal_background': ('OD',), 'wash_count': ('count',), 'titration_point_count': ('count',), 'technical_replicate_count': ('count',), 'incubation_time': ('s', 'min', 'h'), 'temperature': ('C', 'K'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
