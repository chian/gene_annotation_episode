"""Transport_vesicle_probe_flux criteria: the ONE place where the grader's criteria of a continuous vesicle flux experiment read by a probe are declared.

This file is the single source for what the transport_vesicle_probe_flux grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the release of the protein vesicles against the protein-free vesicles, the rate of the
release against the response time of the apparatus, the replicate count), the grader records the number with its support refs and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_transport_vesicle_probe_flux_converter.py. The logic that answers each question is in literature_transport_vesicle_probe_flux_grader.py (one short
function per criterion, same order). There is no constant here: a time unit is turned into seconds by the fixed table of the grader and the half-time into a rate
constant by ln 2 (both FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in TRANSPORT_VESICLE_PROBE_FLUX_CRITERIA
-------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_vesicle_probe_flux_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
No criterion rests on a plain choice field (spread_kind, probe_kind): a choice holds no span in the merged record.
"""

VERSION = 'a105_transport_vesicle_probe_flux_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

TRANSPORT_VESICLE_PROBE_FLUX_CRITERIA = (
    {
        'id': 'protein_free_vesicle_control',
        'question': 'Were vesicles without the protein run through the same protocol, so that the leak and the nonspecific release of the vesicles are set aside?',
        'reads': ('facts.protein_free_vesicle_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'release_over_control',
        'question': 'Is the release of the vesicles with the protein clearly larger than the release of the protein-free vesicles at the same time?',
        'reads': ('quantities.release_fraction', 'quantities.control_release_fraction', 'quantities.release_time'),
        'rule': 'When both shares are given the grader records them (release_percent, control_release_percent) with their refs (release_over_control_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'release_over_control_recorded_for_the_sheet', 'both shares are given: they are recorded and the sheet judges them'),
            ('unknown', 'release_or_control_release_not_stated', 'either share is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'protein_amount_in_vesicles',
        'question': 'Was the amount of protein that is in the vesicles measured, so that the flux is tied to that protein and not to what was put into the reconstitution?',
        'reads': ('facts.protein_quantified_in_vesicles',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'second_ion_control',
        'question': 'Was a second ion or substrate tested in the same kind of vesicles, to show which species the protein moves?',
        'reads': ('facts.second_ion_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'probe_selectivity',
        'question': 'Does the electrode or the entrapped dye respond to the species that is followed and not to the other species in the vesicles and the bath?',
        'reads': ('facts.probe_selective_for_ion',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'ionophore_control',
        'question': 'Was the driving force (the gradient or the counter-ion movement) set or tested with an ionophore, so that the flux is not limited by something other than the protein?',
        'reads': ('facts.ionophore_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'gradient_defined',
        'question': 'Are the concentrations of the ion or substrate inside and outside the vesicles at the start stated, so that the gradient that drives the flux is known?',
        'reads': ('facts.gradient_defined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'detergent_reference',
        'question': 'Was the content left in the vesicles released at the end with a detergent and taken as the whole pool, so that the release is a fraction of a known total?',
        'reads': ('facts.detergent_reference_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'time_resolution',
        'question': 'Is the release slow enough, against the response time of the apparatus, to be read as a rate, or is it correctly stated as only a limit?',
        'reads': ('facts.flux_faster_than_apparatus_response', 'quantities.rate_constant', 'quantities.half_time', 'quantities.dead_time'),
        'rule': 'The fact stated as yes (the paper says the flux was faster than the apparatus could follow) is supported: the rate is stated as a limit and not as a rate. Otherwise, when the rate constant (or the half-time, turned into a rate constant by ln 2) and the response time are both given, the grader records the rate constant in s^-1 and the response time in s (rate_constant_per_s, dead_time_s) with their refs (time_resolution_refs) and leaves the judgement to the sheet. Otherwise the fact stated as no (the paper says the flux was resolved) is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'flux_stated_as_a_limit', 'the fact is yes'),
            ('unknown', 'time_resolution_recorded_for_the_sheet', 'the fact is not yes, and the rate constant (or the half-time) and the response time are given: they are recorded and the sheet judges them'),
            ('supported', 'flux_stated_as_resolved', 'the fact is no and the rate constant (or the half-time) or the response time is not given'),
            ('unknown', 'time_resolution_not_stated', 'the fact is not stated and the rate constant (or the half-time) or the response time is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'probe_calibration',
        'question': 'Was the electrode or the dye calibrated with known amounts of the ion (or known pH values) in the same buffer, so that the signal is read as an amount?',
        'reads': ('facts.probe_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'vesicle_integrity',
        'question': 'Were the vesicles shown to hold their content before the flux was started?',
        'reads': ('facts.vesicle_integrity_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated traces of one batch of vesicles are not replicates.',
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
        'question': 'Is the ion or substrate that was followed the natural substrate of the protein rather than a surrogate or an analogue?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_protein',
        'question': 'Was the protein purified and reconstituted into the vesicles, rather than studied in native membrane vesicles or vesicles from cells?',
        'reads': ('facts.purified_protein',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
