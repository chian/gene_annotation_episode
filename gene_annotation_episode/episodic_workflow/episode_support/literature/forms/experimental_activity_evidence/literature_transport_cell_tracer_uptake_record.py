"""The extracted record of ONE whole-cell tracer uptake (or efflux) experiment (type 'transport_cell_tracer_uptake', class transport_response).

The assay: living cells (bacteria, yeast, cultured cells or oocytes) that make the protein under test, and matched control cells (an empty vector, the
parent or a deletion strain), are given a labelled substrate (14C, 3H, 32P, 35S or an ion tracer such as 86Rb+ or 22Na+). After a stated time the uptake
(or the efflux of a preloaded label) is stopped, by rapid filtration and wash, by centrifugation through oil, or by dilution in ice-cold buffer; the label
kept by the cells is counted by scintillation and, with the specific activity of the label, turned into an amount (pmol, nmol) per mg of cell protein or
dry weight. A rate over the linear part of the time course, the Km of a series of substrate concentrations and the fold over the control cells are what
such an experiment reports. It is NOT this method when the substrate is unlabelled and is measured in the medium or in the cells by chemical analysis, when a
fluorescent analogue or dye is read in the cells, when the protein is purified and put into liposomes, when a vesicle flux is read by an electrode, when a
current is recorded, or when only the growth of the cells depends on the uptake.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_cell_tracer_uptake'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as the
               class note of 2026-11-22 sets them (owner to confirm): the cell culture (or transfection) that makes the protein is the analyte_preparation_ref;
               whole cells have no vesicle batch and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation
               reference, so the extraction leaves all four None.
quantities     The three effect quantities of the class that a whole-cell tracer experiment states, each with the spread the passage gives for it (in the unit of
               the quantity):
                 km and km_spread                                       nM, uM or mM        the Km (or K0.5) of the labelled substrate
                 normalized_rate and normalized_rate_spread             pmol/min/mg, nmol/min/mg or umol/min/mg
                                                                        the uptake rate per mg of cells (protein or dry weight; the basis is the choice rate_basis)
                 fold_over_control and fold_over_control_spread         fold                the uptake of the cells with the protein over that of the paper's own control cells
               and the conditions that decide how far a rate can be trusted:
                 time_window       s or min        the length of the uptake interval the rate was taken from (the time at which uptake was stopped)
                 specific_activity mCi/mmol or Ci/mmol   the specific activity of the label, which turns counts into an amount
                 replicate_count   count           the number of replicate experiments
               A turnover per transporter molecule is not asked: whole cells give no count of active transporters, and a passage almost never states one.
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the saturation curve, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
rate_basis     'protein' or 'dry_weight' or None: what the 'mg' of the rate is. Kept for the reviewer; no criterion rests on a choice (a choice holds no span in
               the merged record).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, rate_basis), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how
well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else'
(the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an
unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is
only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_cell_tracer_uptake_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_cell_tracer_uptake'
QUANTITIES = ('km', 'km_spread', 'normalized_rate', 'normalized_rate_spread', 'fold_over_control', 'fold_over_control_spread', 'time_window', 'specific_activity',
              'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
RATE_BASES = ('protein', 'dry_weight')
# The plain choice fields: name -> vocabulary. They are kept in the record for the reviewer; no criterion rests on one.
CHOICES = {'spread_kind': SPREAD_KINDS, 'rate_basis': RATE_BASES}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'empty_vector_control_done': YES_NO, 'zero_time_control_done': YES_NO, 'linear_interval_shown': YES_NO, 'competitor_control_done': YES_NO,
         'energy_control_done': YES_NO, 'label_identity_shown': YES_NO, 'expression_confirmed': YES_NO, 'viability_checked': YES_NO, 'native_substrate': YES_NO,
         'independent_replicates': YES_NO, 'uptake_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
RATE_UNITS = ('pmol/min/mg', 'nmol/min/mg', 'umol/min/mg')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'km': CONCENTRATION_UNITS, 'km_spread': CONCENTRATION_UNITS, 'normalized_rate': RATE_UNITS, 'normalized_rate_spread': RATE_UNITS,
         'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',), 'time_window': ('s', 'min'), 'specific_activity': ('mCi/mmol', 'Ci/mmol'),
         'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
