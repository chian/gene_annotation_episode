"""The extracted record of ONE limiting-reagent endpoint experiment (type 'coupling_limiting_reagent', class reaction_coupling).

DRAFT 2026-11-22 (first version of the type, built from the reaction_coupling inventory section 3.7; owner to correct). The experiment: one enzyme
reaction is run to completion with ONE reagent limiting (a cofactor such as NADPH, a co-substrate, or the substrate itself), either in a single
limiting dose or by stepwise titration of the limiting reagent into an excess of everything else. At the end the product is measured and set against the
limiting reagent used up: the reaction's own stoichiometry shows as equivalents of the limiting reagent per product (QueF takes 2 NADPH per product)
or as the yield over the limiting reagent. It is the endpoint way of measuring a coupling; the paired-rate ways (cofactor loss against product rate)
and the closure ways (mass balance, electron balance, isotope label) are other types of the class.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted. The shape follows literature_spectro_direct_record.py and literature_colocalization_record.py (private copies).

What the method shows and what can go wrong is what the form keeps. The ratio of product to limiting reagent means the reaction's stoichiometry only when
the limiting reagent was really used up (the reaction went to completion: no more product with more enzyme or time, the limiting reagent measured as gone),
when everything else was in excess (otherwise nothing is limiting), when the limiting reagent was not regenerated (a regeneration system makes any amount of
product from a trace), when the amount of limiting reagent added was verified (NADPH by its absorbance), when the product was identified and measured against
a standard, when the limiting reagent was not also used up by something else (an oxidase side activity, spontaneous loss), and when both sides were taken from
the same reaction at the same end. A titration shows the break between the rise and the plateau, so it needs several points.

Record fields
-------------
version, experiment_type ('coupling_limiting_reagent'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as decided
               2026-11-22 (reaction_coupling inventory section 6, owner to confirm): the enzyme preparation is the analyte_preparation_ref; nothing is immobilized
               and there is no surface, so those two stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     productive_fraction and its spread                       fraction or percent   the share of the limiting reagent that ended in the claimed product with the paper's own reaction
                                                                                              coefficient applied, or the yield against the most the limiting reagent allows
               yield_over_limiting_reagent and its spread               fraction or percent   the product formed as a share of the limiting reagent added, no coefficient applied
               limiting_reagent_per_product and its spread              mol_per_mol           the equivalents of the limiting reagent used up per product, as measured
               stoichiometric_coefficient                               mol_per_mol           the equivalents of the limiting reagent per product the paper's own reaction account expects
               limiting_reagent_remaining                               percent               the share of the limiting reagent still there at the end
               excess_over_limiting                                     fold                  how many times the other reagent exceeds the limiting reagent
               titration_points                                         count                 the number of additions or points of a titration
               replicate_count                                          count                 the number of replicate experiments
choices        spread_kind 'standard_error', 'standard_deviation', 'confidence_interval' or None (what the spreads are), and limiting_reagent_kind 'cofactor',
               'co_substrate', 'substrate' or 'other' or None: both kept for the reviewer. No criterion rests on a choice (a choice holds no span in the merged record).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field, None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how
well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the
quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated
choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for
forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_limiting_reagent_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_limiting_reagent'
QUANTITIES = ('productive_fraction', 'productive_fraction_spread', 'yield_over_limiting_reagent', 'yield_over_limiting_reagent_spread', 'limiting_reagent_per_product',
              'limiting_reagent_per_product_spread', 'stoichiometric_coefficient', 'limiting_reagent_remaining', 'excess_over_limiting', 'titration_points', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
LIMITING_REAGENT_KINDS = ('cofactor', 'co_substrate', 'substrate', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'completion_shown': YES_NO, 'limiting_reagent_consumed_fully': YES_NO, 'other_reagents_in_excess': YES_NO, 'no_regeneration': YES_NO,
         'limiting_amount_verified': YES_NO, 'product_identified': YES_NO, 'product_calibrated': YES_NO, 'same_mixture': YES_NO, 'same_endpoint': YES_NO,
         'no_enzyme_control': YES_NO, 'no_substrate_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'independent_replicates': YES_NO, 'native_substrate': YES_NO,
         'purified_enzyme': YES_NO, 'coupled_product_detected': YES_NO}

FRACTION_UNITS = ('fraction', 'percent')
EQUIVALENT_UNITS = ('mol_per_mol',)
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'productive_fraction': FRACTION_UNITS, 'productive_fraction_spread': FRACTION_UNITS, 'yield_over_limiting_reagent': FRACTION_UNITS, 'yield_over_limiting_reagent_spread': FRACTION_UNITS,
         'limiting_reagent_per_product': EQUIVALENT_UNITS, 'limiting_reagent_per_product_spread': EQUIVALENT_UNITS, 'stoichiometric_coefficient': EQUIVALENT_UNITS,
         'limiting_reagent_remaining': ('percent',), 'excess_over_limiting': ('fold',), 'titration_points': ('count',), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
