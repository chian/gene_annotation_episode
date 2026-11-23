"""The extracted record of ONE counterflow (exchange, trans-stimulation) experiment (type 'transport_counterflow', class transport_response).

The assay: vesicles (native membrane vesicles or proteoliposomes with the purified protein) or whole cells are first loaded with an UNLABELLED substrate (the
preload), then put into a medium with a LABELLED substrate (14C, 3H) at a much lower concentration, and the label kept by the vesicles or cells is followed over
time. A carrier that exchanges the substrate across the membrane takes the label in against the unlabelled substrate that leaves, so the preloaded vesicles take
up the label faster than the same vesicles without the preload (trans-stimulation, a fold over the non-preloaded baseline) and, for a while, hold more label
than the equilibrium level that is reached later (the overshoot, the peak over the equilibrium level). Equilibrium exchange (equal concentrations inside and
outside) and a preload with a second molecule (heterologous exchange: the transporter takes in the label against another molecule it recognizes) are the same
method. A protein-free control and a non-preloaded baseline decide how much it means. It is NOT this method when the vesicles or cells have no preload and the
uptake is measured alone (whole-cell tracer uptake, proteoliposome tracer uptake), when the substrate is not labelled and is measured in the medium, when a
fluorescent probe or an electrode follows the flux, or when a current is recorded.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_counterflow'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as the class
               note of 2026-11-22 sets them (owner to confirm): the preparation that carries the protein (the cell culture, or the purified protein stock) is the
               analyte_preparation_ref; the vesicle or proteoliposome batch is the immobilized_preparation_ref; there is no electrode, so surface_ref stays None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     The effect quantities of the class that a counterflow states, each with the spread the passage gives for it (in the unit of the quantity):
                 fold_over_control and fold_over_control_spread   fold    the uptake of the preloaded vesicles or cells over that of the same preparation without
                                                                           the preload (the non-preloaded baseline is the experiment's own control)
                 overshoot_ratio and overshoot_ratio_spread       fold    the label inside at its peak over the label inside at the equilibrium level reached later
                 normalized_rate and normalized_rate_spread       pmol/min/mg, nmol/min/mg or umol/min/mg   the exchange rate of the preloaded preparation per mg
                 km and km_spread                                 nM, uM or mM    the Km (K0.5) of the external substrate for the exchange
               and the conditions that decide how far the result can be trusted:
                 preload_concentration  uM, mM or M     the concentration of the unlabelled substrate the vesicles or cells were loaded with
                 label_concentration    nM, uM or mM    the concentration of the substrate in the medium outside at the start of the uptake
                 replicate_count        count           the number of replicate experiments
               A turnover per transporter molecule is not asked: a counterflow gives no count of active transporters, and a passage almost never states one.
concentration_series
               operand whose 'value' is a list of external substrate concentrations (nM, uM or mM) of the series that gives the Km, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are. A plain choice: no criterion rests on it (a choice holds no
               span in the merged record); it only tells the converter how to turn a spread into a variance.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how
well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else'
(the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an
unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is
only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_counterflow_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_counterflow'
QUANTITIES = ('fold_over_control', 'fold_over_control_spread', 'overshoot_ratio', 'overshoot_ratio_spread', 'normalized_rate', 'normalized_rate_spread', 'km', 'km_spread',
              'preload_concentration', 'label_concentration', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'non_preloaded_baseline_done': YES_NO, 'protein_free_control_done': YES_NO, 'non_substrate_preload_control_done': YES_NO, 'label_identity_shown': YES_NO,
         'preload_verified': YES_NO, 'preload_retained': YES_NO, 'equilibrium_reached': YES_NO, 'linear_interval_shown': YES_NO, 'native_substrate': YES_NO,
         'independent_replicates': YES_NO, 'transport_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
PRELOAD_UNITS = ('uM', 'mM', 'M')
RATE_UNITS = ('pmol/min/mg', 'nmol/min/mg', 'umol/min/mg')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',), 'overshoot_ratio': ('fold',), 'overshoot_ratio_spread': ('fold',),
         'normalized_rate': RATE_UNITS, 'normalized_rate_spread': RATE_UNITS, 'km': CONCENTRATION_UNITS, 'km_spread': CONCENTRATION_UNITS,
         'preload_concentration': PRELOAD_UNITS, 'label_concentration': CONCENTRATION_UNITS, 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
