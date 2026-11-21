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

Gap pass 2026-11-21 (the range review's grader gaps): the stated spread of the two activities and the growth titre are now recorded for the sheet (reporter_fold, growth_titre); the 3-AT concentration of the bait-alone test is recorded beside the scoring's
(bait_autoactivation); a stated no of the positive control, of the reciprocal orientation and of the second reporter is recorded for the sheet instead of being conflicting (the form now asks 'no' only for a test that was done and went the other way); a stated
negative interaction is not_applicable here (the direction carries it).

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the beta-galactosidase activity of the positive control, the incubation temperature and time, the hybrid system, the
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
def _fact_handed_on(criterion_id, question, fact_name, no_reason, no_when, rule):
    """A one-fact criterion whose stated 'no' is a fact the grader records and the sheet judges (not conflicting here): the answer yes is supported, unknown unknown, not_applicable not applicable."""
    returns = tuple(r for r in _fact_returns() if r[1] != 'fact_answered_no') + (('unknown', no_reason, no_when),)
    return {'id': criterion_id, 'question': question, 'reads': ('facts.' + fact_name,), 'rule': rule, 'thresholds': (), 'returns': returns}


Y2H_CRITERIA = (
    {
        'id': 'interaction_observed',
        'question': 'Did the pair of bait and prey activate the reporter (growth on selective medium or beta-galactosidase activity)?',
        'reads': ('facts.interaction_detected',),
        'rule': 'yes is supported, unknown is unknown. A stated NO is the paper\'s negative statement: it is carried by the qualitative effect (the direction), and it is not evidence of poor quality, so here it is not_applicable (it used to be conflicting, which counted the statement twice: once as the direction and once as a failed quality criterion).',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('not_applicable', 'negative_statement_carried_by_the_direction', 'answer no: the statement goes to the qualitative effect, not to the quality'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'bait_autoactivation',
        'question': 'Was the bait alone (with the empty prey vector) inactive, so that it does not activate the reporter by itself?',
        'reads': ('facts.bait_alone_inactive', 'quantities.bait_alone_three_at_concentration', 'quantities.three_at_concentration'),
        'rule': 'The fact decides: no fails (the bait activates by itself), unknown is unknown, not_applicable is not applicable. Yes with the 3-AT concentration of the bait-alone test and of the scoring both stated: the grader records both (bait_alone_three_at_mM, scoring_three_at_mM and their refs) and the sheet judges whether the autoactivation test was as stringent as the scoring (a test at a higher 3-AT than the scoring shows less than it seems). Yes with either not stated: supported.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes and the two 3-AT concentrations are not both stated'),
            ('unknown', 'bait_alone_three_at_recorded_for_the_sheet', 'answer yes and both 3-AT concentrations are stated: recorded, the sheet judges them'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    _one_fact('prey_autoactivation', 'Was the prey alone (with the empty bait vector) inactive?', 'prey_alone_inactive'),
    _one_fact('non_interacting_control', 'Did an unrelated protein or a non-binding mutant in place of one partner stay inactive?', 'non_interacting_control_done'),
    _fact_handed_on('positive_control', 'Did a known interacting pair activate the reporter, so that the system worked?', 'positive_control_done',
                    'positive_control_failed_recorded_for_the_sheet', 'answer no (the known pair was tested and did not activate): the sheet judges what it means for this result',
                    'yes supported, unknown unknown, not_applicable not applicable. A stated NO (the known pair did not activate) is recorded (positive_control = no with its refs) and the sheet judges it: a system whose known pair fails cannot make a negative result mean anything, but it does not unmake an observed growth of the pair.'),
    _fact_handed_on('reciprocal_orientation', 'Was the interaction also seen with bait and prey swapped?', 'reciprocal_orientation_tested',
                    'one_orientation_only_recorded_for_the_sheet', 'answer no (the swapped orientation was tested and not seen): recorded, the sheet gives partial credit',
                    'yes supported, unknown unknown, not_applicable not applicable. A stated NO (seen in only one orientation) is recorded (reciprocal_orientation = no with its refs) and the sheet gives partial credit: many true pairs work in one orientation only.'),
    _one_fact('nonselective_growth', 'Did the pair grow on non-selective medium (both plasmids present, cells alive)?', 'nonselective_growth_shown'),
    _one_fact('expression_verified', 'Was the expression of the bait and of the prey fusion shown in yeast?', 'fusion_expression_verified'),
    _fact_handed_on('reporter_concordance', 'Did the pair activate more than one reporter?', 'more_than_one_reporter_activated',
                    'one_reporter_only_recorded_for_the_sheet', 'answer no (one reporter activated and another tested did not): recorded, the sheet gives partial credit',
                    'yes supported, unknown unknown, not_applicable not applicable. A stated NO (one reporter and not another that was tested) is recorded (more_than_one_reporter = no with its refs) and the sheet gives partial credit: one of the reporters agrees.'),
    {
        'id': 'reporter_fold',
        'question': 'Was the beta-galactosidase activity of the pair far enough above that of the negative control?',
        'reads': ('quantities.beta_galactosidase_interaction', 'quantities.beta_galactosidase_negative_control', 'quantities.beta_galactosidase_interaction_sd', 'quantities.beta_galactosidase_interaction_sem', 'quantities.beta_galactosidase_negative_control_sd', 'quantities.beta_galactosidase_negative_control_sem'),
        'rule': 'The grader holds no threshold for the fold. When the activity of the pair and the activity of the negative control are both stated, it records the fold (reporter_fold = pair / negative control) and the refs of the two (reporter_fold_refs), together with every spread the paper states for the two activities (activity_spread: the SD and the SEM of the pair and of the negative control, kept apart, and their refs), and leaves the judgement to the sheet. When they are not both stated but the growth titres of the pair and of the negative control are (see growth_titre), the growth titre is the paper\'s read-out and this criterion is not applicable; otherwise unknown. No fact decides it.',
        'thresholds': (),
        'returns': (
            ('unknown', 'reporter_fold_recorded_for_the_sheet', 'both activities are stated: the fold and its stated spread are recorded and the sheet judges them'),
            ('not_applicable', 'growth_titre_is_the_readout', 'the activities are not both stated and both growth titres are'),
            ('unknown', 'reporter_fold_not_given', 'neither the two activities nor the two growth titres are stated'),
        ),
    },
    {
        'id': 'growth_titre',
        'question': 'For a growth read-out on a dilution series, did the pair grow at a far higher dilution than the negative control?',
        'reads': ('quantities.growth_dilution_interaction', 'quantities.growth_dilution_negative_control'),
        'rule': 'The grader holds no threshold. When the most dilute spot with growth of the pair and of the negative control are both stated, it records the titre ratio (growth_titre = pair dilution factor / negative control dilution factor) and the refs of the two (growth_titre_refs) and leaves the judgement to the sheet. When they are not both stated but the two activities are, the activities are the paper\'s read-out and this criterion is not applicable; otherwise unknown. No fact decides it.',
        'thresholds': (),
        'returns': (
            ('unknown', 'growth_titre_recorded_for_the_sheet', 'both growth dilutions are stated: the titre ratio is recorded and the sheet judges it'),
            ('not_applicable', 'reporter_fold_is_the_readout', 'the growth dilutions are not both stated and both activities are'),
            ('unknown', 'growth_titre_not_given', 'neither the two growth dilutions nor the two activities are stated'),
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
