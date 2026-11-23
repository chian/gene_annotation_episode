"""The extracted record of ONE by-product (uncoupling) assay of a coupled reaction (type 'coupling_uncoupling_byproduct', class reaction_coupling).

DRAFT, written 2026-11-22 by copying the shape of literature_spectro_direct_record.py to the reaction_coupling class core. Every choice below is for
the owner to confirm. The assay: one enzyme turns over with a cofactor (NAD(P)H, most often) and a substrate; part of the cofactor goes to the claimed
product and part is lost as a by-product of oxygen reduction: hydrogen peroxide (read with Amplex Red and peroxidase, with ferrous oxidation by xylenol
orange, or by oxygen returned by catalase) or superoxide (read as superoxide-dismutase-inhibitable reduction of cytochrome c). The paper states how much
of the consumed cofactor ended as the by-product (the uncoupled fraction, or the by-product formed per cofactor consumed); the productive share is
the rest, by difference, when the by-product is the only loss. The method says how much of the cofactor use is NOT product; it does not by itself
identify the product.

This is what a leaf extraction holds for one such assay, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None
and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('coupling_uncoupling_byproduct'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               drafted 2026-11-22 (owner to confirm): the enzyme preparation is the analyte_preparation_ref (the two sides of one coupling measurement come
               from one preparation, so they are one dependence unit); nothing is immobilized and nothing is on a surface, so immobilized_preparation_ref and
               surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     productive_fraction and its spread          fraction or percent    the share of the consumed cofactor that ended in the claimed product, as the passage states it
               uncoupled_fraction and its spread           fraction or percent    the share of the consumed cofactor whose electrons ended as the by-product, as the passage states it
               byproduct_per_cofactor and its spread       mol_per_mol            moles of by-product formed per mole of cofactor consumed, as the passage states it
               byproduct_coefficient                       mol_per_mol            the moles of by-product one cofactor gives when wholly uncoupled, when the passage says it
                                                                                  (1 for hydrogen peroxide from NAD(P)H, 2 for superoxide)
               blank_percent_of_signal                     percent                the by-product signal of the no-enzyme blank as a share of the signal of the complete reaction
               standard_recovery                           percent or fraction    the recovery of a known amount of by-product added to the complete reaction mixture
               replicate_count                             count                  the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
byproduct_species   'hydrogen_peroxide' or 'superoxide' or None: which by-product the passage measured (recorded only; no criterion rests on it).
detection_reagent   'amplex_red_peroxidase', 'xylenol_orange', 'cytochrome_c', 'catalase_oxygen_return', 'other_reagent' or None: how the by-product was read (recorded only).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, byproduct_species, detection_reagent), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default
it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_uncoupling_byproduct_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_uncoupling_byproduct'
QUANTITIES = ('productive_fraction', 'productive_fraction_spread', 'uncoupled_fraction', 'uncoupled_fraction_spread', 'byproduct_per_cofactor',
              'byproduct_per_cofactor_spread', 'byproduct_coefficient', 'blank_percent_of_signal', 'standard_recovery', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
BYPRODUCT_SPECIES = ('hydrogen_peroxide', 'superoxide')
DETECTION_REAGENTS = ('amplex_red_peroxidase', 'xylenol_orange', 'cytochrome_c', 'catalase_oxygen_return', 'other_reagent')
# The plain choice fields (recorded only; no criterion rests on a choice, because a choice carries no span after the merge): name -> its vocabulary.
CHOICES = {'spread_kind': SPREAD_KINDS, 'byproduct_species': BYPRODUCT_SPECIES, 'detection_reagent': DETECTION_REAGENTS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_substrate_control': YES_NO, 'catalase_control': YES_NO, 'sod_control': YES_NO,
         'reductant_interference_excluded': YES_NO, 'byproduct_not_consumed': YES_NO, 'standard_series': YES_NO, 'uncoupling_routes_accounted': YES_NO,
         'product_measured_too': YES_NO, 'same_mixture': YES_NO, 'same_window': YES_NO, 'same_preparation': YES_NO, 'native_substrate': YES_NO,
         'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'coupled_product_detected_above_control': YES_NO}

SHARE_UNITS = ('fraction', 'percent')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'productive_fraction': SHARE_UNITS, 'productive_fraction_spread': SHARE_UNITS, 'uncoupled_fraction': SHARE_UNITS, 'uncoupled_fraction_spread': SHARE_UNITS,
         'byproduct_per_cofactor': ('mol_per_mol',), 'byproduct_per_cofactor_spread': ('mol_per_mol',), 'byproduct_coefficient': ('mol_per_mol',),
         'blank_percent_of_signal': ('percent',), 'standard_recovery': ('percent', 'fraction'), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
