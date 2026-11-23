"""Transport_oocyte_two_electrode criteria: the ONE place where the grader's criteria of a two-electrode voltage clamp experiment on Xenopus oocytes are declared.
DRAFT of 2026-11-22, owner to correct.

This file is the single source for what the transport_oocyte_two_electrode grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the current over the control oocytes' current, the size of the current against what
the amplifier can clamp, the substrate series against the Km, the oocyte and batch counts), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_transport_oocyte_two_electrode_converter.py. The logic that answers each question is in literature_transport_oocyte_two_electrode_grader.py (one
short function per criterion, same order). The only constant here is a unit conversion marked FIXED_BY_DEFINITION; a concentration unit is turned into nM
by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

What this method can and cannot show (the reason for the criteria): the current is a flow of CHARGE. A current above the control oocytes' shows that the injected
message makes something that carries charge in response to the substrate; it does not by itself show that the substrate is what crosses (a coupled ion, a leak or a
host channel can carry it), and an electroneutral transporter gives no current at all. So the criteria ask for the controls that tie the current to the protein
(control oocytes, an inactive mutant, expression), to the substrate (a non-substrate molecule, ion dependence) and, where it was done, to the movement of the
substrate itself.

How to read an entry in TRANSPORT_OOCYTE_TWO_ELECTRODE_CRITERIA
-----------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_oocyte_two_electrode_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_transport_oocyte_two_electrode_criteria'
NA_PER_UNIT = {'nA': 1.0, 'uA': 1000.0}  # FIXED_BY_DEFINITION: a current in nA from its unit (1 uA is 1000 nA).

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

TRANSPORT_OOCYTE_TWO_ELECTRODE_CRITERIA = (
    {
        'id': 'uninjected_control',
        'question': 'Were oocytes of the same batch that were injected with water (or not injected) recorded in the same way, so that the oocyte\'s own channels and carriers are set aside?',
        'reads': ('facts.uninjected_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'background_current',
        'question': 'How large is the substrate-induced current of the oocytes with the protein against the substrate-induced current of the control oocytes?',
        'reads': ('facts.control_shows_no_substrate_current', 'quantities.current', 'quantities.control_current'),
        'rule': 'The control oocytes stated to show no substrate-induced current is supported. Otherwise, when both currents are given the grader records the current over the control current (current_over_control, dimensionless, both in nA) with their refs (control_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'control_shows_no_current', 'the control oocytes are stated to show no substrate-induced current'),
            ('unknown', 'control_current_recorded_for_the_sheet', 'both currents are given: their ratio is recorded and the sheet judges it'),
            ('unknown', 'control_current_not_comparable', 'the control is not stated to show none and either current is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'same_oocyte_baseline',
        'question': 'Is the substrate-induced current the change of the current of the same oocyte from before the substrate to during it, rather than a total current compared between oocytes?',
        'reads': ('facts.same_oocyte_baseline_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'leak_subtracted',
        'question': 'Was the leak (holding) current subtracted, or were oocytes with a large or unstable leak excluded, so that the substrate-induced current is not a damaged oocyte\'s?',
        'reads': ('facts.leak_subtracted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'non_substrate_control',
        'question': 'Did a molecule that is not the substrate, applied in the same way to oocytes with the protein, give no current (or a much smaller one), so that the current follows the substrate?',
        'reads': ('facts.non_substrate_gives_no_current',),
        'rule': 'The one fact decides: yes supported, no (a non-substrate gave a current like the substrate\'s) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'ion_dependence',
        'question': 'Did the current, or its reversal voltage, change when the ion was replaced or its concentration was changed, so that the ion that carries the charge is identified?',
        'reads': ('facts.ion_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no (the passage says it did not change) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_uptake_confirmed',
        'question': 'Was the movement of the substrate itself measured as well (by a tracer or a chemical analysis), so that the charge flow is tied to the substrate flow?',
        'reads': ('facts.substrate_uptake_confirmed',),
        'rule': 'The one fact decides: yes supported, no (no movement of the substrate was found) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_mutant_control',
        'question': 'Did an inactive mutant of the protein, or an unrelated protein, expressed in the same way give no current, so that the current is the protein\'s and not a consequence of injecting any message?',
        'reads': ('facts.inactive_mutant_gives_no_current',),
        'rule': 'The one fact decides: yes supported, no (it gave a current like the protein\'s) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'expression_confirmed',
        'question': 'Was the expression of the protein in the oocytes, or its presence at the oocyte surface, shown?',
        'reads': ('facts.expression_confirmed',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'clamp_conditions',
        'question': 'Are the voltage at which the oocytes were held and the substrate concentration at which the current was measured stated, so that the driving force is known?',
        'reads': ('facts.holding_voltage_stated', 'quantities.substrate_concentration'),
        'rule': 'Both stated is supported; either missing is unknown (a clamp whose conditions are not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'holding_voltage_and_substrate_concentration_stated', 'both are given'),
            ('unknown', 'holding_voltage_or_substrate_concentration_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'clamp_current_range',
        'question': 'Is the substrate-induced current small enough for the voltage clamp to hold the oocyte at the stated voltage?',
        'reads': ('quantities.current',),
        'rule': 'When the current is given the grader records it in nA (current_nA) with its ref (current_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'current_recorded_for_the_sheet', 'the current is given: it is recorded and the sheet judges it'),
            ('unknown', 'current_not_stated', 'the current is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the substrate concentrations of the concentration-response curve bracket the Km well enough to define it?',
        'reads': ('quantities.km', 'concentration_series'),
        'rule': 'When the Km and the series are both given the grader records the number of concentrations (concentration_count), the lowest and the highest over the Km (concentration_low_over_km, concentration_high_over_km) and their refs (concentration_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'substrate_series_recorded_for_the_sheet', 'the Km and the series are given: the count and the two ratios are recorded and the sheet judges them'),
            ('unknown', 'km_or_series_missing', 'the Km or the series is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Was the result repeated on enough independent batches of oocytes?',
        'reads': ('quantities.batch_count', 'facts.independent_batches'),
        'rule': 'Independence stated as no fails (a fact). A stated batch count with independence not stated as no is recorded (batch_count, batch_independent, batch_refs) and the judgement is left to the sheet. Oocytes of one batch are not independent replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'batches_not_independent', 'independence is stated as no'),
            ('unknown', 'batch_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'batch_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'oocytes_recorded',
        'question': 'How many oocytes were recorded for the result?',
        'reads': ('quantities.oocyte_count',),
        'rule': 'When the oocyte count is given the grader records it (oocyte_count) with its ref (oocyte_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'oocyte_count_recorded_for_the_sheet', 'the count is given: it is recorded and the sheet judges it'),
            ('unknown', 'oocyte_count_not_stated', 'the count is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'native_substrate',
        'question': 'Is the substrate the protein\'s native substrate rather than a surrogate or an analogue?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
