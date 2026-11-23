"""The extracted record of ONE microscopy co-localization / recruitment experiment: two proteins are followed by fluorescence microscopy (a fluorescent protein fusion, a dye-labelled purified protein or an immunofluorescence stain) and the experiment shows that one labelled protein is found where the other is: the two labelled proteins co-localize in cells; one protein is recruited to the site (a focus, a pole, a membrane, a condensate) that the other makes; the recruitment is reproduced in a heterologous host that has neither protein; a purified labelled protein is recruited into droplets or condensates, onto beads or onto a membrane made of the other purified protein; or the localization is lost when the other protein is deleted or its binding region is removed. The readout is where the fluorescence lies, scored as an observed yes or no, as the fraction of the scored cells, foci or droplets that show it, as a correlation coefficient of the two channels (Pearson), or as an enrichment (the signal at the site of the partner over the signal elsewhere, also called a partition coefficient). The result is QUALITATIVE nearness evidence (with diffraction-limited imaging the two proteins lie within about 250 nm of each other, which is nearness and not contact); it gives no binding constant, and a fraction, a coefficient or an enrichment is never a KD. FRET (its own method), proximity ligation (its own method), split reporters and BiFC (their own method), the mobility of one protein alone (FRAP) and the localization of one protein with no second protein involved are not this method.

What a leaf extraction holds for one co-localization experiment: the two proteins and their labels, the system (the native host, a heterologous host that has neither protein, or purified proteins in vitro), the imaging mode, whether the result is a co-localization or a recruitment, the control with a protein that is not expected to bind (or the fluorescent tag alone), the loss of the localization when the partner is absent, when the binding region is removed, and the following of the partner when it is put somewhere else, the expression level, the function of the tagged protein, the number of cells, foci or droplets scored, the fraction that showed the co-localization, the Pearson coefficient, the enrichment and the number of independent experiments. The control of the experiment is the unrelated protein or the tag alone under the same conditions (it shows that the site does not recruit any protein), the absence of the partner (it shows that the site is the partner and not something else there), the removal of the binding region (it shows that the proposed region is the one that binds), and a system that has no third protein that could bridge the two (a heterologous host or purified proteins).
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis, AUC and PLA records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never invented and never omitted. A fraction of the scored objects may be 0 (none showed it). The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What co-localization shows and what can go wrong is what the form keeps. Two labelled proteins that lie at the same place show only that they are found together: a third protein of the cell can bridge them, a crowded compartment or an overexpressed protein that aggregates puts both in one spot, a fluorescent tag can itself move or cluster a protein, and an image shown for one cell is a picture and not a result. The controls decide how much a co-localization means: a protein that is not expected to bind (or the tag alone) must not be recruited under the same conditions, the localization must be lost when the partner is absent, a mutant or truncation that lacks the proposed binding region must not co-localize, and the protein should follow the partner when the partner is put somewhere else. A heterologous host that has neither protein, or purified proteins, leave no native third protein that could bridge the two. The result is quantified over a stated number of cells, foci or droplets, in independent experiments.

Record fields
-------------
version, experiment_type ('colocalization'), experiment_ref, source_ref, assertion_ref
preparations   component_a_preparation_ref, component_b_preparation_ref (the two proteins that are followed, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (component a as the analyte key, component b as the other partner; there is no surface).
quantities     objects_counted, fraction_colocalized, pearson_coefficient, enrichment_ratio, replicate_count: one operand each.
               Units: objects_counted 'count' (the number of cells, foci or droplets scored for the test), fraction_colocalized 'percent' (the percent of the scored objects that show the
               co-localization or the recruitment), pearson_coefficient 'ratio' (the correlation coefficient of the two channels, from -1 to 1), enrichment_ratio 'ratio' (the signal at the site of
               the partner over the signal elsewhere, also called a partition coefficient or an enrichment), replicate_count 'count'.
choices        imaging_mode 'widefield', 'confocal', 'tirf', 'super_resolution' or None: kept in the record for the reviewer; no criterion rests on a choice (a choice holds no span
               in the merged record). The system is therefore two FACTS, heterologous_host and purified_proteins, each with the span of its quote.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (imaging_mode), None when the choice is not stated.
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


VERSION = 'a105_colocalization_record'
EXPERIMENT_TYPE = 'colocalization'
QUANTITIES = ('objects_counted', 'fraction_colocalized', 'pearson_coefficient', 'enrichment_ratio', 'replicate_count')
PREPARATION_KEYS = ('component_a_preparation_ref', 'component_b_preparation_ref', 'dataset_ref')
IMAGING_MODES = ('widefield', 'confocal', 'tirf', 'super_resolution')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'colocalization_observed': YES_NO, 'unrelated_protein_not_recruited': YES_NO, 'lost_without_partner': YES_NO, 'lost_with_binding_region_removed': YES_NO, 'follows_partner_when_moved': YES_NO, 'heterologous_host': YES_NO, 'purified_proteins': YES_NO, 'expressed_near_native_level': YES_NO, 'fusion_functional': YES_NO, 'quantified_over_many_cells': YES_NO, 'independent_experiments': YES_NO}

COUNT = 'count'
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'objects_counted': (COUNT,), 'fraction_colocalized': ('percent',), 'pearson_coefficient': ('ratio',), 'enrichment_ratio': ('ratio',), 'replicate_count': (COUNT,)}
