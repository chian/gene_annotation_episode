"""The extracted record of ONE HPLC product-distribution experiment (type 'distribution_hplc', class product_distribution).

DRAFT 2026-11-22 (built by the SOP, steps 1 to 5; owner to confirm). The experiment: a reaction (or a reaction left to equilibrium) is stopped, its
species are separated by liquid chromatography (UV or diode-array, fluorescence, refractive-index, ELSD or CAD detection) and the peak areas are turned
into the share of one named product among the products, a ratio of two products, or the composition at equilibrium. The method says which products the
reaction gives and in what proportions. It is not how fast (activity_rate), not how complete (endpoint_conversion) and not a balance with a cofactor
(reaction_coupling). A UV area percent is a molar percent only when the species respond equally, so the response-factor facts matter here.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable',
value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('distribution_hplc'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized
               enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the
               extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity). The share or ratio
               is always read for ONE named product (the record's partner, an identity field given beside the answer):
                 product_fraction and product_fraction_spread                 fraction or percent   share of that product among the products formed
                 product_fraction_ratio and product_fraction_ratio_spread     dimensionless         that product over one other product (a:b is a / b)
                 equilibrium_fraction and equilibrium_fraction_spread         fraction or percent   share of that species in the mixture at equilibrium
                 equilibrium_ratio and equilibrium_ratio_spread               dimensionless         that species over the other side at equilibrium
               and the conditions that decide how far a share can be trusted:
                 total_recovery           fraction or percent   the sum of the quantified species over the amount of substrate applied (closure)
                 peak_resolution          dimensionless         the chromatographic resolution Rs between the product peak and its nearest neighbour
                 detection_limit          fraction or percent   the smallest share of a species the method detects (limit of detection)
                 replicate_count          count                 the number of independent replicate reactions
spread_kind    'standard_deviation', 'standard_error', 'confidence_interval', 'range' or None: what the spreads are.
fraction_basis 'mole', 'mass' or 'peak_area' or None: what the share is a share of (recorded, no criterion rests on it: a choice carries no span).
detector       'uv', 'diode_array', 'fluorescence', 'refractive_index', 'elsd' or 'cad' or None (recorded, no criterion rests on it).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, fraction_basis, detector), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Not in the record, and why: a share of 0 (a number must be above 0; "the product was not detected" is the fact claimed_product_detected answered no); the
relative response factor of each species (the fact response_factors_calibrated says whether the area was corrected; the factors themselves are
the paper's own constants and nothing here would judge them); the number of injections (repeated injections of one sample are technical repeats, not
replicates, and no criterion reads them).

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and
default it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's
answer).
"""

VERSION = 'a105_distribution_hplc_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_hplc'
QUANTITIES = ('product_fraction', 'product_fraction_spread', 'product_fraction_ratio', 'product_fraction_ratio_spread', 'equilibrium_fraction', 'equilibrium_fraction_spread',
              'equilibrium_ratio', 'equilibrium_ratio_spread', 'total_recovery', 'peak_resolution', 'detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_deviation', 'standard_error', 'confidence_interval', 'range')
FRACTION_BASES = ('mole', 'mass', 'peak_area')
DETECTORS = ('uv', 'diode_array', 'fluorescence', 'refractive_index', 'elsd', 'cad')
CHOICES = {'spread_kind': SPREAD_KINDS, 'fraction_basis': FRACTION_BASES, 'detector': DETECTORS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'authentic_standard_for_each_species': YES_NO, 'identity_confirmed_by_mass_or_nmr': YES_NO, 'response_factors_calibrated': YES_NO,
         'calibration_curves_for_each_species': YES_NO, 'fractions_share_one_denominator': YES_NO, 'all_products_identified': YES_NO, 'peaks_resolved': YES_NO,
         'enzyme_removed_or_quenched_before_injection': YES_NO, 'signals_within_calibration_range': YES_NO, 'no_enzyme_control_done': YES_NO,
         'inactive_enzyme_control_done': YES_NO, 'products_stable_under_assay_and_workup': YES_NO, 'distribution_stable_over_time': YES_NO,
         'approached_from_both_sides': YES_NO, 'independent_replicates': YES_NO, 'purified_enzyme': YES_NO, 'native_substrate': YES_NO,
         'claimed_product_detected': YES_NO}

SHARE_UNITS = ('fraction', 'percent')
# The quantities that are a share of a whole and so cannot exceed it (total_recovery can: a sum over the amount applied).
BOUNDED_SHARES = ('product_fraction', 'product_fraction_spread', 'equilibrium_fraction', 'equilibrium_fraction_spread', 'detection_limit')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'product_fraction': SHARE_UNITS, 'product_fraction_spread': SHARE_UNITS, 'product_fraction_ratio': ('dimensionless',), 'product_fraction_ratio_spread': ('dimensionless',),
         'equilibrium_fraction': SHARE_UNITS, 'equilibrium_fraction_spread': SHARE_UNITS, 'equilibrium_ratio': ('dimensionless',), 'equilibrium_ratio_spread': ('dimensionless',),
         'total_recovery': SHARE_UNITS, 'peak_resolution': ('dimensionless',), 'detection_limit': SHARE_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
