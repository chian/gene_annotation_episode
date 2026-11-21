"""The extracted record of ONE scintillation proximity assay (SPA) binding experiment (a radioligand binding to a target captured on scintillant-containing beads: saturation binding for KD and Bmax, competition (displacement) binding for IC50 and Ki, or a kinetic experiment).

What a leaf extraction holds for one SPA binding experiment: a radiolabelled ligand (the radioligand: usually a tritiated or iodine-125 ligand
of a known specific activity in Ci/mmol; SPA works best with weak beta emitters, whose particles travel only a short path) is incubated with a
target (a membrane preparation, a purified protein or whole cells) that is captured on beads containing a scintillant (yttrium silicate (YSi) or
polyvinyltoluene (PVT) beads; the target is held on the bead by wheat-germ agglutinin (WGA) for membrane glycoproteins, by streptavidin for a
biotinylated target, by a metal chelate (Ni, Cu or Co) for a His-tagged target, or by an antibody). Only a radioligand bound to the captured
target is within the range of the bead, so only it excites the scintillant and gives light; the free radioligand in the solution is too far
away. No separation and no wash is needed (a homogeneous, no-wash format), so the binding is measured at equilibrium in the presence of the free
radioligand, and the plate is counted on a microplate scintillation counter (MicroBeta, TopCount). Total binding is measured with the radioligand
alone, non-specific binding with the radioligand in the presence of a large excess of an unlabelled ligand (typically 100 to 1000 times its Kd)
that occupies the specific sites, and specific binding is the total binding minus the non-specific binding. In saturation binding the specific
binding against the concentration of the radioligand (typically 0.1 to 10 times its KD) is fitted to give the dissociation constant KD of the
radioligand and the number of binding sites Bmax; in competition binding an unlabelled ligand lowers the specific binding of one fixed
concentration of the radioligand (at or below its KD), and the curve gives a half-maximal inhibitory concentration IC50, from which the inhibition
constant Ki is calculated with the Cheng-Prusoff equation, Ki = IC50 / (1 + [radioligand] / KD), using the KD of that radioligand on that target.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS,
ELISA, AlphaScreen and radioligand records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs,
origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and
never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

An SPA experiment differs from a filtration radioligand experiment in what can go wrong, and the form keeps exactly those things: there is no
filter and no wash, so neither filter binding nor wash dissociation exists; but the radioligand can bind to the bead itself (and a free
radioligand at a high concentration still gives a small non-proximity signal), so a control without the captured target (beads and radioligand
only, an uncaptured or untagged target) and a check of the non-proximity signal are needed, besides the non-specific binding defined with an
excess of an unlabelled ligand (under 50 percent of the total binding at the highest concentration, or the specific signal is lost in the
difference of two large numbers); the free radioligand concentration is taken to be the added concentration, which holds only while the target
binds less than about 10 percent of the added radioligand (ligand depletion, the bound fraction); the incubation must be long enough for
equilibrium (shown by an association time course); the radioligand must be pure and not degraded; coloured or quenching compounds and the buffer
absorb the light and lower the counts (colour quench), which a counting-efficiency or quench correction handles; the beads settle, and the counts
rise with the settling time, so the time before reading must be fixed; a Hill slope far from 1 shows more than one site, cooperativity, or no
equilibrium; the Cheng-Prusoff equation holds only with the KD of the same radioligand on the same target and a competition that is competitive
for one site; and the replicates are of two kinds (wells of one experiment, and independent experiments).

Record fields
-------------
version, experiment_type ('spa'), experiment_ref, source_ref, assertion_ref
preparations   radioligand_preparation_ref (the radioligand, the labelled ligand), receptor_preparation_ref (the captured target: the membranes,
               the purified protein or the cells), dataset_ref: each a string or None (unknown). The converter hands them to the merger as its
               dependence keys (the radioligand as the analyte key, the captured target as the other partner; there is no surface).
quantities     kd, bmax, ki, ic50, hill_slope, kd_spread, ki_spread, specific_activity, radioligand_concentration, radioligand_range_lowest,
               radioligand_range_highest, bead_amount, bead_concentration, receptor_amount, percent_bound, nonspecific_fraction,
               nonspecific_ligand_concentration, nonspecific_ligand_affinity, nonspecific_excess, bead_only_fraction, counting_efficiency, incubation_time,
               association_half_time, settling_time,
               temperature, titration_point_count, technical_replicate_count, replicate_count: one operand each.
               Units: kd/ki/ic50/kd_spread/ki_spread, radioligand_concentration, radioligand_range_lowest, radioligand_range_highest and
               nonspecific_ligand_concentration, nonspecific_ligand_affinity pM, nM, uM or mM (kd is the dissociation constant of the radioligand from a saturation experiment;
               ki an inhibition constant the source gives; ic50 the half-maximal inhibitory concentration of a competition;
               radioligand_concentration the single concentration of the radioligand in a competition; radioligand_range_lowest and _highest the
               lowest and the highest radioligand concentration of a saturation series); bmax 'fmol/mg', 'pmol/mg', 'sites/cell' or 'nM';
               hill_slope 'ratio'; specific_activity 'Ci/mmol'; bead_amount 'ug' or 'mg' (beads per well); bead_concentration 'mg/mL';
               receptor_amount 'ug' or 'mg' (target protein per well); percent_bound, nonspecific_fraction, bead_only_fraction, counting_efficiency
               'percent' (percent_bound: the percent of the total added radioligand that was bound; nonspecific_fraction: the non-specific binding
               as a percent of the total binding at the highest radioligand concentration; bead_only_fraction: the signal of the control without
               the captured target as a percent of the total signal; counting_efficiency: the percent of the decays counted); nonspecific_excess
               'ratio' (the stated fold excess of the unlabelled ligand over the Kd of the radioligand that defines non-specific binding);
               nonspecific_ligand_affinity the KD or Ki of the unlabelled ligand that defines non-specific binding, which the excess is measured against
               (the radioligand's own KD only when that ligand is the unlabelled radioligand: fact nonspecific_ligand_is_radioligand);
               association_half_time the time to half of the plateau binding in a stated association time course (the converter judges the
               incubation in multiples of it); incubation_time, association_half_time and settling_time s, min or h; temperature C or K; titration_point_count, technical_replicate_count (wells per
               condition) and replicate_count (independent experiments) 'count'.
concentration_series
               operand whose 'value' is a list of radioligand concentrations of a saturation series (unit pM, nM, uM or mM), or None when not given.
assay_format   'saturation' (KD and Bmax) or 'competition' (IC50 and Ki) or 'kinetic' (association and dissociation time courses) or None.
radioligand_isotope
               'tritium' (3H), 'iodine_125' (125I), 'sulfur_35' (35S), 'other' or None.
bead_type      'ysi' (yttrium silicate), 'pvt' (polyvinyltoluene), 'other' or None: the kind of scintillant bead.
capture_method 'wga' (wheat-germ agglutinin), 'streptavidin_biotin', 'metal_chelate' (Ni, Cu or Co chelate holding a His-tagged target),
               'antibody', 'other' or None: how the target is held on the bead.
preparation_type
               'membrane', 'purified_protein', 'whole_cell', 'other' or None: the kind of captured target. Kept in the record for the reviewer;
               no criterion judges it.
counter        'microbeta', 'topcount', 'other' or None: the microplate scintillation counter. Kept in the record for the reviewer.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
fit_model      'one_site' (a one-site binding model), 'two_site', 'hill' (a model with a free Hill slope), 'competitive_binding' (a one-site
               competition model, for a competition curve), 'other' or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (assay_format, radioligand_isotope, bead_type, capture_method, preparation_type,
               counter, spread_kind, fit_model), None when the choice is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', the concentration series, a fact whose answer is stated, a choice field) carries
'support', the extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (the
quote states it only by implication), 'about_something_else' (the quote is on the topic but is really about another measurement or condition).
An unavailable operand and an 'unknown' fact carry support None. The grader keeps it and does not judge it; the converter does. Rule for the
constructors: they take ``support`` and default it to 'direct' only so that forms built by tests, which do not go through the extraction, are
direct; the extraction always passes the model's own value.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record

SUPPORTS = ('direct', 'implied', 'about_something_else')


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': support}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    return {**literature_spr_record.fact(answer, refs), 'support': None if answer == 'unknown' else support}


VERSION = 'a105_spa_record_v1'
EXPERIMENT_TYPE = 'spa'
QUANTITIES = ('kd', 'bmax', 'ki', 'ic50', 'hill_slope', 'kd_spread', 'ki_spread', 'specific_activity', 'radioligand_concentration', 'radioligand_range_lowest', 'radioligand_range_highest', 'bead_amount', 'bead_concentration', 'receptor_amount', 'percent_bound', 'nonspecific_fraction', 'nonspecific_ligand_concentration', 'nonspecific_ligand_affinity', 'nonspecific_excess', 'bead_only_fraction', 'counting_efficiency', 'incubation_time', 'association_half_time', 'settling_time', 'temperature', 'titration_point_count', 'technical_replicate_count', 'replicate_count')
PREPARATION_KEYS = ('radioligand_preparation_ref', 'receptor_preparation_ref', 'dataset_ref')
ASSAY_FORMATS = ('saturation', 'competition', 'kinetic')
ISOTOPES = ('tritium', 'iodine_125', 'sulfur_35', 'other')
BEAD_TYPES = ('ysi', 'pvt', 'other')
CAPTURE_METHODS = ('wga', 'streptavidin_biotin', 'metal_chelate', 'antibody', 'other')
PREPARATION_TYPES = ('membrane', 'purified_protein', 'whole_cell', 'other')
COUNTERS = ('microbeta', 'topcount', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('one_site', 'two_site', 'hill', 'competitive_binding', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'homogeneous_no_wash_format': YES_NO, 'nonspecific_binding_determined': YES_NO, 'nonspecific_ligand_is_radioligand': YES_NO, 'nonproximity_signal_checked': YES_NO, 'bead_only_control_done': YES_NO, 'equilibrium_reached': YES_NO, 'ligand_depletion_checked': YES_NO, 'quench_interference_checked': YES_NO, 'bead_settling_controlled': YES_NO, 'radioligand_purity_checked': YES_NO, 'nonlinear_fit_used': YES_NO, 'cheng_prusoff_applied_with_own_kd': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
TIME_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'bmax': ('fmol/mg', 'pmol/mg', 'sites/cell', 'nM'), 'ki': CONCENTRATION_UNITS, 'ic50': CONCENTRATION_UNITS, 'hill_slope': ('ratio',), 'kd_spread': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'specific_activity': ('Ci/mmol',), 'radioligand_concentration': CONCENTRATION_UNITS, 'radioligand_range_lowest': CONCENTRATION_UNITS, 'radioligand_range_highest': CONCENTRATION_UNITS, 'bead_amount': ('ug', 'mg'), 'bead_concentration': ('mg/mL',), 'receptor_amount': ('ug', 'mg'), 'percent_bound': ('percent',), 'nonspecific_fraction': ('percent',), 'nonspecific_ligand_concentration': CONCENTRATION_UNITS, 'nonspecific_ligand_affinity': CONCENTRATION_UNITS, 'nonspecific_excess': ('ratio',), 'bead_only_fraction': ('percent',), 'counting_efficiency': ('percent',), 'incubation_time': TIME_UNITS, 'association_half_time': TIME_UNITS, 'settling_time': TIME_UNITS, 'temperature': ('C', 'K'), 'titration_point_count': ('count',), 'technical_replicate_count': ('count',), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
