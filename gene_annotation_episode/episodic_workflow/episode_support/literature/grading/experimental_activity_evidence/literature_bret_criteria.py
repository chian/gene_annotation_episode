"""BRET criteria: the ONE place where the BRET / NanoBRET grader's criteria are declared (bioluminescence resonance energy transfer in cells: a luciferase donor on one protein, a fluorescent acceptor or tracer on the other; a saturation titration over the acceptor-to-donor ratio gives BRETmax and BRET50, a tracer titration or displacement gives an apparent KD or Ki).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the BRET grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the BRET50 of the negative control over that of the pair, the BRET ratio of the pair over that of the control,
the number of titration points, the range of the titration relative to BRET50, the R squared of the fit, the replicate count), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_bret_converter.py.
The logic that answers each question is in literature_bret_grader.py (one short function per criterion, same order). The only constants left
here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in BRET_CRITERIA
-------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_bret_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet.

Support rule: a criterion returns 'supported' or 'conflicting' only with support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' or
'not_applicable' with a declared reason, never 'supported' and never 'conflicting'. The choices of the record (format, donor, acceptor, expression, spread kind) hold no span, so no
criterion rests on a choice alone; the one use of a choice is that a run stated as a saturation titration or as a ligand-induced change is 'not_applicable' for the competition criterion when its fact is not stated
('not_a_competition_run'), and a run stated as a competition or a ligand-induced change is 'not_applicable' for the saturation criterion when its fact is not stated ('not_a_saturation_run'), declared reasons that decide nothing about the experiment's quality.

What the claim is. The experiment is judged by how well it supports "these two proteins are in proximity in cells by a specific interaction, not by random collision of over-expressed proteins". A BRET signal alone shows
proximity only; the saturation curve, a BRET50 well below that of a negative control pair, a BRET ratio well above the control, the donor-only and acceptor-only controls, matched expression, swapped fusions and a displaced tracer decide how much it means.

Terms. BRET50: the acceptor-to-donor ratio at half of BRETmax. Negative control over pair BRET50: BRET50 of the negative control pair divided by BRET50 of the pair under test (above 1 when the control needs more acceptor). Signal over control: the BRET ratio of the pair divided by the
BRET ratio of the negative control (both in ratio units; 1 mBU = 0.001 ratio). Low and high over BRET50: the lowest and the highest acceptor-to-donor ratio divided by BRET50.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): BRETmax alone, the tracer concentration, the apparent KD and Ki and their spread and kind, the format, the donor, the acceptor, the expression system and the statement that only this method was used.
"""

VERSION = 'a105_bret_criteria_v1'

# ---- Threshold constants -------------------------------------------------
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
RATIO_PER_SIGNAL_UNIT = {'ratio': 1.0, 'mBU': 0.001}  # FIXED_BY_DEFINITION: BRET ratio per signal unit (a milli BRET unit is one thousandth of a BRET ratio).


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


def _format_fact(criterion_id, question, fact_name, formats, reason):
    return {'id': criterion_id, 'question': question, 'reads': ('facts.' + fact_name,),
            'rule': 'The one fact decides: yes supported, no fails, not_applicable not applicable. An unknown fact is unknown, or not applicable when the format is stated as ' + ' or '.join(formats) + '.',
            'thresholds': (),
            'returns': (
                ('supported', 'facts_answered_yes', 'answer yes'),
                ('conflicting', 'fact_answered_no', 'answer no'),
                ('unknown', 'fact_unknown', 'answer unknown and the format is not stated as ' + ' or '.join(formats)),
                ('not_applicable', reason, 'answer unknown and the format is stated as ' + ' or '.join(formats)),
                ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
            )}


# ---- The criteria --------------------------------------------------------
BRET_CRITERIA = (
    _one_fact('interaction_observed', 'Did the BRET signal show the two proteins in proximity (a signal above that of the control)?', 'interaction_detected'),
    _format_fact('saturation_shown', 'Did the BRET ratio of the pair rise with the acceptor-to-donor ratio as a saturation curve (not a straight line)?', 'saturation_shown', ('competition_displacement', 'ligand_induced_change'), 'not_a_saturation_run'),
    {
        'id': 'bret50_specificity',
        'question': 'Is the BRET50 of the pair far below that of the negative control pair?',
        'reads': ('quantities.bret50', 'quantities.bret50_negative_control'),
        'rule': 'When the BRET50 of the pair and the BRET50 of the negative control are both stated, the grader records the quotient control over pair (bret50_control_over_pair) and the refs of the two (bret50_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'bret50_comparison_recorded_for_the_sheet', 'both BRET50 values are stated: the quotient is recorded and the sheet judges it'),
            ('unknown', 'bret50_comparison_not_given', 'the two BRET50 values are not both stated'),
        ),
    },
    {
        'id': 'signal_over_control',
        'question': 'Is the BRET ratio of the pair well above that of the negative control?',
        'reads': ('quantities.bret_ratio_pair', 'quantities.bret_ratio_negative_control'),
        'rule': 'When the BRET ratio of the pair and that of the negative control are both stated, the grader records the quotient pair over control in ratio units (signal_over_control) and the refs of the two (signal_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('RATIO_PER_SIGNAL_UNIT',),
        'returns': (
            ('unknown', 'signal_over_control_recorded_for_the_sheet', 'both BRET ratios are stated: the quotient is recorded and the sheet judges it'),
            ('unknown', 'signal_over_control_not_given', 'the two BRET ratios are not both stated'),
        ),
    },
    _one_fact('donor_only_control', 'Was the donor expressed alone and its signal in the acceptor channel measured?', 'donor_only_control_done'),
    _one_fact('acceptor_only_control', 'Was the acceptor expressed alone as a control?', 'acceptor_only_control_done'),
    {
        'id': 'negative_control',
        'question': 'Did a non-interacting pair, run in the same way, give no specific signal?',
        'reads': ('facts.negative_control_pair_used', 'facts.negative_control_no_specific_signal'),
        'rule': 'Shared fact rule over the two facts: any no fails (a control not run, or a control that also gave a specific signal); else any unknown is unknown; else yes supported. The refs are those of the facts that decide.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'both facts are yes'),
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'fact_unknown', 'no fact is no and one is unknown'),
            ('not_applicable', 'fact_not_applicable', 'all facts are not_applicable'),
        ),
    },
    _one_fact('expression_matching', 'Were the donor luminescence and the acceptor fluorescence measured in the same cells, to give the acceptor-to-donor ratio?', 'expression_levels_measured'),
    {
        'id': 'titration_points',
        'question': 'Was the titration run at enough acceptor-to-donor ratios (or tracer concentrations) to define a curve?',
        'reads': ('quantities.titration_point_count',),
        'rule': 'A stated number of points is recorded (titration_point_count, titration_refs) and the judgement is left to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'titration_point_count_recorded_for_the_sheet', 'a count is stated: it is recorded and the sheet judges it'),
            ('unknown', 'titration_point_count_not_given', 'no count is stated'),
        ),
    },
    {
        'id': 'ratio_range',
        'question': 'Did the acceptor-to-donor ratios run from well below to well above BRET50 (so that BRETmax and BRET50 are defined by the data)?',
        'reads': ('quantities.ratio_lowest', 'quantities.ratio_highest', 'quantities.bret50'),
        'rule': 'With no BRET50 reported the criterion does not apply. When the lowest ratio, the highest ratio and BRET50 are all stated, the grader records the two quotients (low_over_bret50, high_over_bret50) and the refs of the three (range_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'ratio_range_recorded_for_the_sheet', 'BRET50 is reported and both ends of the range are stated: the quotients are recorded and the sheet judges them'),
            ('unknown', 'ratio_range_not_given', 'BRET50 is reported and the two ends of the range are not both stated'),
            ('not_applicable', 'no_bret50_reported', 'no BRET50 is reported'),
        ),
    },
    _format_fact('competition', 'Did an unlabelled competitor lower the tracer signal in a concentration-dependent way?', 'tracer_displaced_by_competitor', ('saturation_titration', 'ligand_induced_change'), 'not_a_competition_run'),
    _one_fact('orientation', 'Were both fusion orientations (donor and acceptor positions) tried?', 'fusion_orientation_swapped'),
    _one_fact('background_correction', 'Was the background BRET (donor only or no acceptor) subtracted?', 'background_subtracted'),
    {
        'id': 'fit_quality',
        'question': 'Does the fit describe the data (a high R squared)?',
        'reads': ('quantities.fit_r_squared',),
        'rule': 'A stated R squared is recorded (fit_r_squared, fit_refs) and the judgement is left to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'fit_r_squared_recorded_for_the_sheet', 'an R squared is stated: it is recorded and the sheet judges it'),
            ('unknown', 'fit_r_squared_not_given', 'no R squared is stated'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Wells of one plate are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
