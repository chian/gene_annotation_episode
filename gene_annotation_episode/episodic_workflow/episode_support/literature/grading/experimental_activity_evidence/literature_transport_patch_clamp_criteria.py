"""Transport_patch_clamp criteria: the ONE place where the grader's criteria of a patch-clamp experiment on cells are declared. DRAFT 2026-11-22, owner to correct.

This file is the single source for what the transport_patch_clamp grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the series resistance, the seal resistance, the measured reversal potential against
the Nernst potential, the counts of cells and of independent preparations), the grader records the number with its support refs and returns 'unknown'
with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_transport_patch_clamp_converter.py. The logic that answers each question is in literature_transport_patch_clamp_grader.py (one short function
per criterion, same order). There is no constant here: a resistance unit is turned into GOhm by the fixed factor of a unit (FIXED_BY_DEFINITION), and nothing
else is compared.

How to read an entry in TRANSPORT_PATCH_CLAMP_CRITERIA
------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_patch_clamp_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
No criterion rests on a plain choice field (spread_kind, patch_configuration): a choice holds no span in the merged record.
"""

VERSION = 'a105_transport_patch_clamp_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

# The two facts that only a conductance or a charge flow needs (the single-channel record and the driving-force correction): a result whose only effect is a
# fold over the control, or that states no quantity, does not need them, so their silence is not applicable there and not unknown.
_conductance_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown and a unitary conductance or a charge rate is stated'),
    ('not_applicable', 'no_conductance_or_charge_rate_stated', 'the fact is unknown and neither a unitary conductance nor a charge rate is stated'),
)

TRANSPORT_PATCH_CLAMP_CRITERIA = (
    {
        'id': 'host_cell_control',
        'question': 'Were cells that do not make the protein (untransfected, mock-transfected or empty-vector cells, or the parent cell line) recorded the same way, so the host cell\'s own channels and transporters are set aside?',
        'reads': ('facts.untransfected_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_mutant_control',
        'question': 'Was a non-conducting or inactive form of the protein recorded the same way, so the current belongs to the protein and not to the act of expressing something?',
        'reads': ('facts.inactive_mutant_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_free_control',
        'question': 'Was the current recorded without the substrate, agonist or driving gradient (or before it was applied) in the same cells, so the substrate-dependent part is the part that is measured?',
        'reads': ('facts.substrate_free_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'ion_substitution',
        'question': 'Was an ion of the bath or pipette solution replaced and the current or its reversal potential examined, so the carrier of the current is identified and charge flow is not taken for the flow of one ion?',
        'reads': ('facts.ion_substitution_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'blocker_control',
        'question': 'Was a blocker or inhibitor of the protein applied to the current, so the current is shown to be the protein\'s?',
        'reads': ('facts.blocker_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'series_resistance_error',
        'question': 'Was the series resistance small enough, or compensated, that the voltage at the membrane is the voltage that was commanded?',
        'reads': ('quantities.series_resistance', 'facts.series_resistance_compensated'),
        'rule': 'When the series resistance is given the grader records it (series_resistance_mohm, series_resistance_refs) and leaves the judgement to the sheet. Otherwise a compensation stated as yes is supported; anything else is unknown (a recording whose series resistance is not stated is not shown wrong, and a compensation stated as not done without a value is not shown wrong either).',
        'thresholds': (),
        'returns': (
            ('unknown', 'series_resistance_recorded_for_the_sheet', 'the series resistance is given: it is recorded and the sheet judges it'),
            ('supported', 'series_resistance_compensation_stated', 'no series resistance is given and the compensation is yes'),
            ('unknown', 'series_resistance_not_stated', 'no series resistance is given and the compensation is not yes'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'seal_and_leak',
        'question': 'Was the seal tight, or the leak current subtracted, so the leak is not read as the current of the protein?',
        'reads': ('quantities.seal_resistance', 'facts.leak_subtracted'),
        'rule': 'When the seal resistance is given the grader records it (seal_resistance_gohm, seal_resistance_refs) and leaves the judgement to the sheet. Otherwise a leak subtraction stated as yes is supported; anything else is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'seal_recorded_for_the_sheet', 'the seal resistance is given: it is recorded and the sheet judges it'),
            ('supported', 'leak_subtraction_stated', 'no seal resistance is given and the leak subtraction is yes'),
            ('unknown', 'seal_not_stated', 'no seal resistance is given and the leak subtraction is not yes'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'voltage_stated',
        'question': 'Is the voltage at which the current or the conductance was taken stated, so the voltage convention of the number is known?',
        'reads': ('quantities.holding_voltage',),
        'rule': 'The voltage stated is supported; not stated is unknown (a number whose voltage is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'holding_voltage_stated', 'the voltage is given'),
            ('unknown', 'holding_voltage_not_stated', 'the voltage is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'unitary_events_resolved',
        'question': 'Were single-channel events resolved, so a unitary conductance is the conductance of one channel and not an average over many?',
        'reads': ('facts.single_channel_resolved',),
        'rule': 'A fact stated as yes is supported and as no fails. A fact not stated is unknown when a unitary conductance is stated and not applicable when it is not (a fold over the control or a charge rate does not need single-channel events). The grader looks at whether a unitary conductance is stated only to tell these two apart; that quantity is not read as evidence, so its quote support is not carried into this criterion.',
        'thresholds': (),
        'returns': _conductance_fact_returns,
    },
    {
        'id': 'driving_force_correction',
        'question': 'Was the conductance corrected for the driving force (taken from the slope of the current-voltage curve, or as the current over the voltage minus the reversal potential), so it is not the current over the voltage alone?',
        'reads': ('facts.driving_force_corrected',),
        'rule': 'A fact stated as yes is supported and as no fails. A fact not stated is unknown when a unitary conductance or a charge rate is stated and not applicable when neither is (a fold over the control does not need a driving-force correction). The grader looks at whether those two are stated only to tell these two cases apart; they are not read as evidence, so their quote support is not carried into this criterion.',
        'thresholds': (),
        'returns': _conductance_fact_returns,
    },
    {
        'id': 'reversal_potential_match',
        'question': 'Does the measured reversal potential lie where the claimed ion\'s equilibrium (Nernst) potential lies, so the current is carried by that ion?',
        'reads': ('quantities.reversal_potential', 'quantities.nernst_potential'),
        'rule': 'When both are given the grader records the measured reversal potential minus the Nernst potential (reversal_minus_nernst_mv, in mV) with their refs (reversal_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'reversal_recorded_for_the_sheet', 'both potentials are given: their difference is recorded and the sheet judges it'),
            ('unknown', 'reversal_or_nernst_missing', 'either potential is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough cells, from independent transfections or preparations?',
        'reads': ('quantities.cell_count', 'quantities.batch_count', 'facts.independent_preparations'),
        'rule': 'Independence stated as no fails (a fact). A stated cell count or batch count with independence not stated as no is recorded (cell_count, batch_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Cells are the sampling unit, not sweeps or traces; several cells of one dish are not independent preparations.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a cell count or a batch count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'neither count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'native_substrate',
        'question': 'Is the substrate or ion that was applied, or that carried the current, the native one rather than an analogue or a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
