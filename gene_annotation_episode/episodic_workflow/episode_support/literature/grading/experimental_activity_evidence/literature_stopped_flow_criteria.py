"""Stopped_flow criteria: the ONE place where the grader's criteria of a stopped-flow rapid-mixing enzyme experiment are declared.

DRAFT of 2026-11-22 for the owner to correct, copied in structure from literature_spectro_direct_criteria.py.

This file is the single source for what the stopped_flow grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the dead time against the fastest rate constant, the enzyme over the
substrate, the burst amplitude per active site, the substrate series against the half-saturation concentration, the number of shots averaged, the
replicate count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet';
the judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_stopped_flow_converter.py. The logic that answers each question
is in literature_stopped_flow_grader.py (one short function per criterion, same order). The only constants here are unit conversions fixed by
definition (below); nothing else is compared.

How to read an entry in STOPPED_FLOW_CRITERIA
---------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_stopped_flow_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_stopped_flow_criteria_v1'
PER_SECOND = {'s^-1': 1.0, 'min^-1': 1.0 / 60.0}      # FIXED_BY_DEFINITION: a rate constant in min^-1 is a sixtieth of the same in s^-1.
SECONDS = {'ms': 0.001, 's': 1.0}                     # FIXED_BY_DEFINITION: a millisecond is a thousandth of a second.
PER_SITE_UNIT = 'mol/mol_site'                        # FIXED_BY_DEFINITION: the unit spelling of an amount per active site of the enzyme.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

STOPPED_FLOW_CRITERIA = (
    {
        'id': 'spontaneous_reaction_control',
        'question': 'Was the spontaneous (non-enzymatic) change of the substrate measured and set aside, by a no-enzyme control or an inactive-enzyme control?',
        'reads': ('facts.no_enzyme_control', 'facts.inactive_enzyme_control'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'spontaneous_reaction_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'enzyme_only_signal',
        'question': 'Was the signal change that happens without the substrate (mixing or dilution artefact, a change of the enzyme alone) measured with the enzyme mixed with buffer?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'phase_assignment',
        'question': 'Is the observed phase of the signal assigned to the chemical step of the reaction (product formation or substrate consumption) and not to binding or a conformational change?',
        'reads': ('facts.phase_assigned_to_chemical_step',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product (or an intermediate) behind the signal identified by another measurement?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'dead_time_coverage',
        'question': 'Is the fastest rate constant slow enough, against the dead time of the instrument, for the phase to have been seen?',
        'reads': ('quantities.dead_time', 'quantities.single_turnover_rate', 'quantities.observed_rate_constant'),
        'rule': 'When the dead time and at least one of the single-turnover rate constant and the observed rate constant are given, the grader records the dead time in seconds (dead_time_s) and the largest of those rate constants in s^-1 (fastest_rate_per_s) with their refs (dead_time_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'dead_time_recorded_for_the_sheet', 'the dead time and a rate constant are given: both are recorded and the sheet judges them'),
            ('unknown', 'dead_time_or_rate_missing', 'the dead time or both rate constants are not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'enzyme_excess',
        'question': 'Where the experiment is called single turnover, is the enzyme really in excess over the substrate?',
        'reads': ('facts.single_turnover_conditions', 'quantities.enzyme_concentration', 'quantities.substrate_concentration'),
        'rule': 'A passage that states multiple-turnover conditions (the fact is no) leaves the question not applicable. The fact unknown is unknown. The fact yes with the enzyme and the substrate concentrations both given is recorded (enzyme_over_substrate, dimensionless, with enzyme_excess_refs) and left to the sheet; the fact yes without both concentrations is supported by the statement itself.',
        'thresholds': (),
        'returns': (
            ('not_applicable', 'multiple_turnover_stated', 'the fact is no: the passage states substrate in excess'),
            ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
            ('unknown', 'single_turnover_not_stated', 'the fact is unknown'),
            ('supported', 'single_turnover_stated', 'the fact is yes and the enzyme or the substrate concentration is not given'),
            ('unknown', 'enzyme_excess_recorded_for_the_sheet', 'the fact is yes and both concentrations are given: the ratio is recorded and the sheet judges it'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the substrate concentrations at which k_obs was measured bracket the half-saturation concentration well enough to define the limiting rate constant?',
        'reads': ('quantities.half_saturation_concentration', 'concentration_series'),
        'rule': 'When the half-saturation concentration and the series are both given the grader records the number of concentrations (concentration_count), the lowest and the highest over the half-saturation concentration (concentration_low_over_half, concentration_high_over_half) and their refs (concentration_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'substrate_series_recorded_for_the_sheet', 'the half-saturation concentration and the series are given: the count and the two ratios are recorded and the sheet judges them'),
            ('unknown', 'half_saturation_or_series_missing', 'the half-saturation concentration or the series is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'active_enzyme_amount',
        'question': 'Was the amount of active enzyme determined (an active-site titration or an equivalent), so that the enzyme concentration is not the total protein?',
        'reads': ('facts.active_site_concentration_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'burst_amplitude',
        'question': 'Does the burst, per active site of the enzyme, show that the phase belongs to the main population of the enzyme and not to a small part of it?',
        'reads': ('quantities.burst_amplitude', 'quantities.enzyme_concentration'),
        'rule': 'A burst given per active site is recorded as it is; a burst given as a concentration is recorded over the enzyme concentration when that is given (burst_per_site, with burst_refs) and the judgement is left to the sheet; a burst as a concentration without the enzyme concentration, or no burst, is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'burst_amplitude_recorded_for_the_sheet', 'the burst per active site is given or can be formed: it is recorded and the sheet judges it'),
            ('unknown', 'burst_amplitude_needs_enzyme_concentration', 'the burst is a concentration and the enzyme concentration is not given'),
            ('unknown', 'burst_amplitude_not_stated', 'no burst is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'shots_averaged',
        'question': 'Were enough shots averaged into one trace?',
        'reads': ('quantities.shots_averaged',),
        'rule': 'A stated number is recorded (shots_averaged, shots_refs) and the judgement is left to the sheet; otherwise unknown. Shots of one mixture are technical repeats: they lower the noise of a trace and say nothing of independent experiments.',
        'thresholds': (),
        'returns': (
            ('unknown', 'shots_recorded_for_the_sheet', 'the number of shots is given: it is recorded and the sheet judges it'),
            ('unknown', 'shots_averaged_not_stated', 'the number of shots is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated shots of one reaction mixture are not replicates.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'native_reaction',
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the experiment done with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
