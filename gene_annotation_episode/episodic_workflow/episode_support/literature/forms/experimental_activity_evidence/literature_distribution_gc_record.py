"""The extracted record of ONE gas-chromatography product distribution (type 'distribution_gc', class product_distribution).

The GC type of the product_distribution class (drafted 2026-11-22 by the SOP, steps 1 to 5; the owner has not yet reviewed it). The method: the
products of an enzyme reaction (volatile, or made volatile by derivatization) are taken up in a solvent, adsorbed from the headspace or collected
on a fibre, injected into a gas chromatograph and separated on a column; each product is a peak, found by a flame-ionization detector (FID) or a
mass spectrometer (MS), and the area of each peak over the area of all product peaks is the share of that product (terpene spectra of a terpene
synthase, regio-isomers, chain lengths of a prenyl or fatty product). It reports which products the enzyme gives and in what proportion; it does not
report how fast (activity_rate), how much in total (endpoint_conversion) or the balance with a cofactor (reaction_coupling).

What can go wrong, and what the record keeps: a peak is named by an authentic standard, or only by a library match of its mass spectrum and its
retention index (isomers have almost the same mass spectrum, so the retention index carries the identity); a hot injector can rearrange or break a
product (a thermally labile sesquiterpene) so that the peak seen is not the product made; an FID area is nearly proportional to the carbon
burned, an MS ion count is not proportional to the amount, so an uncorrected area percent is a share of signal and not of molecules; unassigned peaks
left out of the total move every share; a product can be lost in the extraction (volatile products evaporate) or come from the solvent, the plastic or
the spontaneous chemistry of the substrate (the no-enzyme extract shows it); a minor product near the detection limit is a weak number.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status
'unavailable', value None and a reason; it is never 0 and never omitted. A product that the passage says was not detected has no share: it is
the fact claimed_product_detected answered no, never a share of 0.

Record fields
-------------
version, experiment_type ('distribution_gc'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used
               as decided 2026-11-22 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized enzyme and no
               surface, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction leaves
               all four None.
quantities     the effect, with the spread the passage gives for it, and the conditions that decide how far the share can be trusted:
                 product_fraction and product_fraction_spread            fraction or percent: the share of ONE named product (the record's partner) among
                                                                          the products formed (peak area percent of the product peaks)
                 product_fraction_ratio and product_fraction_ratio_spread  dimensionless: the share of that product over the share of another named
                                                                          product, that product in the numerator
                 identified_area_fraction                                 fraction or percent: the part of the total peak area that was assigned to
                                                                          identified compounds
                 minimum_integrated_share                                 fraction or percent: the smallest share of the total area the passage says it
                                                                          integrated, reported or could detect
                 extraction_recovery                                      fraction or percent: the share of the product (or of a standard added) found
                                                                          again after the extraction or sampling
                 retention_index_observed, retention_index_reference      dimensionless: the retention (Kovats) index the passage measured for the
                                                                          product and the one it compares with (a library or literature value)
                 replicate_count                                          count: the number of independent replicate reactions
spread_kind    'standard_error', 'standard_deviation' or 'confidence_interval' (what the spreads are), or None.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of the plain choice field (spread_kind), None when it is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

No top-level field outside these is used: the merge of several leaf records into one record (literature_grader_record.merged_record) understands only
this generic structure and drops any other field.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's
fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and
default it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the
model's answer).
"""

VERSION = 'a105_distribution_gc_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_gc'
QUANTITIES = ('product_fraction', 'product_fraction_spread', 'product_fraction_ratio', 'product_fraction_ratio_spread', 'identified_area_fraction',
              'minimum_integrated_share', 'extraction_recovery', 'retention_index_observed', 'retention_index_reference', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'identified_by_standard': YES_NO, 'identified_by_library_match': YES_NO, 'quantified_by_flame_ionization': YES_NO,
         'quantified_by_mass_spectrometry': YES_NO, 'response_factors_calibrated': YES_NO, 'all_peaks_in_denominator': YES_NO,
         'injector_stability_checked': YES_NO, 'products_stable_under_assay_and_workup': YES_NO, 'no_enzyme_control_done': YES_NO,
         'inactive_enzyme_control_done': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO,
         'claimed_product_detected': YES_NO}

SHARE_UNITS = ('fraction', 'percent')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'product_fraction': SHARE_UNITS, 'product_fraction_spread': SHARE_UNITS, 'product_fraction_ratio': ('dimensionless',),
         'product_fraction_ratio_spread': ('dimensionless',), 'identified_area_fraction': SHARE_UNITS, 'minimum_integrated_share': SHARE_UNITS,
         'extraction_recovery': SHARE_UNITS, 'retention_index_observed': ('dimensionless',), 'retention_index_reference': ('dimensionless',),
         'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
