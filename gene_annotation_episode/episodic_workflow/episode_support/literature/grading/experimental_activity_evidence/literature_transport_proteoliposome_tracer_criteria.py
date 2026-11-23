"""Transport_proteoliposome_tracer criteria: the ONE place where the grader's criteria of a proteoliposome tracer transport experiment are declared.

DRAFT built 2026-11-22 on the shape of literature_spectro_direct_criteria.py, owner to correct. This file is the single source for what the transport_proteoliposome_tracer
grader asks. The grader reports FACTS and holds NO threshold that judges goodness: where a criterion needs a number to be compared with a limit (the share of the plateau
uptake reached when the rate was taken, the substrate series against the Km, the replicate count), the grader records the number with its support refs and returns 'unknown'
with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_transport_proteoliposome_tracer_converter.py. The logic that answers each question is in literature_transport_proteoliposome_tracer_grader.py (one short function
per criterion, same order). There is no constant here: a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is
compared.

How to read an entry in TRANSPORT_PROTEOLIPOSOME_TRACER_CRITERIA
----------------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_transport_proteoliposome_tracer_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_transport_proteoliposome_tracer_criteria'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)
_one_fact_rule = 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.'

TRANSPORT_PROTEOLIPOSOME_TRACER_CRITERIA = (
    {
        'id': 'empty_liposome_control',
        'question': 'Was the passive and non-specific uptake (leak, sticking of the label to the lipid or the filter, endogenous contaminants) measured and set aside, by protein-free liposomes put through the same assay?',
        'reads': ('facts.empty_liposome_control_done',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'inactive_protein_control',
        'question': 'Was the transport shown to need the active protein, by a reconstituted inactive (heat-denatured, dead or binding-deficient) protein put through the same assay?',
        'reads': ('facts.inactive_protein_control_done',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'no_gradient_control',
        'question': 'Was the transport shown to depend on the imposed driving force, by the same assay without the gradient or with it dissipated?',
        'reads': ('facts.no_gradient_control_done',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'gradient_verified',
        'question': 'Was the imposed gradient or potential itself shown to be there (a probe or a measurement), so that the driving force is known and not assumed?',
        'reads': ('facts.gradient_verified',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'leak_check',
        'question': 'Were the vesicles shown to be tight (they hold the label or the gradient), so that the signal is transport into a closed compartment?',
        'reads': ('facts.leak_checked',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'competitor_control',
        'question': 'Was the transport shown to be specific for the substrate, by competition with an unlabelled substrate, an analogue or an inhibitor, or by a substituted ion?',
        'reads': ('facts.competitor_control_done',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_identity',
        'question': 'Was the label inside the vesicles shown to be the substrate itself and not a breakdown product?',
        'reads': ('facts.substrate_identity_shown',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'protein_amount_basis',
        'question': 'Was the protein actually incorporated into the proteoliposomes measured, so that a rate per mg is a rate per reconstituted protein and not per protein put into the mixture?',
        'reads': ('facts.protein_quantified_after_reconstitution',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'active_fraction',
        'question': 'Was the fraction of the reconstituted protein that is active and correctly oriented determined, so that a rate per molecule is not a rate per total protein?',
        'reads': ('facts.active_fraction_determined',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_rate_regime',
        'question': 'Is the rate an initial rate: taken from the part of the uptake time course where the uptake is still far from its plateau and the gradient has not run down?',
        'reads': ('quantities.uptake_percent_of_equilibrium', 'facts.linear_interval_shown'),
        'rule': 'A linear-interval fact stated as no fails. When the share of the plateau uptake reached is given the grader records it (equilibrium_percent, equilibrium_refs) and leaves the judgement to the sheet. Otherwise the linear-interval fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-interval fact is no'),
            ('unknown', 'equilibrium_recorded_for_the_sheet', 'the share of the plateau is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'linear_interval_stated', 'no share of the plateau is given and the fact is yes'),
            ('unknown', 'rate_regime_not_stated', 'no share of the plateau is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the substrate concentrations of the saturation series bracket the Km well enough to define it?',
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
        'question': 'Were there enough replicates, run as independent experiments (independent reconstitutions or protein preparations)?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated samples of one proteoliposome batch are not replicates.',
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
        'question': 'Is the substrate the protein\'s native substrate rather than an analogue or a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_protein',
        'question': 'Was the transport measured with a purified protein rather than a membrane extract or a crude preparation?',
        'reads': ('facts.purified_protein',),
        'rule': _one_fact_rule,
        'thresholds': (),
        'returns': _fact_returns,
    },
)
