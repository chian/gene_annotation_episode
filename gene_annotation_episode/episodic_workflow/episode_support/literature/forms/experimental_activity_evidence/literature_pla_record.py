"""The extracted record of ONE proximity ligation assay (PLA: in situ PLA, Duolink) experiment: two proteins are probed in fixed cells or in a tissue section with two primary antibodies raised in different species; secondary antibodies that carry short oligonucleotides (the PLA probes) bind the two primaries; when the two proteins are within about 40 nm of each other the oligonucleotides are joined by a ligation into a circle, the circle is amplified by rolling-circle amplification, and fluorescent probes that hybridise to the amplified product make one bright punctum for each proximity event. The readout is the discrete fluorescent puncta, counted per cell (or per field) by image analysis. The result is QUALITATIVE proximity evidence (the two proteins are within about 40 nm in the cell); it gives no binding constant, and a count of puncta is never a KD.

What a leaf extraction holds for one PLA experiment: the two primary antibodies and the species they come from, whether they were validated, the cells or the tissue and their fixation, the PLA probes and the amplification, the images and the image analysis software, the puncta per cell of the test condition (both primary antibodies) and of the negative controls (a single primary antibody, no primary antibody, a knockdown or knockout of one protein, a competing peptide), a positive control pair, the number of cells counted, the replicates, and where in the cell the puncta lay. The control of the experiment is the single-antibody and the no-primary reaction (they show the probes do not join by themselves), the depletion of one protein or a competitor (it shows the puncta are the proximity of these two proteins), and a pair of proteins known to interact.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never invented and never omitted. A number of puncta may be 0 (a control without a punctum). The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What PLA shows and what can go wrong is what the form keeps. A punctum says only that the two antibody pairs were close: an antibody that also binds another protein, a probe that sticks to the cell, or two proteins that are merely crowded in a small compartment (or overexpressed) give puncta without an interaction, so the controls decide how much a count means: the single-antibody and the no-primary reactions must give few or no puncta, a depletion of one protein (siRNA, knockdown, knockout) or a competing peptide must lower the puncta of the test, and the two primary antibodies must come from different species (the two PLA probes are species specific). The puncta are counted per cell over enough cells, blind or by an automatic image analysis, with a statistical test, in independent experiments.

Record fields
-------------
version, experiment_type ('pla'), experiment_ref, source_ref, assertion_ref
preparations   component_a_preparation_ref, component_b_preparation_ref (the two proteins that are probed, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (component a as the analyte key, component b as the other partner; there is no surface).
quantities     puncta_per_cell_target, puncta_per_cell_control, puncta_per_cell_knockdown, puncta_spread_target, puncta_spread_control, protein_depletion_percent, cells_counted,
               amplification_time, replicate_count: one operand each.
               Units: puncta_per_cell_target 'puncta_per_cell' (the mean number of puncta per cell with both primary antibodies, the test), puncta_per_cell_control
               'puncta_per_cell' (the mean number with a single primary antibody or with no primary antibody: the negative control), puncta_per_cell_knockdown
               'puncta_per_cell' (the mean number with both primary antibodies after the knockdown, the knockout or the competition of one protein);
               puncta_spread_target and puncta_spread_control 'puncta_per_cell' (the stated spread, of the kind puncta_spread_kind names, of the puncta per cell of the test and of the
               negative control); protein_depletion_percent 'percent' (the measured fall of the protein that the specificity control depletes, by western blot or immunofluorescence); cells_counted
               'count' (the number of cells in which the puncta of the test were counted); amplification_time 'min' (the rolling-circle amplification time); replicate_count 'count'.
choices        cell_system 'cultured_cells', 'primary_cells', 'tissue_section' or None; fixation 'paraformaldehyde', 'methanol', 'formalin_fixed_paraffin_embedded' or None;
               quantification_software 'imagej', 'cellprofiler', 'blobfinder', 'other' or None; puncta_spread_kind 'standard_deviation', 'standard_error' or None (what the two
               puncta_spread quantities are). The cell system, fixation and software are kept in the record for the reviewer; the spread kind is read by the grader beside the spreads.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (cell_system, fixation, quantification_software), None when the choice is not stated.
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


VERSION = 'a105_pla_record'
EXPERIMENT_TYPE = 'pla'
QUANTITIES = ('puncta_per_cell_target', 'puncta_per_cell_control', 'puncta_per_cell_knockdown', 'puncta_spread_target', 'puncta_spread_control', 'protein_depletion_percent', 'cells_counted', 'amplification_time', 'replicate_count')
PREPARATION_KEYS = ('component_a_preparation_ref', 'component_b_preparation_ref', 'dataset_ref')
CELL_SYSTEMS = ('cultured_cells', 'primary_cells', 'tissue_section')
FIXATIONS = ('paraformaldehyde', 'methanol', 'formalin_fixed_paraffin_embedded')
SOFTWARES = ('imagej', 'cellprofiler', 'blobfinder', 'other')
SPREAD_KINDS = ('standard_deviation', 'standard_error')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'proximity_signal_detected': YES_NO, 'primary_antibodies_different_species': YES_NO, 'antibodies_validated': YES_NO, 'single_antibody_controls_negative': YES_NO, 'no_primary_control_negative': YES_NO, 'specificity_control_reduces_signal': YES_NO, 'positive_control_pair_done': YES_NO, 'puncta_in_expected_compartment': YES_NO, 'quantification_blinded': YES_NO, 'statistical_test_done': YES_NO, 'independent_experiments': YES_NO}

PUNCTA_PER_CELL = 'puncta_per_cell'
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'puncta_per_cell_target': (PUNCTA_PER_CELL,), 'puncta_per_cell_control': (PUNCTA_PER_CELL,), 'puncta_per_cell_knockdown': (PUNCTA_PER_CELL,), 'puncta_spread_target': (PUNCTA_PER_CELL,), 'puncta_spread_control': (PUNCTA_PER_CELL,), 'protein_depletion_percent': ('percent',), 'cells_counted': ('count',), 'amplification_time': ('min',), 'replicate_count': ('count',)}
