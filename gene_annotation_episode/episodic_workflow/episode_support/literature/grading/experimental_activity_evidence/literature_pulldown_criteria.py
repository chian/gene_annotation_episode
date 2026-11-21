"""Pull-down / co-IP criteria: the ONE place where the pull-down and co-immunoprecipitation grader's criteria and thresholds are declared (a tagged or antibody-captured bait on beads from a lysate or from purified proteins, wash, elution, detection of the prey by western blot or mass spectrometry; qualitative to semi-quantitative).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the pull-down grader asks. The grader reports FACTS and holds NO threshold
that judges goodness: where a criterion needs a number to be compared with a limit (the salt and the detergent of the wash, the number of
washes, the incubation time, the fold enrichment, the replicate count, the spread of the fold), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_pulldown_converter.py. The logic that answers each question is in literature_pulldown_grader.py (one short function per criterion,
same order). The only constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in PULLDOWN_CRITERIA
-----------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_pulldown_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Support rule (from the ELISA work, designed in from the start): a criterion returns 'supported' or 'conflicting' only with
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' with a declared
reason, never 'supported' and never 'conflicting'.

What the claim is. The experiment is judged by how well it supports "these two proteins interact, directly or in a complex". It
reports no binding constant (no KD): a pull-down or co-immunoprecipitation says whether the prey was found with the bait, and the
controls and the stringency of the wash decide how much that means. A lysate co-IP shows association in a complex, not direct
binding, and the claim accepts that; so a direct interaction of purified proteins is a gain (it is judged), and its absence is
never a conflict.

Questions the owner may want to decide differently (all are rules here, not facts of nature): an overexpressed or tagged protein
is called a conflict of the endogenous-levels criterion (the artefact risk is real but an overexpression pull-down can still be
right); a prey found in the negative control is a conflict; an interaction lost after a nuclease treatment is a conflict (it was
bridged by nucleic acid, which does not support a protein-protein interaction).

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the percent of the input recovered
(true interactions are often recovered at well under one percent, so no limit is safe), the input fraction, the temperature of the
incubation, the detection method, the way the bait is captured, the source of the prey, the nuclease named and the crosslinker.
"""

VERSION = 'a105_pulldown_criteria_v1'

# ---- Threshold constants -------------------------------------------------
MM_PER_UNIT = {'mM': 1.0, 'M': 1000.0}  # FIXED_BY_DEFINITION: millimolar per concentration unit.
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.


def _fact_returns():
    return (
        ('supported', 'facts_answered_yes', 'answer yes'),
        ('conflicting', 'fact_answered_no', 'answer no'),
        ('unknown', 'fact_unknown', 'answer unknown'),
        ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
    )


def _one_fact(criterion_id, question, fact_name):
    return {'id': criterion_id, 'question': question, 'reads': ('facts.' + fact_name,),
            'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
            'thresholds': (), 'returns': _fact_returns()}


def _recorded_rule(criterion_id, question, quantity, rule, recorded, unknown):
    return {'id': criterion_id, 'question': question, 'reads': ('quantities.' + quantity,), 'rule': rule, 'thresholds': (),
            'returns': (('unknown', recorded[0], recorded[1]), ('unknown', unknown[0], unknown[1]), ('not_applicable', 'never', 'never returned'))}


# ---- The criteria --------------------------------------------------------
PULLDOWN_CRITERIA = (
    _one_fact('prey_in_eluate', 'Was the prey detected in the eluate of the specific capture?', 'prey_detected_in_eluate'),
    {
        'id': 'negative_control',
        'question': 'Was a bead-only, tag-only or isotype-antibody control capture done, and was the prey absent from it?',
        'reads': ('facts.negative_control_done', 'facts.prey_absent_in_negative_control'),
        'rule': 'A prey found in the control fails; a control not done fails; otherwise a prey stated absent from the control is supported. Both not applicable is not applicable; anything else (a control done with its result not stated, or both unknown) is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'prey_absent_from_control', 'the prey is stated absent from the control and neither fact is no'),
            ('conflicting', 'prey_found_in_negative_control', 'the prey is stated present in the control'),
            ('conflicting', 'negative_control_not_done', 'the control is stated not done and the prey is not stated present in it'),
            ('unknown', 'negative_control_result_unknown', 'no fact is no and the absence of the prey is not stated'),
            ('not_applicable', 'fact_not_applicable', 'both facts not_applicable'),
        ),
    },
    {
        'id': 'positive_control',
        'question': 'Did a positive control (a known interacting pair, or the prey with a bait known to bind it) give its expected result under the same wash and detection, so that a prey that is missing from the eluate is a real absence?',
        'reads': ('facts.positive_control_detected',),
        'rule': 'A stated answer (yes or no) is recorded (positive_control, positive_control_refs) and the judgement is left to the sheet, because it matters only when the prey is not detected. unknown is unknown; not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('unknown', 'positive_control_recorded_for_the_sheet', 'the answer is yes or no: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('bait_minus_control', 'Was the prey incubated with the beads without the bait, to show that it does not bind the beads alone?', 'bait_minus_control_done'),
    _one_fact('input_lane', 'Was an input lane shown, so that the prey is known to have been in the material applied?', 'input_lane_shown'),
    _one_fact('reciprocal', 'Was the pull-down or co-immunoprecipitation done the other way round, with the prey as the bait, and did it find the interaction?', 'reciprocal_done'),
    _one_fact('competition', 'Did competition with untagged protein, or a mutant or deletion that disrupts the interaction, abolish or reduce the capture of the prey?', 'competition_disrupts_interaction'),
    _one_fact('nuclease', 'Did the interaction survive a nuclease treatment, so that it is not bridged by RNA or DNA?', 'interaction_survives_nuclease'),
    _one_fact('specificity', 'Was the specificity of the antibody or tag validated (a knockout or knockdown control)?', 'specificity_validated'),
    {
        'id': 'wash_stringency',
        'question': 'Were the beads washed with enough salt and detergent that a weakly or non-specifically bound prey would be lost?',
        'reads': ('quantities.nacl_wash', 'quantities.detergent_wash'),
        'rule': 'A stated sodium chloride (nacl_wash_mM, in mM, with nacl_wash_refs) and a stated detergent (detergent_percent, with detergent_wash_refs) are recorded and the judgement is left to the sheet. Neither stated is unknown.',
        'thresholds': ('MM_PER_UNIT',),
        'returns': (
            ('unknown', 'wash_recorded_for_the_sheet', 'at least one of the two is stated: it is recorded and the sheet judges it'),
            ('unknown', 'wash_stringency_not_given', 'neither the sodium chloride nor the detergent of the wash is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _recorded_rule('wash_count', 'Were the beads washed enough times?', 'wash_count', 'The stated number of washes is recorded (wash_count, wash_count_refs) and the judgement is left to the sheet. Not given is unknown.',
                   ('wash_count_recorded_for_the_sheet', 'a number of washes is stated: it is recorded and the sheet judges it'), ('wash_count_not_given', 'no number of washes is stated')),
    {
        'id': 'incubation',
        'question': 'Was the bait incubated with the prey long enough to capture it?',
        'reads': ('quantities.incubation_time',),
        'rule': 'The stated incubation time is recorded (incubation_min, in minutes, and incubation_refs) and the judgement is left to the sheet. Not given is unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('unknown', 'incubation_recorded_for_the_sheet', 'an incubation time is stated: it is recorded and the sheet judges it'),
            ('unknown', 'incubation_time_not_given', 'no incubation time is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _one_fact('expression_level', 'Were the interacting proteins at their endogenous levels, not overexpressed?', 'endogenous_expression_levels'),
    {
        'id': 'direct_interaction',
        'question': 'Was the interaction shown with purified proteins, so that it is direct and not only association in a complex?',
        'reads': ('facts.direct_interaction_shown',),
        'rule': 'Direct interaction stated supported. Anything else is unknown, never a conflict: the claim accepts association in a complex, so a lysate co-IP that shows no directness is not contradicted. not_applicable stays not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('unknown', 'direct_interaction_not_shown', 'answer no or unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'enrichment',
        'question': 'Was the prey signal in the specific capture high enough over the control, and large against its own stated spread?',
        'reads': ('quantities.fold_enrichment', 'quantities.fold_enrichment_sd', 'quantities.fold_enrichment_sem'),
        'rule': 'The stated fold enrichment over the control is recorded (fold_enrichment, fold_enrichment_refs) together with its stated standard deviation or standard error (fold_enrichment_sd, fold_enrichment_sem and their refs, None when not stated) and the judgement is left to the sheet. A spread without a fold is not recorded. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'fold_enrichment_recorded_for_the_sheet', 'a fold enrichment is stated: it is recorded (with the spread when stated) and the sheet judges it'),
            ('unknown', 'enrichment_not_given', 'no fold enrichment is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    _one_fact('quantification', 'Were the band intensities quantified and normalized?', 'quantification_with_normalization'),
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Lanes or wells of one experiment are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
