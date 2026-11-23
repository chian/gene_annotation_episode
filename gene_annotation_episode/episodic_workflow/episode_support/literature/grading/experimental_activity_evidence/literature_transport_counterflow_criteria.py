"""Transport_counterflow criteria: the ONE place where the grader's criteria of a counterflow (exchange, trans-stimulation) experiment are declared.

This file is the single source for what the transport_counterflow grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the preloaded substrate over the external substrate, the external
substrate series against the Km, the replicate count), the grader records the number with its support refs and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_transport_counterflow_converter.py. The logic that answers each question is in literature_transport_counterflow_grader.py (one short
function per criterion, same order). There is no constant here: a concentration unit is turned into nM by the grader's fixed scale table
(FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in TRANSPORT_COUNTERFLOW_CRITERIA
------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_counterflow_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
No criterion rests on a plain choice field (spread_kind): a choice holds no span in the merged record.
"""

VERSION = 'a105_transport_counterflow_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

TRANSPORT_COUNTERFLOW_CRITERIA = (
    {
        'id': 'non_preloaded_baseline',
        'question': 'Were the same vesicles or cells without the preload measured in the same experiment, so that the effect of the preload (the trans-stimulation) is read against its own baseline?',
        'reads': ('facts.non_preloaded_baseline_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'protein_free_control',
        'question': 'Was a control without the protein (protein-free liposomes, an empty-vector strain, the parent or a deletion strain) taken through the same preload and uptake, so that the exchange is tied to the protein and not to other carriers or to leak?',
        'reads': ('facts.protein_free_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'non_substrate_preload',
        'question': 'Was a preload with a molecule that is not a substrate tested and shown not to stimulate the uptake of the label, so that the stimulation is specific to recognition of the preloaded molecule?',
        'reads': ('facts.non_substrate_preload_control_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'label_identity',
        'question': 'Was the label kept inside shown to be the unchanged substrate and not a metabolite of it?',
        'reads': ('facts.label_identity_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'preload_verified',
        'question': 'Was the loading of the vesicles or cells verified (the substrate inside was measured or the loading was shown to have reached its aim)?',
        'reads': ('facts.preload_verified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'preload_over_label',
        'question': 'Was the preloaded substrate large against the substrate outside at the start of the uptake, so that an overshoot above the equilibrium level is possible?',
        'reads': ('quantities.preload_concentration', 'quantities.label_concentration'),
        'rule': 'When both concentrations are given the grader records the preloaded concentration over the external concentration (preload_over_label, dimensionless) with their refs (preload_ratio_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'preload_ratio_recorded_for_the_sheet', 'both concentrations are given: the ratio is recorded and the sheet judges it'),
            ('unknown', 'preload_or_label_concentration_missing', 'either concentration is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'preload_retained',
        'question': 'Did the preloaded substrate stay inside the vesicles or cells during the uptake (a leak or retention control), so that the exchange gradient lasts?',
        'reads': ('facts.preload_retained',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'uptake_endpoint',
        'question': 'Is what is measured defined as an overshoot over the equilibrium level that the label reaches later, or as an initial rate from the linear part of the time course?',
        'reads': ('facts.equilibrium_reached', 'facts.linear_interval_shown'),
        'rule': 'Either fact stated as yes is enough. If neither is stated as yes and one is stated as no, it fails. A fact stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'uptake_endpoint_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the external substrate concentrations of the series bracket the Km well enough to define it?',
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
        'id': 'native_substrate',
        'question': 'Are the labelled molecule and the preloaded molecule the natural substrate of the transporter rather than analogues or surrogates?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated samples of one vesicle or cell batch are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
