"""Proximity-labeling criteria: the ONE place where the proximity-labeling grader's criteria and thresholds are declared (a bait fused to a biotin ligase such as BioID or TurboID, or to the peroxidase APEX2, or a split version, biotinylates proteins within about 10 to 20 nm in living cells; the biotinylated proteins are captured on streptavidin and identified by western blot or mass spectrometry; a candidate partner is called proximal when it is enriched over a control: a free enzyme, an unrelated or differently localised bait, or no biotin or no peroxide; qualitative or semi-quantitative, no binding constant).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the proximity grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the fold enrichment, its false discovery rate, the expression of the fusion relative to the endogenous
bait, the replicate count), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_proximity_converter.py.
The logic that answers each question is in literature_proximity_grader.py (one short function per criterion, same order). The only constants left
here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in PROXIMITY_CRITERIA
------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_proximity_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Support rule: a criterion returns 'supported' or 'conflicting' only with support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown'
or 'not_applicable' with a declared reason, never 'supported' and never 'conflicting'. The choices of the record (enzyme, fusion site, cell system, readout, quantification) hold no span, so no criterion
rests on a choice.

What the claim is. The experiment is judged by how well it supports "the candidate is proximal to the bait in living cells" (an enrichment over the control, with a statistic and
replicates). Proximity is not direct binding, so the claim that the experiment supports is a proximity, and no criterion asks for a binding constant. The controls (a free enzyme, no labelling, an unrelated
bait), the checks (the fusion expressed near the endogenous level and localised like the endogenous bait; biotinylation that depends on the fusion; capture on streptavidin) and an independent
validation decide how much the proximity means.

Terms. Fold enrichment: the abundance of the candidate in the bait sample over the control (a ratio; a value given as a base-2 logarithm is converted by 2 to the power). False discovery rate: in percent (a fraction is
converted by 100). Expression ratio: the fusion over the endogenous bait.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the enzyme, the fusion site, the cell system, the readout, the quantification, the labelling time and the biotin and the
peroxide concentration.
"""

VERSION = 'a105_proximity_criteria_v1'

# ---- Threshold constants -------------------------------------------------
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: percent per unit fraction (a false discovery rate given as a fraction is recorded in percent).
LOG2_BASE = 2.0  # FIXED_BY_DEFINITION: the base of the logarithm of an enrichment given as log2 ratio (ratio = 2 to the power of the value).


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
PROXIMITY_CRITERIA = (
    {
        'id': 'proximity_observed',
        'question': 'Does the experiment state whether the candidate was enriched over the control (found in proximity to the bait)?',
        'reads': ('facts.candidate_enriched',),
        'rule': 'The criterion asks whether the result is stated, not whether it is positive: yes AND no are both a stated result (supported; the direction, detected or not detected, travels as the qualitative statement of the experiment), so a well-run experiment that finds the candidate NOT proximal is not penalised for its result. unknown stays unknown, not_applicable stays not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'candidate_enrichment_stated', 'answer yes or no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'enrichment_magnitude',
        'question': 'Was the candidate enriched over the control by at least the minimum fold?',
        'reads': ('quantities.enrichment_fold', 'facts.candidate_enriched', 'facts.fold_over_matched_control'),
        'rule': 'A candidate stated NOT enriched has no magnitude to judge: not applicable. Otherwise, when the fold enrichment is stated, the grader records it as a ratio (fold_enrichment; a log2 value is converted by 2 to the power) and its refs (fold_refs), together with whether the control was matched to the bait (fold_matched_control: the answer of the fact fold_over_matched_control, yes, no or unknown), and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('LOG2_BASE',),
        'returns': (
            ('not_applicable', 'candidate_stated_not_enriched', 'the candidate is stated not enriched (the fact candidate_enriched is no)'),
            ('unknown', 'enrichment_fold_recorded_for_the_sheet', 'the fold enrichment is stated: it is recorded and the sheet judges it'),
            ('unknown', 'enrichment_fold_not_given', 'no fold enrichment is stated'),
        ),
    },
    {
        'id': 'enrichment_significance',
        'question': 'Is the enrichment statistically supported (a false discovery rate low enough)?',
        'reads': ('quantities.enrichment_fdr', 'facts.statistical_test_used', 'facts.candidate_enriched'),
        'rule': 'A candidate stated NOT enriched has no enrichment to support: not applicable. Otherwise a statistical test stated as not used fails (a fact). Otherwise a stated false discovery rate is recorded in percent (fdr_percent, fdr_refs) and the judgement is left to the sheet; with no rate the fact decides: yes supported, unknown unknown, not_applicable not applicable.',
        'thresholds': ('PERCENT_PER_FRACTION',),
        'returns': (
            ('not_applicable', 'candidate_stated_not_enriched', 'the candidate is stated not enriched (the fact candidate_enriched is no)'),
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'enrichment_fdr_recorded_for_the_sheet', 'the fact is not no and a rate is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, no rate is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no rate is stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no rate is stated and the fact is not_applicable'),
        ),
    },
    _one_fact('ligase_only_control', 'Was the enzyme without the bait (a free ligase or peroxidase) run as a control?', 'ligase_only_control'),
    _one_fact('unlabeled_control', 'Was a control without labelling (no biotin, or no peroxide) run?', 'unlabeled_control'),
    _one_fact('unrelated_bait_control', 'Was the enzyme fused to an unrelated protein, or to a protein that sends it to a different compartment, run as a control?', 'unrelated_bait_control'),
    _one_fact('biotinylation_dependence', 'Was biotinylation shown to depend on the fusion and the labelling?', 'biotinylation_confirmed'),
    _one_fact('streptavidin_capture', 'Were the biotinylated proteins captured on streptavidin before identification?', 'streptavidin_capture'),
    {
        'id': 'expression_level',
        'question': 'Was the fusion expressed close to the endogenous level of the bait?',
        'reads': ('quantities.bait_expression_ratio', 'facts.bait_expression_checked'),
        'rule': 'A check stated as not done fails (a fact). Otherwise a stated expression ratio is recorded (expression_ratio, expression_refs) and the judgement is left to the sheet; with no ratio the fact decides: yes supported, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'expression_ratio_recorded_for_the_sheet', 'the fact is not no and a ratio is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, no ratio is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no ratio is stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no ratio is stated and the fact is not_applicable'),
        ),
    },
    _one_fact('localization', 'Was the fusion shown to localise like the endogenous bait?', 'bait_localization_checked'),
    _one_fact('orthogonal_validation', 'Was the proximity of the candidate confirmed by an independent method?', 'orthogonal_validation'),
    {
        'id': 'replicates',
        'question': 'How many independent experiments were there (the sheet gives full credit from the researched number and partial credit below it)?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Lanes and injections of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
