"""Transport_planar_bilayer criteria: the ONE place where the grader's criteria of a planar lipid bilayer recording are declared.

This file is the single source for what the transport_planar_bilayer grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the stated conductance against the current over the driving force,
the permeability ratio, the unitary current over the recording noise, the number of events, the bilayer count), the grader records the number
with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are
on the sheet side, in literature_transport_planar_bilayer_converter.py. The logic that answers each question is in
literature_transport_planar_bilayer_grader.py (one short function per criterion, same order). There is no judging constant here: a unit
(pA, nA, pS, nS) is turned into pA or pS by the grader's fixed scale tables (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in TRANSPORT_PLANAR_BILAYER_CRITERIA
---------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_planar_bilayer_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_transport_planar_bilayer_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

TRANSPORT_PLANAR_BILAYER_CRITERIA = (
    {
        'id': 'protein_free_control',
        'question': 'Was a bilayer without the protein (or with protein-free liposomes, buffer and detergent only) recorded the same way, and did it show no channel events or current?',
        'reads': ('facts.protein_free_bilayer_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'bilayer_integrity',
        'question': 'Was the bilayer shown to be intact and stable (a quiet, leak-free baseline), so that a current step is the protein and not a failing bilayer?',
        'reads': ('facts.bilayer_integrity_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'solutions_stated',
        'question': 'Are the salt or ion concentrations (compositions) of the solutions on both sides of the bilayer stated, so that the driving force and the ion gradient can be known?',
        'reads': ('facts.solutions_stated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'driving_force_correction',
        'question': 'Is the unitary conductance the current over the driving force (the holding voltage minus the reversal potential), not the current over the holding voltage alone?',
        'reads': ('facts.driving_force_corrected', 'quantities.unitary_conductance', 'quantities.unitary_current', 'quantities.holding_voltage', 'quantities.reversal_potential'),
        'rule': 'The fact stated as no fails. When the conductance, the current, the holding voltage and the reversal potential are all given, and the two voltages differ, the grader records the stated conductance (stated_conductance_pS) and the conductance that the current and the driving force give (current_over_driving_force_pS) with their refs (driving_force_refs) and leaves the comparison to the sheet. Otherwise the fact stated as yes is supported; silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'driving_force_recorded_for_the_sheet', 'the four numbers are given, the voltages differ and the fact is not no: both conductances are recorded and the sheet compares them'),
            ('supported', 'driving_force_corrected_stated', 'the numbers are not all given (or the voltages are equal) and the fact is yes'),
            ('unknown', 'driving_force_correction_not_stated', 'the numbers are not all given (or the voltages are equal) and the fact is not stated'),
            ('not_applicable', 'fact_not_applicable', 'the numbers are not all given and the fact is not_applicable'),
        ),
    },
    {
        'id': 'bi_ionic_gradient',
        'question': 'Was the reversal potential (or the current) measured with two different ions or salt concentrations in the two chambers, so that the ion that carries the current can be identified?',
        'reads': ('facts.bi_ionic_gradient_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'ion_preference',
        'question': 'Does the channel prefer the ion or substrate the passage is about over the other ion it was compared with, and by what permeability ratio?',
        'reads': ('facts.named_ion_preferred', 'quantities.permeability_ratio'),
        'rule': 'The fact stated as no fails (the paper says the channel prefers the other ion). When the permeability ratio is given and the fact is not no, the grader records the ratio (permeability_ratio) and the fact answer (named_ion_preferred) with their refs (permeability_refs) and leaves the judgement to the sheet. Otherwise the fact stated as yes is supported; silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the fact is no'),
            ('unknown', 'permeability_ratio_recorded_for_the_sheet', 'the ratio is given and the fact is not no: both are recorded and the sheet judges them'),
            ('supported', 'named_ion_preferred_stated', 'no ratio is given and the fact is yes'),
            ('unknown', 'ion_preference_not_stated', 'no ratio is given and the fact is not stated'),
            ('not_applicable', 'fact_not_applicable', 'no ratio is given and the fact is not_applicable'),
        ),
    },
    {
        'id': 'blocker_control',
        'question': 'Did a known blocker or inhibitor of the channel reduce or abolish the current, showing that the current is the channel\'s?',
        'reads': ('facts.blocker_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'signal_over_noise',
        'question': 'Is the unitary current large against the noise of the recording, so that single-channel steps are told from the baseline?',
        'reads': ('quantities.unitary_current', 'quantities.baseline_noise'),
        'rule': 'When the unitary current and the rms noise are both given the grader records the current over the noise (amplitude_over_noise, dimensionless) with their refs (noise_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'amplitude_over_noise_recorded_for_the_sheet', 'both are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'current_or_noise_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'events_analysed',
        'question': 'How many single-channel events stand behind the stated unitary size?',
        'reads': ('quantities.event_count',),
        'rule': 'When the event count is given the grader records it (event_count) with its ref (event_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'event_count_recorded_for_the_sheet', 'the count is given: it is recorded and the sheet judges it'),
            ('unknown', 'event_count_not_stated', 'the count is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent bilayers (the independent unit; events of one bilayer are not replicates)?',
        'reads': ('quantities.bilayer_count', 'facts.independent_bilayers'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Events or traces of one bilayer are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'purified_protein',
        'question': 'Was the protein purified before it was put into the bilayer, rather than a membrane preparation or extract that may carry other channels?',
        'reads': ('facts.purified_protein',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
