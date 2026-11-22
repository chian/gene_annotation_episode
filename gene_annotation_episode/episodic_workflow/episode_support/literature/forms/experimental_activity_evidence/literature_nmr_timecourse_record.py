"""The extracted record of ONE real-time NMR progress-curve enzyme assay (type 'nmr_timecourse', class activity_rate).

An activity_rate type built from the shape of 'spectro_direct' (the first type of the class); every file of a type is a private copy. The assay:
one enzyme and its substrate are mixed in an NMR tube (1H, 13C, 31P or 19F) and a series of spectra is recorded while the reaction runs; the
integral of a substrate resonance and of a product resonance in each spectrum gives the amount of each species over time (against an internal
concentration standard, or as a share of the sum of the two), and the initial slope, or a fit of the whole curve, gives the rate, kcat, Km or
a specific activity. What marks the method is that the species are told apart by their chemical shifts (the product is seen, not inferred from
a dye), and that the amounts come from integrals, which are quantitative only when the nuclei have relaxed between scans and the signal stands
well above the noise; the method is also insensitive, so it uses micromolar enzyme and millimolar substrate.

This is what a leaf extraction holds for one such assay, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('nmr_timecourse'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized
               enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so
               the extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity):
                 catalytic_efficiency (kcat/Km) and catalytic_efficiency_spread     M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1
                 turnover (kcat) and turnover_spread                                s^-1 or min^-1
                 specific_activity and specific_activity_spread                     U/mg, umol/min/mg or nmol/min/mg
                 rate_over_control and rate_over_control_spread                     fold (the rate of the enzyme over the paper's own control)
               the conditions that decide how far a rate can be trusted (as in spectro_direct):
                 km                       nM, uM or mM                the Michaelis constant the passage reports
                 substrate_concentration  nM, uM or mM                the substrate concentration at which the reported rate was measured
                 enzyme_concentration     nM or uM                    the enzyme concentration of that measurement
                 substrate_consumed_percent  percent                  the share of the substrate consumed in the window the rate was taken from
                 enzyme_mass              kDa                         the molar mass of the enzyme (a subunit) the passage gives
                 replicate_count          count                       the number of replicate time courses
               and the numbers that decide whether the integrals are quantitative (specific to the method):
                 signal_to_noise          ratio                       the signal-to-noise ratio of the integrated product (or substrate) resonance
                 relaxation_delay         s or ms                     the delay between scans (relaxation delay or recycle time)
                 longest_t1               s or ms                     the longest spin-lattice relaxation time T1 of the integrated resonances (or of the standard)
                 time_point_count         count                       the number of spectra (time points) from which the rate was taken
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the saturation curve, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
nucleus        '1H', '13C', '31P', '19F', '15N' or None: the nucleus the integrals come from. Recorded only; no criterion reads it.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, nucleus), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_nmr_timecourse_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'nmr_timecourse'
QUANTITIES = ('catalytic_efficiency', 'catalytic_efficiency_spread', 'turnover', 'turnover_spread', 'specific_activity', 'specific_activity_spread',
              'rate_over_control', 'rate_over_control_spread', 'km', 'substrate_concentration', 'enzyme_concentration', 'substrate_consumed_percent',
              'enzyme_mass', 'replicate_count', 'signal_to_noise', 'relaxation_delay', 'longest_t1', 'time_point_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
NUCLEI = ('1H', '13C', '31P', '19F', '15N')
# The plain choice fields (recording only; a choice carries no span after the merge, so no criterion reads one): name -> its vocabulary.
CHOICES = {'spread_kind': SPREAD_KINDS, 'nucleus': NUCLEI}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'pre_reaction_spectrum': YES_NO, 'rate_proportional_to_enzyme': YES_NO,
         'product_assigned': YES_NO, 'internal_standard_used': YES_NO, 'mass_balance_closed': YES_NO, 'fully_relaxed_acquisition': YES_NO,
         'linear_progress_curve': YES_NO, 'active_site_concentration_determined': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO,
         'independent_replicates': YES_NO, 'activity_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
EFFICIENCY_UNITS = ('M^-1 s^-1', 'mM^-1 s^-1', 'uM^-1 s^-1')
TURNOVER_UNITS = ('s^-1', 'min^-1')
SPECIFIC_ACTIVITY_UNITS = ('U/mg', 'umol/min/mg', 'nmol/min/mg')
TIME_UNITS = ('s', 'ms')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'catalytic_efficiency': EFFICIENCY_UNITS, 'catalytic_efficiency_spread': EFFICIENCY_UNITS, 'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS,
         'specific_activity': SPECIFIC_ACTIVITY_UNITS, 'specific_activity_spread': SPECIFIC_ACTIVITY_UNITS, 'rate_over_control': ('fold',), 'rate_over_control_spread': ('fold',),
         'km': CONCENTRATION_UNITS, 'substrate_concentration': CONCENTRATION_UNITS, 'enzyme_concentration': ('nM', 'uM'), 'substrate_consumed_percent': ('percent',),
         'enzyme_mass': ('kDa',), 'replicate_count': ('count',), 'signal_to_noise': ('ratio',), 'relaxation_delay': TIME_UNITS, 'longest_t1': TIME_UNITS,
         'time_point_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
