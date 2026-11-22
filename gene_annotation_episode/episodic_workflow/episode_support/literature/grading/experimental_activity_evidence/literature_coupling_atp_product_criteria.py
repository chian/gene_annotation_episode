"""Coupling_atp_product criteria: the ONE place where the grader's criteria of a nucleotide-hydrolysis-to-product coupling experiment are declared.

This file is the single source for what the coupling_atp_product grader asks. The grader reports FACTS and holds NO threshold that judges
goodness: where a criterion needs a number to be compared with a limit (the basal share of the hydrolysis rate, the share of the nucleotide
hydrolysed, the link against the bound its own coefficient allows, the replicate count), the grader records the number with its support refs and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_coupling_atp_product_converter.py. The logic that answers each question is in literature_coupling_atp_product_grader.py (one short
function per criterion, same order). The only constant here is the unit table of the two rates (FIXED_BY_DEFINITION), which lets the grader
record the basal rate over the total rate; nothing else is compared.

How to read an entry in COUPLING_ATP_PRODUCT_CRITERIA
-----------------------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_coupling_atp_product_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants of this file the rule uses (none: the judgement is on the sheet side)
returns     every case the criterion can return, as (status, reason_code, when). Statuses are the existing A105 vocabulary:
            supported / unknown / conflicting / not_applicable. 'conflicting' means the record shows the standard is NOT met.
            'unknown' means the record does not say; missing information is never read as met and never as unmet. A status listed
            as 'never' cannot occur for this criterion.
"""

VERSION = 'a105_coupling_atp_product_criteria_v1'

# FIXED_BY_DEFINITION: each rate unit of the record's vocabulary -> (the kind of rate, the exact factor to the kind's own base unit). Only rates of the
# same kind are compared (the basal rate over the total rate). Base units: amount_per_min umol/min; amount_per_min_per_mg umol/min/mg;
# concentration_per_min uM/min; per_enzyme_per_min min^-1. 1 nmol is 1e-3 umol, 1 pmol is 1e-6 umol, 60 s is 1 min.
RATE_UNIT_SCALE = {
    'umol/min': ('amount_per_min', 1.0), 'nmol/min': ('amount_per_min', 1.0e-3), 'pmol/min': ('amount_per_min', 1.0e-6), 'nmol/s': ('amount_per_min', 0.06),
    'umol/min/mg': ('amount_per_min_per_mg', 1.0), 'nmol/min/mg': ('amount_per_min_per_mg', 1.0e-3), 'pmol/min/mg': ('amount_per_min_per_mg', 1.0e-6),
    'uM/min': ('concentration_per_min', 1.0), 'uM/s': ('concentration_per_min', 60.0),
    's^-1': ('per_enzyme_per_min', 60.0), 'min^-1': ('per_enzyme_per_min', 1.0),
}

_fact_returns = (
    ('supported', 'facts_answered_yes', 'the fact is yes'),
    ('conflicting', 'fact_answered_no', 'the fact is no'),
    ('unknown', 'fact_unknown', 'the fact is unknown'),
    ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable'),
)

COUPLING_ATP_PRODUCT_CRITERIA = (
    {
        'id': 'no_enzyme_control',
        'question': 'Was the non-enzymatic hydrolysis of the nucleotide measured with a control without the enzyme?',
        'reads': ('facts.no_enzyme_control',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'reagent_blank',
        'question': 'Was the free phosphate (or ADP) already in the nucleotide stock and the reagents measured in a blank and set aside?',
        'reads': ('facts.reagent_blank_done',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'basal_rate_accounted',
        'question': 'Was the basal (substrate-free or partner-free) nucleotide hydrolysis taken off, so that the link is not diluted by hydrolysis that makes no product?',
        'reads': ('facts.basal_rate_subtracted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'basal_share',
        'question': 'Is the basal hydrolysis small against the hydrolysis of the reaction that makes the product, so that taking it off leaves a net hydrolysis that is well determined?',
        'reads': ('quantities.basal_rate', 'quantities.nucleotide_rate'),
        'rule': 'When both rates are given in rates of the same kind the grader records the basal rate over the total rate (basal_share, dimensionless) with their refs (basal_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'basal_share_recorded_for_the_sheet', 'both rates are given in rates of one kind: the share is recorded and the sheet judges it'),
            ('unknown', 'basal_or_total_rate_missing', 'either rate is not given'),
            ('unknown', 'rate_units_not_comparable', 'both rates are given but they are rates of different kinds (a rate per mg and a rate per enzyme)'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'reporter_capacity',
        'question': 'Did the hydrolysis reporter keep up with the flux: the coupling enzymes in excess, or the phosphate or NADH signal inside the linear range of its standard curve?',
        'reads': ('facts.coupling_enzymes_in_excess', 'facts.signal_in_linear_range'),
        'rule': 'Either fact stated as yes is enough. If neither is stated as yes and one is stated as no, it fails. A fact stated nowhere is unknown, never no.',
        'thresholds': (),
        'returns': (
            ('supported', 'reporter_capacity_stated', 'either fact is yes'),
            ('conflicting', 'fact_answered_no', 'neither is yes and a fact is no'),
            ('unknown', 'fact_unknown', 'neither is yes, none is no, a fact is unknown'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable'),
        ),
    },
    {
        'id': 'nucleotide_supply',
        'question': 'Did the nucleotide stay available and the ADP stay low over the measurement, by a regenerating system or by a small share of the nucleotide hydrolysed?',
        'reads': ('facts.nucleotide_regenerated', 'quantities.nucleotide_consumed_percent'),
        'rule': 'A regenerating system stated as yes is supported. Otherwise, when the share of the nucleotide hydrolysed is given the grader records it (consumed_percent, consumed_refs) and leaves the judgement to the sheet. Otherwise unknown. A regenerating system stated as no is not a failure by itself.',
        'thresholds': (),
        'returns': (
            ('supported', 'nucleotide_regenerated_stated', 'the regenerating-system fact is yes'),
            ('unknown', 'consumed_recorded_for_the_sheet', 'the fact is not yes and the share hydrolysed is given: it is recorded and the sheet judges it'),
            ('unknown', 'nucleotide_supply_not_stated', 'the fact is not yes and no share hydrolysed is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'hydrolysis_dependence',
        'question': 'Was the product shown to depend on the nucleotide hydrolysis (no product without the nucleotide, with a non-hydrolysable analogue or with a hydrolysis-dead mutant)?',
        'reads': ('facts.product_requires_hydrolysis',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_identity',
        'question': 'Was the product identified by another measurement (a standard, mass spectrometry, NMR) rather than inferred?',
        'reads': ('facts.product_identified',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'product_calibration',
        'question': 'Was the amount of product calibrated with a standard?',
        'reads': ('facts.product_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'nucleotide_calibration',
        'question': 'Was the nucleotide hydrolysis side calibrated (a phosphate standard curve, the NADH extinction coefficient, the specific radioactivity of the 32P nucleotide or an ADP standard)?',
        'reads': ('facts.nucleotide_side_calibrated',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_mixture',
        'question': 'Were the hydrolysis and the product measured in the same reaction mixture?',
        'reads': ('facts.same_mixture',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'same_window',
        'question': 'Were the hydrolysis and the product measured over the same time window?',
        'reads': ('facts.same_window',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'coefficient_stated',
        'question': 'Is the number of nucleotides one product needs, by the paper\'s own account of the reaction, stated, so that a cost per product can be read as a share?',
        'reads': ('quantities.stoichiometric_coefficient',),
        'rule': 'Stated is supported; not stated is unknown (a link without its reaction account is a bare ratio, not shown wrong).',
        'thresholds': (),
        'returns': (
            ('supported', 'coefficient_stated', 'the coefficient is given'),
            ('unknown', 'coefficient_not_stated', 'the coefficient is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'coupling_within_bound',
        'question': 'Does the stated link stay within what the reaction\'s own coefficient allows (no more product than the hydrolysed nucleotide can make)?',
        'reads': ('quantities.productive_fraction', 'quantities.nucleotides_per_product', 'quantities.stoichiometric_ratio', 'quantities.stoichiometric_coefficient'),
        'rule': 'When a productive fraction is stated, or the coefficient and either the nucleotides per product or the product per nucleotide are stated, the grader records which numbers it rests on (link_refs) and leaves the judgement to the sheet; otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'link_recorded_for_the_sheet', 'a productive fraction can be read from the stated numbers: their refs are recorded and the sheet judges it'),
            ('unknown', 'productive_fraction_not_available', 'no productive fraction is stated and the coefficient or the link is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
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
        'question': 'Is the substrate (and nucleotide) the enzyme\'s native one rather than a surrogate or an analogue?',
        'reads': ('facts.native_substrate',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
    {
        'id': 'purified_enzyme',
        'question': 'Was the coupling measured with the purified enzyme rather than a cell extract or lysate?',
        'reads': ('facts.purified_enzyme',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': _fact_returns,
    },
)
