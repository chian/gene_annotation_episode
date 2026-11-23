"""Endpoint_optical_plateau criteria: the ONE place where the grader's criteria of a reaction run to an optical plateau are declared. DRAFT 2026-11-22,
owner to correct.

This file is the single source for what the endpoint_optical_plateau grader asks. The grader reports FACTS and holds NO threshold that judges goodness:
where a criterion needs a number to be compared with a limit (how large the no-enzyme baseline is against the signal, how well the full-conversion signal
agrees with the extinction coefficient, how far the signal change is from the full-conversion change, the highest absorbance, the replicate count), the
grader records the number with its support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its
EXPERT_REVIEW constants are on the sheet side, in literature_endpoint_optical_plateau_converter.py. The logic that answers each question is in
literature_endpoint_optical_plateau_grader.py (one short function per criterion, same order).

The only constants here are unit conversions, FIXED_BY_DEFINITION (a percent is a hundredth, 1 mM is 1e-3 M, 1 mm is 0.1 cm, 1 mM^-1 cm^-1 is 1000 M^-1 cm^-1):
they turn the stated units into the ones a ratio is formed in, and nothing is compared with them.

How to read an entry in ENDPOINT_OPTICAL_PLATEAU_CRITERIA
-----------------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_endpoint_optical_plateau_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (unit conversions only: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_endpoint_optical_plateau_criteria'

FRACTION_PER_UNIT = {'percent': 0.01, 'fraction': 1.0}      # FIXED_BY_DEFINITION: a percent is a hundredth.
M_PER_UNIT = {'nM': 1e-9, 'uM': 1e-6, 'mM': 1e-3}      # FIXED_BY_DEFINITION: the molar scale of a concentration unit.
CM_PER_UNIT = {'cm': 1.0, 'mm': 0.1}      # FIXED_BY_DEFINITION: a millimetre is a tenth of a centimetre.
PER_M_CM_PER_UNIT = {'M^-1 cm^-1': 1.0, 'mM^-1 cm^-1': 1000.0}      # FIXED_BY_DEFINITION: an extinction coefficient in mM^-1 cm^-1 is 1000 times its value in M^-1 cm^-1.

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

ENDPOINT_OPTICAL_PLATEAU_CRITERIA = (
    {
        'id': 'readout_stated',
        'question': 'Are the readout channel (the wavelength) and the denominator (the starting substrate concentration) stated for this estimate?',
        'reads': ('quantities.wavelength', 'quantities.substrate_initial'),
        'rule': 'Both stated is supported; either missing is unknown (an estimate whose channel or denominator is not stated is not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'wavelength_and_substrate_stated', 'both are given'),
            ('unknown', 'wavelength_or_substrate_missing', 'either is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'baseline_control',
        'question': 'Was the spontaneous (non-enzymatic) signal change of the substrate or product measured and set aside, by a no-enzyme baseline or an inactive-enzyme control?',
        'reads': ('facts.no_enzyme_control_done', 'facts.inactive_enzyme_control_done'),
        'rule': 'Either control stated as done is enough. If neither is stated as done and one is stated as not done, it fails. A control stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'baseline_control_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'baseline_level',
        'question': 'How large is the signal of the no-enzyme or inactive-enzyme control against the signal of the test?',
        'reads': ('quantities.control_conversion', 'quantities.conversion_percent', 'quantities.signal_change_baseline', 'quantities.signal_change_total'),
        'rule': 'When a control conversion and the test conversion are both given, or a baseline signal change and the test signal change are given in the same unit, the grader records the control conversion over the test conversion (control_over_test) and the baseline over the test signal change (baseline_over_signal, each only when it can be formed) with their refs (baseline_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('FRACTION_PER_UNIT',),
        'returns': (
            ('unknown', 'baseline_level_recorded_for_the_sheet', 'at least one ratio can be formed: the ratios are recorded and the sheet judges them'),
            ('unknown', 'baseline_level_not_stated', 'no control conversion beside a test conversion, and no baseline and test signal change in one unit'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'control_same_window',
        'question': 'Was the control followed over the same time as the reaction, so that the baseline covers the whole time to the plateau?',
        'reads': ('facts.control_read_over_same_time',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'calibration_basis',
        'question': 'Is the signal change turned into a conversion by a calibration: a full-conversion reference, or an extinction coefficient with its wavelength?',
        'reads': ('facts.full_conversion_reference_done', 'quantities.extinction_coefficient', 'quantities.wavelength'),
        'rule': 'A full-conversion reference stated as done is supported; so is an extinction coefficient stated with its wavelength. If neither holds and the reference is stated as not done, it fails. Otherwise unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'full_conversion_reference_stated', 'the full-conversion reference fact is yes'),
            ('supported', 'extinction_coefficient_and_wavelength_stated', 'the reference is not yes and the extinction coefficient and the wavelength are both given'),
            ('conflicting', 'fact_answered_no', 'the reference is no and the extinction coefficient or the wavelength is not given'),
            ('unknown', 'calibration_basis_not_stated', 'none of the above'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'calibration_agreement',
        'question': 'Does the signal change of the full-conversion reference agree with the one the extinction coefficient, the path length and the starting substrate concentration predict?',
        'reads': ('quantities.signal_change_full', 'quantities.extinction_coefficient', 'quantities.path_length', 'quantities.substrate_initial'),
        'rule': 'When the full-conversion signal change is given in absorbance units together with the extinction coefficient, the path length and the starting substrate concentration, the grader records the stated full-conversion change over the predicted one, extinction coefficient times path length times substrate concentration (full_over_expected, dimensionless) with their refs (calibration_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': ('M_PER_UNIT', 'CM_PER_UNIT', 'PER_M_CM_PER_UNIT'),
        'returns': (
            ('unknown', 'calibration_agreement_recorded_for_the_sheet', 'the four are given and the full-conversion change is in absorbance units: the ratio is recorded and the sheet judges it'),
            ('unknown', 'calibration_agreement_inputs_missing', 'any of the four is not given, or the full-conversion change is not in absorbance units'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'signal_linear_range',
        'question': 'Did the signal stay in the range where the detector is linear with the concentration?',
        'reads': ('quantities.absorbance_max', 'facts.signal_in_linear_range'),
        'rule': 'A linear-range fact stated as no fails. When the highest absorbance is given the grader records it (absorbance_max) with its ref (absorbance_refs) and leaves the judgement to the sheet. Otherwise the linear-range fact stated as yes is supported, and silence is unknown.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'fact_answered_no', 'the linear-range fact is no'),
            ('unknown', 'absorbance_recorded_for_the_sheet', 'the highest absorbance is given and the fact is not no: it is recorded and the sheet judges it'),
            ('supported', 'signal_in_linear_range_stated', 'no highest absorbance is given and the fact is yes'),
            ('unknown', 'linear_range_not_stated', 'no highest absorbance is given and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'inner_filter_check',
        'question': 'Was the inner-filter effect, quenching or absorbance of the other components at the read wavelength checked or corrected at the substrate concentration used?',
        'reads': ('facts.inner_filter_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'enzyme_dependence',
        'question': 'Was the signal change shown to depend on the enzyme (it grows with the enzyme amount, or is lost with an inactive enzyme or an inhibitor)?',
        'reads': ('facts.enzyme_dependence_shown',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'plateau_reached',
        'question': 'Is the end point a true plateau (the signal stayed constant after it was reached), not a point on a slope?',
        'reads': ('facts.plateau_stable',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'initial_substrate_determined',
        'question': 'Was the starting amount of the substrate, the denominator of the conversion, measured rather than taken as nominal?',
        'reads': ('facts.initial_substrate_determined',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'conversion_within_full_scale',
        'question': 'Is the final signal change of the test no larger than the signal change of complete conversion, the scale the fraction is taken on?',
        'reads': ('quantities.signal_change_total', 'quantities.signal_change_full'),
        'rule': 'When the test signal change and the full-conversion signal change are both given in the same unit the grader records the first over the second (signal_over_full, dimensionless) with their refs (full_scale_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'full_scale_recorded_for_the_sheet', 'both are given in one unit: the ratio is recorded and the sheet judges it'),
            ('unknown', 'full_scale_comparison_missing', 'either is not given, or the two units differ'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'product_identity',
        'question': 'Was the signal change shown to be the claimed reaction (the product identified by another measurement against a standard)?',
        'reads': ('facts.product_identified_by_standard',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'replicates',
        'question': 'Were there enough replicates, run as independent experiments?',
        'reads': ('quantities.replicate_count', 'facts.independent_replicates'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet. Repeated reads of one reaction mixture are not replicates.',
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
        'question': 'Is the substrate the enzyme\'s native substrate rather than a surrogate (a chromogenic or fluorogenic analogue)?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the conversion measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
