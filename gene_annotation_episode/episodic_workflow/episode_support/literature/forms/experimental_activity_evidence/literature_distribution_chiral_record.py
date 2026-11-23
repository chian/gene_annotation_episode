"""The extracted record of ONE chiral product-distribution experiment (type 'distribution_chiral', class product_distribution).

The first type drafted for the product_distribution class (DRAFT 2026-11-22, owner to confirm); it copies the shape of literature_spectro_direct_record.py. The
experiment: an enzyme makes a product that has stereo-isomers (two enantiomers, or diastereomers, cis and trans isomers, syn and anti isomers), and the isomers are
separated and counted by a method that tells them apart: chiral-phase HPLC, chiral GC, supercritical-fluid chromatography on a chiral column, capillary electrophoresis with a
chiral selector, or an ordinary column when the isomers are diastereomers. The result is the enantiomeric excess (ee), the enantiomer ratio (er) or the diastereomer ratio (dr)
of the product. The racemic (or diastereomeric) standard of the product, run on the same column, is what shows that the column separates both isomers and that equal amounts
give equal peak areas.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason; it
is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('distribution_chiral'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as decided
               2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized enzyme and no electrode, so
               immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     The three ways the same stereochemical result is written, each with the spread the passage gives for it:
                 enantiomeric_excess and enantiomeric_excess_spread     percent or fraction   the excess of the MAJOR enantiomer (ee), a positive number
                 enantiomer_ratio and enantiomer_ratio_spread           dimensionless         the major enantiomer over the minor one (er), at least 1
                 diastereomer_ratio and diastereomer_ratio_spread       dimensionless         the major diastereomer over the minor one (dr), at least 1
               ee, er and dr are one fact in three spellings, never three results: the converter turns one of them into the share of the major isomer, or into a ratio.
               and the conditions that decide how far the result can be trusted:
                 peak_resolution               dimensionless          the resolution Rs between the two isomer peaks
                 minor_isomer_detection_limit  percent or fraction    the smallest share of the minor isomer, of the total, that the method detects or quantifies
                 replicate_count               count                  the number of independent replicate experiments
choices        spread_kind     'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
               configuration   the configuration or relative configuration of the major isomer as the passage names it ('R', 'S', 'E', 'Z', 'cis', 'trans', 'syn', 'anti') or None.
               technique       'chiral_hplc', 'chiral_gc', 'chiral_sfc', 'chiral_ce', 'diastereomers_on_achiral_column' or None.
               The configuration and the technique are kept for the reviewer; no criterion rests on a choice (a choice holds no span in the merged record).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, configuration, technique), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well its
quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the topic
but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does
not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go through the
extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_distribution_chiral_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_chiral'
QUANTITIES = ('enantiomeric_excess', 'enantiomeric_excess_spread', 'enantiomer_ratio', 'enantiomer_ratio_spread', 'diastereomer_ratio', 'diastereomer_ratio_spread',
              'peak_resolution', 'minor_isomer_detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
CONFIGURATIONS = ('R', 'S', 'E', 'Z', 'cis', 'trans', 'syn', 'anti')
TECHNIQUES = ('chiral_hplc', 'chiral_gc', 'chiral_sfc', 'chiral_ce', 'diastereomers_on_achiral_column')
# The plain choice fields and their vocabularies (each is kept in the record with its support in choice_support).
CHOICES = {'spread_kind': SPREAD_KINDS, 'configuration': CONFIGURATIONS, 'technique': TECHNIQUES}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'product_detected': YES_NO, 'racemic_standard_run': YES_NO, 'configuration_assigned_by_standard': YES_NO, 'isomer_peaks_baseline_resolved': YES_NO,
         'response_factors_calibrated': YES_NO, 'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'product_configurationally_stable': YES_NO,
         'independent_replicates': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO}

SHARE_UNITS = ('percent', 'fraction')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'enantiomeric_excess': SHARE_UNITS, 'enantiomeric_excess_spread': SHARE_UNITS, 'enantiomer_ratio': ('dimensionless',), 'enantiomer_ratio_spread': ('dimensionless',),
         'diastereomer_ratio': ('dimensionless',), 'diastereomer_ratio_spread': ('dimensionless',), 'peak_resolution': ('dimensionless',),
         'minor_isomer_detection_limit': SHARE_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
