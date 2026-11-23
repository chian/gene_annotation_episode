"""The extracted record of ONE medium-analysis transport experiment (type 'transport_medium_analysis', class transport_response).

DRAFT 2026-11-22 (first draft of the type, owner to correct), built by the A105 experiment SOP from the shape of 'spectro_direct' with the
transport_response class core (docs/axis_restructure_20261117/A105_TRANSPORT_RESPONSE_INVENTORY.md, section 3.2). The experiment: cells (or
vesicles) of one strain take up or release an UNLABELLED substrate; no tracer and no probe is used. The substrate left in, or appearing in, the
medium (or the content of cells separated from the medium, for example through silicone oil) is measured at stated times by HPLC (often after
derivatization), LC-MS, an enzymatic analyzer or ion analysis (ion chromatography, ICP-MS, an ion-selective electrode on samples), and the change
over the time interval is turned into a rate. The result is an INTERVAL or appearance measure: it is the balance of export, re-uptake, lysis and
metabolism over the interval, and a disappearance over ten minutes is not an initial rate. The record keeps what decides how far it can be trusted.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_medium_analysis'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys
               are used as decided in the inventory, section 6 (owner to confirm): the cell culture that carries the transporter is the
               analyte_preparation_ref; this type has no reconstituted vesicle batch and no electrode, so immobilized_preparation_ref and
               surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     The two effect quantities of the type, each with the spread the passage gives for it:
                 normalized_rate and normalized_rate_spread   pmol/min/mg, nmol/min/mg, umol/min/mg or umol/min/g (a rate per mass of cells:
                                                              of cell protein or of dry weight, told apart by the choice rate_basis)
                 fold_over_control and fold_over_control_spread   fold (the rate of the cells that carry the transporter over the rate of
                                                              the paper's own control cells: empty vector, parent or deletion strain)
               and the conditions that decide how far an interval rate can be trusted:
                 substrate_moved_percent  percent   the share of the starting amount of the substrate (in the medium for an uptake, in the
                                                    cells for an export) that was taken up or released over the interval the rate was taken from
                 interval                 s, min, h the length of the incubation from the start of the transport to the last sample used
                 separation_delay         s, min, h the time from taking a sample to the cells being separated from the medium (or the
                                                    reaction being stopped)
                 replicate_count          count     the number of replicate experiments
sampling_times operand whose 'value' is a list of the times after the start (s, min or h; all above 0) at which samples were taken, or None.
               The time zero is not in the list: the zero-time sample is the fact zero_time_sample_taken.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
rate_basis     'cell_protein', 'dry_weight' or None: what the rate per mass is per (recorded only; no criterion rests on a choice).
analytical_method  'hplc', 'lc_ms', 'enzymatic_analyzer', 'ion_analysis' or None: how the substrate was measured (recorded only).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, rate_basis, analytical_method), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_medium_analysis_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_medium_analysis'
QUANTITIES = ('normalized_rate', 'normalized_rate_spread', 'fold_over_control', 'fold_over_control_spread', 'substrate_moved_percent', 'interval',
              'separation_delay', 'replicate_count')
SERIES = 'sampling_times'
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
RATE_BASES = ('cell_protein', 'dry_weight')
ANALYTICAL_METHODS = ('hplc', 'lc_ms', 'enzymatic_analyzer', 'ion_analysis')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'cell_free_control_done': YES_NO, 'zero_time_sample_taken': YES_NO, 'empty_vector_control_done': YES_NO, 'expression_confirmed': YES_NO,
         'calibration_in_medium': YES_NO, 'internal_standard_used': YES_NO, 'linear_time_course': YES_NO, 'immediate_separation': YES_NO,
         'substrate_identity_confirmed': YES_NO, 'substrate_metabolism_excluded': YES_NO, 'reuptake_excluded': YES_NO, 'lysis_excluded': YES_NO,
         'energy_source_provided': YES_NO, 'native_substrate': YES_NO, 'independent_replicates': YES_NO, 'transport_detected_above_control': YES_NO}

RATE_UNITS = ('pmol/min/mg', 'nmol/min/mg', 'umol/min/mg', 'umol/min/g')
TIME_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity (and of the sampling times): the units a record may carry.
UNITS = {'normalized_rate': RATE_UNITS, 'normalized_rate_spread': RATE_UNITS, 'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',),
         'substrate_moved_percent': ('percent',), 'interval': TIME_UNITS, 'separation_delay': TIME_UNITS, 'replicate_count': ('count',),
         'sampling_times': TIME_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
