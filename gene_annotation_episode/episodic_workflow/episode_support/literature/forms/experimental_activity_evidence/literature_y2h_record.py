"""The extracted record of ONE yeast two-hybrid (Y2H) experiment: a pairwise interaction test of two proteins in yeast. One protein (the bait) is fused to a DNA-binding domain (GAL4 or LexA), the other (the prey) to a transcription activation domain; if the two proteins interact they bring the two domains together and a reporter gene is activated. The reporter is read as GROWTH on selective medium (a medium without histidine and/or adenine, with or without the inhibitor 3-amino-1,2,4-triazole, 3-AT, which raises the stringency of the HIS3 selection) or as lacZ / beta-galactosidase activity (a colony-lift filter assay, or a liquid assay in Miller units). The yeast one-hybrid (Y1H: a protein-DNA interaction, a DNA bait upstream of a reporter and a prey that is an activation-domain fusion) and the yeast three-hybrid (Y3H: an RNA or small-molecule bridge) belong to the form only where a passage reports a pairwise interaction test of this kind; the choice 'system_kind' says which. The result is QUALITATIVE or semi-quantitative (growth or no growth, a growth score, a fold of the beta-galactosidase activity over a control): it reports NO binding constant, and an interaction-strength number such as Miller units is not a dissociation constant.

What a leaf extraction holds for one Y2H experiment: the bait and the prey constructs (the fusion domains, in the orientation tested), the yeast strain, the reporter that was scored and the selective medium it was scored on (and the 3-AT concentration), the incubation temperature and time, and the controls. The controls of a Y2H are what make it mean something: the bait with the empty prey vector and the prey with the empty bait vector must not activate the reporter (autoactivation: a bait that activates alone gives a false positive), an unrelated protein or a non-binding mutant in place of one partner must be negative, a known interacting pair must be positive (the system works), all the pairs must grow on non-selective medium (both plasmids are present and the yeast is alive), the interaction should hold when bait and prey are swapped (the reciprocal orientation), more than one reporter should agree, and the fusion proteins should be shown to be expressed.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What Y2H shows and what can go wrong is what the form keeps. A Y2H is a test in a heterologous host: growth does not show a direct interaction (a bridging yeast protein can connect two proteins that do not touch), nor that the proteins meet where they live. A bait that activates the reporter alone (autoactivation) makes every growing pair a false positive; 3-AT is titrated against it. A prey that activates alone, a sticky prey that interacts with unrelated baits, a fusion that is not expressed or does not fold or reach the nucleus (a negative result is then no evidence of no interaction), and a reporter that is leaky (a HIS3 reporter grows weakly without interaction) are the usual faults. So the result is judged by the controls, by whether more than one reporter agrees, and, where a beta-galactosidase activity is given, by how far it is above the negative control.

Record fields
-------------
version, experiment_type ('y2h'), experiment_ref, source_ref, assertion_ref
preparations   bait_preparation_ref, prey_preparation_ref, dataset_ref: each a string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them
               to the merger as its dependence keys (the prey as the analyte key, the bait as the other partner; there is no surface).
quantities     three_at_concentration, bait_alone_three_at_concentration, beta_galactosidase_interaction, beta_galactosidase_interaction_sd, beta_galactosidase_interaction_sem, beta_galactosidase_negative_control,
               beta_galactosidase_negative_control_sd, beta_galactosidase_negative_control_sem, beta_galactosidase_positive_control, growth_dilution_interaction, growth_dilution_negative_control,
               incubation_temperature, incubation_time, replicate_count: one operand each.
               Units: three_at_concentration 'mM' (the 3-AT concentration of the selective medium on which the pair was scored) and bait_alone_three_at_concentration 'mM' (the 3-AT concentration of the medium on which the bait alone,
               with the empty prey vector, was tested for autoactivation; kept so the sheet can see whether the autoactivation test was at least as permissive as the scoring); beta_galactosidase_interaction, beta_galactosidase_negative_control and
               beta_galactosidase_positive_control 'Miller_units' (the lacZ activity of the bait-prey pair tested, of the negative control pair, and of the positive control pair); the _sd and _sem fields of the pair and of the negative control 'Miller_units' (the stated
               spread of that activity; the SD and the SEM are SEPARATE fields because they differ by sqrt(n) and the passage says which one it gives; kept so the sheet can judge the fold against the paper's own noise);
               growth_dilution_interaction and growth_dilution_negative_control 'dilution_factor' (for a growth read-out on a dilution series or spot assay: the dilution factor of the most dilute spot of the pair, or of the negative control, that still
               shows growth on the scored medium, 1 for undiluted, 1000 for 10^-3; kept so a growth-only paper can be judged as a titre difference); incubation_temperature 'C' or 'K';
               incubation_time 'h' or 'days' (the incubation of the plates or cultures before the reporter is scored); replicate_count 'count'.
system_kind    'y2h', 'y1h', 'y3h' or None: which hybrid system the passage reports. Kept in the record for the reviewer.
bait_fusion_domain 'gal4_dbd', 'lexa_dbd', 'other' or None: the DNA-binding domain of the bait fusion. Kept in the record for the reviewer.
prey_fusion_domain 'gal4_ad', 'b42_ad', 'vp16_ad', 'other' or None: the activation domain of the prey fusion. Kept in the record for the reviewer.
yeast_strain   'ah109', 'y2hgold', 'pj69_4a', 'l40', 'egy48', 'other' or None: the reporter strain. Kept in the record for the reviewer.
selective_medium_scored 'minus_histidine', 'minus_adenine', 'minus_histidine_and_adenine', 'other' or None: the selective medium on which the interaction was scored by growth. Kept in the record for the reviewer.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (system_kind, bait_fusion_domain, prey_fusion_domain, yeast_strain, selective_medium_scored), None when the choice is not stated.
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


VERSION = 'a105_y2h_record'
EXPERIMENT_TYPE = 'y2h'
QUANTITIES = ('three_at_concentration', 'bait_alone_three_at_concentration', 'beta_galactosidase_interaction', 'beta_galactosidase_interaction_sd', 'beta_galactosidase_interaction_sem', 'beta_galactosidase_negative_control', 'beta_galactosidase_negative_control_sd', 'beta_galactosidase_negative_control_sem', 'beta_galactosidase_positive_control', 'growth_dilution_interaction', 'growth_dilution_negative_control', 'incubation_temperature', 'incubation_time', 'replicate_count')
PREPARATION_KEYS = ('bait_preparation_ref', 'prey_preparation_ref', 'dataset_ref')
SYSTEM_KINDS = ('y2h', 'y1h', 'y3h')
BAIT_FUSION_DOMAINS = ('gal4_dbd', 'lexa_dbd', 'other')
PREY_FUSION_DOMAINS = ('gal4_ad', 'b42_ad', 'vp16_ad', 'other')
YEAST_STRAINS = ('ah109', 'y2hgold', 'pj69_4a', 'l40', 'egy48', 'other')
SELECTIVE_MEDIA = ('minus_histidine', 'minus_adenine', 'minus_histidine_and_adenine', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'interaction_detected': YES_NO, 'bait_alone_inactive': YES_NO, 'prey_alone_inactive': YES_NO, 'non_interacting_control_done': YES_NO, 'positive_control_done': YES_NO, 'reciprocal_orientation_tested': YES_NO, 'nonselective_growth_shown': YES_NO, 'fusion_expression_verified': YES_NO, 'more_than_one_reporter_activated': YES_NO, 'independent_experiments': YES_NO}

# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'three_at_concentration': ('mM',), 'bait_alone_three_at_concentration': ('mM',), 'beta_galactosidase_interaction': ('Miller_units',), 'beta_galactosidase_interaction_sd': ('Miller_units',), 'beta_galactosidase_interaction_sem': ('Miller_units',), 'beta_galactosidase_negative_control': ('Miller_units',), 'beta_galactosidase_negative_control_sd': ('Miller_units',), 'beta_galactosidase_negative_control_sem': ('Miller_units',), 'beta_galactosidase_positive_control': ('Miller_units',), 'growth_dilution_interaction': ('dilution_factor',), 'growth_dilution_negative_control': ('dilution_factor',), 'incubation_temperature': ('C', 'K'), 'incubation_time': ('h', 'days'), 'replicate_count': ('count',)}
