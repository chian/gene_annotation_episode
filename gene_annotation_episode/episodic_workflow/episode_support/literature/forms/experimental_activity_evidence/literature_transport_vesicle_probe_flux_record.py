"""The extracted record of ONE continuous vesicle flux experiment read by a probe (type 'transport_vesicle_probe_flux', class transport_response).

The assay: vesicles (liposomes with a purified protein reconstituted into them, or vesicles made from membranes) hold an ion or a substrate inside, or have it
added outside. When the transport starts, the amount that leaves (or enters) is followed continuously, in real time, by a probe that does not need a label on the
substrate: an ion-selective electrode in the bath (for example a fluoride or chloride electrode), or a dye trapped inside the vesicles (pyranine or fluorescein
for pH, ACMA for protons, an ion-sensitive dye). Ionophores (valinomycin, CCCP) are often added to supply the counter-ion or to set the gradient. At the end a
detergent is added to release everything that is left, and that total is taken as the whole pool. The experiment reports the fraction of the pool released over
time (and the same for protein-free vesicles), a rate constant or a half-time of the release, and sometimes a rate per mg of protein, a rate per transporter or
the fold over protein-free vesicles. It is NOT this method when the substrate carries a radioactive or fluorescent label and the vesicles or cells are stopped,
separated and counted (the tracer types), when the substrate is measured by chemical analysis in samples taken at times, when the cells themselves carry the
probe, when a current is recorded (patch clamp, oocyte clamp, planar bilayer, solid-supported membrane), or when only growth of cells depends on the transport.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_vesicle_probe_flux'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as the
               class note of 2026-11-22 sets them (owner to confirm): the purified protein preparation (or the cell culture the native vesicles were made from) is
               the analyte_preparation_ref; the reconstituted vesicle batch is the immobilized_preparation_ref; there is no electrode surface that holds the membrane,
               so surface_ref stays None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     The three effect quantities of the class that a vesicle flux experiment can state, each with the spread the passage gives for it (in the unit of the
               quantity):
                 turnover and turnover_spread                           s^-1 or min^-1      ions or molecules moved per second by ONE transporter or channel
                 normalized_rate and normalized_rate_spread             pmol/min/mg, nmol/min/mg or umol/min/mg   the flux per mg of protein
                 fold_over_control and fold_over_control_spread         fold                the flux of the protein vesicles over that of the paper's own protein-free vesicles
               the release the experiment reads and the control beside it:
                 release_fraction          percent        the share of the whole (detergent-released) pool that left the vesicles with the protein, at release_time
                 control_release_fraction  percent        the same share for the protein-free vesicles, at the same time
                 release_time              s or min       the time at which those shares were read
               the rate of the release as the vesicle population shows it, and the response of the apparatus (context for what the rate means):
                 rate_constant             s^-1 or min^-1 the first-order rate constant of the release of the pool from the vesicles
                 half_time                 s or min       the half-time of the release
                 dead_time                 ms or s        the response time (or dead time) of the electrode, dye or mixing
               and the count behind the numbers:
                 replicate_count           count          the number of replicate experiments
               rate_constant and half_time are NOT turnover: they are the rate of the whole vesicle population, which depends on how many transporters each vesicle holds,
               so they are never an effect of this class (the class reads any s^-1 transport rate as a turnover per transporter). They are kept for the time-resolution
               criterion only.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
probe_kind     'ion_selective_electrode' or 'entrapped_dye' or None: how the flux was read. Kept for the reviewer; no criterion rests on it (a choice holds no span in
               the merged record).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, probe_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how
well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else'
(the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an
unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is
only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_vesicle_probe_flux_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_vesicle_probe_flux'
QUANTITIES = ('turnover', 'turnover_spread', 'normalized_rate', 'normalized_rate_spread', 'fold_over_control', 'fold_over_control_spread', 'release_fraction',
              'control_release_fraction', 'release_time', 'rate_constant', 'half_time', 'dead_time', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
PROBE_KINDS = ('ion_selective_electrode', 'entrapped_dye')
# The plain choice fields: name -> vocabulary. They are kept in the record for the reviewer; no criterion rests on one.
CHOICES = {'spread_kind': SPREAD_KINDS, 'probe_kind': PROBE_KINDS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'protein_free_vesicle_control_done': YES_NO, 'second_ion_control_done': YES_NO, 'probe_selective_for_ion': YES_NO, 'ionophore_control_done': YES_NO,
         'gradient_defined': YES_NO, 'detergent_reference_done': YES_NO, 'probe_calibrated': YES_NO, 'vesicle_integrity_checked': YES_NO,
         'protein_quantified_in_vesicles': YES_NO, 'flux_faster_than_apparatus_response': YES_NO, 'native_substrate': YES_NO, 'purified_protein': YES_NO,
         'independent_replicates': YES_NO, 'transport_detected_above_control': YES_NO}

TURNOVER_UNITS = ('s^-1', 'min^-1')
RATE_UNITS = ('pmol/min/mg', 'nmol/min/mg', 'umol/min/mg')
TIME_UNITS = ('s', 'min')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS, 'normalized_rate': RATE_UNITS, 'normalized_rate_spread': RATE_UNITS,
         'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',), 'release_fraction': ('percent',), 'control_release_fraction': ('percent',),
         'release_time': TIME_UNITS, 'rate_constant': TURNOVER_UNITS, 'half_time': TIME_UNITS, 'dead_time': ('ms', 's'), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
