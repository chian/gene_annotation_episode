"""The extracted record of ONE cellular thermal shift assay (CETSA) experiment: a compound (a ligand, a drug, a fragment) is added to intact cells, to a cell lysate or to a tissue sample, the sample is heated, the denatured and aggregated protein is removed (centrifugation, filtration) and the amount of the target protein that stays soluble is read out (a western blot, an AlphaScreen or other immunoassay, mass spectrometry). A ligand that binds the target protein usually makes it more stable, so more of it stays soluble at a temperature at which the unbound protein is denatured: the TARGET ENGAGEMENT is the ligand-induced thermal stabilisation. Two formats belong to it. The MELT CURVE (thermal shift, or temperature-range CETSA): the sample is heated at a series of temperatures with and without the compound, the soluble fraction against the temperature is a melt curve with a melting temperature Tm, and the engagement is the shift of the curve (delta Tm, in degrees Celsius). The ISOTHERMAL DOSE-RESPONSE format (ITDR-CETSA, ITDRF-CETSA): the sample is heated at ONE temperature, chosen in the transition of the unbound protein, with a series of compound concentrations, and the soluble fraction against the concentration gives an EC50 of the engagement, an apparent measure of the engagement in the cell (a compound that must enter the cell, or be converted, is read as it is in the cell; the EC50 depends on the temperature and the heating time and is not the equilibrium dissociation constant, so it is an apparent constant derived from the thermal shift). Thermal proteome profiling (TPP, CETSA-MS) belongs to it only where a paragraph reports the engagement of one target of one compound (the melt curves of the target with and without the compound).

What a leaf extraction holds for one CETSA experiment: the target protein, the compound and the sample (intact cells of a named line, a lysate, a tissue), the compound concentration (one, or a series for an ITDR) and the time of the compound incubation, the heating (the temperature range of a melt curve with the number of temperatures; the one temperature of an ITDR; the heating time), the readout, and the result (the Tm with and without the compound and its shift, or the EC50 of the engagement). The controls of the experiment are the vehicle control (the same cells with the solvent of the compound, heated the same way), a loading control (a protein that does not change with the compound, or the total protein, to show that the same amount of soluble sample was read), a control of the total amount of the target (the compound does not change the expression or the stability of the target in an unheated sample), a negative compound (an inactive analogue or a compound that does not bind), a specificity control (a mutant of the binding site, a competition with a known ligand, or a knockdown of the target), the viability of the cells and the replicates.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What CETSA shows and what can go wrong is what the form keeps. The thermal shift is read against the vehicle curve of the same experiment, with the same temperatures and the same readout; a shift is only as good as the reproducibility of the Tm (about a degree) and of the number of temperatures that define the curve. A ligand can bind and not change the stability (a binder with no shift is not proof of no binding), and a compound can change the stability of the target through the cell (a change of the expression, a modification, a partner) and not through a direct binding, so an unheated control of the total target, a negative compound and a specificity control (a binding-site mutant, a competition) are what separate the direct engagement. An ITDR needs a temperature in the transition of the unbound protein (at a temperature where all the protein is still folded, or where all is denatured, no ligand effect is seen), concentrations on both sides of the EC50 (the plateaux of the curve), and enough concentrations to fit a sigmoid. A loading control is what shows that a lower band is not a lower load. In intact cells, a compound that kills the cells or lyses them changes the soluble fraction for other reasons.

Record fields
-------------
version, experiment_type ('cetsa'), experiment_ref, source_ref, assertion_ref
preparations   ligand_preparation_ref, target_preparation_ref (the compound and the target protein, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (the ligand as the analyte key, the target as the other partner; there is no surface).
quantities     engagement_ec50, engagement_ec50_spread, tm_vehicle, tm_ligand, tm_shift, tm_spread, isothermal_temperature, heating_time, temperature_lowest, temperature_highest,
               temperature_count, compound_concentration_lowest, compound_concentration_highest, concentration_count, compound_incubation_time, replicate_count: one operand each.
               Units: engagement_ec50 and engagement_ec50_spread pM, nM, uM or mM (the EC50 of the isothermal dose-response, or an apparent affinity that the passage derives from it, and its spread);
               tm_vehicle, tm_ligand and tm_shift 'C' (the melting temperature without and with the compound, and the shift of the melt curve by the compound: the stabilisation, above 0); tm_spread 'C' (the standard deviation of the melting temperature over replicates: the sheet compares the shift with the scatter of the Tm);
               isothermal_temperature 'C' (the one temperature of an ITDR); heating_time 's' or 'min'; temperature_lowest and temperature_highest 'C' (the ends of the temperature range of a melt curve);
               temperature_count 'count' (the number of temperatures of the melt curve); compound_concentration_lowest and compound_concentration_highest pM, nM, uM or mM (the ends of the concentration series);
               concentration_count 'count' (the number of compound concentrations of the series); compound_incubation_time 'min' or 'h' (how long the sample was with the compound before the heating);
               replicate_count 'count'.
sample_format      'intact_cells', 'cell_lysate', 'tissue_or_animal' or None: what was heated.
experiment_format  'melt_curve', 'itdr', 'melt_curve_and_itdr' or None: the format of the result.
readout            'western_blot', 'alphascreen', 'mass_spectrometry', 'other' or None: how the soluble target was read. Kept in the record for the reviewer.
spread_kind        'standard_error', 'standard_deviation', 'confidence_interval' or None. What engagement_ec50_spread is.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (sample_format, experiment_format, readout, spread_kind), None when the choice is not stated.
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


VERSION = 'a105_cetsa_record_v1'
EXPERIMENT_TYPE = 'cetsa'
QUANTITIES = ('engagement_ec50', 'engagement_ec50_spread', 'tm_vehicle', 'tm_ligand', 'tm_shift', 'tm_spread', 'isothermal_temperature', 'heating_time', 'temperature_lowest', 'temperature_highest', 'temperature_count', 'compound_concentration_lowest', 'compound_concentration_highest', 'concentration_count', 'compound_incubation_time', 'replicate_count')
PREPARATION_KEYS = ('ligand_preparation_ref', 'target_preparation_ref', 'dataset_ref')
SAMPLE_FORMATS = ('intact_cells', 'cell_lysate', 'tissue_or_animal')
EXPERIMENT_FORMATS = ('melt_curve', 'itdr', 'melt_curve_and_itdr')
READOUTS = ('western_blot', 'alphascreen', 'mass_spectrometry', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'target_engagement_shown': YES_NO, 'vehicle_control_done': YES_NO, 'loading_control_used': YES_NO, 'melt_curve_measured': YES_NO, 'isothermal_temperature_in_window': YES_NO, 'dose_dependent_shown': YES_NO, 'negative_control_done': YES_NO, 'specificity_control_done': YES_NO, 'cell_integrity_checked': YES_NO, 'total_target_level_controlled': YES_NO, 'independent_experiments': YES_NO, 'tm_spread_over_independent_experiments': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'engagement_ec50': CONCENTRATION_UNITS, 'engagement_ec50_spread': CONCENTRATION_UNITS, 'tm_vehicle': ('C',), 'tm_ligand': ('C',), 'tm_shift': ('C',), 'tm_spread': ('C',), 'isothermal_temperature': ('C',), 'heating_time': ('s', 'min'), 'temperature_lowest': ('C',), 'temperature_highest': ('C',), 'temperature_count': ('count',), 'compound_concentration_lowest': CONCENTRATION_UNITS, 'compound_concentration_highest': CONCENTRATION_UNITS, 'concentration_count': ('count',), 'compound_incubation_time': ('min', 'h'), 'replicate_count': ('count',)}
