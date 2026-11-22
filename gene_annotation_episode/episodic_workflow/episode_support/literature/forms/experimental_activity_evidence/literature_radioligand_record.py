"""The extracted record of ONE radioligand binding experiment (a radiolabelled ligand binding to a receptor or protein: saturation binding for KD and Bmax, competition (displacement) binding for IC50 and Ki, or a kinetic experiment).

What a leaf extraction holds for one radioligand binding experiment: a radiolabelled ligand (the radioligand: a tritiated, iodine-125,
sulfur-35 or phosphorus-32 labelled ligand of a known specific activity in Ci/mmol) is incubated with a receptor or protein
preparation (a membrane preparation, a purified protein or whole cells), the bound radioligand is separated from the free
radioligand (by rapid filtration through glass-fibre filters, usually GF/B or GF/C filters pre-soaked in polyethylenimine (PEI) to lower
the binding of the radioligand to the filter, followed by a wash; or by scintillation proximity assay (SPA) beads that need no
separation; or by centrifugation) and counted. Total binding is measured with the radioligand alone, non-specific binding with the
radioligand in the presence of a large excess of an unlabelled ligand (typically 100 to 1000 times its Kd) that occupies the specific
sites, and specific binding is the total binding minus the non-specific binding. In saturation binding the specific binding against
the concentration of the radioligand (typically 0.1 to 10 times its KD) is fitted to give the dissociation constant KD of the
radioligand and the number of binding sites Bmax; in competition binding an unlabelled ligand lowers the specific binding of one fixed
concentration of the radioligand (at or below its KD), and the curve gives a half-maximal inhibitory concentration IC50, from which the
inhibition constant Ki is calculated with the Cheng-Prusoff equation, Ki = IC50 / (1 + [radioligand] / KD), using the KD of that
radioligand on that preparation. One experiment, or replicate experiments reported as one result, in the same operand shape as the
SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA and AlphaScreen records and the existing A105 assay grading inputs (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status
'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the
SPR record module's; they are shared because they only build operands.

A radioligand experiment differs from the other methods in what can go wrong: the free radioligand concentration is taken to be the
added concentration, which holds only while the receptor binds less than about 10 percent of the added radioligand (ligand
depletion, the bound fraction); the non-specific binding must be a small part of the total binding at the highest concentration
(under 50 percent, or the specific signal is lost in the difference of two large numbers) and is defined with an excess of an
unlabelled ligand high enough to occupy the specific sites; the incubation must be long enough for equilibrium (shown by an
association time course), longer for a high-affinity radioligand and for a low temperature; the radioligand itself must be pure
and not degraded (radiolysis); the radioligand can stick to the filter, and a wash can dissociate a radioligand with a fast
off-rate from the receptor; a Scatchard (linearised) plot distorts the error and a non-linear fit is preferred; the Cheng-Prusoff
equation holds only with the KD of the same radioligand on the same preparation and a competition that is competitive for one
site; a Hill slope far from 1 shows more than one site, cooperativity, or no equilibrium, and the one-site constant is then not
valid; and the replicates are of two kinds (wells of one experiment, and independent experiments). The form keeps exactly those
things.

Record fields
-------------
version, experiment_type ('radioligand'), experiment_ref, source_ref, assertion_ref
preparations   radioligand_preparation_ref (the radioligand, the labelled ligand), receptor_preparation_ref (the receptor or protein
               preparation: the membranes, the purified protein or the cells), dataset_ref: each a string or None (unknown). The
               converter hands them to the merger as its dependence keys (the radioligand as the analyte key, the receptor
               preparation as the other partner; there is no surface).
quantities     kd, bmax, ki, ic50, hill_slope, kd_spread, ki_spread, specific_activity, radioligand_concentration,
               radioligand_range_lowest, radioligand_range_highest, receptor_amount, percent_bound, nonspecific_fraction,
               nonspecific_ligand_concentration, nonspecific_ligand_kd, nonspecific_excess, incubation_time, dissociation_rate, temperature,
               titration_point_count, technical_replicate_count, replicate_count: one operand each.
               Units: kd/ki/ic50/kd_spread/ki_spread, radioligand_concentration, radioligand_range_lowest,
               radioligand_range_highest, nonspecific_ligand_concentration and nonspecific_ligand_kd pM, nM, uM or mM (kd is the dissociation constant of the
               radioligand from a saturation experiment; ki an inhibition constant the source gives; ic50 the half-maximal inhibitory
               concentration of a competition; radioligand_concentration the single concentration of the radioligand in a competition;
               radioligand_range_lowest and _highest the lowest and the highest radioligand concentration of a saturation series;
               nonspecific_ligand_kd the Kd (or Ki) of the unlabelled ligand that defines non-specific binding, of that ligand itself);
               bmax 'fmol/mg', 'pmol/mg', 'sites/cell' or 'nM' (the number of binding sites); hill_slope 'ratio';
               specific_activity 'Ci/mmol'; receptor_amount 'ug' or 'mg' (receptor protein per assay tube or well);
               percent_bound, nonspecific_fraction 'percent' (percent_bound: the percent of the total added radioligand that was bound;
               nonspecific_fraction: the non-specific binding as a percent of the total binding at the highest radioligand
               concentration); nonspecific_excess 'ratio' (the stated fold excess of the unlabelled ligand that defines non-specific binding
               over its own Kd); incubation_time s, min or h; dissociation_rate '1/s', '1/min' or '1/h' (the off-rate koff of the radioligand
               from the receptor preparation); temperature C or K; titration_point_count,
               technical_replicate_count (wells or tubes per condition) and replicate_count (independent experiments) 'count'.
concentration_series
               operand whose 'value' is a list of radioligand concentrations of a saturation series (unit pM, nM, uM or mM), or None
               when not given.
assay_format   'saturation' (KD and Bmax) or 'competition' (IC50 and Ki) or 'kinetic' (association and dissociation time courses) or None.
radioligand_isotope
               'tritium' (3H), 'iodine_125' (125I), 'sulfur_35' (35S), 'phosphorus_32' (32P), 'other' or None.
separation_method
               'filtration', 'scintillation_proximity', 'centrifugation', 'other' or None: how bound radioligand was separated from free.
preparation_type
               'membrane', 'purified_protein', 'whole_cell', 'other' or None: the kind of receptor preparation. Kept in the record for the
               reviewer; no criterion judges it.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
fit_model      'one_site' (a one-site binding model), 'two_site', 'hill' (a model with a free Hill slope), 'competitive_binding' (a
               one-site competition model, for a competition curve), 'other' or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
               binding_detected is the experiment's stated yes/no result (the passage says the two partners bound, or says
               they did not); no criterion reads it. It lets a result stated without a constant count (owner, 2026-11-22).
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

VERSION = 'a105_radioligand_record_v1'
EXPERIMENT_TYPE = 'radioligand'
QUANTITIES = ('kd', 'bmax', 'ki', 'ic50', 'hill_slope', 'kd_spread', 'ki_spread', 'specific_activity', 'radioligand_concentration', 'radioligand_range_lowest', 'radioligand_range_highest', 'receptor_amount', 'percent_bound', 'nonspecific_fraction', 'nonspecific_ligand_concentration', 'nonspecific_ligand_kd', 'nonspecific_excess', 'incubation_time', 'dissociation_rate', 'temperature', 'titration_point_count', 'technical_replicate_count', 'replicate_count')
PREPARATION_KEYS = ('radioligand_preparation_ref', 'receptor_preparation_ref', 'dataset_ref')
CHOICE_FIELDS = ('assay_format', 'radioligand_isotope', 'separation_method', 'preparation_type', 'spread_kind', 'fit_model')
ASSAY_FORMATS = ('saturation', 'competition', 'kinetic')
ISOTOPES = ('tritium', 'iodine_125', 'sulfur_35', 'phosphorus_32', 'other')
SEPARATION_METHODS = ('filtration', 'scintillation_proximity', 'centrifugation', 'other')
PREPARATION_TYPES = ('membrane', 'purified_protein', 'whole_cell', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('one_site', 'two_site', 'hill', 'competitive_binding', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'ligand_depletion_checked': YES_NO, 'nonspecific_binding_determined': YES_NO, 'equilibrium_reached': YES_NO, 'radioligand_purity_checked': YES_NO, 'filter_binding_checked': YES_NO, 'wash_dissociation_considered': YES_NO, 'nonlinear_fit_used': YES_NO, 'cheng_prusoff_applied_with_own_kd': YES_NO, 'depletion_corrected': YES_NO, 'nonspecific_ligand_is_unlabelled_radioligand': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO, 'binding_detected': YES_NO}


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
UNITS = {'kd': CONCENTRATION_UNITS, 'bmax': ('fmol/mg', 'pmol/mg', 'sites/cell', 'nM'), 'ki': CONCENTRATION_UNITS, 'ic50': CONCENTRATION_UNITS, 'hill_slope': ('ratio',), 'kd_spread': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'specific_activity': ('Ci/mmol',), 'radioligand_concentration': CONCENTRATION_UNITS, 'radioligand_range_lowest': CONCENTRATION_UNITS, 'radioligand_range_highest': CONCENTRATION_UNITS, 'receptor_amount': ('ug', 'mg'), 'percent_bound': ('percent',), 'nonspecific_fraction': ('percent',), 'nonspecific_ligand_concentration': CONCENTRATION_UNITS, 'nonspecific_ligand_kd': CONCENTRATION_UNITS, 'nonspecific_excess': ('ratio',), 'incubation_time': ('s', 'min', 'h'), 'dissociation_rate': ('1/s', '1/min', '1/h'), 'temperature': ('C', 'K'), 'titration_point_count': ('count',), 'technical_replicate_count': ('count',), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
