"""Protein_film_electrochem criteria: the ONE place where the grader's criteria of a protein-film electrochemistry experiment are declared.

This file is the single source for what the protein_film_electrochem grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the film loss, the substrate series against the Km, the replicate
count), the grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in literature_protein_film_electrochem_converter.py. The logic that answers
each question is in literature_protein_film_electrochem_grader.py (one short function per criterion, same order). There is no constant here:
a concentration unit is turned into nM by the reader's fixed scale table (FIXED_BY_DEFINITION), and nothing else is compared.

How to read an entry in PROTEIN_FILM_ELECTROCHEM_CRITERIA
---------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_protein_film_electrochem_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_protein_film_electrochem_criteria_v1'

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

PROTEIN_FILM_ELECTROCHEM_CRITERIA = (
    {
        'id': 'bare_electrode_control',
        'question': 'Was the bare electrode (no enzyme film) measured with the substrate, so that the current the substrate gives at the electrode itself is known?',
        'reads': ('facts.bare_electrode_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_free_baseline',
        'question': 'Was the enzyme film also measured without the substrate (a baseline or the non-turnover response), so that the catalytic current is the part that needs the substrate?',
        'reads': ('facts.no_substrate_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'substrate_dependence',
        'question': 'Was the catalytic current shown to depend on the substrate (it rises when the substrate is added or raised and falls when it is removed)?',
        'reads': ('facts.substrate_dependent_current',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product of the reaction behind the catalytic current identified by another measurement?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'potential_reference',
        'question': 'Is the electrode potential of the measurement stated against a named reference electrode?',
        'reads': ('facts.potential_referenced',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'electrode_area',
        'question': 'Is the electrode area stated, by which the current is divided or against which it is reported?',
        'reads': ('facts.electrode_area_stated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'mass_transport_excluded',
        'question': 'Was mass transport of the substrate to the film removed or shown not to limit the current (a rotating electrode, or a current independent of the rotation rate)?',
        'reads': ('facts.mass_transport_excluded',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'steady_state_wave',
        'question': 'Is the catalytic current a steady-state wave (a sigmoidal wave or plateau that does not depend on the scan rate or the time)?',
        'reads': ('facts.steady_state_wave',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'electroactive_amount',
        'question': 'Was the electroactive amount of enzyme measured on the film itself (for example from the non-turnover redox signal), so that a current is a rate per enzyme and not a rate per protein applied?',
        'reads': ('facts.electroactive_coverage_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'film_stability',
        'question': 'Did the enzyme film stay on the electrode and active during the measurement, or was its loss corrected for?',
        'reads': ('quantities.film_loss_percent', 'facts.film_loss_corrected'),
        'rule': 'A loss stated as corrected for is supported. Otherwise, when the share of the signal lost is given, the grader records it (film_loss_percent, film_loss_refs) and leaves the judgement to the sheet. Otherwise a loss stated as not corrected fails, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'film_loss_correction_stated', 'the loss is stated as corrected for'),
            ('unknown', 'film_loss_recorded_for_the_sheet', 'the loss is not stated as corrected, the share lost is given: it is recorded and the sheet judges it'),
            ('conflicting', 'fact_answered_no', 'the loss is stated as not corrected and no share lost is given'),
            ('unknown', 'film_loss_not_stated', 'neither the correction nor the share lost is stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'substrate_range',
        'question': 'Did the substrate concentrations of the current-against-substrate curve bracket the Km well enough to define it?',
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
        'question': 'Were there enough replicates, run as independent films or electrodes?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated scans of one film are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate or a mediator reaction?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the film made of the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
