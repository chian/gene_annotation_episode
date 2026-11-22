"""The extracted record of ONE AlphaScreen / AlphaLISA binding experiment (bead-based amplified luminescent proximity binding assay: direct titration, cross-titration or competition).

What a leaf extraction holds for one AlphaScreen or AlphaLISA binding experiment: one partner is captured on donor beads (usually
a biotinylated partner on streptavidin donor beads) and the other on acceptor beads (usually a His-, GST- or Fc-tagged partner on
nickel-chelate, glutathione, anti-tag or protein A acceptor beads); the interaction of the partners brings a donor and an acceptor
bead within about 200 nm, the donor beads are excited at 680 nm and release singlet oxygen, which reaches an acceptor bead only when
it is that close, and the acceptor bead emits light at 520-620 nm (AlphaScreen) or at 615 nm (AlphaLISA). The signal (counts per
second, cps) is read from a white microplate in a plate reader. The signal against the concentration of a partner is fitted to give
a dissociation constant KD or a half-maximal effective concentration EC50 (a direct titration or a cross-titration of both partners);
in the competition format an unlabelled competitor lowers the signal of a fixed pair and the curve gives a half-maximal inhibitory
concentration IC50, from which a Ki can be calculated. One experiment, or replicate titrations reported as one result, in the same
operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS and ELISA records and the existing A105 assay grading inputs (value,
unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact
are the SPR record module's; they are shared because they only build operands.

AlphaScreen differs from the other methods in what is measured and what can go wrong: the signal is amplified (one donor bead makes
many singlet oxygen molecules) and the partners are presented on beads that carry many copies of the capture molecule, so the number
is an apparent constant of bead-presented complexes (avidity) and not a monovalent solution constant; the signal falls at a high
concentration of a partner because the free partner saturates the capture sites of its beads, so that donor and acceptor beads no
longer bind the same complex (the hook effect: a bell-shaped curve), and a binding constant must be fitted to the rising part or with
a bell-shaped model, and the hook point is found with a cross-titration of both partners; a partner held at a concentration well
above the KD depletes the titrated partner and makes the EC50 or IC50 report the partner concentration instead of the affinity; the
signal is lost by colour quenchers (compounds that absorb at 520-680 nm), singlet oxygen quenchers, biotin mimetics, metal chelators
and by light (the donor beads are light sensitive, so ambient light and 680 nm exposure must be avoided), and a counter-screen with a
biotinylated His-tagged control linker (or a TruHits control) tells signal interference from a loss of binding; the signal window is
read as signal over background and the quality of the assay as the Z' factor; the reader must be inside its linear range; a tag or the
bead capture can change the binding; the binding step must be long enough to reach equilibrium; and the replicates are of two kinds
(technical wells of one plate, and independent experiments on separate plates and dilutions). The form keeps exactly those things.

Record fields
-------------
version, experiment_type ('alphascreen'), experiment_ref, source_ref, assertion_ref
preparations   titrant_preparation_ref (the partner added in a series, or in competition the unlabelled competitor),
               fixed_partner_preparation_ref (the partner held at a constant concentration), dataset_ref: each a string or None
               (unknown). The converter hands them to the merger as its dependence keys (titrant as the analyte key, the fixed
               partner as the other partner; the plate is not a surface reference).
quantities     kd, ki, ec50, ic50, kd_spread, ki_spread, signal_maximum, signal_background, signal_to_background, z_prime,
               bead_concentration, labelled_partner_concentration, tagged_partner_concentration, plate_well_count,
               titration_point_count, technical_replicate_count, incubation_time, bead_incubation_time, temperature,
               replicate_count: one operand each.
               Units: kd/ki/ec50/ic50/kd_spread/ki_spread and the two partner concentrations pM, nM, uM or mM (kd is the apparent
               dissociation constant the source calls a KD; ec50 the half-maximal effective concentration of a binding curve; ic50
               the half-maximal inhibitory concentration of a competition; ki an inhibition constant the source gives);
               signal_maximum and signal_background 'cps' (counts per second: the signal at the top of the curve and of the
               background wells); signal_to_background and z_prime 'ratio' (dimensionless numbers the source reports);
               bead_concentration 'ug/mL' or 'mg/mL' (the final concentration of each bead species in the well);
               plate_well_count, titration_point_count, technical_replicate_count (wells per concentration) and replicate_count
               (independent experiments) 'count'; incubation_time and bead_incubation_time s, min or h (incubation_time is the
               binding step of the partners before the beads are added; bead_incubation_time is the step after the beads were
               added); temperature C or K.
concentration_series
               operand whose 'value' is a list of titrant concentrations (unit pM, nM, uM or mM), or None when not given. In the
               competition format it is the competitor series; in a cross-titration it is the series of the partner that is
               analysed.
assay_format   'saturation_titration' (a partner is titrated; KD or EC50) or 'competition' (an unlabelled competitor lowers the
               signal; IC50 or Ki) or None.
titration_design
               'cross_titration' (both partners titrated against each other in a matrix) or 'fixed_partner_titration' (one partner
               held at a constant concentration and the other titrated) or None.
donor_bead, acceptor_bead
               'streptavidin', 'nickel_chelate', 'anti_tag_antibody', 'protein_a', 'glutathione' or 'other': the capture coating
               of the donor beads and of the acceptor beads, or None. Kept in the record for the reviewer; no criterion judges them.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
fit_model      'one_site' (a one-site binding model), 'quadratic' (a quadratic model that accounts for the depletion of the
               titrated partner), 'four_parameter_logistic', 'bell_shaped_hook' (a model of the curve that falls at a high
               concentration), 'competitive_binding', 'other' or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only. binding_detected is the experiment's stated
               yes/no result (the passage says the two partners bound, or says
               they did not); no criterion reads it. It lets a result that is
               stated without a constant count (owner, 2026-11-22).
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

VERSION = 'a105_alphascreen_record_v1'
EXPERIMENT_TYPE = 'alphascreen'
QUANTITIES = ('kd', 'ki', 'ec50', 'ic50', 'kd_spread', 'ki_spread', 'signal_maximum', 'signal_background', 'signal_to_background', 'z_prime', 'bead_concentration', 'labelled_partner_concentration', 'tagged_partner_concentration', 'plate_well_count', 'titration_point_count', 'technical_replicate_count', 'incubation_time', 'bead_incubation_time', 'temperature', 'replicate_count')
PREPARATION_KEYS = ('titrant_preparation_ref', 'fixed_partner_preparation_ref', 'dataset_ref')
CHOICE_FIELDS = ('assay_format', 'titration_design', 'donor_bead', 'acceptor_bead', 'spread_kind', 'fit_model')
ASSAY_FORMATS = ('saturation_titration', 'competition')
TITRATION_DESIGNS = ('cross_titration', 'fixed_partner_titration')
BEAD_COATINGS = ('streptavidin', 'nickel_chelate', 'anti_tag_antibody', 'protein_a', 'glutathione', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('one_site', 'quadratic', 'four_parameter_logistic', 'bell_shaped_hook', 'competitive_binding', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'counter_screen_done': YES_NO, 'hook_effect_handled': YES_NO, 'partner_concentration_below_kd': YES_NO, 'signal_in_linear_range': YES_NO, 'equilibrium_reached': YES_NO, 'nonspecific_binding_checked': YES_NO, 'capture_does_not_alter_binding': YES_NO, 'light_protected': YES_NO, 'avidity_excluded': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO, 'binding_detected': YES_NO}


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
UNITS = {'kd': CONCENTRATION_UNITS, 'ki': CONCENTRATION_UNITS, 'ec50': CONCENTRATION_UNITS, 'ic50': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'signal_maximum': ('cps',), 'signal_background': ('cps',), 'signal_to_background': ('ratio',), 'z_prime': ('ratio',), 'bead_concentration': ('ug/mL', 'mg/mL'), 'labelled_partner_concentration': CONCENTRATION_UNITS, 'tagged_partner_concentration': CONCENTRATION_UNITS, 'plate_well_count': ('count',), 'titration_point_count': ('count',), 'technical_replicate_count': ('count',), 'incubation_time': ('s', 'min', 'h'), 'bead_incubation_time': ('s', 'min', 'h'), 'temperature': ('C', 'K'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
