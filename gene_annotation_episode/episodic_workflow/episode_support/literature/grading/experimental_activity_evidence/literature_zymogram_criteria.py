"""Zymogram criteria: the ONE place where the grader's criteria of an in-gel activity staining experiment are declared.

This file is the single source for what the zymogram grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a
criterion needs a number to be compared with a limit (the apparent mass of the activity band against the mass expected from the sequence, the
replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_zymogram_converter.py. The logic that answers each question is in
literature_zymogram_grader.py (one short function per criterion, same order). There is no constant here: both masses are in kDa, and nothing else is
compared.

The result of a zymogram is QUALITATIVE (an activity band is seen or not seen). The statement itself (the fact activity_band_detected) is not a
criterion: it is the result, kept in the grader's native values for the converter. The criteria ask how far the band can be trusted to be the enzyme's
activity.

How to read an entry in ZYMOGRAM_CRITERIA
-----------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_zymogram_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_zymogram_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ZYMOGRAM_CRITERIA = (
    {
        'id': 'substrate_dependence_control',
        'question': 'Did a gel or lane developed without the substrate (or without the cofactor) show no band, so that the band is not a stain artefact?',
        'reads': ('facts.no_substrate_control_clean',),
        'rule': 'The one fact decides: yes (the control showed no band) supported, no (the control also showed the band) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_sample_control',
        'question': 'Did a heat-treated or boiled sample, or a sample of a catalytically dead mutant, show no activity band, so that the band is the enzyme\'s catalysis and not a non-enzymatic reaction?',
        'reads': ('facts.inactive_sample_clean',),
        'rule': 'The one fact decides: yes (no band) supported, no (the band still appeared) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'stain_positive_control',
        'question': 'Did a known active enzyme on the same gel show its activity band, so that the gel and the stain could show an activity?',
        'reads': ('facts.positive_control_band_shown',),
        'rule': 'The one fact decides: yes supported, no (the positive control showed no band: the gel or the stain did not work) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'band_position',
        'question': 'Does the apparent mass of the activity band agree with the mass expected for the enzyme from its sequence?',
        'reads': ('quantities.band_mass', 'quantities.expected_mass'),
        'rule': 'When both masses are given the grader records the band mass over the expected mass (band_over_expected, dimensionless) with their refs (band_position_refs) and leaves the judgement to the sheet; otherwise unknown. A band at the expected mass is weak support only (many enzymes share a mass), so this criterion never makes a band conflicting by a missing mass.',
        'thresholds': (),
        'returns': (
            ('unknown', 'band_position_recorded_for_the_sheet', 'both masses are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'band_or_expected_mass_missing', 'either mass is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'band_assignment',
        'question': 'Was the activity band assigned to the enzyme by a second route (the band missing in a sample that lacks the gene, or the band identified by mass spectrometry, an antibody or a purified recombinant enzyme)?',
        'reads': ('facts.deletion_sample_lacks_band', 'facts.band_assigned_to_target'),
        'rule': 'Either fact stated as yes is enough. If a fact is stated as no (the band was still there in the sample that lacks the gene, or the band could not be assigned) it fails, even beside the other fact stated as yes (a stated failure is not outweighed). A fact stated nowhere is unknown, never no. Both not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'band_assigned_to_the_enzyme', 'a fact is yes and none is no'),
            ('conflicting', 'fact_answered_no', 'a fact is no'),
            ('unknown', 'fact_unknown', 'none is yes or no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'inhibitor_sensitivity',
        'question': 'Did a specific inhibitor (or the removal of a required metal or cofactor) abolish the band, which shows what kind of catalysis it is?',
        'reads': ('facts.inhibitor_abolishes_band',),
        'rule': 'Yes is supported. A band the inhibitor did not change is NOT against the claim (the inhibitor may simply not be one of that enzyme\'s class), so it is unknown, never conflicting. Unknown is unknown, not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'inhibitor_abolished_the_band', 'the fact is yes'),
            ('unknown', 'inhibitor_did_not_change_the_band', 'the fact is no'),
            ('unknown', 'fact_unknown', 'the fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. One gel looked at several times is not a set of replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'native_substrate',
        'question': 'Is the substrate of the gel or of the stain the enzyme\'s native substrate rather than a general or surrogate substrate (gelatin, casein, a naphthyl ester)?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the activity measured with the purified enzyme rather than a cell extract, lysate or culture medium?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
