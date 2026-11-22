"""The extracted record of ONE radiolabelled product-distribution experiment (type 'distribution_radio_tlc', class product_distribution).

DRAFT 2026-11-22 (first draft of the type, owner to correct); built from the shape of literature_spectro_direct_record.py. The experiment: one enzyme is
incubated with a radiolabelled substrate (14C, 3H, 32P, 33P or 35S), the products are separated on a thin-layer plate (TLC), by radio-HPLC or on a gel,
and the label of each separated species is counted (scintillation of scraped spots or collected fractions, a flow detector) or imaged (a phosphor
imaging plate, film). The result of the experiment is the SHARE of the labelled counts that lies in one named product (or the ratio of two
products), read lane by lane. A label on one atom reports only the products that keep it, so every share is a share of labelled products.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable',
value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('distribution_radio_tlc'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               decided for the class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; no type of this class has an immobilized
               enzyme or an electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the
               extraction leaves all four None.
quantities     The two effect quantities of this method, each with the spread the passage gives for it (the unit of the quantity):
                 product_fraction and product_fraction_spread               fraction or percent   the share of the counts (or signal) of the lane that lies
                                                                            in ONE named product (the partner of the identity block)
                 product_fraction_ratio and product_fraction_ratio_spread   dimensionless         the ratio of the counts of the partner product (on top) to
                                                                            those of one other species
               and the quantities that decide how far a share can be trusted:
                 lane_recovery            fraction or percent   the counts of all the spots, bands or fractions of the lane over the counts applied
                 counts_background        cpm, dpm or PSL       the background counts (or signal) beside the lane, in the unit the passage gives
                 smallest_species_counts  cpm, dpm or PSL       the counts (or signal) of the smallest species the passage quantifies, in the same unit
                 replicate_count          count                 the number of independent replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval', 'range' or None: what the spreads are.
label          the isotope of the labelled substrate ('14C', '3H', '32P', '33P', '35S') or None. Recorded, not judged.
readout        how the label was read ('scintillation_counting', 'phosphor_imaging', 'radio_hplc_detector', 'film_densitometry') or None. Recorded, not judged.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, label, readout), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and
default it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's
answer).
"""

VERSION = 'a105_distribution_radio_tlc_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_radio_tlc'
QUANTITIES = ('product_fraction', 'product_fraction_spread', 'product_fraction_ratio', 'product_fraction_ratio_spread', 'lane_recovery',
              'counts_background', 'smallest_species_counts', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval', 'range')
LABELS = ('14C', '3H', '32P', '33P', '35S')
READOUTS = ('scintillation_counting', 'phosphor_imaging', 'radio_hplc_detector', 'film_densitometry')
# The plain choice fields: name -> vocabulary. They are recorded for the sheet's record; no criterion rests on a choice.
CHOICES = {'spread_kind': SPREAD_KINDS, 'label': LABELS, 'readout': READOUTS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'cold_standards_co_run': YES_NO, 'label_retained_by_all_products': YES_NO, 'fractions_share_one_denominator': YES_NO,
         'equal_label_per_molecule': YES_NO, 'detection_efficiency_matched': YES_NO, 'spots_resolved': YES_NO, 'background_subtracted': YES_NO,
         'within_linear_range_of_imager': YES_NO, 'no_enzyme_lane_run': YES_NO, 'zero_time_lane_run': YES_NO, 'inactive_enzyme_lane_run': YES_NO,
         'independent_replicates': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'claimed_product_detected': YES_NO}

SHARE_UNITS = ('fraction', 'percent')
COUNT_UNITS = ('cpm', 'dpm', 'PSL')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'product_fraction': SHARE_UNITS, 'product_fraction_spread': SHARE_UNITS, 'product_fraction_ratio': ('dimensionless',),
         'product_fraction_ratio_spread': ('dimensionless',), 'lane_recovery': SHARE_UNITS, 'counts_background': COUNT_UNITS,
         'smallest_species_counts': COUNT_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
