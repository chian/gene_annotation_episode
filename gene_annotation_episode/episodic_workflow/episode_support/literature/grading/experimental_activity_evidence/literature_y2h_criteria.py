"""Y2H criteria: the ONE place where the yeast two-hybrid (Y2H) grader's criteria and thresholds are declared (a pairwise interaction test in yeast: a bait fused to a DNA-binding domain and a prey fused to an activation domain activate a reporter, read as growth on selective medium or as beta-galactosidase activity, only if the two proteins interact; qualitative or semi-quantitative, no binding constant).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the Y2H grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the fold of the beta-galactosidase activity of the pair over the negative control, the replicate count), the grader records
the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_y2h_converter.py.
The logic that answers each question is in literature_y2h_grader.py (one short function per criterion, same order). This file holds no constants: a Y2H needs no unit conversion
(the beta-galactosidase activities are all in Miller units; the fold is a quotient).

How to read an entry in Y2H_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_y2h_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses (none for Y2H)
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Support rule (from the ELISA work, designed in from the start): a criterion returns 'supported' or 'conflicting' only with
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' or 'not_applicable' with a
declared reason, never 'supported' and never 'conflicting'. The choices of the record (system kind, fusion domains, yeast strain, selective medium) hold no span, so no
criterion rests on a choice, and none reads one.

What the claim is. The experiment is judged by how well it supports "these two proteins interact (in yeast)": the pair activated the reporter. The controls (the bait alone and the prey alone inactive, an unrelated or non-binding
partner negative, a positive control that works, growth on non-selective medium, the expression of the fusions, the reciprocal orientation, more than one reporter) decide how much that means, and a beta-galactosidase activity of the pair is
judged by its fold over the negative control. A Y2H reports no KD, so no criterion needs one; the result is qualitative.

Terms. Fold over the control: the beta-galactosidase activity of the pair tested divided by that of the negative control, both in Miller units. Autoactivation: the activation of the reporter by the bait (or the prey) alone, which makes every
growing pair a false positive. Reciprocal orientation: the same two proteins tested with bait and prey swapped. Non-selective growth: growth on a medium that selects only the two plasmids.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the 3-AT concentration, the beta-galactosidase activity of the positive control, the incubation temperature and time, the hybrid system, the
fusion domains, the yeast strain and the selective medium.
"""

VERSION = 'a105_y2h_criteria_v1'


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


# ---- The criteria --------------------------------------------------------
Y2H_CRITERIA = (
    _one_fact('interaction_observed', 'Did the pair of bait and prey activate the reporter (growth on selective medium or beta-galactosidase activity)?', 'interaction_detected'),
    _one_fact('bait_autoactivation', 'Was the bait alone (with the empty prey vector) inactive, so that it does not activate the reporter by itself?', 'bait_alone_inactive'),
    _one_fact('prey_autoactivation', 'Was the prey alone (with the empty bait vector) inactive?', 'prey_alone_inactive'),
    _one_fact('non_interacting_control', 'Did an unrelated protein or a non-binding mutant in place of one partner stay inactive?', 'non_interacting_control_done'),
    _one_fact('positive_control', 'Did a known interacting pair activate the reporter, so that the system worked?', 'positive_control_done'),
    _one_fact('reciprocal_orientation', 'Was the interaction also seen with bait and prey swapped?', 'reciprocal_orientation_tested'),
    _one_fact('nonselective_growth', 'Did the pair grow on non-selective medium (both plasmids present, cells alive)?', 'nonselective_growth_shown'),
    _one_fact('expression_verified', 'Was the expression of the bait and of the prey fusion shown in yeast?', 'fusion_expression_verified'),
    _one_fact('reporter_concordance', 'Did the pair activate more than one reporter?', 'more_than_one_reporter_activated'),
    {
        'id': 'reporter_fold',
        'question': 'Was the beta-galactosidase activity of the pair far enough above that of the negative control?',
        'reads': ('quantities.beta_galactosidase_interaction', 'quantities.beta_galactosidase_negative_control'),
        'rule': 'The grader holds no threshold for the fold. When the activity of the pair and the activity of the negative control are both stated, it records the fold (reporter_fold = pair / negative control) and the refs of the two (reporter_fold_refs) and leaves the judgement to the sheet; otherwise unknown. No fact decides it.',
        'thresholds': (),
        'returns': (
            ('unknown', 'reporter_fold_recorded_for_the_sheet', 'both activities are stated: the fold is recorded and the sheet judges it'),
            ('unknown', 'reporter_fold_not_given', 'the two activities are not both stated'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Spots or colonies of one plate are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
