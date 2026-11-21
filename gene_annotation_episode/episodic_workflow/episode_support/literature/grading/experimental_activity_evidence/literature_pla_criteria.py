"""PLA criteria: the ONE place where the proximity ligation assay (PLA: in situ PLA, Duolink) grader's criteria and thresholds are declared (two proteins are probed in fixed cells or tissue with two primary antibodies from different species and oligonucleotide-linked secondary antibodies; where the two proteins are within about 40 nm the oligonucleotides are ligated, amplified by rolling-circle amplification and detected as one fluorescent punctum; the puncta are counted per cell; qualitative proximity evidence, no binding constant).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the PLA grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the puncta of the test over the puncta of the negative control, the fall of the puncta
after a knockdown, the number of cells counted, the replicate count), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_pla_converter.py.
The logic that answers each question is in literature_pla_grader.py (one short function per criterion, same order). The only constant left
here is a unit conversion (FIXED_BY_DEFINITION).

How to read an entry in PLA_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_pla_record.py)
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
support refs, the quoted source spans of the stated fields it rests on. A fact that holds no span is 'unknown' or 'not_applicable' with a
declared reason, never 'supported' and never 'conflicting'. The choices of the record (cell system, fixation, quantification software) hold no span, so no
criterion rests on a choice.

What the claim is. The experiment is judged by how well it supports "these two proteins are within about 40 nm of each other in the cell" (puncta of both primary antibodies
over the puncta of the negative controls). A punctum is no binding constant and a count of puncta is never a KD. The controls (a single primary antibody, no primary antibody, a
knockdown or competitor that lowers the signal, a positive control pair, two primary antibodies from different species, validated antibodies), the quantification (cells counted,
blind, a statistical test) and the replicates decide how much that means.

Terms. Puncta per cell: the mean number of PLA puncta per cell. Fold over control: puncta per cell of the test divided by puncta per cell of the negative control (None when the control
has 0 puncta, which no division can express). Reduction: (test - knockdown) / test * 100, in percent, signed (a fall is positive).

What this method does not ask (kept in the record for the reviewer, no criterion judges them): the amplification time, the cell system, the fixation and the quantification software.
"""

VERSION = 'a105_pla_criteria_v1'

# ---- Threshold constants -------------------------------------------------
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: percent per unit fraction (the reduction after a knockdown is recorded in percent).


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
PLA_CRITERIA = (
    _one_fact('proximity_observed', 'Did the PLA with both primary antibodies give puncta, that is, a signal of the two proteins within about 40 nm of each other?', 'proximity_signal_detected'),
    {
        'id': 'puncta_enrichment',
        'question': 'Did the test show more puncta per cell than the negative control by at least the minimum fold?',
        'reads': ('quantities.puncta_per_cell_target', 'quantities.puncta_per_cell_control'),
        'rule': 'When the puncta per cell of the test and of the negative control are both stated, the grader records them (puncta_target, puncta_control), their quotient (puncta_fold_over_control, None when the control has 0 puncta) and the refs of the two (puncta_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'puncta_enrichment_recorded_for_the_sheet', 'both puncta numbers are stated: they are recorded and the sheet judges them'),
            ('unknown', 'puncta_enrichment_not_given', 'the two puncta numbers are not both stated'),
        ),
    },
    _one_fact('single_antibody_control', 'Did the PLA with only one of the two primary antibodies give no or few puncta?', 'single_antibody_controls_negative'),
    _one_fact('no_primary_control', 'Did the PLA with no primary antibody give no or few puncta?', 'no_primary_control_negative'),
    {
        'id': 'specificity_control',
        'question': 'Did the puncta fall when one of the two proteins was knocked down, knocked out or competed away, by at least the minimum fall?',
        'reads': ('quantities.puncta_per_cell_knockdown', 'quantities.puncta_per_cell_target', 'facts.specificity_control_reduces_signal'),
        'rule': 'The fact stated as no fails. Otherwise, when the puncta per cell of the test (above 0) and after the knockdown are both stated, the grader records the reduction in percent (puncta_reduction_percent, signed) and the refs of the two (reduction_refs) and leaves the judgement to the sheet; otherwise the fact decides: yes supported, unknown unknown, not_applicable not applicable.',
        'thresholds': ('PERCENT_PER_FRACTION',),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'puncta_reduction_recorded_for_the_sheet', 'the fact is not no and both numbers are stated: the reduction is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'the fact is not no, the numbers are not both stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'the numbers are not both stated and the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'the numbers are not both stated and the fact is not_applicable'),
        ),
    },
    _one_fact('positive_control', 'Did a pair of proteins known to interact give a signal in the same PLA?', 'positive_control_pair_done'),
    _one_fact('antibody_species', 'Were the two primary antibodies raised in different species (as the two PLA probes need)?', 'primary_antibodies_different_species'),
    _one_fact('antibody_validation', 'Were the primary antibodies validated for the use in the PLA or in immunofluorescence?', 'antibodies_validated'),
    _one_fact('compartment', 'Did the puncta lie in the cell compartment where both proteins are present or expected to meet?', 'puncta_in_expected_compartment'),
    {
        'id': 'cells_counted',
        'question': 'Were the puncta counted in enough cells?',
        'reads': ('quantities.cells_counted',),
        'rule': 'A stated number of cells is recorded (cells_counted, cells_counted_refs) and the judgement is left to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'cells_counted_recorded_for_the_sheet', 'a number of cells is stated: it is recorded and the sheet judges it'),
            ('unknown', 'cells_counted_not_given', 'no number of cells is stated'),
        ),
    },
    _one_fact('blinded_quantification', 'Were the puncta counted blind to the condition or by an automatic image analysis?', 'quantification_blinded'),
    _one_fact('statistical_test', 'Were the puncta of the test and of the control compared by a named statistical test?', 'statistical_test_done'),
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Cells and images of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
