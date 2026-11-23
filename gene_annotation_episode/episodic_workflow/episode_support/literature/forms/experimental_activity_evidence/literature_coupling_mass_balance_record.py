"""The extracted record of ONE mass-balance (closure) experiment (type 'coupling_mass_balance', class reaction_coupling).

DRAFT of 2026-11-22 for the owner to correct (built by the SOP, steps 1 to 5; copied in shape from the spectro_direct type, the class core is the reaction_coupling
class of A105_REACTION_COUPLING_INVENTORY.md). The assay: one enzyme, one substrate, a reaction that is sampled (at zero time and at one or more later times, in the
same reaction mixture), and in every sample the substrate and each expected product are separated or resolved and quantified (HPLC, GC, LC-MS, GC-MS or NMR) against
standards, ideally with an internal standard. The substrate that disappeared is set against the sum of the identified products: the closure (also called recovery,
carbon balance, nitrogen balance, molar balance or mass balance) is the share of the consumed substrate that the identified products account for; what is not
accounted for is the residual. A closure near 1 says the reaction goes where the paper claims and nowhere else; a low closure says part of the substrate went somewhere
unmeasured (another product, a volatile, an insoluble, a covalent adduct); a closure well above 1 says something is wrong with the quantification.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('coupling_mass_balance'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). Class keys as decided for
               reaction_coupling (owner to confirm): the enzyme preparation is the analyte_preparation_ref; nothing is immobilized and there is no surface, so
               immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     closure and closure_spread                 percent or fraction     the closure the passage states (identified products over substrate consumed, on the
                                                                                  basis the passage states) and its uncertainty, in the unit of the closure
               substrate_consumed                         nM, uM, mM, pmol, nmol, umol   the net amount of the substrate that disappeared (net of the no-enzyme sample)
               products_total                             same units              the sum of the identified products, only when the passage gives that sum
               balance_residual                           same units              the amount not accounted for, when the passage gives it as an amount
               zero_time_closure                          percent or fraction     the recovery of the added substrate (or of the total) in a sample with no reaction
                                                                                  (time zero or no enzyme): the method's own closure
               detection_limit                            same units              the lowest amount of a product the method detects (the least sensitive product)
               replicate_count                            count                   the number of replicate experiments
choices        spread_kind     'standard_error', 'standard_deviation', 'confidence_interval' or None: what closure_spread is.
               balance_basis   'molar', 'carbon', 'nitrogen' or 'mass' or None: what the closure counts.
               analysis_method 'hplc', 'gc', 'lc_ms', 'gc_ms', 'nmr' or 'other' or None: how the species were quantified.
               Choices are kept for the reviewer; no criterion rests on a choice (a choice holds no span in the merged record).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (spread_kind, balance_basis, analysis_method), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's
fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_mass_balance_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_mass_balance'
QUANTITIES = ('closure', 'closure_spread', 'substrate_consumed', 'products_total', 'balance_residual', 'zero_time_closure', 'detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
BALANCE_BASES = ('molar', 'carbon', 'nitrogen', 'mass')
ANALYSIS_METHODS = ('hplc', 'gc', 'lc_ms', 'gc_ms', 'nmr', 'other')
CHOICES = {'spread_kind': SPREAD_KINDS, 'balance_basis': BALANCE_BASES, 'analysis_method': ANALYSIS_METHODS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'product_identified': YES_NO, 'each_species_calibrated': YES_NO, 'internal_standard': YES_NO, 'zero_time_sample': YES_NO, 'no_enzyme_control': YES_NO,
         'inactive_enzyme_control': YES_NO, 'all_products_quantified': YES_NO, 'volatile_loss_excluded': YES_NO, 'reaction_equation_stated': YES_NO,
         'same_mixture': YES_NO, 'same_window': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO,
         'product_formation_detected': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
AMOUNT_UNITS = ('pmol', 'nmol', 'umol')
BALANCE_UNITS = (*CONCENTRATION_UNITS, *AMOUNT_UNITS)
SHARE_UNITS = ('percent', 'fraction')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'closure': SHARE_UNITS, 'closure_spread': SHARE_UNITS, 'substrate_consumed': BALANCE_UNITS, 'products_total': BALANCE_UNITS, 'balance_residual': BALANCE_UNITS,
         'zero_time_closure': SHARE_UNITS, 'detection_limit': BALANCE_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
