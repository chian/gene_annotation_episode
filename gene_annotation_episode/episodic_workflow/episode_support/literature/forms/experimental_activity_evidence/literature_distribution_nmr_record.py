"""The extracted record of ONE quantitative NMR measurement of a product mixture (type 'distribution_nmr', class product_distribution).

First DRAFT (2026-11-22, owner to confirm), built by the A105 SOP (steps 1 to 3 and 5) on the structure of the first type built outside the binding
class, spectro_direct. The measurement: an enzyme reaction (or a mixture left to equilibrium) is read by NMR of one nucleus (1H, 13C, 31P, 19F), without
separating the species; each species has its own signal, the integrals of the signals are the amounts of the species (each divided by the number of
nuclei it contributes), and the shares of the species, or a ratio of two of them, are stated. No separation step and no detector response curve are
involved: the quantity of a species is its integral, which is the same for every species only when every integrated nucleus has relaxed fully between
scans, so the delay between scans (against the slowest T1) is what the sheet's criterion response_factors rests on here.

This is what a leaf extraction holds for one such measurement, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable',
value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('distribution_nmr'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               decided for the product_distribution class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; no type of this
               class has an immobilized enzyme, a surface or an electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a
               preparation reference, so the extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity). ONE record states the
               share, or the ratio, of ONE species: the species the identity block names as the partner (the product whose share is stated; the
               numerator of a ratio). The shares of the other species are other records of the same experiment.
                 product_fraction (and _spread)         fraction or percent   the share of the partner species among the species the reaction gave
                 product_fraction_ratio (and _spread)   dimensionless         the ratio of the partner species to one other species of the reaction
                 equilibrium_fraction (and _spread)     fraction or percent   the share of the partner species in the mixture at equilibrium
                 equilibrium_ratio (and _spread)        dimensionless         the ratio of the partner species to the other side at equilibrium
               and what decides how far the shares can be trusted:
                 total_recovery        fraction or percent   the sum of the quantified species over the amount started with (closure), when the passage states it
                 relaxation_delay      s or ms               the delay between scans (the relaxation delay or the repetition time)
                 longest_t1            s or ms               the longest spin-lattice relaxation time T1 of the integrated nuclei, when the passage states it
                 signal_to_noise_minor dimensionless         the signal-to-noise ratio of the smallest integrated signal, when the passage states it
                 replicate_count       count                 the number of independent experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval', 'range' or None: what the spreads are.
nucleus        '1H', '13C', '31P', '19F', '15N' or None: the nucleus whose signals were integrated (recorded, no criterion rests on it).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, nucleus), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default
it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_distribution_nmr_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_nmr'
QUANTITIES = ('product_fraction', 'product_fraction_spread', 'product_fraction_ratio', 'product_fraction_ratio_spread',
              'equilibrium_fraction', 'equilibrium_fraction_spread', 'equilibrium_ratio', 'equilibrium_ratio_spread',
              'total_recovery', 'relaxation_delay', 'longest_t1', 'signal_to_noise_minor', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval', 'range')
NUCLEI = ('1H', '13C', '31P', '19F', '15N')
# The plain choice fields of the record: name -> the vocabulary of its answers. A choice carries no span after the merge, so no criterion rests on one.
CHOICES = {'spread_kind': SPREAD_KINDS, 'nucleus': NUCLEI}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'integrals_from_resolved_signals': YES_NO,
         'species_assigned_with_standards': YES_NO, 'relaxation_delay_adequate': YES_NO, 'fractions_share_one_denominator': YES_NO,
         'all_products_identified': YES_NO, 'distribution_stable_over_time': YES_NO, 'approached_from_both_sides': YES_NO,
         'independent_replicates': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'claimed_product_detected': YES_NO}

FRACTION_UNITS = ('fraction', 'percent')
RATIO_UNITS = ('dimensionless',)
TIME_UNITS = ('s', 'ms')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'product_fraction': FRACTION_UNITS, 'product_fraction_spread': FRACTION_UNITS, 'product_fraction_ratio': RATIO_UNITS, 'product_fraction_ratio_spread': RATIO_UNITS,
         'equilibrium_fraction': FRACTION_UNITS, 'equilibrium_fraction_spread': FRACTION_UNITS, 'equilibrium_ratio': RATIO_UNITS, 'equilibrium_ratio_spread': RATIO_UNITS,
         'total_recovery': FRACTION_UNITS, 'relaxation_delay': TIME_UNITS, 'longest_t1': TIME_UNITS, 'signal_to_noise_minor': RATIO_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
