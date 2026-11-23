"""The extracted record of ONE proteoliposome tracer transport experiment (type 'transport_proteoliposome_tracer', class transport_response).

DRAFT built 2026-11-22 on the shape of literature_spectro_direct_record.py, with the class core of transport_response (A105_TRANSPORT_RESPONSE_INVENTORY.md), owner to
correct. The experiment: ONE purified transporter (or channel) reconstituted into liposomes; a driving force is imposed on the vesicles (a pH difference, a membrane
potential made with an ionophore such as valinomycin and a potassium gradient, a sodium or other ion gradient, or ATP inside); a labelled substrate (a radioisotope such as
14C or 3H, rarely a stable isotope or a tag) is taken up into the vesicles or released from them; the vesicles are stopped on a filter, on an ion-exchange column or by
dilution and the retained label is counted. The same protocol is run on protein-free ("empty") liposomes and, as the driving-force control, without the gradient. The system
holds only protein, lipid and gradient, so the flux is the protein's own.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is
never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_proteoliposome_tracer'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref (the purified protein preparation), immobilized_preparation_ref (the reconstituted proteoliposome batch), surface_ref and
               dataset_ref: each a string or None (unknown). The class keys are used as decided 2026-11-22 (owner to confirm); surface_ref stays None (no electrode).
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     The effect quantities of the type, each with the spread the passage gives for it (in the unit of the quantity):
                 km (Km or K0.5 of the substrate) and km_spread                             nM, uM or mM
                 turnover (per transporter molecule) and turnover_spread                    s^-1 or min^-1
                 normalized_rate (rate per mg of protein) and normalized_rate_spread        pmol/min/mg, nmol/min/mg or umol/min/mg
                 fold_over_control (the rate of the proteoliposomes over that of the paper's own protein-free liposomes) and fold_over_control_spread     fold
               and the conditions that decide how far a rate can be trusted:
                 uptake_percent_of_equilibrium  percent    the share of the plateau (equilibrium or steady-state) uptake reached at the time the rate was taken
                 replicate_count                count      the number of replicate experiments
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the saturation curve, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
driving_force  the driving force imposed on the vesicles (a choice, recorded only, never judged), or None.
flux_direction 'uptake', 'efflux' or 'exchange' (a choice, recorded only, never judged), or None.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, driving_force, flux_direction), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well its
quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the topic
but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not
judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go through the
extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_proteoliposome_tracer_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_proteoliposome_tracer'
QUANTITIES = ('km', 'km_spread', 'turnover', 'turnover_spread', 'normalized_rate', 'normalized_rate_spread', 'fold_over_control', 'fold_over_control_spread',
              'uptake_percent_of_equilibrium', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
DRIVING_FORCES = ('proton_gradient', 'membrane_potential', 'sodium_gradient', 'other_ion_gradient', 'atp', 'substrate_gradient')
FLUX_DIRECTIONS = ('uptake', 'efflux', 'exchange')
# The plain choice fields (recorded only: no criterion rests on a choice, a choice carries no span after the merge): name -> its fixed vocabulary.
CHOICES = {'spread_kind': SPREAD_KINDS, 'driving_force': DRIVING_FORCES, 'flux_direction': FLUX_DIRECTIONS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'empty_liposome_control_done': YES_NO, 'inactive_protein_control_done': YES_NO, 'no_gradient_control_done': YES_NO, 'gradient_verified': YES_NO,
         'leak_checked': YES_NO, 'competitor_control_done': YES_NO, 'substrate_identity_shown': YES_NO, 'protein_quantified_after_reconstitution': YES_NO,
         'active_fraction_determined': YES_NO, 'linear_interval_shown': YES_NO, 'independent_replicates': YES_NO, 'native_substrate': YES_NO, 'purified_protein': YES_NO,
         'transport_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
TURNOVER_UNITS = ('s^-1', 'min^-1')
RATE_UNITS = ('pmol/min/mg', 'nmol/min/mg', 'umol/min/mg')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'km': CONCENTRATION_UNITS, 'km_spread': CONCENTRATION_UNITS, 'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS,
         'normalized_rate': RATE_UNITS, 'normalized_rate_spread': RATE_UNITS, 'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',),
         'uptake_percent_of_equilibrium': ('percent',), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
