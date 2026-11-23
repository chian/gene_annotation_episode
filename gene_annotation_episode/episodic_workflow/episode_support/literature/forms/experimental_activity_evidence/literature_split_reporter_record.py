"""The extracted record of ONE split-reporter (protein-fragment complementation) experiment: a reporter is cut into two fragments that are inactive (or dark) apart, the two fragments are fused to the two candidate partner proteins, and when the partners come together the fragments are brought close enough to reconstitute the reporter, whose signal (luminescence, fluorescence or enzyme activity) reports that the partners are in proximity or interact. Reporters in use: split luciferase (NanoBiT, split NanoLuc: a large fragment LgBiT and a small fragment SmBiT of low affinity for each other, so that the signal follows the partners; other split luciferases), split GFP or split fluorescent protein (bimolecular fluorescence complementation, BiFC), split beta-lactamase, split TEV protease (with a reporter gene or a dye). The assay is run in living cells, in a cell lysate or with purified proteins. A signal against a titration of one partner (or a kinetic time course) can give an APPARENT KD, which NanoBiT with its reversible fragments can report; the result is otherwise mostly QUALITATIVE (a signal above the controls).

What a leaf extraction holds for one split-reporter experiment: the reporter system, the two fusions (which end of each partner carries which fragment, and how many of the fusion orientations were built), the system (cells, lysate, purified proteins), the readout (an endpoint, a titration, a kinetic time course), the signal of the tested pair against the background and against the controls (each fragment fusion alone or with the free partner fragment, a pair of non-interacting proteins, a non-binding mutant, a known interacting pair as the positive control), whether the fusion proteins were shown to be expressed, whether the complementation of the reporter is reversible, the titration (its lowest and highest concentration and their number) and any apparent KD, and the replicates.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What a split reporter shows and what can go wrong is what the form keeps. The signal shows that the two fragments came together, not that the two proteins bind directly: proteins in one complex, or crowded in one membrane or compartment, can bring the fragments together, so the signal is judged against controls. The fragments themselves can reconstitute a little by themselves (a high expression, a self-association of the fragments), so each fragment fusion alone, or with the free partner fragment, must be at background. A pair of unrelated proteins fused the same way, and a non-binding mutant of one partner, show that the signal is specific to the interaction. A known interacting pair shows that the system works. The fusion can block the binding or place the fragments too far apart, so a negative result in one orientation is weak, and a positive result that is seen in several orientations is stronger. A signal depends on how much of the fusion proteins is expressed, so the expression must be shown, and the background (untransfected cells, substrate or buffer alone) is subtracted. Some reconstitutions are irreversible (the split fluorescent proteins trap the complex), so the signal accumulates and cannot give an equilibrium constant; a reversible reporter (NanoBiT) follows the equilibrium, and an apparent KD needs a titration with concentrations on both sides of the KD, in which the signal is saturable. An apparent KD is labelled as derived from the split reporter and is not a KD of the purified proteins.

Record fields
-------------
version, experiment_type ('split_reporter'), experiment_ref, source_ref, assertion_ref
preparations   component_a_preparation_ref, component_b_preparation_ref (the two proteins that are fused to the fragments, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (component a as the analyte key, component b as the other partner; there is no surface).
quantities     kd, kd_spread, signal_to_background, signal_over_negative_control, orientation_pairs_tested, orientation_pairs_positive, loaded_concentration_lowest, loaded_concentration_highest,
               fixed_partner_concentration, concentration_count, replicate_count: one operand each.
               Units: kd and kd_spread pM, nM, uM or mM (the apparent dissociation constant from the titration or the kinetics and its spread); signal_to_background 'ratio' (the signal of the tested
               pair divided by the background signal); signal_over_negative_control 'ratio' (the signal of the tested pair divided by the signal of the negative control pair); orientation_pairs_tested
               'count' (the number of fusion orientation combinations tested); orientation_pairs_positive 'count' (the number of those orientation combinations that gave a signal); loaded_concentration_lowest and loaded_concentration_highest pM, nM, uM or mM (the lowest and the highest
               concentration of the titrated partner); fixed_partner_concentration pM, nM, uM or mM (the constant concentration of the partner that is NOT titrated, the one held fixed while the other is added; above the KD the titration is stoichiometric and the apparent KD is only an upper bound); concentration_count 'count' (the number of titration concentrations); replicate_count 'count'.
reporter_system 'split_nanoluc', 'other_split_luciferase', 'split_fluorescent_protein', 'split_beta_lactamase', 'split_tev', 'other' or None: the reporter. Kept in the record for the reviewer.
assay_system   'living_cells', 'cell_lysate', 'purified_proteins', 'other' or None: where the complementation was measured. Kept in the record for the reviewer.
readout_mode   'endpoint', 'titration', 'kinetic_time_course' or None: how the signal was read. Kept in the record for the reviewer.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (reporter_system, assay_system, readout_mode, spread_kind), None when the choice is not stated.
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


VERSION = 'a105_split_reporter_record'
EXPERIMENT_TYPE = 'split_reporter'
QUANTITIES = ('kd', 'kd_spread', 'signal_to_background', 'signal_over_negative_control', 'orientation_pairs_tested', 'orientation_pairs_positive', 'loaded_concentration_lowest', 'loaded_concentration_highest', 'fixed_partner_concentration', 'concentration_count', 'replicate_count')
PREPARATION_KEYS = ('component_a_preparation_ref', 'component_b_preparation_ref', 'dataset_ref')
REPORTER_SYSTEMS = ('split_nanoluc', 'other_split_luciferase', 'split_fluorescent_protein', 'split_beta_lactamase', 'split_tev', 'other')
ASSAY_SYSTEMS = ('living_cells', 'cell_lysate', 'purified_proteins', 'other')
READOUT_MODES = ('endpoint', 'titration', 'kinetic_time_course')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'interaction_detected': YES_NO, 'fragment_alone_control_negative': YES_NO, 'unrelated_pair_control_negative': YES_NO, 'binding_mutant_control_negative': YES_NO, 'positive_control_done': YES_NO, 'signal_in_several_orientations': YES_NO, 'expression_verified': YES_NO, 'expression_matched_to_control': YES_NO, 'saturable_titration_shown': YES_NO, 'complementation_reversible': YES_NO, 'background_subtracted': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'signal_to_background': ('ratio',), 'signal_over_negative_control': ('ratio',), 'orientation_pairs_tested': ('count',), 'orientation_pairs_positive': ('count',), 'loaded_concentration_lowest': CONCENTRATION_UNITS, 'loaded_concentration_highest': CONCENTRATION_UNITS, 'fixed_partner_concentration': CONCENTRATION_UNITS, 'concentration_count': ('count',), 'replicate_count': ('count',)}
