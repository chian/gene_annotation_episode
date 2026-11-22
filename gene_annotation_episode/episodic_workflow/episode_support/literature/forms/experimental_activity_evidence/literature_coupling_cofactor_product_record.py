"""The extracted record of ONE cofactor-consumption / identified-product coupling experiment (type 'coupling_cofactor_product', class reaction_coupling).

A type of the reaction_coupling class (drafted 2026-11-22 by the SOP, steps 1 to 3 and 5; DRAFT for the owner to correct). The experiment: one enzyme in one
reaction mixture, in which two things are measured side by side, the CONSUMED side and the FORMED side. The consumed side is the cofactor NAD(P)H, read
by its absorbance loss at 340 nm (or by its amount by HPLC). The formed side is the claimed product, identified and counted by chromatography (HPLC, GC)
or mass spectrometry against an authentic standard. The link between them is the coupling: how much of the cofactor that was used ended up as the claimed
product. It is the product per cofactor times the reaction's own coefficient (the moles of cofactor the reaction takes per mole of product, for example 1
for a cytochrome P450 monooxygenase, 2 for a four-electron reduction such as QueF), usually written as a percent: coupling percent = coefficient x product /
cofactor. A cofactor that is used without making the product (NAD(P)H oxidised by the enzyme with no substrate, hydrogen peroxide or water made instead of
the product) is the uncoupled share. Past work: P450cam camphor hydroxylation against NADH oxidation, wild type and mutants; QueF, two NADPH per product.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value
None and a reason; it is never 0 and never omitted.

Only the experiment in which BOTH sides are tied to one reaction is this type. A passage that gives only the product, or only the cofactor consumption,
or gives each side without tying them to the same reaction, gives no record of this type (the facts same_mixture, same_window and same_preparation say
how well they are tied when both are given).

Record fields
-------------
version, experiment_type ('coupling_cofactor_product'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as decided
               2026-11-22 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; the two sides of one coupling measurement come from one
               preparation, so they are one dependence unit; nothing is immobilized and nothing is on a surface, so immobilized_preparation_ref and surface_ref stay None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     The stated coupling, three ways, each with the spread the passage gives for it:
                 productive_fraction (and _spread)    fraction or percent    the share of the consumed cofactor that ended in the claimed product, with the reaction's own
                                                                             coefficient applied, as the passage states it (the coupling percent, the coupling efficiency)
                 stoichiometric_ratio (and _spread)   mol_per_mol            moles of product per mole of cofactor consumed, as stated, no coefficient applied
                 cofactor_per_product                 mol_per_mol            moles of cofactor consumed per mole of product, as stated (the reverse way of stating the ratio)
               the reaction's own account:
                 stoichiometric_coefficient           mol_per_mol            moles of cofactor the reaction takes per mole of product (1 for a monooxygenase, 2 for QueF)
               the two sides, as amounts over one window or as rates:
                 cofactor_consumed, product_formed    nM, uM, mM, pmol, nmol or umol
                 cofactor_rate, product_rate          nM/min, uM/min, mM/min, pmol/min, nmol/min, umol/min, pmol/min/mg, nmol/min/mg or umol/min/mg
               what decides how far the cofactor side can be trusted:
                 no_substrate_cofactor_rate           the same rate units       the rate of cofactor consumption of the enzyme with NO substrate (the uncoupled turnover)
                 extinction_coefficient               M^-1 cm^-1 or mM^-1 cm^-1   the coefficient that turns the absorbance loss into the amount of cofactor
                 wavelength                           nm                          the wavelength the absorbance was read at
                 absorbance_max                       AU                          the highest absorbance reached in the measurement
               and the product side:
                 calibration_recovery                 percent                     the recovery of a known amount of the product through the whole product measurement
               and
                 replicate_count                      count                       the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

The record holds no criterion that rests on a choice: the only choice, the spread kind, is for the converter's variance and is recorded for the reviewer; everything a
criterion reads is a quantity or a fact with its own quote.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well its
quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the
topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader
does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go through
the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_cofactor_product_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_cofactor_product'
QUANTITIES = ('productive_fraction', 'productive_fraction_spread', 'stoichiometric_ratio', 'stoichiometric_ratio_spread', 'cofactor_per_product', 'stoichiometric_coefficient',
              'cofactor_consumed', 'product_formed', 'cofactor_rate', 'product_rate', 'no_substrate_cofactor_rate', 'extinction_coefficient', 'wavelength', 'absorbance_max',
              'calibration_recovery', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'product_identified': YES_NO, 'product_calibrated': YES_NO, 'same_mixture': YES_NO, 'same_window': YES_NO, 'same_preparation': YES_NO,
         'no_substrate_control': YES_NO, 'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'background_subtracted': YES_NO, 'byproduct_accounted': YES_NO,
         'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'coupled_product_detected': YES_NO}

FRACTION_UNITS = ('fraction', 'percent')
MOL_PER_MOL = ('mol_per_mol',)
AMOUNT_UNITS = ('nM', 'uM', 'mM', 'pmol', 'nmol', 'umol')
RATE_UNITS = ('nM/min', 'uM/min', 'mM/min', 'pmol/min', 'nmol/min', 'umol/min', 'pmol/min/mg', 'nmol/min/mg', 'umol/min/mg')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'productive_fraction': FRACTION_UNITS, 'productive_fraction_spread': FRACTION_UNITS, 'stoichiometric_ratio': MOL_PER_MOL, 'stoichiometric_ratio_spread': MOL_PER_MOL,
         'cofactor_per_product': MOL_PER_MOL, 'stoichiometric_coefficient': MOL_PER_MOL, 'cofactor_consumed': AMOUNT_UNITS, 'product_formed': AMOUNT_UNITS,
         'cofactor_rate': RATE_UNITS, 'product_rate': RATE_UNITS, 'no_substrate_cofactor_rate': RATE_UNITS, 'extinction_coefficient': ('M^-1 cm^-1', 'mM^-1 cm^-1'),
         'wavelength': ('nm',), 'absorbance_max': ('AU',), 'calibration_recovery': ('percent',), 'replicate_count': ('count',)}
# The family of each amount or rate unit and its exact factor to the family's base unit (uM, nmol, uM/min, nmol/min, nmol/min/mg). FIXED_BY_DEFINITION: a milli is a
# thousand micro, a micro is a thousand nano, a nano is a thousand pico. Two values are compared (their ratio taken) only inside one family: a concentration and an amount
# need the reaction volume, and a rate per mg and a rate per reaction need the protein amount, which the passage may not give.
UNIT_SCALE = {'nM': ('concentration', 1.0e-3), 'uM': ('concentration', 1.0), 'mM': ('concentration', 1.0e3),
              'pmol': ('amount', 1.0e-3), 'nmol': ('amount', 1.0), 'umol': ('amount', 1.0e3),
              'nM/min': ('concentration_rate', 1.0e-3), 'uM/min': ('concentration_rate', 1.0), 'mM/min': ('concentration_rate', 1.0e3),
              'pmol/min': ('amount_rate', 1.0e-3), 'nmol/min': ('amount_rate', 1.0), 'umol/min': ('amount_rate', 1.0e3),
              'pmol/min/mg': ('specific_rate', 1.0e-3), 'nmol/min/mg': ('specific_rate', 1.0), 'umol/min/mg': ('specific_rate', 1.0e3)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
