"""The extracted record of ONE pull-down or co-immunoprecipitation (co-IP) experiment: a qualitative to semi-quantitative interaction assay in which a tagged or antibody-captured bait is held on beads from a lysate or from purified proteins, the beads are washed, the captured material is eluted and the prey is detected in the eluate by western blot or mass spectrometry. It includes GST, His and streptavidin pull-downs and endogenous or overexpressed co-IP.

What a leaf extraction holds for one pull-down or co-IP experiment: a bait (a protein carrying an affinity tag, for example GST, His, Strep, FLAG, HA or Myc, or a protein captured by its own antibody on protein A or protein G beads, or a biotinylated protein on streptavidin beads) is incubated with a source of the prey (purified recombinant protein, a cell lysate or a tissue lysate; the proteins overexpressed or at their endogenous levels), the beads are washed (the salt and the detergent of the wash set how strong an interaction must be to survive), the bound material is eluted and the prey is looked for in the eluate (by western blot, mass spectrometry, fluorescence or autoradiography). The result is mostly a statement (the prey was or was not detected in the eluate of the specific capture) and sometimes a semi-quantitative number (the relative band intensity or fold enrichment over the control, the percent of the input recovered); it is NOT a dissociation constant, and the record has no KD: nothing here is a binding constant.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand and SPA records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What a pull-down shows and what it does not, and what can go wrong, is what the form keeps. The controls are the evidence: the prey must be in the eluate of the specific capture and absent from a bead-only or tag-only control (GST alone, an empty vector, an isotype IgG), and the prey must not bind the beads alone (the control without the bait); the input lane shows that the prey was present in the material applied; a positive control (a known interacting pair, or the prey with a bait known to bind it, taken through the same wash and detection) that gives its expected band shows that a missing prey is a real absence and not a failed wash, blot or antibody; a reciprocal pull-down (the former prey as the bait) makes a tag artefact unlikely; competition with untagged protein or a mutant that disrupts the interaction shows specificity; an interaction that survives a nuclease (benzonase, RNase, DNase) is not bridged by nucleic acid; a knockout or knockdown control shows that the antibody or tag detects the right protein. A lysate co-IP shows association in a complex, not direct binding: only purified proteins show a direct interaction. Overexpression and tags can create an interaction that does not exist at the endogenous levels; sticky preys bind beads and walls whatever the bait is, so the salt and detergent of the wash and the number of washes decide how much the survival of the prey means; crosslinking holds transient or indirect partners together and so lowers what a surviving prey says about the wash. The replicates are independent experiments.

Record fields
-------------
version, experiment_type ('pulldown'), experiment_ref, source_ref, assertion_ref
preparations   bait_preparation_ref (the captured protein), prey_preparation_ref (the protein looked for in the eluate), dataset_ref: each a string or
               None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the merger as
               its dependence keys (the prey as the analyte key, the bait as the other partner; there is no surface).
quantities     fold_enrichment, fold_enrichment_sd, fold_enrichment_sem, percent_input_recovered, input_fraction, nacl_wash, detergent_wash, wash_count, incubation_time, incubation_temperature,
               replicate_count: one operand each.
               Units: fold_enrichment 'ratio' (the prey signal of the specific capture over the prey signal of the control capture); fold_enrichment_sd and
               fold_enrichment_sem 'ratio' (the stated standard deviation, or standard error of the mean, of that fold across the repeats, in fold units; two
               fields because the two spreads differ by sqrt(n) and the passage says which one it gives); percent_input_recovered
               'percent' (the prey recovered in the eluate as a percent of the input); input_fraction 'percent' (the part of the lysate or protein applied
               that is loaded as the input lane); nacl_wash 'mM' or 'M' (the sodium chloride of the wash buffer); detergent_wash 'percent' (the detergent of
               the wash buffer); wash_count 'count'; incubation_time 's', 'min' or 'h' (bait with prey); incubation_temperature 'C' or 'K';
               replicate_count 'count' (independent experiments).
detection_method
               'western_blot', 'mass_spectrometry', 'fluorescence', 'autoradiography', 'other' or None: how the prey was detected in the eluate.
capture_format 'gst', 'his', 'strep', 'flag', 'ha', 'myc', 'antibody' (an antibody against the bait, usually on protein A or protein G beads), 'biotin_streptavidin',
               'other' or None: how the bait is held on the beads.
protein_source 'purified_recombinant', 'cell_lysate', 'tissue_lysate', 'other' or None: what the prey came from. Kept in the record for the reviewer.
nuclease_treatment
               'benzonase', 'rnase', 'dnase', 'rnase_and_dnase', 'other' or None: the nuclease the lysate or the reaction was treated with. Kept in the
               record for the reviewer; the fact interaction_survives_nuclease is what is judged.
crosslinker    'formaldehyde', 'dsp', 'other', 'none' or None: the crosslinker used before capture ('none' only when the source says none was used).
               Kept in the record for the reviewer.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (detection_method, capture_format, protein_source, nuclease_treatment, crosslinker),
               None when the choice is not stated.
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


VERSION = 'a105_pulldown_record_v1'
EXPERIMENT_TYPE = 'pulldown'
QUANTITIES = ('fold_enrichment', 'fold_enrichment_sd', 'fold_enrichment_sem', 'percent_input_recovered', 'input_fraction', 'nacl_wash', 'detergent_wash', 'wash_count', 'incubation_time', 'incubation_temperature', 'replicate_count')
PREPARATION_KEYS = ('bait_preparation_ref', 'prey_preparation_ref', 'dataset_ref')
DETECTION_METHODS = ('western_blot', 'mass_spectrometry', 'fluorescence', 'autoradiography', 'other')
CAPTURE_FORMATS = ('gst', 'his', 'strep', 'flag', 'ha', 'myc', 'antibody', 'biotin_streptavidin', 'other')
PROTEIN_SOURCES = ('purified_recombinant', 'cell_lysate', 'tissue_lysate', 'other')
NUCLEASE_TREATMENTS = ('benzonase', 'rnase', 'dnase', 'rnase_and_dnase', 'other')
CROSSLINKERS = ('formaldehyde', 'dsp', 'other', 'none')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'prey_detected_in_eluate': YES_NO, 'negative_control_done': YES_NO, 'prey_absent_in_negative_control': YES_NO, 'positive_control_detected': YES_NO, 'bait_minus_control_done': YES_NO, 'input_lane_shown': YES_NO, 'reciprocal_done': YES_NO, 'competition_disrupts_interaction': YES_NO, 'interaction_survives_nuclease': YES_NO, 'direct_interaction_shown': YES_NO, 'endogenous_expression_levels': YES_NO, 'quantification_with_normalization': YES_NO, 'specificity_validated': YES_NO, 'independent_experiments': YES_NO}

TIME_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'fold_enrichment': ('ratio',), 'fold_enrichment_sd': ('ratio',), 'fold_enrichment_sem': ('ratio',), 'percent_input_recovered': ('percent',), 'input_fraction': ('percent',), 'nacl_wash': ('mM', 'M'), 'detergent_wash': ('percent',), 'wash_count': ('count',), 'incubation_time': TIME_UNITS, 'incubation_temperature': ('C', 'K'), 'replicate_count': ('count',)}
