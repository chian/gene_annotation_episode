"""The extracted record of ONE BRET / NanoBRET experiment (bioluminescence resonance energy transfer in cells): two proteins are fused, one to a luciferase DONOR (Rluc, Rluc8, NanoLuc) and one to a fluorescent ACCEPTOR (YFP or Venus, a HaloTag ligand, or, in NanoBRET target engagement, a fluorescent TRACER that binds the donor-fused target), and the two are expressed in live cells. When donor and acceptor are closer than about 10 nm, the energy of the luciferase reaction (its substrate: coelenterazine or furimazine) passes to the acceptor, and the BRET ratio (acceptor emission over donor emission, read through two filters) rises. Three kinds of result belong to it. A SATURATION (titration) experiment: the donor amount is held constant, the acceptor amount is raised, and the BRET ratio is plotted against the acceptor-to-donor expression ratio; a specific interaction gives a hyperbola with a BRETmax (the plateau) and a BRET50 (the acceptor-to-donor ratio at half of BRETmax; a low BRET50 means a high apparent affinity), a random collision of two over-expressed proteins in a membrane gives a straight line or a curve with a much higher BRET50. A TRACER experiment (NanoBRET target engagement): a tracer at a fixed concentration, or at a titration, gives an apparent KD for the donor-fused target, and an unlabelled compound that displaces the tracer lowers the signal (an IC50, from which a Ki). A single-ratio or ligand-induced experiment: one BRET ratio of a pair against a negative control, or its change after a ligand.
The result is mostly QUALITATIVE or semi-quantitative (a BRET ratio, a BRET50); an apparent KD or Ki in a concentration unit comes only from a tracer titration or a displacement.

What a leaf extraction holds for one BRET experiment: the donor and the acceptor (their kind), the cells and the expression (transient or stable), the substrate, the format (saturation titration, competition, ligand-induced), the acceptor-to-donor ratio series, BRET50, BRETmax, the BRET ratio of the pair and of the negative control, the tracer, the apparent KD or Ki, the fit, the replicates. The controls are the donor alone (the background that is subtracted), the acceptor alone, a non-interacting pair (that must stay on a line or at a far higher BRET50), the matching of the expression levels (acceptor fluorescence and donor luminescence measured), the swap of the fusion positions, and the displacement of a tracer by an unlabelled competitor.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What BRET shows and what can go wrong is what the form keeps. A BRET signal in cells shows proximity, not binding: over-expressed proteins in one membrane give a BRET signal by random collision (bystander BRET) that grows linearly with the acceptor-to-donor ratio, so the proof of a specific interaction is saturation, and a non-interacting pair run in the same way shows what random collision gives (it may itself saturate, then the pair is not separated). A low BRET50 only means something against the BRET50 of that negative control. The acceptor-to-donor ratio is read from the fluorescence and luminescence of the same cells: the expression levels must be measured. The donor-only signal (donor emission in the acceptor channel) is a background that is subtracted. A fusion can block an interaction: both orientations are tried. A tracer in a target-engagement experiment must be used near or below its own KD for a Ki to follow from its displacement.

Record fields
-------------
version, experiment_type ('bret'), experiment_ref, source_ref, assertion_ref
preparations   component_a_preparation_ref, component_b_preparation_ref (the donor-fused and the acceptor-fused protein, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (component a as the analyte key, component b as the other partner; there is no surface).
quantities     kd, kd_spread, ki, ki_spread, bret50, bret50_negative_control, bret_max, bret_ratio_pair, bret_ratio_negative_control, ratio_lowest, ratio_highest, titration_point_count,
               tracer_concentration, fit_r_squared, replicate_count, and (grader gaps of the 2026-11-21 range review) bret50_spread, bret50_negative_control_spread, bret_ratio_pair_spread,
               bret_ratio_negative_control_spread, bret_ratio_donor_only, tracer_kd: one operand each.
               Units: kd, kd_spread, ki, ki_spread and tracer_concentration pM, nM, uM or mM (the apparent dissociation constant of the tracer or of the pair from a titration, the
               inhibition constant of a competitor from a displacement, and their spread; the tracer concentration used); bret50 and bret50_negative_control 'ratio' (the acceptor-to-donor
               ratio at half of BRETmax, for the pair and for the negative control pair, as the passage gives the number); bret_max, bret_ratio_pair and bret_ratio_negative_control 'ratio' or 'mBU' (milli BRET
               units: the plateau of the saturation curve, the BRET ratio of the pair and the BRET ratio of the negative control); ratio_lowest and ratio_highest 'ratio' (the lowest and
               the highest acceptor-to-donor ratio of the titration); titration_point_count and replicate_count 'count'; fit_r_squared 'ratio' (the coefficient of determination of the fit);
               bret50_spread and bret50_negative_control_spread 'ratio' (the stated standard error, standard deviation or confidence-interval half-width of the BRET50 of the pair and of the negative control, in the same units as
               the BRET50); bret_ratio_pair_spread and bret_ratio_negative_control_spread 'ratio' or 'mBU' (the same for the two BRET ratios); bret_ratio_donor_only 'ratio' or 'mBU' (the BRET ratio of the donor alone, the
               background that a RAW, not background-subtracted, ratio contains); tracer_kd pM, nM, uM or mM (the apparent dissociation constant of the tracer for the donor-fused target, which sets how the tracer concentration compares
               with it for a Ki).
bret_format    'saturation_titration', 'competition_displacement', 'saturation_and_competition', 'ligand_induced_change' or None: what the result is from.
donor          'rluc', 'nanoluc' or 'other' (Rluc and Rluc8 are 'rluc') or None.
acceptor       'fluorescent_protein', 'halotag_ligand', 'fluorescent_tracer' or 'other' or None.
expression     'transient_transfection', 'stable_expression', 'endogenous_tagging' or None: how the fusions are expressed.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What every stated spread of the record is (kd_spread, ki_spread, bret50_spread, bret50_negative_control_spread, bret_ratio_pair_spread, bret_ratio_negative_control_spread).
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
               Two facts are the tests against bystander BRET (random collision of over-expressed proteins): hyperbola_preferred_over_linear (a stated model comparison, F-test or AIC, favouring the
               hyperbola over a straight line for the pair under test) and bret_constant_across_expression (the BRET ratio stays constant when the total expression changes at a fixed
               acceptor-to-donor ratio; James et al. 2006, Felce et al. 2017). background_subtracted also tells whether the stated BRET ratios are net (yes) or raw (no).
choice_support name -> support of each plain choice field (bret_format, donor, acceptor, expression, spread_kind), None when the choice is not stated.
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


VERSION = 'a105_bret_record'
EXPERIMENT_TYPE = 'bret'
QUANTITIES = ('kd', 'kd_spread', 'ki', 'ki_spread', 'bret50', 'bret50_negative_control', 'bret_max', 'bret_ratio_pair', 'bret_ratio_negative_control', 'ratio_lowest', 'ratio_highest', 'titration_point_count', 'tracer_concentration', 'fit_r_squared', 'replicate_count', 'bret50_spread', 'bret50_negative_control_spread', 'bret_ratio_pair_spread', 'bret_ratio_negative_control_spread', 'bret_ratio_donor_only', 'tracer_kd')
PREPARATION_KEYS = ('component_a_preparation_ref', 'component_b_preparation_ref', 'dataset_ref')
BRET_FORMATS = ('saturation_titration', 'competition_displacement', 'saturation_and_competition', 'ligand_induced_change')
DONORS = ('rluc', 'nanoluc', 'other')
ACCEPTORS = ('fluorescent_protein', 'halotag_ligand', 'fluorescent_tracer', 'other')
EXPRESSIONS = ('transient_transfection', 'stable_expression', 'endogenous_tagging')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'interaction_detected': YES_NO, 'saturation_shown': YES_NO, 'negative_control_pair_used': YES_NO, 'negative_control_no_specific_signal': YES_NO, 'donor_only_control_done': YES_NO, 'acceptor_only_control_done': YES_NO,
         'expression_levels_measured': YES_NO, 'background_subtracted': YES_NO, 'fusion_orientation_swapped': YES_NO, 'tracer_displaced_by_competitor': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO,
         'hyperbola_preferred_over_linear': YES_NO, 'bret_constant_across_expression': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
SIGNAL_UNITS = ('ratio', 'mBU')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'ki': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'bret50': ('ratio',), 'bret50_negative_control': ('ratio',), 'bret_max': SIGNAL_UNITS, 'bret_ratio_pair': SIGNAL_UNITS, 'bret_ratio_negative_control': SIGNAL_UNITS, 'ratio_lowest': ('ratio',), 'ratio_highest': ('ratio',), 'titration_point_count': ('count',), 'tracer_concentration': CONCENTRATION_UNITS, 'fit_r_squared': ('ratio',), 'replicate_count': ('count',),
         'bret50_spread': ('ratio',), 'bret50_negative_control_spread': ('ratio',), 'bret_ratio_pair_spread': SIGNAL_UNITS, 'bret_ratio_negative_control_spread': SIGNAL_UNITS, 'bret_ratio_donor_only': SIGNAL_UNITS, 'tracer_kd': CONCENTRATION_UNITS}
