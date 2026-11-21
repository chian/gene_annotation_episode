"""The extracted record of ONE equilibrium dialysis or ultrafiltration binding experiment: a ligand (a small molecule, a peptide, a metal ion or another protein) and a protein are separated from each other's bound form by a semipermeable membrane or a centrifugal force, and the free and the total concentration of the ligand are measured. Equilibrium dialysis (a dialysis cell, cup or cassette, the RED rapid equilibrium dialysis device, a Dianorm cell), ultrafiltration (a centrifugal filter that presses the free ligand through a membrane) and ultracentrifugation (the protein and what is bound to it sediment, the free ligand stays) belong to it. The result is a fraction bound or a percent unbound at one or more stated concentrations (the usual result of a plasma protein binding experiment), or, when a series of ligand concentrations is measured, a dissociation constant KD and a number of binding sites Bmax from a saturation (a Scatchard, a double-reciprocal or a non-linear fit), or, when the protein is held with a labelled ligand and an unlabelled competitor is added, an inhibition constant Ki.

What a leaf extraction holds for one such experiment: the protein is put on one side of a membrane that it cannot cross (a molecular weight cutoff, in kDa, well below the mass of the protein and well above the mass of the ligand) in a buffer (pH, salt), the ligand is added on the other side (or on both), and the cell is kept at a temperature, shaken, for a time until the free ligand has the same concentration on both sides. The free ligand concentration is the concentration on the side without protein; the total ligand concentration on the side with protein is the free plus the bound; the bound is the difference. The fraction bound is bound over total (or the percent unbound is free over total, the fraction unbound), the concentration of the bound ligand against the free gives the saturation curve, and the free and the bound at several total concentrations give KD and Bmax. Both sides are measured by radioactivity (liquid scintillation counting), LC-MS/MS, fluorescence or absorbance. A control without protein (buffer only) shows that the ligand crosses the membrane and equalises; the recovery of the ligand from both chambers (a mass balance) and the binding of the ligand to the membrane and the device show losses.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA and SEC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What this method shows and what can go wrong is what the form keeps. The binding must be at equilibrium: the time to equilibrium is long for a large protein, a tight binder and a low temperature, and a fixed time (4 to 6 hours is usual for a plasma protein binding assay) is checked with a time course (the free concentration on the two sides against time). Ultrafiltration is not truly an equilibrium method: the free ligand is pressed out of a solution that is being depleted of it, and a small filtrate fraction is needed. The ligand can stick to the membrane and the device (nonspecific binding to the membrane inflates the apparent binding), and the recovery of the ligand from both chambers must be near complete (a mass balance, at least 80 percent). The protein is charged, so the Donnan effect and the osmotic flow move water and salt across the membrane and shift the volumes, and the free concentration is not the concentration in the dialysate unless this is corrected or the salt is high. The ligand must be stable over the incubation (no degradation) and the free ligand must be measured directly, not inferred from the total. The protein must not leak through the membrane, and the buffer-only control must show equal concentrations in both chambers. The protein concentration decides what fraction is bound: with a protein concentration far below the KD almost nothing is bound and the fraction cannot be measured, and a bound ligand concentration that exceeds the protein concentration means the sites are used up (ligand depletion for a one-site binder). The replicates must be independent experiments.

Record fields
-------------
version, experiment_type ('dialysis'), experiment_ref, source_ref, assertion_ref
preparations   ligand_preparation_ref, protein_preparation_ref (the ligand that is measured and the protein that binds it, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (the ligand as the analyte key, the protein as the other partner; there is no surface).
quantities     kd, kd_spread, bmax, ki, ki_spread, percent_bound, percent_unbound, fraction_bound, fraction_unbound, ligand_total_concentration, free_ligand_concentration,
               bound_ligand_concentration, protein_concentration, ligand_range_lowest, ligand_range_highest, titration_point_count, membrane_cutoff, equilibration_time,
               run_temperature, buffer_ph, salt_concentration, protein_chamber_volume, buffer_chamber_volume, recovery, membrane_adsorption, volume_shift,
               technical_replicate_count, replicate_count: one operand each.
               Units: kd, kd_spread, ki, ki_spread, ligand_total_concentration, free_ligand_concentration, bound_ligand_concentration, protein_concentration, ligand_range_lowest and
               ligand_range_highest pM, nM, uM or mM; bmax 'nM', 'uM', 'mM' or 'ratio' (the number of binding sites: a concentration, or mol of ligand per mol of protein);
               percent_bound, percent_unbound, recovery, membrane_adsorption and volume_shift 'percent' (percent_bound: the percent of the total ligand that was bound to the
               protein; percent_unbound: the percent of the total ligand that was free; recovery: the percent of the total ligand that was recovered from both chambers;
               membrane_adsorption: the percent of the ligand that bound to the membrane and the device (nonspecific binding of the ligand to them); volume_shift: the percent
               by which the volume of the protein chamber changed during the dialysis); fraction_bound and fraction_unbound 'ratio' (between 0 and 1);
               membrane_cutoff 'kDa' (the molecular weight cutoff of the membrane); equilibration_time 'min' or 'h' (the time the cell was kept until equilibrium);
               run_temperature 'C' or 'K'; buffer_ph 'pH'; salt_concentration 'mM' or 'M' (monovalent salt of the buffer); protein_chamber_volume and buffer_chamber_volume
               'uL' or 'mL'; titration_point_count, technical_replicate_count (cells of one experiment) and replicate_count (independent experiments) 'count'.
concentration_series
               operand whose 'value' is a list of total ligand concentrations of a saturation series (unit pM, nM, uM or mM), or None when not given.
separation_method
               'equilibrium_dialysis', 'rapid_equilibrium_dialysis' (the RED device), 'ultrafiltration', 'ultracentrifugation' or None: how the free ligand was separated from the bound.
device_type    'red_device', 'dianorm', 'dialysis_cassette', 'dialysis_cup', 'spin_filter', 'other' or None: the device or cell. Kept in the record for the reviewer; no criterion
               judges it.
detection      'liquid_scintillation', 'lc_msms', 'fluorescence', 'absorbance', 'other' or None. How the ligand concentration was measured. Kept in the record for the reviewer.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
fit_model      'one_site', 'two_site', 'hill', 'other' or None: the model the saturation data were fitted with.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (separation_method, device_type, detection, spread_kind, fit_model), None when the
               choice is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's
fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (the quote states it only by
implication), 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand and
an 'unknown' fact carry support None. The grader keeps it and does not judge it; the converter does. Rule for the constructors: they take
``support`` and default it to 'direct' only so that forms built by tests, which do not go through the extraction, are direct; the extraction always
passes the model's own value.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record

SUPPORTS = ('direct', 'implied', 'about_something_else')


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': support}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    return {**literature_spr_record.fact(answer, refs), 'support': None if answer == 'unknown' else support}


VERSION = 'a105_dialysis_record_v1'
EXPERIMENT_TYPE = 'dialysis'
QUANTITIES = ('kd', 'kd_spread', 'bmax', 'ki', 'ki_spread', 'percent_bound', 'percent_unbound', 'fraction_bound', 'fraction_unbound', 'ligand_total_concentration', 'free_ligand_concentration', 'bound_ligand_concentration', 'protein_concentration', 'ligand_range_lowest', 'ligand_range_highest', 'titration_point_count', 'membrane_cutoff', 'equilibration_time', 'run_temperature', 'buffer_ph', 'salt_concentration', 'protein_chamber_volume', 'buffer_chamber_volume', 'recovery', 'membrane_adsorption', 'volume_shift', 'technical_replicate_count', 'replicate_count')
PREPARATION_KEYS = ('ligand_preparation_ref', 'protein_preparation_ref', 'dataset_ref')
SEPARATION_METHODS = ('equilibrium_dialysis', 'rapid_equilibrium_dialysis', 'ultrafiltration', 'ultracentrifugation')
DEVICE_TYPES = ('red_device', 'dianorm', 'dialysis_cassette', 'dialysis_cup', 'spin_filter', 'other')
DETECTIONS = ('liquid_scintillation', 'lc_msms', 'fluorescence', 'absorbance', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('one_site', 'two_site', 'hill', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'binding_detected': YES_NO, 'equilibrium_time_course_shown': YES_NO, 'recovery_checked': YES_NO, 'adsorption_checked_and_corrected': YES_NO, 'volume_shift_corrected': YES_NO, 'ligand_stable': YES_NO, 'free_ligand_measured_directly': YES_NO, 'protein_retained': YES_NO, 'buffer_only_control_equal': YES_NO, 'protein_at_or_above_kd': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
VOLUME_UNITS = ('uL', 'mL')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'bmax': ('nM', 'uM', 'mM', 'ratio'), 'ki': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'percent_bound': ('percent',), 'percent_unbound': ('percent',), 'fraction_bound': ('ratio',), 'fraction_unbound': ('ratio',), 'ligand_total_concentration': CONCENTRATION_UNITS, 'free_ligand_concentration': CONCENTRATION_UNITS, 'bound_ligand_concentration': CONCENTRATION_UNITS, 'protein_concentration': CONCENTRATION_UNITS, 'ligand_range_lowest': CONCENTRATION_UNITS, 'ligand_range_highest': CONCENTRATION_UNITS, 'titration_point_count': ('count',), 'membrane_cutoff': ('kDa',), 'equilibration_time': ('min', 'h'), 'run_temperature': ('C', 'K'), 'buffer_ph': ('pH',), 'salt_concentration': ('mM', 'M'), 'protein_chamber_volume': VOLUME_UNITS, 'buffer_chamber_volume': VOLUME_UNITS, 'recovery': ('percent',), 'membrane_adsorption': ('percent',), 'volume_shift': ('percent',), 'technical_replicate_count': ('count',), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
