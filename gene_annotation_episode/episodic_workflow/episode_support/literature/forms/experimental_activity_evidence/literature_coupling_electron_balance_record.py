"""The extracted record of ONE electron balance of a reaction (type 'coupling_electron_balance', class reaction_coupling).

A type of the reaction_coupling class (first DRAFT 2026-11-22 by the SOP, steps 1 and 5; the class core is in
docs/axis_restructure_20261117/A105_REACTION_COUPLING_INVENTORY.md, section 2). The experiment: electrons are delivered to (or taken from) one
reaction in a way that can be counted (a reductant titrated into the vessel, charge passed at an electrode, a reduced donor oxidised and followed
by its absorbance), and the electrons recovered in the product are counted against them (hydrogen by gas chromatography, a reduced compound by
chromatography or mass spectrometry, times the electrons the product needs). The result is the share of the delivered electrons that ends in the
claimed product (electron recovery, faradaic efficiency). The claim 'E catalyzes R' is carried by that share, and by the controls that show the
electrons did not go elsewhere (a mediator that bypasses the enzyme, oxygen, the electrode itself).

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('coupling_electron_balance'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided in the inventory (section 6, owner to confirm): the enzyme preparation is the analyte_preparation_ref; the electrode
               of an electrolysis is a way of delivering electrons, not a dependence unit, so immobilized_preparation_ref and surface_ref stay None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     productive_fraction and productive_fraction_spread   fraction or percent    the share of the delivered electrons found in the product
                                                                                            (electron recovery, faradaic efficiency), as stated
               electrons_delivered      umol, nmol, mmol, mol, C or mC   the electron equivalents delivered (a charge is exact: coulomb over the Faraday constant)
               product_formed           umol, nmol, pmol, mmol or mol    the amount of the claimed product formed over the same interval
               electrons_per_product    mol_per_mol                      the electrons one product molecule takes (2 for H2), as the paper states it
               background_electrons     umol, nmol, mmol, mol, C or mC   the electrons delivered in the control without the enzyme
               standard_recovery        fraction or percent              the recovery of a known standard of the product (a gas injection) through the measurement
               replicate_count          count                            the number of replicate experiments
choices        spread_kind     'standard_error', 'standard_deviation' or 'confidence_interval' (what the spread is), or None
               delivery_kind   'reductant_titration', 'electrolysis_charge' or 'donor_oxidation', or None (how the electrons were counted)
               product_kind    'hydrogen', 'reduced_compound' or 'oxidized_compound', or None (what the electrons were recovered in)
               The choices are for recording only; no criterion rests on one.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field, None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_electron_balance_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_electron_balance'
QUANTITIES = ('productive_fraction', 'productive_fraction_spread', 'electrons_delivered', 'product_formed', 'electrons_per_product', 'background_electrons',
              'standard_recovery', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
DELIVERY_KINDS = ('reductant_titration', 'electrolysis_charge', 'donor_oxidation')
PRODUCT_KINDS = ('hydrogen', 'reduced_compound', 'oxidized_compound')
# The plain choice fields (recorded with their support in choice_support; no criterion rests on one).
CHOICES = {'spread_kind': SPREAD_KINDS, 'delivery_kind': DELIVERY_KINDS, 'product_kind': PRODUCT_KINDS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'background_charge_subtracted': YES_NO, 'delivery_calibrated': YES_NO,
         'product_calibrated': YES_NO, 'headspace_accounted': YES_NO, 'anaerobic_control': YES_NO, 'mediator_bypass_excluded': YES_NO,
         'product_identified': YES_NO, 'same_window': YES_NO, 'same_reaction_mixture': YES_NO, 'native_electron_carrier': YES_NO,
         'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'product_detected_from_electrons': YES_NO}

ELECTRON_UNITS = ('umol', 'nmol', 'mmol', 'mol', 'C', 'mC')
AMOUNT_UNITS = ('umol', 'nmol', 'pmol', 'mmol', 'mol')
FRACTION_UNITS = ('fraction', 'percent')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'productive_fraction': FRACTION_UNITS, 'productive_fraction_spread': FRACTION_UNITS, 'electrons_delivered': ELECTRON_UNITS, 'product_formed': AMOUNT_UNITS,
         'electrons_per_product': ('mol_per_mol',), 'background_electrons': ELECTRON_UNITS, 'standard_recovery': FRACTION_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
