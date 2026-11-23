"""The extracted record of ONE electrophoretic product-distribution experiment (type 'distribution_gel_bands', class product_distribution).

DRAFT 2026-11-22 (owner to correct), built from the SOP steps 1 to 3 and 5 on the shape of the spectro_direct record, with the product_distribution class core
(docs/axis_restructure_20261117/A105_PRODUCT_DISTRIBUTION_INVENTORY.md section 2) in place of the activity class core. The experiment: a reaction mixture is
stopped and its products are separated by size on a gel or in a capillary (denaturing polyacrylamide gel of nucleic acids, capillary fragment analysis, SDS-PAGE of
cleavage products, a sequencing ladder beside the cleavage products), each band or peak is read by densitometry or fragment analysis, and the share of each product
length or cleavage site is stated: the share of the claimed product among the products, or the ratio of two of them.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason;
it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('distribution_gel_bands'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The enzyme preparation is the
               analyte_preparation_ref; this type has no immobilized enzyme, no surface and no electrode, so immobilized_preparation_ref and surface_ref stay None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     the effect quantities of the class core that a gel states, each with the spread the passage gives for it:
                 product_fraction and product_fraction_spread               fraction or percent: the share of ONE named product (the record's partner) among the
                                                                            products formed, read from the band or peak intensities of one lane
                 product_fraction_ratio and product_fraction_ratio_spread   dimensionless: the ratio of the partner's share to the share of one other product
                                                                            (the partner is the numerator; "a:b" is a/b)
               and the conditions that decide how far a share can be trusted:
                 total_recovery                  fraction or percent   the signal of the counted bands over the signal of the whole lane (or the input), when stated
                 substrate_conversion            fraction or percent   the share of the substrate converted when the lane was read
                 minor_species_detection_limit   fraction or percent   the smallest share of the lane the passage says a band can be detected or quantified at
                 replicate_count                 count                 the number of independent replicate reactions
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval', 'range' or None: what the spreads are.
labelling      'end_labelled', 'uniformly_labelled', 'stained' or 'fluorescent_tag' or None: how the products were made visible. Kept in the record for the reviewer; no
               criterion rests on it (a choice holds no span in the merged record). What matters for the share, equal signal per molecule, is two FACTS.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (spread_kind, labelling), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Not in this record, on purpose: the size of a fragment, the position of a cleavage site and the gel percentage. They identify a band but nothing judges them (the size
marker lane, a fact, is what makes the assignment); a field that nothing reads is not asked. The identity block (target, partner, temperature, pH) is added by the
identity extraction and is not part of this form.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well
its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the
topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The
grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_distribution_gel_bands_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_gel_bands'
QUANTITIES = ('product_fraction', 'product_fraction_spread', 'product_fraction_ratio', 'product_fraction_ratio_spread', 'total_recovery', 'substrate_conversion',
              'minor_species_detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval', 'range')
LABELLINGS = ('end_labelled', 'uniformly_labelled', 'stained', 'fluorescent_tag')
# The plain choice fields of the record (name -> vocabulary): kept for the reviewer, never read by a criterion.
CHOICES = {'spread_kind': SPREAD_KINDS, 'labelling': LABELLINGS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'size_markers_run': YES_NO, 'bands_resolved': YES_NO, 'end_labelled_so_equal_response': YES_NO, 'response_corrected_for_length': YES_NO,
         'all_bands_in_denominator': YES_NO, 'within_linear_range': YES_NO, 'reaction_quenched_before_loading': YES_NO, 'background_subtracted': YES_NO,
         'no_enzyme_lane': YES_NO, 'substrate_only_lane': YES_NO, 'inactive_enzyme_lane': YES_NO, 'primary_products_only': YES_NO,
         'independent_replicates': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'claimed_product_detected': YES_NO}

SHARE_UNITS = ('fraction', 'percent')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'product_fraction': SHARE_UNITS, 'product_fraction_spread': SHARE_UNITS, 'product_fraction_ratio': ('dimensionless',), 'product_fraction_ratio_spread': ('dimensionless',),
         'total_recovery': SHARE_UNITS, 'substrate_conversion': SHARE_UNITS, 'minor_species_detection_limit': SHARE_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
