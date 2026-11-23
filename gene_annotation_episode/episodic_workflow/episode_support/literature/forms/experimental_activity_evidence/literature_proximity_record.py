"""The extracted record of ONE proximity-labeling experiment: a bait protein is fused to a biotin ligase (BioID, BioID2, TurboID, miniTurbo) or to a peroxidase (APEX, APEX2), or the enzyme is used as two split halves, and the fusion is expressed in living cells (or tissue). With biotin (ligases; minutes to hours) or biotin-phenol and a short pulse of hydrogen peroxide (peroxidases; about one minute) the enzyme biotinylates proteins within about 10 to 20 nm of the bait. The biotinylated proteins are captured on streptavidin and identified by western blot (a named candidate) or by mass spectrometry (many proteins), and a candidate partner is called PROXIMAL when it is enriched over a control: the same enzyme without the bait (a free ligase), the enzyme fused to an unrelated protein or sent to another compartment, or the same cells without biotin or without hydrogen peroxide. The result is QUALITATIVE or semi-quantitative (an enrichment as a fold change, a spectral count ratio, a SAINT or false discovery rate score); it gives no binding constant, and proximity is not direct binding: a proximal protein may be a direct partner, a member of the same complex, or only a neighbour in the same compartment.

What a leaf extraction holds for one proximity-labeling experiment: the enzyme and the site of its fusion to the bait, the cell system, the labelling conditions (biotin or biotin-phenol concentration, hydrogen peroxide concentration, labelling time), the capture and the readout, and the enrichment of the candidate partner over the control (fold change, false discovery rate). The controls of the experiment are the free enzyme, the unlabelled cells (no biotin or no peroxide), and an unrelated or differently localised bait; the checks are that the fusion is expressed near the endogenous level and localises like the endogenous bait, and that biotinylation depends on the fusion and the labelling.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What can go wrong is what the form keeps. A free enzyme labels everything it can reach, so an enrichment is meaningful only against a control with a matching enzyme level; a fusion expressed far above the endogenous level mislocalises and labels neighbours that are not natural; without biotin (or peroxide) there must be no labelling; abundant, sticky and naturally biotinylated proteins are enriched by the capture itself; and an enriched protein is proximal, not necessarily bound.

Record fields
-------------
version, experiment_type ('proximity'), experiment_ref, source_ref, assertion_ref
preparations   bait_preparation_ref, candidate_preparation_ref, dataset_ref: each a string or None (unknown). They are references to records, which the caller supplies; no passage
               states them. The converter hands them to the merger as its dependence keys (the bait as the analyte key, the candidate as the other partner; there is no surface).
quantities     enrichment_fold, enrichment_fdr, bait_expression_ratio, labeling_time, biotin_concentration, peroxide_concentration, replicate_count: one operand each.
               Units: enrichment_fold 'ratio' (the candidate in the bait sample over the control; fold change) or 'log2_ratio' (its base-2 logarithm); enrichment_fdr 'percent' or 'fraction'
               (the false discovery rate or q-value of the candidate's enrichment); bait_expression_ratio 'ratio' (the fusion over the endogenous bait); labeling_time 'min' or 'h';
               biotin_concentration and peroxide_concentration 'uM' or 'mM' (biotin or biotin-phenol; hydrogen peroxide); replicate_count 'count'.
ligase         'bioid', 'bioid2', 'turboid', 'miniturbo', 'apex', 'apex2', 'split_bioid', 'split_turboid', 'split_apex2', 'other' or None: the labelling enzyme.
fusion_site    'n_terminal', 'c_terminal', 'internal' or None: where the enzyme is fused to the bait.
cell_system    'mammalian_cells', 'yeast', 'bacteria', 'plant', 'parasite', 'animal', 'other' or None: where the labelling was done.
readout        'western_blot', 'mass_spectrometry', 'western_blot_and_mass_spectrometry' or None: how the biotinylated proteins were identified.
quantification 'spectral_counts', 'label_free_intensity', 'silac', 'tmt', 'densitometry', 'other' or None: how the enrichment was quantified. These five choices are kept in the record for the reviewer.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (ligase, fusion_site, cell_system, readout, quantification), None when the choice is not stated.
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


VERSION = 'a105_proximity_record'
EXPERIMENT_TYPE = 'proximity'
QUANTITIES = ('enrichment_fold', 'enrichment_fdr', 'bait_expression_ratio', 'labeling_time', 'biotin_concentration', 'peroxide_concentration', 'replicate_count')
PREPARATION_KEYS = ('bait_preparation_ref', 'candidate_preparation_ref', 'dataset_ref')
LIGASES = ('bioid', 'bioid2', 'turboid', 'miniturbo', 'apex', 'apex2', 'split_bioid', 'split_turboid', 'split_apex2', 'other')
FUSION_SITES = ('n_terminal', 'c_terminal', 'internal')
CELL_SYSTEMS = ('mammalian_cells', 'yeast', 'bacteria', 'plant', 'parasite', 'animal', 'other')
READOUTS = ('western_blot', 'mass_spectrometry', 'western_blot_and_mass_spectrometry')
QUANTIFICATIONS = ('spectral_counts', 'label_free_intensity', 'silac', 'tmt', 'densitometry', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'candidate_enriched': YES_NO, 'ligase_only_control': YES_NO, 'unlabeled_control': YES_NO, 'unrelated_bait_control': YES_NO, 'biotinylation_confirmed': YES_NO, 'streptavidin_capture': YES_NO, 'bait_expression_checked': YES_NO, 'bait_localization_checked': YES_NO, 'orthogonal_validation': YES_NO, 'fold_over_matched_control': YES_NO, 'statistical_test_used': YES_NO, 'independent_experiments': YES_NO}

CONCENTRATION_UNITS = ('uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'enrichment_fold': ('ratio', 'log2_ratio'), 'enrichment_fdr': ('percent', 'fraction'), 'bait_expression_ratio': ('ratio',), 'labeling_time': ('min', 'h'), 'biotin_concentration': CONCENTRATION_UNITS, 'peroxide_concentration': CONCENTRATION_UNITS, 'replicate_count': ('count',)}
