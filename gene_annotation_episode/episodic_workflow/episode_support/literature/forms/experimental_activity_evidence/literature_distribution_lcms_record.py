"""The extracted record of ONE LC-MS or LC-MS/MS product-profile experiment (type 'distribution_lcms', class product_distribution).

DRAFT 2026-11-22 (owner to confirm), built by the A105 experiment SOP (steps 1 to 5) on the structure of 'spectro_direct', the first type built outside the binding class.
The experiment: an enzyme reaction gives one or several products; the reaction is stopped, the species are separated by liquid chromatography and each one is read by
its mass-spectrometric signal (an extracted ion chromatogram, or a selected or multiple reaction monitoring transition). The paper states the SHARE of one product
among the products (as a percent or fraction of the summed signal or amount), or the RATIO of two products. The share is quantitative only when each species is calibrated
on its own (an authentic standard with its own calibration curve, or an isotope-labelled internal standard of the species): an ion signal is not a molar amount,
because the ionisation efficiency differs between species, sometimes by orders of magnitude, and ion suppression by the matrix changes it again.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason;
it is never 0 and never omitted. The one exception is a product share that the passage states as zero: that is a stated point value 0 (the product was not
found), and only the share of a product may be 0.

Class core used (the product_distribution class, docs/axis_restructure_20261117/A105_PRODUCT_DISTRIBUTION_INVENTORY.md section 2): the effect of the class is the share of
the CLAIMED product among the products (a fraction), or a ratio of two products with the claimed product in the numerator. The claimed product is the record's
partner (the identity block's partner_id). The two equilibrium quantities of the class (equilibrium_fraction, equilibrium_ratio) are NOT recorded for this type: an
LC-MS product profile reports what a reaction gave, not where its equilibrium lies, and its own entry in the inventory (3.4) names no equilibrium evidence.

Record fields
-------------
version, experiment_type ('distribution_lcms'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as for the
               activity types (decided 2026-11-21, owner to confirm): the enzyme preparation is the analyte_preparation_ref; no type of this class has an immobilized
               enzyme, a surface or an electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the
               extraction leaves all four None.
quantities     the effect quantities of the type, each with the spread the passage gives for it (the unit of the quantity):
                 product_fraction and product_fraction_spread                 fraction or percent   the share of the product named as the partner among the products
                 product_fraction_ratio and product_fraction_ratio_spread     dimensionless         the ratio of that product to another product (partner in the numerator)
               and what decides how far a share can be trusted:
                 total_recovery           fraction or percent   the sum of the species measured over the amount at the start (closure)
                 product_concentration    nM, uM or mM          the concentration of the product named as the partner in the measured sample
                 limit_of_quantification  nM, uM or mM          the lowest concentration the method quantifies (the lower limit of quantification)
                 replicate_count          count                 the number of independent replicate reactions
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
fraction_basis 'mole', 'ion_signal' or 'mass' or None: what the share is a share of. Kept in the record for the reviewer; no criterion rests on a choice (a choice holds
               no span in the merged record). What a criterion needs about calibration is a yes/no fact (calibrated_per_species, isotope_labelled_internal_standard).
ionization_mode 'positive', 'negative' or 'both' or None: kept for the reviewer, as above.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, fraction_basis, ionization_mode), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well
its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on
the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The
grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_distribution_lcms_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_lcms'
QUANTITIES = ('product_fraction', 'product_fraction_spread', 'product_fraction_ratio', 'product_fraction_ratio_spread', 'total_recovery', 'product_concentration',
              'limit_of_quantification', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FRACTION_BASES = ('mole', 'ion_signal', 'mass')
IONIZATION_MODES = ('positive', 'negative', 'both')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'authentic_standard_for_each_species': YES_NO, 'calibrated_per_species': YES_NO, 'isotope_labelled_internal_standard': YES_NO,
         'matrix_matched_calibration': YES_NO, 'ion_suppression_checked': YES_NO, 'signals_within_calibration_range': YES_NO,
         'fractions_share_one_denominator': YES_NO, 'all_products_identified': YES_NO, 'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO,
         'enzyme_removed_or_quenched_before_analysis': YES_NO, 'products_stable_under_assay_and_workup': YES_NO, 'independent_replicates': YES_NO,
         'purified_enzyme': YES_NO, 'native_substrate': YES_NO, 'claimed_product_detected': YES_NO}

FRACTION_UNITS = ('fraction', 'percent')
CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'product_fraction': FRACTION_UNITS, 'product_fraction_spread': FRACTION_UNITS, 'product_fraction_ratio': ('dimensionless',),
         'product_fraction_ratio_spread': ('dimensionless',), 'total_recovery': FRACTION_UNITS, 'product_concentration': CONCENTRATION_UNITS,
         'limit_of_quantification': CONCENTRATION_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
