"""The extracted record of ONE artificial redox-mediator enzyme assay (type 'redox_mediator', class activity_rate).

DRAFT of the third type of the activity_rate class (2026-11-22), copied from the shape of the first type, spectro_direct. The assay: one
oxidoreductase, its substrate (an electron donor or acceptor) and an ARTIFICIAL electron acceptor or donor, a redox dye that stands in for the
enzyme's natural redox partner (DCPIP, ferricyanide, methyl or benzyl viologen, a tetrazolium dye such as TTC, INT or MTT, a quinone, cytochrome c,
ferrocenium). The colour change of the dye (its reduction or its oxidation) is read over time, and its initial slope is turned into a rate with
the dye's extinction coefficient and the number of electrons per dye molecule. It differs from a direct spectrophotometric assay in what decides
the meaning of the number: the dye can be reduced without the enzyme (thiols, flavins, light), it can be re-oxidised by oxygen, and it can take
electrons from a site the natural partner never reaches (a mediator can bypass the native electron transfer), so the rate with a dye is not
automatically the rate of the claimed reaction.

This is what a leaf extraction holds for one such assay, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('redox_mediator'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The enzyme
               preparation is the analyte_preparation_ref; this type has no immobilized enzyme and no electrode, so the other keys stay None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity):
                 catalytic_efficiency (kcat/Km) and catalytic_efficiency_spread     M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1
                 turnover (kcat) and turnover_spread                                s^-1 or min^-1
                 specific_activity and specific_activity_spread                     U/mg, umol/min/mg or nmol/min/mg
                 rate_over_control and rate_over_control_spread                     fold (the rate of the enzyme over the paper's own control)
               and the conditions that decide how far a dye rate can be trusted:
                 km                       nM, uM or mM                the Michaelis constant for the substrate whose concentration the series varies
                 mediator_km              nM, uM or mM                the Michaelis constant of the enzyme for the artificial dye
                 mediator_concentration   nM, uM or mM                the concentration of the dye in the reaction in which the rate was measured
                 dye_consumed_percent     percent                     the share of the dye consumed in the window the rate was taken from
                 wavelength               nm                          the wavelength the absorbance of the dye was read at
                 extinction_coefficient   M^-1 cm^-1 or mM^-1 cm^-1  the extinction coefficient of the dye used to turn absorbance into concentration
                 absorbance_max           AU                          the highest absorbance reached in the measurement
                 enzyme_mass              kDa                         the molar mass of the enzyme (a subunit) the passage gives
                 replicate_count          count                       the number of replicate experiments
concentration_series
               operand whose 'value' is a list of concentrations (nM, uM or mM) of the substrate of the saturation curve, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
mediator_kind  which artificial redox partner the assay used (MEDIATOR_KINDS) or None. Recorded only: no criterion rests on it.
mediator_role  whether the dye is the electron acceptor or the electron donor of the reaction (MEDIATOR_ROLES) or None. Recorded only.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, mediator_kind, mediator_role), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_redox_mediator_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'redox_mediator'
QUANTITIES = ('catalytic_efficiency', 'catalytic_efficiency_spread', 'turnover', 'turnover_spread', 'specific_activity', 'specific_activity_spread',
              'rate_over_control', 'rate_over_control_spread', 'km', 'mediator_km', 'mediator_concentration', 'dye_consumed_percent',
              'wavelength', 'extinction_coefficient', 'absorbance_max', 'enzyme_mass', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
MEDIATOR_KINDS = ('dcpip', 'ferricyanide', 'viologen', 'tetrazolium', 'quinone', 'phenazine', 'cytochrome_c', 'ferrocenium', 'other_mediator')
MEDIATOR_ROLES = ('electron_acceptor', 'electron_donor')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_substrate_control': YES_NO, 'rate_proportional_to_enzyme': YES_NO,
         'linear_progress_curve': YES_NO, 'active_site_concentration_determined': YES_NO, 'native_substrate': YES_NO, 'native_electron_partner_used': YES_NO,
         'oxygen_excluded': YES_NO, 'reduced_dye_reoxidised_by_oxygen': YES_NO, 'electron_stoichiometry_stated': YES_NO, 'product_identified': YES_NO,
         'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'activity_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
EFFICIENCY_UNITS = ('M^-1 s^-1', 'mM^-1 s^-1', 'uM^-1 s^-1')
TURNOVER_UNITS = ('s^-1', 'min^-1')
SPECIFIC_ACTIVITY_UNITS = ('U/mg', 'umol/min/mg', 'nmol/min/mg')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'catalytic_efficiency': EFFICIENCY_UNITS, 'catalytic_efficiency_spread': EFFICIENCY_UNITS, 'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS,
         'specific_activity': SPECIFIC_ACTIVITY_UNITS, 'specific_activity_spread': SPECIFIC_ACTIVITY_UNITS, 'rate_over_control': ('fold',), 'rate_over_control_spread': ('fold',),
         'km': CONCENTRATION_UNITS, 'mediator_km': CONCENTRATION_UNITS, 'mediator_concentration': CONCENTRATION_UNITS, 'dye_consumed_percent': ('percent',),
         'wavelength': ('nm',), 'extinction_coefficient': ('M^-1 cm^-1', 'mM^-1 cm^-1'), 'absorbance_max': ('AU',), 'enzyme_mass': ('kDa',), 'replicate_count': ('count',),
         'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
