"""Split-reporter criteria: the ONE place where the split-reporter (protein-fragment complementation: split luciferase such as NanoBiT, split GFP / BiFC, split beta-lactamase, split TEV) grader's criteria and thresholds are declared (two fragments of a reporter are fused to the two candidate partners; when the partners come together the reporter is reconstituted and its signal reports proximity or interaction in cells, in a lysate or with purified proteins; a titration or a kinetic time course of a reversible reporter such as NanoBiT can give an apparent KD; otherwise the result is qualitative).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the split-reporter grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the signal over the background, the signal over the negative control, the number of fusion orientations, the number of titration concentrations, the titration range relative to the apparent KD, the replicate count), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_split_reporter_converter.py.
The logic that answers each question is in literature_split_reporter_grader.py (one short function per criterion, same order). The only constants left
here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in SPLIT_REPORTER_CRITERIA
-----------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_split_reporter_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet.

Support rule (from the ELISA work, designed in from the start): a criterion returns 'supported' or 'conflicting' only with
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' or 'not_applicable' with a
declared reason, never 'supported' and never 'conflicting'. The choices of the record (reporter system, assay system, readout mode, spread kind) hold no span, so no
criterion rests on a choice alone; they are kept in the record for the reviewer and decide nothing.

What the claim is. The experiment is judged by how well it supports "these two proteins interact (or are in close proximity) in this system" (a reconstituted signal above the background and above
the negative control, an apparent KD from a titration of a reversible reporter). The controls (each fragment fusion alone at background, a pair of non-interacting proteins and a
non-binding mutant at background, a known interacting pair as the positive control, a signal in several fusion orientations, expression of the fusions shown, a saturable titration, a reversible reporter,
the background subtracted) decide how much that means: the signal shows that the fragments came together, not that the two proteins bind directly. The criteria that need an apparent KD (the number of titration concentrations and the titration range
relative to the KD) are 'not_applicable' for a record that reports no KD ('no_apparent_kd_reported').

Terms. Signal over background: the signal of the tested pair divided by the background signal. Signal over negative control: the signal of the tested pair divided by the signal of the negative control pair. Titration range over the KD: the lowest and the highest
concentration of the titrated partner divided by the apparent KD. Orientation pairs: the fusion orientation combinations of the two partners and the two fragments that were tested.

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the reporter system, the assay system, the readout mode, the spread of the KD and its kind, and the statement that only this method was used.
"""

VERSION = 'a105_split_reporter_criteria_v1'

# ---- Threshold constants -------------------------------------------------
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.


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


def _ratio(criterion_id, question, quantity, native_name):
    return {
        'id': criterion_id,
        'question': question,
        'reads': ('quantities.' + quantity,),
        'rule': 'When the ratio is stated, the grader records it (' + native_name + ') and its refs (' + native_name + '_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', criterion_id + '_recorded_for_the_sheet', 'the ratio is stated: it is recorded and the sheet judges it'),
            ('unknown', criterion_id + '_not_given', 'the ratio is not stated'),
        ),
    }


# ---- The criteria --------------------------------------------------------
SPLIT_REPORTER_CRITERIA = (
    _one_fact('interaction_observed', 'Was a reconstituted reporter signal seen for the tested pair, above the background and the controls?', 'interaction_detected'),
    _ratio('signal_to_background', 'Is the signal of the tested pair clearly above the background signal?', 'signal_to_background', 'signal_to_background'),
    _ratio('negative_control_ratio', 'Is the signal of the tested pair clearly above the signal of the negative control pair?', 'signal_over_negative_control', 'signal_over_negative_control'),
    _one_fact('fragment_alone_control', 'Did each fragment fusion alone (or with the free partner fragment) give only background, so that the fragments do not reconstitute by themselves?', 'fragment_alone_control_negative'),
    _one_fact('unrelated_pair_control', 'Did a pair of non-interacting proteins fused to the same fragments give only background?', 'unrelated_pair_control_negative'),
    _one_fact('binding_mutant_control', 'Did a non-binding mutant of one partner give only background, or a much lower signal than the wild-type pair?', 'binding_mutant_control_negative'),
    _one_fact('positive_control', 'Did a known interacting pair give a signal in the same assay, so that the assay works?', 'positive_control_done'),
    {
        'id': 'fusion_orientations',
        'question': 'Was the interaction tested in several fusion orientations, and seen in more than one?',
        'reads': ('quantities.orientation_pairs_tested', 'facts.signal_in_several_orientations'),
        'rule': 'The fact stated as no (the signal was seen in only one orientation) fails. Otherwise a stated number of orientation combinations tested is recorded (orientation_pairs_tested, orientation_pairs_refs) and the judgement is left to the sheet; with no number the fact decides: yes supported, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'orientation_pairs_recorded_for_the_sheet', 'the fact is not no and a number is stated: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, no number is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no number is stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'no number is stated and the fact is not_applicable'),
        ),
    },
    _one_fact('expression_verified', 'Was the expression of the fusion proteins shown?', 'expression_verified'),
    _one_fact('saturable_titration', 'Did the signal rise with the concentration of the titrated partner and reach a plateau, as for a specific interaction?', 'saturable_titration_shown'),
    {
        'id': 'titration_series',
        'question': 'Was the titration run at enough concentrations to define an apparent KD?',
        'reads': ('quantities.concentration_count',),
        'rule': 'With no apparent KD reported the criterion does not apply. Otherwise a stated number of titration concentrations is recorded (concentration_count, concentration_count_refs) and the judgement is left to the sheet; none stated is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'concentration_count_recorded_for_the_sheet', 'a KD is reported and a count is stated: it is recorded and the sheet judges it'),
            ('unknown', 'concentration_count_not_given', 'a KD is reported and no count is stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    {
        'id': 'titration_range',
        'question': 'Did the titration concentrations span the apparent KD (some well below it, some well above it)?',
        'reads': ('quantities.loaded_concentration_lowest', 'quantities.loaded_concentration_highest', 'quantities.kd'),
        'rule': 'With no apparent KD reported the criterion does not apply. When the lowest concentration, the highest one and the KD are all stated, the grader records the two quotients (low_over_kd, high_over_kd) and the refs of the three (range_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'titration_range_recorded_for_the_sheet', 'a KD is reported and both ends of the range are stated: the quotients are recorded and the sheet judges them'),
            ('unknown', 'titration_range_not_given', 'a KD is reported and the two ends of the range are not both stated'),
            ('not_applicable', 'no_apparent_kd_reported', 'no KD is reported'),
        ),
    },
    _one_fact('reversible_reporter', 'Is the reconstitution of the reporter reversible, so that the signal follows the equilibrium of the partners rather than trapping the complex?', 'complementation_reversible'),
    _one_fact('background_correction', 'Was the background signal measured and subtracted (or used to normalise the signal)?', 'background_subtracted'),
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
