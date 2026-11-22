"""The extracted record of ONE antibody-detected enzyme reaction (type 'product_immunodetection', class activity_rate).

DRAFT of the activity_rate type "antibody detection of the modified product" (drafted 2026-11-22 from the structure of spectro_direct; nothing has
been run). The assay: one enzyme and its substrate (a peptide or a protein) react with a donor of the modification (ATP, S-adenosylmethionine,
acetyl-CoA, ubiquitin and so on), the reaction is stopped, and an antibody that recognises the modified product (a phospho-, methyl-, acetyl- or
ubiquitin-specific antibody) reads how much product formed: TR-FRET / HTRF (the 665/620 nm ratio), ELISA, AlphaScreen or AlphaLISA, or an in vitro
reaction run on a gel and read with the antibody. The signal is relative; it becomes an amount only through a product standard series. It says
how much of the claimed modification the enzyme made.

This is what a leaf extraction holds for one such assay, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('product_immunodetection'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized
               enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. (A bead or plate that carries the antibody is the
               detection, not the enzyme.) No passage states a preparation reference, so the extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity):
                 catalytic_efficiency (kcat/Km) and catalytic_efficiency_spread     M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1
                 turnover (kcat) and turnover_spread                                s^-1 or min^-1
                 specific_activity and specific_activity_spread                     U/mg, umol/min/mg, nmol/min/mg, pmol/min/ug or pmol/min/mg
                 rate_over_control and rate_over_control_spread                     fold (the product signal or amount of the reaction over that of
                                                                                    the paper's own no-enzyme or inactive-enzyme control)
               and the conditions that decide how far the result can be trusted:
                 km                       nM, uM or mM        the Michaelis constant the passage reports
                 substrate_concentration  nM, uM or mM        the substrate concentration at which the reported rate was measured
                 enzyme_concentration     nM or uM            the enzyme concentration of that measurement
                 substrate_converted_percent  percent         the share of the substrate converted to product when the reaction was stopped
                 z_prime                  unitless            the Z' factor of the assay the passage reports (Zhang, Chung and Oldenburg 1999)
                 signal_to_background     fold                the signal of the reaction over the background (signal-to-background, S/B) the passage reports
                 enzyme_mass              kDa                 the molar mass of the enzyme (a subunit) the passage gives
                 replicate_count          count               the number of replicate experiments
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the saturation curve, or None.
standard_series
               operand whose 'value' is a list of the product amounts of the product standard series (nM, uM, mM, pmol or nmol; the unit
               of the standard series as the passage gives it), or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_product_immunodetection_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'product_immunodetection'
QUANTITIES = ('catalytic_efficiency', 'catalytic_efficiency_spread', 'turnover', 'turnover_spread', 'specific_activity', 'specific_activity_spread',
              'rate_over_control', 'rate_over_control_spread', 'km', 'substrate_concentration', 'enzyme_concentration', 'substrate_converted_percent',
              'z_prime', 'signal_to_background', 'enzyme_mass', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_cofactor_control': YES_NO, 'no_substrate_control': YES_NO,
         'antibody_specific_for_product': YES_NO, 'rate_proportional_to_enzyme': YES_NO, 'linear_in_time': YES_NO, 'product_standard_curve': YES_NO,
         'signal_within_standard_range': YES_NO, 'active_site_concentration_determined': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO,
         'product_identified': YES_NO, 'independent_replicates': YES_NO, 'activity_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
STANDARD_UNITS = ('nM', 'uM', 'mM', 'pmol', 'nmol')
EFFICIENCY_UNITS = ('M^-1 s^-1', 'mM^-1 s^-1', 'uM^-1 s^-1')
TURNOVER_UNITS = ('s^-1', 'min^-1')
SPECIFIC_ACTIVITY_UNITS = ('U/mg', 'umol/min/mg', 'nmol/min/mg', 'pmol/min/ug', 'pmol/min/mg')
# The unit vocabulary of each quantity (and of the two series): the units a record may carry.
UNITS = {'catalytic_efficiency': EFFICIENCY_UNITS, 'catalytic_efficiency_spread': EFFICIENCY_UNITS, 'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS,
         'specific_activity': SPECIFIC_ACTIVITY_UNITS, 'specific_activity_spread': SPECIFIC_ACTIVITY_UNITS, 'rate_over_control': ('fold',), 'rate_over_control_spread': ('fold',),
         'km': CONCENTRATION_UNITS, 'substrate_concentration': CONCENTRATION_UNITS, 'enzyme_concentration': ('nM', 'uM'), 'substrate_converted_percent': ('percent',),
         'z_prime': ('unitless',), 'signal_to_background': ('fold',), 'enzyme_mass': ('kDa',), 'replicate_count': ('count',),
         'concentration_series': CONCENTRATION_UNITS, 'standard_series': STANDARD_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
