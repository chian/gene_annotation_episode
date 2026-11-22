"""Co-localization criteria: the ONE place where the microscopy co-localization / recruitment grader's criteria are declared (fluorescence microscopy shows that one labelled protein is found where the other is: two labelled proteins co-localize in cells, one is recruited to the site that the other makes, in a native or a heterologous host or as purified proteins in droplets, on beads or on a membrane, and the localization is lost when the partner is absent or its binding region is removed; qualitative nearness evidence, no binding constant).

DRAFT FOR EXPERT REVIEW. This file is the single source for what the co-localization grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the fraction of the scored objects that showed it, the Pearson coefficient, the enrichment, the number of
cells, foci or droplets scored, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_colocalization_converter.py.
The logic that answers each question is in literature_colocalization_grader.py (one short function per criterion, same order). This method has no constant here
(no unit conversion is needed).

How to read an entry in COLOCALIZATION_CRITERIA
-----------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_colocalization_record.py)
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
declared reason, never 'supported' and never 'conflicting'. No criterion rests on a choice: the system is the two facts heterologous_host and purified_proteins, each with its span.
The imaging mode holds no criterion.

What the claim is. The experiment is judged by how well it supports "one of these two proteins is found where the other is, because of the other" (co-localization or recruitment, and its loss
when the partner is absent or its binding region is removed). A fraction, a coefficient or an enrichment is no binding constant and is never a KD. The controls (an unrelated protein or the tag
alone that is not recruited, the loss without the partner, the loss when the binding region is removed, the following of the partner when it is moved), the system (a heterologous host
or purified proteins leave no native third protein that could bridge the two), the validity of the expression and of the tag, the quantification (cells, foci or droplets scored) and the
replicates decide how much that means. With diffraction-limited imaging the result is nearness within about 250 nm, not contact; that limit is carried by the weight of the type
(literature_row_contract.QUALITATIVE_LOG_RATIO), not by a criterion.

Terms. Fraction: the percent of the scored objects that showed the co-localization. Pearson: the correlation coefficient of the two channels, from -1 to 1. Enrichment: the signal at the site
of the partner over the signal elsewhere (a partition coefficient).

What this method does not ask (kept in the record for the reviewer, no criterion judges it): the imaging mode.
"""

VERSION = 'a105_colocalization_criteria_v1'

# ---- Threshold constants -------------------------------------------------
# None: every number is judged on the sheet side (literature_colocalization_converter.py).


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
COLOCALIZATION_CRITERIA = (
    _one_fact('colocalization_observed', 'Did the passage show the protein where the partner is (co-localized with it or recruited to the site that it makes)?', 'colocalization_observed'),
    {
        'id': 'colocalization_readout',
        'question': 'Did the quantified readout (the fraction of the scored objects, the Pearson coefficient, the enrichment) show the co-localization or the recruitment?',
        'reads': ('quantities.fraction_colocalized', 'quantities.pearson_coefficient', 'quantities.enrichment_ratio'),
        'rule': 'When at least one of the fraction, the Pearson coefficient and the enrichment is stated, the grader records each stated number with the refs of them all (colocalization_fraction, colocalization_pearson, colocalization_enrichment, readout_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'colocalization_readout_recorded_for_the_sheet', 'at least one readout number is stated: the numbers are recorded and the sheet judges them'),
            ('unknown', 'colocalization_readout_not_given', 'none of the three numbers is stated'),
        ),
    },
    {
        'id': 'specificity_control',
        'question': 'Was an unrelated protein (or the tag alone) not recruited under the same conditions, or was the localization lost when the partner was absent?',
        'reads': ('facts.unrelated_protein_not_recruited', 'facts.lost_without_partner'),
        'rule': 'Either fact stated as no fails (the unrelated protein is recruited too, or the protein stays localized without the partner). Otherwise supported when either fact is yes (one stated control is a control; it cites the yes facts); nothing stated leaves it unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'either control fact is no'),
            ('supported', 'facts_answered_yes', 'no fact is no, and a fact is yes'),
            ('unknown', 'fact_unknown', 'neither control is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'directness',
        'question': 'Does the experiment show that the partner itself, and not a third protein that bridges the two, makes the site: a heterologous host or purified proteins, a mutant without the binding region that does not co-localize, a protein that follows the partner when it is moved?',
        'reads': ('facts.lost_with_binding_region_removed', 'facts.follows_partner_when_moved', 'facts.heterologous_host', 'facts.purified_proteins'),
        'rule': 'Either of the first two facts stated as no fails (the binding-region mutant still co-localizes, the protein does not follow the partner). Otherwise supported when one of them is yes, or when the experiment is stated to be in a heterologous host or with purified proteins (it cites the yes facts); a native host (those two facts no), or nothing stated, leaves it unknown, never conflicting.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the binding-region fact or the following fact is no'),
            ('supported', 'facts_answered_yes', 'no fact is no, and a fact is yes'),
            ('supported', 'system_without_a_native_bridge', 'neither of the first two facts is stated, and the heterologous-host or the purified-proteins fact is yes'),
            ('unknown', 'native_host_or_system_unknown', 'neither of the first two facts is stated, and neither a heterologous host nor purified proteins is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'expression_validity',
        'question': 'Were the labelled proteins expressed near the native level (not for purified proteins) and was the tagged protein shown to be functional or the tag shown not to change the localization?',
        'reads': ('facts.expressed_near_native_level', 'facts.fusion_functional', 'facts.purified_proteins'),
        'rule': 'Shared rule over the first two facts, where the expression fact is not applicable when the purified-proteins fact is yes (they have no expression level): any no fails; else any unknown unknown; else all not_applicable not applicable; else supported.',
        'thresholds': (),
        'returns': _fact_returns(),
    },
    {
        'id': 'objects_counted',
        'question': 'Was the result quantified over enough cells, foci or droplets?',
        'reads': ('quantities.objects_counted', 'facts.quantified_over_many_cells'),
        'rule': 'The quantification fact stated as no (one representative image) fails. A stated number of objects is recorded (objects_counted, objects_counted_refs) and the judgement is left to the sheet. Otherwise the fact decides: yes supported, unknown unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the quantification fact is no'),
            ('unknown', 'objects_counted_recorded_for_the_sheet', 'a number of objects is stated and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'facts_answered_yes', 'no number is stated and the fact is yes'),
            ('unknown', 'fact_unknown', 'no number is stated and the fact is unknown'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_experiments'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Cells, foci and droplets of one sample are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
