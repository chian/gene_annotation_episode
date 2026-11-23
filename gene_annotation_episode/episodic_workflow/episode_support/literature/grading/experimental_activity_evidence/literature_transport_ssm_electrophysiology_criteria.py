"""Transport_ssm_electrophysiology criteria: the ONE place where the grader's criteria of a solid-supported membrane (SSM) electrophysiology experiment are declared.

This file is the single source for what the transport_ssm_electrophysiology grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the decay time of the transient against the solution-exchange time, the
substrate series against the Km, the sensor count, the preparation count), the grader records the number with its support refs and returns
'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_transport_ssm_electrophysiology_converter.py. The logic that answers each question is in
literature_transport_ssm_electrophysiology_grader.py (one short function per criterion, same order). There is no constant here: a concentration unit
is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in TRANSPORT_SSM_ELECTROPHYSIOLOGY_CRITERIA
----------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_ssm_electrophysiology_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_transport_ssm_electrophysiology_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

TRANSPORT_SSM_ELECTROPHYSIOLOGY_CRITERIA = (
    {
        'id': 'empty_liposome_control',
        'question': 'Was a control sensor with empty (protein-free) liposomes measured with the same jump, so the current can be told from what the membrane, the lipid and the solutions give without the protein?',
        'reads': ('facts.empty_liposome_sensor_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'buffer_artefact',
        'question': 'Was the solution-exchange artefact (the transient of the jump itself, seen without any transport) measured and subtracted, or shown to be small?',
        'reads': ('facts.buffer_jump_artefact_subtracted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'sensor_quality',
        'question': 'Were the capacitance and conductance of the sensor (the check that the solid-supported membrane is intact) measured or stated?',
        'reads': ('facts.sensor_capacitance_stated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_protein_control',
        'question': 'Did an inactive or mutant protein, reconstituted in the same way, give no current or a smaller one, so the current belongs to the active protein?',
        'reads': ('facts.inactive_protein_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'electrogenic_stated',
        'question': 'Is the transport of the substrate by this protein stated to be electrogenic (net charge moves in the cycle), so that a transient current is the expected signal and its absence would mean something?',
        'reads': ('facts.electrogenic_transport_stated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'native_substrate',
        'question': 'Is the molecule of the jump the native substrate of the protein rather than an analogue or a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'reference_normalization',
        'question': 'Were the peak currents normalized to, or checked against, a reference jump on the same sensor, so that the differing amount of protein on each sensor does not enter the Km or the fold?',
        'reads': ('facts.same_sensor_reference_jump',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'time_resolution',
        'question': 'Is the transient slow enough against the time in which the solution is exchanged at the sensor, so that its peak is the transport and not the exchange?',
        'reads': ('quantities.decay_time',),
        'rule': 'When the decay time of the transient is given the grader records it (decay_time_value, decay_time_unit, decay_time_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'decay_time_recorded_for_the_sheet', 'the decay time is given: it is recorded and the sheet judges it'),
            ('unknown', 'decay_time_not_stated', 'the decay time is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'endpoint_stated',
        'question': 'Is the quantity read from the transient (the peak current or the translocated charge) stated, so that it is clear what the Km or the fold refers to?',
        'reads': ('quantities.peak_current', 'quantities.charge'),
        'rule': 'Either stated is supported; neither stated is unknown (a result whose readout is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'endpoint_quantity_stated', 'the peak current or the charge is given'),
            ('unknown', 'endpoint_quantity_not_stated', 'neither is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'solutions_matched',
        'question': 'Were the resting and activating solutions identical apart from the substrate (the same buffer, pH, ionic strength and ions), so that the jump changes only the substrate?',
        'reads': ('facts.solutions_matched_except_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'specificity_control',
        'question': 'Did a control tie the current to the transport of the claimed substrate or ion: a non-substrate jump, a known blocker or a substitution of the coupling ion?',
        'reads': ('facts.non_substrate_jump_done', 'facts.blocker_control_done', 'facts.ion_substitution_done'),
        'rule': 'Any one of the three stated as done is enough (the refs are those of the facts answered yes). If none is done and every stated one is no, it fails (the refs are those answered no). A control stated nowhere is unknown, never no. All three not_applicable is not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'specificity_control_stated', 'any of the three facts is yes'),
            ('conflicting', 'fact_answered_no', 'none is yes and every fact that is stated is no'),
            ('unknown', 'fact_unknown', 'none is yes and not every stated fact is no'),
            ('not_applicable', 'fact_not_applicable', 'all three facts are not_applicable'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the substrate concentrations of the jumps bracket the Km well enough to define it on one saturation curve?',
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
        'id': 'sensors',
        'question': 'Were there enough sensors, each an independent measurement?',
        'reads': ('quantities.sensor_count', 'facts.independent_sensors'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (sensor_count, sensor_independent, sensor_refs) and the judgement is left to the sheet. Repeated jumps on one sensor are not sensors.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'sensors_not_independent', 'independence is stated as no'),
            ('unknown', 'sensor_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'sensor_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'preparations',
        'question': 'Were there enough independent proteoliposome preparations?',
        'reads': ('quantities.preparation_count', 'facts.independent_preparations'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (preparation_count, preparation_independent, preparation_refs) and the judgement is left to the sheet.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'preparations_not_independent', 'independence is stated as no'),
            ('unknown', 'preparation_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'preparation_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
