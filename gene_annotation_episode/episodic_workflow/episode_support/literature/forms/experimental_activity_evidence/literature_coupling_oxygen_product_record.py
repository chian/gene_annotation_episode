"""The extracted record of ONE oxygen-uptake-with-product coupling experiment (type 'coupling_oxygen_product', class reaction_coupling).

DRAFT 2026-11-22 for the owner to correct (the first draft of the type; nothing was run). It copies the shape of literature_spectro_direct_record.py and
uses the reaction_coupling class core of A105_REACTION_COUPLING_INVENTORY.md. The experiment: one enzyme reaction in one vessel; the dissolved oxygen is read
with an electrode or an optode (Clark electrode, Oroboros chamber, fluorescence optode) and the claimed product is identified and counted by another
measurement (chromatography, mass spectrometry or NMR) over the same interval; the result is the product made per oxygen consumed (one product per O2 for
the reaction of CsiD/LhgO), with the oxygen that went to hydrogen peroxide accounted for. Oxygen uptake alone can be uncoupled chemistry, so the product
and the link between the two sides are what the record must show.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('coupling_oxygen_product'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as in the
               inventory (section 6, owner to confirm): the enzyme preparation is the analyte_preparation_ref; nothing is immobilized and the electrode only
               delivers a reading, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     The link, as the passage states it (each with the spread the passage gives for it, in its own unit):
                 productive_fraction (+ _spread)   fraction or percent   the share of the consumed oxygen that ends in the claimed product, as stated (the
                                                                          reaction's own coefficient already applied)
                 stoichiometric_ratio (+ _spread)  mol/mol or fraction   mol of product per mol of O2 consumed, as stated
                 oxygen_per_product                mol/mol               mol of O2 consumed per mol of product, when the passage states the ratio this way round
                 stoichiometric_coefficient        mol/mol               the paper's own reaction account: mol of O2 consumed per mol of product
               the two sides:
                 oxygen_consumed, product_formed   nM, uM, mM, pmol, nmol or umol   the net amounts over the interval
                 oxygen_rate, product_rate         uM/min, uM/s, nM/min, nM/s, nmol/min, nmol/s, umol/min, pmol/min, umol/min/mg, nmol/min/mg, pmol/min/mg or U/mg
                 oxygen_window, product_window     s, min or h             the length of the interval each side was measured over
               and what decides how far the oxygen side can be trusted:
                 air_saturated_oxygen              uM or mM                the oxygen concentration of air-saturated buffer used to calibrate the electrode
                 drift_percent                     percent                 the drift of the oxygen signal without reaction, as a percent of the oxygen uptake rate
                 no_substrate_oxygen_percent       percent                 the oxygen uptake without the substrate, as a percent of the uptake with it
                 peroxide_percent_of_oxygen        percent                 the hydrogen peroxide formed as a percent of the oxygen consumed
                 replicate_count                   count                   the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the two spreads are.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

The record has no other top-level field: the merge of the leaf records of one experiment (literature_grader_record) keeps only quantities, plain choices named
in choice_support, facts, spans and preparations, so a criterion rests on a quantity or a fact, never on the choice.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how
well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the
quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice
carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by
tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_oxygen_product_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_oxygen_product'
QUANTITIES = ('productive_fraction', 'productive_fraction_spread', 'stoichiometric_ratio', 'stoichiometric_ratio_spread', 'oxygen_per_product', 'stoichiometric_coefficient',
              'oxygen_consumed', 'product_formed', 'oxygen_rate', 'product_rate', 'oxygen_window', 'product_window',
              'air_saturated_oxygen', 'drift_percent', 'no_substrate_oxygen_percent', 'peroxide_percent_of_oxygen', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'electrode_calibrated': YES_NO, 'drift_subtracted': YES_NO, 'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_substrate_control': YES_NO,
         'peroxide_accounted': YES_NO, 'product_identified': YES_NO, 'product_calibrated': YES_NO, 'same_vessel': YES_NO, 'same_window': YES_NO,
         'independent_replicates': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'coupling_detected_above_control': YES_NO}

AMOUNT_UNITS = ('nM', 'uM', 'mM', 'pmol', 'nmol', 'umol')
RATE_UNITS = ('uM/min', 'uM/s', 'nM/min', 'nM/s', 'nmol/min', 'nmol/s', 'umol/min', 'pmol/min', 'umol/min/mg', 'nmol/min/mg', 'pmol/min/mg', 'U/mg')
FRACTION_UNITS = ('fraction', 'percent')
RATIO_UNITS = ('mol/mol', 'fraction')
WINDOW_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'productive_fraction': FRACTION_UNITS, 'productive_fraction_spread': FRACTION_UNITS, 'stoichiometric_ratio': RATIO_UNITS, 'stoichiometric_ratio_spread': RATIO_UNITS,
         'oxygen_per_product': ('mol/mol',), 'stoichiometric_coefficient': ('mol/mol',), 'oxygen_consumed': AMOUNT_UNITS, 'product_formed': AMOUNT_UNITS,
         'oxygen_rate': RATE_UNITS, 'product_rate': RATE_UNITS, 'oxygen_window': WINDOW_UNITS, 'product_window': WINDOW_UNITS,
         'air_saturated_oxygen': ('uM', 'mM'), 'drift_percent': ('percent',), 'no_substrate_oxygen_percent': ('percent',), 'peroxide_percent_of_oxygen': ('percent',),
         'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
